from agents.postgres_agent import get_postgres_agent
from workflows.strategy_discovery import TradingStrategyDiscoveryWorkflow
from workflows.trade_analysis import create_trade_analysis_workflow
from workflows.research_only import create_research_only_workflow
from utils.knowledge_manager import create_base_knowledge_documents
from agents import create_all_agents
from teams import create_all_teams
from agno.knowledge.document import DocumentKnowledgeBase
from agno.vectordb.lancedb import LanceDb, SearchType
from agno.embedder.openai import OpenAIEmbedder
from dotenv import load_dotenv
import os
from agno.playground import Playground, serve_playground_app
from agno.run.response import RunResponse
from typing import Iterator
from agno.utils.pprint import pprint_run_response
from agno.tools.mcp import MCPTools
import asyncio
from agents.trade_analysis_agent import get_trade_analysis_agent

load_dotenv()

print("Starting Agentic Trading Strategy Research & Analysis System...")
"""
Main entry point for the Agentic Trading Strategy Research & Analysis System.

NEW ARCHITECTURE:
- RESEARCH WORKFLOW: Independent research for strategy discovery and knowledge expansion
- ANALYSIS WORKFLOW: Trade analysis with autonomous feedback loop for research requests
- CLEAR SEPARATION: Research and analysis operate independently with shared knowledge base

Key Components:
- ResearchOnlyWorkflow: On-demand research without trade analysis
- TradeAnalysisWorkflow: Autonomous trade bucketing with research feedback loop  
- Shared Knowledge Base: Central repository for strategies and analysis methods
- Agent/Team Factories: Modular creation of specialized agents and teams
"""

from utils.initialize_documents import create_data_documents

class AgenticTradingSystem:
    """
    Main system orchestrator with separated research and analysis capabilities.
    
    NEW FEATURES:
    - research_strategy(): Pure research without trade analysis
    - analyze_trades(): Trade analysis with autonomous research loop
    - discover_strategies(): Original combined workflow (for backward compatibility)
    """
    
    def __init__(self, postgres_agent):
        self.postgres_agent = postgres_agent
        self.knowledge_base = self._create_knowledge_base()
        
        # Initialize workflows with clear separation
        self.research_workflow = create_research_only_workflow(self.knowledge_base)
        self.analysis_workflow = create_trade_analysis_workflow(postgres_agent, self.knowledge_base)
        self.discovery_workflow = TradingStrategyDiscoveryWorkflow(postgres_agent, self.knowledge_base)  # Legacy
        
        # Initialize agents and teams
        self.agents = create_all_agents(knowledge_base=self.knowledge_base)
        self.teams = create_all_teams(knowledge_base=self.knowledge_base)

    def _create_knowledge_base(self):
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
        knowledge_base.load(recreate=False)
        return knowledge_base

    # ===== NEW SEPARATED WORKFLOWS =====
    
    def research_strategy(self, research_topic: str, depth: str = "comprehensive") -> Iterator[RunResponse]:
        """
        Pure research workflow - no trade analysis.
        
        Args:
            research_topic: What to research (e.g., "momentum trading strategies")
            depth: Research depth (preliminary, comprehensive, expert)
            
        Returns:
            Iterator of research progress and findings
        """
        print(f"🔬 Starting research-only session: {research_topic}")
        return self.research_workflow.run(research_topic=research_topic, research_depth=depth)
    
    def analyze_trades(self, user_id: str = None, days: int = 90, min_coverage: float = 0.75) -> Iterator[RunResponse]:
        """
        Autonomous trade analysis with research feedback loop.
        
        This will:
        1. Analyze trades using current knowledge base
        2. Identify unbucketable trades
        3. Automatically request research for gaps
        4. Update knowledge base and re-analyze
        5. Continue until coverage threshold is met
        
        Args:
            user_id: Specific user to analyze (None for all)
            days: Number of days to analyze
            min_coverage: Minimum % of trades that must be bucketable
            
        Returns:
            Iterator of analysis progress and results
        """
        print(f"📊 Starting autonomous trade analysis: {days} days, {min_coverage*100:.1f}% target coverage")
        return self.analysis_workflow.run(
            user_id=user_id, 
            time_period_days=days, 
            min_coverage_threshold=min_coverage
        )
    
    # ===== CONVENIENCE METHODS =====
    
    def research_specific_strategy(self, strategy_name: str) -> Iterator[RunResponse]:
        """Research a specific strategy in detail"""
        print(f"🎯 Researching specific strategy: {strategy_name}")
        return self.research_workflow.research_specific_strategy(strategy_name)
    
    def research_analysis_method(self, method_name: str) -> Iterator[RunResponse]:
        """Research a specific analysis method"""
        print(f"🧮 Researching analysis method: {method_name}")
        return self.research_workflow.research_analysis_method(method_name)
    
    def research_market_phenomenon(self, phenomenon: str) -> Iterator[RunResponse]:
        """Research a market phenomenon or pattern"""
        print(f"📈 Researching market phenomenon: {phenomenon}")
        return self.research_workflow.research_market_phenomenon(phenomenon)
    
    # ===== LEGACY COMPATIBILITY =====
    
    def discover_strategies(self, focus: str) -> Iterator[RunResponse]:
        """
        Legacy method: Combined research and discovery workflow.
        
        NOTE: Consider using research_strategy() or analyze_trades() instead
        for better separation of concerns.
        """
        print(f"⚠️ Using legacy combined workflow: {focus}")
        return self.discovery_workflow.run(research_focus=focus)


# ===== EXAMPLE USAGE FUNCTIONS =====

def example_research_session(system: AgenticTradingSystem):
    """Example of pure research session"""
    print("\n" + "="*80)
    print("🔬 RESEARCH-ONLY SESSION EXAMPLE")
    print("="*80)
    
    # Research momentum strategies
    research_results = system.research_strategy(
        research_topic="momentum trading strategies and breakout patterns",
        depth="comprehensive"
    )
    
    print("\n📚 Research Results:")
    for response in research_results:
        print(f"📝 {response.content}")

def example_trade_analysis(system: AgenticTradingSystem):
    """Example of autonomous trade analysis"""
    print("\n" + "="*80)
    print("📊 AUTONOMOUS TRADE ANALYSIS EXAMPLE")
    print("="*80)
    
    # Analyze trades with autonomous research loop
    analysis_results = system.analyze_trades(
        user_id=None,  # All users
        days=90,       # Last 90 days
        min_coverage=0.80  # 80% coverage target
    )
    
    print("\n📈 Analysis Results:")
    for response in analysis_results:
        print(f"📊 {response.content}")

def example_targeted_research(system: AgenticTradingSystem):
    """Example of targeted research requests"""
    print("\n" + "="*80)
    print("🎯 TARGETED RESEARCH EXAMPLES")
    print("="*80)
    
    # Research specific strategy
    print("\n🔍 Researching VWAP Strategy:")
    vwap_research = system.research_specific_strategy("VWAP trading strategy")
    for response in vwap_research:
        print(f"  📚 {response.content}")
    
    # Research analysis method
    print("\n🧮 Researching Time-of-Day Analysis:")
    tod_research = system.research_analysis_method("time-of-day performance analysis")
    for response in tod_research:
        print(f"  📊 {response.content}")


# Initialize and run system
create_data_documents()

# Initialize the system
postgres_agent = get_postgres_agent()
system = AgenticTradingSystem(postgres_agent)

# Create playground with separated workflows
from agents.interactive_db_agent import get_postgres_agent_interactive

debug_mode = os.getenv('DEBUG_MODE', 'false').lower() == 'true'
'''
if debug_mode:
    # Debug mode: Include research and analysis workflows
    app = Playground(
        agents=[
            get_postgres_agent_interactive(),
            system.agents.get("strategy_research"),
            system.agents.get("analysis_method"),
            system.agents.get("knowledge_updater"),
        ],
        workflows=[
            system.research_workflow,
            system.analysis_workflow,
            system.discovery_workflow,  # Legacy
        ],
        teams=[
            system.teams.get("research_team"),
            system.teams.get("analysis_team"),
        ],
    ).get_app()
else:
    # Production mode: Simple database agent only
    app = Playground(
        agents=[
            get_postgres_agent_interactive(),
        ],
    ).get_app()
'''
app = Playground(
    agents=[
        get_trade_analysis_agent(),
    ],
).get_app()


if __name__ == "__main__":
    if len(os.sys.argv) > 1 and os.sys.argv[1] == "examples":
        # Run examples
        print("🚀 Running System Examples...")
        
        # Example 1: Pure research session
        example_research_session(system)
        
        # Example 2: Autonomous trade analysis
        example_trade_analysis(system)
        
        # Example 3: Targeted research
        example_targeted_research(system)
        
        print("\n✅ Examples completed!")
        
    else:
        # Start playground server
        serve_playground_app("run:app", reload=False)
        #asyncio.run(test_mcp_tools())