from pathlib import Path
from textwrap import dedent

def create_data_documents():
    """
    Create separate data document files for clean code organization.
    This shows how to move knowledge base content to external files.
    """
    
    data_dir = Path("data/knowledge")
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # Strategy research document
    strategy_research_content = dedent("""
    # Trading Strategy Research Framework
    
    ## Momentum Strategies
    
    ### Trend Following Systems
    - Moving Average Crossovers
    - Breakout Systems
    - Price Action Patterns
    
    ### Momentum Oscillators
    - RSI Divergence
    - MACD Signals
    - Stochastic Patterns
    
    ## Mean Reversion Strategies
    
    ### Statistical Approaches
    - Z-Score Reversions
    - Bollinger Band Bounces
    - Pair Trading
    
    ### Support/Resistance
    - Level Testing
    - Range Trading
    - Fibonacci Retracements
    
    ## Advanced Strategies
    
    ### Market Microstructure
    - Order Flow Analysis
    - Level II Patterns
    - Liquidity Analysis
    
    ### Multi-Timeframe
    - Cross-Timeframe Confirmation
    - Fractal Analysis
    - Pyramid Strategies
    """)
    
    with open(data_dir / "strategy_research.md", "w") as f:
        f.write(strategy_research_content)
    
    # Analysis methods document
    analysis_methods_content = dedent("""
    # Advanced Analysis Methods
    
    ## Temporal Analysis
    
    ### Time-Based Patterns
    - Intraday Seasonality
    - Weekly Patterns
    - Monthly Effects
    - Holiday Impact
    
    ### Rolling Window Analysis
    - Performance Stability
    - Strategy Decay Detection
    - Regime Change Analysis
    
    ## Statistical Methods
    
    ### Distribution Analysis
    - PnL Distribution Fitting
    - Tail Risk Analysis
    - Skewness and Kurtosis
    
    ### Correlation Studies
    - Multi-Factor Analysis
    - Lead-Lag Relationships
    - Regime Correlation
    
    ## Behavioral Analysis
    
    ### Decision Patterns
    - Entry Timing Consistency
    - Exit Discipline
    - Position Sizing Evolution
    
    ### Psychological Indicators
    - Revenge Trading Detection
    - Overconfidence Patterns
    - Loss Aversion Analysis
    """)
    
    with open(data_dir / "analysis_methods.md", "w") as f:
        f.write(analysis_methods_content)
    
    # SQL patterns document
    sql_patterns_content = dedent("""
    # SQL Analysis Patterns
    
    ## Performance Analysis
    
    ### Basic Metrics
    ```sql
    -- Win Rate and PnL Analysis
    SELECT 
        COUNT(*) as total_trades,
        AVG(pnl) as avg_pnl,
        COUNT(CASE WHEN pnl > 0 THEN 1 END) * 100.0 / COUNT(*) as win_rate
    FROM trading_data;
    ```
    
    ### Risk Metrics
    ```sql
    -- Sharpe Ratio Calculation
    SELECT 
        AVG(pnl) / NULLIF(STDDEV(pnl), 0) as sharpe_ratio,
        MIN(pnl) as max_loss,
        MAX(pnl) as max_win
    FROM trading_data;
    ```
    
    ## Pattern Discovery
    
    ### Temporal Patterns
    ```sql
    -- Hour-by-Hour Performance
    SELECT 
        entry_hour,
        COUNT(*) as trades,
        AVG(pnl) as avg_pnl,
        STDDEV(pnl) as volatility
    FROM trading_data
    GROUP BY entry_hour
    ORDER BY avg_pnl DESC;
    ```
    
    ### Strategy Patterns
    ```sql
    -- Multi-Factor Analysis
    SELECT 
        symbol,
        side,
        CASE 
            WHEN duration_hours < 1 THEN 'Scalp'
            WHEN duration_hours < 24 THEN 'Intraday'
            ELSE 'Swing'
        END as strategy_type,
        COUNT(*) as trades,
        AVG(pnl) as avg_pnl
    FROM trading_data
    GROUP BY symbol, side, strategy_type
    HAVING trades >= 5
    ORDER BY avg_pnl DESC;
    ```
    """)
    
    with open(data_dir / "sql_patterns.md", "w") as f:
        f.write(sql_patterns_content)
    
    print("📄 Knowledge documents created in ./data/knowledge/")

if __name__ == "__main__":
    create_data_documents()