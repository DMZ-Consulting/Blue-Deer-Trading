-- Function to update monthly P/L for regular trades
CREATE OR REPLACE FUNCTION update_monthly_pl_regular_trade()
RETURNS TRIGGER AS $$
DECLARE
    trade_month DATE;
    trade_config_id BIGINT;
    trade_pl DECIMAL(15,2);
    multiplier INTEGER;
BEGIN
    -- Get the trade details
    SELECT 
        DATE_TRUNC('month', NEW.created_at)::DATE,
        t.configuration_id,
        t.profit_loss,
        CASE 
            WHEN t.symbol = 'ES' THEN 5
            ELSE 100
        END
    INTO 
        trade_month,
        trade_config_id,
        trade_pl,
        multiplier
    FROM trades t
    WHERE t.trade_id = NEW.trade_id;

    -- Only process CLOSE or TRIM transactions
    IF NEW.transaction_type IN ('CLOSE', 'TRIM') THEN
        -- Calculate P/L for this transaction
        IF trade_pl IS NOT NULL THEN
            -- Insert or update monthly P/L record
            INSERT INTO monthly_pl (
                month,
                configuration_id,
                regular_trades_pl
            )
            VALUES (
                trade_month,
                trade_config_id,
                trade_pl * multiplier
            )
            ON CONFLICT (month, configuration_id)
            DO UPDATE SET
                regular_trades_pl = monthly_pl.regular_trades_pl + EXCLUDED.regular_trades_pl;
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Function to update monthly P/L for strategy trades
CREATE OR REPLACE FUNCTION update_monthly_pl_strategy_trade()
RETURNS TRIGGER AS $$
DECLARE
    trade_month DATE;
    trade_config_id BIGINT;
    trade_pl DECIMAL(15,2);
BEGIN
    -- Get the strategy trade details
    SELECT 
        DATE_TRUNC('month', NEW.created_at)::DATE,
        s.configuration_id,
        s.profit_loss
    INTO 
        trade_month,
        trade_config_id,
        trade_pl
    FROM options_strategy_trades s
    WHERE s.id = NEW.strategy_id;

    -- Only process CLOSE or TRIM transactions
    IF NEW.transaction_type IN ('CLOSE', 'TRIM') THEN
        -- Calculate P/L for this transaction
        IF trade_pl IS NOT NULL THEN
            -- Insert or update monthly P/L record
            INSERT INTO monthly_pl (
                month,
                configuration_id,
                strategy_trades_pl
            )
            VALUES (
                trade_month,
                trade_config_id,
                trade_pl
            )
            ON CONFLICT (month, configuration_id)
            DO UPDATE SET
                strategy_trades_pl = monthly_pl.strategy_trades_pl + EXCLUDED.strategy_trades_pl;
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create triggers for regular trades
DROP TRIGGER IF EXISTS update_monthly_pl_regular_trade ON transactions;
CREATE TRIGGER update_monthly_pl_regular_trade
    AFTER INSERT ON transactions
    FOR EACH ROW
    EXECUTE FUNCTION update_monthly_pl_regular_trade();

-- Create triggers for strategy trades
DROP TRIGGER IF EXISTS update_monthly_pl_strategy_trade ON options_strategy_transactions;
CREATE TRIGGER update_monthly_pl_strategy_trade
    AFTER INSERT ON options_strategy_transactions
    FOR EACH ROW
    EXECUTE FUNCTION update_monthly_pl_strategy_trade();

-- Function to backfill historical monthly P/L data
CREATE OR REPLACE FUNCTION backfill_monthly_pl()
RETURNS void AS $$
BEGIN
    -- Clear existing data
    DELETE FROM monthly_pl;

    -- Insert regular trades P/L
    INSERT INTO monthly_pl (
        month,
        configuration_id,
        regular_trades_pl
    )
    SELECT 
        DATE_TRUNC('month', t.closed_at)::DATE as month,
        t.configuration_id,
        SUM(
            CASE 
                WHEN t.symbol = 'ES' THEN t.profit_loss * 5
                ELSE t.profit_loss * 100
            END
        ) as total_pl
    FROM trades t
    WHERE t.status = 'closed'
        AND t.profit_loss IS NOT NULL
        AND t.configuration_id IS NOT NULL
    GROUP BY 
        DATE_TRUNC('month', t.closed_at)::DATE,
        t.configuration_id;

    -- Insert strategy trades P/L
    WITH strategy_transactions AS (
        SELECT 
            s.id as strategy_id,
            s.configuration_id,
            s.closed_at,
            s.size,
            -- Calculate average entry cost
            SUM(CASE 
                WHEN t.transaction_type IN ('OPEN', 'ADD') 
                THEN t.net_cost * CAST(t.size AS DECIMAL)
            END) / NULLIF(SUM(CASE 
                WHEN t.transaction_type IN ('OPEN', 'ADD') 
                THEN CAST(t.size AS DECIMAL)
            END), 0) as avg_entry_cost,
            -- Calculate average exit cost
            SUM(CASE 
                WHEN t.transaction_type IN ('CLOSE', 'TRIM') 
                THEN t.net_cost * CAST(t.size AS DECIMAL)
            END) / NULLIF(SUM(CASE 
                WHEN t.transaction_type IN ('CLOSE', 'TRIM') 
                THEN CAST(t.size AS DECIMAL)
            END), 0) as avg_exit_cost
        FROM options_strategy_trades s
        JOIN options_strategy_transactions t ON t.strategy_id = s.id
        WHERE s.status = 'closed'
            AND s.configuration_id IS NOT NULL
        GROUP BY s.id, s.configuration_id, s.closed_at, s.size
    )
    INSERT INTO monthly_pl (
        month,
        configuration_id,
        strategy_trades_pl
    )
    SELECT 
        DATE_TRUNC('month', st.closed_at)::DATE as month,
        st.configuration_id,
        SUM((st.avg_exit_cost - st.avg_entry_cost) * CAST(st.size AS DECIMAL) * 100) as total_pl
    FROM strategy_transactions st
    WHERE st.avg_entry_cost IS NOT NULL 
        AND st.avg_exit_cost IS NOT NULL
    GROUP BY 
        DATE_TRUNC('month', st.closed_at)::DATE,
        st.configuration_id
    ON CONFLICT (month, configuration_id)
    DO UPDATE SET
        strategy_trades_pl = EXCLUDED.strategy_trades_pl;
END;
$$ LANGUAGE plpgsql; 