"""
Agent definition for updating and expanding the trading analysis knowledge base.
"""
from agno.agent import Agent
from agno.tools.knowledge import KnowledgeTools
from agno.tools.reasoning import ReasoningTools
from agno.knowledge.document import DocumentKnowledgeBase
from agno.models.openai import OpenAIChat
import os
from dotenv import load_dotenv

load_dotenv()

debug_mode = os.getenv("DEBUG_MODE", "false").lower() == "true"

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
