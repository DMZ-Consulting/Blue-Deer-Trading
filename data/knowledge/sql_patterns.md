
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
    