import os
os.environ['FASTAPI_TEST'] = 'true'

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import logging

from app.main import app
from app.database import get_db
from app.test_database import SQLALCHEMY_TEST_DATABASE_URL, override_get_db, create_test_database, drop_test_database
from app import crud, models, schemas

# Move this line to the top of the file
app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

@pytest.fixture(scope="module")
def test_db():
    logging.info("Setting up test database")
    create_test_database()
    prepopulate_test_database(next(override_get_db()))
    yield
    logging.info("Tearing down test database")
    drop_test_database()

def prepopulate_test_database(test_db: Session):
    # Create day_trader, swing_trader, and long_term_trader configuration
    logging.info("Prepopulating test database")
    config = models.TradeConfiguration(
        name="day_trader",
        channel_id="1234567890",
        role_id="1234567890",
        roadmap_channel_id="1234567890",
        update_channel_id="1234567890",
        portfolio_channel_id="1234567890",
        log_channel_id="1234567890"
    )
    test_db.add(config)
    test_db.commit()
    test_db.refresh(config)

    config = models.TradeConfiguration(
        name="swing_trader",
        channel_id="1234567890",
        role_id="1234567890",
        roadmap_channel_id="1234567890",
        update_channel_id="1234567890",
        portfolio_channel_id="1234567890",
        log_channel_id="1234567890"
    )
    test_db.add(config)
    test_db.commit()
    test_db.refresh(config)

    config = models.TradeConfiguration(
        name="long_term_trader",
        channel_id="1234567890",
        role_id="1234567890",
        roadmap_channel_id="1234567890",
        update_channel_id="1234567890",
        portfolio_channel_id="1234567890",
        log_channel_id="1234567890"
    )
    test_db.add(config)
    test_db.commit()
    test_db.refresh(config)


@pytest.fixture(autouse=True)
def run_around_tests(test_db):
    # This fixture will run automatically before and after each test
    logging.info("Starting test")
    yield
    logging.info("Ending test")

@pytest.fixture(scope="function")
def db_session(test_db):
    db = next(override_get_db())
    try:
        yield db
    finally:
        db.close()

def test_read_main(db_session):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"Hello": "World"}

def test_read_trades(db_session):
    response = client.get("/trades")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_read_trade(db_session):
    trade_input = schemas.TradeCreate(
        symbol="AAPL",
        trade_type="long",
        entry_price=150.0,
        size="100"
    )
    trade = crud.create_trade(db_session, trade_input)
    db_session.commit()
    db_session.refresh(trade)
    logging.info(f'[Test Read Trade] Trade created with ID: {trade.trade_id}')
    
    response = client.get(f"/trades/{trade.trade_id}")
    logging.info(f'[Test Read Trade] Response status: {response.status_code}')
    logging.info(f'[Test Read Trade] Response content: {response.json()}')
    
    assert response.status_code == 200
    assert response.json()["trade_id"] == trade.trade_id

def test_create_sto_trade(db_session):
    trade_input = schemas.TradeCreate(
        symbol="GOOGL",
        trade_type="short",
        entry_price=2500.0,
        size="10"
    )
    response = client.post("/trades/sto", json=trade_input.model_dump())
    assert response.status_code == 200
    assert response.json()["symbol"] == trade_input.symbol

def test_create_options_strategy(db_session):
    strategy_input = schemas.StrategyTradeCreate(
        name="Test Strategy",
        underlying_symbol="SPY",
        trade_group="swing_trader",
        status="open"
    )
    response = client.post("/trades/options-strategy", json=strategy_input.model_dump())
    assert response.status_code == 200
    assert response.json()["name"] == strategy_input.name
    assert response.json()["underlying_symbol"] == strategy_input.underlying_symbol
    assert response.json()["status"] == "open"

def test_add_to_trade(db_session):
    # First, create a trade
    trade = crud.create_trade(db_session, schemas.TradeCreate(symbol="AAPL", trade_type="long", entry_price=150.0, size="100"))
    db_session.commit()

    action_input = {"size": "50", "price": 155.0, "trade_id": trade.trade_id}
    response = client.post(f"/trades/{trade.trade_id}/add", json=action_input)
    assert response.status_code == 200
    assert response.json()["current_size"] == "150"

def test_trim_trade(db_session):
    # First, create a trade
    trade = crud.create_trade(db_session, schemas.TradeCreate(symbol="AAPL", trade_type="long", entry_price=150.0, size="100"))
    db_session.commit()

    action_input = {"size": "50", "price": 155.0, "trade_id": trade.trade_id}
    response = client.post(f"/trades/{trade.trade_id}/trim", json=action_input)
    assert response.status_code == 200
    assert response.json()["current_size"] == "50"

def test_exit_trade(db_session):
    # First, create a trade
    trade = crud.create_trade(db_session, schemas.TradeCreate(symbol="AAPL", trade_type="long", entry_price=150.0, size="100"))
    db_session.commit()

    action_input = {"size": "100", "price": 155.0, "trade_id": trade.trade_id}
    response = client.post(f"/trades/{trade.trade_id}/exit", json=action_input)
    assert response.status_code == 200
    assert response.json()["status"] == "closed"

def test_exit_expired_trade(db_session):
    # Create an expired options trade
    trade_input = schemas.TradeCreate(
        symbol="SPY",
        trade_type="long",
        entry_price=5.0,
        size="1",
        option_type="CALL",
        strike=400,
        expiration_date=datetime.now() - timedelta(days=1)
    )
    trade = crud.create_trade(db_session, trade_input)
    db_session.commit()
    db_session.refresh(trade)

    response = client.post(f"/trades/{trade.trade_id}/exit-expired")
    assert response.status_code == 200
    assert response.json()["status"] == "closed"

def test_create_future_trade(db_session):
    trade_input = schemas.TradeCreate(
        symbol="ES",
        trade_type="long",
        entry_price=4200.0,
        size="1",
        is_contract=True
    )
    response = client.post("/trades/fut", json=trade_input.model_dump())
    assert response.status_code == 200
    assert response.json()["symbol"] == trade_input.symbol

def test_create_long_term_trade(db_session):
    trade_input = schemas.TradeCreate(
        symbol="MSFT",
        trade_type="long",
        entry_price=280.0,
        size="100"
    )
    response = client.post("/trades/lt", json=trade_input.model_dump())
    assert response.status_code == 200
    assert response.json()["symbol"] == trade_input.symbol

def test_check_and_exit_expired_trades(db_session):
    # Create an expired options trade
    trade_input = schemas.TradeCreate(
        symbol="QQQ",
        trade_type="short",
        entry_price=3.0,
        size="2",
        option_type="PUT",
        strike=350,
        expiration_date=datetime.now() - timedelta(days=1)
    )
    crud.create_trade(db_session, trade_input)
    db_session.commit()

    response = client.post("/trades/check-and-exit-expired")
    assert response.status_code == 200
    assert len(response.json()["exited_trades"]) > 0

def test_get_performance(db_session):
    response = client.get("/performance")
    assert response.status_code == 200
    assert "total_trades" in response.json()
    assert "total_profit_loss" in response.json()
    assert "win_rate" in response.json()
    assert "average_risk_reward_ratio" in response.json()

def test_database_url():
    db = next(override_get_db())
    assert str(db.bind.url) == SQLALCHEMY_TEST_DATABASE_URL
    db.close()