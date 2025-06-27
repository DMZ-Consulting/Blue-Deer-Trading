CREATE TABLE public.options_strategy_trades (
    strategy_id text NOT NULL,
    name character varying,
    underlying_symbol character varying,
    status character varying ('OPEN', 'CLOSED'),
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    closed_at timestamp without time zone,
    configuration_id integer,
    trade_group character varying,
    net_cost double precision NOT NULL,
    average_net_cost double precision NOT NULL,
    size character varying NOT NULL,
    current_size character varying NOT NULL,
    average_exit_cost double precision,
    win_loss text ('WIN', 'LOSS'),
    profit_loss double precision,
    user_id character varying,
    legs text
);
