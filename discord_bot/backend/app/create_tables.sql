-- Trade Configurations
CREATE TABLE IF NOT EXISTS trade_configurations (
    id SERIAL PRIMARY KEY,
    name VARCHAR,
    channel_id VARCHAR,
    role_id VARCHAR,
    roadmap_channel_id VARCHAR,
    update_channel_id VARCHAR,
    portfolio_channel_id VARCHAR,
    log_channel_id VARCHAR
);

-- Bot Configurations
CREATE TABLE IF NOT EXISTS bot_configurations (
    id SERIAL PRIMARY KEY,
    watchlist_channel_id VARCHAR,
    ta_channel_id VARCHAR
);

-- Roles
CREATE TABLE IF NOT EXISTS roles (
    id SERIAL PRIMARY KEY,
    role_id VARCHAR,
    guild_id VARCHAR,
    UNIQUE(role_id, guild_id)
);

-- Role Requirements
CREATE TABLE IF NOT EXISTS role_requirements (
    id SERIAL PRIMARY KEY,
    guild_id VARCHAR
);

-- Role Requirement Roles (Junction Table)
CREATE TABLE IF NOT EXISTS role_requirement_roles (
    role_requirement_id INTEGER REFERENCES role_requirements(id),
    role_id INTEGER REFERENCES roles(id),
    PRIMARY KEY (role_requirement_id, role_id)
);

-- Conditional Role Grants
CREATE TABLE IF NOT EXISTS conditional_role_grants (
    id SERIAL PRIMARY KEY,
    guild_id VARCHAR,
    grant_role_id VARCHAR,
    exclude_role_id VARCHAR
);

-- Conditional Role Grant Condition Roles (Junction Table)
CREATE TABLE IF NOT EXISTS conditional_role_grant_condition_roles (
    conditional_role_grant_id INTEGER REFERENCES conditional_role_grants(id),
    role_id INTEGER REFERENCES roles(id),
    PRIMARY KEY (conditional_role_grant_id, role_id)
);

-- Verification Configs
CREATE TABLE IF NOT EXISTS verification_configs (
    id SERIAL PRIMARY KEY,
    message_id VARCHAR UNIQUE,
    channel_id VARCHAR,
    role_to_remove_id VARCHAR,
    role_to_add_id VARCHAR,
    log_channel_id VARCHAR,
    terms_of_service_link VARCHAR,
);

-- User Verification Status
-- THIS IS NEW FOR SUPABASE
-- MUST BE IMPLEMENTED IN DISCORD BOT
CREATE TABLE IF NOT EXISTS user_verification_status (
    id SERIAL PRIMARY KEY,
    discord_id VARCHAR,
    discord_username VARCHAR,
    email VARCHAR,
    full_name VARCHAR,
    verification_status VARCHAR,
    configuration_id INTEGER REFERENCES verification_configs(id),
    verified_at TIMESTAMP,
    UNIQUE(discord_id)
);

-- Verifications
CREATE TABLE IF NOT EXISTS verifications (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR,
    username VARCHAR,
    configuration_id INTEGER REFERENCES verification_configs(id),
    timestamp TIMESTAMP,
    UNIQUE(user_id)
);

-- Options Strategy Trades
CREATE TABLE IF NOT EXISTS options_strategy_trades (
    id SERIAL PRIMARY KEY,
    trade_id VARCHAR UNIQUE,
    name VARCHAR,
    underlying_symbol VARCHAR,
    status VARCHAR,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    closed_at TIMESTAMP,
    configuration_id INTEGER REFERENCES trade_configurations(id),
    trade_group VARCHAR,
    legs TEXT NOT NULL,
    net_cost FLOAT NOT NULL,
    average_net_cost FLOAT NOT NULL,
    size VARCHAR NOT NULL,
    current_size VARCHAR NOT NULL
);

-- Trades
CREATE TABLE IF NOT EXISTS trades (
    trade_id VARCHAR PRIMARY KEY,
    symbol VARCHAR NOT NULL,
    trade_type VARCHAR NOT NULL,
    status VARCHAR NOT NULL,
    entry_price FLOAT NOT NULL,
    average_price FLOAT,
    current_size VARCHAR,
    size VARCHAR NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    closed_at TIMESTAMP,
    exit_price FLOAT,
    average_exit_price FLOAT,
    profit_loss FLOAT,
    risk_reward_ratio FLOAT,
    win_loss VARCHAR,
    configuration_id INTEGER REFERENCES trade_configurations(id),
    is_contract BOOLEAN DEFAULT FALSE,
    is_day_trade BOOLEAN DEFAULT FALSE,
    strike FLOAT,
    expiration_date TIMESTAMP,
    option_type VARCHAR
);

-- Transactions
CREATE TABLE IF NOT EXISTS transactions (
    id VARCHAR PRIMARY KEY,
    trade_id VARCHAR REFERENCES trades(trade_id),
    transaction_type VARCHAR,
    amount FLOAT,
    size VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Options Strategy Transactions
CREATE TABLE IF NOT EXISTS options_strategy_transactions (
    id SERIAL PRIMARY KEY,
    strategy_id INTEGER REFERENCES options_strategy_trades(id),
    transaction_type VARCHAR NOT NULL,
    net_cost FLOAT NOT NULL,
    size VARCHAR NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for frequently queried columns
CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol);
CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status);
CREATE INDEX IF NOT EXISTS idx_trades_created_at ON trades(created_at);
CREATE INDEX IF NOT EXISTS idx_verifications_user_id ON verifications(user_id);
CREATE INDEX IF NOT EXISTS idx_options_strategy_trades_underlying ON options_strategy_trades(underlying_symbol);