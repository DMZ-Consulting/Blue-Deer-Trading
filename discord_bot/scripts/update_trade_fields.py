import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.app.models import Trade, Transaction, TransactionTypeEnum, OptionsStrategyTrade
from backend.app.database import Base, get_database_url
from decimal import Decimal, InvalidOperation
from datetime import timedelta
from backend.app.models import TradeStatusEnum
# Create engine and session
# make sure the directory is always the same no matter where the script is run from
#db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'db', 'sql_app.db')
db_path = get_database_url()
print(f"Database path: {db_path}")
engine = create_engine(db_path)
Session = sessionmaker(bind=engine)
session = Session()

trades_to_update = {
    "o4ZvJFDq": { "option_type": "CALL" },
    "jcgj4bLn": { "option_type": "CALL" },
    "KMfKh84h": { "option_type": "PUT" },
    "kpW2T9kS": { "option_type": "PUT" },
    "WKPGubbV": { "option_type": "CALL" },
    "Gyq96yJh": { "option_type": "PUT" },
    "g3shqHqy": { "option_type": "PUT" },
    "A4UZqhJb": { "option_type": "PUT" },
    "HyAGoTmp": { "option_type": "PUT" },
    "4GAwScXn": { "option_type": "PUT" },
    "YWi3Yo5f": { "option_type": "PUT" },
    "kovPL4mu": { "option_type": "PUT" },
    "mymyW7or": { "option_type": "PUT" },
    "X4fJypSS": { "option_type": "PUT" },
    "K54iZTDy": { "option_type": "PUT" },
    "QfbmfCFe": { "option_type": "PUT" },
    "iMafkBmL": { "option_type": "PUT" },
    "MAQhcZQs": { "option_type": "PUT" },
    "o7FavAbr": { "option_type": "PUT" },
    "akBg3qhS": { "option_type": "PUT" },
    "aiRWXmYw": { "option_type": "PUT" },
    "THgT5QhV": { "option_type": "PUT" },
    "4wCoBL4k": { "option_type": "PUT" },
    "WrNzyKvT": { "option_type": "PUT" },
    "ebhrMqyc": { "option_type": "PUT" },
    "fzDSpXzE": { "option_type": "PUT" },
    "e5Rmeygt": { "option_type": "PUT" },
    "BbVjheZQ": { "configuration_id": "3" }

}

transactions_to_update = {
    "Vent2aXK": {"amount": 0},
    "fLndc2Si": {"amount": 1.45, "size": 0.5},
    "m32sXMpM": {"amount": 12.5},
    "TesLDFXQ": {"amount": 5828.75, "size": 6}
}

os_transactions_to_update = {
    "m32sXMpM": {"amount": 12.5}
}

trades_to_delete = [
    "e5Rmeygt",
    "gqm9fMGR",
    "oTgQWrMH",
    "3EWQ8WQd",
    "XwVJfGHq"
]

os_trades_to_delete = [
    "cmQXMsYj"
]

def update_trade_fields():
    trades = session.query(Trade).all()

    for trade in trades:
        # If trade has expiration date, set it to 10PM UTC time of the same date
        if trade.expiration_date:
            #check if time is 00:00:00, if so, set to 10PM that day
            date_string = trade.expiration_date.strftime("%m/%d/%y")
            #if trade.expiration_date == datetime(trade.expiration_date.year, trade.expiration_date.month, trade.expiration_date.day).time():
            trade.expiration_date = datetime.strptime(date_string + " 21:15", "%m/%d/%y %H:%M")
            print(f"TradeID: {trade.trade_id} - Updating expiration_date to {trade.expiration_date}")

        if trade.trade_id in trades_to_update:
            for key, value in trades_to_update[trade.trade_id].items():
                print(f"TradeID: {trade.trade_id} - Updating {key} to {value}")
                setattr(trade, key, value)

        if trade.status == TradeStatusEnum.CLOSED:
            print(f"TradeID: {trade.trade_id} - Status is closed")
            # has expiration date, and closed_at is > expiration date, set closed_at to expiration date at 5pm
            if trade.expiration_date and trade.closed_at and trade.closed_at > trade.expiration_date+ timedelta(hours=17):
                trade.closed_at = trade.expiration_date + timedelta(hours=17)
                print(f"TradeID: {trade.trade_id} - Updating closed_at to {trade.closed_at}")

        if trade.trade_id in trades_to_delete:
            print(f"TradeID: {trade.trade_id} - Deleting trade")
            session.delete(trade)

    session.commit()

    transactions = session.query(Transaction).all()  # Get all transactions without a limit
    for transaction in transactions:
        if transaction.id in transactions_to_update:
            for key, value in transactions_to_update[transaction.id].items():
                print(f"TransactionID: {transaction.id} - Updating {key} to {value}")
                setattr(transaction, key, value)


    session.commit()

    os_trades = session.query(OptionsStrategyTrade).all()
    for trade in os_trades:
        print(trade.trade_id)
        if trade.trade_id in os_trades_to_delete:
            print(f"OptionsStrategyTradeID: {trade.trade_id} - Deleting trade")
            session.delete(trade)

    session.commit()
    
    print("All trades have been updated.")

if __name__ == "__main__":
    update_trade_fields()