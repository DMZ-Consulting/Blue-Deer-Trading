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