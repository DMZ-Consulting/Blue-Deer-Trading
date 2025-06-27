from agno.agent import Agent
from agno.tools.postgres import PostgresTools
from agno.document.base import Document
from agno.knowledge.document import DocumentKnowledgeBase
from agno.vectordb.lancedb import LanceDb
from agno.vectordb.search import SearchType
from agno.models.openai import OpenAIChat
from agno.models.google import Gemini
import psycopg2
import os
from dotenv import load_dotenv
from agno.tools.reasoning import ReasoningTools
from agno.memory.v2.db.sqlite import SqliteMemoryDb
from agno.memory.v2.memory import Memory
from agno.storage.sqlite import SqliteStorage
from agno.tools.yfinance import YFinanceTools
from agno.tools.firecrawl import FirecrawlTools
from toolkits import PolygonOptionsTools

load_dotenv()

debug_mode = os.getenv("DEBUG_MODE", "false").lower() == "true"

# --- CONFIGURE YOUR DATABASE CONNECTION STRING HERE ---
POSTGRES_DB_URL = os.getenv("SUPABASE_DB_URL")

# --- PATH TO YOUR SCHEMA FILE ---
# Place your schema text file at 'data/docs/db_schema.txt'
SCHEMAS_DIR = os.path.join("data", "knowledge", "database")

# --- INSTRUCTIONS FOR THE AGENT (customize for your schema) ---
SCHEMA_INSTRUCTIONS = [
    "You are an agent that will answer questions about the trading database.",
    "Use your knowledge to find the schemas of the database tables.",
    "All trade types and statuses are CAPITALIZED.",
    "You can use the yfinance tools to get historical data related to the trades in the database.",
    "You can use the reasoning tools to reason about the data and the trades.",
    "You can use the postgres tools to query the database.",
    "You can use the knowledge tools to search the knowledge base.",
    "You can use the firecrawl tools to search the web for information.",
    "You can use the reasoning tools to reason about the data and the trades.",
    "When pulling trades from the database, reason which fields need to be extracted and only extract the fields that are needed to answer the question.",
    "Understand that for trades that ARE CONTRACTS, we need to understand the trade represents 100 shares per contract.",
    #"You are ONLY to return the SQL query to execute as TEXT with no markdown formatting, not any other text."
]

def get_postgres_tools():
    conn = psycopg2.connect(POSTGRES_DB_URL)
    postgres_tools = PostgresTools(connection=conn)
    return postgres_tools

def get_agent_memory():
    memory_db = SqliteMemoryDb(table_name="strategy_memories", db_file="tmp/strategy_memory.db")
    memory = Memory(db=memory_db)
    return memory

def get_agent_storage():
    return SqliteStorage(table_name="agent_sessions", db_file="tmp/data.db", mode="agent")

# --- TOOLKIT FUNCTION ---
def get_postgres_agent_interactive():
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

    tools = [
        get_postgres_tools(), 
        ReasoningTools(add_instructions=True),
        YFinanceTools(historical_prices=True),
        FirecrawlTools(search=True, scrape=True, mapping=True),
        PolygonOptionsTools()
    ]

    agent = Agent(
        name="Interactive DB Agent",
        role="An agent that can interact with the database and answer questions about the database. You can use the yfinance tools to get historical data related to the trades in the database. You can use the firecrawl tools to search the web for information.",
        model=OpenAIChat(id="gpt-4.1-mini"),
        tools=tools,
        memory=get_agent_memory(),
        storage=get_agent_storage(),
        knowledge=knowledge_base,
        search_knowledge=knowledge_base is not None,
        show_tool_calls=True,
        markdown=False,
        instructions=SCHEMA_INSTRUCTIONS,
        debug_mode=debug_mode,
        add_datetime_to_instructions=True,
        read_chat_history=True,
    )
    return agent