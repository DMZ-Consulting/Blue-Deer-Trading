"""
Theta Data Options Trading Toolkit for Agno

This toolkit provides AI agents with comprehensive historical options data capabilities
using the Theta Data REST API. It includes options data retrieval, analysis, and
contract management functionality specifically tailored for options trading research
and analysis.

Theta Data provides tick-level and aggregated historical options data with extensive
coverage going back to 2012 for some subscription tiers.
"""

import os
import json
import numpy as np
import pandas as pd
import requests
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional, Union
from decimal import Decimal
from agno.tools import Toolkit
from pydantic import BaseModel, Field

try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False


class ThetaDataError(Exception):
    """Custom exception for Theta Data API errors"""
    pass


class OptionsHistoricalRequest(BaseModel):
    """Request model for historical options data"""
    root: str = Field(..., description="Underlying symbol (e.g., 'AAPL')")
    exp: int = Field(..., description="Expiration date formatted as YYYYMMDD")
    strike: int = Field(..., description="Strike price in 1/10th of a cent (e.g., 170000 for $170.00)")
    right: str = Field(..., description="Option type: 'C' for call, 'P' for put")
    start_date: int = Field(..., description="Start date formatted as YYYYMMDD")
    end_date: int = Field(..., description="End date formatted as YYYYMMDD")
    ivl: Optional[int] = Field(0, description="Interval size in milliseconds (0 for tick data, 60000 for 1-minute)")
    rth: Optional[bool] = Field(True, description="Regular trading hours only")


class OptionsList(BaseModel):
    """Request model for listing options data"""
    root: str = Field(..., description="Underlying symbol")
    exp: Optional[int] = Field(None, description="Expiration date formatted as YYYYMMDD")
    strike: Optional[int] = Field(None, description="Strike price in 1/10th of a cent")
    right: Optional[str] = Field(None, description="Option type: 'C' or 'P'")


class ThetaDataResponse(BaseModel):
    """Response model for Theta Data API responses"""
    header: Dict[str, Any] = Field(..., description="Response header with format and metadata")
    response: List[List[Any]] = Field(..., description="Response data as array of arrays")


class OptionsContractInfo(BaseModel):
    """Options contract information"""
    root: str = Field(..., description="Underlying symbol")
    exp: int = Field(..., description="Expiration date")
    strike: int = Field(..., description="Strike price in 1/10th of a cent")
    right: str = Field(..., description="Call or Put")
    strike_price_dollars: float = Field(..., description="Strike price in dollars")
    expiration_date_formatted: str = Field(..., description="Human-readable expiration date")


class HistoricalOptionsData(BaseModel):
    """Historical options data structure"""
    contract: OptionsContractInfo = Field(..., description="Contract information")
    data_type: str = Field(..., description="Type of data (ohlc, quotes, trades, greeks)")
    timeframe: str = Field(..., description="Data timeframe")
    from_date: str = Field(..., description="Start date")
    to_date: str = Field(..., description="End date")
    count: int = Field(..., description="Number of data points")
    data: List[Dict[str, Any]] = Field(..., description="Historical data points")


class ThetaDataOptionsTools(Toolkit):
    """
    Comprehensive Theta Data Options Trading Toolkit for Agno
    
    Provides AI agents with historical options trading capabilities including:
    - Historical options OHLC data
    - Historical options quotes (bid/ask)
    - Historical options trades
    - Options Greeks calculations (delta, gamma, theta, vega, etc.)
    - Historical implied volatility data (bid, mid, ask IVs)
    - Options open interest data
    - Options contract listing and discovery
    - Comprehensive data analysis and formatting
    
    AI-Friendly Features:
    - Auto-compression when data exceeds token limits (default: 5000 tokens)
    - Intelligent data summarization with key insights
    - Statistical analysis and trading signals
    - Token counting and cost estimation
    
    Note: Requires the Theta Data Terminal to be running locally on port 25510
    """
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        ai_friendly_default: bool = True,
        token_threshold: int = 5000,
        **kwargs
    ):
        """
        Initialize the Theta Data Options Trading toolkit
        
        Args:
            base_url: Theta Data API base URL (defaults to local terminal)
            ai_friendly_default: Default AI-friendly compression for all tools
            token_threshold: Auto-compress data if token count exceeds this limit
        """
        self.base_url = base_url or "http://127.0.0.1:25510"
        self.name = "ThetaDataOptionsTools"
        self.description = "Toolkit for Theta Data Historical Options Trading"
        
        # AI-friendly settings
        self.ai_friendly_default = ai_friendly_default
        self.token_threshold = token_threshold
        
        # Initialize tiktoken encoder for token counting
        self.token_encoder = None
        if TIKTOKEN_AVAILABLE:
            try:
                self.token_encoder = tiktoken.get_encoding("cl100k_base")  # GPT-4 encoding
            except Exception:
                self.token_encoder = None
        
        tools = [
            self.get_historical_options_ohlc,
            self.get_historical_options_quotes,
            self.get_historical_options_trades,
            self.get_historical_options_greeks,
            self.get_historical_options_implied_volatility,
            self.get_historical_options_open_interest,
            self.get_options_eod_report,
            self.list_options_expirations,
            self.list_options_strikes,
            self.list_available_dates,
            self.get_bulk_historical_options_data,
            self.analyze_options_historical_data,
            self.get_options_summary_for_ai
        ]
        super().__init__(name=self.name, tools=tools, **kwargs)

    def count_tokens(self, text: Union[str, Dict, List], model: str = "gpt-4") -> Dict[str, Any]:
        """
        Count tokens in text/data using tiktoken for accurate LLM token estimation.
        
        Args:
            text: Text string or JSON-serializable data structure to count tokens for
            model: Model name for encoding selection (gpt-4, gpt-3.5-turbo, etc.)
            
        Returns:
            Dictionary with token count and additional metadata
        """
        # Convert data to string if needed
        if isinstance(text, (dict, list)):
            text_str = json.dumps(text, default=str, separators=(',', ':'))
        else:
            text_str = str(text)
        
        # Try to use tiktoken for accurate counting
        if TIKTOKEN_AVAILABLE and self.token_encoder:
            try:
                tokens = self.token_encoder.encode(text_str)
                token_count = len(tokens)
                
                return {
                    "token_count": token_count,
                    "character_count": len(text_str),
                    "estimated_cost_gpt4": token_count * 0.00003,  # $0.03 per 1K tokens (approx)
                    "estimated_cost_gpt35": token_count * 0.000002,  # $0.002 per 1K tokens (approx)
                    "method": "tiktoken_accurate",
                    "encoding": "cl100k_base",
                    "compressibility_ratio": len(text_str) / token_count if token_count > 0 else 0
                }
            except Exception as e:
                # Fallback to estimation
                pass
        
        # Fallback estimation (roughly 4 characters per token)
        estimated_tokens = len(text_str) // 4
        return {
            "token_count": estimated_tokens,
            "character_count": len(text_str),
            "estimated_cost_gpt4": estimated_tokens * 0.00003,
            "estimated_cost_gpt35": estimated_tokens * 0.000002,
            "method": "estimated_fallback",
            "encoding": "character_based_estimate",
            "compressibility_ratio": 4.0
        }

    def analyze_data_token_efficiency(
        self, 
        raw_data: Dict[str, Any], 
        compressed_data: Dict[str, Any],
        model: str = "gpt-4"
    ) -> Dict[str, Any]:
        """
        Analyze token efficiency between raw and compressed data.
        
        Args:
            raw_data: Original uncompressed data
            compressed_data: AI-friendly compressed data
            model: Model to analyze for
            
        Returns:
            Efficiency analysis with token counts and savings
        """
        raw_tokens = self.count_tokens(raw_data, model)
        compressed_tokens = self.count_tokens(compressed_data, model)
        
        # Calculate efficiency metrics
        token_reduction = raw_tokens["token_count"] - compressed_tokens["token_count"]
        compression_ratio = raw_tokens["token_count"] / compressed_tokens["token_count"] if compressed_tokens["token_count"] > 0 else 0
        cost_savings_gpt4 = raw_tokens["estimated_cost_gpt4"] - compressed_tokens["estimated_cost_gpt4"]
        cost_savings_gpt35 = raw_tokens["estimated_cost_gpt35"] - compressed_tokens["estimated_cost_gpt35"]
        
        return {
            "raw_analysis": raw_tokens,
            "compressed_analysis": compressed_tokens,
            "efficiency_metrics": {
                "token_reduction": token_reduction,
                "compression_ratio": compression_ratio,
                "percentage_reduction": (token_reduction / raw_tokens["token_count"] * 100) if raw_tokens["token_count"] > 0 else 0,
                "cost_savings": {
                    "gpt4_dollars": cost_savings_gpt4,
                    "gpt35_dollars": cost_savings_gpt35
                },
                "data_preservation": {
                    "insights_added": len(compressed_data.get("insights", [])),
                    "statistics_added": len(compressed_data.get("statistics", {})),
                    "samples_included": len(compressed_data.get("samples", [])),
                    "total_records": compressed_data.get("total_records", 0)
                }
            },
            "recommendation": self._get_compression_recommendation(compression_ratio, token_reduction)
        }

    def _get_compression_recommendation(self, compression_ratio: float, token_reduction: int) -> str:
        """Generate recommendation based on compression efficiency"""
        if compression_ratio > 10:
            return "EXCELLENT: >10x compression with preserved insights"
        elif compression_ratio > 5:
            return "VERY_GOOD: 5-10x compression maintains data value"
        elif compression_ratio > 2:
            return "GOOD: 2-5x compression provides reasonable efficiency"
        elif compression_ratio > 1:
            return "MINIMAL: <2x compression, consider raw data for simple cases"
        else:
            return "INEFFICIENT: Compression added overhead without benefit"

    def _should_compress_data(self, data: List[Dict[str, Any]], force_ai_friendly: Optional[bool] = None) -> bool:
        """
        Determine if data should be compressed based on tool settings and token count.
        
        Args:
            data: Raw data to evaluate
            force_ai_friendly: Override the default setting
            
        Returns:
            True if data should be compressed
        """
        # Check explicit override first
        if force_ai_friendly is not None:
            return force_ai_friendly
        
        # Use tool default if no override
        if self.ai_friendly_default:
            return True
        
        # Check token threshold even if ai_friendly_default is False
        if data and self.token_threshold > 0:
            token_analysis = self.count_tokens(data)
            if token_analysis["token_count"] > self.token_threshold:
                return True
        
        return False

    def _prepare_data_response(
        self,
        parsed_data: List[Dict[str, Any]],
        contract_info: OptionsContractInfo,
        data_type: str,
        params: Dict[str, Any],
        raw_data: Dict[str, Any],
        ai_friendly: Optional[bool] = None,
        max_samples: int = 10,
        additional_fields: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Prepare standardized data response with optional AI-friendly compression.
        
        Args:
            parsed_data: Processed data from API
            contract_info: Contract information
            data_type: Type of data (ohlc, trades, etc.)
            params: Original request parameters
            raw_data: Raw API response
            ai_friendly: Override compression setting
            max_samples: Max samples for compression
            additional_fields: Extra fields to add to response
            
        Returns:
            Formatted response dictionary
        """
        base_response = {
            "success": True,
            "contract": contract_info.dict(),
            "data_type": data_type,
            "count": len(parsed_data)
        }
        
        # Add additional fields if provided
        if additional_fields:
            base_response.update(additional_fields)
        
        # Determine if we should compress
        should_compress = self._should_compress_data(parsed_data, ai_friendly)
        
        if should_compress:
            # Return compressed data for AI agents
            compressed = self._compress_data_for_ai(parsed_data, data_type, max_samples)
            base_response.update(compressed)
            base_response["ai_optimized"] = True
            
            # Add token efficiency info if we auto-compressed due to size
            if ai_friendly is None and not self.ai_friendly_default:
                token_analysis = self.count_tokens(parsed_data)
                base_response["auto_compressed"] = True
                base_response["reason"] = f"Data exceeded {self.token_threshold} token limit ({token_analysis['token_count']} tokens)"
        else:
            # Return full data
            base_response.update({
                "data": parsed_data,
                "metadata": {
                    "header": raw_data.get('header', {}),
                    "request_params": params
                }
            })
        
        return base_response

    def _compress_data_for_ai(
        self,
        data: List[Dict[str, Any]], 
        data_type: str,
        max_samples: int = 10,
        include_statistics: bool = True
    ) -> Dict[str, Any]:
        """
        Compress large datasets into AI-friendly summaries with key insights.
        
        Args:
            data: Raw data array
            data_type: Type of data for specialized compression
            max_samples: Maximum number of sample records to include
            include_statistics: Whether to include statistical summaries
        
        Returns:
            Compressed data structure optimized for AI consumption
        """
        if not data:
            return {"samples": [], "statistics": {}, "insights": []}
        
        compressed = {
            "total_records": len(data),
            "samples": data[:max_samples] if len(data) > max_samples else data,
            "statistics": {},
            "insights": []
        }
        
        # Add data-type specific statistics and insights
        if data_type == "ohlc":
            compressed.update(self._compress_ohlc_data(data))
        elif data_type == "trades":
            compressed.update(self._compress_trade_data(data))
        elif data_type == "implied_volatility":
            compressed.update(self._compress_iv_data(data))
        elif data_type == "greeks":
            compressed.update(self._compress_greeks_data(data))
        elif data_type == "quotes":
            compressed.update(self._compress_quote_data(data))
        elif data_type == "open_interest":
            compressed.update(self._compress_oi_data(data))
            
        return compressed
    
    def _compress_ohlc_data(self, data: List[Dict]) -> Dict[str, Any]:
        """Compress OHLC data with price movement insights"""
        prices = [r.get('close', 0) for r in data if r.get('close', 0) > 0]
        highs = [r.get('high', 0) for r in data if r.get('high', 0) > 0]
        lows = [r.get('low', 0) for r in data if r.get('low', 0) > 0]
        opens = [r.get('open', 0) for r in data if r.get('open', 0) > 0]
        volumes = [r.get('volume', 0) for r in data if r.get('volume', 0) > 0]
        
        if not prices:
            return {"statistics": {}, "insights": ["No valid price data"]}
        
        # Basic price statistics
        price_change = prices[-1] - prices[0] if len(prices) > 1 else 0
        price_change_pct = ((prices[-1] - prices[0]) / prices[0] * 100) if len(prices) > 1 and prices[0] != 0 else 0
        
        # Advanced numerical indicators
        import numpy as np
        
        # Volatility measures
        price_returns = [(prices[i] - prices[i-1]) / prices[i-1] for i in range(1, len(prices)) if prices[i-1] != 0]
        price_volatility = np.std(price_returns) * 100 if price_returns else 0  # As percentage
        
        # High-low spreads (intraday volatility)
        hl_spreads = [(h - l) / l * 100 for h, l in zip(highs, lows) if l > 0]
        avg_intraday_volatility = np.mean(hl_spreads) if hl_spreads else 0
        
        # Volume analysis
        total_volume = sum(volumes) if volumes else 0
        avg_volume = np.mean(volumes) if volumes else 0
        volume_weighted_price = sum(p * v for p, v in zip(prices, volumes)) / total_volume if total_volume > 0 else 0
        
        # Trend analysis
        price_trend_strength = 0
        if len(prices) >= 3:
            # Simple momentum: compare first third vs last third
            first_third = np.mean(prices[:len(prices)//3])
            last_third = np.mean(prices[-len(prices)//3:])
            price_trend_strength = ((last_third - first_third) / first_third * 100) if first_third > 0 else 0
        
        # Price distribution
        price_percentiles = {}
        if len(prices) >= 5:
            price_percentiles = {
                "25th": np.percentile(prices, 25),
                "50th": np.percentile(prices, 50),  # median
                "75th": np.percentile(prices, 75)
            }
        
        stats = {
            # Basic metrics
            "price_range": {"low": min(prices), "high": max(prices)},
            "price_change": price_change,
            "price_change_pct": price_change_pct,
            "average_price": np.mean(prices),
            "current_price": prices[-1] if prices else 0,
            "opening_price": prices[0] if prices else 0,
            
            # Volume metrics
            "total_volume": total_volume,
            "average_volume": avg_volume,
            "volume_weighted_price": volume_weighted_price,
            "volume_to_price_ratio": total_volume / np.mean(prices) if prices else 0,
            
            # Volatility metrics
            "price_volatility_pct": price_volatility,
            "intraday_volatility_pct": avg_intraday_volatility,
            "price_range_ratio": ((max(prices) - min(prices)) / min(prices) * 100) if prices and min(prices) > 0 else 0,
            
            # Trend and momentum
            "trend_strength_pct": price_trend_strength,
            "price_momentum": price_change_pct,  # Alias for clarity
            
            # Statistical measures
            "price_percentiles": price_percentiles,
            "records_count": len(data)
        }
        
        insights = []
        
        # Price movement insights
        if abs(price_change_pct) > 10:
            direction = "surged" if price_change_pct > 0 else "plunged"
            insights.append(f"Price {direction} {abs(price_change_pct):.1f}% - significant movement")
        elif abs(price_change_pct) > 5:
            direction = "gained" if price_change_pct > 0 else "declined"
            insights.append(f"Price {direction} {abs(price_change_pct):.1f}% - moderate movement")
        else:
            insights.append(f"Price stable with {abs(price_change_pct):.1f}% change")
        
        # Volatility insights
        if price_volatility > 5:
            insights.append(f"High volatility: {price_volatility:.1f}% - unstable pricing")
        elif price_volatility < 1:
            insights.append(f"Low volatility: {price_volatility:.1f}% - stable pricing")
        
        # Volume insights
        if total_volume > 1000:
            insights.append(f"High volume: {total_volume:,} contracts - strong interest")
        elif total_volume < 100:
            insights.append(f"Low volume: {total_volume:,} contracts - limited liquidity")
        
        # Trend insights
        if abs(price_trend_strength) > 3:
            direction = "bullish" if price_trend_strength > 0 else "bearish"
            insights.append(f"Strong {direction} trend: {abs(price_trend_strength):.1f}%")
        
        return {"statistics": stats, "insights": insights}
    
    def _compress_trade_data(self, data: List[Dict]) -> Dict[str, Any]:
        """Compress trade data focusing on volume and price distribution"""
        prices = [r.get('price', 0) for r in data if r.get('price', 0) > 0]
        sizes = [r.get('size', 0) for r in data if r.get('size', 0) > 0]
        timestamps = [r.get('ms_of_day', 0) for r in data if r.get('ms_of_day', 0) > 0]
        
        if not prices or not sizes:
            return {"statistics": {}, "insights": ["No valid trade data"]}
        
        import numpy as np
        
        # Basic volume and price metrics
        total_volume = sum(sizes)
        total_value = sum(p * s for p, s in zip(prices, sizes))
        vwap = total_value / total_volume if total_volume > 0 else 0
        
        # Advanced trade analytics
        trade_values = [p * s for p, s in zip(prices, sizes)]  # Dollar volume per trade
        
        # Size distribution analysis
        size_percentiles = {
            "25th": np.percentile(sizes, 25),
            "50th": np.percentile(sizes, 50),  # median trade size
            "75th": np.percentile(sizes, 75),
            "95th": np.percentile(sizes, 95)   # large trade threshold
        }
        
        # Price impact analysis
        price_std = np.std(prices) if len(prices) > 1 else 0
        price_spread = (max(prices) - min(prices)) / min(prices) * 100 if prices and min(prices) > 0 else 0
        
        # Volume distribution
        large_trades = [s for s in sizes if s >= size_percentiles["95th"]]
        large_trade_volume = sum(large_trades)
        large_trade_percentage = (large_trade_volume / total_volume * 100) if total_volume > 0 else 0
        
        # Trading intensity (trades per hour if timestamps available)
        trading_intensity = 0
        if len(timestamps) > 1:
            time_span_hours = (max(timestamps) - min(timestamps)) / (1000 * 60 * 60)  # Convert ms to hours
            trading_intensity = len(data) / time_span_hours if time_span_hours > 0 else 0
        
        # Volume-weighted statistics
        volume_weights = [s / total_volume for s in sizes] if total_volume > 0 else [0] * len(sizes)
        volume_weighted_std = np.sqrt(sum(w * (p - vwap)**2 for w, p in zip(volume_weights, prices))) if prices else 0
        
        # Liquidity metrics
        average_trade_value = np.mean(trade_values) if trade_values else 0
        liquidity_score = min(total_volume / 1000, 10)  # Scale 0-10 based on volume
        
        stats = {
            # Basic trade metrics
            "total_trades": len(data),
            "total_volume": total_volume,
            "total_dollar_volume": total_value,
            "vwap": vwap,
            "price_range": {"low": min(prices), "high": max(prices)},
            
            # Size analysis
            "average_trade_size": np.mean(sizes),
            "median_trade_size": size_percentiles["50th"],
            "largest_trade": max(sizes),
            "size_percentiles": size_percentiles,
            
            # Volume distribution
            "large_trade_count": len(large_trades),
            "large_trade_volume": large_trade_volume,
            "large_trade_percentage": large_trade_percentage,
            
            # Price dynamics
            "price_volatility": price_std,
            "price_spread_pct": price_spread,
            "volume_weighted_std": volume_weighted_std,
            
            # Trading activity
            "trading_intensity_per_hour": trading_intensity,
            "average_trade_value": average_trade_value,
            "liquidity_score": liquidity_score,
            
            # Advanced metrics
            "volume_to_trade_ratio": total_volume / len(data) if data else 0,
            "price_efficiency": price_std / vwap * 100 if vwap > 0 else 0,  # Lower is more efficient
        }
        
        insights = []
        
        # Volume insights
        if large_trade_percentage > 50:
            insights.append(f"Institutional activity: {large_trade_percentage:.1f}% from large trades")
        elif large_trade_percentage > 20:
            insights.append(f"Some large trades: {large_trade_percentage:.1f}% from size >95th percentile")
        
        if stats["largest_trade"] > stats["average_trade_size"] * 10:
            insights.append(f"Block trade detected: {stats['largest_trade']:,} vs avg {stats['average_trade_size']:.0f}")
        
        # VWAP insights
        current_price = prices[-1] if prices else 0
        vwap_deviation = ((current_price - vwap) / vwap * 100) if vwap > 0 else 0
        if abs(vwap_deviation) > 2:
            direction = "above" if vwap_deviation > 0 else "below"
            insights.append(f"Price {direction} VWAP by {abs(vwap_deviation):.1f}%")
        
        # Liquidity insights
        if liquidity_score >= 8:
            insights.append("Excellent liquidity - high volume and activity")
        elif liquidity_score >= 5:
            insights.append("Good liquidity - sufficient trading activity")
        elif liquidity_score < 3:
            insights.append("Poor liquidity - limited trading activity")
        
        # Trading pattern insights
        if trading_intensity > 10:
            insights.append(f"High trading intensity: {trading_intensity:.1f} trades/hour")
        elif trading_intensity < 1:
            insights.append(f"Low trading intensity: {trading_intensity:.1f} trades/hour")
        
        insights.append(f"VWAP: ${vwap:.2f} over {total_volume:,} contracts ({len(data)} trades)")
        
        return {"statistics": stats, "insights": insights}
    
    def _compress_iv_data(self, data: List[Dict]) -> Dict[str, Any]:
        """Compress implied volatility data with volatility insights"""
        mid_ivs = [r.get('implied_vol', 0) for r in data if r.get('implied_vol', 0) > 0]
        bid_ivs = [r.get('bid_implied_vol', 0) for r in data if r.get('bid_implied_vol', 0) > 0]
        ask_ivs = [r.get('ask_implied_vol', 0) for r in data if r.get('ask_implied_vol', 0) > 0]
        underlying_prices = [r.get('underlying_price', 0) for r in data if r.get('underlying_price', 0) > 0]
        option_prices = [r.get('midpoint', 0) for r in data if r.get('midpoint', 0) > 0]
        
        if not mid_ivs:
            return {"statistics": {}, "insights": ["No valid IV data"]}
        
        import numpy as np
        
        # Basic IV statistics
        iv_change = mid_ivs[-1] - mid_ivs[0] if len(mid_ivs) > 1 else 0
        iv_change_pct = ((mid_ivs[-1] - mid_ivs[0]) / mid_ivs[0] * 100) if len(mid_ivs) > 1 and mid_ivs[0] != 0 else 0
        
        # Advanced IV analytics
        iv_volatility = np.std(mid_ivs) if len(mid_ivs) > 1 else 0  # Volatility of volatility
        iv_percentiles = {
            "25th": np.percentile(mid_ivs, 25),
            "50th": np.percentile(mid_ivs, 50),  # median IV
            "75th": np.percentile(mid_ivs, 75)
        } if len(mid_ivs) >= 4 else {}
        
        # Bid-Ask IV spread analysis
        iv_spread_stats = {}
        if bid_ivs and ask_ivs and len(bid_ivs) == len(ask_ivs):
            iv_spreads = [ask_ivs[i] - bid_ivs[i] for i in range(len(bid_ivs))]
            iv_spread_stats = {
                "average_spread": np.mean(iv_spreads),
                "min_spread": min(iv_spreads),
                "max_spread": max(iv_spreads),
                "spread_volatility": np.std(iv_spreads) if len(iv_spreads) > 1 else 0,
                "current_spread": iv_spreads[-1] if iv_spreads else 0
            }
            
            # Relative spread (as percentage of mid IV)
            rel_spreads = [s / mid_ivs[i] * 100 for i, s in enumerate(iv_spreads) if mid_ivs[i] > 0]
            iv_spread_stats["relative_spread_pct"] = np.mean(rel_spreads) if rel_spreads else 0
        
        # IV term structure analysis (if we have time series)
        iv_momentum = 0
        iv_trend_strength = 0
        if len(mid_ivs) >= 3:
            # Calculate momentum as rate of IV change
            iv_returns = [(mid_ivs[i] - mid_ivs[i-1]) / mid_ivs[i-1] for i in range(1, len(mid_ivs))]
            iv_momentum = np.mean(iv_returns) * 100 if iv_returns else 0  # As percentage
            
            # Trend strength: compare first third vs last third
            first_third = np.mean(mid_ivs[:len(mid_ivs)//3])
            last_third = np.mean(mid_ivs[-len(mid_ivs)//3:])
            iv_trend_strength = ((last_third - first_third) / first_third * 100) if first_third > 0 else 0
        
        # IV rank and percentile calculations
        iv_current = mid_ivs[-1] if mid_ivs else 0
        iv_rank = 0
        if len(mid_ivs) > 1:
            sorted_ivs = sorted(mid_ivs)
            rank_position = sorted_ivs.index(iv_current) if iv_current in sorted_ivs else 0
            iv_rank = (rank_position / (len(sorted_ivs) - 1) * 100) if len(sorted_ivs) > 1 else 0
        
        # Option price to IV relationship
        iv_efficiency = 0
        if option_prices and len(option_prices) == len(mid_ivs):
            # Correlation between IV and option price changes
            if len(option_prices) > 2:
                iv_changes = [mid_ivs[i] - mid_ivs[i-1] for i in range(1, len(mid_ivs))]
                price_changes = [option_prices[i] - option_prices[i-1] for i in range(1, len(option_prices))]
                if iv_changes and price_changes:
                    iv_efficiency = np.corrcoef(iv_changes, price_changes)[0,1] if not np.isnan(np.corrcoef(iv_changes, price_changes)[0,1]) else 0
        
        stats = {
            # Basic IV metrics
            "iv_range": {"low": min(mid_ivs), "high": max(mid_ivs)},
            "average_iv": np.mean(mid_ivs),
            "current_iv": iv_current,
            "opening_iv": mid_ivs[0] if mid_ivs else 0,
            "iv_change": iv_change,
            "iv_change_pct": iv_change_pct,
            
            # IV distribution and volatility
            "iv_volatility": iv_volatility,
            "iv_percentiles": iv_percentiles,
            "iv_rank": iv_rank,  # Where current IV sits in historical range
            
            # Spread analysis
            "bid_ask_spread": iv_spread_stats,
            
            # Trend and momentum
            "iv_momentum_pct": iv_momentum,
            "iv_trend_strength_pct": iv_trend_strength,
            
            # Advanced metrics
            "iv_to_price_correlation": iv_efficiency,
            "records_count": len(data),
            
            # Classification metrics
            "iv_level_classification": self._classify_iv_level(np.mean(mid_ivs)),
            "iv_percentile_current": iv_rank
        }
        
        insights = []
        
        # IV level insights
        avg_iv = stats["average_iv"]
        if avg_iv > 0.6:
            insights.append("Extremely high IV - major event/earnings expected")
        elif avg_iv > 0.4:
            insights.append("Very high IV - significant uncertainty priced in")
        elif avg_iv > 0.3:
            insights.append("High IV - elevated uncertainty")
        elif avg_iv > 0.2:
            insights.append("Moderate IV - normal market conditions")
        elif avg_iv < 0.15:
            insights.append("Low IV - stable market expectations")
        
        # IV change insights
        if abs(iv_change_pct) > 20:
            direction = "spiked" if iv_change_pct > 0 else "crushed"
            insights.append(f"IV {direction} {abs(iv_change_pct):.1f}% - major volatility event")
        elif abs(iv_change_pct) > 10:
            direction = "increased" if iv_change_pct > 0 else "decreased"
            insights.append(f"IV {direction} significantly: {iv_change_pct:+.1f}%")
        
        # IV rank insights
        if iv_rank > 80:
            insights.append(f"IV at {iv_rank:.0f}th percentile - near historical highs")
        elif iv_rank < 20:
            insights.append(f"IV at {iv_rank:.0f}th percentile - near historical lows")
        
        # Spread insights
        if iv_spread_stats.get("relative_spread_pct", 0) > 10:
            insights.append("Wide IV spreads - poor liquidity or market stress")
        elif iv_spread_stats.get("relative_spread_pct", 0) < 3:
            insights.append("Tight IV spreads - good options liquidity")
        
        # Momentum insights
        if abs(iv_momentum) > 5:
            direction = "accelerating upward" if iv_momentum > 0 else "declining rapidly"
            insights.append(f"IV momentum {direction}: {iv_momentum:+.1f}%")
        
        return {"statistics": stats, "insights": insights}
    
    def _classify_iv_level(self, iv_value: float) -> str:
        """Classify IV level for easy AI interpretation"""
        if iv_value > 0.6:
            return "EXTREMELY_HIGH"
        elif iv_value > 0.4:
            return "VERY_HIGH"
        elif iv_value > 0.3:
            return "HIGH"
        elif iv_value > 0.2:
            return "MODERATE"
        elif iv_value > 0.15:
            return "NORMAL"
        elif iv_value > 0.1:
            return "LOW"
        else:
            return "VERY_LOW"
    
    def _compress_greeks_data(self, data: List[Dict]) -> Dict[str, Any]:
        """Compress Greeks data with risk insights"""
        if not data:
            return {"statistics": {}, "insights": ["No Greeks data"]}
        
        import numpy as np
        
        # Extract all Greeks values
        deltas = [r.get('delta', 0) for r in data if r.get('delta') is not None]
        gammas = [r.get('gamma', 0) for r in data if r.get('gamma') is not None]
        thetas = [r.get('theta', 0) for r in data if r.get('theta') is not None]
        vegas = [r.get('vega', 0) for r in data if r.get('vega') is not None]
        rhos = [r.get('rho', 0) for r in data if r.get('rho') is not None]
        implied_vols = [r.get('implied_vol', 0) for r in data if r.get('implied_vol', 0) > 0]
        
        latest = data[-1]
        first = data[0] if len(data) > 1 else latest
        
        # Current Greeks values
        current_delta = latest.get('delta', 0)
        current_gamma = latest.get('gamma', 0)
        current_theta = latest.get('theta', 0)
        current_vega = latest.get('vega', 0)
        current_rho = latest.get('rho', 0)
        current_iv = latest.get('implied_vol', 0)
        
        # Greeks changes over time
        delta_change = current_delta - first.get('delta', 0) if len(data) > 1 else 0
        gamma_change = current_gamma - first.get('gamma', 0) if len(data) > 1 else 0
        theta_change = current_theta - first.get('theta', 0) if len(data) > 1 else 0
        vega_change = current_vega - first.get('vega', 0) if len(data) > 1 else 0
        
        # Greeks volatility (how much they moved)
        greeks_volatility = {}
        if len(deltas) > 1:
            greeks_volatility = {
                "delta_volatility": np.std(deltas),
                "gamma_volatility": np.std(gammas) if gammas else 0,
                "theta_volatility": np.std(thetas) if thetas else 0,
                "vega_volatility": np.std(vegas) if vegas else 0
            }
        
        # Risk metrics calculations
        delta_exposure_risk = abs(current_delta)  # Higher delta = more directional risk
        gamma_risk = abs(current_gamma) * 100  # Scaled for readability
        theta_decay_daily = abs(current_theta)  # Daily time decay
        vega_risk = abs(current_vega) * 10  # IV sensitivity (scaled)
        
        # Option moneyness classification
        moneyness = self._classify_moneyness(current_delta, latest.get('right', 'C'))
        
        # Greeks efficiency ratios
        delta_gamma_ratio = abs(current_delta / current_gamma) if current_gamma != 0 else 0
        theta_vega_ratio = abs(current_theta / current_vega) if current_vega != 0 else 0
        
        # Greeks percentiles if we have enough data
        greeks_percentiles = {}
        if len(deltas) >= 5:
            greeks_percentiles = {
                "delta": {
                    "25th": np.percentile(deltas, 25),
                    "50th": np.percentile(deltas, 50),
                    "75th": np.percentile(deltas, 75)
                }
            }
            if gammas:
                greeks_percentiles["gamma"] = {
                    "25th": np.percentile(gammas, 25),
                    "50th": np.percentile(gammas, 50),
                    "75th": np.percentile(gammas, 75)
                }
        
        stats = {
            # Current Greeks values
            "current_greeks": {
                "delta": current_delta,
                "gamma": current_gamma,
                "theta": current_theta,
                "vega": current_vega,
                "rho": current_rho,
                "implied_vol": current_iv
            },
            
            # Greeks changes
            "greeks_changes": {
                "delta_change": delta_change,
                "gamma_change": gamma_change,
                "theta_change": theta_change,
                "vega_change": vega_change
            },
            
            # Greeks ranges
            "greeks_ranges": {
                "delta_range": {"min": min(deltas), "max": max(deltas)} if deltas else {},
                "gamma_range": {"min": min(gammas), "max": max(gammas)} if gammas else {},
                "theta_range": {"min": min(thetas), "max": max(thetas)} if thetas else {},
                "vega_range": {"min": min(vegas), "max": max(vegas)} if vegas else {}
            },
            
            # Greeks volatility
            "greeks_volatility": greeks_volatility,
            
            # Risk metrics
            "risk_metrics": {
                "delta_exposure_risk": delta_exposure_risk,
                "gamma_risk": gamma_risk,
                "theta_decay_daily": theta_decay_daily,
                "vega_risk": vega_risk,
                "total_risk_score": (delta_exposure_risk + gamma_risk/100 + theta_decay_daily*10 + vega_risk/10) / 4
            },
            
            # Classification and ratios
            "moneyness": moneyness,
            "delta_gamma_ratio": delta_gamma_ratio,
            "theta_vega_ratio": theta_vega_ratio,
            "greeks_percentiles": greeks_percentiles,
            
            # Time sensitivity
            "days_to_expiry_impact": abs(current_theta) * 7,  # Weekly theta decay
            "iv_sensitivity_1pct": abs(current_vega),  # P&L impact of 1% IV change
            
            # Advanced metrics
            "records_count": len(data),
            "greeks_stability": 1 - (np.std(deltas) if deltas and len(deltas) > 1 else 0)  # 1 = very stable
        }
        
        insights = []
        
        # Delta insights (directional exposure)
        if abs(current_delta) > 0.8:
            insights.append(f"High directional exposure: Δ={current_delta:.3f} - deep {'ITM' if current_delta > 0.8 else 'OTM'}")
        elif 0.4 <= abs(current_delta) <= 0.6:
            insights.append(f"Near ATM: Δ={current_delta:.3f} - balanced risk/reward")
        elif abs(current_delta) < 0.2:
            insights.append(f"Low delta: Δ={current_delta:.3f} - high leverage, low probability")
        
        # Gamma insights (acceleration risk)
        if abs(current_gamma) > 0.05:
            insights.append(f"High gamma: Γ={current_gamma:.4f} - significant acceleration risk")
        elif abs(current_gamma) > 0.02:
            insights.append(f"Moderate gamma: Γ={current_gamma:.4f} - noticeable delta sensitivity")
        
        # Theta insights (time decay)
        if abs(current_theta) > 0.05:
            insights.append(f"High time decay: Θ=${abs(current_theta):.3f}/day - significant time risk")
        elif abs(current_theta) > 0.02:
            insights.append(f"Moderate time decay: Θ=${abs(current_theta):.3f}/day")
        
        # Vega insights (volatility sensitivity)
        if abs(current_vega) > 0.1:
            insights.append(f"High vega: ν={current_vega:.3f} - very sensitive to IV changes")
        elif abs(current_vega) > 0.05:
            insights.append(f"Moderate vega: ν={current_vega:.3f} - sensitive to volatility")
        
        # Combined risk assessment
        total_risk = stats["risk_metrics"]["total_risk_score"]
        if total_risk > 3:
            insights.append("HIGH RISK: Multiple significant Greeks exposures")
        elif total_risk > 2:
            insights.append("MODERATE RISK: Some notable exposures")
        elif total_risk < 1:
            insights.append("LOW RISK: Limited Greeks exposures")
        
        # Moneyness insight
        insights.append(f"Position: {moneyness} - {self._get_moneyness_description(moneyness)}")
        
        return {"statistics": stats, "insights": insights}
    
    def _classify_moneyness(self, delta: float, option_type: str) -> str:
        """Classify option moneyness based on delta"""
        abs_delta = abs(delta)
        
        if abs_delta > 0.8:
            return "DEEP_ITM"
        elif abs_delta > 0.6:
            return "ITM"
        elif 0.4 <= abs_delta <= 0.6:
            return "ATM"
        elif abs_delta > 0.2:
            return "OTM"
        else:
            return "DEEP_OTM"
    
    def _get_moneyness_description(self, moneyness: str) -> str:
        """Get description for moneyness classification"""
        descriptions = {
            "DEEP_ITM": "High intrinsic value, low time value",
            "ITM": "Good intrinsic value, some time value",
            "ATM": "Maximum time value, balanced risk/reward",
            "OTM": "Pure time value, higher risk/reward",
            "DEEP_OTM": "Very low probability, maximum leverage"
        }
        return descriptions.get(moneyness, "Unknown classification")
    
    def _compress_quote_data(self, data: List[Dict]) -> Dict[str, Any]:
        """Compress quote data focusing on spread and liquidity"""
        spreads = []
        for r in data:
            bid, ask = r.get('bid', 0), r.get('ask', 0)
            if bid > 0 and ask > 0:
                spreads.append(ask - bid)
        
        if not spreads:
            return {"statistics": {}, "insights": ["No valid quote data"]}
        
        stats = {
            "average_spread": sum(spreads) / len(spreads),
            "min_spread": min(spreads),
            "max_spread": max(spreads),
            "total_quotes": len(data)
        }
        
        insights = []
        avg_spread = stats["average_spread"]
        if avg_spread < 0.05:
            insights.append("Tight spreads - good liquidity")
        elif avg_spread > 0.20:
            insights.append("Wide spreads - poor liquidity")
        
        return {"statistics": stats, "insights": insights}
    
    def _compress_oi_data(self, data: List[Dict]) -> Dict[str, Any]:
        """Compress open interest data with position flow insights"""
        if not data:
            return {"statistics": {}, "insights": ["No OI data"]}
        
        oi_values = [r.get('open_interest', 0) for r in data]
        
        stats = {
            "current_oi": oi_values[-1] if oi_values else 0,
            "oi_change": oi_values[-1] - oi_values[0] if len(oi_values) > 1 else 0,
            "max_oi": max(oi_values) if oi_values else 0
        }
        
        insights = []
        if stats["oi_change"] > 1000:
            insights.append(f"Large position building: +{stats['oi_change']:,} contracts")
        elif stats["oi_change"] < -1000:
            insights.append(f"Position unwinding: {stats['oi_change']:,} contracts")
        
        return {"statistics": stats, "insights": insights}

    def _make_request(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Make HTTP request to Theta Data API"""
        url = f"{self.base_url}{endpoint}"
        
        # Remove None values from params
        cleaned_params = {k: v for k, v in params.items() if v is not None}
        
        try:
            response = requests.get(url, params=cleaned_params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # Check for API errors
            if isinstance(data, dict) and data.get('header', {}).get('error_type'):
                raise ThetaDataError(f"API Error: {data['header']['error_type']}")
            
            return data
            
        except requests.exceptions.ConnectionError:
            raise ThetaDataError("Cannot connect to Theta Data Terminal. Please ensure it's running on port 25510.")
        except requests.exceptions.Timeout:
            raise ThetaDataError("Request timed out. Please try again.")
        except requests.exceptions.HTTPError as e:
            raise ThetaDataError(f"HTTP Error: {e}")
        except ValueError as e:
            raise ThetaDataError(f"Invalid JSON response: {e}")

    def _format_strike_price(self, strike_cents: int) -> float:
        """Convert strike price from 1/10th cent to dollars"""
        return strike_cents / 1000.0

    def _format_date(self, date_int: int) -> str:
        """Convert YYYYMMDD integer to readable date string"""
        date_str = str(date_int)
        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"

    def _parse_data_response(self, raw_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse data from Theta Data response"""
        if not raw_data.get('response'):
            return []
        
        header_format = raw_data.get('header', {}).get('format', [])
        data_points = []
        
        for row in raw_data['response']:
            if len(row) >= len(header_format):
                data_point = {}
                for i, field in enumerate(header_format):
                    if i < len(row):
                        data_point[field] = row[i]
                
                # Convert timestamp if present
                if 'ms_of_day' in data_point:
                    data_point['timestamp_ms'] = data_point['ms_of_day']
                    hours = data_point['ms_of_day'] // (1000 * 60 * 60)
                    minutes = (data_point['ms_of_day'] % (1000 * 60 * 60)) // (1000 * 60)
                    seconds = (data_point['ms_of_day'] % (1000 * 60)) // 1000
                    ms = data_point['ms_of_day'] % 1000
                    data_point['time_formatted'] = f"{hours:02d}:{minutes:02d}:{seconds:02d}.{ms:03d}"
                
                data_points.append(data_point)
        
        return data_points

    def get_historical_options_ohlc(
        self,
        root: str,
        exp: int,
        strike: int,
        right: str,
        start_date: int,
        end_date: int,
        ivl: int = 60000,
        rth: bool = True,
        ai_friendly: Optional[bool] = None,
        max_samples: int = 10
    ) -> Dict[str, Any]:
        """
        Get historical OHLC (Open, High, Low, Close) data for options contracts.
        
        Args:
            root: Underlying symbol (e.g., 'AAPL')
            exp: Expiration date as YYYYMMDD (e.g., 20240315)
            strike: Strike price in 1/10th cent (e.g., 170000 for $170.00)
            right: 'C' for call, 'P' for put
            start_date: Start date as YYYYMMDD
            end_date: End date as YYYYMMDD
            ivl: Interval in milliseconds (60000 = 1 minute, 0 = tick level)
            rth: Regular trading hours only (True/False)
            ai_friendly: Override tool default for AI compression (None = use tool default)
            max_samples: Maximum sample records when compressed
        
        Returns:
            Dictionary containing OHLC data and metadata
        """
        params = {
            'root': root,
            'exp': exp,
            'strike': strike,
            'right': right,
            'start_date': start_date,
            'end_date': end_date,
            'ivl': ivl,
            'rth': rth
        }
        
        try:
            raw_data = self._make_request('/v2/hist/option/ohlc', params)
            parsed_data = self._parse_data_response(raw_data)
            
            contract_info = OptionsContractInfo(
                root=root,
                exp=exp,
                strike=strike,
                right=right,
                strike_price_dollars=self._format_strike_price(strike),
                expiration_date_formatted=self._format_date(exp)
            )
            
            additional_fields = {
                "interval_ms": ivl,
                "regular_trading_hours": rth,
                "from_date": self._format_date(start_date),
                "to_date": self._format_date(end_date)
            }
            
            return self._prepare_data_response(
                parsed_data=parsed_data,
                contract_info=contract_info,
                data_type="ohlc",
                params=params,
                raw_data=raw_data,
                ai_friendly=ai_friendly,
                max_samples=max_samples,
                additional_fields=additional_fields
            )
            
        except ThetaDataError as e:
            return {
                "success": False,
                "error": str(e),
                "contract": {
                    "root": root,
                    "exp": exp,
                    "strike": strike,
                    "right": right
                }
            }

    def get_historical_options_quotes(
        self,
        root: str,
        exp: int,
        strike: int,
        right: str,
        start_date: int,
        end_date: int,
        ivl: int = 0,
        rth: bool = True
    ) -> Dict[str, Any]:
        """
        Get historical bid/ask quote data for options contracts.
        
        Args:
            root: Underlying symbol
            exp: Expiration date as YYYYMMDD
            strike: Strike price in 1/10th cent
            right: 'C' for call, 'P' for put
            start_date: Start date as YYYYMMDD
            end_date: End date as YYYYMMDD
            ivl: Interval in milliseconds (0 = tick level)
            rth: Regular trading hours only
        
        Returns:
            Dictionary containing quote data and metadata
        """
        params = {
            'root': root,
            'exp': exp,
            'strike': strike,
            'right': right,
            'start_date': start_date,
            'end_date': end_date,
            'ivl': ivl,
            'rth': rth
        }
        
        try:
            raw_data = self._make_request('/v2/hist/option/quote', params)
            parsed_data = self._parse_data_response(raw_data)
            
            contract_info = OptionsContractInfo(
                root=root,
                exp=exp,
                strike=strike,
                right=right,
                strike_price_dollars=self._format_strike_price(strike),
                expiration_date_formatted=self._format_date(exp)
            )
            
            return {
                "success": True,
                "contract": contract_info.dict(),
                "data_type": "quotes",
                "interval_ms": ivl,
                "regular_trading_hours": rth,
                "from_date": self._format_date(start_date),
                "to_date": self._format_date(end_date),
                "count": len(parsed_data),
                "data": parsed_data,
                "metadata": {
                    "header": raw_data.get('header', {}),
                    "request_params": params
                }
            }
            
        except ThetaDataError as e:
            return {
                "success": False,
                "error": str(e),
                "contract": {
                    "root": root,
                    "exp": exp,
                    "strike": strike,
                    "right": right
                }
            }

    def get_historical_options_trades(
        self,
        root: str,
        exp: int,
        strike: int,
        right: str,
        start_date: int,
        end_date: int,
        ivl: int = 0,
        rth: bool = True,
        ai_friendly: Optional[bool] = None,
        max_samples: int = 10
    ) -> Dict[str, Any]:
        """
        Get historical trade data for options contracts.
        
        Args:
            root: Underlying symbol
            exp: Expiration date as YYYYMMDD
            strike: Strike price in 1/10th cent
            right: 'C' for call, 'P' for put
            start_date: Start date as YYYYMMDD
            end_date: End date as YYYYMMDD
            ivl: Interval in milliseconds (0 = tick level)
            rth: Regular trading hours only
            ai_friendly: Override tool default for AI compression (None = use tool default)
            max_samples: Maximum sample records when compressed
        
        Returns:
            Dictionary containing trade data and metadata
        """
        params = {
            'root': root,
            'exp': exp,
            'strike': strike,
            'right': right,
            'start_date': start_date,
            'end_date': end_date,
            'ivl': ivl,
            'rth': rth
        }
        
        try:
            raw_data = self._make_request('/v2/hist/option/trade', params)
            parsed_data = self._parse_data_response(raw_data)
            
            contract_info = OptionsContractInfo(
                root=root,
                exp=exp,
                strike=strike,
                right=right,
                strike_price_dollars=self._format_strike_price(strike),
                expiration_date_formatted=self._format_date(exp)
            )
            
            additional_fields = {
                "interval_ms": ivl,
                "regular_trading_hours": rth,
                "from_date": self._format_date(start_date),
                "to_date": self._format_date(end_date)
            }
            
            return self._prepare_data_response(
                parsed_data=parsed_data,
                contract_info=contract_info,
                data_type="trades",
                params=params,
                raw_data=raw_data,
                ai_friendly=ai_friendly,
                max_samples=max_samples,
                additional_fields=additional_fields
            )
            
        except ThetaDataError as e:
            return {
                "success": False,
                "error": str(e),
                "contract": {
                    "root": root,
                    "exp": exp,
                    "strike": strike,
                    "right": right
                }
            }

    def get_historical_options_greeks(
        self,
        root: str,
        exp: int,
        strike: int,
        right: str,
        start_date: int,
        end_date: int,
        ivl: int = 60000,
        rth: bool = True,
        ai_friendly: Optional[bool] = None,
        max_samples: int = 10
    ) -> Dict[str, Any]:
        """
        Get historical options Greeks (delta, gamma, theta, vega, etc.) data.
        
        Args:
            root: Underlying symbol
            exp: Expiration date as YYYYMMDD
            strike: Strike price in 1/10th cent
            right: 'C' for call, 'P' for put
            start_date: Start date as YYYYMMDD
            end_date: End date as YYYYMMDD
            ivl: Interval in milliseconds (recommended: 60000+)
            rth: Regular trading hours only
            ai_friendly: Override tool default for AI compression (None = use tool default)
            max_samples: Maximum sample records when compressed
        
        Returns:
            Dictionary containing Greeks data and metadata
        """
        params = {
            'root': root,
            'exp': exp,
            'strike': strike,
            'right': right,
            'start_date': start_date,
            'end_date': end_date,
            'ivl': ivl,
            'rth': rth
        }
        
        try:
            raw_data = self._make_request('/v2/hist/option/greeks', params)
            parsed_data = self._parse_data_response(raw_data)
            
            contract_info = OptionsContractInfo(
                root=root,
                exp=exp,
                strike=strike,
                right=right,
                strike_price_dollars=self._format_strike_price(strike),
                expiration_date_formatted=self._format_date(exp)
            )
            
            additional_fields = {
                "interval_ms": ivl,
                "regular_trading_hours": rth,
                "from_date": self._format_date(start_date),
                "to_date": self._format_date(end_date),
                "greeks_info": {
                    "calculated_using": "option and underlying midpoint price",
                    "available_greeks": ["delta", "theta", "vega", "rho", "epsilon", "lambda", "implied_vol"]
                }
            }
            
            return self._prepare_data_response(
                parsed_data=parsed_data,
                contract_info=contract_info,
                data_type="greeks",
                params=params,
                raw_data=raw_data,
                ai_friendly=ai_friendly,
                max_samples=max_samples,
                additional_fields=additional_fields
            )
            
        except ThetaDataError as e:
            return {
                "success": False,
                "error": str(e),
                "contract": {
                    "root": root,
                    "exp": exp,
                    "strike": strike,
                    "right": right
                }
            }

    def get_historical_options_implied_volatility(
        self,
        root: str,
        exp: int,
        strike: int,
        right: str,
        start_date: int,
        end_date: int,
        ivl: int = 0,
        rth: bool = True,
        ai_friendly: Optional[bool] = None,
        max_samples: int = 10
    ) -> Dict[str, Any]:
        """
        Get historical implied volatility data for options contracts.
        
        Returns implied volatilities calculated using the national best bid, mid, and ask price
        of the option respectively. The underlying price represents the last underlying price
        at the ms_of_day field.
        
        Args:
            root: Underlying symbol
            exp: Expiration date as YYYYMMDD
            strike: Strike price in 1/10th cent
            right: 'C' for call, 'P' for put
            start_date: Start date as YYYYMMDD
            end_date: End date as YYYYMMDD
            ivl: Interval in milliseconds (0 = tick level, 60000 = 1 minute)
            rth: Regular trading hours only
        
        Returns:
            Dictionary containing implied volatility data and metadata
        """
        params = {
            'root': root,
            'exp': exp,
            'strike': strike,
            'right': right,
            'start_date': start_date,
            'end_date': end_date,
            'ivl': ivl,
            'rth': rth
        }
        
        try:
            raw_data = self._make_request('/v2/hist/option/implied_volatility', params)
            parsed_data = self._parse_data_response(raw_data)
            
            contract_info = OptionsContractInfo(
                root=root,
                exp=exp,
                strike=strike,
                right=right,
                strike_price_dollars=self._format_strike_price(strike),
                expiration_date_formatted=self._format_date(exp)
            )
            
            return {
                "success": True,
                "contract": contract_info.dict(),
                "data_type": "implied_volatility",
                "interval_ms": ivl,
                "regular_trading_hours": rth,
                "from_date": self._format_date(start_date),
                "to_date": self._format_date(end_date),
                "count": len(parsed_data),
                "data": parsed_data,
                "metadata": {
                    "header": raw_data.get('header', {}),
                    "request_params": params,
                    "iv_info": {
                        "calculated_using": "national best bid, mid, and ask price",
                        "fields": [
                            "ms_of_day", "bid", "bid_implied_vol", "midpoint", 
                            "implied_vol", "ask", "ask_implied_vol", "iv_error", 
                            "ms_of_day2", "underlying_price", "date"
                        ],
                        "description": {
                            "bid_implied_vol": "IV calculated using bid price",
                            "implied_vol": "IV calculated using mid price", 
                            "ask_implied_vol": "IV calculated using ask price",
                            "iv_error": "Option value using IV divided by actual quote value"
                        }
                    }
                }
            }
            
        except ThetaDataError as e:
            return {
                "success": False,
                "error": str(e),
                "contract": {
                    "root": root,
                    "exp": exp,
                    "strike": strike,
                    "right": right
                }
            }

    def get_historical_options_open_interest(
        self,
        root: str,
        exp: int,
        strike: int,
        right: str,
        start_date: int,
        end_date: int
    ) -> Dict[str, Any]:
        """
        Get historical open interest data for options contracts.
        
        Args:
            root: Underlying symbol
            exp: Expiration date as YYYYMMDD
            strike: Strike price in 1/10th cent
            right: 'C' for call, 'P' for put
            start_date: Start date as YYYYMMDD
            end_date: End date as YYYYMMDD
        
        Returns:
            Dictionary containing open interest data and metadata
        """
        params = {
            'root': root,
            'exp': exp,
            'strike': strike,
            'right': right,
            'start_date': start_date,
            'end_date': end_date
        }
        
        try:
            raw_data = self._make_request('/v2/hist/option/open_interest', params)
            parsed_data = self._parse_data_response(raw_data)
            
            contract_info = OptionsContractInfo(
                root=root,
                exp=exp,
                strike=strike,
                right=right,
                strike_price_dollars=self._format_strike_price(strike),
                expiration_date_formatted=self._format_date(exp)
            )
            
            return {
                "success": True,
                "contract": contract_info.dict(),
                "data_type": "open_interest",
                "from_date": self._format_date(start_date),
                "to_date": self._format_date(end_date),
                "count": len(parsed_data),
                "data": parsed_data,
                "metadata": {
                    "header": raw_data.get('header', {}),
                    "request_params": params,
                    "note": "Open interest is reported at end of previous trading day"
                }
            }
            
        except ThetaDataError as e:
            return {
                "success": False,
                "error": str(e),
                "contract": {
                    "root": root,
                    "exp": exp,
                    "strike": strike,
                    "right": right
                }
            }

    def get_options_eod_report(
        self,
        root: str,
        exp: int,
        strike: int,
        right: str,
        start_date: int,
        end_date: int
    ) -> Dict[str, Any]:
        """
        Get end-of-day (EOD) report for options contracts.
        
        Args:
            root: Underlying symbol
            exp: Expiration date as YYYYMMDD
            strike: Strike price in 1/10th cent
            right: 'C' for call, 'P' for put
            start_date: Start date as YYYYMMDD
            end_date: End date as YYYYMMDD
        
        Returns:
            Dictionary containing EOD data and metadata
        """
        params = {
            'root': root,
            'exp': exp,
            'strike': strike,
            'right': right,
            'start_date': start_date,
            'end_date': end_date
        }
        
        try:
            raw_data = self._make_request('/v2/hist/option/eod', params)
            parsed_data = self._parse_data_response(raw_data)
            
            contract_info = OptionsContractInfo(
                root=root,
                exp=exp,
                strike=strike,
                right=right,
                strike_price_dollars=self._format_strike_price(strike),
                expiration_date_formatted=self._format_date(exp)
            )
            
            return {
                "success": True,
                "contract": contract_info.dict(),
                "data_type": "eod_report",
                "from_date": self._format_date(start_date),
                "to_date": self._format_date(end_date),
                "count": len(parsed_data),
                "data": parsed_data,
                "metadata": {
                    "header": raw_data.get('header', {}),
                    "request_params": params,
                    "note": "Theta Data generated national EOD report"
                }
            }
            
        except ThetaDataError as e:
            return {
                "success": False,
                "error": str(e),
                "contract": {
                    "root": root,
                    "exp": exp,
                    "strike": strike,
                    "right": right
                }
            }

    def list_options_expirations(self, root: str) -> Dict[str, Any]:
        """
        List all available expiration dates for an underlying symbol.
        
        Args:
            root: Underlying symbol (e.g., 'AAPL')
        
        Returns:
            Dictionary containing available expiration dates
        """
        params = {'root': root}
        
        try:
            raw_data = self._make_request('/v2/list/exp/option', params)
            
            expirations = []
            if raw_data.get('response'):
                for exp_data in raw_data['response']:
                    if isinstance(exp_data, list) and len(exp_data) > 0:
                        exp_int = exp_data[0]
                        expirations.append({
                            "expiration_date": exp_int,
                            "formatted_date": self._format_date(exp_int),
                            "days_to_expiration": self._calculate_days_to_expiration(exp_int)
                        })
            
            return {
                "success": True,
                "root": root,
                "count": len(expirations),
                "expirations": expirations,
                "metadata": {
                    "header": raw_data.get('header', {}),
                    "note": "Available expiration dates for options contracts"
                }
            }
            
        except ThetaDataError as e:
            return {
                "success": False,
                "error": str(e),
                "root": root
            }

    def list_options_strikes(self, root: str, exp: int) -> Dict[str, Any]:
        """
        List all available strike prices for a specific expiration.
        
        Args:
            root: Underlying symbol
            exp: Expiration date as YYYYMMDD
        
        Returns:
            Dictionary containing available strike prices
        """
        params = {'root': root, 'exp': exp}
        
        try:
            raw_data = self._make_request('/v2/list/strikes/option', params)
            
            strikes = []
            if raw_data.get('response'):
                for strike_data in raw_data['response']:
                    if isinstance(strike_data, list) and len(strike_data) > 0:
                        strike_cents = strike_data[0]
                        strikes.append({
                            "strike_price_cents": strike_cents,
                            "strike_price_dollars": self._format_strike_price(strike_cents)
                        })
            
            return {
                "success": True,
                "root": root,
                "expiration": exp,
                "expiration_formatted": self._format_date(exp),
                "count": len(strikes),
                "strikes": strikes,
                "metadata": {
                    "header": raw_data.get('header', {}),
                    "note": "Available strike prices for the specified expiration"
                }
            }
            
        except ThetaDataError as e:
            return {
                "success": False,
                "error": str(e),
                "root": root,
                "expiration": exp
            }

    def list_available_dates(
        self,
        root: str,
        request_type: str = "quote",
        exp: Optional[int] = None,
        strike: Optional[int] = None,
        right: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        List all available data dates for options contracts.
        
        Args:
            root: Underlying symbol
            request_type: Type of data ('quote', 'trade', 'ohlc')
            exp: Optional expiration date (for specific contract)
            strike: Optional strike price (for specific contract)
            right: Optional option type ('C' or 'P')
        
        Returns:
            Dictionary containing available dates
        """
        params = {
            'root': root,
            'exp': exp,
            'strike': strike,
            'right': right
        }
        
        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}
        
        try:
            raw_data = self._make_request(f'/v2/list/dates/option/{request_type}', params)
            
            dates = []
            if raw_data.get('response'):
                for date_data in raw_data['response']:
                    if isinstance(date_data, list) and len(date_data) > 0:
                        date_int = date_data[0]
                        dates.append({
                            "date": date_int,
                            "formatted_date": self._format_date(date_int)
                        })
            
            return {
                "success": True,
                "root": root,
                "request_type": request_type,
                "contract_filter": {k: v for k, v in params.items() if k != 'root'},
                "count": len(dates),
                "available_dates": dates,
                "metadata": {
                    "header": raw_data.get('header', {}),
                    "note": "Dates with available data for the specified criteria"
                }
            }
            
        except ThetaDataError as e:
            return {
                "success": False,
                "error": str(e),
                "root": root,
                "request_type": request_type
            }

    def get_bulk_historical_options_data(
        self,
        root: str,
        exp: int,
        data_type: str,
        start_date: int,
        end_date: int,
        ivl: int = 60000
    ) -> Dict[str, Any]:
        """
        Get bulk historical data for all options contracts in an expiration.
        
        Args:
            root: Underlying symbol
            exp: Expiration date as YYYYMMDD
            data_type: Type of data ('quote', 'ohlc', 'trade', 'implied_volatility', 'open_interest')
            start_date: Start date as YYYYMMDD
            end_date: End date as YYYYMMDD
            ivl: Interval in milliseconds (where applicable)
        
        Returns:
            Dictionary containing bulk data for all contracts
        """
        endpoint_map = {
            'quote': '/v2/bulk_hist/option/quote',
            'ohlc': '/v2/bulk_hist/option/ohlc',
            'trade': '/v2/bulk_hist/option/trade',
            'implied_volatility': '/v2/bulk_hist/option/implied_volatility',
            'open_interest': '/v2/bulk_hist/option/open_interest',
            'eod': '/v2/bulk_hist/option/eod'
        }
        
        if data_type not in endpoint_map:
            return {
                "success": False,
                "error": f"Invalid data_type. Must be one of: {list(endpoint_map.keys())}",
                "root": root,
                "expiration": exp
            }
        
        params = {
            'root': root,
            'exp': exp,
            'start_date': start_date,
            'end_date': end_date
        }
        
        # Add interval for applicable data types
        if data_type in ['quote', 'ohlc', 'trade', 'implied_volatility']:
            params['ivl'] = ivl
        
        try:
            raw_data = self._make_request(endpoint_map[data_type], params)
            parsed_data = self._parse_data_response(raw_data)
            
            return {
                "success": True,
                "root": root,
                "expiration": exp,
                "expiration_formatted": self._format_date(exp),
                "data_type": f"bulk_{data_type}",
                "interval_ms": ivl if data_type in ['quote', 'ohlc', 'trade', 'implied_volatility'] else None,
                "from_date": self._format_date(start_date),
                "to_date": self._format_date(end_date),
                "count": len(parsed_data),
                "data": parsed_data,
                "metadata": {
                    "header": raw_data.get('header', {}),
                    "request_params": params,
                    "note": f"Bulk {data_type} data for all contracts in expiration"
                }
            }
            
        except ThetaDataError as e:
            return {
                "success": False,
                "error": str(e),
                "root": root,
                "expiration": exp,
                "data_type": data_type
            }

    def analyze_options_historical_data(
        self,
        historical_data: Dict[str, Any],
        analysis_type: str = "summary"
    ) -> Dict[str, Any]:
        """
        Analyze historical options data and provide insights.
        
        Args:
            historical_data: Data returned from other historical data methods
            analysis_type: Type of analysis ('summary', 'volatility', 'volume', 'greeks')
        
        Returns:
            Dictionary containing analysis results
        """
        if not historical_data.get("success") or not historical_data.get("data"):
            return {
                "success": False,
                "error": "Invalid or empty historical data provided",
                "analysis_type": analysis_type
            }
        
        data = historical_data["data"]
        data_type = historical_data.get("data_type", "unknown")
        
        analysis = {
            "success": True,
            "contract": historical_data.get("contract", {}),
            "data_type": data_type,
            "analysis_type": analysis_type,
            "period": {
                "from": historical_data.get("from_date"),
                "to": historical_data.get("to_date"),
                "count": len(data)
            }
        }
        
        if analysis_type == "summary":
            analysis["summary"] = self._generate_summary_analysis(data, data_type)
        elif analysis_type == "volatility" and data_type in ["ohlc", "quotes", "trades"]:
            analysis["volatility"] = self._generate_volatility_analysis(data)
        elif analysis_type == "volume" and data_type in ["trades", "ohlc"]:
            analysis["volume"] = self._generate_volume_analysis(data)
        elif analysis_type == "greeks" and data_type == "greeks":
            analysis["greeks_analysis"] = self._generate_greeks_analysis(data)
        elif analysis_type == "implied_volatility" and data_type == "implied_volatility":
            analysis["iv_analysis"] = self._generate_iv_analysis(data)
        else:
            analysis["error"] = f"Analysis type '{analysis_type}' not supported for data type '{data_type}'"
            analysis["supported_combinations"] = {
                "summary": ["all data types"],
                "volatility": ["ohlc", "quotes", "trades"],
                "volume": ["trades", "ohlc"],
                "greeks": ["greeks"],
                "implied_volatility": ["implied_volatility"]
            }
        
        return analysis

    def get_options_summary_for_ai(
        self,
        root: str,
        exp: int,
        strike: int,
        right: str,
        start_date: int,
        end_date: int,
        data_types: List[str] = None,
        max_samples_per_type: int = 5
    ) -> Dict[str, Any]:
        """
        Get a compressed, AI-friendly summary of options data across multiple data types.
        Perfect for AI agents that need comprehensive but concise market insights.
        
        Args:
            root: Underlying symbol
            exp: Expiration date as YYYYMMDD
            strike: Strike price in 1/10th cent
            right: 'C' for call, 'P' for put
            start_date: Start date as YYYYMMDD
            end_date: End date as YYYYMMDD
            data_types: List of data types to include ['ohlc', 'trades', 'implied_volatility', 'greeks', 'open_interest']
            max_samples_per_type: Maximum sample records per data type
        
        Returns:
            Compressed summary optimized for AI consumption with key insights and statistics
        """
        if data_types is None:
            data_types = ['ohlc', 'trades', 'implied_volatility', 'greeks']
        
        contract_info = OptionsContractInfo(
            root=root,
            exp=exp,
            strike=strike,
            right=right,
            strike_price_dollars=self._format_strike_price(strike),
            expiration_date_formatted=self._format_date(exp)
        )
        
        summary = {
            "success": True,
            "contract": contract_info.dict(),
            "period": {
                "from": self._format_date(start_date),
                "to": self._format_date(end_date),
                "days_to_expiration": self._calculate_days_to_expiration(exp)
            },
            "data_summary": {},
            "key_insights": [],
            "risk_metrics": {},
            "trading_signals": []
        }
        
        # Fetch and compress each data type
        errors = []
        
        for data_type in data_types:
            try:
                # Fetch data using appropriate method
                if data_type == 'ohlc':
                    raw_data = self.get_historical_options_ohlc(
                        root, exp, strike, right, start_date, end_date, ivl=300000)
                elif data_type == 'trades':
                    raw_data = self.get_historical_options_trades(
                        root, exp, strike, right, start_date, end_date, ivl=0)
                elif data_type == 'implied_volatility':
                    raw_data = self.get_historical_options_implied_volatility(
                        root, exp, strike, right, start_date, end_date, ivl=300000)
                elif data_type == 'greeks':
                    raw_data = self.get_historical_options_greeks(
                        root, exp, strike, right, start_date, end_date, ivl=900000)
                elif data_type == 'open_interest':
                    raw_data = self.get_historical_options_open_interest(
                        root, exp, strike, right, start_date, end_date)
                else:
                    continue
                
                if raw_data.get("success") and raw_data.get("data"):
                    # Compress the data
                    compressed = self._compress_data_for_ai(
                        raw_data["data"], 
                        data_type, 
                        max_samples_per_type
                    )
                    summary["data_summary"][data_type] = compressed
                    
                    # Add insights to key insights
                    if compressed.get("insights"):
                        summary["key_insights"].extend([
                            f"{data_type.upper()}: {insight}" 
                            for insight in compressed["insights"]
                        ])
                else:
                    errors.append(f"{data_type}: {raw_data.get('error', 'No data available')}")
                    
            except Exception as e:
                errors.append(f"{data_type}: {str(e)}")
        
        # Generate consolidated risk metrics
        summary["risk_metrics"] = self._generate_consolidated_risk_metrics(summary["data_summary"])
        
        # Generate trading signals
        summary["trading_signals"] = self._generate_trading_signals(summary["data_summary"])
        
        # Add errors if any
        if errors:
            summary["warnings"] = errors
        
        # Add executive summary
        summary["executive_summary"] = self._generate_executive_summary(summary)
        
        return summary

    def _generate_consolidated_risk_metrics(self, data_summary: Dict) -> Dict[str, Any]:
        """Generate consolidated risk metrics from multiple data types"""
        metrics = {}
        
        # Price risk from OHLC
        if 'ohlc' in data_summary:
            ohlc_stats = data_summary['ohlc'].get('statistics', {})
            metrics['price_volatility'] = abs(ohlc_stats.get('price_change_pct', 0))
            metrics['price_range_ratio'] = (
                (ohlc_stats.get('price_range', {}).get('high', 0) - 
                 ohlc_stats.get('price_range', {}).get('low', 0)) / 
                ohlc_stats.get('average_price', 1)
            ) if ohlc_stats.get('average_price', 0) > 0 else 0
        
        # Greeks risk
        if 'greeks' in data_summary:
            greeks_stats = data_summary['greeks'].get('statistics', {})
            metrics['delta_exposure'] = abs(greeks_stats.get('delta', 0))
            metrics['gamma_risk'] = abs(greeks_stats.get('gamma', 0))
            metrics['theta_decay'] = abs(greeks_stats.get('theta', 0))
            metrics['vega_risk'] = abs(greeks_stats.get('vega', 0))
        
        # IV risk
        if 'implied_volatility' in data_summary:
            iv_stats = data_summary['implied_volatility'].get('statistics', {})
            metrics['iv_level'] = iv_stats.get('current_iv', 0)
            metrics['iv_instability'] = abs(iv_stats.get('iv_change_pct', 0))
        
        # Liquidity risk from trades
        if 'trades' in data_summary:
            trade_stats = data_summary['trades'].get('statistics', {})
            metrics['liquidity_score'] = min(trade_stats.get('total_volume', 0) / 100, 10)  # 0-10 scale
        
        return metrics

    def _generate_trading_signals(self, data_summary: Dict) -> List[str]:
        """Generate trading signals based on consolidated data"""
        signals = []
        
        # Volume signals
        if 'trades' in data_summary:
            trade_stats = data_summary['trades'].get('statistics', {})
            if trade_stats.get('total_volume', 0) > 1000:
                signals.append("HIGH_VOLUME")
            if trade_stats.get('largest_trade', 0) > trade_stats.get('average_trade_size', 0) * 5:
                signals.append("BLOCK_ACTIVITY")
        
        # Price momentum signals
        if 'ohlc' in data_summary:
            ohlc_stats = data_summary['ohlc'].get('statistics', {})
            price_change = ohlc_stats.get('price_change_pct', 0)
            if price_change > 10:
                signals.append("STRONG_BULLISH")
            elif price_change > 5:
                signals.append("BULLISH")
            elif price_change < -10:
                signals.append("STRONG_BEARISH")
            elif price_change < -5:
                signals.append("BEARISH")
        
        # IV signals
        if 'implied_volatility' in data_summary:
            iv_stats = data_summary['implied_volatility'].get('statistics', {})
            if iv_stats.get('current_iv', 0) > 0.4:
                signals.append("HIGH_IV")
            elif iv_stats.get('current_iv', 0) < 0.15:
                signals.append("LOW_IV")
            
            if abs(iv_stats.get('iv_change_pct', 0)) > 15:
                signals.append("IV_CRUSH" if iv_stats.get('iv_change_pct', 0) < 0 else "IV_EXPANSION")
        
        # Greeks signals
        if 'greeks' in data_summary:
            greeks_stats = data_summary['greeks'].get('statistics', {})
            delta = greeks_stats.get('delta', 0)
            if delta > 0.8:
                signals.append("DEEP_ITM")
            elif 0.4 <= delta <= 0.6:
                signals.append("ATM")
            elif delta < 0.2:
                signals.append("DEEP_OTM")
        
        return signals

    def _generate_executive_summary(self, summary: Dict) -> str:
        """Generate a one-line executive summary for AI agents"""
        contract = summary['contract']
        signals = summary.get('trading_signals', [])
        key_insights = summary.get('key_insights', [])
        
        # Extract key metrics
        price_change = 0
        iv_level = 0
        volume = 0
        
        if 'ohlc' in summary['data_summary']:
            price_change = summary['data_summary']['ohlc'].get('statistics', {}).get('price_change_pct', 0)
        
        if 'implied_volatility' in summary['data_summary']:
            iv_level = summary['data_summary']['implied_volatility'].get('statistics', {}).get('current_iv', 0)
        
        if 'trades' in summary['data_summary']:
            volume = summary['data_summary']['trades'].get('statistics', {}).get('total_volume', 0)
        
        # Create summary
        direction = "up" if price_change > 0 else "down" if price_change < 0 else "flat"
        return (f"{contract['root']} ${contract['strike_price_dollars']:.0f} {contract['right']} "
                f"({summary['period']['days_to_expiration']}DTE) moved {direction} {abs(price_change):.1f}% "
                f"with {iv_level:.1%} IV and {volume:,.0f} volume. Signals: {', '.join(signals[:3])}")

    def _calculate_days_to_expiration(self, exp_date: int) -> int:
        """Calculate days to expiration from current date"""
        try:
            exp_str = str(exp_date)
            exp_datetime = datetime.strptime(exp_str, "%Y%m%d")
            today = datetime.now()
            return (exp_datetime - today).days
        except:
            return 0

    def _generate_summary_analysis(self, data: List[Dict], data_type: str) -> Dict[str, Any]:
        """Generate summary analysis for any data type"""
        if not data:
            return {"note": "No data available for analysis"}
        
        summary = {
            "total_records": len(data),
            "first_record": data[0] if data else None,
            "last_record": data[-1] if data else None
        }
        
        # Add specific analysis based on data type
        if data_type == "ohlc":
            prices = [record.get('close', 0) for record in data if record.get('close')]
            if prices:
                summary.update({
                    "price_range": {"min": min(prices), "max": max(prices)},
                    "average_close": sum(prices) / len(prices),
                    "price_change": prices[-1] - prices[0] if len(prices) > 1 else 0
                })
        
        return summary

    def _generate_volatility_analysis(self, data: List[Dict]) -> Dict[str, Any]:
        """Generate volatility analysis for price data"""
        return {"note": "Volatility analysis implementation pending"}

    def _generate_volume_analysis(self, data: List[Dict]) -> Dict[str, Any]:
        """Generate volume analysis for trade data"""
        return {"note": "Volume analysis implementation pending"}

    def _generate_greeks_analysis(self, data: List[Dict]) -> Dict[str, Any]:
        """Generate Greeks analysis for options data"""
        return {"note": "Greeks analysis implementation pending"}

    def _generate_iv_analysis(self, data: List[Dict]) -> Dict[str, Any]:
        """Generate implied volatility analysis for options data"""
        if not data:
            return {"note": "No implied volatility data available for analysis"}
        
        # Extract IV values
        bid_ivs = [record.get('bid_implied_vol', 0) for record in data if record.get('bid_implied_vol')]
        mid_ivs = [record.get('implied_vol', 0) for record in data if record.get('implied_vol')]
        ask_ivs = [record.get('ask_implied_vol', 0) for record in data if record.get('ask_implied_vol')]
        
        analysis = {
            "total_records": len(data),
            "iv_statistics": {}
        }
        
        # Analyze mid IVs (most commonly used)
        if mid_ivs:
            analysis["iv_statistics"]["mid_iv"] = {
                "min": min(mid_ivs),
                "max": max(mid_ivs),
                "average": sum(mid_ivs) / len(mid_ivs),
                "first": mid_ivs[0],
                "last": mid_ivs[-1],
                "change": mid_ivs[-1] - mid_ivs[0] if len(mid_ivs) > 1 else 0,
                "change_percent": ((mid_ivs[-1] - mid_ivs[0]) / mid_ivs[0] * 100) if len(mid_ivs) > 1 and mid_ivs[0] != 0 else 0
            }
        
        # Analyze bid-ask IV spread
        if bid_ivs and ask_ivs and len(bid_ivs) == len(ask_ivs):
            iv_spreads = [ask_ivs[i] - bid_ivs[i] for i in range(len(bid_ivs))]
            analysis["iv_statistics"]["bid_ask_spread"] = {
                "average_spread": sum(iv_spreads) / len(iv_spreads),
                "min_spread": min(iv_spreads),
                "max_spread": max(iv_spreads)
            }
        
        # IV level classification
        if mid_ivs:
            avg_iv = sum(mid_ivs) / len(mid_ivs)
            if avg_iv > 0.4:
                iv_level = "Very High"
            elif avg_iv > 0.3:
                iv_level = "High"
            elif avg_iv > 0.2:
                iv_level = "Moderate"
            elif avg_iv > 0.1:
                iv_level = "Low"
            else:
                iv_level = "Very Low"
            
            analysis["iv_level"] = {
                "classification": iv_level,
                "average_iv": avg_iv,
                "percentage": f"{avg_iv:.1%}"
            }
        
        return analysis 