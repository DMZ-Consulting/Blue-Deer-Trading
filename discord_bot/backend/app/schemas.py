from pydantic import BaseModel, ConfigDict, field_validator
from datetime import datetime
from typing import Any, List, Optional, Union, Dict
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
    configuration_id: Optional[str]
    pass

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

    model_config = model_config

class OptionsStrategyTransactionBase(BaseModel):
    transaction_type: TransactionTypeEnum
    net_cost: float
    size: str
    created_at: datetime

class OptionsStrategyTransaction(OptionsStrategyTransactionBase):
    id: Union[str, int]
    strategy_id: Union[str, int]

    model_config = model_config

class OptionsStrategyTrade(BaseModel):
    id: Union[str, int]
    trade_id: str
    name: str
    underlying_symbol: str
    status: OptionsStrategyStatusEnum
    created_at: datetime
    closed_at: Optional[datetime]
    configuration_id: Union[str, int]
    trade_group: Optional[str]
    legs: str
    net_cost: float
    average_net_cost: float
    size: str
    current_size: str
    transactions: List["OptionsStrategyTransaction"]

    @field_validator('id', 'configuration_id', 'trade_id', mode='before')
    @classmethod
    def convert_ids_to_str(cls, v):
        return str(v) if v is not None else None

    model_config = model_config

class PortfolioTradeBase(BaseModel):
    oneliner: str
    realized_pl: float
    realized_size: float
    avg_entry_price: float
    avg_exit_price: float
    pct_change: float
    trade_type: str

class RegularPortfolioTrade(PortfolioTradeBase):
    trade: Trade
    model_config = model_config

class StrategyPortfolioTrade(PortfolioTradeBase):
    trade: OptionsStrategyTrade
    model_config = model_config

PortfolioTrade = Union[RegularPortfolioTrade, StrategyPortfolioTrade]

class OptionsStrategyTradeBase(BaseModel):
    name: str
    underlying_symbol: str
    status: OptionsStrategyStatusEnum
    trade_group: Optional[str] = None
    net_cost: float
    average_net_cost: float
    size: str
    current_size: str
    legs: str  # This will be a JSON string
    configuration_id: Optional[int]

class OptionsStrategyTradeCreate(OptionsStrategyTradeBase):
    pass

class Performance(BaseModel):
    total_trades: int
    total_profit_loss: float
    win_rate: float
    average_risk_reward_ratio: float
