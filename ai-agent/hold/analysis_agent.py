from io import StringIO
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.knowledge.document import DocumentKnowledgeBase
from agno.vectordb.lancedb import LanceDb
from agno.vectordb.search import SearchType
from agno.embedder.openai import OpenAIEmbedder
from agno.tools.knowledge import KnowledgeTools
from agno.tools.reasoning import ReasoningTools
from agno.document.base import Document
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from typing import Dict, List, Any
import json

load_dotenv()

class TradingAnalysisAgent:
    """
    Advanced Trading Strategy Analysis Agent that can:
    - Analyze trading patterns and identify underlying strategies
    - Explain how patterns were found using AI interpretation
    - Identify when and where the user makes the most money
    - Assess consistency to trading style
    - Differentiate between randomness and set patterns
    - Perform momentum analysis
    """
    
    def __init__(self, postgres_agent):
        self.postgres_agent = postgres_agent
        self.knowledge_base = self._create_knowledge_base()
        self.analysis_agent = self._create_analysis_agent()
        
    def _create_knowledge_base(self):
        """Create a knowledge base with trading strategy documents and momentum analysis."""
        
        # Define trading strategy and momentum analysis knowledge
        trading_strategies_doc = Document(
            content="""
            # Trading Strategy Patterns and Analysis Framework
            
            ## Common Trading Strategies
            
            ### Trend Following Strategies
            - **Moving Average Crossovers**: Buy when short MA crosses above long MA, sell when opposite
            - **Breakout Trading**: Enter positions when price breaks above resistance or below support
            - **Momentum Trading**: Follow strong price movements in the direction of the trend
            
            ### Mean Reversion Strategies
            - **RSI Reversal**: Buy when RSI below 30, sell when above 70
            - **Bollinger Band Bounce**: Buy at lower band, sell at upper band
            - **Support/Resistance Trading**: Buy at support, sell at resistance
            
            ### Pattern Recognition Strategies
            - **Cup and Handle**: Bullish continuation pattern
            - **Head and Shoulders**: Bearish reversal pattern
            - **Double Top/Bottom**: Reversal patterns at key levels
            
            ### Time-Based Strategies
            - **Day Trading**: Positions held for minutes to hours
            - **Swing Trading**: Positions held for days to weeks
            - **Position Trading**: Positions held for weeks to months
            
            ## Key Performance Metrics
            
            ### Profitability Metrics
            - **Win Rate**: Percentage of profitable trades
            - **Average Win vs Average Loss**: Risk-reward ratio analysis
            - **Profit Factor**: Gross profit divided by gross loss
            - **Maximum Drawdown**: Largest peak-to-trough decline
            
            ### Consistency Metrics
            - **Standard Deviation of Returns**: Measure of volatility
            - **Sharpe Ratio**: Risk-adjusted return measure
            - **Calmar Ratio**: Annual return divided by maximum drawdown
            - **Consecutive Wins/Losses**: Streak analysis
            
            ### Timing Metrics
            - **Average Hold Time**: How long positions are typically held
            - **Time of Day Analysis**: When most profitable trades occur
            - **Day of Week Analysis**: Which days perform best
            - **Market Condition Analysis**: Performance in different market states
            
            ## Pattern Detection Methods
            
            ### Statistical Analysis
            - **Correlation Analysis**: Relationship between different variables
            - **Regression Analysis**: Trend identification and prediction
            - **Cluster Analysis**: Grouping similar trades
            - **Time Series Analysis**: Temporal pattern identification
            
            ### Behavioral Analysis
            - **Entry Timing Patterns**: Consistent entry conditions
            - **Exit Timing Patterns**: Consistent exit conditions
            - **Position Sizing Patterns**: Risk management consistency
            - **Market Selection Patterns**: Asset or sector preferences
            
            ## Randomness vs Pattern Identification
            
            ### Signs of Random Trading
            - No correlation between entry conditions and outcomes
            - Inconsistent position sizing
            - Random timing of entries and exits
            - No clear risk management rules
            - Win rate around 50% with no edge
            
            ### Signs of Strategic Trading
            - Consistent entry and exit criteria
            - Clear risk management rules
            - Repeatable patterns in profitable trades
            - Edge in specific market conditions
            - Correlation between strategy elements and outcomes
            
            ## Momentum Analysis Framework
            
            ### Price Momentum Indicators
            - **Rate of Change (ROC)**: Percentage change over time periods
            - **Momentum Oscillator**: Current price minus price n periods ago
            - **MACD**: Moving Average Convergence Divergence
            - **ADX**: Average Directional Index for trend strength
            
            ### Volume Momentum
            - **Volume Rate of Change**: Change in trading volume
            - **On-Balance Volume**: Cumulative volume based on price direction
            - **Accumulation/Distribution Line**: Volume and price relationship
            
            ### Market Momentum States
            - **Strong Uptrend**: Higher highs, higher lows, increasing volume
            - **Weak Uptrend**: Higher highs, decreasing momentum
            - **Consolidation**: Sideways movement, unclear direction
            - **Weak Downtrend**: Lower lows, decreasing momentum
            - **Strong Downtrend**: Lower highs, lower lows, increasing volume
            
            ## Strategy Consistency Analysis
            
            ### Consistency Indicators
            - **Entry Consistency**: Similar conditions for trade initiation
            - **Exit Consistency**: Similar conditions for trade closure
            - **Risk Consistency**: Consistent position sizing and stop losses
            - **Time Consistency**: Similar holding periods for similar setups
            
            ### Inconsistency Red Flags
            - Widely varying position sizes without clear logic
            - Random entry and exit timing
            - No apparent stop loss or risk management
            - Emotional decision-making patterns
            - Lack of correlation between similar setups
            """
        )
        
        momentum_analysis_doc = Document(
            content="""
            # Advanced Momentum Analysis for Trading Strategies
            
            ## Momentum Characteristics Analysis
            
            ### Identifying Momentum Trades
            Momentum trades typically exhibit:
            - Entry during strong directional moves
            - Quick profit taking or trend following
            - Higher win rates in trending markets
            - Correlation with market volatility
            
            ### Momentum Entry Patterns
            - **Breakout Momentum**: Entering on price breakouts above resistance
            - **Pullback Momentum**: Entering on pullbacks in strong trends
            - **Gap Momentum**: Trading gaps in the direction of the trend
            - **News Momentum**: Trading on fundamental catalysts
            
            ### Momentum Exit Strategies
            - **Trailing Stops**: Following the trend with protective stops
            - **Target Exits**: Pre-defined profit targets based on momentum strength
            - **Momentum Exhaustion**: Exiting when momentum indicators weaken
            - **Time-Based Exits**: Exiting after predetermined time periods
            
            ## Performance Analysis in Different Market Conditions
            
            ### Trending Markets
            - Higher success rates for momentum strategies
            - Longer average hold times
            - Better risk-reward ratios
            - Higher profit factors
            
            ### Ranging Markets
            - Lower success rates for momentum strategies
            - More frequent false breakouts
            - Higher importance of quick exits
            - Better suited for mean reversion
            
            ### Volatile Markets
            - Increased profit potential but higher risk
            - Need for wider stops and targets
            - More opportunities but faster execution required
            - Higher emotional stress and decision fatigue
            
            ## Money-Making Pattern Identification
            
            ### High-Profit Trade Characteristics
            Look for common elements in most profitable trades:
            - Specific entry times or market conditions
            - Particular assets or sectors
            - Consistent position sizing relative to account
            - Similar market volatility levels
            - Specific risk-reward ratios
            
            ### Optimal Conditions Analysis
            - **Time Analysis**: Best performing hours, days, months
            - **Market Condition Analysis**: Bull vs bear vs sideways markets
            - **Volatility Analysis**: Optimal VIX levels or ATR ranges
            - **Sector Analysis**: Which sectors provide best opportunities
            - **Setup Analysis**: Which technical setups work best
            
            ### Loss Pattern Analysis
            - **Common Loss Scenarios**: Identifying recurring loss patterns
            - **Risk Management Failures**: Where stops were too tight/wide
            - **Market Condition Mismatches**: Wrong strategy for market state
            - **Emotional Trading Indicators**: Revenge trading, overconfidence
            
            ## Strategy Evolution Analysis
            
            ### Learning Curve Identification
            - Improvement in win rates over time
            - Better risk management over time
            - Adaptation to different market conditions
            - Refinement of entry and exit criteria
            
            ### Strategy Refinement Indicators
            - Consistent improvement in key metrics
            - Better performance in previously challenging conditions
            - Reduced maximum drawdown periods
            - More consistent month-to-month performance
            """
        )
        
        # Create knowledge base with trading documents
        knowledge_base = DocumentKnowledgeBase(
            documents=[trading_strategies_doc, momentum_analysis_doc],
            vector_db=LanceDb(
                table_name="trading_strategy_knowledge",
                uri="./tmp/trading_lancedb",
                search_type=SearchType.hybrid,
                embedder=OpenAIEmbedder(id="text-embedding-3-small"),
            ),
        )
        
        return knowledge_base
    
    def _create_analysis_agent(self):
        """Create the main analysis agent with knowledge and reasoning tools."""
        
        # Create knowledge tools with advanced capabilities
        knowledge_tools = KnowledgeTools(
            knowledge=self.knowledge_base,
            think=True,      # Enable analytical thinking
            search=True,     # Enable knowledge base search
            analyze=True,    # Enable deep analysis capabilities
            add_few_shot=True,  # Add examples for better performance
        )
        
        # Create reasoning tools for logical analysis
        reasoning_tools = ReasoningTools(
            add_instructions=True
        )
        
        # Create the analysis agent
        agent = Agent(
            name="Trading Strategy Analysis Agent",
            model=OpenAIChat(id="gpt-4o"),
            tools=[knowledge_tools, reasoning_tools],
            instructions=[
                "You are an expert trading strategy analyst with deep knowledge of market patterns and trading psychology.",
                "Your role is to analyze trading data and identify underlying strategies, patterns, and decision-making processes.",
                "Always search your knowledge base first before providing analysis.",
                "Provide clear explanations of HOW patterns were identified and WHY they indicate specific strategies.",
                "Use statistical analysis and behavioral analysis to support your conclusions.",
                "Differentiate between random outcomes and systematic patterns.",
                "Focus on actionable insights that can improve trading performance.",
                "Always cite specific evidence from the data to support your analysis.",
                "Use tables and structured formatting to present analysis clearly.",
                "Be objective and highlight both strengths and weaknesses in trading patterns."
            ],
            knowledge=self.knowledge_base,
            search_knowledge=True,
            show_tool_calls=True,
            markdown=True,
            add_datetime_to_instructions=True,
        )
        
        return agent
    
    def load_knowledge_base(self, recreate=False):
        """Load the knowledge base."""
        self.knowledge_base.load(recreate=recreate)
    
    def get_trading_data(self, query: str) -> pd.DataFrame:
        """Get trading data from the postgres agent."""
        try:
            # Get the raw response from the postgres agent
            response = self.postgres_agent.run(query)
            
            # Extract the data - this might need adjustment based on your postgres agent's response format
            # Assuming the postgres agent returns the data in some accessible format
            if hasattr(response, 'content'):
                data_text = response.content
            else:
                data_text = str(response)
            
            # Parse the response to extract tabular data
            # This is a simplified example - you might need to adjust based on actual response format
            return self._parse_trading_data(data_text)
            
        except Exception as e:
            print(f"Error getting trading data: {e}")
            return pd.DataFrame()
    
    def _parse_trading_data(self, data_text: str) -> pd.DataFrame:
        """Parse trading data from text response - customize based on your data format."""
        # This is a placeholder - implement based on your actual data format
        # You might need to parse SQL results, CSV format, or other structured data
        try:
            # Example implementation - adjust as needed
            lines = data_text.split('\n')
            # Process lines to create DataFrame
            # This is just an example structure
            return pd.DataFrame()
        except:
            return pd.DataFrame()
    
    def analyze_trading_strategy(self, analysis_type: str = "comprehensive", 
                               custom_query: str = None,
                               date_range: tuple = None,
                               data: pd.DataFrame = None) -> str:
        """
        Perform comprehensive trading strategy analysis.
        
        Args:
            analysis_type: Type of analysis ("comprehensive", "patterns", "profitability", "consistency", "momentum")
            custom_query: Custom SQL query for specific data analysis
            date_range: Tuple of (start_date, end_date) for time-based analysis
        """
        
        # Build appropriate query based on analysis type
        if custom_query:
            base_query = custom_query
        else:
            base_query = self._build_analysis_query(analysis_type, date_range)
        
        # Get trading data
        print(f"Fetching trading data with query: {base_query}")
        trading_data = data if data is not None else self.get_trading_data(base_query)
        
        # Prepare analysis prompt based on type
        analysis_prompt = self._build_analysis_prompt(analysis_type, trading_data)
        
        # Get analysis from the agent
        print("Analyzing trading patterns...")
        response = self.analysis_agent.run(analysis_prompt)
        
        return response.content if hasattr(response, 'content') else str(response)
    
    def _build_analysis_query(self, analysis_type: str, date_range: tuple = None) -> str:
        """Build SQL query based on analysis type."""
        
        base_tables = """
        SELECT 
            trade_id,
            symbol,
            side,
            quantity,
            entry_price,
            exit_price,
            entry_time,
            exit_time,
            pnl,
            fees,
            EXTRACT(EPOCH FROM (exit_time - entry_time))/3600 as duration_hours,
            EXTRACT(DOW FROM entry_time) as entry_day_of_week,
            EXTRACT(HOUR FROM entry_time) as entry_hour,
            CASE WHEN pnl > 0 THEN 'WIN' ELSE 'LOSS' END as outcome
        FROM trades 
        WHERE exit_time IS NOT NULL
        """
        
        if date_range:
            base_tables += f" AND entry_time >= '{date_range[0]}' AND entry_time <= '{date_range[1]}'"
        
        if analysis_type == "comprehensive":
            return base_tables + " ORDER BY entry_time DESC LIMIT 1000"
        elif analysis_type == "patterns":
            return base_tables + " ORDER BY entry_time DESC LIMIT 500"
        elif analysis_type == "profitability":
            return base_tables + " ORDER BY pnl DESC LIMIT 200"
        elif analysis_type == "momentum":
            return base_tables + " AND duration_hours < 24 ORDER BY entry_time DESC LIMIT 300"
        else:
            return base_tables + " ORDER BY entry_time DESC LIMIT 500"
    
    def _build_analysis_prompt(self, analysis_type: str, trading_data: pd.DataFrame) -> str:
        """Build analysis prompt based on type and data."""
        
        # Convert data to summary statistics for analysis
        data_summary = self._create_data_summary(trading_data)
        
        base_prompt = f"""
        Please analyze the following trading data and provide insights about the underlying trading strategy.
        
        Trading Data Summary:
        {data_summary}
        
        Please focus on the following aspects based on the analysis type: {analysis_type}
        """
        
        if analysis_type == "comprehensive":
            prompt_addition = """
            Provide a comprehensive analysis including:
            1. **Strategy Identification**: What trading strategies does this data suggest?
            2. **Pattern Recognition**: What consistent patterns do you observe?
            3. **Profitability Analysis**: When and where does the trader make the most money?
            4. **Consistency Assessment**: How consistent is the trading approach?
            5. **Randomness vs Systematic**: Is this systematic trading or random?
            6. **Momentum Analysis**: How does the trader handle momentum?
            7. **Recommendations**: What improvements could be made?
            
            Use your knowledge base to explain HOW you identified these patterns and WHY they indicate specific strategies.
            """
        elif analysis_type == "patterns":
            prompt_addition = """
            Focus on pattern identification:
            1. Entry and exit timing patterns
            2. Position sizing patterns  
            3. Asset selection patterns
            4. Time-based patterns (day of week, hour of day)
            5. Market condition patterns
            
            Explain HOW each pattern was identified and what it suggests about the trading approach.
            """
        elif analysis_type == "profitability":
            prompt_addition = """
            Focus on profitability analysis:
            1. **Where Most Money is Made**: Identify the specific conditions, times, assets, or setups that generate the highest profits
            2. **Win Rate Analysis**: Analyze the percentage of profitable trades and what characterizes winning trades
            3. **Risk-Reward Analysis**: Examine the relationship between risk taken and rewards achieved
            4. **Loss Analysis**: Identify what causes the biggest losses and how they could be avoided
            5. **Optimization Opportunities**: Suggest ways to increase profitability based on the patterns observed
            
            Provide specific, actionable insights about when and how this trader makes money.
            """
        elif analysis_type == "momentum":
            prompt_addition = """
            Focus on momentum analysis:
            1. How does the trader identify and enter momentum trades?
            2. What is the typical duration of momentum trades?
            3. How does performance vary with market momentum conditions?
            4. Are there specific momentum indicators being used?
            5. How does the trader exit momentum trades?
            
            Use your momentum analysis knowledge to provide detailed insights.
            """
        else:
            prompt_addition = "Provide a general analysis of the trading patterns and strategies observed."
        
        return base_prompt + prompt_addition
    
    def _create_data_summary(self, df: pd.DataFrame) -> str:
        """Create a statistical summary of trading data for analysis."""
        if df.empty:
            return "No trading data available for analysis."
        
        try:
            summary = f"""
            Total Trades: {len(df)}
            Date Range: {df['entry_time'].min()} to {df['entry_time'].max()}
            
            Performance Metrics:
            - Total PnL: ${df['pnl'].sum():.2f}
            - Average PnL per Trade: ${df['pnl'].mean():.2f}
            - Win Rate: {(df['pnl'] > 0).mean()*100:.1f}%
            - Average Winner: ${df[df['pnl'] > 0]['pnl'].mean():.2f}
            - Average Loser: ${df[df['pnl'] < 0]['pnl'].mean():.2f}
            - Largest Win: ${df['pnl'].max():.2f}
            - Largest Loss: ${df['pnl'].min():.2f}
            
            Trading Patterns:
            - Average Hold Time: {df['duration_hours'].mean():.1f} hours
            - Most Active Day: {df['entry_day_of_week'].mode().iloc[0] if not df['entry_day_of_week'].mode().empty else 'N/A'}
            - Most Active Hour: {df['entry_hour'].mode().iloc[0] if not df['entry_hour'].mode().empty else 'N/A'}
            - Most Traded Symbol: {df['symbol'].mode().iloc[0] if not df['symbol'].mode().empty else 'N/A'}
            - Long vs Short Ratio: {(df['side'] == 'BUY').mean()*100:.1f}% Long
            
            Risk Metrics:
            - Standard Deviation of PnL: ${df['pnl'].std():.2f}
            - Maximum Drawdown: Analysis needed with sequential data
            - Average Position Size: {df['quantity'].mean():.2f}
            """
            
            return summary
        except Exception as e:
            return f"Error creating data summary: {e}"
    
    def analyze_specific_pattern(self, pattern_description: str) -> str:
        """Analyze a specific pattern described by the user."""
        
        prompt = f"""
        I need you to analyze a specific trading pattern or behavior. Here's what I'm looking for:
        
        {pattern_description}
        
        Please:
        1. Search your knowledge base for relevant information about this pattern
        2. Explain what this pattern typically indicates about trading strategy
        3. Provide guidance on how to identify this pattern in trading data
        4. Suggest what data points I should look for
        5. Explain whether this indicates systematic trading or random behavior
        6. Provide recommendations for analysis or improvement
        
        Use your trading strategy knowledge to provide detailed insights.
        """
        
        response = self.analysis_agent.run(prompt)
        return response.content if hasattr(response, 'content') else str(response)
    
    def explain_analysis_methodology(self) -> str:
        """Explain how the AI performs its analysis."""
        
        prompt = """
        Please explain your methodology for analyzing trading data and identifying patterns. Cover:
        
        1. **Pattern Detection Methods**: How do you identify trading patterns and strategies?
        2. **Statistical Analysis**: What statistical methods do you use?
        3. **Behavioral Analysis**: How do you analyze trading behavior and psychology?
        4. **Consistency Assessment**: How do you determine if trading is systematic vs random?
        5. **Momentum Analysis**: How do you analyze momentum trading patterns?
        6. **Profitability Analysis**: How do you identify where and when traders make money?
        7. **Evidence Requirements**: What evidence do you look for to support conclusions?
        
        Provide a comprehensive explanation of your analytical framework.
        """
        
        response = self.analysis_agent.run(prompt)
        return response.content if hasattr(response, 'content') else str(response)


# Example usage and testing
def create_trading_analysis_system(postgres_agent):
    """Create and initialize the trading analysis system."""
    
    # Create the analysis agent
    analysis_system = TradingAnalysisAgent(postgres_agent)
    
    # Load the knowledge base (set recreate=True on first run)
    print("Loading trading strategy knowledge base...")
    analysis_system.load_knowledge_base(recreate=False)
    
    return analysis_system


# Integration with your existing postgres agent
if __name__ == "__main__":
    # Import your existing postgres agent setup
    from custom_toolkits import get_postgres_agent  # Replace with your actual import
    
    # Get your postgres agent
    postgres_agent = get_postgres_agent()
    
    # Create the analysis system
    analysis_system = create_trading_analysis_system(postgres_agent)

    trading_data = postgres_agent.run("Get all trades that have been closed. Make sure to only include fields that are going to be relevant for analysis. This includes the trade_id, symbol, trade_type, size, average_price, average_exit_price, created_at, closed_at, win_loss, expiration_date, strike_price, option_type, open_date, is_contract, and profit_loss. Return CSV with headers so that it can be used as a pandas dataframe.")
    if trading_data.content:
        print(trading_data.content)
        trading_data = pd.read_csv(StringIO(trading_data.content))
        print(trading_data.head())
    else:
        print("No trading data found")
        exit()
    
    # Example analyses
    exit()
    print("=== COMPREHENSIVE TRADING ANALYSIS ===")
    comprehensive_analysis = analysis_system.analyze_trading_strategy("comprehensive", data=trading_data)
    print(comprehensive_analysis)
    
    print("\n=== PROFITABILITY ANALYSIS ===")
    profitability_analysis = analysis_system.analyze_trading_strategy("profitability", data=trading_data)
    print(profitability_analysis)
    
    print("\n=== MOMENTUM ANALYSIS ===")
    momentum_analysis = analysis_system.analyze_trading_strategy("momentum", data=trading_data)
    print(momentum_analysis)
    
    print("\n=== ANALYSIS METHODOLOGY ===")
    methodology = analysis_system.explain_analysis_methodology()
    print(methodology)