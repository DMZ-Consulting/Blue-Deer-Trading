from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional
from .models import TradeStatusEnum, WinLossEnum, TransactionTypeEnum

class TransactionBase(BaseModel):
    transaction_type: TransactionTypeEnum
    amount: float
    size: str
    created_at: datetime

class TransactionCreate(TransactionBase):
    pass

class Transaction(TransactionBase):
    id: int
    trade_id: str

    class Config:
        orm_mode = True

class TradeBase(BaseModel):
    symbol: str
    trade_type: str
    entry_price: float
    current_size: str

class TradeCreate(TradeBase):
    pass

class Trade(TradeBase):
    trade_id: str
    status: TradeStatusEnum
    created_at: datetime
    closed_at: Optional[datetime]
    exit_price: Optional[float]
    profit_loss: Optional[float]
    risk_reward_ratio: Optional[float]
    win_loss: Optional[WinLossEnum]
    transactions: List[Transaction]

    class Config:
        orm_mode = True

class Performance(BaseModel):
    total_trades: int
    total_profit_loss: float
    win_rate: float
    average_risk_reward_ratio: float