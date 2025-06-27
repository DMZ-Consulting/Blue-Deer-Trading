from agno.document.base import Document
from textwrap import dedent

def create_base_knowledge_documents() -> list:
    """Create foundational knowledge base documents"""
    strategy_research_doc = Document(
        content=dedent("""
        # Trading Strategy Research Framework
        
        ## Common Trading Strategy Categories
        
        ### Momentum Strategies
        - **Trend Following**: Moving average crossovers, breakout systems
        - **Momentum Oscillators**: RSI divergence, MACD signals
        - **Price Action**: Support/resistance breaks, pattern recognition
        - **Volume Momentum**: Volume-price analysis, accumulation/distribution
        
        ### Mean Reversion Strategies
        - **Oversold/Overbought**: RSI extremes, Bollinger band bounces
        - **Statistical Arbitrage**: Z-score reversions, pair trading
        - **Support/Resistance**: Level bounces, range trading
        - **Volatility Contraction**: Low volatility expansion plays
        
        ### Market Microstructure Strategies
        - **Scalping**: Bid-ask spread capture, order flow analysis
        - **Market Making**: Liquidity provision, inventory management
        - **Arbitrage**: Cross-market, temporal, statistical arbitrage
        - **Order Flow**: Level II analysis, tape reading
        
        ### Fundamental Strategies
        - **Earnings Based**: Pre/post earnings moves, surprise reactions
        - **News Based**: Event-driven trading, sentiment analysis
        - **Economic Data**: Macro releases, correlation trading
        - **Sector Rotation**: Thematic investing, relative strength
        
        ### Risk Management Strategies
        - **Position Sizing**: Kelly criterion, fixed fractional
        - **Stop Loss Systems**: Trailing stops, volatility-based stops
        - **Hedging**: Portfolio protection, tail risk hedging
        - **Diversification**: Correlation analysis, risk parity
        
        ## Research Sources and Methods
        
        ### Academic Sources
        - Quantitative finance journals
        - Trading competition results
        - Academic papers on market microstructure
        - Behavioral finance research
        
        ### Industry Sources
        - Hedge fund methodologies
        - Proprietary trading firm strategies
        - Exchange research and data
        - Financial technology innovations
        
        ### Data Analysis Approaches
        - Time series analysis
        - Statistical modeling
        - Machine learning applications
        - Behavioral pattern recognition
        """)
    )
    analysis_methods_doc = Document(
        content=dedent("""
        # Advanced Trading Data Analysis Methods
        
        ## Temporal Analysis Techniques
        
        ### Time-Based Bucketing
        - **Intraday Patterns**: Hour-by-hour performance analysis
        - **Day-of-Week Effects**: Systematic daily performance variations
        - **Monthly Seasonality**: Calendar effects and patterns
        - **Market Session Analysis**: Pre-market, regular hours, after-hours
        - **Holiday Effects**: Performance around market holidays
        
        ### Rolling Window Analysis
        - **Performance Stability**: Consistency across time periods
        - **Strategy Degradation**: Identification of strategy decay
        - **Market Regime Changes**: Adaptation to changing conditions
        - **Learning Curves**: Improvement patterns over time
        
        ## Performance Attribution Methods
        
        ### Factor Analysis
        - **Market Exposure**: Beta analysis and market correlation
        - **Sector Attribution**: Performance by industry/sector
        - **Size Effects**: Large cap vs small cap performance
        - **Volatility Attribution**: Performance in different VIX regimes
        
        ### Risk-Adjusted Metrics
        - **Sharpe Ratio Analysis**: Risk-adjusted return calculation
        - **Maximum Drawdown**: Peak-to-trough analysis
        - **Calmar Ratio**: Return to max drawdown ratio
        - **Sortino Ratio**: Downside deviation adjusted returns
        
        ## Behavioral Analysis Techniques
        
        ### Decision Pattern Analysis
        - **Entry Timing Consistency**: Systematic vs random entry patterns
        - **Exit Discipline**: Systematic vs emotional exit patterns
        - **Position Sizing Evolution**: Risk management consistency
        - **Loss Recovery Patterns**: Behavior after losses
        
        ### Psychological Indicators
        - **Revenge Trading**: Oversized positions after losses
        - **Overconfidence**: Position size increase after wins
        - **Loss Aversion**: Asymmetric risk-taking behavior
        - **Recency Bias**: Recent performance affecting decisions
        
        ## Advanced Statistical Methods
        
        ### Clustering Analysis
        - **Trade Similarity**: Grouping similar trade characteristics
        - **Market Condition Clustering**: Similar market environments
        - **Performance Clustering**: Grouping by outcome patterns
        - **Time Clustering**: Similar temporal characteristics
        
        ### Correlation Analysis
        - **Multi-Factor Correlation**: Relationship between variables
        - **Lead-Lag Analysis**: Temporal relationships
        - **Regime Correlation**: Changing relationships over time
        - **Cross-Asset Correlation**: Relationships across instruments
        
        ## Strategy Validation Frameworks
        
        ### Statistical Significance Testing
        - **Sample Size Requirements**: Minimum trades for reliability
        - **Confidence Intervals**: Statistical confidence in results
        - **P-Value Analysis**: Significance of observed patterns
        - **Monte Carlo Simulation**: Randomness testing
        
        ### Out-of-Sample Testing
        - **Walk-Forward Analysis**: Progressive testing methodology
        - **Cross-Validation**: Multiple period validation
        - **Robustness Testing**: Performance across conditions
        - **Stability Analysis**: Consistency across time periods
        """)
    )
    sql_patterns_doc = Document(
        content=dedent("""
        # SQL Analysis Patterns for Trading Strategy Discovery
        
        ## Temporal Pattern Queries
        
        ### Hour-by-Hour Analysis
        ```sql
        SELECT 
            entry_hour,
            COUNT(*) as trade_count,
            AVG(pnl) as avg_pnl,
            STDDEV(pnl) as pnl_volatility,
            COUNT(CASE WHEN pnl > 0 THEN 1 END) * 100.0 / COUNT(*) as win_rate,
            SUM(pnl) as total_pnl,
            AVG(duration_hours) as avg_duration
        FROM trading_data
        GROUP BY entry_hour
        HAVING trade_count >= 10
        ORDER BY avg_pnl DESC;
        ```
        
        ### Market Session Performance
        ```sql
        SELECT 
            CASE 
                WHEN entry_hour BETWEEN 4 AND 9 THEN 'Pre-Market'
                WHEN entry_hour BETWEEN 9 AND 16 THEN 'Regular Hours'
                WHEN entry_hour BETWEEN 16 AND 20 THEN 'After Hours'
                ELSE 'Overnight'
            END as market_session,
            COUNT(*) as trades,
            AVG(pnl) as avg_pnl,
            SUM(pnl) as total_pnl,
            COUNT(CASE WHEN pnl > 0 THEN 1 END) * 100.0 / COUNT(*) as win_rate
        FROM trading_data
        GROUP BY market_session
        ORDER BY avg_pnl DESC;
        ```
        
        ## Strategy Pattern Discovery
        
        ### Quick Momentum Plays
        ```sql
        SELECT 
            symbol,
            AVG(pnl) as avg_pnl,
            COUNT(*) as trade_count,
            AVG(duration_hours) as avg_duration,
            COUNT(CASE WHEN pnl > 0 THEN 1 END) * 100.0 / COUNT(*) as win_rate
        FROM trading_data
        WHERE duration_hours < 2  -- Quick trades
        AND ABS(pnl) > 50  -- Meaningful moves
        GROUP BY symbol
        HAVING trade_count >= 5
        ORDER BY avg_pnl DESC;
        ```
        
        ### Size Momentum Analysis
        ```sql
        SELECT 
            CASE 
                WHEN quantity < 100 THEN 'Small'
                WHEN quantity < 500 THEN 'Medium'
                WHEN quantity < 1000 THEN 'Large'
                ELSE 'Very Large'
            END as position_size,
            AVG(duration_hours) as avg_duration,
            AVG(pnl) as avg_pnl,
            COUNT(*) as trade_count,
            STDDEV(pnl) as volatility
        FROM trading_data
        GROUP BY position_size
        ORDER BY avg_pnl DESC;
        ```
        
        ## Risk Pattern Analysis
        
        ### Consecutive Trade Analysis
        ```sql
        WITH consecutive_trades AS (
            SELECT *,
                LAG(pnl, 1) OVER (ORDER BY entry_time) as prev_pnl,
                LAG(pnl, 2) OVER (ORDER BY entry_time) as prev_pnl_2
            FROM trading_data
        )
        SELECT 
            CASE 
                WHEN prev_pnl > 0 AND prev_pnl_2 > 0 THEN 'After 2 Wins'
                WHEN prev_pnl > 0 THEN 'After 1 Win'
                WHEN prev_pnl < 0 AND prev_pnl_2 < 0 THEN 'After 2 Losses'
                WHEN prev_pnl < 0 THEN 'After 1 Loss'
                ELSE 'First Trades'
            END as trade_context,
            COUNT(*) as trade_count,
            AVG(pnl) as avg_pnl,
            AVG(quantity) as avg_position_size,
            COUNT(CASE WHEN pnl > 0 THEN 1 END) * 100.0 / COUNT(*) as win_rate
        FROM consecutive_trades
        WHERE prev_pnl IS NOT NULL
        GROUP BY trade_context
        ORDER BY avg_pnl DESC;
        ```
        
        ## Advanced Pattern Discovery
        
        ### Volatility Regime Analysis
        ```sql
        WITH volatility_calc AS (
            SELECT *,
                STDDEV(pnl) OVER (
                    ORDER BY entry_time 
                    ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
                ) as rolling_volatility
            FROM trading_data
        )
        SELECT 
            CASE 
                WHEN rolling_volatility < 50 THEN 'Low Vol'
                WHEN rolling_volatility < 100 THEN 'Medium Vol'
                ELSE 'High Vol'
            END as volatility_regime,
            COUNT(*) as trade_count,
            AVG(pnl) as avg_pnl,
            AVG(duration_hours) as avg_duration,
            COUNT(CASE WHEN pnl > 0 THEN 1 END) * 100.0 / COUNT(*) as win_rate
        FROM volatility_calc
        WHERE rolling_volatility IS NOT NULL
        GROUP BY volatility_regime
        ORDER BY avg_pnl DESC;
        ```
        
        ### Multi-Factor Strategy Discovery
        ```sql
        SELECT 
            symbol,
            entry_hour,
            side,
            CASE 
                WHEN duration_hours < 1 THEN 'Scalp'
                WHEN duration_hours < 4 THEN 'Short'
                WHEN duration_hours < 24 THEN 'Intraday'
                ELSE 'Swing'
            END as strategy_type,
            COUNT(*) as trade_count,
            AVG(pnl) as avg_pnl,
            SUM(pnl) as total_pnl,
            AVG(quantity) as avg_size,
            COUNT(CASE WHEN pnl > 0 THEN 1 END) * 100.0 / COUNT(*) as win_rate
        FROM trading_data
        GROUP BY symbol, entry_hour, side, strategy_type
        HAVING trade_count >= 3
        ORDER BY avg_pnl DESC, total_pnl DESC
        LIMIT 50;
        ```
        """)
    )
    return [strategy_research_doc, analysis_methods_doc, sql_patterns_doc]
