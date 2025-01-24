-- Trade Configurations
CREATE TABLE IF NOT EXISTS trade_configurations (
    id SERIAL PRIMARY KEY,
    name VARCHAR,
    channel_id VARCHAR,
    role_id VARCHAR,
    roadmap_channel_id VARCHAR,
    update_channel_id VARCHAR,
    portfolio_channel_id VARCHAR,
    log_channel_id VARCHAR
);

-- Bot Configurations
CREATE TABLE IF NOT EXISTS bot_configurations (
    id SERIAL PRIMARY KEY,
    watchlist_channel_id VARCHAR,
    ta_channel_id VARCHAR
);

-- Roles
CREATE TABLE IF NOT EXISTS roles (
    id SERIAL PRIMARY KEY,
    role_id VARCHAR,
    guild_id VARCHAR,
    UNIQUE(role_id, guild_id)
);

-- Role Requirements
CREATE TABLE IF NOT EXISTS role_requirements (
    id SERIAL PRIMARY KEY,
    guild_id VARCHAR
);

-- Role Requirement Roles (Junction Table)
CREATE TABLE IF NOT EXISTS role_requirement_roles (
    role_requirement_id INTEGER REFERENCES role_requirements(id),
    role_id INTEGER REFERENCES roles(id),
    PRIMARY KEY (role_requirement_id, role_id)
);

-- Conditional Role Grants
CREATE TABLE IF NOT EXISTS conditional_role_grants (
    id SERIAL PRIMARY KEY,
    guild_id VARCHAR,
    grant_role_id VARCHAR,
    exclude_role_id VARCHAR
);

-- Conditional Role Grant Condition Roles (Junction Table)
CREATE TABLE IF NOT EXISTS conditional_role_grant_condition_roles (
    conditional_role_grant_id INTEGER REFERENCES conditional_role_grants(id),
    role_id INTEGER REFERENCES roles(id),
    PRIMARY KEY (conditional_role_grant_id, role_id)
);

-- Verification Configs
CREATE TABLE IF NOT EXISTS verification_configs (
    id SERIAL PRIMARY KEY,
    message_id VARCHAR UNIQUE,
    channel_id VARCHAR,
    role_to_remove_id VARCHAR,
    role_to_add_id VARCHAR,
    log_channel_id VARCHAR,
    terms_of_service_link VARCHAR,
);

-- User Verification Status
-- THIS IS NEW FOR SUPABASE
-- MUST BE IMPLEMENTED IN DISCORD BOT
CREATE TABLE IF NOT EXISTS user_verification_status (
    id SERIAL PRIMARY KEY,
    discord_id VARCHAR,
    discord_username VARCHAR,
    email VARCHAR,
    full_name VARCHAR,
    verification_status VARCHAR,
    configuration_id INTEGER REFERENCES verification_configs(id),
    verified_at TIMESTAMPTZ,
    UNIQUE(discord_id)
);

-- Verifications
CREATE TABLE IF NOT EXISTS verifications (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR,
    username VARCHAR,
    configuration_id INTEGER REFERENCES verification_configs(id),
    timestamp TIMESTAMPTZ,
    UNIQUE(user_id)
);

-- Options Strategy Trades
CREATE TABLE IF NOT EXISTS options_strategy_trades (
    id SERIAL PRIMARY KEY,
    trade_id VARCHAR UNIQUE,
    name VARCHAR,
    underlying_symbol VARCHAR,
    status VARCHAR,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    closed_at TIMESTAMPTZ,
    configuration_id INTEGER REFERENCES trade_configurations(id),
    trade_group VARCHAR,
    legs TEXT NOT NULL,
    net_cost FLOAT NOT NULL,
    average_net_cost FLOAT NOT NULL,
    size VARCHAR NOT NULL,
    current_size VARCHAR NOT NULL
);

-- Trades
CREATE TABLE IF NOT EXISTS trades (
    trade_id VARCHAR PRIMARY KEY,
    symbol VARCHAR NOT NULL,
    trade_type VARCHAR NOT NULL,
    status VARCHAR NOT NULL,
    entry_price FLOAT NOT NULL,
    average_price FLOAT,
    current_size VARCHAR,
    size VARCHAR NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    closed_at TIMESTAMPTZ,
    exit_price FLOAT,
    average_exit_price FLOAT,
    profit_loss FLOAT,
    risk_reward_ratio FLOAT,
    win_loss VARCHAR,
    configuration_id INTEGER REFERENCES trade_configurations(id),
    is_contract BOOLEAN DEFAULT FALSE,
    is_day_trade BOOLEAN DEFAULT FALSE,
    strike FLOAT,
    expiration_date TIMESTAMPTZ,
    option_type VARCHAR
);

-- Transactions
CREATE TABLE IF NOT EXISTS transactions (
    id VARCHAR PRIMARY KEY,
    trade_id VARCHAR REFERENCES trades(trade_id),
    transaction_type VARCHAR,
    amount FLOAT,
    size VARCHAR,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Options Strategy Transactions
CREATE TABLE IF NOT EXISTS options_strategy_transactions (
    id SERIAL PRIMARY KEY,
    strategy_id INTEGER REFERENCES options_strategy_trades(id),
    transaction_type VARCHAR NOT NULL,
    net_cost FLOAT NOT NULL,
    size VARCHAR NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for frequently queried columns
CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol);
CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status);
CREATE INDEX IF NOT EXISTS idx_trades_created_at ON trades(created_at);
CREATE INDEX IF NOT EXISTS idx_verifications_user_id ON verifications(user_id);
CREATE INDEX IF NOT EXISTS idx_options_strategy_trades_underlying ON options_strategy_trades(underlying_symbol);

-- Create function to update trade after transaction changes
CREATE OR REPLACE FUNCTION update_trade_before_transaction_change()
RETURNS TRIGGER AS $$
DECLARE
    total_cost FLOAT := 0;
    total_shares FLOAT := 0;
    total_exit_cost FLOAT := 0;
    total_exit_shares FLOAT := 0;
    updated_trade RECORD;
    transaction_record RECORD;
    newest_transaction_id VARCHAR;
BEGIN
    -- For DELETE operations, verify this is the newest transaction
    IF TG_OP = 'DELETE' THEN
        SELECT id INTO newest_transaction_id
        FROM transactions
        WHERE trade_id = OLD.trade_id
        ORDER BY created_at DESC
        LIMIT 1;

        IF OLD.id != newest_transaction_id THEN
            RAISE EXCEPTION 'Only the most recent transaction can be deleted';
        END IF;
    END IF;

    -- Get all transactions for this trade, ordered by creation time
    FOR transaction_record IN (
        SELECT 
            transaction_type,
            amount,
            size,
            created_at,
            id
        FROM transactions 
        WHERE trade_id = COALESCE(NEW.trade_id, OLD.trade_id)
        AND id != COALESCE(OLD.id, '0')  -- Exclude the transaction being deleted if any
        ORDER BY created_at ASC
    ) LOOP
        -- Process each transaction
        CASE transaction_record.transaction_type
            WHEN 'OPEN' THEN
                total_cost := total_cost + (transaction_record.amount * CAST(transaction_record.size AS FLOAT));
                total_shares := total_shares + CAST(transaction_record.size AS FLOAT);
            WHEN 'ADD' THEN
                total_cost := total_cost + (transaction_record.amount * CAST(transaction_record.size AS FLOAT));
                total_shares := total_shares + CAST(transaction_record.size AS FLOAT);
            WHEN 'TRIM' THEN
                total_exit_cost := total_exit_cost + (transaction_record.amount * CAST(transaction_record.size AS FLOAT));
                total_exit_shares := total_exit_shares + CAST(transaction_record.size AS FLOAT);
                total_shares := total_shares - CAST(transaction_record.size AS FLOAT);
            WHEN 'CLOSE' THEN
                total_exit_cost := total_exit_cost + (transaction_record.amount * CAST(transaction_record.size AS FLOAT));
                total_exit_shares := total_exit_shares + CAST(transaction_record.size AS FLOAT);
                total_shares := total_shares - CAST(transaction_record.size AS FLOAT);
        END CASE;
    END LOOP;

    -- If this is an insert or update, add the new transaction to the totals
    IF TG_OP IN ('INSERT', 'UPDATE') THEN
        CASE NEW.transaction_type
            WHEN 'OPEN' THEN
                total_cost := total_cost + (NEW.amount * CAST(NEW.size AS FLOAT));
                total_shares := total_shares + CAST(NEW.size AS FLOAT);
            WHEN 'ADD' THEN
                total_cost := total_cost + (NEW.amount * CAST(NEW.size AS FLOAT));
                total_shares := total_shares + CAST(NEW.size AS FLOAT);
            WHEN 'TRIM' THEN
                total_exit_cost := total_exit_cost + (NEW.amount * CAST(NEW.size AS FLOAT));
                total_exit_shares := total_exit_shares + CAST(NEW.size AS FLOAT);
                total_shares := total_shares - CAST(NEW.size AS FLOAT);
            WHEN 'CLOSE' THEN
                total_exit_cost := total_exit_cost + (NEW.amount * CAST(NEW.size AS FLOAT));
                total_exit_shares := total_exit_shares + CAST(NEW.size AS FLOAT);
                total_shares := total_shares - CAST(NEW.size AS FLOAT);
        END CASE;
    END IF;

    -- Calculate average prices and profit/loss
    DECLARE
        avg_entry_price FLOAT;
        avg_exit_price FLOAT;
        total_pl FLOAT;
    BEGIN
        -- Calculate averages only when we have shares
        avg_entry_price := CASE 
            WHEN total_shares + total_exit_shares > 0 THEN total_cost / (total_shares + total_exit_shares)
            ELSE NULL
        END;

        avg_exit_price := CASE 
            WHEN total_exit_shares > 0 THEN total_exit_cost / total_exit_shares
            ELSE NULL
        END;

        -- Calculate P/L: (exit price - entry price) * shares sold
        total_pl := CASE 
            WHEN total_exit_shares > 0 THEN 
                (total_exit_cost - (avg_entry_price * total_exit_shares))
            ELSE NULL
        END;

        -- Update the trade with calculated values
        UPDATE trades 
        SET 
            average_price = avg_entry_price,
            current_size = CASE 
                WHEN total_shares > 0 THEN total_shares::TEXT
                ELSE '0'
            END,
            status = CASE 
                WHEN total_shares > 0 THEN 'OPEN'
                ELSE 'CLOSED'
            END,
            closed_at = CASE 
                WHEN total_shares <= 0 THEN 
                    CASE 
                        WHEN TG_OP IN ('INSERT', 'UPDATE') THEN NEW.created_at
                        ELSE (
                            SELECT created_at 
                            FROM transactions 
                            WHERE trade_id = COALESCE(NEW.trade_id, OLD.trade_id)
                            ORDER BY created_at DESC 
                            LIMIT 1
                        )
                    END
                ELSE NULL
            END,
            exit_price = CASE 
                WHEN total_shares <= 0 THEN avg_exit_price
                ELSE NULL
            END,
            average_exit_price = avg_exit_price,
            profit_loss = total_pl,
            win_loss = CASE
                WHEN total_pl > 0 THEN 'WIN'
                WHEN total_pl < 0 THEN 'LOSS'
                WHEN total_pl = 0 THEN 'BREAKEVEN'
                ELSE NULL
            END
        WHERE trade_id = COALESCE(NEW.trade_id, OLD.trade_id)
        RETURNING * INTO updated_trade;
    END;

    -- Return the appropriate record based on operation type
    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    ELSE
        RETURN NEW;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Drop existing triggers if they exist
DROP TRIGGER IF EXISTS transaction_after_insert_update ON transactions;
DROP TRIGGER IF EXISTS transaction_after_delete ON transactions;

-- Create new BEFORE triggers for transaction changes
CREATE TRIGGER transaction_before_insert_update
    BEFORE INSERT OR UPDATE ON transactions
    FOR EACH ROW
    EXECUTE FUNCTION update_trade_before_transaction_change();

CREATE TRIGGER transaction_before_delete
    BEFORE DELETE ON transactions
    FOR EACH ROW
    EXECUTE FUNCTION update_trade_before_transaction_change();

-- Create function to close expired trades
CREATE OR REPLACE FUNCTION close_expired_trades()
RETURNS trigger AS $$
DECLARE
    expired_trade RECORD;
    new_transaction_id VARCHAR;
BEGIN
    -- Find trades that have just expired (expiration_date is in the past and status is still OPEN)
    FOR expired_trade IN
        SELECT trade_id, current_size
        FROM trades
        WHERE expiration_date IS NOT NULL
        AND expiration_date < CURRENT_TIMESTAMP
        AND status = 'OPEN'
    LOOP
        -- Generate a new transaction ID (using the same format as your application)
        SELECT CAST(EXTRACT(EPOCH FROM CURRENT_TIMESTAMP) * 1000 AS BIGINT)::TEXT INTO new_transaction_id;
        
        -- Insert a CLOSE transaction at $0
        INSERT INTO transactions (
            id,
            trade_id,
            transaction_type,
            amount,
            size,
            created_at
        ) VALUES (
            new_transaction_id,
            expired_trade.trade_id,
            'CLOSE',
            0, -- Close at $0 since it expired
            expired_trade.current_size, -- Close the entire position
            CURRENT_TIMESTAMP
        );
        
        -- The existing transaction trigger will handle updating the trade status
    END LOOP;
    
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to check for expired trades
CREATE OR REPLACE TRIGGER check_expired_trades
    AFTER INSERT OR UPDATE ON trades
    FOR EACH ROW
    WHEN (NEW.expiration_date IS NOT NULL AND NEW.status = 'OPEN')
    EXECUTE FUNCTION close_expired_trades();

-- Also create a scheduled job to run periodically to catch any trades that expire between updates
CREATE EXTENSION IF NOT EXISTS pg_cron;

-- Run at 4:45 PM Monday-Friday (16:45)
SELECT cron.schedule('check_expired_trades', '45 16 * * 1-5', $$
    SELECT close_expired_trades();
$$);