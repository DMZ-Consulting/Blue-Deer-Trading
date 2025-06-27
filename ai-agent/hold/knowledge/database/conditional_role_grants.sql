CREATE TABLE public.conditional_role_grants (
    id integer NOT NULL,
    guild_id character varying,
    grant_role_id character varying,
    exclude_role_id character varying
);
