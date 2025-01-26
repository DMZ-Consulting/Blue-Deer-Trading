-- Options Strategy Trades CRUD Operations

-- Create new options strategy trade
CREATE OR REPLACE FUNCTION create_options_strategy_trade(
    p_user_id TEXT,
    p_ticker TEXT,
    p_strategy_type TEXT,
    p_start_date TIMESTAMP WITH TIME ZONE DEFAULT NULL,
    p_notes TEXT DEFAULT NULL
) RETURNS TEXT AS $$
DECLARE
    v_strategy_id TEXT;
BEGIN
    INSERT INTO options_strategy_trades (
        user_id,
        ticker,
        strategy_type,
        start_date,
        notes
    ) VALUES (
        p_user_id,
        p_ticker,
        p_strategy_type,
        p_start_date,
        p_notes
    ) RETURNING strategy_id INTO v_strategy_id;
    
    RETURN v_strategy_id;
END;
$$ LANGUAGE plpgsql;

-- Get options strategy trade by ID
CREATE OR REPLACE FUNCTION get_options_strategy_trade(p_strategy_id TEXT)
RETURNS TABLE (
    strategy_id TEXT,
    user_id TEXT,
    ticker TEXT,
    strategy_type TEXT,
    status trade_status,
    start_date TIMESTAMP WITH TIME ZONE,
    end_date TIMESTAMP WITH TIME ZONE,
    profit_loss DECIMAL,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    SELECT *
    FROM options_strategy_trades
    WHERE strategy_id = p_strategy_id;
END;
$$ LANGUAGE plpgsql;

-- Update options strategy trade
CREATE OR REPLACE FUNCTION update_options_strategy_trade(
    p_strategy_id TEXT,
    p_status trade_status DEFAULT NULL,
    p_end_date TIMESTAMP WITH TIME ZONE DEFAULT NULL,
    p_profit_loss DECIMAL DEFAULT NULL,
    p_notes TEXT DEFAULT NULL
) RETURNS BOOLEAN AS $$
BEGIN
    UPDATE options_strategy_trades
    SET
        status = COALESCE(p_status, status),
        end_date = COALESCE(p_end_date, end_date),
        profit_loss = COALESCE(p_profit_loss, profit_loss),
        notes = COALESCE(p_notes, notes)
    WHERE strategy_id = p_strategy_id;
    
    RETURN FOUND;
END;
$$ LANGUAGE plpgsql;

-- Delete options strategy trade
CREATE OR REPLACE FUNCTION delete_options_strategy_trade(p_strategy_id TEXT)
RETURNS BOOLEAN AS $$
BEGIN
    DELETE FROM options_strategy_trades
    WHERE strategy_id = p_strategy_id;
    
    RETURN FOUND;
END;
$$ LANGUAGE plpgsql;

-- Options Strategy Transactions CRUD Operations

-- Create new options strategy transaction
CREATE OR REPLACE FUNCTION create_options_strategy_transaction(
    p_strategy_id TEXT,
    p_transaction_type transaction_type,
    p_transaction_date TIMESTAMP WITH TIME ZONE,
    p_strike_price DECIMAL,
    p_expiration_date DATE,
    p_premium DECIMAL,
    p_contracts INTEGER,
    p_option_type TEXT,
    p_side TEXT,
    p_notes TEXT DEFAULT NULL
) RETURNS TEXT AS $$
DECLARE
    v_transaction_id TEXT;
BEGIN
    INSERT INTO options_strategy_transactions (
        strategy_id,
        transaction_type,
        transaction_date,
        strike_price,
        expiration_date,
        premium,
        contracts,
        option_type,
        side,
        notes
    ) VALUES (
        p_strategy_id,
        p_transaction_type,
        p_transaction_date,
        p_strike_price,
        p_expiration_date,
        p_premium,
        p_contracts,
        p_option_type,
        p_side,
        p_notes
    ) RETURNING transaction_id INTO v_transaction_id;
    
    RETURN v_transaction_id;
END;
$$ LANGUAGE plpgsql;

-- Get options strategy transaction by ID
CREATE OR REPLACE FUNCTION get_options_strategy_transaction(p_transaction_id TEXT)
RETURNS TABLE (
    transaction_id TEXT,
    strategy_id TEXT,
    transaction_type transaction_type,
    transaction_date TIMESTAMP WITH TIME ZONE,
    strike_price DECIMAL,
    expiration_date DATE,
    premium DECIMAL,
    contracts INTEGER,
    option_type TEXT,
    side TEXT,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    SELECT *
    FROM options_strategy_transactions
    WHERE transaction_id = p_transaction_id;
END;
$$ LANGUAGE plpgsql;

-- Get all transactions for a strategy
CREATE OR REPLACE FUNCTION get_strategy_transactions(p_strategy_id TEXT)
RETURNS TABLE (
    transaction_id TEXT,
    strategy_id TEXT,
    transaction_type transaction_type,
    transaction_date TIMESTAMP WITH TIME ZONE,
    strike_price DECIMAL,
    expiration_date DATE,
    premium DECIMAL,
    contracts INTEGER,
    option_type TEXT,
    side TEXT,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    SELECT *
    FROM options_strategy_transactions
    WHERE strategy_id = p_strategy_id
    ORDER BY transaction_date;
END;
$$ LANGUAGE plpgsql;

-- Update options strategy transaction
CREATE OR REPLACE FUNCTION update_options_strategy_transaction(
    p_transaction_id TEXT,
    p_transaction_date TIMESTAMP WITH TIME ZONE DEFAULT NULL,
    p_strike_price DECIMAL DEFAULT NULL,
    p_expiration_date DATE DEFAULT NULL,
    p_premium DECIMAL DEFAULT NULL,
    p_contracts INTEGER DEFAULT NULL,
    p_notes TEXT DEFAULT NULL
) RETURNS BOOLEAN AS $$
BEGIN
    UPDATE options_strategy_transactions
    SET
        transaction_date = COALESCE(p_transaction_date, transaction_date),
        strike_price = COALESCE(p_strike_price, strike_price),
        expiration_date = COALESCE(p_expiration_date, expiration_date),
        premium = COALESCE(p_premium, premium),
        contracts = COALESCE(p_contracts, contracts),
        notes = COALESCE(p_notes, notes)
    WHERE transaction_id = p_transaction_id;
    
    RETURN FOUND;
END;
$$ LANGUAGE plpgsql;

-- Delete options strategy transaction
CREATE OR REPLACE FUNCTION delete_options_strategy_transaction(p_transaction_id TEXT)
RETURNS BOOLEAN AS $$
BEGIN
    DELETE FROM options_strategy_transactions
    WHERE transaction_id = p_transaction_id;
    
    RETURN FOUND;
END;
$$ LANGUAGE plpgsql; 