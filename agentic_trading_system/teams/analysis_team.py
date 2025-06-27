"""
Team definition for testing strategies and updating the knowledge base.
"""
from agno.team import Team
from agno.models.anthropic import Claude
from agno.tools.reasoning import ReasoningTools
from agno.knowledge.document import DocumentKnowledgeBase
from agents.knowledge_updater import create_knowledge_updater_agent
from agents.analysis_method_developer import StrategyTestResults
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.duckdb import DuckDbTools

import os
from dotenv import load_dotenv

load_dotenv()

debug_mode = os.getenv("DEBUG_MODE", "false").lower() == "true"

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
        debug_mode=debug_mode,
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
        knowledge=knowledge_base,
        show_members_responses=True,
        enable_agentic_context=True,
        add_datetime_to_instructions=True,
        debug_mode=debug_mode,
    )

if __name__ == "__main__":
    from agno.document.base import Document
    from agno.knowledge.document import DocumentKnowledgeBase
    from agno.vectordb.lancedb import LanceDb, SearchType
    from agno.embedder.openai import OpenAIEmbedder
    from agno.utils.pprint import pprint_run_response

    # Minimal knowledge base for test
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
