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
            UPPER(transaction_type) as transaction_type,  -- Convert to uppercase for consistency
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
            ELSE
                RAISE EXCEPTION 'Invalid transaction type: %', transaction_record.transaction_type;
        END CASE;
    END LOOP;

    -- If this is an insert or update, add the new transaction to the totals
    IF TG_OP IN ('INSERT', 'UPDATE') THEN
        CASE UPPER(NEW.transaction_type)  -- Convert to uppercase for consistency
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
            ELSE
                RAISE EXCEPTION 'Invalid transaction type: %', NEW.transaction_type;
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

-- Update monthly P/L table structure
CREATE TABLE IF NOT EXISTS monthly_pl (
    id SERIAL PRIMARY KEY,
    configuration_id INTEGER REFERENCES trade_configurations(id),
    month DATE NOT NULL, -- Stored as first day of month
    regular_trades_pl DOUBLE PRECISION NOT NULL DEFAULT 0,
    strategy_trades_pl DOUBLE PRECISION NOT NULL DEFAULT 0,
    total_pl DOUBLE PRECISION GENERATED ALWAYS AS (regular_trades_pl + strategy_trades_pl) STORED,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(configuration_id, month)
);

-- Function to calculate P/L with multiplier based on trade type and symbol
CREATE OR REPLACE FUNCTION calculate_pl_with_multiplier(
    trade_type TEXT,
    symbol TEXT,
    base_pl DOUBLE PRECISION
) RETURNS DOUBLE PRECISION AS $$
BEGIN
    -- For common stock ES, multiply by 5
    IF trade_type = 'common' AND symbol = 'ES' THEN
        RETURN base_pl * 5;
    -- For other common stock, multiply by 10
    ELSIF trade_type = 'common' THEN
        RETURN base_pl * 10;
    -- For options contracts, multiply by 100
    ELSE
        RETURN base_pl * 100;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Function to calculate realized P/L for a specific trade and transaction
CREATE OR REPLACE FUNCTION calculate_realized_pl_for_transaction(
    trade_record trades,
    transaction_record transactions
) RETURNS DOUBLE PRECISION AS $$
DECLARE
    realized_pl DOUBLE PRECISION;
BEGIN
    -- For TRIM and CLOSE transactions, calculate the realized P/L
    IF UPPER(transaction_record.transaction_type) IN ('TRIM', 'CLOSE') THEN
        -- Calculate P/L: (exit price - average entry price) * size
        realized_pl := (transaction_record.amount - trade_record.average_price) * 
                      CAST(transaction_record.size AS FLOAT);
        
        -- Apply the appropriate multiplier
        RETURN calculate_pl_with_multiplier(
            trade_record.trade_type,
            trade_record.symbol,
            realized_pl
        );
    END IF;
    
    RETURN 0;
END;
$$ LANGUAGE plpgsql;

-- Function to update monthly P/L
CREATE OR REPLACE FUNCTION update_monthly_pl() RETURNS TRIGGER AS $$
DECLARE
    trade_record trades%ROWTYPE;
    transaction_month DATE;
    realized_pl DOUBLE PRECISION;
BEGIN
    -- Only process TRIM and CLOSE transactions
    IF UPPER(NEW.transaction_type) NOT IN ('TRIM', 'CLOSE') THEN
        RETURN NEW;
    END IF;

    -- Get the associated trade record
    SELECT t.* 
    INTO trade_record
    FROM trades t
    WHERE t.trade_id = NEW.trade_id;

    -- Get the configuration ID separately since it's not part of trades%ROWTYPE
    SELECT c.id INTO trade_record.configuration_id
    FROM trade_configurations c
    WHERE c.id = trade_record.configuration_id;

    -- Calculate the first day of the month for the transaction
    transaction_month := DATE_TRUNC('month', NEW.created_at::DATE);

    -- Calculate P/L for this transaction
    realized_pl := COALESCE(calculate_realized_pl_for_transaction(trade_record, NEW), 0);

    -- Insert or update monthly P/L record
    INSERT INTO monthly_pl (configuration_id, month, regular_trades_pl, strategy_trades_pl)
    VALUES (
        trade_record.configuration_id, 
        transaction_month,
        realized_pl,
        0  -- Strategy P/L will be handled by a separate function
    )
    ON CONFLICT (configuration_id, month)
    DO UPDATE SET 
        regular_trades_pl = COALESCE((
            -- Sum of all realized P/L from TRIM and CLOSE transactions in this month
            SELECT SUM(
                COALESCE(calculate_realized_pl_for_transaction(t, tx), 0)
            )
            FROM trades t
            JOIN transactions tx ON t.trade_id = tx.trade_id
            WHERE t.configuration_id = trade_record.configuration_id
            AND DATE_TRUNC('month', tx.created_at) = transaction_month
            AND UPPER(tx.transaction_type) IN ('TRIM', 'CLOSE')
        ), 0),
        updated_at = CURRENT_TIMESTAMP;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to update monthly P/L after transaction changes
CREATE OR REPLACE TRIGGER update_monthly_pl_trigger
    AFTER INSERT OR UPDATE ON transactions
    FOR EACH ROW
    WHEN (pg_trigger_depth() < 1)  -- Prevent recursive trigger calls
    EXECUTE FUNCTION update_monthly_pl();

-- Function to backfill monthly P/L
CREATE OR REPLACE FUNCTION backfill_monthly_pl() RETURNS void AS $$
DECLARE
    config_record RECORD;
    month_record RECORD;
    trade_record RECORD;
    last_transaction RECORD;
BEGIN
    -- First, clear existing monthly P/L records to avoid duplicates
    TRUNCATE TABLE monthly_pl;
    
    -- For each configuration
    FOR config_record IN SELECT id FROM trade_configurations LOOP
        RAISE NOTICE 'Processing configuration %', config_record.id;
        
        -- For each month where we have TRIM or CLOSE transactions
        FOR month_record IN 
            SELECT DISTINCT DATE_TRUNC('month', tx.created_at) as month
            FROM transactions tx
            JOIN trades t ON tx.trade_id = t.trade_id
            WHERE t.configuration_id = config_record.id 
            AND tx.transaction_type IN ('TRIM', 'CLOSE', 'trim', 'close')
            AND tx.created_at <= CURRENT_TIMESTAMP  -- Include all historical transactions
            ORDER BY month
        LOOP
            RAISE NOTICE 'Processing month %', month_record.month;
            
            -- Insert monthly P/L record
            INSERT INTO monthly_pl (configuration_id, month, regular_trades_pl, strategy_trades_pl)
            VALUES (
                config_record.id,
                month_record.month,
                (
                    -- Calculate regular trades P/L from transactions
                    SELECT COALESCE(SUM(
                        calculate_realized_pl_for_transaction(t, tx)
                    ), 0)
                    FROM trades t
                    JOIN transactions tx ON tx.trade_id = t.trade_id
                    WHERE t.configuration_id = config_record.id
                    AND DATE_TRUNC('month', tx.created_at) = month_record.month
                    AND tx.transaction_type IN ('TRIM', 'CLOSE', 'trim', 'close')
                    AND NOT EXISTS (
                        SELECT 1 FROM options_strategy_trades ost 
                        WHERE ost.trade_id = t.trade_id
                    )
                ),
                (
                    -- Calculate strategy trades P/L from transactions
                    SELECT COALESCE(SUM(
                        calculate_realized_pl_for_transaction(t, tx)
                    ), 0)
                    FROM trades t
                    JOIN transactions tx ON tx.trade_id = t.trade_id
                    WHERE t.configuration_id = config_record.id
                    AND DATE_TRUNC('month', tx.created_at) = month_record.month
                    AND tx.transaction_type IN ('TRIM', 'CLOSE', 'trim', 'close')
                    AND EXISTS (
                        SELECT 1 FROM options_strategy_trades ost 
                        WHERE ost.trade_id = t.trade_id
                    )
                )
            );
            
            -- Log the values we just inserted
            RAISE NOTICE 'Inserted record for config % month %: Regular P/L: %, Strategy P/L: %',
                config_record.id,
                month_record.month,
                (SELECT regular_trades_pl FROM monthly_pl WHERE configuration_id = config_record.id AND month = month_record.month),
                (SELECT strategy_trades_pl FROM monthly_pl WHERE configuration_id = config_record.id AND month = month_record.month);
        END LOOP;
    END LOOP;
    
    -- After processing monthly P/L, update all trades' average prices
    FOR trade_record IN SELECT * FROM trades LOOP
        -- Get the most recent transaction for this trade
        SELECT * INTO last_transaction
        FROM transactions
        WHERE trade_id = trade_record.trade_id
        ORDER BY created_at DESC
        LIMIT 1;
        
        -- If there is a transaction, trigger a recalculation by doing a no-op update
        IF last_transaction IS NOT NULL THEN
            RAISE NOTICE 'Updating averages for trade %', trade_record.trade_id;
            UPDATE transactions 
            SET created_at = created_at  -- No-op update to trigger the recalculation
            WHERE id = last_transaction.id;
        END IF;
    END LOOP;
    
    -- Log final counts
    RAISE NOTICE 'Monthly P/L backfill completed. Total records created: %',
        (SELECT COUNT(*) FROM monthly_pl);
END;
$$ LANGUAGE plpgsql;

-- To run the backfill, execute:
-- SELECT backfill_monthly_pl();

-- Function to clean up transactions and update trade data
CREATE OR REPLACE FUNCTION cleanup_and_update_trades() RETURNS void AS $$
DECLARE
    trade_record RECORD;
    first_close_transaction RECORD;
    extra_close_transaction RECORD;
BEGIN
    -- For each trade
    FOR trade_record IN SELECT * FROM trades LOOP
        RAISE NOTICE 'Processing trade %', trade_record.trade_id;
        
        -- Find the first (oldest) CLOSE transaction for this trade
        SELECT * INTO first_close_transaction
        FROM transactions
        WHERE trade_id = trade_record.trade_id
        AND UPPER(transaction_type) = 'CLOSE'
        ORDER BY created_at ASC
        LIMIT 1;
        
        -- If there is a CLOSE transaction, delete any subsequent CLOSE transactions
        -- Process in reverse chronological order (newest first)
        IF first_close_transaction IS NOT NULL THEN
            FOR extra_close_transaction IN 
                SELECT * FROM transactions 
                WHERE trade_id = trade_record.trade_id
                AND UPPER(transaction_type) = 'CLOSE'
                AND id != first_close_transaction.id
                ORDER BY created_at DESC  -- Changed to DESC to process newest first
            LOOP
                RAISE NOTICE 'Deleting extra CLOSE transaction % for trade %', 
                    extra_close_transaction.id, trade_record.trade_id;
                
                DELETE FROM transactions 
                WHERE id = extra_close_transaction.id;
            END LOOP;
        END IF;
        
        -- Now trigger a recalculation of the trade's data by updating the first CLOSE transaction
        -- This will trigger the update_trade_before_transaction_change function
        IF first_close_transaction IS NOT NULL THEN
            UPDATE transactions 
            SET created_at = created_at  -- No-op update to trigger the recalculation
            WHERE id = first_close_transaction.id;
        END IF;
    END LOOP;
    
    RAISE NOTICE 'Cleanup and update completed successfully';
END;
$$ LANGUAGE plpgsql;

-- To run the cleanup and update:
-- SELECT cleanup_and_update_trades();

-- Function to update options strategy trade based on transactions
CREATE OR REPLACE FUNCTION update_options_strategy_before_transaction_change()
RETURNS TRIGGER AS $$
DECLARE
    strategy_record options_strategy_trades%ROWTYPE;
    total_cost DECIMAL := 0;
    total_size DECIMAL := 0;
    total_exit_cost DECIMAL := 0;
    total_exit_size DECIMAL := 0;
    avg_entry_cost DECIMAL;
    avg_exit_cost DECIMAL;
    total_pl DECIMAL;
BEGIN
    -- Get the strategy record
    SELECT * INTO strategy_record
    FROM options_strategy_trades
    WHERE strategy_id = COALESCE(NEW.strategy_id, OLD.strategy_id);

    -- Calculate totals from all transactions except the current one being modified
    WITH entry_totals AS (
        SELECT 
            SUM(net_cost * CAST(size AS DECIMAL)) as total_cost,
            SUM(CAST(size AS DECIMAL)) as total_size
        FROM options_strategy_transactions
        WHERE strategy_id = strategy_record.strategy_id
        AND transaction_id != COALESCE(NEW.transaction_id, OLD.transaction_id)
        AND transaction_type IN ('OPEN', 'ADD')
    ),
    exit_totals AS (
        SELECT 
            SUM(net_cost * CAST(size AS DECIMAL)) as total_cost,
            SUM(CAST(size AS DECIMAL)) as total_size
        FROM options_strategy_transactions
        WHERE strategy_id = strategy_record.strategy_id
        AND transaction_id != COALESCE(NEW.transaction_id, OLD.transaction_id)
        AND transaction_type IN ('TRIM', 'CLOSE')
    )
    SELECT 
        COALESCE(entry_totals.total_cost, 0),
        COALESCE(entry_totals.total_size, 0),
        COALESCE(exit_totals.total_cost, 0),
        COALESCE(exit_totals.total_size, 0)
    INTO
        total_cost, total_size,
        total_exit_cost, total_exit_size
    FROM (SELECT 1) t
    LEFT JOIN entry_totals ON true
    LEFT JOIN exit_totals ON true;

    -- Add the new/updated transaction to the totals
    IF TG_OP IN ('INSERT', 'UPDATE') THEN
        IF NEW.transaction_type IN ('OPEN', 'ADD') THEN
            total_cost := total_cost + (NEW.net_cost * CAST(NEW.size AS DECIMAL));
            total_size := total_size + CAST(NEW.size AS DECIMAL);
        ELSIF NEW.transaction_type IN ('TRIM', 'CLOSE') THEN
            total_exit_cost := total_exit_cost + (NEW.net_cost * CAST(NEW.size AS DECIMAL));
            total_exit_size := total_exit_size + CAST(NEW.size AS DECIMAL);
        END IF;
    END IF;

    -- Calculate averages and P/L
    IF total_size > 0 THEN
        avg_entry_cost := total_cost / total_size;
    END IF;

    IF total_exit_size > 0 THEN
        avg_exit_cost := total_exit_cost / total_exit_size;
        -- For options strategies, P/L is (exit cost - entry cost) for the exited portion
        total_pl := total_exit_cost - (avg_entry_cost * total_exit_size);
    END IF;

    -- Update the strategy
    UPDATE options_strategy_trades
    SET
        average_net_cost = COALESCE(avg_entry_cost, average_net_cost),
        average_exit_cost = COALESCE(avg_exit_cost, average_exit_cost),
        current_size = CAST(total_size - total_exit_size AS TEXT),
        profit_loss = COALESCE(total_pl, profit_loss),
        status = CASE
            WHEN total_size - total_exit_size <= 0 THEN 'CLOSED'
            ELSE 'OPEN'
        END,
        closed_at = CASE
            WHEN total_size - total_exit_size <= 0 THEN CURRENT_TIMESTAMP
            ELSE NULL
        END,
        win_loss = CASE
            WHEN total_size - total_exit_size <= 0 THEN
                CASE
                    WHEN COALESCE(total_pl, 0) > 0 THEN 'WIN'
                    WHEN COALESCE(total_pl, 0) < 0 THEN 'LOSS'
                    ELSE NULL
                END
            ELSE NULL
        END
    WHERE strategy_id = strategy_record.strategy_id;

    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    ELSE
        RETURN NEW;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for options strategy transactions
CREATE TRIGGER options_strategy_transaction_before_change
    BEFORE INSERT OR UPDATE OR DELETE ON options_strategy_transactions
    FOR EACH ROW
    EXECUTE FUNCTION update_options_strategy_before_transaction_change();

-- Function to update all options strategy trades
CREATE OR REPLACE FUNCTION update_all_options_strategies()
RETURNS void AS $$
DECLARE
    strategy_record options_strategy_trades%ROWTYPE;
    last_transaction options_strategy_transactions%ROWTYPE;
BEGIN
    -- Loop through each strategy
    FOR strategy_record IN SELECT * FROM options_strategy_trades
    LOOP
        RAISE NOTICE 'Processing strategy %', strategy_record.id;
        
        -- Find the most recent transaction for this strategy
        SELECT * INTO last_transaction
        FROM options_strategy_transactions
        WHERE strategy_id = strategy_record.strategy_id
        ORDER BY created_at DESC
        LIMIT 1;
        
        IF FOUND THEN
            -- Perform a no-op update on the last transaction to trigger recalculation
            UPDATE options_strategy_transactions
            SET created_at = created_at
            WHERE id = last_transaction.id;
            
            RAISE NOTICE 'Updated strategy % via transaction %', strategy_record.id, last_transaction.id;
        ELSE
            RAISE NOTICE 'No transactions found for strategy %', strategy_record.id;
        END IF;
    END LOOP;
    
    RAISE NOTICE 'All options strategies have been updated';
END;
$$ LANGUAGE plpgsql;

-- To run the update:
-- SELECT update_all_options_strategies();

-- Function to generate options strategy trade ID
CREATE OR REPLACE FUNCTION generate_options_strategy_trade_id() RETURNS TEXT AS $$
DECLARE
    new_id TEXT;
BEGIN
    -- Generate a random 6-character string using uppercase letters and numbers
    SELECT string_agg(substr('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', ceil(random() * 36)::integer, 1), '')
    INTO new_id
    FROM generate_series(1, 6);
    
    -- Add 'OST' prefix for Options Strategy Trade
    new_id := 'OST' || new_id;
    
    -- Check if ID already exists and regenerate if needed
    WHILE EXISTS (SELECT 1 FROM options_strategy_trades WHERE strategy_id = new_id) LOOP
        SELECT string_agg(substr('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', ceil(random() * 36)::integer, 1), '')
        INTO new_id
        FROM generate_series(1, 6);
        new_id := 'OST' || new_id;
    END LOOP;
    
    RETURN new_id;
END;
$$ LANGUAGE plpgsql;

-- Function to generate options strategy transaction ID
CREATE OR REPLACE FUNCTION generate_options_strategy_transaction_id() RETURNS TEXT AS $$
DECLARE
    new_id TEXT;
BEGIN
    -- Generate a random 6-character string using uppercase letters and numbers
    SELECT string_agg(substr('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', ceil(random() * 36)::integer, 1), '')
    INTO new_id
    FROM generate_series(1, 6);
    
    -- Add 'OSTX' prefix for Options Strategy Transaction
    new_id := 'OSTX' || new_id;
    
    -- Check if ID already exists and regenerate if needed
    WHILE EXISTS (SELECT 1 FROM options_strategy_transactions WHERE transaction_id = new_id) LOOP
        SELECT string_agg(substr('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', ceil(random() * 36)::integer, 1), '')
        INTO new_id
        FROM generate_series(1, 6);
        new_id := 'OSTX' || new_id;
    END LOOP;
    
    RETURN new_id;
END;
$$ LANGUAGE plpgsql;

-- Trigger for auto-generating strategy IDs
CREATE OR REPLACE FUNCTION set_options_strategy_trade_id()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.strategy_id IS NULL THEN
        NEW.strategy_id := generate_options_strategy_trade_id();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for auto-generating transaction IDs
CREATE OR REPLACE FUNCTION set_options_strategy_transaction_id()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.transaction_id IS NULL THEN
        NEW.transaction_id := generate_options_strategy_transaction_id();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create triggers for both tables
DROP TRIGGER IF EXISTS set_options_strategy_trade_id ON options_strategy_trades;
CREATE TRIGGER set_options_strategy_trade_id
    BEFORE INSERT ON options_strategy_trades
    FOR EACH ROW
    EXECUTE FUNCTION set_options_strategy_trade_id();

DROP TRIGGER IF EXISTS set_options_strategy_transaction_id ON options_strategy_transactions;
CREATE TRIGGER set_options_strategy_transaction_id
    BEFORE INSERT ON options_strategy_transactions
    FOR EACH ROW
    EXECUTE FUNCTION set_options_strategy_transaction_id();