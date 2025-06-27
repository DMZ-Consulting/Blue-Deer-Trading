from agno.agent import Agent
from agno.tools.postgres import PostgresTools
from agno.document.base import Document
from agno.knowledge.document import DocumentKnowledgeBase
from agno.vectordb.lancedb import LanceDb
from agno.vectordb.search import SearchType
from agno.models.openai import OpenAIChat
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()


# --- CONFIGURE YOUR DATABASE CONNECTION STRING HERE ---
POSTGRES_DB_URL = os.getenv("SUPABASE_DB_URL")

# --- PATH TO YOUR SCHEMA FILE ---
# Place your schema text file at 'data/docs/db_schema.txt'
SCHEMAS_DIR = os.path.join("knowledge", "database")

# --- INSTRUCTIONS FOR THE AGENT (customize for your schema) ---
SCHEMA_INSTRUCTIONS = [
    "You are an agent that will answer questions about the trading database.",
    "Use your knowledge to find the schemas of the database tables.",
    "All trade types and statuses are CAPITALIZED.",
    "You are ONLY to return the SQL query to execute, not any other text."
]



# --- TOOLKIT FUNCTION ---
def get_postgres_agent():
    """
    Returns an Agno Agent configured with PostgresTools for querying the trading database using a direct db_url, and a knowledge base containing the DB schema.
    """
    # Load schema as a document
    if os.path.exists(SCHEMAS_DIR):
        documents = []
        for file in os.listdir(SCHEMAS_DIR):
            with open(os.path.join(SCHEMAS_DIR, file), "r") as f:
                schema_text = f.read()
            documents.append(Document(content=schema_text))
        knowledge_base = DocumentKnowledgeBase(
            documents=documents,
            vector_db=LanceDb(
                table_name="db_schema_documents",
                uri="./tmp/lancedb",
                search_type=SearchType.keyword
            ),
        )
        knowledge_base.load(recreate=False)
    else:
        knowledge_base = None

    conn = psycopg2.connect(POSTGRES_DB_URL)
    postgres_tools = PostgresTools(connection=conn)
    agent = Agent(
        model=OpenAIChat(id="gpt-4o"),
        tools=[postgres_tools],
        knowledge=knowledge_base,
        search_knowledge=knowledge_base is not None,
        show_tool_calls=True,
        markdown=True,
        instructions=SCHEMA_INSTRUCTIONS,
        debug_mode=True,
    )
    return agent

# --- EXAMPLE USAGE ---
if __name__ == "__main__":
    agent = get_postgres_agent()
    # Example: Get all trades opened before a specific date
    #agent.print_response("Get all trades opened after 2025-05-01")
    # Example: Get all trades closed before a specific date
    #agent.print_response("Get all trades closed after 2025-05-01")
    # Example: Ask about the schema
    #agent.print_response("What columns are in the trades table?")

    agent.print_response("Get all trades that have an opened duration of > 10 days")
