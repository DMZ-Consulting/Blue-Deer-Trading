-- Phase 1, Task 3: Data Migration Strategy - Schema Changes
-- This migration adds the new schema elements needed for the data migration

-- Step 1: Add user_id columns to existing tables
ALTER TABLE public.trades
ADD COLUMN user_id character varying NULL;

ALTER TABLE public.options_strategy_trades
ADD COLUMN user_id character varying NULL;

-- Step 2: Create the new options_strategy_legs table
CREATE TABLE public.options_strategy_legs (
    strategy_leg_id character varying NOT NULL PRIMARY KEY,
    strategy_id text NOT NULL,
    trade_id character varying NOT NULL,
    leg_sequence integer NULL, -- To maintain order of legs within a strategy
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_options_strategy
        FOREIGN KEY (strategy_id)
        REFERENCES public.options_strategy_trades (strategy_id)
        ON DELETE CASCADE, -- If a strategy is deleted, its legs links are also deleted
    CONSTRAINT fk_trade_leg
        FOREIGN KEY (trade_id)
        REFERENCES public.trades (trade_id)
        ON DELETE CASCADE -- If a trade (leg) is deleted, its strategy link is also deleted
) TABLESPACE pg_default;

-- Add indexes for foreign keys
CREATE INDEX IF NOT EXISTS idx_options_strategy_legs_strategy_id 
ON public.options_strategy_legs USING btree (strategy_id) TABLESPACE pg_default;

CREATE INDEX IF NOT EXISTS idx_options_strategy_legs_trade_id 
ON public.options_strategy_legs USING btree (trade_id) TABLESPACE pg_default;

-- Step 3: Create lookup tables for trade types and statuses (optional but recommended)
CREATE TABLE public.trade_types (
    id SERIAL PRIMARY KEY,
    type_name character varying NOT NULL UNIQUE,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
) TABLESPACE pg_default;

CREATE TABLE public.trade_statuses (
    id SERIAL PRIMARY KEY,
    status_name character varying NOT NULL UNIQUE,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
) TABLESPACE pg_default;

-- Populate lookup tables with existing values
INSERT INTO public.trade_types (type_name)
SELECT DISTINCT trade_type FROM public.trades
WHERE trade_type IS NOT NULL
ON CONFLICT (type_name) DO NOTHING;

INSERT INTO public.trade_statuses (status_name)
SELECT DISTINCT status FROM public.trades
WHERE status IS NOT NULL
ON CONFLICT (status_name) DO NOTHING;

-- Add common trade types and statuses if not present
INSERT INTO public.trade_types (type_name) VALUES 
    ('Option'),
    ('Stock'),
    ('common')
ON CONFLICT (type_name) DO NOTHING;

INSERT INTO public.trade_statuses (status_name) VALUES 
    ('OPEN'),
    ('CLOSED'),
    ('pending'),
    ('in-progress'),
    ('review'),
    ('deferred'),
    ('cancelled')
ON CONFLICT (status_name) DO NOTHING;

-- Create a function to generate UUIDs for strategy_leg_id
CREATE OR REPLACE FUNCTION public.generate_strategy_leg_id() RETURNS text
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN 'leg_' || EXTRACT(EPOCH FROM CURRENT_TIMESTAMP)::BIGINT || '_' || FLOOR(RANDOM() * 1000)::TEXT;
END;
$$;

-- Create a backup table for the original legs data (for rollback purposes)
CREATE TABLE public.options_strategy_trades_legs_backup AS
SELECT strategy_id, legs, created_at as backup_created_at
FROM public.options_strategy_trades
WHERE legs IS NOT NULL AND legs != '';

-- Add a comment to track migration
COMMENT ON TABLE public.options_strategy_legs IS 'Created during Phase 1 Task 3 migration to normalize options strategy legs';
COMMENT ON TABLE public.options_strategy_trades_legs_backup IS 'Backup of original legs data before Phase 1 Task 3 migration'; 