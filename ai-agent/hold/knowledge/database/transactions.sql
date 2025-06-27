CREATE TABLE public.transactions (
    id character varying NOT NULL,
    trade_id character varying,
    transaction_type character varying ('OPEN', 'ADD', 'CLOSE', 'TRIM'),
    amount double precision,
    size character varying,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);
