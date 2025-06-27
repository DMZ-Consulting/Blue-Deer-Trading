CREATE TABLE public.verification_configs (
    id integer NOT NULL,
    message_id character varying,
    channel_id character varying,
    role_to_remove_id character varying,
    role_to_add_id character varying,
    log_channel_id character varying
);
