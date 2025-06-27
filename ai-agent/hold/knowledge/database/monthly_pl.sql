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
