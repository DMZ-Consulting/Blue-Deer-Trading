--
-- PostgreSQL database dump
--

-- Dumped from database version 15.8
-- Dumped by pg_dump version 15.13 (Homebrew)

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

--
-- Name: auth; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA auth;


--
-- Name: pg_cron; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pg_cron WITH SCHEMA pg_catalog;


--
-- Name: EXTENSION pg_cron; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION pg_cron IS 'Job scheduler for PostgreSQL';


--
-- Name: extensions; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA extensions;


--
-- Name: graphql; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA graphql;


--
-- Name: graphql_public; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA graphql_public;


--
-- Name: pg_net; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pg_net WITH SCHEMA extensions;


--
-- Name: EXTENSION pg_net; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION pg_net IS 'Async HTTP';


--
-- Name: pgbouncer; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA pgbouncer;


--
-- Name: pgsodium; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA pgsodium;


--
-- Name: pgsodium; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pgsodium WITH SCHEMA pgsodium;


--
-- Name: EXTENSION pgsodium; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION pgsodium IS 'Pgsodium is a modern cryptography library for Postgres.';


--
-- Name: realtime; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA realtime;


--
-- Name: storage; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA storage;


--
-- Name: supabase_migrations; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA supabase_migrations;


--
-- Name: vault; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA vault;


--
-- Name: pg_graphql; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pg_graphql WITH SCHEMA graphql;


--
-- Name: EXTENSION pg_graphql; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION pg_graphql IS 'pg_graphql: GraphQL support';


--
-- Name: pg_stat_statements; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pg_stat_statements WITH SCHEMA extensions;


--
-- Name: EXTENSION pg_stat_statements; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION pg_stat_statements IS 'track planning and execution statistics of all SQL statements executed';


--
-- Name: pgcrypto; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA extensions;


--
-- Name: EXTENSION pgcrypto; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION pgcrypto IS 'cryptographic functions';


--
-- Name: pgjwt; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pgjwt WITH SCHEMA extensions;


--
-- Name: EXTENSION pgjwt; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION pgjwt IS 'JSON Web Token API for Postgresql';


--
-- Name: supabase_vault; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS supabase_vault WITH SCHEMA vault;


--
-- Name: EXTENSION supabase_vault; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION supabase_vault IS 'Supabase Vault Extension';


--
-- Name: uuid-ossp; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA extensions;


--
-- Name: EXTENSION "uuid-ossp"; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION "uuid-ossp" IS 'generate universally unique identifiers (UUIDs)';


--
-- Name: aal_level; Type: TYPE; Schema: auth; Owner: -
--

CREATE TYPE auth.aal_level AS ENUM (
    'aal1',
    'aal2',
    'aal3'
);


--
-- Name: code_challenge_method; Type: TYPE; Schema: auth; Owner: -
--

CREATE TYPE auth.code_challenge_method AS ENUM (
    's256',
    'plain'
);


--
-- Name: factor_status; Type: TYPE; Schema: auth; Owner: -
--

CREATE TYPE auth.factor_status AS ENUM (
    'unverified',
    'verified'
);


--
-- Name: factor_type; Type: TYPE; Schema: auth; Owner: -
--

CREATE TYPE auth.factor_type AS ENUM (
    'totp',
    'webauthn',
    'phone'
);


--
-- Name: one_time_token_type; Type: TYPE; Schema: auth; Owner: -
--

CREATE TYPE auth.one_time_token_type AS ENUM (
    'confirmation_token',
    'reauthentication_token',
    'recovery_token',
    'email_change_token_new',
    'email_change_token_current',
    'phone_change_token'
);


--
-- Name: action; Type: TYPE; Schema: realtime; Owner: -
--

CREATE TYPE realtime.action AS ENUM (
    'INSERT',
    'UPDATE',
    'DELETE',
    'TRUNCATE',
    'ERROR'
);


--
-- Name: equality_op; Type: TYPE; Schema: realtime; Owner: -
--

CREATE TYPE realtime.equality_op AS ENUM (
    'eq',
    'neq',
    'lt',
    'lte',
    'gt',
    'gte',
    'in'
);


--
-- Name: user_defined_filter; Type: TYPE; Schema: realtime; Owner: -
--

CREATE TYPE realtime.user_defined_filter AS (
	column_name text,
	op realtime.equality_op,
	value text
);


--
-- Name: wal_column; Type: TYPE; Schema: realtime; Owner: -
--

CREATE TYPE realtime.wal_column AS (
	name text,
	type_name text,
	type_oid oid,
	value jsonb,
	is_pkey boolean,
	is_selectable boolean
);


--
-- Name: wal_rls; Type: TYPE; Schema: realtime; Owner: -
--

CREATE TYPE realtime.wal_rls AS (
	wal jsonb,
	is_rls_enabled boolean,
	subscription_ids uuid[],
	errors text[]
);


--
-- Name: email(); Type: FUNCTION; Schema: auth; Owner: -
--

CREATE FUNCTION auth.email() RETURNS text
    LANGUAGE sql STABLE
    AS $$
  select 
  coalesce(
    nullif(current_setting('request.jwt.claim.email', true), ''),
    (nullif(current_setting('request.jwt.claims', true), '')::jsonb ->> 'email')
  )::text
$$;


--
-- Name: FUNCTION email(); Type: COMMENT; Schema: auth; Owner: -
--

COMMENT ON FUNCTION auth.email() IS 'Deprecated. Use auth.jwt() -> ''email'' instead.';


--
-- Name: jwt(); Type: FUNCTION; Schema: auth; Owner: -
--

CREATE FUNCTION auth.jwt() RETURNS jsonb
    LANGUAGE sql STABLE
    AS $$
  select 
    coalesce(
        nullif(current_setting('request.jwt.claim', true), ''),
        nullif(current_setting('request.jwt.claims', true), '')
    )::jsonb
$$;


--
-- Name: role(); Type: FUNCTION; Schema: auth; Owner: -
--

CREATE FUNCTION auth.role() RETURNS text
    LANGUAGE sql STABLE
    AS $$
  select 
  coalesce(
    nullif(current_setting('request.jwt.claim.role', true), ''),
    (nullif(current_setting('request.jwt.claims', true), '')::jsonb ->> 'role')
  )::text
$$;


--
-- Name: FUNCTION role(); Type: COMMENT; Schema: auth; Owner: -
--

COMMENT ON FUNCTION auth.role() IS 'Deprecated. Use auth.jwt() -> ''role'' instead.';


--
-- Name: uid(); Type: FUNCTION; Schema: auth; Owner: -
--

CREATE FUNCTION auth.uid() RETURNS uuid
    LANGUAGE sql STABLE
    AS $$
  select 
  coalesce(
    nullif(current_setting('request.jwt.claim.sub', true), ''),
    (nullif(current_setting('request.jwt.claims', true), '')::jsonb ->> 'sub')
  )::uuid
$$;


--
-- Name: FUNCTION uid(); Type: COMMENT; Schema: auth; Owner: -
--

COMMENT ON FUNCTION auth.uid() IS 'Deprecated. Use auth.jwt() -> ''sub'' instead.';


--
-- Name: grant_pg_cron_access(); Type: FUNCTION; Schema: extensions; Owner: -
--

CREATE FUNCTION extensions.grant_pg_cron_access() RETURNS event_trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
  IF EXISTS (
    SELECT
    FROM pg_event_trigger_ddl_commands() AS ev
    JOIN pg_extension AS ext
    ON ev.objid = ext.oid
    WHERE ext.extname = 'pg_cron'
  )
  THEN
    grant usage on schema cron to postgres with grant option;

    alter default privileges in schema cron grant all on tables to postgres with grant option;
    alter default privileges in schema cron grant all on functions to postgres with grant option;
    alter default privileges in schema cron grant all on sequences to postgres with grant option;

    alter default privileges for user supabase_admin in schema cron grant all
        on sequences to postgres with grant option;
    alter default privileges for user supabase_admin in schema cron grant all
        on tables to postgres with grant option;
    alter default privileges for user supabase_admin in schema cron grant all
        on functions to postgres with grant option;

    grant all privileges on all tables in schema cron to postgres with grant option;
    revoke all on table cron.job from postgres;
    grant select on table cron.job to postgres with grant option;
  END IF;
END;
$$;


--
-- Name: FUNCTION grant_pg_cron_access(); Type: COMMENT; Schema: extensions; Owner: -
--

COMMENT ON FUNCTION extensions.grant_pg_cron_access() IS 'Grants access to pg_cron';


--
-- Name: grant_pg_graphql_access(); Type: FUNCTION; Schema: extensions; Owner: -
--

CREATE FUNCTION extensions.grant_pg_graphql_access() RETURNS event_trigger
    LANGUAGE plpgsql
    AS $_$
DECLARE
    func_is_graphql_resolve bool;
BEGIN
    func_is_graphql_resolve = (
        SELECT n.proname = 'resolve'
        FROM pg_event_trigger_ddl_commands() AS ev
        LEFT JOIN pg_catalog.pg_proc AS n
        ON ev.objid = n.oid
    );

    IF func_is_graphql_resolve
    THEN
        -- Update public wrapper to pass all arguments through to the pg_graphql resolve func
        DROP FUNCTION IF EXISTS graphql_public.graphql;
        create or replace function graphql_public.graphql(
            "operationName" text default null,
            query text default null,
            variables jsonb default null,
            extensions jsonb default null
        )
            returns jsonb
            language sql
        as $$
            select graphql.resolve(
                query := query,
                variables := coalesce(variables, '{}'),
                "operationName" := "operationName",
                extensions := extensions
            );
        $$;

        -- This hook executes when `graphql.resolve` is created. That is not necessarily the last
        -- function in the extension so we need to grant permissions on existing entities AND
        -- update default permissions to any others that are created after `graphql.resolve`
        grant usage on schema graphql to postgres, anon, authenticated, service_role;
        grant select on all tables in schema graphql to postgres, anon, authenticated, service_role;
        grant execute on all functions in schema graphql to postgres, anon, authenticated, service_role;
        grant all on all sequences in schema graphql to postgres, anon, authenticated, service_role;
        alter default privileges in schema graphql grant all on tables to postgres, anon, authenticated, service_role;
        alter default privileges in schema graphql grant all on functions to postgres, anon, authenticated, service_role;
        alter default privileges in schema graphql grant all on sequences to postgres, anon, authenticated, service_role;

        -- Allow postgres role to allow granting usage on graphql and graphql_public schemas to custom roles
        grant usage on schema graphql_public to postgres with grant option;
        grant usage on schema graphql to postgres with grant option;
    END IF;

END;
$_$;


--
-- Name: FUNCTION grant_pg_graphql_access(); Type: COMMENT; Schema: extensions; Owner: -
--

COMMENT ON FUNCTION extensions.grant_pg_graphql_access() IS 'Grants access to pg_graphql';


--
-- Name: grant_pg_net_access(); Type: FUNCTION; Schema: extensions; Owner: -
--

CREATE FUNCTION extensions.grant_pg_net_access() RETURNS event_trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM pg_event_trigger_ddl_commands() AS ev
    JOIN pg_extension AS ext
    ON ev.objid = ext.oid
    WHERE ext.extname = 'pg_net'
  )
  THEN
    IF NOT EXISTS (
      SELECT 1
      FROM pg_roles
      WHERE rolname = 'supabase_functions_admin'
    )
    THEN
      CREATE USER supabase_functions_admin NOINHERIT CREATEROLE LOGIN NOREPLICATION;
    END IF;

    GRANT USAGE ON SCHEMA net TO supabase_functions_admin, postgres, anon, authenticated, service_role;

    IF EXISTS (
      SELECT FROM pg_extension
      WHERE extname = 'pg_net'
      -- all versions in use on existing projects as of 2025-02-20
      -- version 0.12.0 onwards don't need these applied
      AND extversion IN ('0.2', '0.6', '0.7', '0.7.1', '0.8', '0.10.0', '0.11.0')
    ) THEN
      ALTER function net.http_get(url text, params jsonb, headers jsonb, timeout_milliseconds integer) SECURITY DEFINER;
      ALTER function net.http_post(url text, body jsonb, params jsonb, headers jsonb, timeout_milliseconds integer) SECURITY DEFINER;

      ALTER function net.http_get(url text, params jsonb, headers jsonb, timeout_milliseconds integer) SET search_path = net;
      ALTER function net.http_post(url text, body jsonb, params jsonb, headers jsonb, timeout_milliseconds integer) SET search_path = net;

      REVOKE ALL ON FUNCTION net.http_get(url text, params jsonb, headers jsonb, timeout_milliseconds integer) FROM PUBLIC;
      REVOKE ALL ON FUNCTION net.http_post(url text, body jsonb, params jsonb, headers jsonb, timeout_milliseconds integer) FROM PUBLIC;

      GRANT EXECUTE ON FUNCTION net.http_get(url text, params jsonb, headers jsonb, timeout_milliseconds integer) TO supabase_functions_admin, postgres, anon, authenticated, service_role;
      GRANT EXECUTE ON FUNCTION net.http_post(url text, body jsonb, params jsonb, headers jsonb, timeout_milliseconds integer) TO supabase_functions_admin, postgres, anon, authenticated, service_role;
    END IF;
  END IF;
END;
$$;


--
-- Name: FUNCTION grant_pg_net_access(); Type: COMMENT; Schema: extensions; Owner: -
--

COMMENT ON FUNCTION extensions.grant_pg_net_access() IS 'Grants access to pg_net';


--
-- Name: pgrst_ddl_watch(); Type: FUNCTION; Schema: extensions; Owner: -
--

CREATE FUNCTION extensions.pgrst_ddl_watch() RETURNS event_trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
  cmd record;
BEGIN
  FOR cmd IN SELECT * FROM pg_event_trigger_ddl_commands()
  LOOP
    IF cmd.command_tag IN (
      'CREATE SCHEMA', 'ALTER SCHEMA'
    , 'CREATE TABLE', 'CREATE TABLE AS', 'SELECT INTO', 'ALTER TABLE'
    , 'CREATE FOREIGN TABLE', 'ALTER FOREIGN TABLE'
    , 'CREATE VIEW', 'ALTER VIEW'
    , 'CREATE MATERIALIZED VIEW', 'ALTER MATERIALIZED VIEW'
    , 'CREATE FUNCTION', 'ALTER FUNCTION'
    , 'CREATE TRIGGER'
    , 'CREATE TYPE', 'ALTER TYPE'
    , 'CREATE RULE'
    , 'COMMENT'
    )
    -- don't notify in case of CREATE TEMP table or other objects created on pg_temp
    AND cmd.schema_name is distinct from 'pg_temp'
    THEN
      NOTIFY pgrst, 'reload schema';
    END IF;
  END LOOP;
END; $$;


--
-- Name: pgrst_drop_watch(); Type: FUNCTION; Schema: extensions; Owner: -
--

CREATE FUNCTION extensions.pgrst_drop_watch() RETURNS event_trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
  obj record;
BEGIN
  FOR obj IN SELECT * FROM pg_event_trigger_dropped_objects()
  LOOP
    IF obj.object_type IN (
      'schema'
    , 'table'
    , 'foreign table'
    , 'view'
    , 'materialized view'
    , 'function'
    , 'trigger'
    , 'type'
    , 'rule'
    )
    AND obj.is_temporary IS false -- no pg_temp objects
    THEN
      NOTIFY pgrst, 'reload schema';
    END IF;
  END LOOP;
END; $$;


--
-- Name: set_graphql_placeholder(); Type: FUNCTION; Schema: extensions; Owner: -
--

CREATE FUNCTION extensions.set_graphql_placeholder() RETURNS event_trigger
    LANGUAGE plpgsql
    AS $_$
    DECLARE
    graphql_is_dropped bool;
    BEGIN
    graphql_is_dropped = (
        SELECT ev.schema_name = 'graphql_public'
        FROM pg_event_trigger_dropped_objects() AS ev
        WHERE ev.schema_name = 'graphql_public'
    );

    IF graphql_is_dropped
    THEN
        create or replace function graphql_public.graphql(
            "operationName" text default null,
            query text default null,
            variables jsonb default null,
            extensions jsonb default null
        )
            returns jsonb
            language plpgsql
        as $$
            DECLARE
                server_version float;
            BEGIN
                server_version = (SELECT (SPLIT_PART((select version()), ' ', 2))::float);

                IF server_version >= 14 THEN
                    RETURN jsonb_build_object(
                        'errors', jsonb_build_array(
                            jsonb_build_object(
                                'message', 'pg_graphql extension is not enabled.'
                            )
                        )
                    );
                ELSE
                    RETURN jsonb_build_object(
                        'errors', jsonb_build_array(
                            jsonb_build_object(
                                'message', 'pg_graphql is only available on projects running Postgres 14 onwards.'
                            )
                        )
                    );
                END IF;
            END;
        $$;
    END IF;

    END;
$_$;


--
-- Name: FUNCTION set_graphql_placeholder(); Type: COMMENT; Schema: extensions; Owner: -
--

COMMENT ON FUNCTION extensions.set_graphql_placeholder() IS 'Reintroduces placeholder function for graphql_public.graphql';


--
-- Name: get_auth(text); Type: FUNCTION; Schema: pgbouncer; Owner: -
--

CREATE FUNCTION pgbouncer.get_auth(p_usename text) RETURNS TABLE(username text, password text)
    LANGUAGE plpgsql SECURITY DEFINER
    AS $_$
begin
    raise debug 'PgBouncer auth request: %', p_usename;

    return query
    select 
        rolname::text, 
        case when rolvaliduntil < now() 
            then null 
            else rolpassword::text 
        end 
    from pg_authid 
    where rolname=$1 and rolcanlogin;
end;
$_$;


--
-- Name: backfill_monthly_pl(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.backfill_monthly_pl() RETURNS void
    LANGUAGE plpgsql
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


--
-- Name: calculate_pl_with_multiplier(text, text, double precision); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.calculate_pl_with_multiplier(trade_type text, symbol text, base_pl double precision) RETURNS double precision
    LANGUAGE plpgsql
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


--
-- Name: calculate_pl_with_multiplier(text, text, numeric); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.calculate_pl_with_multiplier(trade_type text, symbol text, base_pl numeric) RETURNS numeric
    LANGUAGE plpgsql
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


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: trades; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.trades (
    trade_id character varying NOT NULL,
    symbol character varying NOT NULL,
    trade_type character varying NOT NULL,
    status character varying NOT NULL,
    entry_price double precision NOT NULL,
    average_price double precision,
    current_size character varying,
    size character varying NOT NULL,
    created_at timestamp with time zone NOT NULL,
    closed_at timestamp with time zone,
    exit_price double precision,
    average_exit_price double precision,
    profit_loss double precision,
    risk_reward_ratio double precision,
    win_loss character varying,
    configuration_id integer,
    is_contract boolean DEFAULT false,
    is_day_trade boolean DEFAULT false,
    strike double precision,
    expiration_date timestamp with time zone,
    option_type character varying,
    user_id character varying
);


--
-- Name: transactions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.transactions (
    id character varying NOT NULL,
    trade_id character varying,
    transaction_type character varying,
    amount double precision,
    size character varying,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: calculate_realized_pl_for_transaction(public.trades, public.transactions); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.calculate_realized_pl_for_transaction(trade_record public.trades, transaction_record public.transactions) RETURNS double precision
    LANGUAGE plpgsql
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


--
-- Name: check_expired_trades_trigger(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.check_expired_trades_trigger() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    PERFORM handle_expired_trades();
    RETURN NULL;
END;
$$;


--
-- Name: cleanup_and_update_trades(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.cleanup_and_update_trades() RETURNS void
    LANGUAGE plpgsql
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


--
-- Name: close_expired_trades(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.close_expired_trades() RETURNS trigger
    LANGUAGE plpgsql
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


--
-- Name: delete_all_transactions(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.delete_all_transactions() RETURNS void
    LANGUAGE plpgsql SECURITY DEFINER
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


--
-- Name: generate_options_strategy_id(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.generate_options_strategy_id() RETURNS text
    LANGUAGE plpgsql
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


--
-- Name: generate_options_strategy_trade_id(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.generate_options_strategy_trade_id() RETURNS text
    LANGUAGE plpgsql
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


--
-- Name: generate_options_strategy_transaction_id(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.generate_options_strategy_transaction_id() RETURNS text
    LANGUAGE plpgsql
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


--
-- Name: generate_strategy_leg_id(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.generate_strategy_leg_id() RETURNS text
    LANGUAGE plpgsql
    AS $$
BEGIN
    RETURN 'leg_' || EXTRACT(EPOCH FROM CURRENT_TIMESTAMP)::BIGINT || '_' || FLOOR(RANDOM() * 1000)::TEXT;
END;
$$;


--
-- Name: handle_expired_trades(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.handle_expired_trades() RETURNS void
    LANGUAGE plpgsql
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


--
-- Name: set_options_strategy_ids(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.set_options_strategy_ids() RETURNS trigger
    LANGUAGE plpgsql
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


--
-- Name: set_options_strategy_trade_id(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.set_options_strategy_trade_id() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF NEW.strategy_id IS NULL THEN
        NEW.strategy_id := generate_options_strategy_trade_id();
    END IF;
    RETURN NEW;
END;
$$;


--
-- Name: set_options_strategy_transaction_id(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.set_options_strategy_transaction_id() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF NEW.transaction_id IS NULL THEN
        NEW.transaction_id := generate_options_strategy_transaction_id();
    END IF;
    RETURN NEW;
END;
$$;


--
-- Name: trigger_exit_expired_trades(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.trigger_exit_expired_trades() RETURNS void
    LANGUAGE plpgsql SECURITY DEFINER
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


--
-- Name: update_all_options_strategies(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.update_all_options_strategies() RETURNS void
    LANGUAGE plpgsql
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


--
-- Name: update_monthly_pl(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.update_monthly_pl() RETURNS trigger
    LANGUAGE plpgsql
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


--
-- Name: update_monthly_pl_regular_trade(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.update_monthly_pl_regular_trade() RETURNS trigger
    LANGUAGE plpgsql
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


--
-- Name: update_monthly_pl_strategy_trade(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.update_monthly_pl_strategy_trade() RETURNS trigger
    LANGUAGE plpgsql
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


--
-- Name: update_monthly_pl_updated_at(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.update_monthly_pl_updated_at() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;


--
-- Name: update_monthly_strategy_pl(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.update_monthly_strategy_pl() RETURNS trigger
    LANGUAGE plpgsql
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


--
-- Name: update_options_strategy_before_transaction_change(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.update_options_strategy_before_transaction_change() RETURNS trigger
    LANGUAGE plpgsql
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


--
-- Name: update_trade_before_transaction_change(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.update_trade_before_transaction_change() RETURNS trigger
    LANGUAGE plpgsql
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


--
-- Name: apply_rls(jsonb, integer); Type: FUNCTION; Schema: realtime; Owner: -
--

CREATE FUNCTION realtime.apply_rls(wal jsonb, max_record_bytes integer DEFAULT (1024 * 1024)) RETURNS SETOF realtime.wal_rls
    LANGUAGE plpgsql
    AS $$
declare
-- Regclass of the table e.g. public.notes
entity_ regclass = (quote_ident(wal ->> 'schema') || '.' || quote_ident(wal ->> 'table'))::regclass;

-- I, U, D, T: insert, update ...
action realtime.action = (
    case wal ->> 'action'
        when 'I' then 'INSERT'
        when 'U' then 'UPDATE'
        when 'D' then 'DELETE'
        else 'ERROR'
    end
);

-- Is row level security enabled for the table
is_rls_enabled bool = relrowsecurity from pg_class where oid = entity_;

subscriptions realtime.subscription[] = array_agg(subs)
    from
        realtime.subscription subs
    where
        subs.entity = entity_;

-- Subscription vars
roles regrole[] = array_agg(distinct us.claims_role::text)
    from
        unnest(subscriptions) us;

working_role regrole;
claimed_role regrole;
claims jsonb;

subscription_id uuid;
subscription_has_access bool;
visible_to_subscription_ids uuid[] = '{}';

-- structured info for wal's columns
columns realtime.wal_column[];
-- previous identity values for update/delete
old_columns realtime.wal_column[];

error_record_exceeds_max_size boolean = octet_length(wal::text) > max_record_bytes;

-- Primary jsonb output for record
output jsonb;

begin
perform set_config('role', null, true);

columns =
    array_agg(
        (
            x->>'name',
            x->>'type',
            x->>'typeoid',
            realtime.cast(
                (x->'value') #>> '{}',
                coalesce(
                    (x->>'typeoid')::regtype, -- null when wal2json version <= 2.4
                    (x->>'type')::regtype
                )
            ),
            (pks ->> 'name') is not null,
            true
        )::realtime.wal_column
    )
    from
        jsonb_array_elements(wal -> 'columns') x
        left join jsonb_array_elements(wal -> 'pk') pks
            on (x ->> 'name') = (pks ->> 'name');

old_columns =
    array_agg(
        (
            x->>'name',
            x->>'type',
            x->>'typeoid',
            realtime.cast(
                (x->'value') #>> '{}',
                coalesce(
                    (x->>'typeoid')::regtype, -- null when wal2json version <= 2.4
                    (x->>'type')::regtype
                )
            ),
            (pks ->> 'name') is not null,
            true
        )::realtime.wal_column
    )
    from
        jsonb_array_elements(wal -> 'identity') x
        left join jsonb_array_elements(wal -> 'pk') pks
            on (x ->> 'name') = (pks ->> 'name');

for working_role in select * from unnest(roles) loop

    -- Update `is_selectable` for columns and old_columns
    columns =
        array_agg(
            (
                c.name,
                c.type_name,
                c.type_oid,
                c.value,
                c.is_pkey,
                pg_catalog.has_column_privilege(working_role, entity_, c.name, 'SELECT')
            )::realtime.wal_column
        )
        from
            unnest(columns) c;

    old_columns =
            array_agg(
                (
                    c.name,
                    c.type_name,
                    c.type_oid,
                    c.value,
                    c.is_pkey,
                    pg_catalog.has_column_privilege(working_role, entity_, c.name, 'SELECT')
                )::realtime.wal_column
            )
            from
                unnest(old_columns) c;

    if action <> 'DELETE' and count(1) = 0 from unnest(columns) c where c.is_pkey then
        return next (
            jsonb_build_object(
                'schema', wal ->> 'schema',
                'table', wal ->> 'table',
                'type', action
            ),
            is_rls_enabled,
            -- subscriptions is already filtered by entity
            (select array_agg(s.subscription_id) from unnest(subscriptions) as s where claims_role = working_role),
            array['Error 400: Bad Request, no primary key']
        )::realtime.wal_rls;

    -- The claims role does not have SELECT permission to the primary key of entity
    elsif action <> 'DELETE' and sum(c.is_selectable::int) <> count(1) from unnest(columns) c where c.is_pkey then
        return next (
            jsonb_build_object(
                'schema', wal ->> 'schema',
                'table', wal ->> 'table',
                'type', action
            ),
            is_rls_enabled,
            (select array_agg(s.subscription_id) from unnest(subscriptions) as s where claims_role = working_role),
            array['Error 401: Unauthorized']
        )::realtime.wal_rls;

    else
        output = jsonb_build_object(
            'schema', wal ->> 'schema',
            'table', wal ->> 'table',
            'type', action,
            'commit_timestamp', to_char(
                ((wal ->> 'timestamp')::timestamptz at time zone 'utc'),
                'YYYY-MM-DD"T"HH24:MI:SS.MS"Z"'
            ),
            'columns', (
                select
                    jsonb_agg(
                        jsonb_build_object(
                            'name', pa.attname,
                            'type', pt.typname
                        )
                        order by pa.attnum asc
                    )
                from
                    pg_attribute pa
                    join pg_type pt
                        on pa.atttypid = pt.oid
                where
                    attrelid = entity_
                    and attnum > 0
                    and pg_catalog.has_column_privilege(working_role, entity_, pa.attname, 'SELECT')
            )
        )
        -- Add "record" key for insert and update
        || case
            when action in ('INSERT', 'UPDATE') then
                jsonb_build_object(
                    'record',
                    (
                        select
                            jsonb_object_agg(
                                -- if unchanged toast, get column name and value from old record
                                coalesce((c).name, (oc).name),
                                case
                                    when (c).name is null then (oc).value
                                    else (c).value
                                end
                            )
                        from
                            unnest(columns) c
                            full outer join unnest(old_columns) oc
                                on (c).name = (oc).name
                        where
                            coalesce((c).is_selectable, (oc).is_selectable)
                            and ( not error_record_exceeds_max_size or (octet_length((c).value::text) <= 64))
                    )
                )
            else '{}'::jsonb
        end
        -- Add "old_record" key for update and delete
        || case
            when action = 'UPDATE' then
                jsonb_build_object(
                        'old_record',
                        (
                            select jsonb_object_agg((c).name, (c).value)
                            from unnest(old_columns) c
                            where
                                (c).is_selectable
                                and ( not error_record_exceeds_max_size or (octet_length((c).value::text) <= 64))
                        )
                    )
            when action = 'DELETE' then
                jsonb_build_object(
                    'old_record',
                    (
                        select jsonb_object_agg((c).name, (c).value)
                        from unnest(old_columns) c
                        where
                            (c).is_selectable
                            and ( not error_record_exceeds_max_size or (octet_length((c).value::text) <= 64))
                            and ( not is_rls_enabled or (c).is_pkey ) -- if RLS enabled, we can't secure deletes so filter to pkey
                    )
                )
            else '{}'::jsonb
        end;

        -- Create the prepared statement
        if is_rls_enabled and action <> 'DELETE' then
            if (select 1 from pg_prepared_statements where name = 'walrus_rls_stmt' limit 1) > 0 then
                deallocate walrus_rls_stmt;
            end if;
            execute realtime.build_prepared_statement_sql('walrus_rls_stmt', entity_, columns);
        end if;

        visible_to_subscription_ids = '{}';

        for subscription_id, claims in (
                select
                    subs.subscription_id,
                    subs.claims
                from
                    unnest(subscriptions) subs
                where
                    subs.entity = entity_
                    and subs.claims_role = working_role
                    and (
                        realtime.is_visible_through_filters(columns, subs.filters)
                        or (
                          action = 'DELETE'
                          and realtime.is_visible_through_filters(old_columns, subs.filters)
                        )
                    )
        ) loop

            if not is_rls_enabled or action = 'DELETE' then
                visible_to_subscription_ids = visible_to_subscription_ids || subscription_id;
            else
                -- Check if RLS allows the role to see the record
                perform
                    -- Trim leading and trailing quotes from working_role because set_config
                    -- doesn't recognize the role as valid if they are included
                    set_config('role', trim(both '"' from working_role::text), true),
                    set_config('request.jwt.claims', claims::text, true);

                execute 'execute walrus_rls_stmt' into subscription_has_access;

                if subscription_has_access then
                    visible_to_subscription_ids = visible_to_subscription_ids || subscription_id;
                end if;
            end if;
        end loop;

        perform set_config('role', null, true);

        return next (
            output,
            is_rls_enabled,
            visible_to_subscription_ids,
            case
                when error_record_exceeds_max_size then array['Error 413: Payload Too Large']
                else '{}'
            end
        )::realtime.wal_rls;

    end if;
end loop;

perform set_config('role', null, true);
end;
$$;


--
-- Name: broadcast_changes(text, text, text, text, text, record, record, text); Type: FUNCTION; Schema: realtime; Owner: -
--

CREATE FUNCTION realtime.broadcast_changes(topic_name text, event_name text, operation text, table_name text, table_schema text, new record, old record, level text DEFAULT 'ROW'::text) RETURNS void
    LANGUAGE plpgsql
    AS $$
DECLARE
    -- Declare a variable to hold the JSONB representation of the row
    row_data jsonb := '{}'::jsonb;
BEGIN
    IF level = 'STATEMENT' THEN
        RAISE EXCEPTION 'function can only be triggered for each row, not for each statement';
    END IF;
    -- Check the operation type and handle accordingly
    IF operation = 'INSERT' OR operation = 'UPDATE' OR operation = 'DELETE' THEN
        row_data := jsonb_build_object('old_record', OLD, 'record', NEW, 'operation', operation, 'table', table_name, 'schema', table_schema);
        PERFORM realtime.send (row_data, event_name, topic_name);
    ELSE
        RAISE EXCEPTION 'Unexpected operation type: %', operation;
    END IF;
EXCEPTION
    WHEN OTHERS THEN
        RAISE EXCEPTION 'Failed to process the row: %', SQLERRM;
END;

$$;


--
-- Name: build_prepared_statement_sql(text, regclass, realtime.wal_column[]); Type: FUNCTION; Schema: realtime; Owner: -
--

CREATE FUNCTION realtime.build_prepared_statement_sql(prepared_statement_name text, entity regclass, columns realtime.wal_column[]) RETURNS text
    LANGUAGE sql
    AS $$
      /*
      Builds a sql string that, if executed, creates a prepared statement to
      tests retrive a row from *entity* by its primary key columns.
      Example
          select realtime.build_prepared_statement_sql('public.notes', '{"id"}'::text[], '{"bigint"}'::text[])
      */
          select
      'prepare ' || prepared_statement_name || ' as
          select
              exists(
                  select
                      1
                  from
                      ' || entity || '
                  where
                      ' || string_agg(quote_ident(pkc.name) || '=' || quote_nullable(pkc.value #>> '{}') , ' and ') || '
              )'
          from
              unnest(columns) pkc
          where
              pkc.is_pkey
          group by
              entity
      $$;


--
-- Name: cast(text, regtype); Type: FUNCTION; Schema: realtime; Owner: -
--

CREATE FUNCTION realtime."cast"(val text, type_ regtype) RETURNS jsonb
    LANGUAGE plpgsql IMMUTABLE
    AS $$
    declare
      res jsonb;
    begin
      execute format('select to_jsonb(%L::'|| type_::text || ')', val)  into res;
      return res;
    end
    $$;


--
-- Name: check_equality_op(realtime.equality_op, regtype, text, text); Type: FUNCTION; Schema: realtime; Owner: -
--

CREATE FUNCTION realtime.check_equality_op(op realtime.equality_op, type_ regtype, val_1 text, val_2 text) RETURNS boolean
    LANGUAGE plpgsql IMMUTABLE
    AS $$
      /*
      Casts *val_1* and *val_2* as type *type_* and check the *op* condition for truthiness
      */
      declare
          op_symbol text = (
              case
                  when op = 'eq' then '='
                  when op = 'neq' then '!='
                  when op = 'lt' then '<'
                  when op = 'lte' then '<='
                  when op = 'gt' then '>'
                  when op = 'gte' then '>='
                  when op = 'in' then '= any'
                  else 'UNKNOWN OP'
              end
          );
          res boolean;
      begin
          execute format(
              'select %L::'|| type_::text || ' ' || op_symbol
              || ' ( %L::'
              || (
                  case
                      when op = 'in' then type_::text || '[]'
                      else type_::text end
              )
              || ')', val_1, val_2) into res;
          return res;
      end;
      $$;


--
-- Name: is_visible_through_filters(realtime.wal_column[], realtime.user_defined_filter[]); Type: FUNCTION; Schema: realtime; Owner: -
--

CREATE FUNCTION realtime.is_visible_through_filters(columns realtime.wal_column[], filters realtime.user_defined_filter[]) RETURNS boolean
    LANGUAGE sql IMMUTABLE
    AS $_$
    /*
    Should the record be visible (true) or filtered out (false) after *filters* are applied
    */
        select
            -- Default to allowed when no filters present
            $2 is null -- no filters. this should not happen because subscriptions has a default
            or array_length($2, 1) is null -- array length of an empty array is null
            or bool_and(
                coalesce(
                    realtime.check_equality_op(
                        op:=f.op,
                        type_:=coalesce(
                            col.type_oid::regtype, -- null when wal2json version <= 2.4
                            col.type_name::regtype
                        ),
                        -- cast jsonb to text
                        val_1:=col.value #>> '{}',
                        val_2:=f.value
                    ),
                    false -- if null, filter does not match
                )
            )
        from
            unnest(filters) f
            join unnest(columns) col
                on f.column_name = col.name;
    $_$;


--
-- Name: list_changes(name, name, integer, integer); Type: FUNCTION; Schema: realtime; Owner: -
--

CREATE FUNCTION realtime.list_changes(publication name, slot_name name, max_changes integer, max_record_bytes integer) RETURNS SETOF realtime.wal_rls
    LANGUAGE sql
    SET log_min_messages TO 'fatal'
    AS $$
      with pub as (
        select
          concat_ws(
            ',',
            case when bool_or(pubinsert) then 'insert' else null end,
            case when bool_or(pubupdate) then 'update' else null end,
            case when bool_or(pubdelete) then 'delete' else null end
          ) as w2j_actions,
          coalesce(
            string_agg(
              realtime.quote_wal2json(format('%I.%I', schemaname, tablename)::regclass),
              ','
            ) filter (where ppt.tablename is not null and ppt.tablename not like '% %'),
            ''
          ) w2j_add_tables
        from
          pg_publication pp
          left join pg_publication_tables ppt
            on pp.pubname = ppt.pubname
        where
          pp.pubname = publication
        group by
          pp.pubname
        limit 1
      ),
      w2j as (
        select
          x.*, pub.w2j_add_tables
        from
          pub,
          pg_logical_slot_get_changes(
            slot_name, null, max_changes,
            'include-pk', 'true',
            'include-transaction', 'false',
            'include-timestamp', 'true',
            'include-type-oids', 'true',
            'format-version', '2',
            'actions', pub.w2j_actions,
            'add-tables', pub.w2j_add_tables
          ) x
      )
      select
        xyz.wal,
        xyz.is_rls_enabled,
        xyz.subscription_ids,
        xyz.errors
      from
        w2j,
        realtime.apply_rls(
          wal := w2j.data::jsonb,
          max_record_bytes := max_record_bytes
        ) xyz(wal, is_rls_enabled, subscription_ids, errors)
      where
        w2j.w2j_add_tables <> ''
        and xyz.subscription_ids[1] is not null
    $$;


--
-- Name: quote_wal2json(regclass); Type: FUNCTION; Schema: realtime; Owner: -
--

CREATE FUNCTION realtime.quote_wal2json(entity regclass) RETURNS text
    LANGUAGE sql IMMUTABLE STRICT
    AS $$
      select
        (
          select string_agg('' || ch,'')
          from unnest(string_to_array(nsp.nspname::text, null)) with ordinality x(ch, idx)
          where
            not (x.idx = 1 and x.ch = '"')
            and not (
              x.idx = array_length(string_to_array(nsp.nspname::text, null), 1)
              and x.ch = '"'
            )
        )
        || '.'
        || (
          select string_agg('' || ch,'')
          from unnest(string_to_array(pc.relname::text, null)) with ordinality x(ch, idx)
          where
            not (x.idx = 1 and x.ch = '"')
            and not (
              x.idx = array_length(string_to_array(nsp.nspname::text, null), 1)
              and x.ch = '"'
            )
          )
      from
        pg_class pc
        join pg_namespace nsp
          on pc.relnamespace = nsp.oid
      where
        pc.oid = entity
    $$;


--
-- Name: send(jsonb, text, text, boolean); Type: FUNCTION; Schema: realtime; Owner: -
--

CREATE FUNCTION realtime.send(payload jsonb, event text, topic text, private boolean DEFAULT true) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
  BEGIN
    -- Set the topic configuration
    EXECUTE format('SET LOCAL realtime.topic TO %L', topic);

    -- Attempt to insert the message
    INSERT INTO realtime.messages (payload, event, topic, private, extension)
    VALUES (payload, event, topic, private, 'broadcast');
  EXCEPTION
    WHEN OTHERS THEN
      -- Capture and notify the error
      PERFORM pg_notify(
          'realtime:system',
          jsonb_build_object(
              'error', SQLERRM,
              'function', 'realtime.send',
              'event', event,
              'topic', topic,
              'private', private
          )::text
      );
  END;
END;
$$;


--
-- Name: subscription_check_filters(); Type: FUNCTION; Schema: realtime; Owner: -
--

CREATE FUNCTION realtime.subscription_check_filters() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
    /*
    Validates that the user defined filters for a subscription:
    - refer to valid columns that the claimed role may access
    - values are coercable to the correct column type
    */
    declare
        col_names text[] = coalesce(
                array_agg(c.column_name order by c.ordinal_position),
                '{}'::text[]
            )
            from
                information_schema.columns c
            where
                format('%I.%I', c.table_schema, c.table_name)::regclass = new.entity
                and pg_catalog.has_column_privilege(
                    (new.claims ->> 'role'),
                    format('%I.%I', c.table_schema, c.table_name)::regclass,
                    c.column_name,
                    'SELECT'
                );
        filter realtime.user_defined_filter;
        col_type regtype;

        in_val jsonb;
    begin
        for filter in select * from unnest(new.filters) loop
            -- Filtered column is valid
            if not filter.column_name = any(col_names) then
                raise exception 'invalid column for filter %', filter.column_name;
            end if;

            -- Type is sanitized and safe for string interpolation
            col_type = (
                select atttypid::regtype
                from pg_catalog.pg_attribute
                where attrelid = new.entity
                      and attname = filter.column_name
            );
            if col_type is null then
                raise exception 'failed to lookup type for column %', filter.column_name;
            end if;

            -- Set maximum number of entries for in filter
            if filter.op = 'in'::realtime.equality_op then
                in_val = realtime.cast(filter.value, (col_type::text || '[]')::regtype);
                if coalesce(jsonb_array_length(in_val), 0) > 100 then
                    raise exception 'too many values for `in` filter. Maximum 100';
                end if;
            else
                -- raises an exception if value is not coercable to type
                perform realtime.cast(filter.value, col_type);
            end if;

        end loop;

        -- Apply consistent order to filters so the unique constraint on
        -- (subscription_id, entity, filters) can't be tricked by a different filter order
        new.filters = coalesce(
            array_agg(f order by f.column_name, f.op, f.value),
            '{}'
        ) from unnest(new.filters) f;

        return new;
    end;
    $$;


--
-- Name: to_regrole(text); Type: FUNCTION; Schema: realtime; Owner: -
--

CREATE FUNCTION realtime.to_regrole(role_name text) RETURNS regrole
    LANGUAGE sql IMMUTABLE
    AS $$ select role_name::regrole $$;


--
-- Name: topic(); Type: FUNCTION; Schema: realtime; Owner: -
--

CREATE FUNCTION realtime.topic() RETURNS text
    LANGUAGE sql STABLE
    AS $$
select nullif(current_setting('realtime.topic', true), '')::text;
$$;


--
-- Name: can_insert_object(text, text, uuid, jsonb); Type: FUNCTION; Schema: storage; Owner: -
--

CREATE FUNCTION storage.can_insert_object(bucketid text, name text, owner uuid, metadata jsonb) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
  INSERT INTO "storage"."objects" ("bucket_id", "name", "owner", "metadata") VALUES (bucketid, name, owner, metadata);
  -- hack to rollback the successful insert
  RAISE sqlstate 'PT200' using
  message = 'ROLLBACK',
  detail = 'rollback successful insert';
END
$$;


--
-- Name: extension(text); Type: FUNCTION; Schema: storage; Owner: -
--

CREATE FUNCTION storage.extension(name text) RETURNS text
    LANGUAGE plpgsql
    AS $$
DECLARE
_parts text[];
_filename text;
BEGIN
	select string_to_array(name, '/') into _parts;
	select _parts[array_length(_parts,1)] into _filename;
	-- @todo return the last part instead of 2
	return reverse(split_part(reverse(_filename), '.', 1));
END
$$;


--
-- Name: filename(text); Type: FUNCTION; Schema: storage; Owner: -
--

CREATE FUNCTION storage.filename(name text) RETURNS text
    LANGUAGE plpgsql
    AS $$
DECLARE
_parts text[];
BEGIN
	select string_to_array(name, '/') into _parts;
	return _parts[array_length(_parts,1)];
END
$$;


--
-- Name: foldername(text); Type: FUNCTION; Schema: storage; Owner: -
--

CREATE FUNCTION storage.foldername(name text) RETURNS text[]
    LANGUAGE plpgsql
    AS $$
DECLARE
_parts text[];
BEGIN
	select string_to_array(name, '/') into _parts;
	return _parts[1:array_length(_parts,1)-1];
END
$$;


--
-- Name: get_size_by_bucket(); Type: FUNCTION; Schema: storage; Owner: -
--

CREATE FUNCTION storage.get_size_by_bucket() RETURNS TABLE(size bigint, bucket_id text)
    LANGUAGE plpgsql
    AS $$
BEGIN
    return query
        select sum((metadata->>'size')::int) as size, obj.bucket_id
        from "storage".objects as obj
        group by obj.bucket_id;
END
$$;


--
-- Name: list_multipart_uploads_with_delimiter(text, text, text, integer, text, text); Type: FUNCTION; Schema: storage; Owner: -
--

CREATE FUNCTION storage.list_multipart_uploads_with_delimiter(bucket_id text, prefix_param text, delimiter_param text, max_keys integer DEFAULT 100, next_key_token text DEFAULT ''::text, next_upload_token text DEFAULT ''::text) RETURNS TABLE(key text, id text, created_at timestamp with time zone)
    LANGUAGE plpgsql
    AS $_$
BEGIN
    RETURN QUERY EXECUTE
        'SELECT DISTINCT ON(key COLLATE "C") * from (
            SELECT
                CASE
                    WHEN position($2 IN substring(key from length($1) + 1)) > 0 THEN
                        substring(key from 1 for length($1) + position($2 IN substring(key from length($1) + 1)))
                    ELSE
                        key
                END AS key, id, created_at
            FROM
                storage.s3_multipart_uploads
            WHERE
                bucket_id = $5 AND
                key ILIKE $1 || ''%'' AND
                CASE
                    WHEN $4 != '''' AND $6 = '''' THEN
                        CASE
                            WHEN position($2 IN substring(key from length($1) + 1)) > 0 THEN
                                substring(key from 1 for length($1) + position($2 IN substring(key from length($1) + 1))) COLLATE "C" > $4
                            ELSE
                                key COLLATE "C" > $4
                            END
                    ELSE
                        true
                END AND
                CASE
                    WHEN $6 != '''' THEN
                        id COLLATE "C" > $6
                    ELSE
                        true
                    END
            ORDER BY
                key COLLATE "C" ASC, created_at ASC) as e order by key COLLATE "C" LIMIT $3'
        USING prefix_param, delimiter_param, max_keys, next_key_token, bucket_id, next_upload_token;
END;
$_$;


--
-- Name: list_objects_with_delimiter(text, text, text, integer, text, text); Type: FUNCTION; Schema: storage; Owner: -
--

CREATE FUNCTION storage.list_objects_with_delimiter(bucket_id text, prefix_param text, delimiter_param text, max_keys integer DEFAULT 100, start_after text DEFAULT ''::text, next_token text DEFAULT ''::text) RETURNS TABLE(name text, id uuid, metadata jsonb, updated_at timestamp with time zone)
    LANGUAGE plpgsql
    AS $_$
BEGIN
    RETURN QUERY EXECUTE
        'SELECT DISTINCT ON(name COLLATE "C") * from (
            SELECT
                CASE
                    WHEN position($2 IN substring(name from length($1) + 1)) > 0 THEN
                        substring(name from 1 for length($1) + position($2 IN substring(name from length($1) + 1)))
                    ELSE
                        name
                END AS name, id, metadata, updated_at
            FROM
                storage.objects
            WHERE
                bucket_id = $5 AND
                name ILIKE $1 || ''%'' AND
                CASE
                    WHEN $6 != '''' THEN
                    name COLLATE "C" > $6
                ELSE true END
                AND CASE
                    WHEN $4 != '''' THEN
                        CASE
                            WHEN position($2 IN substring(name from length($1) + 1)) > 0 THEN
                                substring(name from 1 for length($1) + position($2 IN substring(name from length($1) + 1))) COLLATE "C" > $4
                            ELSE
                                name COLLATE "C" > $4
                            END
                    ELSE
                        true
                END
            ORDER BY
                name COLLATE "C" ASC) as e order by name COLLATE "C" LIMIT $3'
        USING prefix_param, delimiter_param, max_keys, next_token, bucket_id, start_after;
END;
$_$;


--
-- Name: operation(); Type: FUNCTION; Schema: storage; Owner: -
--

CREATE FUNCTION storage.operation() RETURNS text
    LANGUAGE plpgsql STABLE
    AS $$
BEGIN
    RETURN current_setting('storage.operation', true);
END;
$$;


--
-- Name: search(text, text, integer, integer, integer, text, text, text); Type: FUNCTION; Schema: storage; Owner: -
--

CREATE FUNCTION storage.search(prefix text, bucketname text, limits integer DEFAULT 100, levels integer DEFAULT 1, offsets integer DEFAULT 0, search text DEFAULT ''::text, sortcolumn text DEFAULT 'name'::text, sortorder text DEFAULT 'asc'::text) RETURNS TABLE(name text, id uuid, updated_at timestamp with time zone, created_at timestamp with time zone, last_accessed_at timestamp with time zone, metadata jsonb)
    LANGUAGE plpgsql STABLE
    AS $_$
declare
  v_order_by text;
  v_sort_order text;
begin
  case
    when sortcolumn = 'name' then
      v_order_by = 'name';
    when sortcolumn = 'updated_at' then
      v_order_by = 'updated_at';
    when sortcolumn = 'created_at' then
      v_order_by = 'created_at';
    when sortcolumn = 'last_accessed_at' then
      v_order_by = 'last_accessed_at';
    else
      v_order_by = 'name';
  end case;

  case
    when sortorder = 'asc' then
      v_sort_order = 'asc';
    when sortorder = 'desc' then
      v_sort_order = 'desc';
    else
      v_sort_order = 'asc';
  end case;

  v_order_by = v_order_by || ' ' || v_sort_order;

  return query execute
    'with folders as (
       select path_tokens[$1] as folder
       from storage.objects
         where objects.name ilike $2 || $3 || ''%''
           and bucket_id = $4
           and array_length(objects.path_tokens, 1) <> $1
       group by folder
       order by folder ' || v_sort_order || '
     )
     (select folder as "name",
            null as id,
            null as updated_at,
            null as created_at,
            null as last_accessed_at,
            null as metadata from folders)
     union all
     (select path_tokens[$1] as "name",
            id,
            updated_at,
            created_at,
            last_accessed_at,
            metadata
     from storage.objects
     where objects.name ilike $2 || $3 || ''%''
       and bucket_id = $4
       and array_length(objects.path_tokens, 1) = $1
     order by ' || v_order_by || ')
     limit $5
     offset $6' using levels, prefix, search, bucketname, limits, offsets;
end;
$_$;


--
-- Name: update_updated_at_column(); Type: FUNCTION; Schema: storage; Owner: -
--

CREATE FUNCTION storage.update_updated_at_column() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW; 
END;
$$;


--
-- Name: audit_log_entries; Type: TABLE; Schema: auth; Owner: -
--

CREATE TABLE auth.audit_log_entries (
    instance_id uuid,
    id uuid NOT NULL,
    payload json,
    created_at timestamp with time zone,
    ip_address character varying(64) DEFAULT ''::character varying NOT NULL
);


--
-- Name: TABLE audit_log_entries; Type: COMMENT; Schema: auth; Owner: -
--

COMMENT ON TABLE auth.audit_log_entries IS 'Auth: Audit trail for user actions.';


--
-- Name: flow_state; Type: TABLE; Schema: auth; Owner: -
--

CREATE TABLE auth.flow_state (
    id uuid NOT NULL,
    user_id uuid,
    auth_code text NOT NULL,
    code_challenge_method auth.code_challenge_method NOT NULL,
    code_challenge text NOT NULL,
    provider_type text NOT NULL,
    provider_access_token text,
    provider_refresh_token text,
    created_at timestamp with time zone,
    updated_at timestamp with time zone,
    authentication_method text NOT NULL,
    auth_code_issued_at timestamp with time zone
);


--
-- Name: TABLE flow_state; Type: COMMENT; Schema: auth; Owner: -
--

COMMENT ON TABLE auth.flow_state IS 'stores metadata for pkce logins';


--
-- Name: identities; Type: TABLE; Schema: auth; Owner: -
--

CREATE TABLE auth.identities (
    provider_id text NOT NULL,
    user_id uuid NOT NULL,
    identity_data jsonb NOT NULL,
    provider text NOT NULL,
    last_sign_in_at timestamp with time zone,
    created_at timestamp with time zone,
    updated_at timestamp with time zone,
    email text GENERATED ALWAYS AS (lower((identity_data ->> 'email'::text))) STORED,
    id uuid DEFAULT gen_random_uuid() NOT NULL
);


--
-- Name: TABLE identities; Type: COMMENT; Schema: auth; Owner: -
--

COMMENT ON TABLE auth.identities IS 'Auth: Stores identities associated to a user.';


--
-- Name: COLUMN identities.email; Type: COMMENT; Schema: auth; Owner: -
--

COMMENT ON COLUMN auth.identities.email IS 'Auth: Email is a generated column that references the optional email property in the identity_data';


--
-- Name: instances; Type: TABLE; Schema: auth; Owner: -
--

CREATE TABLE auth.instances (
    id uuid NOT NULL,
    uuid uuid,
    raw_base_config text,
    created_at timestamp with time zone,
    updated_at timestamp with time zone
);


--
-- Name: TABLE instances; Type: COMMENT; Schema: auth; Owner: -
--

COMMENT ON TABLE auth.instances IS 'Auth: Manages users across multiple sites.';


--
-- Name: mfa_amr_claims; Type: TABLE; Schema: auth; Owner: -
--

CREATE TABLE auth.mfa_amr_claims (
    session_id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    authentication_method text NOT NULL,
    id uuid NOT NULL
);


--
-- Name: TABLE mfa_amr_claims; Type: COMMENT; Schema: auth; Owner: -
--

COMMENT ON TABLE auth.mfa_amr_claims IS 'auth: stores authenticator method reference claims for multi factor authentication';


--
-- Name: mfa_challenges; Type: TABLE; Schema: auth; Owner: -
--

CREATE TABLE auth.mfa_challenges (
    id uuid NOT NULL,
    factor_id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    verified_at timestamp with time zone,
    ip_address inet NOT NULL,
    otp_code text,
    web_authn_session_data jsonb
);


--
-- Name: TABLE mfa_challenges; Type: COMMENT; Schema: auth; Owner: -
--

COMMENT ON TABLE auth.mfa_challenges IS 'auth: stores metadata about challenge requests made';


--
-- Name: mfa_factors; Type: TABLE; Schema: auth; Owner: -
--

CREATE TABLE auth.mfa_factors (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    friendly_name text,
    factor_type auth.factor_type NOT NULL,
    status auth.factor_status NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    secret text,
    phone text,
    last_challenged_at timestamp with time zone,
    web_authn_credential jsonb,
    web_authn_aaguid uuid
);


--
-- Name: TABLE mfa_factors; Type: COMMENT; Schema: auth; Owner: -
--

COMMENT ON TABLE auth.mfa_factors IS 'auth: stores metadata about factors';


--
-- Name: one_time_tokens; Type: TABLE; Schema: auth; Owner: -
--

CREATE TABLE auth.one_time_tokens (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    token_type auth.one_time_token_type NOT NULL,
    token_hash text NOT NULL,
    relates_to text NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    CONSTRAINT one_time_tokens_token_hash_check CHECK ((char_length(token_hash) > 0))
);


--
-- Name: refresh_tokens; Type: TABLE; Schema: auth; Owner: -
--

CREATE TABLE auth.refresh_tokens (
    instance_id uuid,
    id bigint NOT NULL,
    token character varying(255),
    user_id character varying(255),
    revoked boolean,
    created_at timestamp with time zone,
    updated_at timestamp with time zone,
    parent character varying(255),
    session_id uuid
);


--
-- Name: TABLE refresh_tokens; Type: COMMENT; Schema: auth; Owner: -
--

COMMENT ON TABLE auth.refresh_tokens IS 'Auth: Store of tokens used to refresh JWT tokens once they expire.';


--
-- Name: refresh_tokens_id_seq; Type: SEQUENCE; Schema: auth; Owner: -
--

CREATE SEQUENCE auth.refresh_tokens_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: refresh_tokens_id_seq; Type: SEQUENCE OWNED BY; Schema: auth; Owner: -
--

ALTER SEQUENCE auth.refresh_tokens_id_seq OWNED BY auth.refresh_tokens.id;


--
-- Name: saml_providers; Type: TABLE; Schema: auth; Owner: -
--

CREATE TABLE auth.saml_providers (
    id uuid NOT NULL,
    sso_provider_id uuid NOT NULL,
    entity_id text NOT NULL,
    metadata_xml text NOT NULL,
    metadata_url text,
    attribute_mapping jsonb,
    created_at timestamp with time zone,
    updated_at timestamp with time zone,
    name_id_format text,
    CONSTRAINT "entity_id not empty" CHECK ((char_length(entity_id) > 0)),
    CONSTRAINT "metadata_url not empty" CHECK (((metadata_url = NULL::text) OR (char_length(metadata_url) > 0))),
    CONSTRAINT "metadata_xml not empty" CHECK ((char_length(metadata_xml) > 0))
);


--
-- Name: TABLE saml_providers; Type: COMMENT; Schema: auth; Owner: -
--

COMMENT ON TABLE auth.saml_providers IS 'Auth: Manages SAML Identity Provider connections.';


--
-- Name: saml_relay_states; Type: TABLE; Schema: auth; Owner: -
--

CREATE TABLE auth.saml_relay_states (
    id uuid NOT NULL,
    sso_provider_id uuid NOT NULL,
    request_id text NOT NULL,
    for_email text,
    redirect_to text,
    created_at timestamp with time zone,
    updated_at timestamp with time zone,
    flow_state_id uuid,
    CONSTRAINT "request_id not empty" CHECK ((char_length(request_id) > 0))
);


--
-- Name: TABLE saml_relay_states; Type: COMMENT; Schema: auth; Owner: -
--

COMMENT ON TABLE auth.saml_relay_states IS 'Auth: Contains SAML Relay State information for each Service Provider initiated login.';


--
-- Name: schema_migrations; Type: TABLE; Schema: auth; Owner: -
--

CREATE TABLE auth.schema_migrations (
    version character varying(255) NOT NULL
);


--
-- Name: TABLE schema_migrations; Type: COMMENT; Schema: auth; Owner: -
--

COMMENT ON TABLE auth.schema_migrations IS 'Auth: Manages updates to the auth system.';


--
-- Name: sessions; Type: TABLE; Schema: auth; Owner: -
--

CREATE TABLE auth.sessions (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    created_at timestamp with time zone,
    updated_at timestamp with time zone,
    factor_id uuid,
    aal auth.aal_level,
    not_after timestamp with time zone,
    refreshed_at timestamp without time zone,
    user_agent text,
    ip inet,
    tag text
);


--
-- Name: TABLE sessions; Type: COMMENT; Schema: auth; Owner: -
--

COMMENT ON TABLE auth.sessions IS 'Auth: Stores session data associated to a user.';


--
-- Name: COLUMN sessions.not_after; Type: COMMENT; Schema: auth; Owner: -
--

COMMENT ON COLUMN auth.sessions.not_after IS 'Auth: Not after is a nullable column that contains a timestamp after which the session should be regarded as expired.';


--
-- Name: sso_domains; Type: TABLE; Schema: auth; Owner: -
--

CREATE TABLE auth.sso_domains (
    id uuid NOT NULL,
    sso_provider_id uuid NOT NULL,
    domain text NOT NULL,
    created_at timestamp with time zone,
    updated_at timestamp with time zone,
    CONSTRAINT "domain not empty" CHECK ((char_length(domain) > 0))
);


--
-- Name: TABLE sso_domains; Type: COMMENT; Schema: auth; Owner: -
--

COMMENT ON TABLE auth.sso_domains IS 'Auth: Manages SSO email address domain mapping to an SSO Identity Provider.';


--
-- Name: sso_providers; Type: TABLE; Schema: auth; Owner: -
--

CREATE TABLE auth.sso_providers (
    id uuid NOT NULL,
    resource_id text,
    created_at timestamp with time zone,
    updated_at timestamp with time zone,
    CONSTRAINT "resource_id not empty" CHECK (((resource_id = NULL::text) OR (char_length(resource_id) > 0)))
);


--
-- Name: TABLE sso_providers; Type: COMMENT; Schema: auth; Owner: -
--

COMMENT ON TABLE auth.sso_providers IS 'Auth: Manages SSO identity provider information; see saml_providers for SAML.';


--
-- Name: COLUMN sso_providers.resource_id; Type: COMMENT; Schema: auth; Owner: -
--

COMMENT ON COLUMN auth.sso_providers.resource_id IS 'Auth: Uniquely identifies a SSO provider according to a user-chosen resource ID (case insensitive), useful in infrastructure as code.';


--
-- Name: users; Type: TABLE; Schema: auth; Owner: -
--

CREATE TABLE auth.users (
    instance_id uuid,
    id uuid NOT NULL,
    aud character varying(255),
    role character varying(255),
    email character varying(255),
    encrypted_password character varying(255),
    email_confirmed_at timestamp with time zone,
    invited_at timestamp with time zone,
    confirmation_token character varying(255),
    confirmation_sent_at timestamp with time zone,
    recovery_token character varying(255),
    recovery_sent_at timestamp with time zone,
    email_change_token_new character varying(255),
    email_change character varying(255),
    email_change_sent_at timestamp with time zone,
    last_sign_in_at timestamp with time zone,
    raw_app_meta_data jsonb,
    raw_user_meta_data jsonb,
    is_super_admin boolean,
    created_at timestamp with time zone,
    updated_at timestamp with time zone,
    phone text DEFAULT NULL::character varying,
    phone_confirmed_at timestamp with time zone,
    phone_change text DEFAULT ''::character varying,
    phone_change_token character varying(255) DEFAULT ''::character varying,
    phone_change_sent_at timestamp with time zone,
    confirmed_at timestamp with time zone GENERATED ALWAYS AS (LEAST(email_confirmed_at, phone_confirmed_at)) STORED,
    email_change_token_current character varying(255) DEFAULT ''::character varying,
    email_change_confirm_status smallint DEFAULT 0,
    banned_until timestamp with time zone,
    reauthentication_token character varying(255) DEFAULT ''::character varying,
    reauthentication_sent_at timestamp with time zone,
    is_sso_user boolean DEFAULT false NOT NULL,
    deleted_at timestamp with time zone,
    is_anonymous boolean DEFAULT false NOT NULL,
    CONSTRAINT users_email_change_confirm_status_check CHECK (((email_change_confirm_status >= 0) AND (email_change_confirm_status <= 2)))
);


--
-- Name: TABLE users; Type: COMMENT; Schema: auth; Owner: -
--

COMMENT ON TABLE auth.users IS 'Auth: Stores user login data within a secure schema.';


--
-- Name: COLUMN users.is_sso_user; Type: COMMENT; Schema: auth; Owner: -
--

COMMENT ON COLUMN auth.users.is_sso_user IS 'Auth: Set this column to true when the account comes from SSO. These accounts can have duplicate emails.';


--
-- Name: bot_configurations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.bot_configurations (
    id integer NOT NULL,
    watchlist_channel_id character varying,
    ta_channel_id character varying,
    log_channel_id text
);


--
-- Name: bot_configurations_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.bot_configurations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: bot_configurations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.bot_configurations_id_seq OWNED BY public.bot_configurations.id;


--
-- Name: conditional_role_grant_condition_roles; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.conditional_role_grant_condition_roles (
    conditional_role_grant_id integer NOT NULL,
    role_id integer NOT NULL
);


--
-- Name: conditional_role_grants; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.conditional_role_grants (
    id integer NOT NULL,
    guild_id character varying,
    grant_role_id character varying,
    exclude_role_id character varying
);


--
-- Name: conditional_role_grants_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.conditional_role_grants_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: conditional_role_grants_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.conditional_role_grants_id_seq OWNED BY public.conditional_role_grants.id;


--
-- Name: monthly_pl; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.monthly_pl (
    id integer NOT NULL,
    configuration_id integer,
    month date NOT NULL,
    regular_trades_pl numeric(15,2) DEFAULT 0 NOT NULL,
    strategy_trades_pl numeric(15,2) DEFAULT 0 NOT NULL,
    total_pl numeric(15,2) GENERATED ALWAYS AS ((regular_trades_pl + strategy_trades_pl)) STORED,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: monthly_pl_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.monthly_pl_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: monthly_pl_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.monthly_pl_id_seq OWNED BY public.monthly_pl.id;


--
-- Name: options_strategy_legs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.options_strategy_legs (
    strategy_leg_id character varying NOT NULL,
    strategy_id text NOT NULL,
    trade_id character varying NOT NULL,
    leg_sequence integer,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: TABLE options_strategy_legs; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.options_strategy_legs IS 'Created during Phase 1 Task 3 migration to normalize options strategy legs';


--
-- Name: options_strategy_trades; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.options_strategy_trades (
    strategy_id text NOT NULL,
    name character varying,
    underlying_symbol character varying,
    status character varying,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    closed_at timestamp without time zone,
    configuration_id integer,
    trade_group character varying,
    net_cost double precision NOT NULL,
    average_net_cost double precision NOT NULL,
    size character varying NOT NULL,
    current_size character varying NOT NULL,
    average_exit_cost double precision,
    win_loss text,
    profit_loss double precision,
    user_id character varying,
    legs text
);


--
-- Name: options_strategy_trades_legs_backup; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.options_strategy_trades_legs_backup (
    strategy_id text,
    legs text,
    backup_created_at timestamp without time zone
);


--
-- Name: TABLE options_strategy_trades_legs_backup; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.options_strategy_trades_legs_backup IS 'Backup of original legs data before Phase 1 Task 3 migration';


--
-- Name: options_strategy_transactions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.options_strategy_transactions (
    transaction_type character varying NOT NULL,
    net_cost double precision NOT NULL,
    size character varying NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    transaction_id text DEFAULT public.generate_options_strategy_id() NOT NULL,
    strategy_id text
);


--
-- Name: role_requirement_roles; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.role_requirement_roles (
    role_requirement_id integer NOT NULL,
    role_id integer NOT NULL
);


--
-- Name: role_requirements; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.role_requirements (
    id integer NOT NULL,
    guild_id character varying
);


--
-- Name: role_requirements_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.role_requirements_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: role_requirements_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.role_requirements_id_seq OWNED BY public.role_requirements.id;


--
-- Name: roles; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.roles (
    id integer NOT NULL,
    role_id character varying,
    guild_id character varying
);


--
-- Name: roles_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.roles_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: roles_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.roles_id_seq OWNED BY public.roles.id;


--
-- Name: trade_configurations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.trade_configurations (
    id integer NOT NULL,
    name character varying,
    channel_id character varying,
    role_id character varying,
    roadmap_channel_id character varying,
    update_channel_id character varying,
    portfolio_channel_id character varying,
    log_channel_id character varying
);


--
-- Name: trade_configurations_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.trade_configurations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: trade_configurations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.trade_configurations_id_seq OWNED BY public.trade_configurations.id;


--
-- Name: trade_statuses; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.trade_statuses (
    id integer NOT NULL,
    status_name character varying NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: trade_statuses_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.trade_statuses_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: trade_statuses_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.trade_statuses_id_seq OWNED BY public.trade_statuses.id;


--
-- Name: trade_types; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.trade_types (
    id integer NOT NULL,
    type_name character varying NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: trade_types_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.trade_types_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: trade_types_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.trade_types_id_seq OWNED BY public.trade_types.id;


--
-- Name: verification_configs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.verification_configs (
    id integer NOT NULL,
    message_id character varying,
    channel_id character varying,
    role_to_remove_id character varying,
    role_to_add_id character varying,
    log_channel_id character varying
);


--
-- Name: verification_configs_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.verification_configs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: verification_configs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.verification_configs_id_seq OWNED BY public.verification_configs.id;


--
-- Name: verifications; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.verifications (
    id integer NOT NULL,
    user_id character varying,
    username character varying,
    configuration_id integer,
    "timestamp" timestamp without time zone
);


--
-- Name: verifications_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.verifications_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: verifications_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.verifications_id_seq OWNED BY public.verifications.id;


--
-- Name: messages; Type: TABLE; Schema: realtime; Owner: -
--

CREATE TABLE realtime.messages (
    topic text NOT NULL,
    extension text NOT NULL,
    payload jsonb,
    event text,
    private boolean DEFAULT false,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    inserted_at timestamp without time zone DEFAULT now() NOT NULL,
    id uuid DEFAULT gen_random_uuid() NOT NULL
)
PARTITION BY RANGE (inserted_at);


--
-- Name: schema_migrations; Type: TABLE; Schema: realtime; Owner: -
--

CREATE TABLE realtime.schema_migrations (
    version bigint NOT NULL,
    inserted_at timestamp(0) without time zone
);


--
-- Name: subscription; Type: TABLE; Schema: realtime; Owner: -
--

CREATE TABLE realtime.subscription (
    id bigint NOT NULL,
    subscription_id uuid NOT NULL,
    entity regclass NOT NULL,
    filters realtime.user_defined_filter[] DEFAULT '{}'::realtime.user_defined_filter[] NOT NULL,
    claims jsonb NOT NULL,
    claims_role regrole GENERATED ALWAYS AS (realtime.to_regrole((claims ->> 'role'::text))) STORED NOT NULL,
    created_at timestamp without time zone DEFAULT timezone('utc'::text, now()) NOT NULL
);


--
-- Name: subscription_id_seq; Type: SEQUENCE; Schema: realtime; Owner: -
--

ALTER TABLE realtime.subscription ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME realtime.subscription_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: buckets; Type: TABLE; Schema: storage; Owner: -
--

CREATE TABLE storage.buckets (
    id text NOT NULL,
    name text NOT NULL,
    owner uuid,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    public boolean DEFAULT false,
    avif_autodetection boolean DEFAULT false,
    file_size_limit bigint,
    allowed_mime_types text[],
    owner_id text
);


--
-- Name: COLUMN buckets.owner; Type: COMMENT; Schema: storage; Owner: -
--

COMMENT ON COLUMN storage.buckets.owner IS 'Field is deprecated, use owner_id instead';


--
-- Name: migrations; Type: TABLE; Schema: storage; Owner: -
--

CREATE TABLE storage.migrations (
    id integer NOT NULL,
    name character varying(100) NOT NULL,
    hash character varying(40) NOT NULL,
    executed_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: objects; Type: TABLE; Schema: storage; Owner: -
--

CREATE TABLE storage.objects (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    bucket_id text,
    name text,
    owner uuid,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    last_accessed_at timestamp with time zone DEFAULT now(),
    metadata jsonb,
    path_tokens text[] GENERATED ALWAYS AS (string_to_array(name, '/'::text)) STORED,
    version text,
    owner_id text,
    user_metadata jsonb
);


--
-- Name: COLUMN objects.owner; Type: COMMENT; Schema: storage; Owner: -
--

COMMENT ON COLUMN storage.objects.owner IS 'Field is deprecated, use owner_id instead';


--
-- Name: s3_multipart_uploads; Type: TABLE; Schema: storage; Owner: -
--

CREATE TABLE storage.s3_multipart_uploads (
    id text NOT NULL,
    in_progress_size bigint DEFAULT 0 NOT NULL,
    upload_signature text NOT NULL,
    bucket_id text NOT NULL,
    key text NOT NULL COLLATE pg_catalog."C",
    version text NOT NULL,
    owner_id text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    user_metadata jsonb
);


--
-- Name: s3_multipart_uploads_parts; Type: TABLE; Schema: storage; Owner: -
--

CREATE TABLE storage.s3_multipart_uploads_parts (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    upload_id text NOT NULL,
    size bigint DEFAULT 0 NOT NULL,
    part_number integer NOT NULL,
    bucket_id text NOT NULL,
    key text NOT NULL COLLATE pg_catalog."C",
    etag text NOT NULL,
    owner_id text,
    version text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: schema_migrations; Type: TABLE; Schema: supabase_migrations; Owner: -
--

CREATE TABLE supabase_migrations.schema_migrations (
    version text NOT NULL,
    statements text[],
    name text
);


--
-- Name: seed_files; Type: TABLE; Schema: supabase_migrations; Owner: -
--

CREATE TABLE supabase_migrations.seed_files (
    path text NOT NULL,
    hash text NOT NULL
);


--
-- Name: refresh_tokens id; Type: DEFAULT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.refresh_tokens ALTER COLUMN id SET DEFAULT nextval('auth.refresh_tokens_id_seq'::regclass);


--
-- Name: bot_configurations id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.bot_configurations ALTER COLUMN id SET DEFAULT nextval('public.bot_configurations_id_seq'::regclass);


--
-- Name: conditional_role_grants id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.conditional_role_grants ALTER COLUMN id SET DEFAULT nextval('public.conditional_role_grants_id_seq'::regclass);


--
-- Name: monthly_pl id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monthly_pl ALTER COLUMN id SET DEFAULT nextval('public.monthly_pl_id_seq'::regclass);


--
-- Name: role_requirements id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.role_requirements ALTER COLUMN id SET DEFAULT nextval('public.role_requirements_id_seq'::regclass);


--
-- Name: roles id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.roles ALTER COLUMN id SET DEFAULT nextval('public.roles_id_seq'::regclass);


--
-- Name: trade_configurations id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.trade_configurations ALTER COLUMN id SET DEFAULT nextval('public.trade_configurations_id_seq'::regclass);


--
-- Name: trade_statuses id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.trade_statuses ALTER COLUMN id SET DEFAULT nextval('public.trade_statuses_id_seq'::regclass);


--
-- Name: trade_types id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.trade_types ALTER COLUMN id SET DEFAULT nextval('public.trade_types_id_seq'::regclass);


--
-- Name: verification_configs id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.verification_configs ALTER COLUMN id SET DEFAULT nextval('public.verification_configs_id_seq'::regclass);


--
-- Name: verifications id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.verifications ALTER COLUMN id SET DEFAULT nextval('public.verifications_id_seq'::regclass);


--
-- Name: mfa_amr_claims amr_id_pk; Type: CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.mfa_amr_claims
    ADD CONSTRAINT amr_id_pk PRIMARY KEY (id);


--
-- Name: audit_log_entries audit_log_entries_pkey; Type: CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.audit_log_entries
    ADD CONSTRAINT audit_log_entries_pkey PRIMARY KEY (id);


--
-- Name: flow_state flow_state_pkey; Type: CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.flow_state
    ADD CONSTRAINT flow_state_pkey PRIMARY KEY (id);


--
-- Name: identities identities_pkey; Type: CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.identities
    ADD CONSTRAINT identities_pkey PRIMARY KEY (id);


--
-- Name: identities identities_provider_id_provider_unique; Type: CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.identities
    ADD CONSTRAINT identities_provider_id_provider_unique UNIQUE (provider_id, provider);


--
-- Name: instances instances_pkey; Type: CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.instances
    ADD CONSTRAINT instances_pkey PRIMARY KEY (id);


--
-- Name: mfa_amr_claims mfa_amr_claims_session_id_authentication_method_pkey; Type: CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.mfa_amr_claims
    ADD CONSTRAINT mfa_amr_claims_session_id_authentication_method_pkey UNIQUE (session_id, authentication_method);


--
-- Name: mfa_challenges mfa_challenges_pkey; Type: CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.mfa_challenges
    ADD CONSTRAINT mfa_challenges_pkey PRIMARY KEY (id);


--
-- Name: mfa_factors mfa_factors_last_challenged_at_key; Type: CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.mfa_factors
    ADD CONSTRAINT mfa_factors_last_challenged_at_key UNIQUE (last_challenged_at);


--
-- Name: mfa_factors mfa_factors_pkey; Type: CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.mfa_factors
    ADD CONSTRAINT mfa_factors_pkey PRIMARY KEY (id);


--
-- Name: one_time_tokens one_time_tokens_pkey; Type: CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.one_time_tokens
    ADD CONSTRAINT one_time_tokens_pkey PRIMARY KEY (id);


--
-- Name: refresh_tokens refresh_tokens_pkey; Type: CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.refresh_tokens
    ADD CONSTRAINT refresh_tokens_pkey PRIMARY KEY (id);


--
-- Name: refresh_tokens refresh_tokens_token_unique; Type: CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.refresh_tokens
    ADD CONSTRAINT refresh_tokens_token_unique UNIQUE (token);


--
-- Name: saml_providers saml_providers_entity_id_key; Type: CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.saml_providers
    ADD CONSTRAINT saml_providers_entity_id_key UNIQUE (entity_id);


--
-- Name: saml_providers saml_providers_pkey; Type: CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.saml_providers
    ADD CONSTRAINT saml_providers_pkey PRIMARY KEY (id);


--
-- Name: saml_relay_states saml_relay_states_pkey; Type: CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.saml_relay_states
    ADD CONSTRAINT saml_relay_states_pkey PRIMARY KEY (id);


--
-- Name: schema_migrations schema_migrations_pkey; Type: CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.schema_migrations
    ADD CONSTRAINT schema_migrations_pkey PRIMARY KEY (version);


--
-- Name: sessions sessions_pkey; Type: CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.sessions
    ADD CONSTRAINT sessions_pkey PRIMARY KEY (id);


--
-- Name: sso_domains sso_domains_pkey; Type: CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.sso_domains
    ADD CONSTRAINT sso_domains_pkey PRIMARY KEY (id);


--
-- Name: sso_providers sso_providers_pkey; Type: CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.sso_providers
    ADD CONSTRAINT sso_providers_pkey PRIMARY KEY (id);


--
-- Name: users users_phone_key; Type: CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.users
    ADD CONSTRAINT users_phone_key UNIQUE (phone);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: bot_configurations bot_configurations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.bot_configurations
    ADD CONSTRAINT bot_configurations_pkey PRIMARY KEY (id);


--
-- Name: conditional_role_grant_condition_roles conditional_role_grant_condition_roles_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.conditional_role_grant_condition_roles
    ADD CONSTRAINT conditional_role_grant_condition_roles_pkey PRIMARY KEY (conditional_role_grant_id, role_id);


--
-- Name: conditional_role_grants conditional_role_grants_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.conditional_role_grants
    ADD CONSTRAINT conditional_role_grants_pkey PRIMARY KEY (id);


--
-- Name: monthly_pl monthly_pl_configuration_id_month_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monthly_pl
    ADD CONSTRAINT monthly_pl_configuration_id_month_key UNIQUE (configuration_id, month);


--
-- Name: monthly_pl monthly_pl_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monthly_pl
    ADD CONSTRAINT monthly_pl_pkey PRIMARY KEY (id);


--
-- Name: options_strategy_legs options_strategy_legs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.options_strategy_legs
    ADD CONSTRAINT options_strategy_legs_pkey PRIMARY KEY (strategy_leg_id);


--
-- Name: options_strategy_trades options_strategy_trades_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.options_strategy_trades
    ADD CONSTRAINT options_strategy_trades_pkey PRIMARY KEY (strategy_id);


--
-- Name: options_strategy_trades options_strategy_trades_trade_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.options_strategy_trades
    ADD CONSTRAINT options_strategy_trades_trade_id_key UNIQUE (strategy_id);


--
-- Name: options_strategy_transactions options_strategy_transactions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.options_strategy_transactions
    ADD CONSTRAINT options_strategy_transactions_pkey PRIMARY KEY (transaction_id);


--
-- Name: role_requirement_roles role_requirement_roles_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.role_requirement_roles
    ADD CONSTRAINT role_requirement_roles_pkey PRIMARY KEY (role_requirement_id, role_id);


--
-- Name: role_requirements role_requirements_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.role_requirements
    ADD CONSTRAINT role_requirements_pkey PRIMARY KEY (id);


--
-- Name: roles roles_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.roles
    ADD CONSTRAINT roles_pkey PRIMARY KEY (id);


--
-- Name: roles roles_role_id_guild_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.roles
    ADD CONSTRAINT roles_role_id_guild_id_key UNIQUE (role_id, guild_id);


--
-- Name: trade_configurations trade_configurations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.trade_configurations
    ADD CONSTRAINT trade_configurations_pkey PRIMARY KEY (id);


--
-- Name: trade_statuses trade_statuses_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.trade_statuses
    ADD CONSTRAINT trade_statuses_pkey PRIMARY KEY (id);


--
-- Name: trade_statuses trade_statuses_status_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.trade_statuses
    ADD CONSTRAINT trade_statuses_status_name_key UNIQUE (status_name);


--
-- Name: trade_types trade_types_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.trade_types
    ADD CONSTRAINT trade_types_pkey PRIMARY KEY (id);


--
-- Name: trade_types trade_types_type_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.trade_types
    ADD CONSTRAINT trade_types_type_name_key UNIQUE (type_name);


--
-- Name: trades trades_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.trades
    ADD CONSTRAINT trades_pkey PRIMARY KEY (trade_id);


--
-- Name: transactions transactions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.transactions
    ADD CONSTRAINT transactions_pkey PRIMARY KEY (id);


--
-- Name: verification_configs verification_configs_message_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.verification_configs
    ADD CONSTRAINT verification_configs_message_id_key UNIQUE (message_id);


--
-- Name: verification_configs verification_configs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.verification_configs
    ADD CONSTRAINT verification_configs_pkey PRIMARY KEY (id);


--
-- Name: verifications verifications_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.verifications
    ADD CONSTRAINT verifications_pkey PRIMARY KEY (id);


--
-- Name: verifications verifications_user_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.verifications
    ADD CONSTRAINT verifications_user_id_key UNIQUE (user_id);


--
-- Name: messages messages_pkey; Type: CONSTRAINT; Schema: realtime; Owner: -
--

ALTER TABLE ONLY realtime.messages
    ADD CONSTRAINT messages_pkey PRIMARY KEY (id, inserted_at);


--
-- Name: subscription pk_subscription; Type: CONSTRAINT; Schema: realtime; Owner: -
--

ALTER TABLE ONLY realtime.subscription
    ADD CONSTRAINT pk_subscription PRIMARY KEY (id);


--
-- Name: schema_migrations schema_migrations_pkey; Type: CONSTRAINT; Schema: realtime; Owner: -
--

ALTER TABLE ONLY realtime.schema_migrations
    ADD CONSTRAINT schema_migrations_pkey PRIMARY KEY (version);


--
-- Name: buckets buckets_pkey; Type: CONSTRAINT; Schema: storage; Owner: -
--

ALTER TABLE ONLY storage.buckets
    ADD CONSTRAINT buckets_pkey PRIMARY KEY (id);


--
-- Name: migrations migrations_name_key; Type: CONSTRAINT; Schema: storage; Owner: -
--

ALTER TABLE ONLY storage.migrations
    ADD CONSTRAINT migrations_name_key UNIQUE (name);


--
-- Name: migrations migrations_pkey; Type: CONSTRAINT; Schema: storage; Owner: -
--

ALTER TABLE ONLY storage.migrations
    ADD CONSTRAINT migrations_pkey PRIMARY KEY (id);


--
-- Name: objects objects_pkey; Type: CONSTRAINT; Schema: storage; Owner: -
--

ALTER TABLE ONLY storage.objects
    ADD CONSTRAINT objects_pkey PRIMARY KEY (id);


--
-- Name: s3_multipart_uploads_parts s3_multipart_uploads_parts_pkey; Type: CONSTRAINT; Schema: storage; Owner: -
--

ALTER TABLE ONLY storage.s3_multipart_uploads_parts
    ADD CONSTRAINT s3_multipart_uploads_parts_pkey PRIMARY KEY (id);


--
-- Name: s3_multipart_uploads s3_multipart_uploads_pkey; Type: CONSTRAINT; Schema: storage; Owner: -
--

ALTER TABLE ONLY storage.s3_multipart_uploads
    ADD CONSTRAINT s3_multipart_uploads_pkey PRIMARY KEY (id);


--
-- Name: schema_migrations schema_migrations_pkey; Type: CONSTRAINT; Schema: supabase_migrations; Owner: -
--

ALTER TABLE ONLY supabase_migrations.schema_migrations
    ADD CONSTRAINT schema_migrations_pkey PRIMARY KEY (version);


--
-- Name: seed_files seed_files_pkey; Type: CONSTRAINT; Schema: supabase_migrations; Owner: -
--

ALTER TABLE ONLY supabase_migrations.seed_files
    ADD CONSTRAINT seed_files_pkey PRIMARY KEY (path);


--
-- Name: audit_logs_instance_id_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX audit_logs_instance_id_idx ON auth.audit_log_entries USING btree (instance_id);


--
-- Name: confirmation_token_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE UNIQUE INDEX confirmation_token_idx ON auth.users USING btree (confirmation_token) WHERE ((confirmation_token)::text !~ '^[0-9 ]*$'::text);


--
-- Name: email_change_token_current_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE UNIQUE INDEX email_change_token_current_idx ON auth.users USING btree (email_change_token_current) WHERE ((email_change_token_current)::text !~ '^[0-9 ]*$'::text);


--
-- Name: email_change_token_new_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE UNIQUE INDEX email_change_token_new_idx ON auth.users USING btree (email_change_token_new) WHERE ((email_change_token_new)::text !~ '^[0-9 ]*$'::text);


--
-- Name: factor_id_created_at_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX factor_id_created_at_idx ON auth.mfa_factors USING btree (user_id, created_at);


--
-- Name: flow_state_created_at_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX flow_state_created_at_idx ON auth.flow_state USING btree (created_at DESC);


--
-- Name: identities_email_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX identities_email_idx ON auth.identities USING btree (email text_pattern_ops);


--
-- Name: INDEX identities_email_idx; Type: COMMENT; Schema: auth; Owner: -
--

COMMENT ON INDEX auth.identities_email_idx IS 'Auth: Ensures indexed queries on the email column';


--
-- Name: identities_user_id_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX identities_user_id_idx ON auth.identities USING btree (user_id);


--
-- Name: idx_auth_code; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX idx_auth_code ON auth.flow_state USING btree (auth_code);


--
-- Name: idx_user_id_auth_method; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX idx_user_id_auth_method ON auth.flow_state USING btree (user_id, authentication_method);


--
-- Name: mfa_challenge_created_at_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX mfa_challenge_created_at_idx ON auth.mfa_challenges USING btree (created_at DESC);


--
-- Name: mfa_factors_user_friendly_name_unique; Type: INDEX; Schema: auth; Owner: -
--

CREATE UNIQUE INDEX mfa_factors_user_friendly_name_unique ON auth.mfa_factors USING btree (friendly_name, user_id) WHERE (TRIM(BOTH FROM friendly_name) <> ''::text);


--
-- Name: mfa_factors_user_id_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX mfa_factors_user_id_idx ON auth.mfa_factors USING btree (user_id);


--
-- Name: one_time_tokens_relates_to_hash_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX one_time_tokens_relates_to_hash_idx ON auth.one_time_tokens USING hash (relates_to);


--
-- Name: one_time_tokens_token_hash_hash_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX one_time_tokens_token_hash_hash_idx ON auth.one_time_tokens USING hash (token_hash);


--
-- Name: one_time_tokens_user_id_token_type_key; Type: INDEX; Schema: auth; Owner: -
--

CREATE UNIQUE INDEX one_time_tokens_user_id_token_type_key ON auth.one_time_tokens USING btree (user_id, token_type);


--
-- Name: reauthentication_token_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE UNIQUE INDEX reauthentication_token_idx ON auth.users USING btree (reauthentication_token) WHERE ((reauthentication_token)::text !~ '^[0-9 ]*$'::text);


--
-- Name: recovery_token_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE UNIQUE INDEX recovery_token_idx ON auth.users USING btree (recovery_token) WHERE ((recovery_token)::text !~ '^[0-9 ]*$'::text);


--
-- Name: refresh_tokens_instance_id_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX refresh_tokens_instance_id_idx ON auth.refresh_tokens USING btree (instance_id);


--
-- Name: refresh_tokens_instance_id_user_id_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX refresh_tokens_instance_id_user_id_idx ON auth.refresh_tokens USING btree (instance_id, user_id);


--
-- Name: refresh_tokens_parent_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX refresh_tokens_parent_idx ON auth.refresh_tokens USING btree (parent);


--
-- Name: refresh_tokens_session_id_revoked_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX refresh_tokens_session_id_revoked_idx ON auth.refresh_tokens USING btree (session_id, revoked);


--
-- Name: refresh_tokens_updated_at_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX refresh_tokens_updated_at_idx ON auth.refresh_tokens USING btree (updated_at DESC);


--
-- Name: saml_providers_sso_provider_id_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX saml_providers_sso_provider_id_idx ON auth.saml_providers USING btree (sso_provider_id);


--
-- Name: saml_relay_states_created_at_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX saml_relay_states_created_at_idx ON auth.saml_relay_states USING btree (created_at DESC);


--
-- Name: saml_relay_states_for_email_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX saml_relay_states_for_email_idx ON auth.saml_relay_states USING btree (for_email);


--
-- Name: saml_relay_states_sso_provider_id_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX saml_relay_states_sso_provider_id_idx ON auth.saml_relay_states USING btree (sso_provider_id);


--
-- Name: sessions_not_after_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX sessions_not_after_idx ON auth.sessions USING btree (not_after DESC);


--
-- Name: sessions_user_id_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX sessions_user_id_idx ON auth.sessions USING btree (user_id);


--
-- Name: sso_domains_domain_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE UNIQUE INDEX sso_domains_domain_idx ON auth.sso_domains USING btree (lower(domain));


--
-- Name: sso_domains_sso_provider_id_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX sso_domains_sso_provider_id_idx ON auth.sso_domains USING btree (sso_provider_id);


--
-- Name: sso_providers_resource_id_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE UNIQUE INDEX sso_providers_resource_id_idx ON auth.sso_providers USING btree (lower(resource_id));


--
-- Name: unique_phone_factor_per_user; Type: INDEX; Schema: auth; Owner: -
--

CREATE UNIQUE INDEX unique_phone_factor_per_user ON auth.mfa_factors USING btree (user_id, phone);


--
-- Name: user_id_created_at_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX user_id_created_at_idx ON auth.sessions USING btree (user_id, created_at);


--
-- Name: users_email_partial_key; Type: INDEX; Schema: auth; Owner: -
--

CREATE UNIQUE INDEX users_email_partial_key ON auth.users USING btree (email) WHERE (is_sso_user = false);


--
-- Name: INDEX users_email_partial_key; Type: COMMENT; Schema: auth; Owner: -
--

COMMENT ON INDEX auth.users_email_partial_key IS 'Auth: A partial unique index that applies only when is_sso_user is false';


--
-- Name: users_instance_id_email_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX users_instance_id_email_idx ON auth.users USING btree (instance_id, lower((email)::text));


--
-- Name: users_instance_id_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX users_instance_id_idx ON auth.users USING btree (instance_id);


--
-- Name: users_is_anonymous_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX users_is_anonymous_idx ON auth.users USING btree (is_anonymous);


--
-- Name: idx_options_strategy_legs_strategy_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_options_strategy_legs_strategy_id ON public.options_strategy_legs USING btree (strategy_id);


--
-- Name: idx_options_strategy_legs_trade_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_options_strategy_legs_trade_id ON public.options_strategy_legs USING btree (trade_id);


--
-- Name: idx_options_strategy_trades_underlying; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_options_strategy_trades_underlying ON public.options_strategy_trades USING btree (underlying_symbol);


--
-- Name: idx_trades_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_trades_created_at ON public.trades USING btree (created_at);


--
-- Name: idx_trades_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_trades_status ON public.trades USING btree (status);


--
-- Name: idx_trades_symbol; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_trades_symbol ON public.trades USING btree (symbol);


--
-- Name: idx_verifications_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_verifications_user_id ON public.verifications USING btree (user_id);


--
-- Name: ix_realtime_subscription_entity; Type: INDEX; Schema: realtime; Owner: -
--

CREATE INDEX ix_realtime_subscription_entity ON realtime.subscription USING btree (entity);


--
-- Name: subscription_subscription_id_entity_filters_key; Type: INDEX; Schema: realtime; Owner: -
--

CREATE UNIQUE INDEX subscription_subscription_id_entity_filters_key ON realtime.subscription USING btree (subscription_id, entity, filters);


--
-- Name: bname; Type: INDEX; Schema: storage; Owner: -
--

CREATE UNIQUE INDEX bname ON storage.buckets USING btree (name);


--
-- Name: bucketid_objname; Type: INDEX; Schema: storage; Owner: -
--

CREATE UNIQUE INDEX bucketid_objname ON storage.objects USING btree (bucket_id, name);


--
-- Name: idx_multipart_uploads_list; Type: INDEX; Schema: storage; Owner: -
--

CREATE INDEX idx_multipart_uploads_list ON storage.s3_multipart_uploads USING btree (bucket_id, key, created_at);


--
-- Name: idx_objects_bucket_id_name; Type: INDEX; Schema: storage; Owner: -
--

CREATE INDEX idx_objects_bucket_id_name ON storage.objects USING btree (bucket_id, name COLLATE "C");


--
-- Name: name_prefix_search; Type: INDEX; Schema: storage; Owner: -
--

CREATE INDEX name_prefix_search ON storage.objects USING btree (name text_pattern_ops);


--
-- Name: options_strategy_transactions options_strategy_transaction_before_change; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER options_strategy_transaction_before_change BEFORE INSERT OR DELETE OR UPDATE ON public.options_strategy_transactions FOR EACH ROW EXECUTE FUNCTION public.update_options_strategy_before_transaction_change();


--
-- Name: options_strategy_trades set_options_strategy_trade_id; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER set_options_strategy_trade_id BEFORE INSERT ON public.options_strategy_trades FOR EACH ROW EXECUTE FUNCTION public.set_options_strategy_trade_id();


--
-- Name: options_strategy_transactions set_options_strategy_transaction_id; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER set_options_strategy_transaction_id BEFORE INSERT ON public.options_strategy_transactions FOR EACH ROW EXECUTE FUNCTION public.set_options_strategy_transaction_id();


--
-- Name: transactions transaction_before_delete; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER transaction_before_delete BEFORE DELETE ON public.transactions FOR EACH ROW EXECUTE FUNCTION public.update_trade_before_transaction_change();


--
-- Name: transactions transaction_before_insert_update; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER transaction_before_insert_update BEFORE INSERT OR UPDATE ON public.transactions FOR EACH ROW EXECUTE FUNCTION public.update_trade_before_transaction_change();


--
-- Name: subscription tr_check_filters; Type: TRIGGER; Schema: realtime; Owner: -
--

CREATE TRIGGER tr_check_filters BEFORE INSERT OR UPDATE ON realtime.subscription FOR EACH ROW EXECUTE FUNCTION realtime.subscription_check_filters();


--
-- Name: objects update_objects_updated_at; Type: TRIGGER; Schema: storage; Owner: -
--

CREATE TRIGGER update_objects_updated_at BEFORE UPDATE ON storage.objects FOR EACH ROW EXECUTE FUNCTION storage.update_updated_at_column();


--
-- Name: identities identities_user_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.identities
    ADD CONSTRAINT identities_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;


--
-- Name: mfa_amr_claims mfa_amr_claims_session_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.mfa_amr_claims
    ADD CONSTRAINT mfa_amr_claims_session_id_fkey FOREIGN KEY (session_id) REFERENCES auth.sessions(id) ON DELETE CASCADE;


--
-- Name: mfa_challenges mfa_challenges_auth_factor_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.mfa_challenges
    ADD CONSTRAINT mfa_challenges_auth_factor_id_fkey FOREIGN KEY (factor_id) REFERENCES auth.mfa_factors(id) ON DELETE CASCADE;


--
-- Name: mfa_factors mfa_factors_user_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.mfa_factors
    ADD CONSTRAINT mfa_factors_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;


--
-- Name: one_time_tokens one_time_tokens_user_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.one_time_tokens
    ADD CONSTRAINT one_time_tokens_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;


--
-- Name: refresh_tokens refresh_tokens_session_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.refresh_tokens
    ADD CONSTRAINT refresh_tokens_session_id_fkey FOREIGN KEY (session_id) REFERENCES auth.sessions(id) ON DELETE CASCADE;


--
-- Name: saml_providers saml_providers_sso_provider_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.saml_providers
    ADD CONSTRAINT saml_providers_sso_provider_id_fkey FOREIGN KEY (sso_provider_id) REFERENCES auth.sso_providers(id) ON DELETE CASCADE;


--
-- Name: saml_relay_states saml_relay_states_flow_state_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.saml_relay_states
    ADD CONSTRAINT saml_relay_states_flow_state_id_fkey FOREIGN KEY (flow_state_id) REFERENCES auth.flow_state(id) ON DELETE CASCADE;


--
-- Name: saml_relay_states saml_relay_states_sso_provider_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.saml_relay_states
    ADD CONSTRAINT saml_relay_states_sso_provider_id_fkey FOREIGN KEY (sso_provider_id) REFERENCES auth.sso_providers(id) ON DELETE CASCADE;


--
-- Name: sessions sessions_user_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.sessions
    ADD CONSTRAINT sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;


--
-- Name: sso_domains sso_domains_sso_provider_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.sso_domains
    ADD CONSTRAINT sso_domains_sso_provider_id_fkey FOREIGN KEY (sso_provider_id) REFERENCES auth.sso_providers(id) ON DELETE CASCADE;


--
-- Name: conditional_role_grant_condition_roles conditional_role_grant_condition_conditional_role_grant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.conditional_role_grant_condition_roles
    ADD CONSTRAINT conditional_role_grant_condition_conditional_role_grant_id_fkey FOREIGN KEY (conditional_role_grant_id) REFERENCES public.conditional_role_grants(id);


--
-- Name: conditional_role_grant_condition_roles conditional_role_grant_condition_roles_role_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.conditional_role_grant_condition_roles
    ADD CONSTRAINT conditional_role_grant_condition_roles_role_id_fkey FOREIGN KEY (role_id) REFERENCES public.roles(id);


--
-- Name: options_strategy_legs fk_options_strategy; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.options_strategy_legs
    ADD CONSTRAINT fk_options_strategy FOREIGN KEY (strategy_id) REFERENCES public.options_strategy_trades(strategy_id) ON DELETE CASCADE;


--
-- Name: options_strategy_legs fk_trade_leg; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.options_strategy_legs
    ADD CONSTRAINT fk_trade_leg FOREIGN KEY (trade_id) REFERENCES public.trades(trade_id) ON DELETE CASCADE;


--
-- Name: monthly_pl monthly_pl_configuration_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.monthly_pl
    ADD CONSTRAINT monthly_pl_configuration_id_fkey FOREIGN KEY (configuration_id) REFERENCES public.trade_configurations(id);


--
-- Name: options_strategy_trades options_strategy_trades_configuration_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.options_strategy_trades
    ADD CONSTRAINT options_strategy_trades_configuration_id_fkey FOREIGN KEY (configuration_id) REFERENCES public.trade_configurations(id);


--
-- Name: options_strategy_transactions options_strategy_transactions_strategy_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.options_strategy_transactions
    ADD CONSTRAINT options_strategy_transactions_strategy_id_fkey FOREIGN KEY (strategy_id) REFERENCES public.options_strategy_trades(strategy_id) ON DELETE CASCADE;


--
-- Name: role_requirement_roles role_requirement_roles_role_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.role_requirement_roles
    ADD CONSTRAINT role_requirement_roles_role_id_fkey FOREIGN KEY (role_id) REFERENCES public.roles(id);


--
-- Name: role_requirement_roles role_requirement_roles_role_requirement_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.role_requirement_roles
    ADD CONSTRAINT role_requirement_roles_role_requirement_id_fkey FOREIGN KEY (role_requirement_id) REFERENCES public.role_requirements(id);


--
-- Name: trades trades_configuration_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.trades
    ADD CONSTRAINT trades_configuration_id_fkey FOREIGN KEY (configuration_id) REFERENCES public.trade_configurations(id);


--
-- Name: transactions transactions_trade_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.transactions
    ADD CONSTRAINT transactions_trade_id_fkey FOREIGN KEY (trade_id) REFERENCES public.trades(trade_id);


--
-- Name: verifications verifications_configuration_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.verifications
    ADD CONSTRAINT verifications_configuration_id_fkey FOREIGN KEY (configuration_id) REFERENCES public.verification_configs(id);


--
-- Name: objects objects_bucketId_fkey; Type: FK CONSTRAINT; Schema: storage; Owner: -
--

ALTER TABLE ONLY storage.objects
    ADD CONSTRAINT "objects_bucketId_fkey" FOREIGN KEY (bucket_id) REFERENCES storage.buckets(id);


--
-- Name: s3_multipart_uploads s3_multipart_uploads_bucket_id_fkey; Type: FK CONSTRAINT; Schema: storage; Owner: -
--

ALTER TABLE ONLY storage.s3_multipart_uploads
    ADD CONSTRAINT s3_multipart_uploads_bucket_id_fkey FOREIGN KEY (bucket_id) REFERENCES storage.buckets(id);


--
-- Name: s3_multipart_uploads_parts s3_multipart_uploads_parts_bucket_id_fkey; Type: FK CONSTRAINT; Schema: storage; Owner: -
--

ALTER TABLE ONLY storage.s3_multipart_uploads_parts
    ADD CONSTRAINT s3_multipart_uploads_parts_bucket_id_fkey FOREIGN KEY (bucket_id) REFERENCES storage.buckets(id);


--
-- Name: s3_multipart_uploads_parts s3_multipart_uploads_parts_upload_id_fkey; Type: FK CONSTRAINT; Schema: storage; Owner: -
--

ALTER TABLE ONLY storage.s3_multipart_uploads_parts
    ADD CONSTRAINT s3_multipart_uploads_parts_upload_id_fkey FOREIGN KEY (upload_id) REFERENCES storage.s3_multipart_uploads(id) ON DELETE CASCADE;


--
-- Name: audit_log_entries; Type: ROW SECURITY; Schema: auth; Owner: -
--

ALTER TABLE auth.audit_log_entries ENABLE ROW LEVEL SECURITY;

--
-- Name: flow_state; Type: ROW SECURITY; Schema: auth; Owner: -
--

ALTER TABLE auth.flow_state ENABLE ROW LEVEL SECURITY;

--
-- Name: identities; Type: ROW SECURITY; Schema: auth; Owner: -
--

ALTER TABLE auth.identities ENABLE ROW LEVEL SECURITY;

--
-- Name: instances; Type: ROW SECURITY; Schema: auth; Owner: -
--

ALTER TABLE auth.instances ENABLE ROW LEVEL SECURITY;

--
-- Name: mfa_amr_claims; Type: ROW SECURITY; Schema: auth; Owner: -
--

ALTER TABLE auth.mfa_amr_claims ENABLE ROW LEVEL SECURITY;

--
-- Name: mfa_challenges; Type: ROW SECURITY; Schema: auth; Owner: -
--

ALTER TABLE auth.mfa_challenges ENABLE ROW LEVEL SECURITY;

--
-- Name: mfa_factors; Type: ROW SECURITY; Schema: auth; Owner: -
--

ALTER TABLE auth.mfa_factors ENABLE ROW LEVEL SECURITY;

--
-- Name: one_time_tokens; Type: ROW SECURITY; Schema: auth; Owner: -
--

ALTER TABLE auth.one_time_tokens ENABLE ROW LEVEL SECURITY;

--
-- Name: refresh_tokens; Type: ROW SECURITY; Schema: auth; Owner: -
--

ALTER TABLE auth.refresh_tokens ENABLE ROW LEVEL SECURITY;

--
-- Name: saml_providers; Type: ROW SECURITY; Schema: auth; Owner: -
--

ALTER TABLE auth.saml_providers ENABLE ROW LEVEL SECURITY;

--
-- Name: saml_relay_states; Type: ROW SECURITY; Schema: auth; Owner: -
--

ALTER TABLE auth.saml_relay_states ENABLE ROW LEVEL SECURITY;

--
-- Name: schema_migrations; Type: ROW SECURITY; Schema: auth; Owner: -
--

ALTER TABLE auth.schema_migrations ENABLE ROW LEVEL SECURITY;

--
-- Name: sessions; Type: ROW SECURITY; Schema: auth; Owner: -
--

ALTER TABLE auth.sessions ENABLE ROW LEVEL SECURITY;

--
-- Name: sso_domains; Type: ROW SECURITY; Schema: auth; Owner: -
--

ALTER TABLE auth.sso_domains ENABLE ROW LEVEL SECURITY;

--
-- Name: sso_providers; Type: ROW SECURITY; Schema: auth; Owner: -
--

ALTER TABLE auth.sso_providers ENABLE ROW LEVEL SECURITY;

--
-- Name: users; Type: ROW SECURITY; Schema: auth; Owner: -
--

ALTER TABLE auth.users ENABLE ROW LEVEL SECURITY;

--
-- Name: messages; Type: ROW SECURITY; Schema: realtime; Owner: -
--

ALTER TABLE realtime.messages ENABLE ROW LEVEL SECURITY;

--
-- Name: buckets; Type: ROW SECURITY; Schema: storage; Owner: -
--

ALTER TABLE storage.buckets ENABLE ROW LEVEL SECURITY;

--
-- Name: migrations; Type: ROW SECURITY; Schema: storage; Owner: -
--

ALTER TABLE storage.migrations ENABLE ROW LEVEL SECURITY;

--
-- Name: objects; Type: ROW SECURITY; Schema: storage; Owner: -
--

ALTER TABLE storage.objects ENABLE ROW LEVEL SECURITY;

--
-- Name: s3_multipart_uploads; Type: ROW SECURITY; Schema: storage; Owner: -
--

ALTER TABLE storage.s3_multipart_uploads ENABLE ROW LEVEL SECURITY;

--
-- Name: s3_multipart_uploads_parts; Type: ROW SECURITY; Schema: storage; Owner: -
--

ALTER TABLE storage.s3_multipart_uploads_parts ENABLE ROW LEVEL SECURITY;

--
-- Name: supabase_realtime; Type: PUBLICATION; Schema: -; Owner: -
--

CREATE PUBLICATION supabase_realtime WITH (publish = 'insert, update, delete, truncate');


--
-- Name: issue_graphql_placeholder; Type: EVENT TRIGGER; Schema: -; Owner: -
--

CREATE EVENT TRIGGER issue_graphql_placeholder ON sql_drop
         WHEN TAG IN ('DROP EXTENSION')
   EXECUTE FUNCTION extensions.set_graphql_placeholder();


--
-- Name: issue_pg_cron_access; Type: EVENT TRIGGER; Schema: -; Owner: -
--

CREATE EVENT TRIGGER issue_pg_cron_access ON ddl_command_end
         WHEN TAG IN ('CREATE EXTENSION')
   EXECUTE FUNCTION extensions.grant_pg_cron_access();


--
-- Name: issue_pg_graphql_access; Type: EVENT TRIGGER; Schema: -; Owner: -
--

CREATE EVENT TRIGGER issue_pg_graphql_access ON ddl_command_end
         WHEN TAG IN ('CREATE FUNCTION')
   EXECUTE FUNCTION extensions.grant_pg_graphql_access();


--
-- Name: issue_pg_net_access; Type: EVENT TRIGGER; Schema: -; Owner: -
--

CREATE EVENT TRIGGER issue_pg_net_access ON ddl_command_end
         WHEN TAG IN ('CREATE EXTENSION')
   EXECUTE FUNCTION extensions.grant_pg_net_access();


--
-- Name: pgrst_ddl_watch; Type: EVENT TRIGGER; Schema: -; Owner: -
--

CREATE EVENT TRIGGER pgrst_ddl_watch ON ddl_command_end
   EXECUTE FUNCTION extensions.pgrst_ddl_watch();


--
-- Name: pgrst_drop_watch; Type: EVENT TRIGGER; Schema: -; Owner: -
--

CREATE EVENT TRIGGER pgrst_drop_watch ON sql_drop
   EXECUTE FUNCTION extensions.pgrst_drop_watch();


--
-- PostgreSQL database dump complete
--

