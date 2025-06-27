CREATE TABLE public.trade_statuses (
    id integer NOT NULL,
    status_name character varying NOT NULL ('OPEN', 'CLOSED'),
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);
