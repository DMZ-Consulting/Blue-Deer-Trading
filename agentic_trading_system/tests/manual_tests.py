from datetime import datetime
import os
import sys
from agno.utils.pprint import pprint_run_response
import pandas as pd

os.environ["DEBUG_MODE"] = os.getenv("DEBUG_MODE", "true")

# add our modules to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_postgres_agent():
    from agents.postgres_agent import get_postgres_agent
    agent = get_postgres_agent()
    query = "Get all trades that have an opened duration of > 10 days"
    try:
        sql_query = agent.run(query)
        if hasattr(sql_query, 'content'):
            sql_query = sql_query.content
            print(sql_query)
        else:
            raise Exception("SQL query response is not a string")
        query_response = pd.read_sql_query(sql=sql_query, con=agent.tools[0].connection)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_filepath = f"discovery_data_{timestamp}.csv"
        query_response.to_csv(csv_filepath, index=False)
        print(f"Trading data saved to {csv_filepath}")
    except Exception as e:
        raise Exception(f"Failed to fetch trading data: {e}")

def test_strategy_research_agent():
    from agents.strategy_researcher import create_strategy_research_agent
    agent = create_strategy_research_agent()
    prompt = "Research momentum trading strategies and provide a summary."
    print("\n[Manual Test] Running Strategy Research Agent...")
    response = agent.run(prompt)
    pprint_run_response(response)

def test_analysis_method_agent():
    from agents.analysis_method_developer import create_analysis_method_agent
    agent = create_analysis_method_agent()
    prompt = "Given trading data with entry/exit times, symbols, and PnL, suggest a novel SQL analysis method."
    print("\n[Manual Test] Running Analysis Method Agent...")
    response = agent.run(prompt)
    pprint_run_response(response)

def test_knowledge_updater_agent():
    from agno.document.base import Document
    from agno.knowledge.document import DocumentKnowledgeBase
    from agno.vectordb.lancedb import LanceDb, SearchType
    from agno.embedder.openai import OpenAIEmbedder
    from agents.knowledge_updater import create_knowledge_updater_agent
    documents = [Document(content="Test knowledge base document.")]
    knowledge_base = DocumentKnowledgeBase(
        documents=documents,
        vector_db=LanceDb(
            table_name="test_knowledge",
            uri="./tmp/test_knowledge_lancedb",
            search_type=SearchType.hybrid,
            embedder=OpenAIEmbedder(id="text-embedding-3-small"),
        ),
    )
    knowledge_base.load(recreate=True)
    agent = create_knowledge_updater_agent(knowledge_base)
    prompt = "Integrate new findings about risk management into the knowledge base."
    print("\n[Manual Test] Running Knowledge Updater Agent...")
    response = agent.run(prompt)
    pprint_run_response(response)

def test_research_team():
    from teams.research_team import create_research_team
    team = create_research_team()
    prompt = "Research new momentum trading strategies and analysis methods."
    print("\n[Manual Test] Running Research Team...")
    response = team.run(prompt)
    pprint_run_response(response)

def test_analysis_team():
    from agno.document.base import Document
    from agno.knowledge.document import DocumentKnowledgeBase
    from agno.vectordb.lancedb import LanceDb, SearchType
    from agno.embedder.openai import OpenAIEmbedder
    from teams.analysis_team import create_analysis_team
    documents = [Document(content="Test knowledge base document.")]
    knowledge_base = DocumentKnowledgeBase(
        documents=documents,
        vector_db=LanceDb(
            table_name="test_analysis_knowledge",
            uri="./tmp/test_analysis_knowledge_lancedb",
            search_type=SearchType.hybrid,
            embedder=OpenAIEmbedder(id="text-embedding-3-small"),
        ),
    )
    knowledge_base.load(recreate=True)
    team = create_analysis_team(knowledge_base)
    prompt = "Test new SQL analysis methods for momentum trading strategies."
    print("\n[Manual Test] Running Analysis Team...")
    response = team.run(prompt)
    pprint_run_response(response)

def test_strategy_discovery_workflow():
    from agno.document.base import Document
    from agno.knowledge.document import DocumentKnowledgeBase
    from agno.vectordb.lancedb import LanceDb, SearchType
    from agno.embedder.openai import OpenAIEmbedder
    from agno.agent import Agent
    from agno.tools.postgres import PostgresTools
    from workflows.strategy_discovery import TradingStrategyDiscoveryWorkflow
    class DummyConn:
        def cursor(self): return self
        def execute(self, *a, **kw): return None
        def fetchall(self): return []
        def close(self): pass
    dummy_postgres_tools = PostgresTools(connection=DummyConn())
    postgres_agent = Agent(
        name="Dummy Postgres Agent",
        model=None,
        tools=[dummy_postgres_tools],
        instructions=["Stub agent for workflow test."],
    )
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

if __name__ == "__main__":
    #test_postgres_agent()
    #test_strategy_research_agent()
    #test_analysis_method_agent()
    #test_knowledge_updater_agent()
    test_research_team()
    #test_analysis_team()
    #test_strategy_discovery_workflow()
    print("\n====================\nAll manual tests completed.\n====================\n") 