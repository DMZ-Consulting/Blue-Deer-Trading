import requests
from datetime import datetime, timedelta

# Base URL of the API
BASE_URL = "http://localhost:8000"

# Helper function to create a trade
def create_trade(trade_type, symbol, entry_price, size, trade_group, expiration_date=None, strike=None, option_type=None):
    trade_data = {
        "symbol": symbol,
        "trade_type": trade_type,
        "entry_price": entry_price,
        "size": size,
        "trade_group": trade_group,
        "expiration_date": expiration_date,
        "strike": strike,
        "option_type": option_type
    }
    response = requests.post(f"{BASE_URL}/trades/bto", json=trade_data)
    return response.json()

# Helper function to add to a trade
def add_to_trade(trade_id, price, size):
    action_data = {
        "trade_id": trade_id,
        "price": price,
        "size": size
    }
    response = requests.post(f"{BASE_URL}/trades/{trade_id}/add", json=action_data)
    return response.json()

# Helper function to trim a trade
def trim_trade(trade_id, price, size):
    action_data = {
        "trade_id": trade_id,
        "price": price,
        "size": size
    }
    response = requests.post(f"{BASE_URL}/trades/{trade_id}/trim", json=action_data)
    return response.json()

# Helper function to exit a trade
def exit_trade(trade_id, price):
    action_data = {
        "trade_id": trade_id,
        "price": price,
        "size": ""
    }
    response = requests.post(f"{BASE_URL}/trades/{trade_id}/exit", json=action_data)
    return response.json()

# Create trades for swing trader
swing_trades = []
for i in range(5):
    trade = create_trade("BTO", f"SWING{i}", 150 + i, "50", "swing_trader")
    swing_trades.append(trade)

# Create trades for day trader
day_trades = []
for i in range(5):
    trade = create_trade("STO", f"DAY{i}", 300 + i, "25", "day_trader", "2023-07-21", 160 + i, "PUT")
    day_trades.append(trade)

# Add to some trades
for trade in swing_trades[:3]:
    add_to_trade(trade['trade_id'], trade['entry_price'] + 5, "10")

for trade in day_trades[:3]:
    add_to_trade(trade['trade_id'], trade['entry_price'] + 5, "5")

# Trim some trades
for trade in swing_trades[3:]:
    trim_trade(trade['trade_id'], trade['entry_price'] + 10, "10")

for trade in day_trades[3:]:
    trim_trade(trade['trade_id'], trade['entry_price'] + 10, "5")

# Exit some trades
for trade in swing_trades:
    exit_trade(trade['trade_id'], trade['entry_price'] + 15)

for trade in day_trades:
    exit_trade(trade['trade_id'], trade['entry_price'] + 15)

print("Trades created and modified successfully.")