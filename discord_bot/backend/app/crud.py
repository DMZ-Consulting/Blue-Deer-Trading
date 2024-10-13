from sqlalchemy.orm import Session
from sqlalchemy import func
from . import models, schemas
from typing import List, Optional
from .schemas import TransactionTypeEnum
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, field_validator
import logging

class TradeInput(BaseModel):
    symbol: str
    trade_type: str
    entry_price: float
    size: str
    expiration_date: Optional[str] = None
    strike: Optional[float] = None
    note: Optional[str] = None

    @field_validator('expiration_date')
    def validate_expiration_date(cls, v):
        if v:
            try:
                datetime.strptime(v, "%m/%d/%y")
            except ValueError:
                raise ValueError("Incorrect date format, should be MM/DD/YY")
        return v

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

def get_os_trades(db: Session, status: models.TradeStatusEnum = None, skip: int = 0, limit: int = 100):
    query = db.query(models.OptionsStrategyTrade)
    if status is not None:
        query = query.filter(models.OptionsStrategyTrade.status == status)
    
    trades = query.offset(skip).limit(limit).all()

    # ensure enum values are properly converted
    for trade in trades:
        trade.status = models.OptionsStrategyStatusEnum(trade.status)
        for transaction in trade.transactions:
            transaction.transaction_type = models.TransactionTypeEnum(transaction.transaction_type)

    return trades

def get_trade(db: Session, trade_id: str):
    logging.info(f"Attempting to retrieve trade with ID: {trade_id}")
    trade = db.query(models.Trade).filter(models.Trade.trade_id == trade_id).first()
    if trade:
        logging.info(f"Trade found: {trade.trade_id}")
    else:
        logging.warning(f"Trade not found: {trade_id}")
    return trade

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

def bto_trade(db: Session, trade_input: TradeInput):
    trade_group = determine_trade_group(trade_input.expiration_date, "bto")
    config = get_configuration(db, trade_group)
    if not config:
        raise ValueError(f"No configuration found for trade group: {trade_group}")

    new_trade = models.Trade(
        symbol=trade_input.symbol,
        trade_type="Buy to Open",
        status=models.TradeStatusEnum.OPEN,
        entry_price=trade_input.entry_price,
        average_price=trade_input.entry_price,
        size=trade_input.size,
        current_size=trade_input.size,
        created_at=datetime.utcnow(),
        configuration_id=config.id,
        is_contract=trade_input.expiration_date is not None,
        strike=trade_input.strike,
        expiration_date=datetime.strptime(trade_input.expiration_date, "%m/%d/%y") if trade_input.expiration_date else None,
    )
    db.add(new_trade)
    db.commit()
    db.refresh(new_trade)

    new_transaction = models.Transaction(
        trade_id=new_trade.trade_id,
        transaction_type=models.TransactionTypeEnum.OPEN,
        amount=trade_input.entry_price,
        size=trade_input.size,
        created_at=datetime.utcnow()
    )
    db.add(new_transaction)
    db.commit()

    return new_trade

def sto_trade(db: Session, trade_input: TradeInput):
    trade_group = determine_trade_group(trade_input.expiration_date, "sto")
    config = get_configuration(db, trade_group)
    if not config:
        raise ValueError(f"No configuration found for trade group: {trade_group}")

    new_trade = models.Trade(
        symbol=trade_input.symbol,
        trade_type="Sell to Open",
        status=models.TradeStatusEnum.OPEN,
        entry_price=trade_input.entry_price,
        average_price=trade_input.entry_price,
        size=trade_input.size,
        current_size=trade_input.size,
        created_at=datetime.utcnow(),
        configuration_id=config.id,
        is_contract=trade_input.expiration_date is not None,
        strike=trade_input.strike,
        expiration_date=datetime.strptime(trade_input.expiration_date, "%m/%d/%y") if trade_input.expiration_date else None,
    )
    db.add(new_trade)
    db.commit()
    db.refresh(new_trade)

    new_transaction = models.Transaction(
        trade_id=new_trade.trade_id,
        transaction_type=models.TransactionTypeEnum.OPEN,
        amount=trade_input.entry_price,
        size=trade_input.size,
        created_at=datetime.utcnow()
    )
    db.add(new_transaction)
    db.commit()

    return new_trade

class OptionsStrategyInput(BaseModel):
    strategy_name: str
    underlying_symbol: str
    legs: List[TradeInput]
    note: Optional[str] = None

def options_strategy(db: Session, strategy_input: OptionsStrategyInput):
    strategy_trade = models.StrategyTrade(
        name=strategy_input.strategy_name,
        underlying_symbol=strategy_input.underlying_symbol,
        created_at=datetime.utcnow(),
        note=strategy_input.note
    )
    db.add(strategy_trade)
    db.commit()
    db.refresh(strategy_trade)

    for leg in strategy_input.legs:
        trade_group = determine_trade_group(leg.expiration_date, leg.trade_type)
        config = get_configuration(db, trade_group)
        if not config:
            raise ValueError(f"No configuration found for trade group: {trade_group}")

        new_trade = models.Trade(
            symbol=strategy_input.underlying_symbol,
            trade_type=leg.trade_type,
            status=models.TradeStatusEnum.OPEN,
            entry_price=leg.entry_price,
            average_price=leg.entry_price,
            size=leg.size,
            current_size=leg.size,
            created_at=datetime.utcnow(),
            configuration_id=config.id,
            is_contract=True,
            strike=leg.strike,
            expiration_date=datetime.strptime(leg.expiration_date, "%m/%d/%y") if leg.expiration_date else None,
            strategy_trade_id=strategy_trade.id
        )
        db.add(new_trade)
        db.commit()
        db.refresh(new_trade)

        new_transaction = models.Transaction(
            trade_id=new_trade.trade_id,
            transaction_type=models.TransactionTypeEnum.OPEN,
            amount=leg.entry_price,
            size=leg.size,
            created_at=datetime.utcnow()
        )
        db.add(new_transaction)
        db.commit()

    return strategy_trade

class TradeActionInput(BaseModel):
    trade_id: str
    size: str
    price: float

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

def add_to_trade(db: Session, action_input: TradeActionInput):
    trade = get_trade(db, action_input.trade_id)
    if not trade:
        raise ValueError(f"Trade {action_input.trade_id} not found.")

    new_transaction = models.Transaction(
        trade_id=trade.trade_id,
        transaction_type=models.TransactionTypeEnum.ADD,
        amount=action_input.price,
        size=action_input.size,
        created_at=datetime.utcnow()
    )
    db.add(new_transaction)

    new_size = Decimal(trade.current_size) + Decimal(action_input.size)
    trade.current_size = str(new_size)
    trade.average_price = ((Decimal(trade.average_price) * Decimal(trade.current_size)) + (Decimal(action_input.price) * Decimal(action_input.size))) / new_size

    db.commit()
    db.refresh(trade)

    return trade

def trim_trade(db: Session, action_input: TradeActionInput):
    trade = get_trade(db, action_input.trade_id)
    if not trade:
        raise ValueError(f"Trade {action_input.trade_id} not found.")

    current_size = Decimal(trade.current_size)
    trim_size = Decimal(action_input.size)

    if trim_size > current_size:
        raise ValueError(f"Trim size ({trim_size}) is greater than current trade size ({current_size}).")

    new_transaction = models.Transaction(
        trade_id=trade.trade_id,
        transaction_type=models.TransactionTypeEnum.TRIM,
        amount=action_input.price,
        size=str(trim_size),
        created_at=datetime.utcnow()
    )
    db.add(new_transaction)

    new_size = current_size - trim_size
    trade.current_size = str(new_size)

    trim_transactions = get_transactions_for_trade(db, trade.trade_id, [models.TransactionTypeEnum.TRIM])
    trim_transactions.append(new_transaction)
    average_trim_price = sum(Decimal(t.amount) * Decimal(t.size) for t in trim_transactions) / sum(Decimal(t.size) for t in trim_transactions)
    trade.average_exit_price = float(average_trim_price)

    db.commit()
    db.refresh(trade)

    return trade

def exit_trade(db: Session, action_input: TradeActionInput):
    trade = get_trade(db, action_input.trade_id)
    if not trade:
        raise ValueError(f"Trade {action_input.trade_id} not found.")

    trade.status = models.TradeStatusEnum.CLOSED
    trade.exit_price = action_input.price
    trade.closed_at = datetime.utcnow()

    new_transaction = models.Transaction(
        trade_id=trade.trade_id,
        transaction_type=models.TransactionTypeEnum.CLOSE,
        amount=action_input.price,
        size=action_input.size,
        created_at=datetime.utcnow()
    )
    db.add(new_transaction)

    # Calculate profit/loss
    open_transactions = get_transactions_for_trade(db, trade.trade_id, [models.TransactionTypeEnum.OPEN, models.TransactionTypeEnum.ADD])
    trim_transactions = get_transactions_for_trade(db, trade.trade_id, [models.TransactionTypeEnum.TRIM])

    total_cost = sum(Decimal(t.amount) * Decimal(t.size) for t in open_transactions)
    total_open_size = sum(Decimal(t.size) for t in open_transactions)
    total_trimmed_size = sum(Decimal(t.size) for t in trim_transactions)

    average_cost = total_cost / total_open_size if total_open_size > 0 else 0

    trim_profit_loss = sum((Decimal(t.amount) - average_cost) * Decimal(t.size) for t in trim_transactions)
    exit_profit_loss = (Decimal(action_input.price) - average_cost) * Decimal(action_input.size)

    total_profit_loss = trim_profit_loss + exit_profit_loss
    trade.profit_loss = float(total_profit_loss)

    # Determine win/loss
    if total_profit_loss > 0:
        trade.win_loss = models.WinLossEnum.WIN
    elif total_profit_loss < 0:
        trade.win_loss = models.WinLossEnum.LOSS
    else:
        trade.win_loss = models.WinLossEnum.BREAKEVEN

    db.commit()
    db.refresh(trade)

    return trade

def exit_expired_trade(db: Session, trade_id: str):
    trade = get_trade(db, trade_id)
    if not trade:
        raise ValueError(f"Trade {trade_id} not found.")

    # Set exit price to max loss
    exit_price = 0 if trade.trade_type.lower() in ["long", "buy to open"] else trade.strike * 2

    trade.status = models.TradeStatusEnum.CLOSED
    trade.exit_price = exit_price
    trade.closed_at = datetime.utcnow()

    current_size = Decimal(trade.current_size)

    new_transaction = models.Transaction(
        trade_id=trade.trade_id,
        transaction_type=models.TransactionTypeEnum.CLOSE,
        amount=exit_price,
        size=str(current_size),
        created_at=datetime.utcnow()
    )
    db.add(new_transaction)

    # Calculate profit/loss
    open_transactions = get_transactions_for_trade(db, trade.trade_id, [models.TransactionTypeEnum.OPEN, models.TransactionTypeEnum.ADD])
    trim_transactions = get_transactions_for_trade(db, trade.trade_id, [models.TransactionTypeEnum.TRIM])

    total_cost = sum(Decimal(t.amount) * Decimal(t.size) for t in open_transactions)
    total_open_size = sum(Decimal(t.size) for t in open_transactions)
    total_trimmed_size = sum(Decimal(t.size) for t in trim_transactions)

    average_cost = total_cost / total_open_size if total_open_size > 0 else 0

    trim_profit_loss = sum((Decimal(t.amount) - average_cost) * Decimal(t.size) for t in trim_transactions)
    exit_profit_loss = (Decimal(exit_price) - average_cost) * current_size

    total_profit_loss = trim_profit_loss + exit_profit_loss
    trade.profit_loss = float(total_profit_loss)

    # Determine win/loss
    trade.win_loss = models.WinLossEnum.LOSS

    db.commit()
    db.refresh(trade)

    return trade

def get_configuration(db: Session, trade_group: str):
    return db.query(models.TradeConfiguration).filter(models.TradeConfiguration.name == trade_group).first()

def determine_trade_group(expiration_date: str, trade_type: str) -> str:
    if not expiration_date and trade_type.lower() in ["sto", "bto"]:
        return "swing_trader"
    
    try:
        exp_date = datetime.strptime(expiration_date, "%m/%d/%y").date()
    except ValueError:
        return "swing_trader"
    
    days_to_expiration = (exp_date - datetime.now().date()).days
    
    if days_to_expiration < 7:
        return "day_trader"
    else:
        return "swing_trader"

def future_trade(db: Session, trade_input: schemas.TradeCreate):
    trade_group = "day_trader"  # Futures are typically day trades
    config = get_configuration(db, trade_group)
    if not config:
        raise ValueError(f"No configuration found for trade group: {trade_group}")

    new_trade = models.Trade(
        symbol=trade_input.symbol,
        trade_type="Future",
        status=models.TradeStatusEnum.OPEN,
        entry_price=trade_input.entry_price,
        average_price=trade_input.entry_price,
        size=trade_input.size,
        current_size=trade_input.size,
        created_at=datetime.now(),
        configuration_id=config.id,
        is_contract=True,
        is_day_trade=True,
    )
    db.add(new_trade)
    db.commit()
    db.refresh(new_trade)

    new_transaction = models.Transaction(
        trade_id=new_trade.trade_id,
        transaction_type=models.TransactionTypeEnum.OPEN,
        amount=trade_input.entry_price,
        size=trade_input.size,
        created_at=datetime.now()
    )
    db.add(new_transaction)
    db.commit()

    return new_trade

def long_term_trade(db: Session, trade_input: schemas.TradeCreate):
    trade_group = "long_term_trader"
    config = get_configuration(db, trade_group)
    if not config:
        raise ValueError(f"No configuration found for trade group: {trade_group}")

    new_trade = models.Trade(
        symbol=trade_input.symbol,
        trade_type="Long Term",
        status=models.TradeStatusEnum.OPEN,
        entry_price=trade_input.entry_price,
        average_price=trade_input.entry_price,
        size=trade_input.size,
        current_size=trade_input.size,
        created_at=datetime.now(),
        configuration_id=config.id,
        is_contract=False,
        is_day_trade=False,
    )
    db.add(new_trade)
    db.commit()
    db.refresh(new_trade)

    new_transaction = models.Transaction(
        trade_id=new_trade.trade_id,
        transaction_type=models.TransactionTypeEnum.OPEN,
        amount=trade_input.entry_price,
        size=trade_input.size,
        created_at=datetime.now()
    )
    db.add(new_transaction)
    db.commit()

    return new_trade

def create_trade(db: Session, trade: schemas.TradeCreate):
    db_trade = models.Trade(**trade.model_dump(), status=models.TradeStatusEnum.OPEN)
    db_trade.average_price = trade.entry_price
    db_trade.size = trade.size
    db_trade.current_size = trade.size

    transaction = models.Transaction(
        trade_id=db_trade.trade_id,
        transaction_type=models.TransactionTypeEnum.OPEN,
        amount=trade.entry_price,
        size=trade.size,
        created_at=datetime.now()
    )
    
    db.add(transaction)
    db.add(db_trade)
    db.commit()
    db.refresh(db_trade)
    logging.info(f"Trade created: {db_trade.trade_id}")
    return db_trade

def create_options_strategy(db: Session, strategy: schemas.StrategyTradeCreate):
    db_strategy = models.OptionsStrategyTrade(
        name=strategy.name,
        underlying_symbol=strategy.underlying_symbol,
        status=models.OptionsStrategyStatusEnum.OPEN,
        trade_group=strategy.trade_group
    )
    db.add(db_strategy)
    db.commit()
    db.refresh(db_strategy)
    return db_strategy