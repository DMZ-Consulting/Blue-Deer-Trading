-- Create enum types
CREATE TYPE trade_status AS ENUM ('open', 'closed', 'cancelled');
CREATE TYPE transaction_type AS ENUM ('open', 'close', 'adjustment');

-- Create options strategy trades table
CREATE TABLE IF NOT EXISTS options_strategy_trades (
    strategy_id TEXT PRIMARY KEY DEFAULT generate_options_strategy_trade_id(),
    user_id TEXT NOT NULL,
    ticker TEXT NOT NULL,
    strategy_type TEXT NOT NULL,
    status trade_status NOT NULL DEFAULT 'open',
    start_date TIMESTAMP WITH TIME ZONE,
    end_date TIMESTAMP WITH TIME ZONE,
    profit_loss DECIMAL,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create options strategy transactions table
CREATE TABLE IF NOT EXISTS options_strategy_transactions (
    transaction_id TEXT PRIMARY KEY DEFAULT generate_options_strategy_transaction_id(),
    strategy_id TEXT REFERENCES options_strategy_trades(strategy_id) ON DELETE CASCADE,
    transaction_type transaction_type NOT NULL,
    transaction_date TIMESTAMP WITH TIME ZONE NOT NULL,
    strike_price DECIMAL NOT NULL,
    expiration_date DATE NOT NULL,
    premium DECIMAL NOT NULL,
    contracts INTEGER NOT NULL,
    option_type TEXT NOT NULL,
    side TEXT NOT NULL,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create trigger function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for both tables
CREATE TRIGGER update_options_strategy_trades_updated_at
    BEFORE UPDATE ON options_strategy_trades
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_options_strategy_transactions_updated_at
    BEFORE UPDATE ON options_strategy_transactions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column(); 