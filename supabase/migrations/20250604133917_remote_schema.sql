

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;


CREATE EXTENSION IF NOT EXISTS "pg_cron" WITH SCHEMA "pg_catalog";






CREATE EXTENSION IF NOT EXISTS "pg_net" WITH SCHEMA "extensions";






CREATE EXTENSION IF NOT EXISTS "pgsodium";






COMMENT ON SCHEMA "public" IS 'standard public schema';



CREATE EXTENSION IF NOT EXISTS "pg_graphql" WITH SCHEMA "graphql";






CREATE EXTENSION IF NOT EXISTS "pg_stat_statements" WITH SCHEMA "extensions";






CREATE EXTENSION IF NOT EXISTS "pgcrypto" WITH SCHEMA "extensions";






CREATE EXTENSION IF NOT EXISTS "pgjwt" WITH SCHEMA "extensions";






CREATE EXTENSION IF NOT EXISTS "supabase_vault" WITH SCHEMA "vault";






CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA "extensions";






CREATE OR REPLACE FUNCTION "public"."backfill_monthly_pl"() RETURNS "void"
    LANGUAGE "plpgsql"
    AS $$
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
$$;


ALTER FUNCTION "public"."backfill_monthly_pl"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."calculate_pl_with_multiplier"("trade_type" "text", "symbol" "text", "base_pl" double precision) RETURNS double precision
    LANGUAGE "plpgsql"
    AS $$
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
$$;


ALTER FUNCTION "public"."calculate_pl_with_multiplier"("trade_type" "text", "symbol" "text", "base_pl" double precision) OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."calculate_pl_with_multiplier"("trade_type" "text", "symbol" "text", "base_pl" numeric) RETURNS numeric
    LANGUAGE "plpgsql"
    AS $$
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
$$;


ALTER FUNCTION "public"."calculate_pl_with_multiplier"("trade_type" "text", "symbol" "text", "base_pl" numeric) OWNER TO "postgres";

SET default_tablespace = '';

SET default_table_access_method = "heap";


CREATE TABLE IF NOT EXISTS "public"."trades" (
    "trade_id" character varying NOT NULL,
    "symbol" character varying NOT NULL,
    "trade_type" character varying NOT NULL,
    "status" character varying NOT NULL,
    "entry_price" double precision NOT NULL,
    "average_price" double precision,
    "current_size" character varying,
    "size" character varying NOT NULL,
    "created_at" timestamp with time zone NOT NULL,
    "closed_at" timestamp with time zone,
    "exit_price" double precision,
    "average_exit_price" double precision,
    "profit_loss" double precision,
    "risk_reward_ratio" double precision,
    "win_loss" character varying,
    "configuration_id" integer,
    "is_contract" boolean DEFAULT false,
    "is_day_trade" boolean DEFAULT false,
    "strike" double precision,
    "expiration_date" timestamp with time zone,
    "option_type" character varying
);


ALTER TABLE "public"."trades" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."transactions" (
    "id" character varying NOT NULL,
    "trade_id" character varying,
    "transaction_type" character varying,
    "amount" double precision,
    "size" character varying,
    "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE "public"."transactions" OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."calculate_realized_pl_for_transaction"("trade_record" "public"."trades", "transaction_record" "public"."transactions") RETURNS double precision
    LANGUAGE "plpgsql"
    AS $$
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
$$;


ALTER FUNCTION "public"."calculate_realized_pl_for_transaction"("trade_record" "public"."trades", "transaction_record" "public"."transactions") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."check_expired_trades_trigger"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
BEGIN
    PERFORM handle_expired_trades();
    RETURN NULL;
END;
$$;


ALTER FUNCTION "public"."check_expired_trades_trigger"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."cleanup_and_update_trades"() RETURNS "void"
    LANGUAGE "plpgsql"
    AS $$
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
$$;


ALTER FUNCTION "public"."cleanup_and_update_trades"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."close_expired_trades"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $_$
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
$_$;


ALTER FUNCTION "public"."close_expired_trades"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."delete_all_transactions"() RETURNS "void"
    LANGUAGE "plpgsql" SECURITY DEFINER
    AS $$
begin
    -- Disable the trigger temporarily
    alter table transactions disable trigger all;
    
    -- Delete all transactions
    delete from transactions;
    
    -- Re-enable the trigger
    alter table transactions enable trigger all;
end;
$$;


ALTER FUNCTION "public"."delete_all_transactions"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."generate_options_strategy_id"() RETURNS "text"
    LANGUAGE "plpgsql"
    AS $$
DECLARE
    new_id TEXT;
BEGIN
    -- Generate a random 6-character string using uppercase letters and numbers
    SELECT string_agg(substr('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', ceil(random() * 36)::integer, 1), '')
    INTO new_id
    FROM generate_series(1, 6);
    
    -- Add 'OS' prefix for Options Strategy
    new_id := 'OS' || new_id;
    
    -- Check if ID already exists and regenerate if needed
    WHILE EXISTS (SELECT 1 FROM options_strategy_trades WHERE strategy_id = new_id) LOOP
        SELECT string_agg(substr('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', ceil(random() * 36)::integer, 1), '')
        INTO new_id
        FROM generate_series(1, 6);
        new_id := 'OS' || new_id;
    END LOOP;
    
    RETURN new_id;
END;
$$;


ALTER FUNCTION "public"."generate_options_strategy_id"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."generate_options_strategy_trade_id"() RETURNS "text"
    LANGUAGE "plpgsql"
    AS $$
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
$$;


ALTER FUNCTION "public"."generate_options_strategy_trade_id"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."generate_options_strategy_transaction_id"() RETURNS "text"
    LANGUAGE "plpgsql"
    AS $$
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
$$;


ALTER FUNCTION "public"."generate_options_strategy_transaction_id"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."handle_expired_trades"() RETURNS "void"
    LANGUAGE "plpgsql"
    AS $_$
DECLARE
    expired_trade RECORD;
    new_transaction_id VARCHAR;
    alphanumeric CONSTANT VARCHAR := 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
BEGIN
    -- Find trades that have just expired (expiration_date is in the past and status is still OPEN)
    FOR expired_trade IN
        SELECT trade_id, current_size
        FROM trades
        WHERE expiration_date IS NOT NULL
        AND expiration_date < CURRENT_TIMESTAMP
        AND status = 'OPEN'
    LOOP
        -- Generate a new transaction ID (starting with 'T' followed by 7 random alphanumeric characters)
        new_transaction_id := 'T' || 
            substring(alphanumeric from (1 + floor(random() * 36))::int for 1) ||
            substring(alphanumeric from (1 + floor(random() * 36))::int for 1) ||
            substring(alphanumeric from (1 + floor(random() * 36))::int for 1) ||
            substring(alphanumeric from (1 + floor(random() * 36))::int for 1) ||
            substring(alphanumeric from (1 + floor(random() * 36))::int for 1) ||
            substring(alphanumeric from (1 + floor(random() * 36))::int for 1) ||
            substring(alphanumeric from (1 + floor(random() * 36))::int for 1);
        
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
END;
$_$;


ALTER FUNCTION "public"."handle_expired_trades"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."set_options_strategy_ids"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
BEGIN
    -- For trades table
    IF TG_TABLE_NAME = 'options_strategy_trades' AND NEW.strategy_id IS NULL THEN
        NEW.strategy_id := generate_options_strategy_id();
    END IF;
    
    -- For transactions table
    IF TG_TABLE_NAME = 'options_strategy_transactions' AND NEW.transaction_id IS NULL THEN
        NEW.transaction_id := generate_options_strategy_id();
    END IF;
    
    RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."set_options_strategy_ids"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."set_options_strategy_trade_id"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
BEGIN
    IF NEW.strategy_id IS NULL THEN
        NEW.strategy_id := generate_options_strategy_trade_id();
    END IF;
    RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."set_options_strategy_trade_id"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."set_options_strategy_transaction_id"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
BEGIN
    IF NEW.transaction_id IS NULL THEN
        NEW.transaction_id := generate_options_strategy_transaction_id();
    END IF;
    RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."set_options_strategy_transaction_id"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."trigger_exit_expired_trades"() RETURNS "void"
    LANGUAGE "plpgsql" SECURITY DEFINER
    AS $$
DECLARE
    trade_record RECORD;
    edge_function_url TEXT := 'https://hsnppengoffvgtnifceo.supabase.co/functions/v1/trades'; -- !! IMPORTANT: Replace placeholders
    service_role_key TEXT := 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhzbnBwZW5nb2Zmdmd0bmlmY2VvIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzQ0NTA0NjYsImV4cCI6MjA1MDAyNjQ2Nn0.XtcQPD1uD-cqZMpRCRgDWjBh5gaZeZdcEI75G3pXPKc'; -- !! IMPORTANT: Replace placeholder (Keep this secure!)
    payload JSONB;
    request_id BIGINT;
BEGIN
    -- Find 'OPEN' trades where expiration_date is in the past
    -- Adjust 'OPEN' if your status value for open trades is different
    FOR trade_record IN
        SELECT trade_id
        FROM public.trades
        WHERE status = 'OPEN' -- Make sure 'OPEN' is the correct status value
          AND expiration_date IS NOT NULL
          AND expiration_date < NOW() -- NOW() gives the current transaction timestamp (when the cron runs)
    LOOP
        -- Construct the payload for your Edge Function
        -- !!! CRITICAL POINT: Your Edge Function requires a 'price'.
        -- This automated trigger based on expiration doesn't know the 'exit price'.
        -- You MUST modify your Edge Function ('exitTrade' case) to handle calls
        -- triggered by expiration. It might need to:
        --    a) Fetch the current market price itself.
        --    b) Use a default closing logic when no price is provided.
        --    c) Or accept a specific flag indicating expiration exit.
        -- For now, this payload only sends the trade_id and action.
        -- Adapt the payload AND your Edge Function accordingly.
        payload := jsonb_build_object(
            'action', 'exitTrade',
            'trade_id', trade_record.trade_id,
            'price', 0
            -- Potentially add another field like 'trigger_reason': 'expiration'
            -- DO NOT include 'price' here unless you have a way to determine it
        );

        -- Asynchronously call the Edge Function using pg_net
        -- This makes an HTTP POST request.
        SELECT net.http_post(
            url := edge_function_url,
            body := payload,
            headers := jsonb_build_object(
                'Content-Type', 'application/json',
                'Authorization', 'Bearer ' || service_role_key -- Use the Service Role Key for auth
            )
            -- timeout_milliseconds := 3000 -- Optional: set a timeout (default 5s)
        ) INTO request_id;

        -- Optional: Log that the function was called for this trade
        RAISE NOTICE 'Triggered exitTrade for trade_id % via Edge Function. Request ID: %', trade_record.trade_id, request_id;

        -- Add a small delay if you anticipate many calls hitting the function at once (optional)
        -- PERFORM pg_sleep(0.1); -- Sleep for 100 milliseconds

    END LOOP;
END;
$$;


ALTER FUNCTION "public"."trigger_exit_expired_trades"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."update_all_options_strategies"() RETURNS "void"
    LANGUAGE "plpgsql"
    AS $$
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
        WHERE strategy_id = strategy_record.id
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
$$;


ALTER FUNCTION "public"."update_all_options_strategies"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."update_monthly_pl"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
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
$$;


ALTER FUNCTION "public"."update_monthly_pl"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."update_monthly_pl_regular_trade"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
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
$$;


ALTER FUNCTION "public"."update_monthly_pl_regular_trade"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."update_monthly_pl_strategy_trade"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
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
$$;


ALTER FUNCTION "public"."update_monthly_pl_strategy_trade"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."update_monthly_pl_updated_at"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."update_monthly_pl_updated_at"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."update_monthly_strategy_pl"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
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
$$;


ALTER FUNCTION "public"."update_monthly_strategy_pl"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."update_options_strategy_before_transaction_change"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
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
$$;


ALTER FUNCTION "public"."update_options_strategy_before_transaction_change"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."update_trade_before_transaction_change"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
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
$$;


ALTER FUNCTION "public"."update_trade_before_transaction_change"() OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."bot_configurations" (
    "id" integer NOT NULL,
    "watchlist_channel_id" character varying,
    "ta_channel_id" character varying,
    "log_channel_id" "text"
);


ALTER TABLE "public"."bot_configurations" OWNER TO "postgres";


CREATE SEQUENCE IF NOT EXISTS "public"."bot_configurations_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE "public"."bot_configurations_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "public"."bot_configurations_id_seq" OWNED BY "public"."bot_configurations"."id";



CREATE TABLE IF NOT EXISTS "public"."conditional_role_grant_condition_roles" (
    "conditional_role_grant_id" integer NOT NULL,
    "role_id" integer NOT NULL
);


ALTER TABLE "public"."conditional_role_grant_condition_roles" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."conditional_role_grants" (
    "id" integer NOT NULL,
    "guild_id" character varying,
    "grant_role_id" character varying,
    "exclude_role_id" character varying
);


ALTER TABLE "public"."conditional_role_grants" OWNER TO "postgres";


CREATE SEQUENCE IF NOT EXISTS "public"."conditional_role_grants_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE "public"."conditional_role_grants_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "public"."conditional_role_grants_id_seq" OWNED BY "public"."conditional_role_grants"."id";



CREATE TABLE IF NOT EXISTS "public"."monthly_pl" (
    "id" integer NOT NULL,
    "configuration_id" integer,
    "month" "date" NOT NULL,
    "regular_trades_pl" numeric(15,2) DEFAULT 0 NOT NULL,
    "strategy_trades_pl" numeric(15,2) DEFAULT 0 NOT NULL,
    "total_pl" numeric(15,2) GENERATED ALWAYS AS (("regular_trades_pl" + "strategy_trades_pl")) STORED,
    "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    "updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE "public"."monthly_pl" OWNER TO "postgres";


CREATE SEQUENCE IF NOT EXISTS "public"."monthly_pl_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE "public"."monthly_pl_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "public"."monthly_pl_id_seq" OWNED BY "public"."monthly_pl"."id";



CREATE TABLE IF NOT EXISTS "public"."options_strategy_trades" (
    "strategy_id" "text" NOT NULL,
    "name" character varying,
    "underlying_symbol" character varying,
    "status" character varying,
    "created_at" timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    "closed_at" timestamp without time zone,
    "configuration_id" integer,
    "trade_group" character varying,
    "legs" "text" NOT NULL,
    "net_cost" double precision NOT NULL,
    "average_net_cost" double precision NOT NULL,
    "size" character varying NOT NULL,
    "current_size" character varying NOT NULL,
    "average_exit_cost" double precision,
    "win_loss" "text",
    "profit_loss" double precision
);


ALTER TABLE "public"."options_strategy_trades" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."options_strategy_transactions" (
    "transaction_type" character varying NOT NULL,
    "net_cost" double precision NOT NULL,
    "size" character varying NOT NULL,
    "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    "transaction_id" "text" DEFAULT "public"."generate_options_strategy_id"() NOT NULL,
    "strategy_id" "text"
);


ALTER TABLE "public"."options_strategy_transactions" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."role_requirement_roles" (
    "role_requirement_id" integer NOT NULL,
    "role_id" integer NOT NULL
);


ALTER TABLE "public"."role_requirement_roles" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."role_requirements" (
    "id" integer NOT NULL,
    "guild_id" character varying
);


ALTER TABLE "public"."role_requirements" OWNER TO "postgres";


CREATE SEQUENCE IF NOT EXISTS "public"."role_requirements_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE "public"."role_requirements_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "public"."role_requirements_id_seq" OWNED BY "public"."role_requirements"."id";



CREATE TABLE IF NOT EXISTS "public"."roles" (
    "id" integer NOT NULL,
    "role_id" character varying,
    "guild_id" character varying
);


ALTER TABLE "public"."roles" OWNER TO "postgres";


CREATE SEQUENCE IF NOT EXISTS "public"."roles_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE "public"."roles_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "public"."roles_id_seq" OWNED BY "public"."roles"."id";



CREATE TABLE IF NOT EXISTS "public"."trade_configurations" (
    "id" integer NOT NULL,
    "name" character varying,
    "channel_id" character varying,
    "role_id" character varying,
    "roadmap_channel_id" character varying,
    "update_channel_id" character varying,
    "portfolio_channel_id" character varying,
    "log_channel_id" character varying
);


ALTER TABLE "public"."trade_configurations" OWNER TO "postgres";


CREATE SEQUENCE IF NOT EXISTS "public"."trade_configurations_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE "public"."trade_configurations_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "public"."trade_configurations_id_seq" OWNED BY "public"."trade_configurations"."id";



CREATE TABLE IF NOT EXISTS "public"."verification_configs" (
    "id" integer NOT NULL,
    "message_id" character varying,
    "channel_id" character varying,
    "role_to_remove_id" character varying,
    "role_to_add_id" character varying,
    "log_channel_id" character varying
);


ALTER TABLE "public"."verification_configs" OWNER TO "postgres";


CREATE SEQUENCE IF NOT EXISTS "public"."verification_configs_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE "public"."verification_configs_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "public"."verification_configs_id_seq" OWNED BY "public"."verification_configs"."id";



CREATE TABLE IF NOT EXISTS "public"."verifications" (
    "id" integer NOT NULL,
    "user_id" character varying,
    "username" character varying,
    "configuration_id" integer,
    "timestamp" timestamp without time zone
);


ALTER TABLE "public"."verifications" OWNER TO "postgres";


CREATE SEQUENCE IF NOT EXISTS "public"."verifications_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE "public"."verifications_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "public"."verifications_id_seq" OWNED BY "public"."verifications"."id";



ALTER TABLE ONLY "public"."bot_configurations" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."bot_configurations_id_seq"'::"regclass");



ALTER TABLE ONLY "public"."conditional_role_grants" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."conditional_role_grants_id_seq"'::"regclass");



ALTER TABLE ONLY "public"."monthly_pl" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."monthly_pl_id_seq"'::"regclass");



ALTER TABLE ONLY "public"."role_requirements" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."role_requirements_id_seq"'::"regclass");



ALTER TABLE ONLY "public"."roles" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."roles_id_seq"'::"regclass");



ALTER TABLE ONLY "public"."trade_configurations" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."trade_configurations_id_seq"'::"regclass");



ALTER TABLE ONLY "public"."verification_configs" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."verification_configs_id_seq"'::"regclass");



ALTER TABLE ONLY "public"."verifications" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."verifications_id_seq"'::"regclass");



ALTER TABLE ONLY "public"."bot_configurations"
    ADD CONSTRAINT "bot_configurations_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."conditional_role_grant_condition_roles"
    ADD CONSTRAINT "conditional_role_grant_condition_roles_pkey" PRIMARY KEY ("conditional_role_grant_id", "role_id");



ALTER TABLE ONLY "public"."conditional_role_grants"
    ADD CONSTRAINT "conditional_role_grants_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."monthly_pl"
    ADD CONSTRAINT "monthly_pl_configuration_id_month_key" UNIQUE ("configuration_id", "month");



ALTER TABLE ONLY "public"."monthly_pl"
    ADD CONSTRAINT "monthly_pl_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."options_strategy_trades"
    ADD CONSTRAINT "options_strategy_trades_pkey" PRIMARY KEY ("strategy_id");



ALTER TABLE ONLY "public"."options_strategy_trades"
    ADD CONSTRAINT "options_strategy_trades_trade_id_key" UNIQUE ("strategy_id");



ALTER TABLE ONLY "public"."options_strategy_transactions"
    ADD CONSTRAINT "options_strategy_transactions_pkey" PRIMARY KEY ("transaction_id");



ALTER TABLE ONLY "public"."role_requirement_roles"
    ADD CONSTRAINT "role_requirement_roles_pkey" PRIMARY KEY ("role_requirement_id", "role_id");



ALTER TABLE ONLY "public"."role_requirements"
    ADD CONSTRAINT "role_requirements_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."roles"
    ADD CONSTRAINT "roles_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."roles"
    ADD CONSTRAINT "roles_role_id_guild_id_key" UNIQUE ("role_id", "guild_id");



ALTER TABLE ONLY "public"."trade_configurations"
    ADD CONSTRAINT "trade_configurations_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."trades"
    ADD CONSTRAINT "trades_pkey" PRIMARY KEY ("trade_id");



ALTER TABLE ONLY "public"."transactions"
    ADD CONSTRAINT "transactions_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."verification_configs"
    ADD CONSTRAINT "verification_configs_message_id_key" UNIQUE ("message_id");



ALTER TABLE ONLY "public"."verification_configs"
    ADD CONSTRAINT "verification_configs_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."verifications"
    ADD CONSTRAINT "verifications_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."verifications"
    ADD CONSTRAINT "verifications_user_id_key" UNIQUE ("user_id");



CREATE INDEX "idx_options_strategy_trades_underlying" ON "public"."options_strategy_trades" USING "btree" ("underlying_symbol");



CREATE INDEX "idx_trades_created_at" ON "public"."trades" USING "btree" ("created_at");



CREATE INDEX "idx_trades_status" ON "public"."trades" USING "btree" ("status");



CREATE INDEX "idx_trades_symbol" ON "public"."trades" USING "btree" ("symbol");



CREATE INDEX "idx_verifications_user_id" ON "public"."verifications" USING "btree" ("user_id");



CREATE OR REPLACE TRIGGER "options_strategy_transaction_before_change" BEFORE INSERT OR DELETE OR UPDATE ON "public"."options_strategy_transactions" FOR EACH ROW EXECUTE FUNCTION "public"."update_options_strategy_before_transaction_change"();



CREATE OR REPLACE TRIGGER "set_options_strategy_trade_id" BEFORE INSERT ON "public"."options_strategy_trades" FOR EACH ROW EXECUTE FUNCTION "public"."set_options_strategy_trade_id"();



CREATE OR REPLACE TRIGGER "set_options_strategy_transaction_id" BEFORE INSERT ON "public"."options_strategy_transactions" FOR EACH ROW EXECUTE FUNCTION "public"."set_options_strategy_transaction_id"();



CREATE OR REPLACE TRIGGER "transaction_before_delete" BEFORE DELETE ON "public"."transactions" FOR EACH ROW EXECUTE FUNCTION "public"."update_trade_before_transaction_change"();



CREATE OR REPLACE TRIGGER "transaction_before_insert_update" BEFORE INSERT OR UPDATE ON "public"."transactions" FOR EACH ROW EXECUTE FUNCTION "public"."update_trade_before_transaction_change"();



ALTER TABLE ONLY "public"."conditional_role_grant_condition_roles"
    ADD CONSTRAINT "conditional_role_grant_condition_conditional_role_grant_id_fkey" FOREIGN KEY ("conditional_role_grant_id") REFERENCES "public"."conditional_role_grants"("id");



ALTER TABLE ONLY "public"."conditional_role_grant_condition_roles"
    ADD CONSTRAINT "conditional_role_grant_condition_roles_role_id_fkey" FOREIGN KEY ("role_id") REFERENCES "public"."roles"("id");



ALTER TABLE ONLY "public"."monthly_pl"
    ADD CONSTRAINT "monthly_pl_configuration_id_fkey" FOREIGN KEY ("configuration_id") REFERENCES "public"."trade_configurations"("id");



ALTER TABLE ONLY "public"."options_strategy_trades"
    ADD CONSTRAINT "options_strategy_trades_configuration_id_fkey" FOREIGN KEY ("configuration_id") REFERENCES "public"."trade_configurations"("id");



ALTER TABLE ONLY "public"."options_strategy_transactions"
    ADD CONSTRAINT "options_strategy_transactions_strategy_id_fkey" FOREIGN KEY ("strategy_id") REFERENCES "public"."options_strategy_trades"("strategy_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."role_requirement_roles"
    ADD CONSTRAINT "role_requirement_roles_role_id_fkey" FOREIGN KEY ("role_id") REFERENCES "public"."roles"("id");



ALTER TABLE ONLY "public"."role_requirement_roles"
    ADD CONSTRAINT "role_requirement_roles_role_requirement_id_fkey" FOREIGN KEY ("role_requirement_id") REFERENCES "public"."role_requirements"("id");



ALTER TABLE ONLY "public"."trades"
    ADD CONSTRAINT "trades_configuration_id_fkey" FOREIGN KEY ("configuration_id") REFERENCES "public"."trade_configurations"("id");



ALTER TABLE ONLY "public"."transactions"
    ADD CONSTRAINT "transactions_trade_id_fkey" FOREIGN KEY ("trade_id") REFERENCES "public"."trades"("trade_id");



ALTER TABLE ONLY "public"."verifications"
    ADD CONSTRAINT "verifications_configuration_id_fkey" FOREIGN KEY ("configuration_id") REFERENCES "public"."verification_configs"("id");





ALTER PUBLICATION "supabase_realtime" OWNER TO "postgres";








GRANT USAGE ON SCHEMA "public" TO "postgres";
GRANT USAGE ON SCHEMA "public" TO "anon";
GRANT USAGE ON SCHEMA "public" TO "authenticated";
GRANT USAGE ON SCHEMA "public" TO "service_role";









































































































































































































GRANT ALL ON FUNCTION "public"."backfill_monthly_pl"() TO "anon";
GRANT ALL ON FUNCTION "public"."backfill_monthly_pl"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."backfill_monthly_pl"() TO "service_role";



GRANT ALL ON FUNCTION "public"."calculate_pl_with_multiplier"("trade_type" "text", "symbol" "text", "base_pl" double precision) TO "anon";
GRANT ALL ON FUNCTION "public"."calculate_pl_with_multiplier"("trade_type" "text", "symbol" "text", "base_pl" double precision) TO "authenticated";
GRANT ALL ON FUNCTION "public"."calculate_pl_with_multiplier"("trade_type" "text", "symbol" "text", "base_pl" double precision) TO "service_role";



GRANT ALL ON FUNCTION "public"."calculate_pl_with_multiplier"("trade_type" "text", "symbol" "text", "base_pl" numeric) TO "anon";
GRANT ALL ON FUNCTION "public"."calculate_pl_with_multiplier"("trade_type" "text", "symbol" "text", "base_pl" numeric) TO "authenticated";
GRANT ALL ON FUNCTION "public"."calculate_pl_with_multiplier"("trade_type" "text", "symbol" "text", "base_pl" numeric) TO "service_role";



GRANT ALL ON TABLE "public"."trades" TO "anon";
GRANT ALL ON TABLE "public"."trades" TO "authenticated";
GRANT ALL ON TABLE "public"."trades" TO "service_role";



GRANT ALL ON TABLE "public"."transactions" TO "anon";
GRANT ALL ON TABLE "public"."transactions" TO "authenticated";
GRANT ALL ON TABLE "public"."transactions" TO "service_role";



GRANT ALL ON FUNCTION "public"."calculate_realized_pl_for_transaction"("trade_record" "public"."trades", "transaction_record" "public"."transactions") TO "anon";
GRANT ALL ON FUNCTION "public"."calculate_realized_pl_for_transaction"("trade_record" "public"."trades", "transaction_record" "public"."transactions") TO "authenticated";
GRANT ALL ON FUNCTION "public"."calculate_realized_pl_for_transaction"("trade_record" "public"."trades", "transaction_record" "public"."transactions") TO "service_role";



GRANT ALL ON FUNCTION "public"."check_expired_trades_trigger"() TO "anon";
GRANT ALL ON FUNCTION "public"."check_expired_trades_trigger"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."check_expired_trades_trigger"() TO "service_role";



GRANT ALL ON FUNCTION "public"."cleanup_and_update_trades"() TO "anon";
GRANT ALL ON FUNCTION "public"."cleanup_and_update_trades"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."cleanup_and_update_trades"() TO "service_role";



GRANT ALL ON FUNCTION "public"."close_expired_trades"() TO "anon";
GRANT ALL ON FUNCTION "public"."close_expired_trades"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."close_expired_trades"() TO "service_role";



GRANT ALL ON FUNCTION "public"."delete_all_transactions"() TO "anon";
GRANT ALL ON FUNCTION "public"."delete_all_transactions"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."delete_all_transactions"() TO "service_role";



GRANT ALL ON FUNCTION "public"."generate_options_strategy_id"() TO "anon";
GRANT ALL ON FUNCTION "public"."generate_options_strategy_id"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."generate_options_strategy_id"() TO "service_role";



GRANT ALL ON FUNCTION "public"."generate_options_strategy_trade_id"() TO "anon";
GRANT ALL ON FUNCTION "public"."generate_options_strategy_trade_id"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."generate_options_strategy_trade_id"() TO "service_role";



GRANT ALL ON FUNCTION "public"."generate_options_strategy_transaction_id"() TO "anon";
GRANT ALL ON FUNCTION "public"."generate_options_strategy_transaction_id"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."generate_options_strategy_transaction_id"() TO "service_role";



GRANT ALL ON FUNCTION "public"."handle_expired_trades"() TO "anon";
GRANT ALL ON FUNCTION "public"."handle_expired_trades"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."handle_expired_trades"() TO "service_role";



GRANT ALL ON FUNCTION "public"."set_options_strategy_ids"() TO "anon";
GRANT ALL ON FUNCTION "public"."set_options_strategy_ids"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."set_options_strategy_ids"() TO "service_role";



GRANT ALL ON FUNCTION "public"."set_options_strategy_trade_id"() TO "anon";
GRANT ALL ON FUNCTION "public"."set_options_strategy_trade_id"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."set_options_strategy_trade_id"() TO "service_role";



GRANT ALL ON FUNCTION "public"."set_options_strategy_transaction_id"() TO "anon";
GRANT ALL ON FUNCTION "public"."set_options_strategy_transaction_id"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."set_options_strategy_transaction_id"() TO "service_role";



GRANT ALL ON FUNCTION "public"."trigger_exit_expired_trades"() TO "anon";
GRANT ALL ON FUNCTION "public"."trigger_exit_expired_trades"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."trigger_exit_expired_trades"() TO "service_role";



GRANT ALL ON FUNCTION "public"."update_all_options_strategies"() TO "anon";
GRANT ALL ON FUNCTION "public"."update_all_options_strategies"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."update_all_options_strategies"() TO "service_role";



GRANT ALL ON FUNCTION "public"."update_monthly_pl"() TO "anon";
GRANT ALL ON FUNCTION "public"."update_monthly_pl"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."update_monthly_pl"() TO "service_role";



GRANT ALL ON FUNCTION "public"."update_monthly_pl_regular_trade"() TO "anon";
GRANT ALL ON FUNCTION "public"."update_monthly_pl_regular_trade"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."update_monthly_pl_regular_trade"() TO "service_role";



GRANT ALL ON FUNCTION "public"."update_monthly_pl_strategy_trade"() TO "anon";
GRANT ALL ON FUNCTION "public"."update_monthly_pl_strategy_trade"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."update_monthly_pl_strategy_trade"() TO "service_role";



GRANT ALL ON FUNCTION "public"."update_monthly_pl_updated_at"() TO "anon";
GRANT ALL ON FUNCTION "public"."update_monthly_pl_updated_at"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."update_monthly_pl_updated_at"() TO "service_role";



GRANT ALL ON FUNCTION "public"."update_monthly_strategy_pl"() TO "anon";
GRANT ALL ON FUNCTION "public"."update_monthly_strategy_pl"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."update_monthly_strategy_pl"() TO "service_role";



GRANT ALL ON FUNCTION "public"."update_options_strategy_before_transaction_change"() TO "anon";
GRANT ALL ON FUNCTION "public"."update_options_strategy_before_transaction_change"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."update_options_strategy_before_transaction_change"() TO "service_role";



GRANT ALL ON FUNCTION "public"."update_trade_before_transaction_change"() TO "anon";
GRANT ALL ON FUNCTION "public"."update_trade_before_transaction_change"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."update_trade_before_transaction_change"() TO "service_role";
























GRANT ALL ON TABLE "public"."bot_configurations" TO "anon";
GRANT ALL ON TABLE "public"."bot_configurations" TO "authenticated";
GRANT ALL ON TABLE "public"."bot_configurations" TO "service_role";



GRANT ALL ON SEQUENCE "public"."bot_configurations_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."bot_configurations_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."bot_configurations_id_seq" TO "service_role";



GRANT ALL ON TABLE "public"."conditional_role_grant_condition_roles" TO "anon";
GRANT ALL ON TABLE "public"."conditional_role_grant_condition_roles" TO "authenticated";
GRANT ALL ON TABLE "public"."conditional_role_grant_condition_roles" TO "service_role";



GRANT ALL ON TABLE "public"."conditional_role_grants" TO "anon";
GRANT ALL ON TABLE "public"."conditional_role_grants" TO "authenticated";
GRANT ALL ON TABLE "public"."conditional_role_grants" TO "service_role";



GRANT ALL ON SEQUENCE "public"."conditional_role_grants_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."conditional_role_grants_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."conditional_role_grants_id_seq" TO "service_role";



GRANT ALL ON TABLE "public"."monthly_pl" TO "anon";
GRANT ALL ON TABLE "public"."monthly_pl" TO "authenticated";
GRANT ALL ON TABLE "public"."monthly_pl" TO "service_role";



GRANT ALL ON SEQUENCE "public"."monthly_pl_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."monthly_pl_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."monthly_pl_id_seq" TO "service_role";



GRANT ALL ON TABLE "public"."options_strategy_trades" TO "anon";
GRANT ALL ON TABLE "public"."options_strategy_trades" TO "authenticated";
GRANT ALL ON TABLE "public"."options_strategy_trades" TO "service_role";



GRANT ALL ON TABLE "public"."options_strategy_transactions" TO "anon";
GRANT ALL ON TABLE "public"."options_strategy_transactions" TO "authenticated";
GRANT ALL ON TABLE "public"."options_strategy_transactions" TO "service_role";



GRANT ALL ON TABLE "public"."role_requirement_roles" TO "anon";
GRANT ALL ON TABLE "public"."role_requirement_roles" TO "authenticated";
GRANT ALL ON TABLE "public"."role_requirement_roles" TO "service_role";



GRANT ALL ON TABLE "public"."role_requirements" TO "anon";
GRANT ALL ON TABLE "public"."role_requirements" TO "authenticated";
GRANT ALL ON TABLE "public"."role_requirements" TO "service_role";



GRANT ALL ON SEQUENCE "public"."role_requirements_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."role_requirements_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."role_requirements_id_seq" TO "service_role";



GRANT ALL ON TABLE "public"."roles" TO "anon";
GRANT ALL ON TABLE "public"."roles" TO "authenticated";
GRANT ALL ON TABLE "public"."roles" TO "service_role";



GRANT ALL ON SEQUENCE "public"."roles_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."roles_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."roles_id_seq" TO "service_role";



GRANT ALL ON TABLE "public"."trade_configurations" TO "anon";
GRANT ALL ON TABLE "public"."trade_configurations" TO "authenticated";
GRANT ALL ON TABLE "public"."trade_configurations" TO "service_role";



GRANT ALL ON SEQUENCE "public"."trade_configurations_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."trade_configurations_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."trade_configurations_id_seq" TO "service_role";



GRANT ALL ON TABLE "public"."verification_configs" TO "anon";
GRANT ALL ON TABLE "public"."verification_configs" TO "authenticated";
GRANT ALL ON TABLE "public"."verification_configs" TO "service_role";



GRANT ALL ON SEQUENCE "public"."verification_configs_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."verification_configs_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."verification_configs_id_seq" TO "service_role";



GRANT ALL ON TABLE "public"."verifications" TO "anon";
GRANT ALL ON TABLE "public"."verifications" TO "authenticated";
GRANT ALL ON TABLE "public"."verifications" TO "service_role";



GRANT ALL ON SEQUENCE "public"."verifications_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."verifications_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."verifications_id_seq" TO "service_role";



ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES  TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES  TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES  TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES  TO "service_role";






ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS  TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS  TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS  TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS  TO "service_role";






ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES  TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES  TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES  TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES  TO "service_role";






























RESET ALL;
