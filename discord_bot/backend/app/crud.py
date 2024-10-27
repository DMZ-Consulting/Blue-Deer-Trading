from sqlalchemy.orm import Session
from sqlalchemy import func, desc, asc
from . import models, schemas
from typing import List, Optional
from .schemas import TransactionTypeEnum
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, field_validator
from .bot import create_trade_oneliner
import logging
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)

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

class TradeActionInput(BaseModel):
    trade_id: str
    price: float
    size: str

class StrategyTradeActionInput(BaseModel):
    strategy_id: str
    net_cost: float
    size: str

def get_trades(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    status: Optional[models.TradeStatusEnum] = None,
    symbol: Optional[str] = None,
    trade_type: Optional[str] = None,
    sort_by: Optional[str] = None,
    sort_order: str = "desc",
    config_name: Optional[str] = None,
    week_filter: Optional[str] = None,
    month_filter: Optional[str] = None,
    year_filter: Optional[str] = None
) -> List[models.Trade]:
    print("Entering get_trades function")
    query = db.query(models.Trade)

    if status:
        query = query.filter(models.Trade.status == status)
    if symbol:
        query = query.filter(models.Trade.symbol == symbol)
    if trade_type:
        query = query.filter(models.Trade.trade_type == trade_type)
    
    if config_name:
        trade_config = db.query(models.TradeConfiguration).filter(models.TradeConfiguration.name == config_name).first()
        if trade_config:
            query = query.filter(models.Trade.configuration_id == trade_config.id)
        else:
            return []

    if week_filter and status == models.TradeStatusEnum.CLOSED:
        # Find the friday of the week from the week_filter string
        # Get the date of the first day of the week (monday)
        day = datetime.strptime(week_filter, "%Y-%m-%d")
        first_day_of_week = day - timedelta(days=day.weekday())
        # Get the date of the last day of the week (friday)
        last_day_of_week = first_day_of_week + timedelta(days=4)
        query = query.filter(models.Trade.closed_at >= first_day_of_week)
        query = query.filter(models.Trade.closed_at <= last_day_of_week + timedelta(days=1))
    if month_filter and status == models.TradeStatusEnum.CLOSED:
        query = query.filter(models.Trade.closed_at >= month_filter)
    if year_filter and status == models.TradeStatusEnum.CLOSED:
        query = query.filter(models.Trade.closed_at >= year_filter)

    if sort_by:
        if hasattr(models.Trade, sort_by):
            order_func = desc if sort_order == "desc" else asc
            query = query.order_by(order_func(getattr(models.Trade, sort_by)))
        else:
            raise ValueError(f"Invalid sort_by parameter: {sort_by}")

    print(f"Final query: {query}")
    result = query.offset(skip).limit(limit).all()
    print(f"Retrieved {len(result)} trades")
    return result

def get_portfolio_trades(
    db: Session,
    skip: int = 0,
    limit: int = 500,
    status: Optional[models.TradeStatusEnum] = 'closed',
    sort_by: Optional[str] = None,
    sort_order: str = "desc",
    config_name: Optional[str] = None,
    week_filter: Optional[str] = None
):
    query = db.query(models.Trade)

    if status:
        query = query.filter(models.Trade.status == status)

    if config_name:
        trade_config = db.query(models.TradeConfiguration).filter(models.TradeConfiguration.name == config_name).first()
        if trade_config:
            query = query.filter(models.Trade.configuration_id == trade_config.id)
        else:
            return []

    if not week_filter:
        raise ValueError("Week filter is required")
    
    # Find the Monday and Sunday of the week from the week_filter string
    day = datetime.strptime(week_filter, "%Y-%m-%d")
    monday = day - timedelta(days=day.weekday())
    sunday = monday + timedelta(days=6)
    query = query.filter(
        (models.Trade.closed_at >= monday) & (models.Trade.closed_at <= sunday + timedelta(days=1))
    )

    if sort_by:
        if hasattr(models.Trade, sort_by):
            order_func = desc if sort_order == "desc" else asc
            query = query.order_by(order_func(getattr(models.Trade, sort_by)))
        else:
            raise ValueError(f"Invalid sort_by parameter: {sort_by}")

    trades = query.offset(skip).limit(limit).all()

    # Calculate additional fields
    total_pl = Decimal(0)

    processed_trades = []

    for trade in trades:
        # Get all transactions for this trade
        transactions = get_transactions_for_trade(db, trade.trade_id)
        
        trade_pl = Decimal(0)
        trade_size = Decimal(0)
        trade_entry_cost = Decimal(0)
        trade_exit_value = Decimal(0)
        
        processed_transactions = []

        for transaction in transactions:
            if monday - timedelta(days=1) <= transaction.created_at <= sunday:
                size = Decimal(transaction.size)
                
                if transaction.transaction_type in [models.TransactionTypeEnum.CLOSE, models.TransactionTypeEnum.TRIM]:
                    exit_price = Decimal(transaction.amount)
                    entry_price = Decimal(trade.average_price)
                    
                    pl = (exit_price - entry_price) * size
                    print(f"PL: {pl}")
                    percent_change = (exit_price - entry_price) / entry_price * 100

                    if trade.is_contract:
                        print(f"Trade is a contract")
                        pl = pl * 100

                    trade_pl += pl
                    trade_size += size
                    trade_entry_cost += entry_price * size 
                    trade_exit_value += exit_price * size

                    processed_transactions.append({
                        "id": transaction.id,
                        "trade_id": trade.trade_id,
                        "type": transaction.transaction_type,
                        "amount": float(transaction.amount),
                        "size": float(size),
                        "pl": float(pl),
                        "percent_change": float(percent_change)
                    })

        trade_avg_exit = trade_exit_value / trade_size if trade_size > 0 else Decimal(0)
        trade_pct_change = (Decimal(trade_avg_exit) - Decimal(trade.average_price)) / Decimal(trade.average_price) * 100
        
        processed_trades.append({
            "trade": trade,
            "oneliner": create_trade_oneliner(trade),
            "realized_pl": float(trade_pl),
            "realized_size": float(trade_size),
            "avg_entry_price": float(trade.average_price),
            "avg_exit_price": float(trade_avg_exit),
            "pct_change": float(trade_pct_change),
            #"transactions": processed_transactions
        })

        print(f"Processed trades: {processed_trades}")

        total_pl += trade_pl

    # Instead of returning a dictionary, return the list of processed trades
    return processed_trades

def get_os_trades(
    db: Session,
    status: Optional[models.OptionsStrategyStatusEnum] = None,
    skip: int = 0,
    limit: int = 100
):
    query = db.query(models.OptionsStrategyTrade)
    if status is not None:
        query = query.filter(models.OptionsStrategyTrade.status == status)
    
    trades = query.offset(skip).limit(limit).all()

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
    win_rate = db.query(models.Trade).filter(models.Trade.win_loss == models.WinLossEnum.WIN).count() / total_trades if total_trades > 0 else 0
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

def create_trade(db: Session, trade: schemas.TradeCreate):
    db_trade = models.Trade(
        **trade.model_dump(),
        status=models.TradeStatusEnum.OPEN,
    )
    db_trade.average_price = trade.entry_price
    db_trade.size = trade.size
    db_trade.current_size = trade.size

    db.add(db_trade)  # Commit db_trade first to get the id
    db.commit()       # Commit to save the trade and generate the ID
    db.refresh(db_trade)  # Refresh to get the latest state of db_trade

    transaction = models.Transaction(
        trade_id=db_trade.trade_id,
        transaction_type=models.TransactionTypeEnum.OPEN,
        amount=trade.entry_price,
        size=trade.size,
        created_at=datetime.now()
    )
    
    db.add(transaction)
    db.commit()  # Commit the transaction after adding it
    logging.info(f"Trade created: {db_trade.trade_id}")
    return db_trade

def create_options_strategy(db: Session, strategy: schemas.OptionsStrategyTradeCreate):
    db_strategy = models.OptionsStrategyTrade(
        name=strategy.name,
        underlying_symbol=strategy.underlying_symbol,
        status=models.OptionsStrategyStatusEnum.OPEN,
        trade_group=strategy.trade_group,
        legs=json.dumps(strategy.legs),
        net_cost=strategy.net_cost,
        average_net_cost=strategy.net_cost,
        size=strategy.size,
        current_size=strategy.size
    )
    db.add(db_strategy)
    db.commit()
    db.refresh(db_strategy)

    open_transaction = models.OptionsStrategyTransaction(
        strategy_id=db_strategy.id,
        transaction_type=models.TransactionTypeEnum.OPEN,
        net_cost=strategy.net_cost,
        size=strategy.size
    )
    db.add(open_transaction)
    db.commit()

    return db_strategy

def add_to_options_strategy(db: Session, strategy_id: int, net_cost: float, size: str):
    strategy = db.query(models.OptionsStrategyTrade).filter(models.OptionsStrategyTrade.id == strategy_id).first()
    if not strategy:
        raise ValueError(f"Options strategy with ID {strategy_id} not found.")

    new_transaction = models.OptionsStrategyTransaction(
        strategy_id=strategy.id,
        transaction_type=models.TransactionTypeEnum.ADD,
        net_cost=net_cost,
        size=size
    )
    db.add(new_transaction)

    strategy.current_size = str(float(strategy.current_size) + float(size))
    strategy.average_net_cost = ((float(strategy.average_net_cost) * float(strategy.current_size)) + (float(net_cost) * float(size))) / (float(strategy.current_size) + float(size))
    db.commit()
    db.refresh(strategy)

    return strategy

def trim_options_strategy(db: Session, strategy_id: int, net_cost: float, size: str):
    strategy = db.query(models.OptionsStrategyTrade).filter(models.OptionsStrategyTrade.id == strategy_id).first()
    if not strategy:
        raise ValueError(f"Options strategy with ID {strategy_id} not found.")

    if float(size) > float(strategy.current_size):
        raise ValueError(f"Trim size ({size}) is greater than current strategy size ({strategy.current_size}).")

    new_transaction = models.OptionsStrategyTransaction(
        strategy_id=strategy.id,
        transaction_type=models.TransactionTypeEnum.TRIM,
        net_cost=net_cost,
        size=size
    )
    db.add(new_transaction)

    strategy.current_size = str(float(strategy.current_size) - float(size))
    db.commit()
    db.refresh(strategy)

    return strategy

def exit_options_strategy(db: Session, strategy_id: int, net_cost: float):
    strategy = db.query(models.OptionsStrategyTrade).filter(models.OptionsStrategyTrade.id == strategy_id).first()
    if not strategy:
        raise ValueError(f"Options strategy with ID {strategy_id} not found.")

    new_transaction = models.OptionsStrategyTransaction(
        strategy_id=strategy.id,
        transaction_type=models.TransactionTypeEnum.CLOSE,
        net_cost=net_cost,
        size=strategy.current_size
    )
    db.add(new_transaction)

    strategy.status = models.OptionsStrategyStatusEnum.CLOSED
    strategy.closed_at = datetime.now()
    db.commit()
    db.refresh(strategy)

    return strategy

def get_configuration(db: Session, trade_group: str):
    return db.query(models.TradeConfiguration).filter(models.TradeConfiguration.name == trade_group).first()

def add_to_trade(db: Session, action_input: TradeActionInput):
    trade = get_trade(db, action_input.trade_id)
    if not trade:
        raise ValueError(f"Trade {action_input.trade_id} not found.")

    new_transaction = models.Transaction(
        trade_id=trade.trade_id,
        transaction_type=models.TransactionTypeEnum.ADD,
        amount=action_input.price,
        size=action_input.size,
        created_at=datetime.now()
    )
    db.add(new_transaction)

    current_size = Decimal(trade.current_size)
    add_size = Decimal(action_input.size)
    new_size = current_size + add_size

    # Update average entry price
    total_cost = (current_size * Decimal(trade.average_price)) + (add_size * Decimal(action_input.price))
    trade.average_price = float(total_cost / new_size)

    trade.current_size = str(new_size)

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
        created_at=datetime.now()
    )
    db.add(new_transaction)

    new_size = current_size - trim_size
    trade.current_size = str(new_size)

    db.commit()
    db.refresh(trade)

    return trade

def exit_trade(db: Session, action_input: TradeActionInput):
    trade = get_trade(db, action_input.trade_id)
    if not trade:
        raise ValueError(f"Trade {action_input.trade_id} not found.")
    
    action_input.size = trade.current_size

    trade.status = models.TradeStatusEnum.CLOSED
    trade.exit_price = action_input.price
    trade.closed_at = datetime.now()

    new_transaction = models.Transaction(
        trade_id=trade.trade_id,
        transaction_type=models.TransactionTypeEnum.CLOSE,
        amount=action_input.price,
        size=trade.current_size,
        created_at=datetime.now()
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
    exit_profit_loss = (Decimal(action_input.price) - average_cost) * Decimal(trade.current_size)

    total_profit_loss = trim_profit_loss + exit_profit_loss
    trade.profit_loss = float(total_profit_loss)

    # Update average exit price
    total_exit_value = sum(Decimal(t.amount) * Decimal(t.size) for t in trim_transactions) + (Decimal(action_input.price) * Decimal(trade.current_size))
    total_exit_size = total_trimmed_size + Decimal(trade.current_size)
    trade.average_exit_price = float(total_exit_value / total_exit_size)

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

def os_add(db: Session, strategy_id: str, net_cost: float, size: str):
    strategy = db.query(models.OptionsStrategyTrade).filter(models.OptionsStrategyTrade.trade_id == strategy_id).first()
    if not strategy:
        raise ValueError(f"Options strategy trade {strategy_id} not found.")

    new_transaction = models.OptionsStrategyTransaction(
        strategy_id=strategy.id,
        transaction_type=models.TransactionTypeEnum.ADD,
        net_cost=net_cost,
        size=size
    )
    db.add(new_transaction)

    strategy.current_size = str(float(strategy.current_size) + float(size))
    strategy.average_net_cost = ((float(strategy.average_net_cost) * float(strategy.current_size)) + (float(net_cost) * float(size))) / (float(strategy.current_size) + float(size))
    db.commit()
    db.refresh(strategy)

    return strategy

def os_trim(db: Session, strategy_id: str, net_cost: float, size: str):
    strategy = db.query(models.OptionsStrategyTrade).filter(models.OptionsStrategyTrade.trade_id == strategy_id).first()
    if not strategy:
        raise ValueError(f"Options strategy trade {strategy_id} not found.")

    if float(size) > float(strategy.current_size):
        raise ValueError(f"Trim size ({size}) is greater than current strategy size ({strategy.current_size}).")

    new_transaction = models.OptionsStrategyTransaction(
        strategy_id=strategy.id,
        transaction_type=models.TransactionTypeEnum.TRIM,
        net_cost=net_cost,
        size=size
    )
    db.add(new_transaction)

    strategy.current_size = str(float(strategy.current_size) - float(size))
    db.commit()
    db.refresh(strategy)

    return strategy

def os_exit(db: Session, strategy_id: str, net_cost: float):
    strategy = db.query(models.OptionsStrategyTrade).filter(models.OptionsStrategyTrade.trade_id == strategy_id).first()
    if not strategy:
        raise ValueError(f"Options strategy trade {strategy_id} not found.")

    new_transaction = models.OptionsStrategyTransaction(
        strategy_id=strategy.id,
        transaction_type=models.TransactionTypeEnum.CLOSE,
        net_cost=net_cost,
        size=strategy.current_size
    )
    db.add(new_transaction)

    strategy.status = models.OptionsStrategyStatusEnum.CLOSED
    strategy.closed_at = datetime.now()

    # Calculate P/L
    transactions = db.query(models.OptionsStrategyTransaction).filter_by(strategy_id=strategy.id).all()
    open_transactions = [t for t in transactions if t.transaction_type in [models.TransactionTypeEnum.OPEN, models.TransactionTypeEnum.ADD]]
    trim_transactions = [t for t in transactions if t.transaction_type == models.TransactionTypeEnum.TRIM]

    total_cost = sum(float(t.net_cost) * float(t.size) for t in open_transactions)
    total_size = sum(float(t.size) for t in open_transactions)
    avg_entry_cost = total_cost / total_size if total_size > 0 else 0

    total_exit_cost = sum(float(t.net_cost) * float(t.size) for t in trim_transactions) + (float(net_cost) * float(strategy.current_size))
    total_exit_size = sum(float(t.size) for t in trim_transactions) + float(strategy.current_size)
    avg_exit_cost = total_exit_cost / total_exit_size if total_exit_size > 0 else 0

    strategy.profit_loss = (avg_exit_cost - avg_entry_cost) * float(strategy.size)

    db.commit()
    db.refresh(strategy)

    return strategy

# Add more CRUD functions as needed...

