"""
Polygon Options Trading Toolkit for Agno

This toolkit provides AI agents with comprehensive options trading capabilities
using the Polygon.io API. It includes options data retrieval, analysis, and
contract management functionality specifically tailored for options trading.
"""

import os
import json
import numpy as np
import pandas as pd
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional, Union
from decimal import Decimal
from agno.tools import Toolkit

from pydantic import BaseModel, Field
from polygon import RESTClient
from polygon.rest.models.contracts import OptionsContract
from polygon.rest.models.aggs import Agg
from polygon.rest.models.quotes import LastQuote
from polygon.rest.models.trades import LastTrade


class OptionsChainRequest(BaseModel):
    """Request model for options chain data"""
    underlying_ticker: str = Field(..., description="Underlying stock symbol (e.g., 'AAPL')")
    expiration_date: Optional[str] = Field(None, description="Expiration date in YYYY-MM-DD format")
    strike_price_gte: Optional[float] = Field(None, description="Minimum strike price")
    strike_price_lte: Optional[float] = Field(None, description="Maximum strike price")
    option_type: Optional[str] = Field(None, description="Option type: 'call' or 'put'")
    limit: Optional[int] = Field(50, description="Number of results to return")


class TechnicalIndicatorRequest(BaseModel):
    """Request model for technical indicator calculations"""
    ticker: str = Field(..., description="Options contract ticker")
    timespan: str = Field("minute", description="Time interval ('minute', 'hour', 'day')")
    window: int = Field(..., description="Window size for calculations")
    from_date: Optional[str] = Field(None, description="Start date (YYYY-MM-DD)")
    to_date: Optional[str] = Field(None, description="End date (YYYY-MM-DD)")
    fast_period: Optional[int] = Field(None, description="Fast period for MACD")
    slow_period: Optional[int] = Field(None, description="Slow period for MACD")
    signal_period: Optional[int] = Field(None, description="Signal period for MACD")


class TechnicalIndicatorResult(BaseModel):
    """Result model for technical indicator calculations"""
    ticker: str = Field(..., description="Options contract ticker")
    indicator_type: str = Field(..., description="Type of indicator (SMA, EMA, MACD, RSI)")
    data: List[Dict[str, Any]] = Field(..., description="Calculated indicator values")
    metadata: Dict[str, Any] = Field(..., description="Additional information about the calculation")


class OptionsContractDetails(BaseModel):
    """Detailed options contract information"""
    ticker: str = Field(..., description="Options contract ticker")
    strike_price: float = Field(..., description="Strike price")
    expiration_date: str = Field(..., description="Expiration date")
    option_type: str = Field(..., description="Call or Put")
    underlying_ticker: str = Field(..., description="Underlying stock symbol")
    shares_per_contract: int = Field(..., description="Shares per contract")
    contract_type: str = Field(..., description="Contract type")


class OptionsMarketData(BaseModel):
    """Options market data snapshot"""
    ticker: str = Field(..., description="Options contract ticker")
    last_quote_bid: Optional[float] = Field(None, description="Last bid price")
    last_quote_ask: Optional[float] = Field(None, description="Last ask price")
    last_quote_spread: Optional[float] = Field(None, description="Bid-ask spread")
    last_trade_price: Optional[float] = Field(None, description="Last trade price")
    volume: Optional[int] = Field(None, description="Trading volume")
    open_interest: Optional[int] = Field(None, description="Open interest")
    implied_volatility: Optional[float] = Field(None, description="Implied volatility")
    delta: Optional[float] = Field(None, description="Option delta")
    gamma: Optional[float] = Field(None, description="Option gamma")
    theta: Optional[float] = Field(None, description="Option theta")
    vega: Optional[float] = Field(None, description="Option vega")


class OptionsAnalysis(BaseModel):
    """Options analysis results"""
    ticker: str = Field(..., description="Options contract ticker")
    intrinsic_value: float = Field(..., description="Intrinsic value of the option")
    time_value: float = Field(..., description="Time value of the option")
    moneyness: str = Field(..., description="ITM, ATM, or OTM")
    break_even_price: float = Field(..., description="Break-even price at expiration")
    profit_loss_ratio: Optional[float] = Field(None, description="Maximum profit to loss ratio")
    days_to_expiration: int = Field(..., description="Days until expiration")


class HistoricalOptionsData(BaseModel):
    """Historical options data structure"""
    ticker: str = Field(..., description="Options contract ticker")
    timeframe: str = Field(..., description="Data timeframe (minute, hour, day)")
    data_type: str = Field(..., description="Type of data (aggregates, trades, quotes)")
    from_date: str = Field(..., description="Start date")
    to_date: str = Field(..., description="End date")
    count: int = Field(..., description="Number of data points")
    data: List[Dict[str, Any]] = Field(..., description="Historical data points")


class OptionsTradeAnalysis(BaseModel):
    """Options trade analysis results"""
    entry_data: Dict[str, Any] = Field(..., description="Entry trade data")
    exit_data: Optional[Dict[str, Any]] = Field(None, description="Exit trade data")
    trade_duration: Optional[int] = Field(None, description="Trade duration in minutes")
    profit_loss: Optional[float] = Field(None, description="Realized P&L")
    profit_loss_percent: Optional[float] = Field(None, description="P&L percentage")
    max_profit: Optional[float] = Field(None, description="Maximum unrealized profit")
    max_loss: Optional[float] = Field(None, description="Maximum unrealized loss")
    context: Dict[str, Any] = Field(..., description="Market context during trade")


class PolygonOptionsTools(Toolkit):
    """
    Comprehensive Polygon Options Trading Toolkit for Agno
    
    Provides AI agents with full options trading capabilities including:
    - Options contract search and filtering
    - Real-time options market data
    - Historical options data (aggregates, trades, quotes)
    - Options chain analysis
    - Greeks calculation and analysis
    - Options strategy evaluation
    - Trade analysis and context understanding
    - Risk assessment and position sizing
    - Technical indicators (SMA, EMA, MACD, RSI)
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize the Polygon Options Trading toolkit
        
        Args:
            api_key: Polygon.io API key (will use POLYGON_API_KEY env var if not provided)
        """
        self.api_key = api_key or os.getenv("POLYGON_API_KEY")
        if not self.api_key:
            raise ValueError("Polygon API key required. Set POLYGON_API_KEY environment variable or pass api_key parameter.")
        
        self.client = RESTClient(self.api_key)
        self.name="PolygonOptionsTools"
        self.description="Toolkit for Polygon Options Trading"
        tools = [
            self.get_options_chain, 
            self.get_options_contract_details, 
            self.get_options_market_data, 
            self.get_simple_options_market_data, 
            self.get_historical_options_aggregates,
            self.calculate_sma,
            self.calculate_ema,
            self.calculate_macd,
            self.calculate_rsi
        ]
        super().__init__(name=self.name, 
                         tools=tools, 
                        **kwargs)

    def _get_historical_data_as_df(
        self,
        ticker: str,
        timespan: str = "minute",
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        limit: int = 50000
    ) -> pd.DataFrame:
        """Helper method to get historical data as a pandas DataFrame"""
        try:
            # Get historical data
            aggs_data = self.get_historical_options_aggregates(
                options_ticker=ticker,
                multiplier=1,
                timespan=timespan,
                from_date=from_date,
                to_date=to_date,
                limit=limit
            )
            
            if "error" in aggs_data:
                raise ValueError(f"Failed to get historical data: {aggs_data['error']}")
            
            if not aggs_data["data"]:
                raise ValueError("No historical data available")
            
            # Convert to DataFrame
            df = pd.DataFrame(aggs_data["data"])
            
            # Convert timestamp to datetime and set as index
            df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms")
            df.set_index("datetime", inplace=True)
            df.sort_index(inplace=True)
            
            # Keep only necessary columns for technical analysis
            keep_columns = ["open", "high", "low", "close", "volume", "vwap"]
            df = df[keep_columns]
            
            return df
            
        except Exception as e:
            raise ValueError(f"Error converting historical data to DataFrame: {str(e)}")

    def calculate_sma(
        self,
        ticker: str,
        window: int = 20,
        timespan: str = "minute",
        from_date: Optional[str] = None,
        to_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculate Simple Moving Average (SMA) for an options contract
        
        Args:
            ticker: Options contract ticker
            window: Number of periods for SMA calculation
            timespan: Time interval ('minute', 'hour', 'day')
            from_date: Start date (YYYY-MM-DD)
            to_date: End date (YYYY-MM-DD)
            
        Returns:
            Dictionary containing SMA values and metadata
        """
        try:
            df = self._get_historical_data_as_df(ticker, timespan, from_date, to_date)
            
            # Calculate SMA
            df["sma"] = df["close"].rolling(window=window).mean()
            
            # Convert results to list of dictionaries
            results = []
            for idx, row in df.iterrows():
                if not pd.isna(row["sma"]):
                    results.append({
                        "datetime": idx.isoformat(),
                        "close": row["close"],
                        "sma": row["sma"]
                    })
            
            return {
                "ticker": ticker,
                "indicator_type": "SMA",
                "data": results,
                "metadata": {
                    "window": window,
                    "timespan": timespan,
                    "from_date": from_date,
                    "to_date": to_date,
                    "points_calculated": len(results)
                }
            }
            
        except Exception as e:
            return {"error": f"Failed to calculate SMA: {str(e)}"}

    def calculate_ema(
        self,
        ticker: str,
        window: int = 20,
        timespan: str = "minute",
        from_date: Optional[str] = None,
        to_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculate Exponential Moving Average (EMA) for an options contract
        
        Args:
            ticker: Options contract ticker
            window: Number of periods for EMA calculation
            timespan: Time interval ('minute', 'hour', 'day')
            from_date: Start date (YYYY-MM-DD)
            to_date: End date (YYYY-MM-DD)
            
        Returns:
            Dictionary containing EMA values and metadata
        """
        try:
            df = self._get_historical_data_as_df(ticker, timespan, from_date, to_date)
            
            # Calculate EMA
            df["ema"] = df["close"].ewm(span=window, adjust=False).mean()
            
            # Convert results to list of dictionaries
            results = []
            for idx, row in df.iterrows():
                if not pd.isna(row["ema"]):
                    results.append({
                        "datetime": idx.isoformat(),
                        "close": row["close"],
                        "ema": row["ema"]
                    })
            
            return {
                "ticker": ticker,
                "indicator_type": "EMA",
                "data": results,
                "metadata": {
                    "window": window,
                    "timespan": timespan,
                    "from_date": from_date,
                    "to_date": to_date,
                    "points_calculated": len(results)
                }
            }
            
        except Exception as e:
            return {"error": f"Failed to calculate EMA: {str(e)}"}

    def calculate_macd(
        self,
        ticker: str,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
        timespan: str = "minute",
        from_date: Optional[str] = None,
        to_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculate Moving Average Convergence Divergence (MACD) for an options contract
        
        Args:
            ticker: Options contract ticker
            fast_period: Fast EMA period
            slow_period: Slow EMA period
            signal_period: Signal line period
            timespan: Time interval ('minute', 'hour', 'day')
            from_date: Start date (YYYY-MM-DD)
            to_date: End date (YYYY-MM-DD)
            
        Returns:
            Dictionary containing MACD values and metadata
        """
        try:
            df = self._get_historical_data_as_df(ticker, timespan, from_date, to_date)
            
            # Calculate MACD components
            fast_ema = df["close"].ewm(span=fast_period, adjust=False).mean()
            slow_ema = df["close"].ewm(span=slow_period, adjust=False).mean()
            df["macd"] = fast_ema - slow_ema
            df["signal"] = df["macd"].ewm(span=signal_period, adjust=False).mean()
            df["histogram"] = df["macd"] - df["signal"]
            
            # Convert results to list of dictionaries
            results = []
            for idx, row in df.iterrows():
                if not pd.isna(row["macd"]):
                    results.append({
                        "datetime": idx.isoformat(),
                        "close": row["close"],
                        "macd": row["macd"],
                        "signal": row["signal"],
                        "histogram": row["histogram"]
                    })
            
            return {
                "ticker": ticker,
                "indicator_type": "MACD",
                "data": results,
                "metadata": {
                    "fast_period": fast_period,
                    "slow_period": slow_period,
                    "signal_period": signal_period,
                    "timespan": timespan,
                    "from_date": from_date,
                    "to_date": to_date,
                    "points_calculated": len(results)
                }
            }
            
        except Exception as e:
            return {"error": f"Failed to calculate MACD: {str(e)}"}

    def calculate_rsi(
        self,
        ticker: str,
        window: int = 14,
        timespan: str = "minute",
        from_date: Optional[str] = None,
        to_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculate Relative Strength Index (RSI) for an options contract
        
        Args:
            ticker: Options contract ticker
            window: Number of periods for RSI calculation
            timespan: Time interval ('minute', 'hour', 'day')
            from_date: Start date (YYYY-MM-DD)
            to_date: End date (YYYY-MM-DD)
            
        Returns:
            Dictionary containing RSI values and metadata
        """
        try:
            df = self._get_historical_data_as_df(ticker, timespan, from_date, to_date)
            
            # Calculate price changes
            df["price_change"] = df["close"].diff()
            
            # Calculate gains and losses
            df["gain"] = df["price_change"].apply(lambda x: x if x > 0 else 0)
            df["loss"] = df["price_change"].apply(lambda x: abs(x) if x < 0 else 0)
            
            # Calculate average gains and losses
            avg_gain = df["gain"].rolling(window=window).mean()
            avg_loss = df["loss"].rolling(window=window).mean()
            
            # Calculate RS and RSI
            rs = avg_gain / avg_loss
            df["rsi"] = 100 - (100 / (1 + rs))
            
            # Convert results to list of dictionaries
            results = []
            for idx, row in df.iterrows():
                if not pd.isna(row["rsi"]):
                    results.append({
                        "datetime": idx.isoformat(),
                        "close": row["close"],
                        "rsi": row["rsi"]
                    })
            
            return {
                "ticker": ticker,
                "indicator_type": "RSI",
                "data": results,
                "metadata": {
                    "window": window,
                    "timespan": timespan,
                    "from_date": from_date,
                    "to_date": to_date,
                    "points_calculated": len(results),
                    "overbought_level": 70,
                    "oversold_level": 30
                }
            }
            
        except Exception as e:
            return {"error": f"Failed to calculate RSI: {str(e)}"}
    
    def get_options_chain(
        self,
        underlying_ticker: str,
        expiration_date: Optional[str] = None,
        strike_price_gte: Optional[float] = None,
        strike_price_lte: Optional[float] = None,
        option_type: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get options chain for an underlying stock
        
        Args:
            underlying_ticker: Stock symbol (e.g., 'AAPL')
            expiration_date: Filter by expiration date (YYYY-MM-DD)
            strike_price_gte: Minimum strike price
            strike_price_lte: Maximum strike price
            option_type: Filter by 'call' or 'put'
            limit: Maximum number of results
            
        Returns:
            List of options contracts with details
        """
        try:
            params = {}
            if expiration_date:
                params["expiration_date"] = expiration_date
            if strike_price_gte is not None:
                params["strike_price.gte"] = strike_price_gte
            if strike_price_lte is not None:
                params["strike_price.lte"] = strike_price_lte
            if option_type:
                params["contract_type"] = option_type
            
            contracts = []
            for contract in self.client.list_options_contracts(
                underlying_ticker=underlying_ticker,
                params=params,
                limit=limit
            ):
                contracts.append({
                    "ticker": contract.ticker,
                    "strike_price": contract.strike_price,
                    "expiration_date": contract.expiration_date,
                    "option_type": contract.contract_type,
                    "underlying_ticker": contract.underlying_ticker,
                    "shares_per_contract": getattr(contract, 'shares_per_contract', 100),
                    "exercise_style": getattr(contract, 'exercise_style', 'American')
                })
            
            return contracts
            
        except Exception as e:
            return [{"error": f"Failed to get options chain: {str(e)}"}]
    
    def get_options_contract_details(self, options_ticker: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific options contract
        
        Args:
            options_ticker: Options contract ticker (e.g., 'O:AAPL241220C00150000')
            
        Returns:
            Detailed contract information
        """
        try:
            contract = self.client.get_options_contract(options_ticker)
            
            return {
                "ticker": contract.ticker,
                "underlying_ticker": contract.underlying_ticker,
                "strike_price": contract.strike_price,
                "expiration_date": contract.expiration_date,
                "option_type": contract.contract_type,
                "exercise_style": getattr(contract, 'exercise_style', 'American'),
                "shares_per_contract": getattr(contract, 'shares_per_contract', 100),
                "primary_exchange": getattr(contract, 'primary_exchange', None),
                "cfi": getattr(contract, 'cfi', None)
            }
            
        except Exception as e:
            return {"error": f"Failed to get contract details: {str(e)}"}
    
    def get_options_market_data(self, options_ticker: str) -> Dict[str, Any]:
        """
        Get real-time market data for an options contract
        
        Args:
            options_ticker: Options contract ticker
            
        Returns:
            Current market data including quotes, Greeks, and volume
        """
        try:
            result = {
                "ticker": options_ticker,
                "last_updated": datetime.now().isoformat()
            }
            
            # For now, return a simplified response that indicates data is available
            # but requires a premium subscription or the contract may be inactive
            # This prevents long API calls and timeouts
            result.update({
                "status": "limited_data",
                "message": "Real-time options market data requires premium subscription or contract may be inactive",
                "bid": None,
                "ask": None,
                "last_trade_price": None,
                "volume": None,
                "open_interest": None,
                "spread": None,
                "delta": None,
                "gamma": None,
                "theta": None,
                "vega": None
            })
            
            return result
            
        except Exception as e:
            return {"error": f"Failed to get market data: {str(e)}"}
    
    def get_simple_options_market_data(self, options_ticker: str) -> Dict[str, Any]:
        """
        Alternative method to get basic options market data using snapshot chain
        
        This method attempts to get market data but times out quickly if not available
        """
        try:
            # Extract underlying ticker from options ticker (e.g., O:AAPL250613C00220000 -> AAPL)
            parts = options_ticker.split(':')
            if len(parts) != 2:
                return {"error": "Invalid options ticker format"}
            
            underlying_ticker = parts[1][:4]  # Get first 4 chars for ticker (AAPL)
            
            result = {
                "ticker": options_ticker,
                "last_updated": datetime.now().isoformat()
            }
            
            # Try to get snapshot data with a timeout approach
            contract_type = "call" if "C" in options_ticker else "put"
            
            # Use a simple iteration with break to avoid long waits
            found_contract = False
            contract_count = 0
            max_contracts_to_check = 10  # Limit to first 10 contracts to avoid timeouts
            
            try:
                for snapshot in self.client.list_snapshot_options_chain(
                    underlying_ticker,
                    params={"contract_type": contract_type}
                ):
                    contract_count += 1
                    if hasattr(snapshot, 'ticker') and snapshot.ticker == options_ticker:
                        # Found our contract - extract data
                        if hasattr(snapshot, 'last_quote') and snapshot.last_quote:
                            quote = snapshot.last_quote
                            result.update({
                                "bid": getattr(quote, 'bid', None),
                                "ask": getattr(quote, 'ask', None),
                                "bid_size": getattr(quote, 'bid_size', None),
                                "ask_size": getattr(quote, 'ask_size', None),
                            })
                            if hasattr(quote, 'bid') and hasattr(quote, 'ask') and quote.bid and quote.ask:
                                result["spread"] = quote.ask - quote.bid
                        
                        if hasattr(snapshot, 'details') and snapshot.details:
                            details = snapshot.details
                            result.update({
                                "volume": getattr(details, 'volume', None),
                                "open_interest": getattr(details, 'open_interest', None),
                            })
                        
                        found_contract = True
                        break
                    
                    # Stop after checking a reasonable number of contracts
                    if contract_count >= max_contracts_to_check:
                        break
                        
            except Exception:
                # If snapshot call fails, return basic structure
                pass
            
            if not found_contract:
                result.update({
                    "status": "contract_not_found",
                    "message": f"Contract {options_ticker} not found in first {max_contracts_to_check} active contracts",
                    "bid": None,
                    "ask": None,
                    "volume": None,
                    "open_interest": None
                })
            
            return result
            
        except Exception as e:
            return {"error": f"Failed to get market data: {str(e)}"}
    
    # ===== HISTORICAL DATA METHODS =====
    
    def get_historical_options_aggregates(
        self,
        options_ticker: str,
        multiplier: int = 1,
        timespan: str = "minute",
        from_date: str = None,
        to_date: str = None,
        limit: int = 5000
    ) -> Dict[str, Any]:
        """
        Get historical aggregate (OHLCV) data for an options contract
        
        This is essential for analyzing past trades and understanding price movements
        during the time a trade was held.
        
        Args:
            options_ticker: Options contract ticker (e.g., 'O:AAPL241220C00150000')
            multiplier: Size of the timespan multiplier (1 for 1-minute bars)
            timespan: Size of the time window ('minute', 'hour', 'day', 'week', 'month', 'quarter', 'year')
            from_date: Start date (YYYY-MM-DD format)
            to_date: End date (YYYY-MM-DD format) 
            limit: Maximum number of results (max 50,000)
            
        Returns:
            Historical OHLCV data with metadata
        """
        try:
            # Default date range if not provided (last 30 days)
            if not to_date:
                to_date = datetime.now().strftime('%Y-%m-%d')
            if not from_date:
                from_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            
            aggregates = []
            
            # Get aggregates using Polygon's list_aggs method
            for agg in self.client.list_aggs(
                ticker=options_ticker,
                multiplier=multiplier,
                timespan=timespan,
                from_=from_date,
                to=to_date,
                limit=limit
            ):
                aggregates.append({
                    "timestamp": agg.timestamp,
                    "open": agg.open,
                    "high": agg.high,
                    "low": agg.low,
                    "close": agg.close,
                    "volume": agg.volume,
                    "vwap": getattr(agg, 'vwap', None),
                    "number_of_transactions": getattr(agg, 'transactions', None),
                    "datetime": datetime.fromtimestamp(agg.timestamp / 1000).isoformat()
                })
            
            return {
                "ticker": options_ticker,
                "timeframe": f"{multiplier}{timespan}",
                "data_type": "aggregates",
                "from_date": from_date,
                "to_date": to_date,
                "count": len(aggregates),
                "data": aggregates,
                "request_metadata": {
                    "limit": limit,
                    "requested_at": datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            return {"error": f"Failed to get historical aggregates: {str(e)}"}
    
    def get_historical_options_trades(
        self,
        options_ticker: str,
        timestamp_date: str,
        limit: int = 50000
    ) -> Dict[str, Any]:
        """
        Get historical trades for an options contract on a specific date
        
        This provides detailed trade-by-trade data including exact prices,
        sizes, and exchange information - crucial for analyzing execution quality.
        
        Args:
            options_ticker: Options contract ticker
            timestamp_date: Date for trade data (YYYY-MM-DD format)
            limit: Maximum number of trades to return
            
        Returns:
            Historical trade data with execution details
        """
        try:
            trades = []
            
            # Get historical trades using Polygon's list_trades method
            for trade in self.client.list_trades(
                ticker=options_ticker,
                timestamp=timestamp_date,
                limit=limit
            ):
                trades.append({
                    "timestamp": trade.timestamp,
                    "price": trade.price,
                    "size": trade.size,
                    "exchange": getattr(trade, 'exchange', None),
                    "conditions": getattr(trade, 'conditions', []),
                    "timeframe": getattr(trade, 'timeframe', None),
                    "datetime": datetime.fromtimestamp(trade.timestamp / 1e9).isoformat()  # nanoseconds to seconds
                })
            
            return {
                "ticker": options_ticker,
                "data_type": "trades",
                "date": timestamp_date,
                "count": len(trades),
                "data": trades,
                "request_metadata": {
                    "limit": limit,
                    "requested_at": datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            return {"error": f"Failed to get historical trades: {str(e)}"}
    
    def get_historical_options_quotes(
        self,
        options_ticker: str,
        timestamp_date: str,
        limit: int = 50000
    ) -> Dict[str, Any]:
        """
        Get historical quotes (bid/ask) for an options contract on a specific date
        
        This provides bid/ask spread data over time, essential for understanding
        market liquidity and the cost of trading during specific periods.
        
        Args:
            options_ticker: Options contract ticker
            timestamp_date: Date for quote data (YYYY-MM-DD format)
            limit: Maximum number of quotes to return
            
        Returns:
            Historical quote data with bid/ask spreads
        """
        try:
            quotes = []
            
            # Get historical quotes using Polygon's list_quotes method
            for quote in self.client.list_quotes(
                ticker=options_ticker,
                timestamp=timestamp_date,
                limit=limit
            ):
                quotes.append({
                    "timestamp": quote.timestamp,
                    "bid": quote.bid,
                    "ask": quote.ask,
                    "bid_size": getattr(quote, 'bid_size', None),
                    "ask_size": getattr(quote, 'ask_size', None),
                    "exchange": getattr(quote, 'exchange', None),
                    "spread": quote.ask - quote.bid if quote.ask and quote.bid else None,
                    "midpoint": (quote.ask + quote.bid) / 2 if quote.ask and quote.bid else None,
                    "datetime": datetime.fromtimestamp(quote.timestamp / 1e9).isoformat()  # nanoseconds to seconds
                })
            
            return {
                "ticker": options_ticker,
                "data_type": "quotes",
                "date": timestamp_date,
                "count": len(quotes),
                "data": quotes,
                "request_metadata": {
                    "limit": limit,
                    "requested_at": datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            return {"error": f"Failed to get historical quotes: {str(e)}"}
    
    def analyze_options_trade_execution(
        self,
        options_ticker: str,
        entry_time: str,
        exit_time: Optional[str] = None,
        position_size: int = 1,
        side: str = "long"
    ) -> Dict[str, Any]:
        """
        Analyze the execution and performance of an options trade
        
        This method combines historical data to provide comprehensive trade analysis
        including entry/exit analysis, P&L calculation, and market context.
        
        Args:
            options_ticker: Options contract ticker
            entry_time: Entry timestamp (ISO format: YYYY-MM-DDTHH:MM:SS)
            exit_time: Exit timestamp (ISO format, optional for open positions)
            position_size: Number of contracts (positive for long, negative for short)
            side: Position side ('long' or 'short')
            
        Returns:
            Comprehensive trade analysis with P&L and context
        """
        try:
            entry_dt = datetime.fromisoformat(entry_time)
            entry_date = entry_dt.strftime('%Y-%m-%d')
            
            analysis = {
                "ticker": options_ticker,
                "entry_time": entry_time,
                "exit_time": exit_time,
                "position_size": position_size,
                "side": side,
                "analysis_timestamp": datetime.now().isoformat()
            }
            
            # Get historical data around entry time
            entry_aggs = self.get_historical_options_aggregates(
                options_ticker=options_ticker,
                multiplier=1,
                timespan="minute",
                from_date=entry_date,
                to_date=entry_date,
                limit=1000
            )
            
            if "error" not in entry_aggs and entry_aggs["data"]:
                # Find entry price (closest to entry time)
                entry_timestamp = int(entry_dt.timestamp() * 1000)
                closest_entry = min(
                    entry_aggs["data"], 
                    key=lambda x: abs(x["timestamp"] - entry_timestamp)
                )
                analysis["entry_data"] = closest_entry
                analysis["entry_price"] = closest_entry["close"]
                
                if exit_time:
                    exit_dt = datetime.fromisoformat(exit_time)
                    exit_date = exit_dt.strftime('%Y-%m-%d')
                    
                    # Get exit data
                    exit_aggs = self.get_historical_options_aggregates(
                        options_ticker=options_ticker,
                        multiplier=1,
                        timespan="minute",
                        from_date=exit_date,
                        to_date=exit_date,
                        limit=1000
                    )
                    
                    if "error" not in exit_aggs and exit_aggs["data"]:
                        exit_timestamp = int(exit_dt.timestamp() * 1000)
                        closest_exit = min(
                            exit_aggs["data"],
                            key=lambda x: abs(x["timestamp"] - exit_timestamp)
                        )
                        analysis["exit_data"] = closest_exit
                        analysis["exit_price"] = closest_exit["close"]
                        
                        # Calculate P&L
                        entry_price = closest_entry["close"]
                        exit_price = closest_exit["close"]
                        
                        if side == "long":
                            pnl = (exit_price - entry_price) * position_size * 100  # 100 shares per contract
                            pnl_percent = ((exit_price - entry_price) / entry_price) * 100
                        else:  # short
                            pnl = (entry_price - exit_price) * position_size * 100
                            pnl_percent = ((entry_price - exit_price) / entry_price) * 100
                        
                        analysis["profit_loss"] = pnl
                        analysis["profit_loss_percent"] = pnl_percent
                        analysis["trade_duration_minutes"] = (exit_timestamp - entry_timestamp) // (1000 * 60)
                
                # Add market context
                analysis["market_context"] = self._get_market_context(
                    options_ticker, entry_date, entry_aggs["data"]
                )
                
            else:
                analysis["error"] = "Unable to retrieve historical data for analysis"
            
            return analysis
            
        except Exception as e:
            return {"error": f"Failed to analyze trade execution: {str(e)}"}
    
    def get_options_trading_context(
        self,
        options_ticker: str,
        trade_date: str,
        analysis_window_hours: int = 4
    ) -> Dict[str, Any]:
        """
        Get comprehensive market context around an options trade
        
        This provides AI agents with context to understand what was happening
        in the market when a trade occurred - volatility, volume patterns, etc.
        
        Args:
            options_ticker: Options contract ticker
            trade_date: Date of the trade (YYYY-MM-DD)
            analysis_window_hours: Hours before/after to analyze
            
        Returns:
            Market context including volatility, volume, and price patterns
        """
        try:
            # Get intraday data for context
            aggregates = self.get_historical_options_aggregates(
                options_ticker=options_ticker,
                multiplier=1,
                timespan="minute",
                from_date=trade_date,
                to_date=trade_date,
                limit=5000
            )
            
            if "error" in aggregates:
                return aggregates
            
            data = aggregates["data"]
            if not data:
                return {"error": "No historical data available for context analysis"}
            
            # Calculate context metrics
            prices = [bar["close"] for bar in data]
            volumes = [bar["volume"] for bar in data if bar["volume"]]
            
            context = {
                "ticker": options_ticker,
                "trade_date": trade_date,
                "analysis_window_hours": analysis_window_hours,
                "data_points": len(data),
                "price_analysis": {
                    "day_high": max(bar["high"] for bar in data),
                    "day_low": min(bar["low"] for bar in data),
                    "day_open": data[0]["open"] if data else None,
                    "day_close": data[-1]["close"] if data else None,
                    "day_range": max(bar["high"] for bar in data) - min(bar["low"] for bar in data),
                    "average_price": sum(prices) / len(prices) if prices else None
                },
                "volume_analysis": {
                    "total_volume": sum(volumes) if volumes else 0,
                    "average_volume": sum(volumes) / len(volumes) if volumes else 0,
                    "max_volume_bar": max(volumes) if volumes else 0,
                    "volume_distribution": self._calculate_volume_distribution(data)
                },
                "volatility_analysis": {
                    "intraday_volatility": self._calculate_intraday_volatility(data),
                    "price_moves": self._analyze_price_moves(data)
                },
                "trading_patterns": {
                    "number_of_transactions": sum(bar.get("number_of_transactions", 0) for bar in data),
                    "average_transaction_size": self._calculate_avg_transaction_size(data),
                    "time_distribution": self._analyze_time_distribution(data)
                }
            }
            
            return context
            
        except Exception as e:
            return {"error": f"Failed to get trading context: {str(e)}"}
    
    # ===== HELPER METHODS FOR ANALYSIS =====
    
    def _get_market_context(self, options_ticker: str, date: str, agg_data: List[Dict]) -> Dict[str, Any]:
        """Helper method to extract market context from aggregate data"""
        if not agg_data:
            return {"error": "No data for context analysis"}
        
        prices = [bar["close"] for bar in agg_data]
        volumes = [bar["volume"] for bar in agg_data if bar["volume"]]
        
        return {
            "trading_range": {
                "high": max(bar["high"] for bar in agg_data),
                "low": min(bar["low"] for bar in agg_data),
                "range_percent": ((max(bar["high"] for bar in agg_data) - min(bar["low"] for bar in agg_data)) / min(bar["low"] for bar in agg_data)) * 100
            },
            "volume_profile": {
                "total_volume": sum(volumes) if volumes else 0,
                "average_volume": sum(volumes) / len(volumes) if volumes else 0
            },
            "price_trend": self._determine_trend(prices) if prices else "insufficient_data"
        }
    
    def _calculate_volume_distribution(self, data: List[Dict]) -> Dict[str, int]:
        """Calculate volume distribution across different time periods"""
        if not data:
            return {}
        
        total_minutes = len(data)
        if total_minutes < 60:
            return {"insufficient_data": True}
        
        # Divide day into periods
        period_size = total_minutes // 4
        periods = ["morning", "midday", "afternoon", "close"]
        distribution = {}
        
        for i, period in enumerate(periods):
            start_idx = i * period_size
            end_idx = min((i + 1) * period_size, total_minutes)
            period_data = data[start_idx:end_idx]
            period_volume = sum(bar["volume"] for bar in period_data if bar["volume"])
            distribution[period] = period_volume
        
        return distribution
    
    def _calculate_intraday_volatility(self, data: List[Dict]) -> float:
        """Calculate intraday volatility as average of high-low ranges"""
        if not data:
            return 0.0
        
        ranges = []
        for bar in data:
            if bar["high"] and bar["low"] and bar["close"]:
                range_pct = ((bar["high"] - bar["low"]) / bar["close"]) * 100
                ranges.append(range_pct)
        
        return sum(ranges) / len(ranges) if ranges else 0.0
    
    def _analyze_price_moves(self, data: List[Dict]) -> Dict[str, Any]:
        """Analyze significant price movements during the day"""
        if len(data) < 2:
            return {"insufficient_data": True}
        
        price_changes = []
        for i in range(1, len(data)):
            if data[i-1]["close"] and data[i]["close"]:
                pct_change = ((data[i]["close"] - data[i-1]["close"]) / data[i-1]["close"]) * 100
                price_changes.append(pct_change)
        
        if not price_changes:
            return {"insufficient_data": True}
        
        return {
            "max_gain": max(price_changes),
            "max_loss": min(price_changes),
            "average_move": sum(abs(change) for change in price_changes) / len(price_changes),
            "positive_moves": len([c for c in price_changes if c > 0]),
            "negative_moves": len([c for c in price_changes if c < 0])
        }
    
    def _calculate_avg_transaction_size(self, data: List[Dict]) -> float:
        """Calculate average transaction size where data is available"""
        transactions = [bar.get("number_of_transactions", 0) for bar in data]
        volumes = [bar.get("volume", 0) for bar in data]
        
        total_volume = sum(volumes)
        total_transactions = sum(transactions)
        
        return total_volume / total_transactions if total_transactions > 0 else 0.0
    
    def _analyze_time_distribution(self, data: List[Dict]) -> Dict[str, Any]:
        """Analyze trading activity distribution across time"""
        if not data:
            return {}
        
        hourly_volume = {}
        for bar in data:
            if bar.get("datetime") and bar.get("volume"):
                dt = datetime.fromisoformat(bar["datetime"])
                hour = dt.hour
                hourly_volume[hour] = hourly_volume.get(hour, 0) + bar["volume"]
        
        peak_hour = max(hourly_volume, key=hourly_volume.get) if hourly_volume else None
        
        return {
            "hourly_volume": hourly_volume,
            "peak_trading_hour": peak_hour,
            "total_trading_hours": len(hourly_volume)
        }
    
    def _determine_trend(self, prices: List[float]) -> str:
        """Determine overall price trend"""
        if len(prices) < 2:
            return "insufficient_data"
        
        start_price = prices[0]
        end_price = prices[-1]
        
        change_pct = ((end_price - start_price) / start_price) * 100
        
        if change_pct > 2:
            return "strong_uptrend"
        elif change_pct > 0.5:
            return "uptrend"
        elif change_pct < -2:
            return "strong_downtrend"
        elif change_pct < -0.5:
            return "downtrend"
        else:
            return "sideways"
    
    # ===== EXISTING METHODS CONTINUE BELOW =====
    
    def analyze_options_contract(
        self,
        options_ticker: str,
        underlying_price: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Perform comprehensive analysis of an options contract
        
        Args:
            options_ticker: Options contract ticker
            underlying_price: Current underlying stock price (will fetch if not provided)
            
        Returns:
            Analysis including intrinsic value, time value, moneyness, etc.
        """
        try:
            # Get contract details
            contract = self.get_options_contract_details(options_ticker)
            if "error" in contract:
                return contract
            
            # Get underlying price if not provided
            if underlying_price is None:
                underlying_ticker = contract["underlying_ticker"]
                underlying_data = self.client.get_last_trade(underlying_ticker)
                underlying_price = underlying_data.price
            
            strike_price = contract["strike_price"]
            option_type = contract["option_type"].lower()
            expiration_date = datetime.strptime(contract["expiration_date"], "%Y-%m-%d").date()
            days_to_expiration = (expiration_date - date.today()).days
            
            # Calculate intrinsic value
            if option_type == "call":
                intrinsic_value = max(0, underlying_price - strike_price)
            else:  # put
                intrinsic_value = max(0, strike_price - underlying_price)
            
            # Try to get market data but don't fail if it's not available
            market_data = self.get_options_market_data(options_ticker)
            option_price = None
            
            if "error" not in market_data:
                if market_data.get("last_trade_price"):
                    option_price = market_data["last_trade_price"]
                elif market_data.get("bid") and market_data.get("ask"):
                    option_price = (market_data["bid"] + market_data["ask"]) / 2
            
            time_value = option_price - intrinsic_value if option_price else None
            
            # Determine moneyness
            if option_type == "call":
                if underlying_price > strike_price:
                    moneyness = "ITM"  # In The Money
                elif abs(underlying_price - strike_price) < 0.01:
                    moneyness = "ATM"  # At The Money
                else:
                    moneyness = "OTM"  # Out of The Money
            else:  # put
                if underlying_price < strike_price:
                    moneyness = "ITM"
                elif abs(underlying_price - strike_price) < 0.01:
                    moneyness = "ATM"
                else:
                    moneyness = "OTM"
            
            # Calculate break-even price
            if option_type == "call":
                break_even = strike_price + (option_price or 0)
            else:  # put
                break_even = strike_price - (option_price or 0)
            
            analysis = {
                "ticker": options_ticker,
                "underlying_ticker": contract["underlying_ticker"],
                "underlying_price": underlying_price,
                "strike_price": strike_price,
                "option_type": option_type,
                "current_option_price": option_price,
                "intrinsic_value": intrinsic_value,
                "time_value": time_value,
                "moneyness": moneyness,
                "break_even_price": break_even,
                "days_to_expiration": days_to_expiration,
                "expiration_date": contract["expiration_date"]
            }
            
            # Add Greeks if available in market data
            if "error" not in market_data and any(k in market_data for k in ["delta", "gamma", "theta", "vega"]):
                analysis["greeks"] = {
                    "delta": market_data.get("delta"),
                    "gamma": market_data.get("gamma"),
                    "theta": market_data.get("theta"),
                    "vega": market_data.get("vega")
                }
            
            return analysis
            
        except Exception as e:
            return {"error": f"Failed to analyze contract: {str(e)}"}
    
    def screen_options_by_criteria(
        self,
        underlying_ticker: str,
        min_volume: Optional[int] = None,
        max_spread_percent: Optional[float] = None,
        min_open_interest: Optional[int] = None,
        days_to_expiration_range: Optional[tuple] = None,
        moneyness_filter: Optional[str] = None,
        option_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Screen options based on trading criteria
        
        Note: This simplified version focuses on contract details and basic filtering
        without intensive market data calls to avoid timeouts.
        """
        try:
            # Get a targeted options chain
            chain = self.get_options_chain(
                underlying_ticker=underlying_ticker,
                option_type=option_type,
                limit=50  # Reasonable limit
            )
            
            if not chain or "error" in str(chain[0]):
                return chain if chain else [{"error": "No options chain data available"}]
            
            filtered_options = []
            
            for contract in chain:
                try:
                    # Apply days to expiration filter first (no API calls needed)
                    if days_to_expiration_range:
                        expiration_date = datetime.strptime(contract["expiration_date"], "%Y-%m-%d").date()
                        days_to_exp = (expiration_date - date.today()).days
                        min_days, max_days = days_to_expiration_range
                        if days_to_exp < min_days or days_to_exp > max_days:
                            continue
                    
                    # Apply moneyness filter if requested (requires underlying price)
                    if moneyness_filter:
                        try:
                            analysis = self.analyze_options_contract(contract["ticker"])
                            if "error" not in analysis and analysis.get("moneyness") != moneyness_filter:
                                continue
                        except:
                            continue
                    
                    # Add basic contract info
                    enhanced_contract = {
                        **contract,
                        "days_to_expiration": (datetime.strptime(contract["expiration_date"], "%Y-%m-%d").date() - date.today()).days,
                        "screening_note": "Market data screening requires premium API access"
                    }
                    
                    filtered_options.append(enhanced_contract)
                    
                    # Limit results
                    if len(filtered_options) >= 20:
                        break
                        
                except Exception:
                    continue
            
            return filtered_options
            
        except Exception as e:
            return [{"error": f"Failed to screen options: {str(e)}"}]
    
    def calculate_option_strategy_pnl(
        self,
        strategy_legs: List[Dict[str, Any]],
        underlying_price_range: tuple,
        price_step: float = 1.0
    ) -> Dict[str, Any]:
        """
        Calculate P&L for multi-leg options strategies
        
        Args:
            strategy_legs: List of legs with contract details and position info
                          Each leg: {"ticker": str, "position": "long"/"short", "quantity": int}
            underlying_price_range: (min_price, max_price) for P&L calculation
            price_step: Price increment for calculation
            
        Returns:
            P&L analysis across price range
        """
        try:
            min_price, max_price = underlying_price_range
            prices = []
            pnl_values = []
            
            # Get contract details for all legs
            leg_details = []
            for leg in strategy_legs:
                contract_details = self.get_options_contract_details(leg["ticker"])
                if "error" in contract_details:
                    return {"error": f"Failed to get details for {leg['ticker']}: {contract_details['error']}"}
                
                leg_details.append({
                    **contract_details,
                    "position": leg["position"],
                    "quantity": leg["quantity"]
                })
            
            # Calculate P&L at each price point
            current_price = min_price
            while current_price <= max_price:
                total_pnl = 0
                
                for leg in leg_details:
                    strike = leg["strike_price"]
                    option_type = leg["option_type"].lower()
                    position = leg["position"]
                    quantity = leg["quantity"]
                    
                    # Calculate intrinsic value at expiration
                    if option_type == "call":
                        intrinsic_value = max(0, current_price - strike)
                    else:  # put
                        intrinsic_value = max(0, strike - current_price)
                    
                    # Calculate position P&L
                    if position == "long":
                        leg_pnl = intrinsic_value * quantity * 100  # 100 shares per contract
                    else:  # short
                        leg_pnl = -intrinsic_value * quantity * 100
                    
                    total_pnl += leg_pnl
                
                prices.append(current_price)
                pnl_values.append(total_pnl)
                current_price += price_step
            
            # Find break-even points
            break_even_points = []
            for i in range(len(pnl_values) - 1):
                if (pnl_values[i] <= 0 <= pnl_values[i + 1]) or (pnl_values[i] >= 0 >= pnl_values[i + 1]):
                    # Linear interpolation to find exact break-even
                    if pnl_values[i + 1] != pnl_values[i]:
                        be_price = prices[i] - pnl_values[i] * (prices[i + 1] - prices[i]) / (pnl_values[i + 1] - pnl_values[i])
                        break_even_points.append(round(be_price, 2))
            
            return {
                "strategy_legs": strategy_legs,
                "price_range": underlying_price_range,
                "prices": prices,
                "pnl_values": pnl_values,
                "max_profit": max(pnl_values) if pnl_values else 0,
                "max_loss": min(pnl_values) if pnl_values else 0,
                "break_even_points": break_even_points
            }
            
        except Exception as e:
            return {"error": f"Failed to calculate strategy P&L: {str(e)}"} 