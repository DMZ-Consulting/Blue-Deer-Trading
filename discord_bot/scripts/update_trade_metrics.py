import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.app.models import Trade, Transaction, TransactionTypeEnum, OptionsStrategyTrade, OptionsStrategyTransaction
from backend.app.database import Base, get_database_url
#from backend.app.bot import manually_expire_trades
from decimal import Decimal, InvalidOperation

# Create engine and session
# make sure the directory is always the same no matter where the script is run from
#db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'db', 'sql_app.db')
db_path = get_database_url()
print(f"Database path: {db_path}")
engine = create_engine(db_path)
Session = sessionmaker(bind=engine)
session = Session()


def decimal_or_zero(value):
    try:
        return Decimal(value)
    except (InvalidOperation, TypeError):
        print(f"Warning: Invalid size value '{value}', using 0 instead.")
        return Decimal('0')

def update_trade_metrics():
    #manually_expire_trades()

    trades = session.query(Trade).all()

    for trade in trades:
        if trade.symbol.upper() == "ES":
            trade.configuration_id = 1

        if str(trade.size).upper() == "MAX" or str(trade.current_size).upper() == "MAX":
            trade.current_size = 6
            trade.size = 6
            transactions = session.query(Transaction).filter(Transaction.trade_id == trade.trade_id).all()
            for t in transactions:
                if str(t.size).upper() == "MAX":
                    t.size = 6
        elif "x" in str(trade.size) or "x" in str(trade.current_size):
            trade.size = int(str(trade.size).replace("x", ""))
            trade.current_size = int(str(trade.current_size).replace("x", ""))
            transactions = session.query(Transaction).filter(Transaction.trade_id == trade.trade_id).all()
            for t in transactions:
                if "x" in str(t.size):
                    t.size = int((str(t.size).replace("x", "")))
    
    session.commit()

    # Check all trades for multiple close transactions. If one does, print the trade_id and the transactions with the size and amount
    trades = session.query(Trade).all()
    for trade in trades:
        transactions = session.query(Transaction).filter(Transaction.trade_id == trade.trade_id).all()
        close_transactions = [t for t in transactions if t.transaction_type in [TransactionTypeEnum.CLOSE]]
        # delete all the transactions that are after the first close transaction. Make sure the "first" refers to the oldest transaction
        close_transactions_sorted = sorted(close_transactions, key=lambda x: x.created_at, reverse=False)  # Oldest first
        if len(close_transactions_sorted) > 1:
            first_close_index = transactions.index(close_transactions_sorted[0])
            for t in transactions[first_close_index + 1:]:
                session.delete(t)
        if trade.symbol.upper() == "TEST":
            session.delete(trade)
        if len(close_transactions) > 1:
            print(f"Trade {trade.trade_id} has multiple close transactions: {close_transactions}")
        if trade.trade_type.lower() == "long":
            trade.trade_type = "BTO"
        elif trade.trade_type.lower() == "short":
            trade.trade_type = "STO"
        elif trade.trade_type == "bto":
            trade.trade_type = "BTO"
        elif trade.trade_type == "sto":
            trade.trade_type = "STO"

    session.commit()

    for trade in trades:
        transactions = session.query(Transaction).filter(Transaction.trade_id == trade.trade_id).all()
        
        open_transactions = [t for t in transactions if t.transaction_type in [TransactionTypeEnum.OPEN, TransactionTypeEnum.ADD]]
        
        if not open_transactions:
            # Create a new open transaction
            new_transaction = Transaction(
                trade_id=trade.trade_id,
                transaction_type=TransactionTypeEnum.OPEN,
                size=float(trade.size),  # Use the trade size
                amount=float(trade.average_price) * float(trade.size) if float(trade.size) > 0 else 0,  # Back calculate amount
                created_at=trade.created_at  # Set the date to the same as created_at for the trade
            )
            session.add(new_transaction)
            print(f"Added new open transaction for trade {trade.trade_id}: size={new_transaction.size}, amount={new_transaction.amount}")
    
    session.commit()
    

    trades = session.query(Trade).all()

    for trade in trades:
        print(f"Trade {trade.trade_id} updating metrics")
        transactions = session.query(Transaction).filter(Transaction.trade_id == trade.trade_id).all()
        
        open_transactions = [t for t in transactions if t.transaction_type in [TransactionTypeEnum.OPEN, TransactionTypeEnum.ADD]]
        close_transactions = [t for t in transactions if t.transaction_type in [TransactionTypeEnum.CLOSE, TransactionTypeEnum.TRIM]]

        trade.symbol = trade.symbol.upper()

        # Calculate original opened size
        trade.size = str(sum(decimal_or_zero(t.size) for t in open_transactions))

        # Calculate average purchase price
        total_cost = sum(Decimal(t.amount) * decimal_or_zero(t.size) for t in open_transactions)
        total_size = sum(decimal_or_zero(t.size) for t in open_transactions)
        trade.average_price = float(total_cost / total_size) if total_size > 0 else 0

        # Calculate average exit price
        if close_transactions:
            total_exit_value = sum(Decimal(t.amount) * decimal_or_zero(t.size) for t in close_transactions)
            total_exit_size = sum(decimal_or_zero(t.size) for t in close_transactions)
            trade.average_exit_price = float(total_exit_value / total_exit_size) if total_exit_size > 0 else 0
        else:
            trade.average_exit_price = None

        print(f"Updated trade {trade.trade_id}: size={trade.size}, avg_price={trade.average_price}, avg_exit_price={trade.average_exit_price}")

    session.commit()
    print("All trades have been updated.")

    strategies = session.query(OptionsStrategyTrade).all()
    for strategy in strategies:
        open_transactions = session.query(OptionsStrategyTransaction).filter(OptionsStrategyTransaction.strategy_id == strategy.id, OptionsStrategyTransaction.transaction_type == TransactionTypeEnum.OPEN).all()
        
        avg_cost = sum(float(t.net_cost)*float(t.size) for t in open_transactions) / sum(float(t.size) for t in open_transactions) if open_transactions else 0
        strategy.average_net_cost = avg_cost
        session.commit()
        print(f"Strategy {strategy.id}: {strategy.name}")

if __name__ == "__main__":
    update_trade_metrics()
