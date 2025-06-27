from pathlib import Path
from datetime import datetime
from textwrap import dedent
import pandas as pd
from sqlalchemy import text
from agno.workflow import Workflow, RunResponse, RunEvent
from teams.research_team import create_research_team
from teams.analysis_team import create_analysis_team
import os
from dotenv import load_dotenv

load_dotenv()

debug_mode = os.getenv("DEBUG_MODE", "false").lower() == "true"

class TradingStrategyDiscoveryWorkflow(Workflow):
    """
    Agentic workflow for discovering and testing new trading strategies.
    """
    description: str = dedent("""
        An intelligent system for discovering, testing, and integrating new trading
        strategy analysis methods. This workflow uses multiple AI agents to continuously
        expand the knowledge base of trading analysis techniques, ensuring the system
        becomes more sophisticated over time.
        """)
    
    def __init__(self, postgres_agent, knowledge_base):
        super().__init__()
        self.postgres_agent = postgres_agent
        self.knowledge_base = knowledge_base
        self.research_team = create_research_team()
        self.analysis_team = create_analysis_team(knowledge_base)
        self.data_dir = Path("./trading_data")
        self.data_dir.mkdir(exist_ok=True)
        self.debug_mode = debug_mode

    def run(self, 
            research_focus: str,
            trading_data_csv: str = None,
            use_existing_data: bool = False):
        """
        Execute the strategy discovery workflow.
        """
        yield RunResponse(
            content=f"🔍 Starting strategy discovery research on: {research_focus}",
            event=RunEvent.workflow_started
        )
        yield RunResponse(
            content="📚 Researching new trading strategies and analysis methods...",
            event=RunEvent.workflow_started
        )
        research_response = self.research_team.run(
            f"Research {research_focus} trading strategies. Focus on finding new ways to analyze "
            f"and bucket trading data that could reveal profitable patterns. Look for both "
            f"academic research and practical industry methods."
        )
        yield RunResponse(
            content=f"Research findings: {research_response.content}",
            event=RunEvent.workflow_started
        )
        if not use_existing_data or not trading_data_csv:
            yield RunResponse(
                content="📊 Fetching fresh trading data for analysis...",
                event=RunEvent.workflow_started
            )
            trading_data_csv = self._get_trading_data_for_analysis()
            yield RunResponse(
                content=f"Data prepared: {trading_data_csv}",
                event=RunEvent.workflow_started
            )
        yield RunResponse(
            content="🧪 Testing new analysis methods and updating knowledge base...",
            event=RunEvent.workflow_started
        )
        analysis_response = self.analysis_team.run(
            f"Test the analysis methods from the research findings on the trading data "
            f"in {trading_data_csv}. Validate the effectiveness of these methods and "
            f"integrate any significant findings into the knowledge base. Focus on methods "
            f"that reveal new insights about {research_focus}."
        )
        yield RunResponse(
            content=f"Analysis results: {analysis_response.content}",
            event=RunEvent.workflow_started
        )
        summary = self._generate_discovery_summary(
            research_focus, research_response.content, analysis_response.content
        )
        yield RunResponse(
            content=summary,
            event=RunEvent.workflow_completed
        )
    
    def _get_trading_data_for_analysis(self) -> str:
        query = "Get all trades that have an opened duration of > 10 days"
        try:
            sql_query = self.postgres_agent.run(query)
            if hasattr(sql_query, 'content'):
                sql_query = sql_query.content
                print(sql_query)
            else:
                raise Exception("SQL query response is not a string")
            query_response = pd.read_sql_query(sql=sql_query, con=self.postgres_agent.tools[0].connection)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            csv_filepath = self.data_dir / f"discovery_data_{timestamp}.csv"
            query_response.to_csv(csv_filepath, index=False)
            return str(csv_filepath)
        except Exception as e:
            raise Exception(f"Failed to fetch trading data: {e}")
    
    def _generate_discovery_summary(self, focus: str, research: str, analysis: str) -> str:
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

if __name__ == "__main__":
    from agno.document.base import Document
    from agno.knowledge.document import DocumentKnowledgeBase
    from agno.vectordb.lancedb import LanceDb, SearchType
    from agno.embedder.openai import OpenAIEmbedder
    from agno.agent import Agent
    from agno.tools.postgres import PostgresTools
    from agno.utils.pprint import pprint_run_response
    import types

    # Minimal stub Postgres agent (no real DB connection)
    class DummyConn:
        def cursor(self):
            return self
        def execute(self, *a, **kw):
            return None
        def fetchall(self):
            return []
        def close(self):
            pass
    dummy_postgres_tools = PostgresTools(connection=DummyConn())
    postgres_agent = Agent(
        name="Dummy Postgres Agent",
        model=None,
        tools=[dummy_postgres_tools],
        instructions=["Stub agent for workflow test."],
    )

    # Minimal knowledge base for test
    documents = [Document(content="Test knowledge base document.")]
    knowledge_base = DocumentKnowledgeBase(
        documents=documents,
        vector_db=LanceDb(
            table_name="test_workflow_knowledge",
            uri="./tmp/test_workflow_knowledge_lancedb",
            search_type=SearchType.hybrid,
            embedder=OpenAIEmbedder(id="text-embedding-3-small"),
        ),
    )
    knowledge_base.load(recreate=True)

    workflow = TradingStrategyDiscoveryWorkflow(postgres_agent, knowledge_base)
    prompt = "momentum trading strategies"
    print("\n[Manual Test] Running TradingStrategyDiscoveryWorkflow...")
    response = workflow.run(research_focus=prompt)
    pprint_run_response(response)
