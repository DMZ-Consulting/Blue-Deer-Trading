from sqlalchemy.orm import Session
from sqlalchemy import func
from . import models, schemas
from typing import List
from .schemas import TransactionTypeEnum

def get_trades(db: Session, status: models.TradeStatusEnum = None, skip: int = 0, limit: int = 100):
    query = db.query(models.Trade)
    if status is not None:
        query = query.filter(models.Trade.status == status)
    trades = query.offset(skip).limit(limit).all()
    
    # Ensure enum values are properly converted
    for trade in trades:
        trade.status = models.TradeStatusEnum(trade.status)
        if trade.win_loss:
            trade.win_loss = models.WinLossEnum(trade.win_loss)
        for transaction in trade.transactions:
            transaction.transaction_type = models.TransactionTypeEnum(transaction.transaction_type)
    
    return trades

def get_trade(db: Session, trade_id: str):
    return db.query(models.Trade).filter(models.Trade.trade_id == trade_id).first()

def get_trade_transactions(db: Session, trade_id: str):
    return db.query(models.Transaction).filter(models.Transaction.trade_id == trade_id).all()

def get_performance(db: Session):
    total_trades = db.query(models.Trade).count()
    total_profit_loss = db.query(func.sum(models.Trade.profit_loss)).scalar() or 0
    win_rate = db.query(models.Trade).filter(models.Trade.win_loss == "win").count() / total_trades if total_trades > 0 else 0
    average_risk_reward_ratio = db.query(func.avg(models.Trade.risk_reward_ratio)).scalar() or 0

    return schemas.Performance(
        total_trades=total_trades,
        total_profit_loss=total_profit_loss,
        win_rate=win_rate,
        average_risk_reward_ratio=average_risk_reward_ratio
    )

def get_transactions_for_trade(db: Session, trade_id: str, transaction_types: List[TransactionTypeEnum] = None):
    query = db.query(models.Transaction).filter(models.Transaction.trade_id == trade_id)
    if transaction_types:
        query = query.filter(models.Transaction.transaction_type.in_(transaction_types))
    return query.all()