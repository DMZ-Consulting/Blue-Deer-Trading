CREATE OR REPLACE FUNCTION update_monthly_strategy_pl() RETURNS TRIGGER AS $$
DECLARE
    strategy_record options_strategy_trades%ROWTYPE;
    transaction_month DATE;
    realized_pl DOUBLE PRECISION;
BEGIN
    -- Only process TRIM and CLOSE transactions
    IF UPPER(NEW.transaction_type) NOT IN ('TRIM', 'CLOSE') THEN
        RETURN NEW;
    END IF;

    -- Get the associated strategy record
    SELECT ost.* 
    INTO strategy_record
    FROM options_strategy_trades ost
    WHERE ost.strategy_id = NEW.strategy_id;

    -- Get the configuration ID for this strategy
    SELECT c.id INTO strategy_record.configuration_id
    FROM trade_configurations c
    WHERE c.id = strategy_record.configuration_id;

    -- Calculate the first day of the month for the transaction
    transaction_month := DATE_TRUNC('month', NEW.created_at::DATE);

    -- Calculate P/L for this strategy transaction
    realized_pl := COALESCE(calculate_strategy_realized_pl_for_transaction(strategy_record, NEW), 0);

    -- Insert or update monthly P/L record
    INSERT INTO monthly_pl (configuration_id, month, regular_trades_pl, strategy_trades_pl)
    VALUES (
        strategy_record.configuration_id, 
        transaction_month,
        0,  -- Regular trades P/L handled by separate function
        realized_pl
    )
    ON CONFLICT (configuration_id, month)
    DO UPDATE SET 
        strategy_trades_pl = COALESCE((
            -- Sum of all realized P/L from TRIM and CLOSE strategy transactions in this month
            SELECT SUM(
                COALESCE(calculate_strategy_realized_pl_for_transaction(ost, tx), 0)
            )
            FROM options_strategy_trades ost
            JOIN options_strategy_transactions tx ON ost.strategy_id = tx.strategy_id
            WHERE ost.configuration_id = strategy_record.configuration_id
            AND DATE_TRUNC('month', tx.created_at) = transaction_month
            AND UPPER(tx.transaction_type) IN ('TRIM', 'CLOSE')
        ), 0),
        updated_at = CURRENT_TIMESTAMP;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for options strategy transactions
CREATE TRIGGER update_monthly_strategy_pl_trigger
    AFTER INSERT OR UPDATE
    ON options_strategy_transactions
    FOR EACH ROW
    EXECUTE FUNCTION update_monthly_strategy_pl();

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
            trade_record.is_option,
            trade_record.symbol,
            realized_pl
        );
    END IF;
    
    RETURN 0;
END;
$$ LANGUAGE plpgsql;


-- Function to calculate realized P/L for a specific options strategy and transaction
CREATE OR REPLACE FUNCTION calculate_strategy_realized_pl_for_transaction(
    strategy_record options_strategy_trades,
    transaction_record options_strategy_transactions
) RETURNS DOUBLE PRECISION AS $$
DECLARE
    realized_pl DOUBLE PRECISION;
BEGIN
    -- For TRIM and CLOSE transactions, calculate the realized P/L
    IF UPPER(transaction_record.transaction_type) IN ('TRIM', 'CLOSE') THEN
        -- Calculate P/L: (exit price - average entry price) * size
        realized_pl := (transaction_record.amount - strategy_record.average_price) * 
                      CAST(transaction_record.size AS FLOAT);
        
        -- Apply the appropriate multiplier
        RETURN calculate_pl_with_multiplier(
            TRUE, 
            strategy_record.underlying_symbol,
            realized_pl
        );
    END IF;
    
    RETURN 0;
END;


-- Function to calculate realized P/L for a specific trade and transaction
CREATE OR REPLACE FUNCTION calculate_pl_with_multiplier(
    is_option BOOLEAN,
    symbol TEXT,
    realized_pl DOUBLE PRECISION
) RETURNS DOUBLE PRECISION AS $$
DECLARE
    multiplier DOUBLE PRECISION;
BEGIN
    -- Here is where the multiplier math is applied
    -- For example if the trade is an options strategy, the multiplier is 100
    -- If the trade is a regular trade, the multiplier is 10
    -- If the trade symbol is ES the multiplier is 5

    -- Get the multiplier for the trade type and symbol
    SELECT multiplier INTO multiplier
    FROM trade_multipliers
    WHERE is_option = is_option
    AND symbol = symbol;

    -- If the multiplier is not found try the trade_type with NULL Symbol
    IF multiplier IS NULL THEN
        SELECT multiplier INTO multiplier
        FROM trade_multipliers
        WHERE is_option = is_option
        AND symbol IS NULL;
    END IF;

    -- Return the realized P/L multiplied by the multiplier
    RETURN realized_pl * multiplier;
END;
$$ LANGUAGE plpgsql;


CREATE TABLE IF NOT EXISTS trade_multipliers (
    is_option BOOLEAN,
    symbol TEXT,
    multiplier DOUBLE PRECISION
);

INSERT INTO trade_multipliers (is_option, symbol, multiplier) VALUES
(FALSE, 'ES', 5),
(FALSE, NULL , 100),
(TRUE, NULL, 100);


