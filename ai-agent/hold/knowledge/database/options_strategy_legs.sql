CREATE TABLE public.options_strategy_legs (
    strategy_leg_id character varying NOT NULL,
    strategy_id text NOT NULL,
    trade_id character varying NOT NULL,
    leg_sequence integer,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);
