from pydantic import BaseModel, ConfigDict, validator, field_validator
from datetime import datetime
from typing import List, Optional
from .models import TradeStatusEnum, WinLossEnum, TransactionTypeEnum, OptionsStrategyStatusEnum

model_config = ConfigDict(from_attributes=True)

class TransactionBase(BaseModel):
    transaction_type: TransactionTypeEnum
    amount: float
    size: str
    created_at: datetime

class TransactionCreate(TransactionBase):
    pass

class Transaction(TransactionBase):
    id: str
    trade_id: str

    model_config = model_config

class TradeBase(BaseModel):
    symbol: str
    trade_type: str
    entry_price: float
    size: str
    current_size: Optional[str] = None
    is_contract: bool = False
    is_day_trade: bool = False
    strike: Optional[float] = None
    expiration_date: Optional[datetime] = None
    option_type: Optional[str] = None

    @field_validator('current_size', mode='before')
    @classmethod
    def validate_current_size(cls, v):
        if isinstance(v, float):
            return str(v)
        return v

class TradeCreate(TradeBase):
    is_contract: Optional[bool] = False

class Trade(TradeBase):
    trade_id: str
    status: TradeStatusEnum
    average_price: Optional[float]
    created_at: datetime
    closed_at: Optional[datetime]
    exit_price: Optional[float]
    average_exit_price: Optional[float]
    profit_loss: Optional[float]
    risk_reward_ratio: Optional[float]
    win_loss: Optional[WinLossEnum]
    transactions: List[Transaction]
    configuration_id: Optional[str]
    strategy_trade_id: Optional[int]

    model_config = ConfigDict(from_attributes=True)

class StrategyTradeBase(BaseModel):
    name: str
    underlying_symbol: str
    status: OptionsStrategyStatusEnum
    trade_group: Optional[str] = None

class StrategyTradeCreate(StrategyTradeBase):
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class StrategyTrade(StrategyTradeBase):
    id: int
    created_at: datetime
    closed_at: Optional[datetime]
    configuration_id: Optional[int]
    legs: List[Trade]

    model_config = model_config

class Performance(BaseModel):
    total_trades: int
    total_profit_loss: float
    win_rate: float
    average_risk_reward_ratio: float