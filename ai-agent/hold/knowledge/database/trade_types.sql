CREATE TABLE public.trade_types (
    id integer NOT NULL,
    type_name character varying NOT NULL ('BTO', 'STO'),
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);
