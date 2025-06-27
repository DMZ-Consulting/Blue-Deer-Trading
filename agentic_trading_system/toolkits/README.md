# Polygon Options Trading Toolkit for Agno

A comprehensive toolkit that provides AI agents with professional-grade options trading capabilities using the Polygon.io API. This toolkit enables agents to analyze options chains, evaluate strategies, assess risk, and make informed trading decisions.

## Features

### 📊 Options Data & Analysis
- **Options Chain Retrieval**: Get complete options chains with filtering capabilities
- **Contract Details**: Detailed information about specific options contracts
- **Real-time Market Data**: Live quotes, Greeks, volume, and open interest
- **Comprehensive Analysis**: Intrinsic value, time value, moneyness calculations

### 🔍 Advanced Screening
- **Volume & Liquidity Filters**: Screen by volume, open interest, and bid-ask spreads
- **Expiration Filtering**: Target specific expiration timeframes
- **Moneyness Filters**: Find ITM, ATM, or OTM options
- **Custom Criteria**: Flexible screening for specific trading needs

### 📈 Strategy Development
- **Multi-leg Strategy Analysis**: Calculate P&L for complex options strategies
- **Break-even Analysis**: Identify break-even points for any strategy
- **Risk Assessment**: Comprehensive risk analysis for options positions
- **Greeks Analysis**: Delta, gamma, theta, vega calculations and interpretation

### 🎯 Specialized Use Cases
- **Earnings Strategies**: Volatility plays around earnings announcements
- **Risk Management**: Portfolio Greeks monitoring and position sizing
- **Market Making**: Spread analysis and liquidity assessment
- **Covered Calls**: Income generation strategies

## Installation

1. Install required dependencies:
```bash
pip install polygon-api-client pydantic python-dotenv
```

2. Set up your Polygon.io API key:
```bash
export POLYGON_API_KEY="your_polygon_api_key_here"
```

3. Import the toolkit in your agno agents:
```python
from toolkits.polygon_options import PolygonOptionsTools
```

## Quick Start

### Basic Agent Setup
```python
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from toolkits.polygon_options import PolygonOptionsTools

# Create an options trading agent
options_tools = PolygonOptionsTools()
agent = Agent(
    name="Options Analyst",
    model=OpenAIChat(id="gpt-4o"),
    tools=[options_tools],
    instructions=[
        "You are an expert options trading analyst.",
        "Use the Polygon Options tools to provide detailed analysis.",
        "Focus on risk management and practical trading insights."
    ]
)

# Use the agent
response = agent.run("Analyze AAPL options chain for next month")
```

### Options Chain Analysis
```python
# Get options chain for AAPL
chain = options_tools.get_options_chain(
    underlying_ticker="AAPL",
    strike_price_gte=180,
    strike_price_lte=200,
    option_type="call"
)
```

### Contract Analysis
```python
# Analyze specific contract
analysis = options_tools.analyze_options_contract(
    options_ticker="O:AAPL241220C00190000"
)
```

### Strategy P&L Calculation
```python
# Calculate iron condor P&L
strategy_legs = [
    {"ticker": "O:SPY241220C00580000", "position": "short", "quantity": 1},
    {"ticker": "O:SPY241220C00590000", "position": "long", "quantity": 1},
    {"ticker": "O:SPY241220P00570000", "position": "short", "quantity": 1},
    {"ticker": "O:SPY241220P00560000", "position": "long", "quantity": 1}
]

pnl_analysis = options_tools.calculate_option_strategy_pnl(
    strategy_legs=strategy_legs,
    underlying_price_range=(550, 600),
    price_step=1.0
)
```

## API Reference

### PolygonOptionsTools

The main toolkit class that provides all options trading functionality.

#### Constructor
```python
PolygonOptionsTools(api_key: Optional[str] = None)
```
- `api_key`: Polygon.io API key (uses POLYGON_API_KEY env var if not provided)

#### Methods

##### get_options_chain()
```python
get_options_chain(
    underlying_ticker: str,
    expiration_date: Optional[str] = None,
    strike_price_gte: Optional[float] = None,
    strike_price_lte: Optional[float] = None,
    option_type: Optional[str] = None,
    limit: int = 50
) -> List[Dict[str, Any]]
```
Retrieves options chain for an underlying stock with filtering capabilities.

##### get_options_contract_details()
```python
get_options_contract_details(options_ticker: str) -> Dict[str, Any]
```
Gets detailed information about a specific options contract.

##### get_options_market_data()
```python
get_options_market_data(options_ticker: str) -> Dict[str, Any]
```
Retrieves real-time market data including quotes, Greeks, and volume.

##### analyze_options_contract()
```python
analyze_options_contract(
    options_ticker: str,
    underlying_price: Optional[float] = None
) -> Dict[str, Any]
```
Performs comprehensive analysis including intrinsic value, time value, and moneyness.

##### screen_options_by_criteria()
```python
screen_options_by_criteria(
    underlying_ticker: str,
    min_volume: Optional[int] = None,
    max_spread_percent: Optional[float] = None,
    min_open_interest: Optional[int] = None,
    days_to_expiration_range: Optional[tuple] = None,
    moneyness_filter: Optional[str] = None,
    option_type: Optional[str] = None
) -> List[Dict[str, Any]]
```
Screens options based on various trading criteria.

##### calculate_option_strategy_pnl()
```python
calculate_option_strategy_pnl(
    strategy_legs: List[Dict[str, Any]],
    underlying_price_range: tuple,
    price_step: float = 1.0
) -> Dict[str, Any]
```
Calculates P&L for multi-leg options strategies across price ranges.

## Example Use Cases

### 1. Weekly Options Scanner
```python
agent.run("""
Scan for weekly options expiring this Friday on high-volume stocks like AAPL, TSLA, NVDA.
Find options with:
- Volume > 1000
- Open interest > 500
- Bid-ask spread < 3%
- Focus on near-the-money strikes
""")
```

### 2. Earnings Strategy Development
```python
agent.run("""
AMZN reports earnings next week. Design a volatility strategy:
1. Get the current implied volatility
2. Compare straddle vs strangle costs
3. Calculate break-even points
4. Recommend the best approach
""")
```

### 3. Risk Management Analysis
```python
agent.run("""
Analyze my current options portfolio:
1. Calculate total portfolio Greeks
2. Identify concentration risks
3. Suggest hedging strategies
4. Recommend position adjustments
""")
```

### 4. Covered Call Optimization
```python
agent.run("""
I own 500 shares of MSFT at $420 cost basis.
Find optimal covered call strikes for:
- 30-45 days to expiration
- Target 1-2% monthly income
- Minimize assignment risk
""")
```

## Data Models

### OptionsChainRequest
Request parameters for options chain queries.

### OptionsContractDetails
Comprehensive contract information including strikes, expirations, and contract specifications.

### OptionsMarketData
Real-time market data including quotes, Greeks, volume, and open interest.

### OptionsAnalysis
Analysis results including intrinsic value, time value, moneyness, and break-even calculations.

## Requirements

- Python 3.8+
- Polygon.io API key with options data access
- Agno framework
- Dependencies: `polygon-api-client`, `pydantic`, `python-dotenv`

## API Rate Limits

The toolkit respects Polygon.io rate limits:
- Free tier: 5 calls per minute
- Basic tier: 100 calls per minute
- Professional tier: 1000 calls per minute

## Support

For issues related to:
- **Toolkit functionality**: Open an issue in this repository
- **Polygon.io API**: Visit [Polygon.io documentation](https://polygon.io/docs)
- **Agno framework**: Check the Agno documentation

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## License

This toolkit is provided under the same license as the parent project.

---

**Note**: This toolkit requires a valid Polygon.io API key with options data access. Options trading involves significant risk and this toolkit is for informational purposes only. 