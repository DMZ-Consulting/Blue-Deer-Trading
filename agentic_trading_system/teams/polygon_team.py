"""
3-Agent Trade Analysis Team in Coordinator Mode

This team uses a coordinator pattern with specialized agents:
1. Database Agent - Retrieves trade data from PostgreSQL
2. Polygon Agent - Fetches historical market data from Polygon API  
3. Analysis Agent - Synthesizes data into comprehensive trade analysis

The coordinator orchestrates the workflow and ensures proper data flow.
"""
from agno.team import Team
from agno.models.anthropic import Claude
from agno.models.openai import OpenAIChat
from agno.tools.reasoning import ReasoningTools
from agno.knowledge.document import DocumentKnowledgeBase
from agents.polygon_options_agent import get_polygon_options_agent
from agents.trade_analysis_specialist import create_trade_analysis_team_member
from agents.postgres_agent import create_database_agent
from agno.agent import Agent
from typing import Optional
from agno.storage.sqlite import SqliteStorage
from agno.vectordb.lancedb import LanceDb, SearchType
from agno.embedder.openai import OpenAIEmbedder

import os
from dotenv import load_dotenv

load_dotenv()

debug_mode = os.getenv("DEBUG_MODE", "false").lower() == "true"

def get_report_storage():
    return SqliteStorage(table_name="trade_analysis_reports", db_file="./tmp/report_storage.db")

def create_storage_agent():
    return Agent(
        name="Storage Agent",
        role="Store and retrieve trade analysis reports",
        instructions=[
            "🎯 MISSION: Store and retrieve trade analysis reports",
            "You are to store the trade analysis reports in the database.",
            "You are to retrieve the trade analysis reports from the database.",
            "You are to update the trade analysis reports in the database.",
            "You are to delete the trade analysis reports from the database.",
            "You are to search the trade analysis reports in the database.",
            "You are to get the trade analysis reports from the database.",
        ],
        storage=get_report_storage(),
    )

def create_database_trade_agent() -> Agent:
    """Agent specialized in retrieving trade data from PostgreSQL database"""
    return create_database_agent(
        name="Trade Database Specialist",
        role="Retrieve comprehensive trade data for analysis",
        instructions=[
            "🎯 MISSION: Retrieve complete trade data for analysis requests",
            "📊 DATA TO RETRIEVE:",
            "• Trade identification: trade_id, symbol, trade_type",
            "• Position details: strike, expiration_date, option_type, position_size", 
            "• Entry/exit data: created_at, closed_at, entry_price, exit_price",
            "• Performance data: profit_loss, size",
            "• Additional context: Any relevant trade metadata",
            "",
            "🔍 RETRIEVAL STANDARDS:",
            "• Provide complete trade records with all available fields",
            "• Validate data quality and flag any missing information",
            "• Format dates and numbers consistently",
            "• Include related trades if pattern analysis is requested",
            "• Ensure matching the data retrieved with the correct column names in the database. "
            "",
            "🤝 TEAM COORDINATION:",
            "• Focus on data retrieval - analysis is done by other team members",
            "• Provide structured, clean data for downstream processing",
            "• Flag data quality issues or missing information",
            "• Be ready to retrieve additional context if requested",
            "",
            "🔍 DATA PREVIEW:",
            "• Always show a preview of the data you are returning.",
            "• If the data is too large, show a preview of the first 10 rows.",
            "• Return the data with the fields attached, so the other agents can use it.",
        ]
    )

def create_trade_analysis_team(knowledge_base: Optional[DocumentKnowledgeBase] = None) -> Team:
    """
    Create a 3-agent trade analysis team using coordinator mode
    
    Team Members:
    1. Database Agent - Retrieves trade data from PostgreSQL
    2. Polygon Agent - Fetches market data from Polygon API
    3. Analysis Agent - Performs comprehensive trade analysis
    
    Workflow:
    - Coordinator receives trade ID or analysis request
    - Database agent retrieves trade details 
    - Polygon agent fetches relevant market data
    - Analysis agent synthesizes everything into comprehensive report
    """
    
    # Create specialized agents
    database_agent = create_database_trade_agent()
    polygon_agent = get_polygon_options_agent()
    analysis_agent = create_trade_analysis_team_member()
    
    return Team(
        name="Trade Analysis Team",
        mode="coordinate",  # Coordinator mode for structured workflow
        model=Claude(id="claude-3-5-sonnet-20241022"),  # Coordinator model
        members=[database_agent, polygon_agent, analysis_agent],
        tools=[ReasoningTools(add_instructions=True)],
        instructions=[
            "🎯 MISSION: Provide comprehensive analysis of individual trades using a 3-agent workflow",
            "",
            "👥 TEAM COORDINATION WORKFLOW:",
            "1. UNDERSTAND REQUEST: Parse the trade analysis request (trade ID, specific questions, etc.)",
            "2. GET TRADE DATA: Direct database agent to retrieve complete trade information",
            "3. GET MARKET DATA: Direct polygon agent to fetch relevant historical market data",
            "4. SYNTHESIZE ANALYSIS: Direct analysis agent to provide comprehensive assessment",
            "5. QUALITY CHECK: Ensure all data is complete and analysis is thorough",
            "6. STORE REPORT: Direct storage agent to store the trade analysis report in the database",
            "",
            "📊 DATA FLOW MANAGEMENT:",
            "• Database Agent provides: Trade details, P&L, timing, position info",
            "• Polygon Agent provides: Market prices, volatility, volume, context data",
            "• Analysis Agent provides: Performance metrics, insights, recommendations",
            "",
            "🔧 COORDINATION PRINCIPLES:",
            "• Ensure each agent has necessary data before proceeding to analysis",
            "• Validate data quality at each step",
            "• Request additional data if needed for complete analysis",
            "• Provide clear, structured final output combining all insights",
            "",
            "⚡ EFFICIENCY GUIDELINES:",
            "• Run database and polygon data retrieval in parallel when possible",
            "• Don't proceed to analysis until both data sources are complete",
            "• Focus on the specific trade(s) requested - avoid scope creep",
            "• Provide interim updates on progress",
            "",
            "🎪 OUTPUT STRUCTURE:",
            "• Executive Summary from analysis agent",
            "• Complete trade details from database agent", 
            "• Market context from polygon agent",
            "• Integrated insights and recommendations",
            "• Data quality notes and any limitations",
            "",
            "🚨 QUALITY STANDARDS:",
            "• Ensure all analysis is based on actual data, not assumptions",
            "• Flag any missing data or analysis limitations",
            "• Provide confidence levels for assessments",
            "• Include both quantitative metrics and qualitative insights"
        ],
        knowledge=knowledge_base,
        markdown=True,
        show_members_responses=True,
        enable_agentic_context=True,
        add_datetime_to_instructions=True,
        debug_mode=debug_mode,
        storage=get_report_storage(),
    )

if __name__ == "__main__":
    from agno.document.base import Document
    from agno.knowledge.document import DocumentKnowledgeBase
    from agno.vectordb.lancedb import LanceDb, SearchType
    from agno.embedder.openai import OpenAIEmbedder
    from agno.utils.pprint import pprint_run_response
    from typing import Optional

    # Test the trade analysis team
    def test_trade_analysis_team():
        """Test the 3-agent trade analysis team"""
        print("🚀 Testing 3-Agent Trade Analysis Team")
        print("=" * 60)
        
        # Optional knowledge base for storing analysis results
        try:
            documents = [Document(content="Trade analysis knowledge base initialized.")]
            knowledge_base = DocumentKnowledgeBase(
                documents=documents,
                vector_db=LanceDb(
                    table_name="trade_analysis_knowledge",
                    uri="./tmp/trade_analysis_knowledge_lancedb",
                    search_type=SearchType.hybrid,
                    embedder=OpenAIEmbedder(id="text-embedding-3-small"),
                ),
            )
            knowledge_base.load(recreate=False)
            print("✅ Knowledge base initialized")
        except Exception as e:
            print(f"⚠️ Knowledge base failed to initialize: {e}")
            knowledge_base = None

        # Create the team
        team = create_trade_analysis_team(knowledge_base)
        print("✅ Trade analysis team created")
        
        # Test with a specific trade
        test_prompts = [
            "Analyze trade GNUMT0M0 - I want to understand the performance and market conditions during this trade.",
            "Provide detailed analysis of trade GNUMT0M0 including execution quality and recommendations for improvement."
        ]
        
        for i, prompt in enumerate(test_prompts, 1):
            print(f"\n🧪 Test {i}: {prompt[:50]}...")
            print("-" * 40)
            
            try:
                response = team.run(prompt)
                pprint_run_response(response, markdown=True)
                print(f"✅ Test {i} completed successfully")
            except Exception as e:
                print(f"❌ Test {i} failed: {e}")
                import traceback
                traceback.print_exc()
            
            print("-" * 40)

    def test_individual_agents():
        """Test individual agents before team integration"""
        print("\n🔧 Testing Individual Agents")
        print("=" * 40)
        
        # Test database agent
        try:
            db_agent = create_database_trade_agent()
            print("✅ Database agent created")
        except Exception as e:
            print(f"❌ Database agent failed: {e}")
        
        # Test polygon agent  
        try:
            polygon_agent = get_polygon_options_agent()
            print("✅ Polygon agent created")
        except Exception as e:
            print(f"❌ Polygon agent failed: {e}")
            
        # Test analysis agent
        try:
            analysis_agent = create_trade_analysis_team_member()
            print("✅ Analysis agent created")
        except Exception as e:
            print(f"❌ Analysis agent failed: {e}")

    # Run tests
    test_individual_agents()
    test_trade_analysis_team()
