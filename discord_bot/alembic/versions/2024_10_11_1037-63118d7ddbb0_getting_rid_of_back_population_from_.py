"""Getting rid of back population from trades to OS

Revision ID: 63118d7ddbb0
Revises: 88f55205a3ff
Create Date: 2024-10-11 10:37:47.776288

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector


# revision identifiers, used by Alembic.
revision: str = '63118d7ddbb0'
down_revision: Union[str, None] = '88f55205a3ff'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create a new table without the strategy_trade_id column
    op.execute("""
    CREATE TABLE trades_new (
        trade_id VARCHAR NOT NULL, 
        symbol VARCHAR NOT NULL, 
        trade_type VARCHAR NOT NULL, 
        status VARCHAR NOT NULL, 
        entry_price FLOAT NOT NULL, 
        average_price FLOAT, 
        current_size VARCHAR, 
        size VARCHAR NOT NULL, 
        created_at DATETIME NOT NULL, 
        closed_at DATETIME, 
        exit_price FLOAT, 
        average_exit_price FLOAT, 
        profit_loss FLOAT, 
        risk_reward_ratio FLOAT, 
        win_loss VARCHAR, 
        configuration_id VARCHAR, 
        is_contract BOOLEAN, 
        is_day_trade BOOLEAN, 
        strike FLOAT, 
        expiration_date DATETIME, 
        option_type VARCHAR,
        PRIMARY KEY (trade_id),
        FOREIGN KEY(configuration_id) REFERENCES trade_configurations (id)
    )
    """)

    # Copy data from the old table to the new one
    op.execute("""
    INSERT INTO trades_new SELECT
        trade_id, symbol, trade_type, status, entry_price, average_price,
        current_size, size, created_at, closed_at, exit_price, average_exit_price,
        profit_loss, risk_reward_ratio, win_loss, configuration_id, is_contract,
        is_day_trade, strike, expiration_date, option_type
    FROM trades
    """)

    # Drop the old table
    op.drop_table('trades')

    # Rename the new table to the original name
    op.rename_table('trades_new', 'trades')


def downgrade() -> None:
    # Create a new table with the strategy_trade_id column
    op.execute("""
    CREATE TABLE trades_old (
        trade_id VARCHAR NOT NULL, 
        symbol VARCHAR NOT NULL, 
        trade_type VARCHAR NOT NULL, 
        status VARCHAR NOT NULL, 
        entry_price FLOAT NOT NULL, 
        average_price FLOAT, 
        current_size VARCHAR, 
        size VARCHAR NOT NULL, 
        created_at DATETIME NOT NULL, 
        closed_at DATETIME, 
        exit_price FLOAT, 
        average_exit_price FLOAT, 
        profit_loss FLOAT, 
        risk_reward_ratio FLOAT, 
        win_loss VARCHAR, 
        configuration_id VARCHAR, 
        is_contract BOOLEAN, 
        is_day_trade BOOLEAN, 
        strike FLOAT, 
        expiration_date DATETIME, 
        option_type VARCHAR,
        strategy_trade_id INTEGER,
        PRIMARY KEY (trade_id),
        FOREIGN KEY(configuration_id) REFERENCES trade_configurations (id),
        FOREIGN KEY(strategy_trade_id) REFERENCES options_strategy_trades (id)
    )
    """)

    # Copy data from the current table to the new one
    op.execute("""
    INSERT INTO trades_old SELECT
        trade_id, symbol, trade_type, status, entry_price, average_price,
        current_size, size, created_at, closed_at, exit_price, average_exit_price,
        profit_loss, risk_reward_ratio, win_loss, configuration_id, is_contract,
        is_day_trade, strike, expiration_date, option_type, NULL
    FROM trades
    """)

    # Drop the current table
    op.drop_table('trades')

    # Rename the new table to the original name
    op.rename_table('trades_old', 'trades')
