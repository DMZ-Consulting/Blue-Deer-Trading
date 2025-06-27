CREATE TABLE public.verifications (
    id integer NOT NULL,
    user_id character varying,
    username character varying,
    configuration_id integer,
    "timestamp" timestamp without time zone
);
