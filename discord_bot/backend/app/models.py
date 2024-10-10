import enum
from datetime import datetime

import shortuuid
from sqlalchemy import (Boolean, Column, DateTime, Float, ForeignKey,
                        Integer, String, Table, TypeDecorator)
from sqlalchemy.orm import relationship

from .database import Base
from .enum_type import EnumType

# Add this import at the top
from sqlalchemy import Column, ForeignKey, String, Table

import logging
from pydantic import field_validator


# Define a named ENUM type
class TradeStatusEnum(enum.Enum):
    OPEN = "open"
    CLOSED = "closed"
    CANCELLED = "cancelled"

# Add this new enum
class OptionsStrategyStatusEnum(str, enum.Enum):
    OPEN = "open"
    CLOSED = "closed"
    CANCELLED = "cancelled"

class WinLossEnum(enum.Enum):
    WIN = "win"
    LOSS = "loss"
    BREAKEVEN = "breakeven"

class TransactionTypeEnum(enum.Enum):
    OPEN = "open"
    CLOSE = "close"
    ADD = "add"
    TRIM = "trim"

class Trade(Base):
    __tablename__ = "trades"

    trade_id = Column(String, primary_key=True, unique=True, index=True, nullable=False, default=lambda: shortuuid.uuid()[:8])
    symbol = Column(String, index=True, nullable=False)
    trade_type = Column(String, nullable=False)
    status = Column(EnumType(TradeStatusEnum), nullable=False)
    entry_price = Column(Float, nullable=False)
    average_price = Column(Float, nullable=True)
    current_size = Column(String, nullable=True)
    size = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    closed_at = Column(DateTime, nullable=True)
    exit_price = Column(Float, nullable=True)
    average_exit_price = Column(Float, nullable=True)
    profit_loss = Column(Float, nullable=True)
    risk_reward_ratio = Column(Float, nullable=True)
    win_loss = Column(EnumType(WinLossEnum), nullable=True)
    transactions = relationship("Transaction", back_populates="trade")
    configuration_id = Column(String, ForeignKey("trade_configurations.id"), nullable=True)
    configuration = relationship("TradeConfiguration")
    strategy_trade_id = Column(Integer, ForeignKey("options_strategy_trades.id"), nullable=True)
    strategy = relationship("OptionsStrategyTrade", back_populates="legs")
    is_contract = Column(Boolean, default=False)
    is_day_trade = Column(Boolean, default=False)
    strike = Column(Float, nullable=True)
    expiration_date = Column(DateTime, nullable=True)
    option_type = Column(String, nullable=True)

    @field_validator('current_size', mode='before')
    @classmethod
    def validate_current_size(cls, v):
        if isinstance(v, float):
            return str(v)
        return v

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(String, primary_key=True, unique=True, index=True, nullable=False, default=lambda: shortuuid.uuid()[:8])
    trade_id = Column(String, ForeignKey("trades.trade_id"))
    transaction_type = Column(EnumType(TransactionTypeEnum))
    amount = Column(Float)
    size = Column(String)  # Add this line
    created_at = Column(DateTime, default=datetime.utcnow)

    trade = relationship("Trade", back_populates="transactions")


# Add this new model
class TradeConfiguration(Base):
    __tablename__ = "trade_configurations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    channel_id = Column(String)
    role_id = Column(String)
    roadmap_channel_id = Column(String)
    update_channel_id = Column(String)
    portfolio_channel_id = Column(String)
    log_channel_id = Column(String)  # Add this line

class OptionsStrategyTrade(Base):
    __tablename__ = "options_strategy_trades"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    underlying_symbol = Column(String, index=True)
    status = Column(EnumType(OptionsStrategyStatusEnum))
    created_at = Column(DateTime, default=datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)
    configuration_id = Column(Integer, ForeignKey("trade_configurations.id"))
    trade_group = Column(String, nullable=True)  # Added this line
    
    # Relationship to individual trades (legs)
    legs = relationship("Trade", back_populates="strategy")
    configuration = relationship("TradeConfiguration")

# Add this to your existing models.py file
class VerificationConfig(Base):
    __tablename__ = "verification_configs"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(String, unique=True, index=True)
    channel_id = Column(String)
    role_to_remove_id = Column(String)
    role_to_add_id = Column(String)
    log_channel_id = Column(String)

class Verification(Base):
    __tablename__ = "verifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    username = Column(String)
    configuration_id = Column(Integer, ForeignKey("verification_configs.id"))
    timestamp = Column(DateTime)

from sqlalchemy import Column, ForeignKey, Integer, String, Table
from sqlalchemy.orm import relationship

from .database import Base


class RoleRequirement(Base):
    __tablename__ = "role_requirements"

    id = Column(Integer, primary_key=True, index=True)
    guild_id = Column(String, index=True)
    required_roles = relationship("Role", secondary="role_requirement_roles")

class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    role_id = Column(String, index=True)
    guild_id = Column(String, index=True)

class ConditionalRoleGrant(Base):
    __tablename__ = "conditional_role_grants"

    id = Column(Integer, primary_key=True, index=True)
    guild_id = Column(String, index=True)
    condition_roles = relationship("Role", secondary="conditional_role_grant_condition_roles")
    grant_role_id = Column(String)
    exclude_role_id = Column(String)

role_requirement_roles = Table('role_requirement_roles', Base.metadata,
    Column('role_requirement_id', Integer, ForeignKey('role_requirements.id')),
    Column('role_id', Integer, ForeignKey('roles.id'))
)

conditional_role_grant_condition_roles = Table('conditional_role_grant_condition_roles', Base.metadata,
    Column('conditional_role_grant_id', Integer, ForeignKey('conditional_role_grants.id')),
    Column('role_id', Integer, ForeignKey('roles.id'))
)

class BotConfiguration(Base):
    __tablename__ = "bot_configurations"

    id = Column(Integer, primary_key=True, index=True)
    watchlist_channel_id = Column(String)
    ta_channel_id = Column(String)

# Add this function at the end of the file
def create_tables(engine):
    Base.metadata.create_all(bind=engine)

# After all your model definitions
logging.info(f"Models defined: {', '.join(Base.metadata.tables.keys())}")


class EnumType(TypeDecorator):
    impl = String
    cache_ok = True

    def __init__(self, enum_class):
        super().__init__()
        self.enum_class = enum_class

    def process_bind_param(self, value, dialect):
        if isinstance(value, str):
            return value
        return value.value if value else None

    def process_result_value(self, value, dialect):
        return self.enum_class(value) if value else None

