#!/usr/bin/env python3
"""
Comprehensive Trade Analysis Workflow using Agno

This workflow provides a complete trade analysis pipeline that:
1. Takes a trade ID as input
2. Retrieves trade data from database
3. Fetches historical market data using PolygonOptionsTools
4. Applies strategy analysis methods
5. Generates a detailed analysis report
6. Saves results to document database for future reference
7. Is extensible for additional data sources and analysis methods
"""

import json
import os
from datetime import datetime
from typing import Dict, Iterator, List, Optional, Any
from textwrap import dedent

from agno.agent import Agent
from agno.document.base import Document
from agno.knowledge.document import DocumentKnowledgeBase
from agno.models.openai import OpenAIChat
from agno.run.response import RunEvent, RunResponse
from agno.storage.sqlite import SqliteStorage
from agno.tools.postgres import PostgresTools
from agno.tools.reasoning import ReasoningTools
from agno.vectordb.lancedb import LanceDb
from agno.vectordb.search import SearchType
from agno.workflow import Workflow
from agno.utils.log import logger
from agno.utils.pprint import pprint_run_response
from pydantic import BaseModel, Field
import psycopg2
from dotenv import load_dotenv

from toolkits.polygon_options import PolygonOptionsTools
from agents.postgres_agent import get_postgres_tools

load_dotenv()

# Pydantic Models for structured data
class TradeData(BaseModel):
    """Structured trade data from database"""
    trade_id: str = Field(..., description="Unique trade identifier")
    symbol: str = Field(..., description="Trading symbol (e.g., NVDA)")
    strike: float = Field(..., description="Strike price")
    expiration_date: datetime = Field(..., description="Option expiration date")
    option_type: str = Field(..., description="Option type (C for Call, P for Put)")
    created_at: datetime = Field(..., description="Trade entry time")
    closed_at: Optional[datetime] = Field(None, description="Trade exit time")
    entry_price: Optional[float] = Field(None, description="Entry price per contract")
    exit_price: Optional[float] = Field(None, description="Exit price per contract")
    current_size: Optional[str] = Field(None, description="Current position size")
    profit_loss: Optional[float] = Field(None, description="Realized P&L")
    options_ticker: Optional[str] = Field(None, description="Formatted options ticker")

class MarketDataAnalysis(BaseModel):
    """Market data analysis results"""
    options_ticker: str = Field(..., description="Options ticker analyzed")
    historical_data_points: int = Field(..., description="Number of data points retrieved")
    price_range: Dict[str, float] = Field(..., description="Price range during trade period")
    volume_analysis: Dict[str, Any] = Field(..., description="Volume analysis results")
    volatility_metrics: Dict[str, float] = Field(..., description="Volatility calculations")
    execution_quality: Dict[str, Any] = Field(..., description="Execution quality assessment")
    market_context: Dict[str, Any] = Field(..., description="Market conditions during trade")

class StrategyAnalysis(BaseModel):
    """Strategy analysis results"""
    strategy_type: str = Field(..., description="Identified trading strategy")
    performance_metrics: Dict[str, float] = Field(..., description="Performance calculations")
    risk_assessment: Dict[str, Any] = Field(..., description="Risk analysis results")
    timing_analysis: Dict[str, str] = Field(..., description="Entry/exit timing evaluation")
    optimization_suggestions: List[str] = Field(..., description="Improvement recommendations")

class TradeAnalysisReport(BaseModel):
    """Complete trade analysis report"""
    trade_data: TradeData = Field(..., description="Original trade information")
    market_analysis: MarketDataAnalysis = Field(..., description="Market data analysis")
    strategy_analysis: StrategyAnalysis = Field(..., description="Strategy analysis")
    executive_summary: str = Field(..., description="High-level analysis summary")
    detailed_findings: List[str] = Field(..., description="Detailed analysis points")
    recommendations: List[str] = Field(..., description="Actionable recommendations")
    analysis_timestamp: datetime = Field(default_factory=datetime.now, description="When analysis was performed")
    extensibility_metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata for future extensions")

class TradeAnalysisWorkflow(Workflow):
    """
    Comprehensive trade analysis workflow with extensible architecture
    
    This workflow orchestrates multiple specialized agents to provide:
    - Database trade retrieval
    - Historical market data analysis
    - Strategy evaluation
    - Risk assessment
    - Performance optimization recommendations
    """
    
    description: str = dedent("""\
        Advanced trade analysis workflow that combines database queries, 
        market data analysis, and strategic evaluation to generate 
        comprehensive trade performance reports with actionable insights.
    """)

    # Database Agent: Retrieves trade data from PostgreSQL
    database_agent: Agent = Agent(
        name="TradeDB Specialist",
        model=OpenAIChat(id="gpt-4o-mini"),
        tools=[get_postgres_tools()],  # Will be set in __init__
        description=dedent("""\
            You are a database specialist focused on retrieving and formatting trade data.
            Your expertise includes precise SQL queries, data validation, and options ticker formatting.
        """),
        instructions=[
            "Retrieve complete trade details for the specified trade ID",
            "Format options ticker as O:SYMBOL[YYMMDD][C/P][STRIKE_PADDED]",
            "Validate all retrieved data for completeness",
            "Handle missing or null values appropriately",
            "Ensure date formats are consistent and parseable"
        ],
        response_model=TradeData,
        structured_outputs=True,
    )

    # Market Data Agent: Analyzes historical market data using Polygon API
    market_data_agent: Agent = Agent(
        name="Market Data Analyst", 
        model=OpenAIChat(id="gpt-4o"),
        tools=[PolygonOptionsTools()],
        description=dedent("""\
            You are an expert market data analyst specializing in options trading data.
            You analyze historical price movements, volume patterns, volatility, and execution quality.
        """),
        instructions=[
            "Retrieve historical options aggregates for the trade period",
            "Analyze price movement patterns and trends",
            "Calculate volatility metrics and risk indicators",
            "Assess execution quality versus market conditions",
            "Evaluate liquidity and spread characteristics",
            "Provide context on market conditions during the trade",
            "Use ALL available PolygonOptionsTools methods for comprehensive analysis"
        ],
        response_model=MarketDataAnalysis,
        structured_outputs=True,
    )

    # Strategy Analyst: Evaluates trading strategy and performance
    strategy_analyst: Agent = Agent(
        name="Strategy Evaluation Specialist",
        model=OpenAIChat(id="gpt-4o"),
        tools=[ReasoningTools()],
        description=dedent("""\
            You are a trading strategy expert who evaluates trade performance,
            identifies strategy patterns, and provides optimization recommendations.
        """),
        instructions=[
            "Identify the trading strategy used (directional, volatility, income, etc.)",
            "Calculate comprehensive performance metrics (P&L, ROI, Sharpe ratio, etc.)",
            "Assess risk management effectiveness",
            "Evaluate entry and exit timing quality",
            "Compare performance against strategy benchmarks",
            "Provide specific optimization recommendations",
            "Consider market conditions impact on strategy effectiveness"
        ],
        response_model=StrategyAnalysis,
        structured_outputs=True,
    )

    # Report Generator: Synthesizes all analyses into comprehensive report
    report_generator: Agent = Agent(
        name="Trade Analysis Reporter",
        model=OpenAIChat(id="gpt-4o"),
        description=dedent("""\
            You are an expert financial analyst who synthesizes complex trading data
            into clear, actionable reports for traders and portfolio managers.
        """),
        instructions=[
            "Create executive summary highlighting key findings",
            "Synthesize technical analysis with strategic insights", 
            "Provide clear, actionable recommendations",
            "Explain complex concepts in accessible language",
            "Highlight both successful elements and improvement areas",
            "Structure findings for easy reference and follow-up",
            "Include forward-looking strategic guidance"
        ],
        response_model=TradeAnalysisReport,
        structured_outputs=True,
    )

    def __init__(self, **kwargs):
        """Initialize workflow with database connection and document storage"""
        super().__init__(**kwargs)
        
        # Setup database connection
        postgres_db_url = os.getenv("SUPABASE_DB_URL")
        if not postgres_db_url:
            raise ValueError("SUPABASE_DB_URL environment variable is required")
        
        conn = psycopg2.connect(postgres_db_url)
        postgres_tools = PostgresTools(connection=conn)
        self.database_agent.tools = [postgres_tools]
        
        # Setup document knowledge base for storing analysis results
        self.setup_document_storage()

    def setup_document_storage(self):
        """Setup document database for storing and retrieving analysis reports"""
        self.knowledge_base = DocumentKnowledgeBase(
            documents=[],  # Will be populated with analysis reports
            vector_db=LanceDb(
                table_name="trade_analysis_reports",
                uri="./tmp/trade_analysis_knowledge_lancedb",
                search_type=SearchType.hybrid  # Enable both keyword and semantic search
            ),
        )
        # Load existing documents
        self.knowledge_base.load(recreate=False)

    def format_options_ticker(self, trade_data: TradeData) -> str:
        """Format options ticker from trade data"""
        # Format expiration date as YYMMDD
        exp_formatted = trade_data.expiration_date.strftime("%y%m%d")
        
        # Format option type
        opt_type = trade_data.option_type.upper()
        
        # Format strike price (multiply by 1000, pad to 8 digits)
        strike_formatted = f"{int(trade_data.strike * 1000):08d}"
        
        # Combine into ticker format
        ticker = f"O:{trade_data.symbol.upper()}{exp_formatted}{opt_type}{strike_formatted}"
        
        return ticker

    def save_analysis_to_knowledge_base(self, report: TradeAnalysisReport):
        """Save analysis report to document knowledge base for future reference"""
        try:
            # Create document content
            doc_content = f"""
            Trade Analysis Report - {report.trade_data.trade_id}
            
            Symbol: {report.trade_data.symbol}
            Trade Date: {report.trade_data.created_at.strftime('%Y-%m-%d')}
            Strategy: {report.strategy_analysis.strategy_type}
            
            Executive Summary:
            {report.executive_summary}
            
            Key Findings:
            {chr(10).join(f'• {finding}' for finding in report.detailed_findings)}
            
            Recommendations:
            {chr(10).join(f'• {rec}' for rec in report.recommendations)}
            
            Performance Metrics:
            {json.dumps(report.strategy_analysis.performance_metrics, indent=2)}
            
            Market Analysis:
            Options Ticker: {report.market_analysis.options_ticker}
            Data Points: {report.market_analysis.historical_data_points}
            Price Range: {json.dumps(report.market_analysis.price_range, indent=2)}
            
            Full Report Data:
            {report.model_dump_json(indent=2)}
            """
            
            # Create document with metadata
            document = Document(
                content=doc_content,
                meta_data={
                    "trade_id": report.trade_data.trade_id,
                    "symbol": report.trade_data.symbol,
                    "strategy_type": report.strategy_analysis.strategy_type,
                    "analysis_date": report.analysis_timestamp.isoformat(),
                    "options_ticker": report.market_analysis.options_ticker,
                    "entry_date": report.trade_data.created_at.isoformat(),
                    "exit_date": report.trade_data.closed_at.isoformat() if report.trade_data.closed_at else None,
                    "document_type": "trade_analysis_report"
                }
            )
            
            # Add to knowledge base
            self.knowledge_base.documents = [document]
            self.knowledge_base.load(recreate=False)
            
            logger.info(f"✅ Saved analysis report for trade {report.trade_data.trade_id} to knowledge base")
            
        except Exception as e:
            logger.error(f"❌ Failed to save analysis to knowledge base: {e}")

    def get_similar_trades(self, trade_data: TradeData, limit: int = 5) -> List[Dict]:
        """Search for similar trades in the knowledge base"""
        try:
            query = f"symbol:{trade_data.symbol} strategy analysis"
            results = self.knowledge_base.search(query=query, num_documents=limit)
            
            similar_trades = []
            for result in results:
                if result.meta_data.get("trade_id") != trade_data.trade_id:
                    similar_trades.append(result.meta_data)
            
            return similar_trades
        except Exception as e:
            logger.warning(f"Could not retrieve similar trades: {e}")
            return []

    def run(self, trade_id: str, include_similar_trades: bool = True, 
            extend_with: Optional[Dict[str, Any]] = None) -> Iterator[RunResponse]:
        """
        Execute comprehensive trade analysis workflow
        
        Args:
            trade_id: Unique identifier for the trade to analyze
            include_similar_trades: Whether to include analysis of similar historical trades
            extend_with: Optional dictionary of additional data sources/analysis methods
        """
        logger.info(f"🚀 Starting comprehensive analysis for trade {trade_id}")
        
        try:
            # Step 1: Retrieve trade data from database
            yield RunResponse(
                run_id=self.run_id,
                content="📊 Retrieving trade data from database...",
                event=RunEvent.workflow_started.value
            )
            
            #trade_query = f"SELECT trade_id, symbol, strike, expiration_date, option_type, created_at, closed_at, entry_price, exit_price, current_size, profit_loss FROM trades WHERE trade_id = '{trade_id}'"
            #trade_query = f"SELECT * FROM trades WHERE trade_id = '{trade_id}'"
            
            trade_response: RunResponse = self.database_agent.run(
                f"Get this trade from the database: {trade_id}"
            )
            
            if not trade_response or not trade_response.content:
                yield RunResponse(
                    run_id=self.run_id,
                    content=f"❌ Failed to retrieve trade data for {trade_id} - No response from database",
                    event=RunEvent.workflow_completed.value
                )
                return
            
            # Handle different response types
            if isinstance(trade_response.content, TradeData):
                trade_data = trade_response.content
            else:
                # Try to parse the response if it's not already a TradeData object
                try:
                    # If it's a string response, we'll need to create TradeData manually
                    # For now, let's create a fallback
                    yield RunResponse(
                        run_id=self.run_id,
                        content=f"❌ Database returned unexpected format for {trade_id}. Response type: {type(trade_response.content)}",
                        event=RunEvent.workflow_completed.value
                    )
                    return
                except Exception as e:
                    yield RunResponse(
                        run_id=self.run_id,
                        content=f"❌ Failed to parse trade data for {trade_id}: {str(e)}",
                        event=RunEvent.workflow_completed.value
                    )
                    return
            trade_data.options_ticker = self.format_options_ticker(trade_data)
            
            yield RunResponse(
                run_id=self.run_id,
                content=f"✅ Retrieved trade data: {trade_data.symbol} {trade_data.options_ticker}",
                event=RunEvent.run_response.value
            )

            # Step 2: Analyze market data using PolygonOptionsTools
            yield RunResponse(
                run_id=self.run_id,
                content="📈 Analyzing historical market data...",
                event=RunEvent.run_response.value
            )
            
            market_analysis_prompt = f"""
            Analyze the market data for options ticker {trade_data.options_ticker}:
            - Entry time: {trade_data.created_at.isoformat()}
            - Exit time: {trade_data.closed_at.isoformat() if trade_data.closed_at else 'Open position'}
            - Entry price: ${trade_data.entry_price}
            - Exit price: ${trade_data.exit_price if trade_data.exit_price else 'N/A'}
            
            Use ALL available PolygonOptionsTools methods to get comprehensive market data and analysis.
            """
            
            market_response: RunResponse = self.market_data_agent.run(market_analysis_prompt)
            
            if not market_response.content:
                yield RunResponse(
                    run_id=self.run_id,
                    content="❌ Failed to retrieve market data",
                    event=RunEvent.workflow_completed.value
                )
                return

            market_analysis: MarketDataAnalysis = market_response.content
            
            yield RunResponse(
                run_id=self.run_id,
                content=f"✅ Market analysis complete: {market_analysis.historical_data_points} data points analyzed",
                event=RunEvent.run_response.value
            )

            # Step 3: Perform strategy analysis
            yield RunResponse(
                run_id=self.run_id,
                content="🎯 Analyzing trading strategy and performance...",
                event=RunEvent.run_response.value
            )
            
            # Get similar trades for comparison
            similar_trades = []
            if include_similar_trades:
                similar_trades = self.get_similar_trades(trade_data)
                
            strategy_prompt = f"""
            Analyze the trading strategy and performance for this trade:
            
            Trade Data: {trade_data.model_dump_json(indent=2)}
            Market Analysis: {market_analysis.model_dump_json(indent=2)}
            Similar Historical Trades: {json.dumps(similar_trades, indent=2)}
            
            Provide comprehensive strategy analysis including performance metrics, risk assessment, and optimization recommendations.
            """
            
            strategy_response: RunResponse = self.strategy_analyst.run(strategy_prompt)
            
            if not strategy_response.content:
                yield RunResponse(
                    run_id=self.run_id,
                    content="❌ Failed to complete strategy analysis",
                    event=RunEvent.workflow_completed.value
                )
                return

            strategy_analysis: StrategyAnalysis = strategy_response.content
            
            yield RunResponse(
                run_id=self.run_id,
                content=f"✅ Strategy analysis complete: {strategy_analysis.strategy_type}",
                event=RunEvent.run_response.value
            )

            # Step 4: Apply extensions if provided
            extension_results = {}
            if extend_with:
                yield RunResponse(
                    run_id=self.run_id,
                    content="🔧 Applying workflow extensions...",
                    event=RunEvent.run_response.value
                )
                
                for extension_name, extension_config in extend_with.items():
                    try:
                        # Future: Add extension handling logic here
                        # Extensions could include sentiment analysis, news correlation, etc.
                        extension_results[extension_name] = f"Extension {extension_name} processed"
                        logger.info(f"Applied extension: {extension_name}")
                    except Exception as e:
                        logger.warning(f"Extension {extension_name} failed: {e}")
                        extension_results[extension_name] = f"Failed: {e}"

            # Step 5: Generate comprehensive report
            yield RunResponse(
                run_id=self.run_id,
                content="📝 Generating comprehensive analysis report...",
                event=RunEvent.run_response.value
            )
            
            report_prompt = f"""
            Create a comprehensive trade analysis report synthesizing all data:
            
            Trade Data: {trade_data.model_dump_json(indent=2)}
            Market Analysis: {market_analysis.model_dump_json(indent=2)}
            Strategy Analysis: {strategy_analysis.model_dump_json(indent=2)}
            Extension Results: {json.dumps(extension_results, indent=2)}
            Similar Trades: {json.dumps(similar_trades, indent=2)}
            
            Generate a detailed report with executive summary, findings, and actionable recommendations.
            """
            
            report_response: RunResponse = self.report_generator.run(report_prompt)
            
            if not report_response.content:
                yield RunResponse(
                    run_id=self.run_id,
                    content="❌ Failed to generate analysis report",
                    event=RunEvent.workflow_completed.value
                )
                return

            final_report: TradeAnalysisReport = report_response.content
            
            # Add extension metadata
            final_report.extensibility_metadata.update({
                "extensions_applied": list(extension_results.keys()),
                "extension_results": extension_results,
                "similar_trades_analyzed": len(similar_trades),
                "workflow_version": "1.0.0"
            })

            # Step 6: Save to document knowledge base
            yield RunResponse(
                run_id=self.run_id,
                content="💾 Saving analysis to knowledge base...",
                event=RunEvent.run_response.value
            )
            
            self.save_analysis_to_knowledge_base(final_report)

            # Step 7: Return final comprehensive report
            yield RunResponse(
                run_id=self.run_id,
                content=final_report.model_dump_json(indent=2),
                event=RunEvent.workflow_completed.value
            )
            
            logger.info(f"✅ Trade analysis workflow completed for {trade_id}")

        except Exception as e:
            logger.error(f"❌ Workflow failed: {e}")
            yield RunResponse(
                run_id=self.run_id,
                content=f"❌ Analysis failed: {str(e)}",
                event=RunEvent.workflow_completed.value
            )

def create_trade_analysis_workflow(session_id: Optional[str] = None) -> TradeAnalysisWorkflow:
    """
    Factory function to create a configured trade analysis workflow
    
    Args:
        session_id: Optional session ID for workflow persistence
        
    Returns:
        Configured TradeAnalysisWorkflow instance
    """
    if session_id is None:
        session_id = f"trade-analysis-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    workflow = TradeAnalysisWorkflow(
        session_id=session_id,
        storage=SqliteStorage(
            table_name="trade_analysis_workflows",
            db_file="tmp/trade_analysis_workflows.db"
        ),
        debug_mode=True
    )
    
    return workflow

# Example usage and testing
if __name__ == "__main__":
    from rich.prompt import Prompt
    
    # Example trade IDs for testing
    example_trades = [
        "GNUMT0M0",  # NVDA call example
        # Add more example trade IDs here
    ]
    
    # Get trade ID from user
    trade_id = Prompt.ask(
        "[bold]Enter a trade ID to analyze[/bold]",
        default=example_trades[0] if example_trades else "GNUMT0M0"
    )
    
    # Create and run workflow
    workflow = create_trade_analysis_workflow()
    
    # Example extensions (future functionality)
    extensions = {
        "sentiment_analysis": {"source": "news", "timeframe": "trade_period"},
        "sector_analysis": {"compare_sector_performance": True}
    }
    
    # Execute workflow
    analysis_stream: Iterator[RunResponse] = workflow.run(
        trade_id=trade_id,
        include_similar_trades=True,
        extend_with=extensions
    )
    
    # Print results
    pprint_run_response(analysis_stream, markdown=True, show_time=True) 