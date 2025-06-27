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
    "You are ONLY to return the SQL query to execute as TEXT with no markdown formatting, not any other text."
]

def get_postgres_tools():
    conn = psycopg2.connect(POSTGRES_DB_URL)
    postgres_tools = PostgresTools(connection=conn)
    return postgres_tools

def get_postgres_knowledge_base():
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
    return knowledge_base   

# --- TOOLKIT FUNCTION ---
def get_postgres_agent():
    """
    Returns an Agno Agent configured with PostgresTools for querying the trading database using a direct db_url, and a knowledge base containing the DB schema.
    """
    knowledge_base = get_postgres_knowledge_base()

    print(POSTGRES_DB_URL)


    agent = Agent(
        model=OpenAIChat(id="gpt-4o"),
        tools=[get_postgres_tools()],
        knowledge=knowledge_base,
        search_knowledge=knowledge_base is not None,
        show_tool_calls=True,
        markdown=False,
        instructions=SCHEMA_INSTRUCTIONS,
        debug_mode=debug_mode,
    )
    return agent

def create_database_agent(name: str, role: str, instructions: list[str] = []):

    instructions = [
        "You are a database agent that will answer questions about the trading database.",
        "When asked to return data, you MUST execute the SQL query and return the actual data results.",
        "CRITICAL: Always return data in JSON format using the EXACT column names from the database schema.",
        "NEVER rename or transform column names - use the exact field names as defined in the database schema.",
        "",
        "DATABASE SCHEMA MAPPING - USE THESE EXACT COLUMN NAMES:",
        "- trade_id (NOT id)",
        "- symbol", 
        "- trade_type (NOT direction) - values: 'BTO', 'STO'",
        "- status - values: 'OPEN', 'CLOSED'",
        "- entry_price (NOT open_price or avg_price)",
        "- average_price",
        "- size (NOT quantity)",
        "- current_size",
        "- created_at (NOT entry_date)",
        "- closed_at (NOT exit_date)",
        "- exit_price",
        "- average_exit_price", 
        "- profit_loss",
        "- risk_reward_ratio",
        "- win_loss (NOT trade_result) - values: 'WIN', 'LOSS'",
        "- strike (THIS IS THE STRIKE PRICE - NOT roi)",
        "- expiration_date (NOT expiry)",
        "- option_type",
        "- user_id",
        "- is_contract",
        "- is_day_trade",
        "",
        "ALWAYS verify your output matches the actual database column names in your knowledge base schema.",
        "Include transactions from the transactions table when asked for complete trade data.",
        "If you see mismatched field names, correct them to match the database schema."
    ] + instructions

    return Agent(
        model=OpenAIChat(id="gpt-4o"),  # Use more capable model for better schema adherence
        tools=[get_postgres_tools()],
        knowledge=get_postgres_knowledge_base(),
        search_knowledge=False,
        show_tool_calls=True,
        markdown=False,
        name=name,
        role=role,
        instructions=instructions,
        debug_mode=debug_mode,
        add_datetime_to_instructions=True,
    )