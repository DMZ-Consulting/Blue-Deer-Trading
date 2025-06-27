CREATE TABLE public.options_strategy_transactions (
    transaction_type character varying NOT NULL ('OPEN', 'ADD', 'CLOSE', 'TRIM'),
    net_cost double precision NOT NULL,
    size character varying NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    transaction_id text DEFAULT public.generate_options_strategy_id() NOT NULL,
    strategy_id text
);
