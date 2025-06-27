"""
Agentic Trading Strategy Research & Discovery System

This system uses multiple AI agents to:
1. Research new trading strategies and analysis techniques
2. Generate new ways to bucket and analyze trading data
3. Continuously expand the knowledge base with new findings
4. Test and validate discovered strategies against trading data

Architecture:
- Research Team: Discovers new trading strategies and analysis methods
- Strategy Team: Converts research into testable SQL queries
- Analysis Team: Executes tests and validates findings
- Knowledge Team: Updates and manages the growing knowledge base

Note: This should be split into multiple files for production:
- data/knowledge/: All knowledge base documents
- agents/: Individual agent definitions
- teams/: Team configurations
- workflows/: Workflow orchestration
- config/: Database and system configuration
"""

import os
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Iterator
from textwrap import dedent

import pandas as pd
from pydantic import BaseModel, Field

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.models.anthropic import Claude
from agno.team import Team
from agno.workflow import Workflow, RunResponse, RunEvent
from agno.knowledge.document import DocumentKnowledgeBase
from agno.vectordb.lancedb import LanceDb, SearchType
from agno.embedder.openai import OpenAIEmbedder
from agno.tools.knowledge import KnowledgeTools
from agno.tools.reasoning import ReasoningTools
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.duckdb import DuckDbTools
from agno.document.base import Document

# ===== DATA MODELS =====
# These should be in data/models.py

class TradingStrategyResearch(BaseModel):
    """Research findings about trading strategies"""
    strategy_name: str = Field(..., description="Name of the trading strategy")
    strategy_type: str = Field(..., description="Category (momentum, mean_reversion, etc.)")
    description: str = Field(..., description="Detailed description of the strategy")
    key_indicators: List[str] = Field(..., description="Key indicators or signals used")
    typical_timeframes: List[str] = Field(..., description="Common timeframes for this strategy")
    market_conditions: str = Field(..., description="Best market conditions for this strategy")
    risk_characteristics: str = Field(..., description="Risk profile and characteristics")
    sources: List[str] = Field(..., description="Sources of information")

class AnalysisMethod(BaseModel):
    """New analysis method discovered"""
    method_name: str = Field(..., description="Name of the analysis method")
    purpose: str = Field(..., description="What this method reveals")
    sql_pattern: str = Field(..., description="SQL query pattern for this analysis")
    bucketing_criteria: str = Field(..., description="How to group/bucket the data")
    interpretation_guide: str = Field(..., description="How to interpret results")
    validation_criteria: str = Field(..., description="How to validate findings")

class StrategyTestResults(BaseModel):
    """Results from testing a strategy against data"""
    strategy_name: str
    test_description: str
    sql_query: str
    results_summary: str
    statistical_significance: str
    actionable_insights: List[str]
    recommended_actions: List[str]

# ===== KNOWLEDGE BASE DOCUMENTS =====
# These should be in data/knowledge/ directory

def create_base_knowledge_documents() -> List[Document]:
    """Create foundational knowledge base documents"""
    
    strategy_research_doc = Document(
        content="""
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
        """
    )
    
    analysis_methods_doc = Document(
        content="""
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
        """
    )
    
    sql_patterns_doc = Document(
        content="""
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
        """
    )
    
    return [strategy_research_doc, analysis_methods_doc, sql_patterns_doc]

# ===== INDIVIDUAL AGENTS =====
# These should be in agents/ directory

def create_strategy_research_agent() -> Agent:
    """Agent that researches new trading strategies and methods"""
    return Agent(
        name="Strategy Research Agent",
        role="Research new trading strategies and analysis methods",
        model=OpenAIChat(id="gpt-4o"),
        tools=[DuckDuckGoTools()],
        instructions=[
            "You are an expert trading strategy researcher specializing in discovering new approaches.",
            "Research academic papers, industry reports, and trading methodologies.",
            "Focus on finding novel ways to analyze trading data and identify profitable patterns.",
            "Look for both well-established and cutting-edge trading techniques.",
            "Always provide credible sources for your research findings.",
            "Structure your findings in a clear, actionable format.",
        ],
        response_model=TradingStrategyResearch,
        add_datetime_to_instructions=True,
        markdown=True,
    )

def create_analysis_method_agent() -> Agent:
    """Agent that converts research into concrete analysis methods"""
    return Agent(
        name="Analysis Method Agent", 
        role="Convert strategy research into testable analysis methods",
        model=OpenAIChat(id="gpt-4o"),
        tools=[ReasoningTools(add_instructions=True)],
        instructions=[
            "You convert trading strategy research into concrete, testable analysis methods.",
            "Focus on creating SQL query patterns that can reveal strategy patterns in data.",
            "Design bucketing and grouping criteria that expose meaningful patterns.",
            "Provide clear interpretation guidelines for analysis results.",
            "Ensure methods are statistically sound and practically applicable.",
            "Create validation criteria to test the significance of findings.",
        ],
        response_model=AnalysisMethod,
        add_datetime_to_instructions=True,
        markdown=True,
    )

def create_knowledge_updater_agent(knowledge_base: DocumentKnowledgeBase) -> Agent:
    """Agent that updates and expands the knowledge base"""
    knowledge_tools = KnowledgeTools(
        knowledge=knowledge_base,
        think=True,
        search=True,
        analyze=True,
        add_few_shot=True,
    )
    
    return Agent(
        name="Knowledge Updater Agent",
        role="Update and expand the trading analysis knowledge base",
        model=OpenAIChat(id="gpt-4o"),
        tools=[knowledge_tools, ReasoningTools()],
        instructions=[
            "You manage and expand the trading strategy knowledge base.",
            "Search existing knowledge to avoid duplication.",
            "Integrate new findings with existing knowledge in a coherent way.",
            "Organize information logically and maintain knowledge quality.",
            "Create connections between related concepts and methods.",
            "Ensure knowledge base remains comprehensive and up-to-date.",
        ],
        knowledge=knowledge_base,
        search_knowledge=True,
        add_datetime_to_instructions=True,
        markdown=True,
    )

def create_data_analyst_agent() -> Agent:
    """Agent that executes SQL analysis and validates findings"""
    return Agent(
        name="Data Analysis Agent",
        role="Execute trading data analysis and validate findings",
        model=OpenAIChat(id="gpt-4o"),
        tools=[DuckDbTools(), ReasoningTools()],
        instructions=[
            "You execute comprehensive SQL analysis on trading data.",
            "Test new analysis methods and validate their effectiveness.",
            "Focus on statistical significance and practical relevance.",
            "Interpret results in the context of trading strategy insights.",
            "Identify actionable patterns and profitable opportunities.",
            "Provide clear, evidence-based recommendations.",
        ],
        response_model=StrategyTestResults,
        add_datetime_to_instructions=True,
        markdown=True,
    )

# ===== TEAMS =====
# These should be in teams/ directory

def create_research_team() -> Team:
    """Team that researches and discovers new trading strategies"""
    research_agent = create_strategy_research_agent()
    method_agent = create_analysis_method_agent()
    
    return Team(
        name="Strategy Research Team",
        mode="coordinate",
        model=Claude(id="claude-3-7-sonnet-latest"),
        members=[research_agent, method_agent],
        tools=[ReasoningTools(add_instructions=True)],
        instructions=[
            "You coordinate research into new trading strategies and analysis methods.",
            "First, have the research agent investigate specific strategy areas or questions.",
            "Then, have the method agent convert findings into testable analysis methods.",
            "Focus on practical, implementable strategies that can be tested with SQL.",
            "Ensure all methods have clear validation criteria and interpretation guides.",
            "Prioritize novel approaches that aren't already in the knowledge base.",
        ],
        markdown=True,
        show_members_responses=True,
        enable_agentic_context=True,
        add_datetime_to_instructions=True,
    )

def create_analysis_team(knowledge_base: DocumentKnowledgeBase) -> Team:
    """Team that tests strategies and updates knowledge"""
    analyst_agent = create_data_analyst_agent()
    knowledge_agent = create_knowledge_updater_agent(knowledge_base)
    
    return Team(
        name="Analysis & Knowledge Team",
        mode="coordinate", 
        model=Claude(id="claude-3-7-sonnet-latest"),
        members=[analyst_agent, knowledge_agent],
        tools=[ReasoningTools(add_instructions=True)],
        instructions=[
            "You test new analysis methods and update the knowledge base.",
            "First, have the analyst execute the proposed analysis methods on trading data.",
            "Then, have the knowledge updater integrate validated findings into the knowledge base.",
            "Only add methods that show statistical significance and practical value.",
            "Ensure new knowledge is well-integrated with existing information.",
            "Focus on expanding the range and sophistication of available analysis methods.",
        ],
        markdown=True,
        show_members_responses=True,
        enable_agentic_context=True,
        add_datetime_to_instructions=True,
    )

# ===== MAIN WORKFLOW =====
# This should be in workflows/ directory

class TradingStrategyDiscoveryWorkflow(Workflow):
    """
    Agentic workflow for discovering and testing new trading strategies.
    
    This workflow:
    1. Researches new trading strategies and analysis methods
    2. Converts research into testable SQL analysis methods
    3. Tests methods against actual trading data
    4. Updates knowledge base with validated findings
    5. Continuously expands analytical capabilities
    """
    
    description: str = dedent("""\
        An intelligent system for discovering, testing, and integrating new trading
        strategy analysis methods. This workflow uses multiple AI agents to continuously
        expand the knowledge base of trading analysis techniques, ensuring the system
        becomes more sophisticated over time.
        """)
    
    def __init__(self, postgres_agent, knowledge_base: DocumentKnowledgeBase):
        super().__init__()
        self.postgres_agent = postgres_agent
        self.knowledge_base = knowledge_base
        self.research_team = create_research_team()
        self.analysis_team = create_analysis_team(knowledge_base)
        self.data_dir = Path("./trading_data")
        self.data_dir.mkdir(exist_ok=True)
    
    def run(self, 
            research_focus: str,
            trading_data_csv: str = None,
            use_existing_data: bool = False) -> Iterator[RunResponse]:
        """
        Execute the strategy discovery workflow.
        
        Args:
            research_focus: What to research (e.g., "momentum strategies", "risk management")
            trading_data_csv: Path to existing CSV, or None to fetch from database
            use_existing_data: Whether to use existing CSV or fetch fresh data
        """
        
        yield RunResponse(
            content=f"🔍 Starting strategy discovery research on: {research_focus}",
            event=RunEvent.workflow_started
        )
        
        # Step 1: Research new strategies and methods
        yield RunResponse(
            content="📚 Researching new trading strategies and analysis methods...",
            event=RunEvent.step_started
        )
        
        research_response = self.research_team.run(
            f"Research {research_focus} trading strategies. Focus on finding new ways to analyze "
            f"and bucket trading data that could reveal profitable patterns. Look for both "
            f"academic research and practical industry methods."
        )
        
        yield RunResponse(
            content=f"Research findings: {research_response.content}",
            event=RunEvent.step_completed
        )
        
        # Step 2: Get or prepare trading data
        if not use_existing_data or not trading_data_csv:
            yield RunResponse(
                content="📊 Fetching fresh trading data for analysis...",
                event=RunEvent.step_started
            )
            
            trading_data_csv = self._get_trading_data_for_analysis()
            
            yield RunResponse(
                content=f"Data prepared: {trading_data_csv}",
                event=RunEvent.step_completed
            )
        
        # Step 3: Test methods and update knowledge base
        yield RunResponse(
            content="🧪 Testing new analysis methods and updating knowledge base...",
            event=RunEvent.step_started
        )
        
        analysis_response = self.analysis_team.run(
            f"Test the analysis methods from the research findings on the trading data "
            f"in {trading_data_csv}. Validate the effectiveness of these methods and "
            f"integrate any significant findings into the knowledge base. Focus on methods "
            f"that reveal new insights about {research_focus}."
        )
        
        yield RunResponse(
            content=f"Analysis results: {analysis_response.content}",
            event=RunEvent.step_completed
        )
        
        # Step 4: Generate summary and recommendations
        summary = self._generate_discovery_summary(
            research_focus, research_response.content, analysis_response.content
        )
        
        yield RunResponse(
            content=summary,
            event=RunEvent.workflow_completed
        )
    
    def _get_trading_data_for_analysis(self) -> str:
        """Fetch comprehensive trading data for analysis"""
        sql_query = """
        SELECT 
            trade_id, symbol, side, quantity,
            entry_price, exit_price, entry_time, exit_time,
            pnl, fees,
            EXTRACT(EPOCH FROM (exit_time - entry_time))/3600 as duration_hours,
            EXTRACT(DOW FROM entry_time) as entry_day_of_week,
            EXTRACT(HOUR FROM entry_time) as entry_hour,
            EXTRACT(MONTH FROM entry_time) as entry_month,
            CASE WHEN pnl > 0 THEN 'WIN' ELSE 'LOSS' END as outcome
        FROM trades 
        WHERE exit_time IS NOT NULL
        ORDER BY entry_time DESC
        LIMIT 5000;
        """
        
        try:
            conn = self.postgres_agent.tools[0].connection
            df = pd.read_sql_query(sql_query, conn)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            csv_filepath = self.data_dir / f"discovery_data_{timestamp}.csv"
            df.to_csv(csv_filepath, index=False)
            
            return str(csv_filepath)
        except Exception as e:
            raise Exception(f"Failed to fetch trading data: {e}")
    
    def _generate_discovery_summary(self, focus: str, research: str, analysis: str) -> str:
        """Generate summary of discovery session"""
        return f"""
        # Strategy Discovery Session Summary
        
        **Research Focus**: {focus}
        **Date**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        
        ## Research Phase
        {research}
        
        ## Analysis & Validation Phase  
        {analysis}
        
        ## Next Steps
        - Continue testing discovered methods on different time periods
        - Expand research into related strategy areas
        - Monitor performance of newly identified patterns
        - Consider implementing top-performing strategies
        
        **Knowledge Base Updated**: New analysis methods and findings have been integrated
        """

# ===== MAIN SYSTEM CLASS =====

class AgenticTradingResearchSystem:
    """
    Main system that orchestrates agentic trading strategy research and discovery.
    
    This system continuously learns and expands its analytical capabilities by:
    - Researching new trading strategies
    - Converting research into testable methods
    - Validating methods against real data
    - Expanding the knowledge base automatically
    """
    
    def __init__(self, postgres_agent):
        self.postgres_agent = postgres_agent
        self.knowledge_base = self._create_knowledge_base()
        self.workflow = TradingStrategyDiscoveryWorkflow(postgres_agent, self.knowledge_base)
        
    def _create_knowledge_base(self) -> DocumentKnowledgeBase:
        """Create and initialize the expandable knowledge base"""
        documents = create_base_knowledge_documents()
        
        knowledge_base = DocumentKnowledgeBase(
            documents=documents,
            vector_db=LanceDb(
                table_name="agentic_trading_knowledge",
                uri="./tmp/agentic_trading_lancedb",
                search_type=SearchType.hybrid,
                embedder=OpenAIEmbedder(id="text-embedding-3-small"),
            ),
        )
        
        return knowledge_base
    
    def initialize_system(self, recreate_knowledge: bool = False):
        """Initialize the system and load knowledge base"""
        print("🚀 Initializing Agentic Trading Research System...")
        self.knowledge_base.load(recreate=recreate_knowledge)
        print("✅ System initialized successfully")
    
    def discover_strategies(self, research_focus: str) -> str:
        """
        Discover new trading strategies and analysis methods.
        
        Args:
            research_focus: What to research (e.g., "momentum strategies", "risk management")
            
        Returns:
            Summary of discoveries and knowledge base updates
        """
        print(f"🔍 Starting strategy discovery: {research_focus}")
        
        results = []
        for response in self.workflow.run(research_focus):
            print(f"📝 {response.content}")
            results.append(response.content)
            
        return "\n".join(results)
    
    def research_specific_question(self, question: str) -> str:
        """
        Research a specific trading strategy question.
        
        Args:
            question: Specific question about trading strategies or analysis
            
        Returns:
            Research findings and analysis recommendations
        """
        research_team = create_research_team()
        response = research_team.run(
            f"Research this specific trading strategy question: {question}. "
            f"Provide concrete analysis methods that could help answer this question."
        )
        
        return response.content
    
    def expand_knowledge_base(self, new_findings: str) -> str:
        """
        Manually add new findings to the knowledge base.
        
        Args:
            new_findings: New trading strategy information to add
            
        Returns:
            Confirmation of knowledge base update
        """
        knowledge_agent = create_knowledge_updater_agent(self.knowledge_base)
        response = knowledge_agent.run(
            f"Integrate these new trading strategy findings into the knowledge base: {new_findings}"
        )
        
        return response.content
    
    def get_analysis_suggestions(self, data_description: str) -> str:
        """
        Get suggestions for new ways to analyze trading data.
        
        Args:
            data_description: Description of available trading data
            
        Returns:
            Suggestions for new analysis approaches
        """
        method_agent = create_analysis_method_agent()
        response = method_agent.run(
            f"Given this trading data: {data_description}, suggest new and innovative "
            f"ways to analyze it for strategy discovery. Focus on novel bucketing "
            f"methods and analysis approaches that might reveal hidden patterns."
        )
        
        return response.content

# ===== EXAMPLE USAGE AND CONFIGURATION =====

def main():
    """Example usage of the Agentic Trading Research System"""
    
    # Import your existing postgres agent
    from your_postgres_agent_file import get_postgres_agent  # Replace with actual import
    
    # Initialize the system
    postgres_agent = get_postgres_agent()
    research_system = AgenticTradingResearchSystem(postgres_agent)
    
    # Initialize knowledge base (set recreate=True on first run)
    research_system.initialize_system(recreate_knowledge=False)
    
    print("=" * 80)
    print("🧠 AGENTIC TRADING STRATEGY RESEARCH SYSTEM")
    print("=" * 80)
    
    # Example 1: Discover momentum strategies
    print("\n🚀 DISCOVERING MOMENTUM STRATEGIES")
    print("-" * 50)
    momentum_results = research_system.discover_strategies(
        "momentum trading strategies and high-frequency patterns"
    )
    print(momentum_results)
    
    # Example 2: Research specific question
    print("\n🤔 RESEARCHING SPECIFIC QUESTION")
    print("-" * 50)
    question_results = research_system.research_specific_question(
        "What are the most effective ways to identify and capitalize on post-earnings announcement drift?"
    )
    print(question_results)
    
    # Example 3: Get analysis suggestions
    print("\n💡 GETTING ANALYSIS SUGGESTIONS")
    print("-" * 50)
    suggestions = research_system.get_analysis_suggestions(
        "Trading data with entry/exit times, symbols, PnL, position sizes, and market conditions"
    )
    print(suggestions)
    
    # Example 4: Discover risk management strategies
    print("\n🛡️ DISCOVERING RISK MANAGEMENT STRATEGIES")
    print("-" * 50)
    risk_results = research_system.discover_strategies(
        "advanced risk management and position sizing strategies"
    )
    print(risk_results)

# ===== CONFIGURATION FILES =====
# These should be in separate config files

def create_config_files():
    """
    Create configuration files for production deployment.
    This function shows how to structure the system for maintainability.
    """
    
    config_dir = Path("./config")
    config_dir.mkdir(exist_ok=True)
    
    # Database configuration
    db_config = {
        "postgres": {
            "host": "localhost",
            "port": 5432,
            "database": "trading_db",
            "user": "trading_user",
            "password": "secure_password"
        },
        "vector_db": {
            "uri": "./tmp/agentic_trading_lancedb",
            "table_name": "agentic_trading_knowledge",
            "search_type": "hybrid"
        }
    }
    
    with open(config_dir / "database.json", "w") as f:
        json.dump(db_config, f, indent=2)
    
    # Agent configuration
    agent_config = {
        "models": {
            "research_model": "gpt-4o",
            "analysis_model": "gpt-4o", 
            "coordination_model": "claude-3-7-sonnet-latest"
        },
        "tools": {
            "web_search": "DuckDuckGoTools",
            "data_analysis": "DuckDbTools",
            "reasoning": "ReasoningTools",
            "knowledge": "KnowledgeTools"
        },
        "research_agents": {
            "strategy_researcher": {
                "role": "Research new trading strategies",
                "response_model": "TradingStrategyResearch"
            },
            "method_developer": {
                "role": "Convert research into testable methods",
                "response_model": "AnalysisMethod"
            }
        }
    }
    
    with open(config_dir / "agents.json", "w") as f:
        json.dump(agent_config, f, indent=2)
    
    print("📁 Configuration files created in ./config/")

def create_data_documents():
    """
    Create separate data document files for clean code organization.
    This shows how to move knowledge base content to external files.
    """
    
    data_dir = Path("./data/knowledge")
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # Strategy research document
    strategy_research_content = """
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
    """
    
    with open(data_dir / "strategy_research.md", "w") as f:
        f.write(strategy_research_content)
    
    # Analysis methods document
    analysis_methods_content = """
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
    """
    
    with open(data_dir / "analysis_methods.md", "w") as f:
        f.write(analysis_methods_content)
    
    # SQL patterns document
    sql_patterns_content = """
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
    """
    
    with open(data_dir / "sql_patterns.md", "w") as f:
        f.write(sql_patterns_content)
    
    print("📄 Knowledge documents created in ./data/knowledge/")

# ===== PRODUCTION DEPLOYMENT STRUCTURE =====

def create_production_structure():
    """
    Create the recommended file structure for production deployment.
    This shows how to organize the code for maintainability and expansion.
    """
    
    structure = {
        "agents/": [
            "strategy_researcher.py",
            "analysis_method_developer.py", 
            "knowledge_updater.py",
            "data_analyst.py",
            "__init__.py"
        ],
        "teams/": [
            "research_team.py",
            "analysis_team.py",
            "__init__.py"
        ],
        "workflows/": [
            "strategy_discovery.py",
            "knowledge_expansion.py",
            "__init__.py"
        ],
        "data/": {
            "knowledge/": [
                "strategy_research.md",
                "analysis_methods.md",
                "sql_patterns.md",
                "risk_management.md"
            ],
            "models/": [
                "strategy_models.py",
                "analysis_models.py"
            ]
        },
        "config/": [
            "database.json",
            "agents.json", 
            "teams.json",
            "workflows.json"
        ],
        "utils/": [
            "data_fetcher.py",
            "knowledge_manager.py",
            "sql_generator.py"
        ],
        "tests/": [
            "test_agents.py",
            "test_teams.py",
            "test_workflows.py"
        ]
    }
    
    def create_dirs(base_path: Path, structure: dict):
        for key, value in structure.items():
            if key.endswith("/"):
                # It's a directory
                dir_path = base_path / key.rstrip("/")
                dir_path.mkdir(parents=True, exist_ok=True)
                
                if isinstance(value, dict):
                    create_dirs(dir_path, value)
                elif isinstance(value, list):
                    for file in value:
                        if file.endswith("/"):
                            (dir_path / file.rstrip("/")).mkdir(exist_ok=True)
                        else:
                            (dir_path / file).touch()
    
    base_path = Path("./agentic_trading_system")
    create_dirs(base_path, structure)
    
    # Create main system file
    main_content = '''"""
Agentic Trading Strategy Research System

Main entry point for the system.
Import and configure all components here.
"""

from agents import create_all_agents
from teams import create_all_teams  
from workflows import TradingStrategyDiscoveryWorkflow
from utils.knowledge_manager import KnowledgeManager

class AgenticTradingSystem:
    """Main system orchestrator"""
    
    def __init__(self, postgres_agent):
        self.postgres_agent = postgres_agent
        self.knowledge_manager = KnowledgeManager()
        self.agents = create_all_agents()
        self.teams = create_all_teams()
        self.workflow = TradingStrategyDiscoveryWorkflow()
    
    def discover_strategies(self, focus: str):
        """Discover new trading strategies"""
        return self.workflow.run(focus)

if __name__ == "__main__":
    # Initialize and run system
    pass
'''
    
    with open(base_path / "main.py", "w") as f:
        f.write(main_content)
    
    print(f"🏗️ Production structure created in {base_path}/")
    print("📋 Recommended file organization:")
    print("   - agents/: Individual agent definitions")
    print("   - teams/: Team configurations and coordination")
    print("   - workflows/: Complex multi-step processes")
    print("   - data/knowledge/: Knowledge base documents")
    print("   - config/: System configuration files") 
    print("   - utils/: Helper functions and utilities")

if __name__ == "__main__":
    # Run the main example
    main()
    
    # Optionally create configuration and structure files
    # create_config_files()
    # create_data_documents()
    # create_production_structure()