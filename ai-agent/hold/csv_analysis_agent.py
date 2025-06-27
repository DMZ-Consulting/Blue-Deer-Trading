import pandas as pd
import numpy as np
from pathlib import Path
import os
from datetime import datetime
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.knowledge.document import DocumentKnowledgeBase
from agno.vectordb.lancedb import LanceDb
from agno.vectordb.search import SearchType
from agno.embedder.openai import OpenAIEmbedder
from agno.tools.knowledge import KnowledgeTools
from agno.tools.reasoning import ReasoningTools
from agno.tools.pandas import PandasTools  # Key tool for data analysis
from agno.tools.csv_toolkit import CsvTools  # Alternative CSV analysis tool
from agno.document.base import Document
from dotenv import load_dotenv
from agno.models.google import Gemini

load_dotenv()


#default_model = OpenAIChat(id="gpt-4o")
default_model = Gemini(id="gemini-2.5-flash-preview-05-20")


class TradingDataAnalysisAgent:
    """
    Advanced Trading Data Analysis Agent using Agno's PandasTools for complete dataset analysis.
    This approach gives the AI full access to analyze the entire dataset with pandas capabilities.
    """
    
    def __init__(self, knowledge_base=None):
        self.knowledge_base = knowledge_base or self._create_knowledge_base()
        self.analysis_agent = self._create_analysis_agent()
        self.data_dir = Path("./trading_data")
        self.data_dir.mkdir(exist_ok=True)
    
    def _create_knowledge_base(self):
        """Create comprehensive trading strategy knowledge base."""
        trading_analysis_doc = Document(
            content="""
            # Complete Trading Dataset Analysis Framework
            
            ## Data Analysis Methodology
            
            ### Full Dataset Statistical Analysis
            When analyzing complete trading datasets, perform:
            - **Temporal Analysis**: Time-based patterns, seasonality, trends
            - **Performance Analysis**: PnL distribution, win/loss patterns, risk metrics
            - **Strategy Detection**: Entry/exit pattern identification
            - **Risk Assessment**: Drawdown analysis, volatility patterns
            - **Correlation Analysis**: Relationship between variables
            - **Momentum Analysis**: Speed of price movements and holding periods
            
            ### Key Trading Metrics to Calculate
            
            #### Performance Metrics
            - **Total Return**: Sum of all PnL
            - **Win Rate**: Percentage of profitable trades
            - **Average Win/Loss**: Mean profit vs mean loss
            - **Profit Factor**: Gross profit / Gross loss
            - **Sharpe Ratio**: Risk-adjusted returns
            - **Maximum Drawdown**: Largest peak-to-trough decline
            - **Calmar Ratio**: Annual return / Max drawdown
            
            #### Strategy Identification Metrics
            - **Average Hold Time**: Typical position duration
            - **Position Size Consistency**: Standard deviation of position sizes
            - **Entry Time Patterns**: Clustering of entry times
            - **Symbol Preferences**: Most traded assets
            - **Market Condition Performance**: Bull vs bear market results
            
            #### Risk Management Analysis
            - **Stop Loss Usage**: Percentage of trades with stops
            - **Risk Per Trade**: Position size relative to account
            - **Consecutive Loss Streaks**: Maximum losing streak
            - **Tail Risk**: 95th percentile losses
            
            ### Pattern Detection Techniques
            
            #### Time-Based Patterns
            - **Intraday Patterns**: Performance by hour of day
            - **Weekly Patterns**: Performance by day of week
            - **Monthly Patterns**: Seasonal performance variations
            - **Market Session Analysis**: Performance by trading session
            
            #### Strategy Pattern Recognition
            - **Entry Signal Clustering**: Common entry conditions
            - **Exit Signal Analysis**: Systematic exit patterns
            - **Position Sizing Rules**: Consistent sizing methodology
            - **Symbol Selection Criteria**: Asset preference patterns
            
            #### Momentum Trading Indicators
            - **Quick Wins**: Trades profitable within hours
            - **Trend Following**: Extended hold periods in one direction
            - **Breakout Trading**: Entries near price extremes
            - **Mean Reversion**: Entries against recent price moves
            
            ### Profitability Analysis Framework
            
            #### "Where Most Money is Made" Analysis
            - **Time-Based Profitability**: Best performing times/periods
            - **Asset-Based Profitability**: Most profitable symbols/sectors
            - **Setup-Based Profitability**: Most profitable trade setups
            - **Market Condition Profitability**: Best performing market states
            - **Duration-Based Profitability**: Optimal holding periods
            
            #### Optimization Opportunities
            - **Entry Timing Optimization**: Refining entry conditions
            - **Exit Timing Optimization**: Improving exit rules
            - **Position Sizing Optimization**: Risk-adjusted position sizing
            - **Asset Selection Optimization**: Focusing on best performers
            
            ### Consistency vs Randomness Assessment
            
            #### Signs of Systematic Trading
            - Consistent patterns across multiple metrics
            - Repeatable entry/exit conditions
            - Stable performance across time periods
            - Clear risk management rules
            - Statistical significance in results
            
            #### Signs of Random Trading
            - No discernible patterns in entry/exit timing
            - Highly variable position sizing
            - Performance clustering around 50% win rate
            - No correlation between similar setups
            - High variance in results
            
            ### Data Analysis Best Practices
            
            #### Statistical Significance
            - Minimum sample sizes for reliable conclusions
            - Confidence intervals for key metrics
            - Hypothesis testing for pattern validation
            - Correlation vs causation awareness
            
            #### Visualization Techniques
            - Equity curve analysis
            - Drawdown charts
            - Performance distribution histograms
            - Heat maps for time-based performance
            - Scatter plots for relationship analysis
            """
        )
        
        knowledge_base = DocumentKnowledgeBase(
            documents=[trading_analysis_doc],
            vector_db=LanceDb(
                table_name="trading_data_analysis_knowledge",
                uri="./tmp/trading_analysis_lancedb",
                search_type=SearchType.hybrid,
                embedder=OpenAIEmbedder(id="text-embedding-3-small"),
            ),
        )
        
        return knowledge_base
    
    def _create_analysis_agent(self):
        """Create analysis agent with PandasTools for complete data analysis."""
        
        # Create knowledge tools
        knowledge_tools = KnowledgeTools(
            knowledge=self.knowledge_base,
            think=True,
            search=True,
            analyze=True,
            add_few_shot=True,
        )
        
        # Create reasoning tools
        reasoning_tools = ReasoningTools(add_instructions=True)
        
        # Create pandas tools for data analysis
        pandas_tools = PandasTools()
        
        agent = Agent(
            name="Trading Data Analysis Expert",
            model=default_model,
            tools=[knowledge_tools, reasoning_tools, pandas_tools],
            instructions=[
                "You are an expert trading data analyst with access to complete datasets.",
                "Use PandasTools to load and analyze entire CSV files of trading data.",
                "Perform comprehensive statistical analysis on all data points.",
                "Search your knowledge base for trading analysis frameworks and methodologies.",
                "Focus on identifying trading strategies, patterns, and performance drivers.",
                "Provide detailed insights with statistical evidence and visualizations.",
                "Look for both obvious and subtle patterns in the data.",
                "Always analyze the complete dataset, not just samples or summaries.",
                "Explain HOW you identified patterns and WHY they indicate specific strategies.",
                "Provide actionable recommendations for strategy improvement.",
                "Use pandas for calculations, groupby operations, and statistical analysis.",
                "Create visualizations when they help illustrate patterns.",
                "Be thorough but focus on the most important insights.",
            ],
            knowledge=self.knowledge_base,
            search_knowledge=True,
            show_tool_calls=True,
            markdown=True,
            add_datetime_to_instructions=True,
        )
        
        return agent
    
    def load_knowledge_base(self, recreate=False):
        """Load the trading analysis knowledge base."""
        self.knowledge_base.load(recreate=recreate)
    
    def save_trading_data_to_csv(self, df: pd.DataFrame, filename: str = None) -> str:
        """Save trading DataFrame to CSV file for analysis."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"trading_data_{timestamp}.csv"
        
        filepath = self.data_dir / filename
        df.to_csv(filepath, index=False)
        
        print(f"Saved {len(df)} rows to {filepath}")
        return str(filepath)
    
    def analyze_complete_trading_dataset(self, csv_filepath: str, analysis_focus: str = "comprehensive") -> str:
        """
        Analyze complete trading dataset using PandasTools.
        
        Args:
            csv_filepath: Path to the CSV file containing trading data
            analysis_focus: Type of analysis to perform
        """
        
        analysis_prompt = f"""
        I need you to perform a comprehensive analysis of the complete trading dataset in this CSV file: {csv_filepath}
        
        Analysis Focus: {analysis_focus}
        
        **IMPORTANT**: Use PandasTools to load and analyze the ENTIRE dataset. Do not work with summaries.
        
        Please perform the following analysis:
        
        1. **Data Loading and Overview**
           - Load the complete CSV file using pandas
           - Display basic dataset information (shape, columns, data types)
           - Show first few rows to understand the data structure
        
        2. **Performance Analysis**
           - Calculate key performance metrics (total PnL, win rate, average win/loss, etc.)
           - Analyze the distribution of PnL
           - Calculate Sharpe ratio and maximum drawdown
           - Create equity curve analysis
        
        3. **Strategy Pattern Identification**
           - Analyze entry and exit timing patterns
           - Look for position sizing patterns
           - Identify most profitable setups and conditions
           - Examine holding period distributions
        
        4. **Temporal Analysis**
           - Performance by day of week
           - Performance by hour of day (if intraday data)
           - Monthly/seasonal patterns
           - Trend analysis over time
        
        5. **Asset and Market Analysis**
           - Performance by symbol/asset
           - Volume patterns and market conditions
           - Sector or asset class analysis if applicable
        
        6. **Risk Management Assessment**
           - Stop loss usage and effectiveness
           - Position sizing consistency
           - Drawdown analysis and recovery patterns
           - Risk-adjusted performance metrics
        
        7. **Profitability Drivers ("Where Most Money is Made")**
           - Identify the specific conditions, times, assets, and setups that generate the highest profits
           - Analyze what differentiates winning trades from losing trades
           - Find optimization opportunities
        
        8. **Strategy Consistency vs Randomness**
           - Statistical tests for pattern significance
           - Correlation analysis between different factors
           - Assessment of systematic vs random behavior
        
        9. **Momentum Analysis**
           - Identify momentum trading patterns
           - Analyze quick wins vs longer holds
           - Speed of entry/exit decisions
        
        10. **Actionable Recommendations**
            - Specific improvements based on data analysis
            - Strategy refinements and optimizations
            - Risk management enhancements
        
        **Use your knowledge base to guide the analysis and explain the methodology.**
        **Provide statistical evidence for all conclusions.**
        **Create visualizations where helpful.**
        **Focus on actionable insights that can improve trading performance.**
        """
        
        response = self.analysis_agent.run(analysis_prompt)
        return response.content if hasattr(response, 'content') else str(response)

# Alternative implementation using CsvTools
class TradingDataAnalysisWithCsvTools:
    """
    Alternative implementation using Agno's CsvTools for CSV-specific analysis.
    """
    
    def __init__(self, csv_files: list = None):
        self.csv_files = csv_files or []
        self.knowledge_base = self._create_knowledge_base()
        self.analysis_agent = self._create_analysis_agent()
    
    def _create_knowledge_base(self):
        """Create knowledge base for CSV analysis."""
        # Same knowledge base as above
        trading_analysis_doc = Document(
            content="""
            # CSV Trading Data Analysis with CsvTools
            
            ## CsvTools Analysis Approach
            
            ### SQL-like Querying of CSV Data
            CsvTools allows SQL-like operations on CSV files:
            - SELECT statements for data filtering
            - GROUP BY for aggregations
            - WHERE clauses for condition filtering
            - ORDER BY for sorting
            - Mathematical functions for calculations
            
            ### Trading Data Analysis Queries
            
            #### Performance Queries
            ```sql
            -- Total PnL
            SELECT SUM(pnl) as total_pnl FROM trading_data;
            
            -- Win rate
            SELECT 
                COUNT(CASE WHEN pnl > 0 THEN 1 END) * 100.0 / COUNT(*) as win_rate 
            FROM trading_data;
            
            -- Average win vs loss
            SELECT 
                AVG(CASE WHEN pnl > 0 THEN pnl END) as avg_win,
                AVG(CASE WHEN pnl < 0 THEN pnl END) as avg_loss
            FROM trading_data;
            ```
            
            #### Pattern Analysis Queries
            ```sql
            -- Performance by day of week
            SELECT 
                EXTRACT(DOW FROM entry_time) as day_of_week,
                COUNT(*) as trade_count,
                AVG(pnl) as avg_pnl,
                SUM(pnl) as total_pnl
            FROM trading_data
            GROUP BY EXTRACT(DOW FROM entry_time)
            ORDER BY avg_pnl DESC;
            
            -- Performance by symbol
            SELECT 
                symbol,
                COUNT(*) as trade_count,
                AVG(pnl) as avg_pnl,
                SUM(pnl) as total_pnl,
                AVG(duration_hours) as avg_duration
            FROM trading_data
            GROUP BY symbol
            ORDER BY total_pnl DESC;
            ```
            """
        )
        
        knowledge_base = DocumentKnowledgeBase(
            documents=[trading_analysis_doc],
            vector_db=LanceDb(
                table_name="csv_tools_analysis_knowledge",
                uri="./tmp/csv_tools_lancedb",
                search_type=SearchType.hybrid,
                embedder=OpenAIEmbedder(id="text-embedding-3-small"),
            ),
        )
        
        return knowledge_base
    
    def _create_analysis_agent(self):
        """Create analysis agent with CsvTools."""
        
        # Convert file paths to Path objects
        csv_paths = [Path(f) for f in self.csv_files]
        
        # Create CSV tools
        csv_tools = CsvTools(csvs=csv_paths)
        
        # Create knowledge tools
        knowledge_tools = KnowledgeTools(
            knowledge=self.knowledge_base,
            think=True,
            search=True,
            analyze=True,
        )
        
        agent = Agent(
            name="CSV Trading Data Analyst",
            model=OpenAIChat(id="gpt-4o"),
            tools=[csv_tools, knowledge_tools],
            instructions=[
                "You are a trading data analyst using CSV analysis tools.",
                "First, always get the list of available CSV files.",
                "Then check the columns in the trading data file.",
                "Use SQL-like queries to analyze the complete dataset.",
                "Search your knowledge base for analysis frameworks.",
                "Focus on comprehensive statistical analysis of all trading data.",
                "Look for patterns, trends, and profitability drivers.",
                "Use appropriate SQL functions for calculations and aggregations.",
                "Always wrap column names with double quotes if they contain spaces.",
                "Use single quotes for string values in queries.",
                "Provide detailed insights with statistical evidence.",
            ],
            knowledge=self.knowledge_base,
            search_knowledge=True,
            show_tool_calls=True,
            markdown=True,
        )
        
        return agent
    
    def add_csv_file(self, csv_filepath: str):
        """Add a CSV file for analysis."""
        self.csv_files.append(csv_filepath)
        # Recreate agent with updated CSV files
        self.analysis_agent = self._create_analysis_agent()
    
    def analyze_with_csv_tools(self, analysis_request: str) -> str:
        """Analyze trading data using CsvTools."""
        
        analysis_prompt = f"""
        I need you to analyze the trading data in the available CSV files.
        
        Analysis Request: {analysis_request}
        
        Please:
        1. First, get the list of available CSV files
        2. Check the columns and structure of the trading data
        3. Use SQL-like queries to perform comprehensive analysis
        4. Search your knowledge base for appropriate analysis methods
        5. Focus on the complete dataset, not just samples
        6. Provide statistical insights and pattern identification
        7. Look for trading strategy indicators and profitability drivers
        
        Use the CSV tools to run appropriate queries for this analysis.
        """
        
        response = self.analysis_agent.run(analysis_prompt)
        return response.content if hasattr(response, 'content') else str(response)

# Complete integration system
class CompleteTradingAnalysisSystem:
    """
    Complete trading analysis system that integrates SQL data retrieval with full dataset analysis.
    """
    
    def __init__(self, postgres_agent):
        self.postgres_agent = postgres_agent
        self.pandas_analyzer = TradingDataAnalysisAgent()
        
    def analyze_trading_strategy_complete(self, analysis_request: str, 
                                        approach: str = "pandas",
                                        save_data: bool = True) -> str:
        """
        Complete trading strategy analysis workflow.
        
        Args:
            analysis_request: Natural language description of analysis needed
            approach: "pandas" or "csv_tools" 
            save_data: Whether to save CSV file for future reference
        """
        
        # Step 1: Generate and execute SQL to get data
        print("🔍 Generating SQL query for data retrieval...")
        sql_query = self._get_sql_query(analysis_request)
        
        print("📊 Executing SQL query...")
        df = self._execute_sql_query(sql_query)
        
        if df.empty:
            return "❌ No data retrieved for analysis. Please check your database connection and query."
        
        print(f"✅ Retrieved {len(df)} rows of trading data")
        
        # Step 2: Save data to CSV
        csv_filepath = self.pandas_analyzer.save_trading_data_to_csv(df)
        
        # Step 3: Load knowledge base
        print("📚 Loading trading analysis knowledge base...")
        self.pandas_analyzer.load_knowledge_base(recreate=False)
        
        # Step 4: Perform complete dataset analysis
        print("🧠 Starting comprehensive AI analysis of complete dataset...")
        
        if approach == "pandas":
            analysis_result = self.pandas_analyzer.analyze_complete_trading_dataset(
                csv_filepath, analysis_request
            )
        elif approach == "csv_tools":
            csv_analyzer = TradingDataAnalysisWithCsvTools([csv_filepath])
            csv_analyzer.knowledge_base.load(recreate=False)
            analysis_result = csv_analyzer.analyze_with_csv_tools(analysis_request)
        else:
            return "❌ Invalid approach. Use 'pandas' or 'csv_tools'"
        
        # Clean up temporary file if not saving
        if not save_data:
            try:
                Path(csv_filepath).unlink()
                print("🗑️ Temporary CSV file cleaned up")
            except:
                pass
        
        return analysis_result
    
    def _get_sql_query(self, analysis_request: str) -> str:
        """Generate SQL query from analysis request."""
        sql_prompt = f"""
        Generate a SQL query for this trading analysis request: {analysis_request}
        
        Requirements:
        - Return ONLY the SQL query, no explanations
        - Include all relevant columns for comprehensive analysis
        - Use proper SQL syntax for our trading database schema
        - Order by entry_time for temporal analysis
        - Include calculated fields like duration, day of week, hour, etc.
        - Ensure the query returns complete data needed for analysis
        
        Example columns to include:
        - trade_id, symbol, side, quantity
        - entry_price, exit_price, entry_time, exit_time
        - pnl, fees
        - calculated: duration_hours, entry_day_of_week, entry_hour
        """
        
        response = self.postgres_agent.run(sql_prompt)
        return self._extract_sql(response)
    
    def _extract_sql(self, response) -> str:
        """Extract SQL from agent response."""
        if hasattr(response, 'content'):
            content = response.content
        else:
            content = str(response)
        
        import re
        
        # Try to find SQL in code blocks
        sql_match = re.search(r'```sql\n(.*?)\n```', content, re.DOTALL | re.IGNORECASE)
        if sql_match:
            return sql_match.group(1).strip()
        
        # Try to find any code block
        sql_match = re.search(r'```\n(.*?)\n```', content, re.DOTALL)
        if sql_match:
            return sql_match.group(1).strip()
        
        # Clean up the response
        content = re.sub(r'^.*?SELECT', 'SELECT', content, flags=re.IGNORECASE | re.DOTALL)
        content = content.split(';')[0] + ';'
        
        return content.strip()
    
    def _execute_sql_query(self, sql_query: str) -> pd.DataFrame:
        """Execute SQL query directly against database."""
        try:
            conn = self.postgres_agent.tools[0].connection
            return pd.read_sql_query(sql_query, conn)
        except Exception as e:
            print(f"❌ Error executing SQL query: {e}")
            print(f"Query was: {sql_query}")
            return pd.DataFrame()

# Usage example
def main():
    """Example usage of the complete trading analysis system."""
    
    # Import your existing postgres agent
    from custom_toolkits import get_postgres_agent  # Replace with actual import
    
    # Create the complete analysis system
    postgres_agent = get_postgres_agent()
    analysis_system = CompleteTradingAnalysisSystem(postgres_agent)
    
    # Example analyses
    print("=" * 60)
    print("🚀 COMPREHENSIVE TRADING STRATEGY ANALYSIS")
    print("=" * 60)
    
    # Comprehensive analysis
    result1 = analysis_system.analyze_trading_strategy_complete(
        "Analyze all my trading patterns, profitability drivers, and strategy consistency from the last 12 months",
        approach="pandas"
    )
    print(result1)
    
    print("\n" + "=" * 60)
    print("💰 PROFITABILITY ANALYSIS")
    print("=" * 60)
    
    # Profitability focus
    result2 = analysis_system.analyze_trading_strategy_complete(
        "Identify exactly where and when I make the most money - specific times, assets, setups, and market conditions",
        approach="pandas"
    )
    print(result2)
    
    print("\n" + "=" * 60)
    print("⚡ MOMENTUM TRADING ANALYSIS")
    print("=" * 60)
    
    # Momentum analysis
    result3 = analysis_system.analyze_trading_strategy_complete(
        "Analyze my momentum trading patterns - how I identify, enter, and exit momentum trades",
        approach="pandas"
    )
    print(result3)

if __name__ == "__main__":
    main()