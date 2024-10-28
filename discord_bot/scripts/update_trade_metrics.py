import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.app.models import Trade, Transaction, TransactionTypeEnum
from backend.app.database import Base
from decimal import Decimal, InvalidOperation

# Create engine and session
# make sure the directory is always the same no matter where the script is run from
db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'db', 'sql_app.db')
engine = create_engine('sqlite:///' + db_path)
Session = sessionmaker(bind=engine)
session = Session()

def decimal_or_zero(value):
    try:
        return Decimal(value)
    except (InvalidOperation, TypeError):
        print(f"Warning: Invalid size value '{value}', using 0 instead.")
        return Decimal('0')

def update_trade_metrics():
    trades = session.query(Trade).all()

    for trade in trades:
        print(trade.size)
        if str(trade.size).upper() == "MAX":
            trade.size = decimal_or_zero(6)
            transactions = session.query(Transaction).filter(Transaction.trade_id == trade.trade_id).all()
            for t in open_transactions:
                if str(t.size).upper() == "MAX":
                    t.size = decimal_or_zero(6)
        elif "x" in str(trade.size):
            trade.size = decimal_or_zero(str(trade.size).replace("x", ""))
            transactions = session.query(Transaction).filter(Transaction.trade_id == trade.trade_id).all()
            for t in open_transactions:
                if "x" in str(t.size):
                    t.size = decimal_or_zero(str(trade.size).replace("x", ""))
    
    session.commit()

    trades = session.query(Trade).all()

    for trade in trades:
        transactions = session.query(Transaction).filter(Transaction.trade_id == trade.trade_id).all()
        
        open_transactions = [t for t in transactions if t.transaction_type in [TransactionTypeEnum.OPEN, TransactionTypeEnum.ADD]]
        close_transactions = [t for t in transactions if t.transaction_type in [TransactionTypeEnum.CLOSE, TransactionTypeEnum.TRIM]]

        

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

if __name__ == "__main__":
    update_trade_metrics()
