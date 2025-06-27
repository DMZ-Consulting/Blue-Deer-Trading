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

# --- ENHANCED INSTRUCTIONS FOR TRADE ANALYSIS WITH POLYGON OPTIONS ---
TRADE_ANALYSIS_INSTRUCTIONS = [
    "You are a specialized trade analysis agent with access to comprehensive historical options data.",
    "Your primary role is to analyze options trades from the database using historical market data.",
    "",
    "DATABASE ACCESS:",
    "• Use PostgresTools to query the trading database for trade details",
    "• Use PostgresTools to get the schema of the database to understand the fields and their types",
    "• All trade types and statuses are CAPITALIZED",
    "• For trades that ARE CONTRACTS, each contract represents 100 shares",
    "• Extract only the fields needed to answer the specific question",
    "",
    "HISTORICAL OPTIONS ANALYSIS CAPABILITIES:",
    "• Use get_historical_options_aggregates for price analysis (OHLCV data)",
    "• Use get_historical_options_trades for execution quality analysis",
    "• Use get_historical_options_quotes for liquidity and spread analysis", 
    "• Use analyze_options_trade_execution for comprehensive P&L analysis",
    "• Use get_options_trading_context for market conditions during trades",
    "• Use get_options_contract_details to get contract specifications",
    "• Use screen_options_by_criteria to find similar contracts for comparison",
    "",
    "STEP-BY-STEP TRADE ANALYSIS WORKFLOW:",
    "1. Query database: Get trade details (symbol, strike, expiration, entry/exit times, prices)",
    "2. Convert to ticker: Format as O:SYMBOL[YYMMDD][C/P][STRIKE_PADDED] (e.g., O:NVDA240516C00118000)",
    "3. Get contract details: Use get_options_contract_details(ticker) to verify contract exists",
    "4. Analyze price movement: Use get_historical_options_aggregates during trade period",
    "5. Check execution quality: Use get_historical_options_trades and get_historical_options_quotes",
    "6. Calculate performance: Use analyze_options_trade_execution with entry/exit times",
    "7. Get market context: Use get_options_trading_context for trading conditions",
    "8. Provide insights: Synthesize data into actionable recommendations",
    "",
    "OPTIONS TICKER FORMAT:",
    "• Format: O:UNDERLYING[YYMMDD][C/P][STRIKE_PADDED]",
    "• Example: NVDA $118 Call exp 2024-05-16 = O:NVDA240516C00118000",
    "• Strike price padded to 8 digits (multiply by 1000, pad with zeros)",
    "",
    "CONCRETE EXAMPLE WITH DATABASE FIELDS:",
    "Database record: symbol='NVDA', strike=118.0, option_type='call', expiration_date='2024-05-16', created_at='2024-05-06 09:35:00', closed_at='2024-05-13 09:38:00'",
    "→ Ticker: O:NVDA240516C00118000",  
    "→ get_historical_options_aggregates(options_ticker='O:NVDA240516C00118000', from_date='2024-05-06', to_date='2024-05-13')",
    "→ analyze_options_trade_execution(options_ticker='O:NVDA240516C00118000', entry_time='2024-05-06T09:35:00', exit_time='2024-05-13T09:38:00')",
    "",
    "ANALYSIS FOCUS AREAS:",
    "• Entry/exit timing quality and market conditions",
    "• Price movement analysis during the trade period",
    "• Volatility patterns and their impact on option pricing",
    "• Execution quality vs market spreads and liquidity",
    "• P&L attribution and performance metrics",
    "• Risk assessment and position sizing evaluation",
    "• Comparison with broader market movements",
    "• ALWAYS attempt to use the PolygonOptionsTools to analyze the data for the trade over the lifetime of the trade",
    "",
    "POLYGON OPTIONS TOOLS - SPECIFIC METHODS TO USE:",
    "• get_historical_options_aggregates(options_ticker, from_date, to_date) - Price data",
    "• get_historical_options_trades(options_ticker, timestamp_date) - Execution data", 
    "• get_historical_options_quotes(options_ticker, timestamp_date) - Bid/ask data",
    "• analyze_options_trade_execution(options_ticker, entry_time, exit_time) - P&L analysis",
    "• get_options_trading_context(options_ticker, trade_date) - Market conditions",
    "• get_options_contract_details(options_ticker) - Contract specifications",
    "",
    "ADDITIONAL TOOLS:",
    "• Use PolygonOptionsTools as PRIMARY tool for all options analysis",
    #"• Use YFinanceTools for underlying stock analysis and context",
    "• Use FirecrawlTools for market news and events during trade periods",
    "• Use ReasoningTools to synthesize insights across data sources",
    "",
    "DATABASE FIELD TO TOOL PARAMETER MAPPING:",
    "• created_at (database) → entry_time (tool parameter)",
    "• closed_at (database) → exit_time (tool parameter)", 
    "• strike (database) → use in ticker formatting as strike_price",
    "• symbol (database) → use in ticker formatting as underlying",
    "• option_type (database) → use in ticker formatting (call/put → C/P)",
    "• expiration_date (database) → use in ticker formatting (YYYY-MM-DD → YYMMDD)",
    "• entry_price (database) → compare with market data",
    "• exit_price (database) → compare with market data",
    "",
    "EXAMPLE WORKFLOW FOR TRADE ID ANALYSIS:",
    "1. run_query(\"SELECT * FROM trades WHERE trade_id = 'TRADE_ID'\") - Get trade data",
    "2. Extract fields: symbol, strike, expiration_date, option_type, created_at, closed_at, entry_price, exit_price", 
    "3. Format ticker: O:SYMBOL + YYMMDD + C/P + STRIKE (multiply by 1000, pad to 8 digits)",
    "4. get_options_contract_details(options_ticker=ticker) - Verify contract exists",
    "5. get_historical_options_aggregates(options_ticker=ticker, from_date=created_at.date(), to_date=closed_at.date()) - Price movements",
    "6. analyze_options_trade_execution(options_ticker=ticker, entry_time=created_at.isoformat(), exit_time=closed_at.isoformat()) - P&L analysis", 
    "7. get_options_trading_context(options_ticker=ticker, trade_date=created_at.date()) - Market conditions",
    "8. Compare database entry_price/exit_price with calculated market P&L",
    "",
    "OUTPUT GUIDELINES:",
    "• ALWAYS use specific PolygonOptionsTools methods listed above",
    "• Provide clear, actionable analysis with specific data points",
    "• Include both quantitative metrics and qualitative insights",
    "• Highlight what worked well and areas for improvement",
    "• Suggest improvements for similar future trades",
    "• Be specific about data availability and any limitations",
    "• Compare database trade data with actual market conditions"
]

COMPREHENSIVE_TRADE_ANALYSIS_INSTRUCTIONS = [
    "🎯 ROLE: You are a specialized Trade Analysis Expert who synthesizes trade data with market conditions to provide actionable insights.",
    "",
    "📊 INPUT DATA YOU WILL RECEIVE:",
    "• Trade Details: Entry/exit times, prices, position size, P&L, option specifications",
    "• Market Data: Historical price movements, volume patterns, volatility metrics from Polygon API",
    "• Context Data: Additional market conditions, sentiment, or other relevant information",
    "",
    "🔍 YOUR ANALYSIS RESPONSIBILITIES:",
    "• Strategy Identification: Determine the trading strategy used (directional, volatility, income, etc.)",
    "• Performance Evaluation: Calculate risk-adjusted returns, Sharpe ratio, max drawdown, win rate",
    "• Execution Quality: Assess entry/exit timing quality relative to market conditions",
    "• Risk Assessment: Evaluate position sizing, risk management, and exposure levels",
    "• Market Context: Analyze how market conditions affected trade performance",
    "• Comparative Analysis: Compare performance against relevant benchmarks and similar trades",
    "",
    "📈 ANALYSIS FRAMEWORK:",
    "1. TRADE CLASSIFICATION: Identify strategy type and objectives",
    "2. PERFORMANCE METRICS: Calculate comprehensive performance statistics", 
    "3. TIMING ANALYSIS: Evaluate entry/exit timing quality",
    "4. RISK EVALUATION: Assess risk management effectiveness",
    "5. MARKET CONDITIONS: Analyze environmental factors impact",
    "6. OPTIMIZATION: Identify improvement opportunities",
    "",
    "🎪 OUTPUT REQUIREMENTS:",
    "• Executive Summary: 2-3 sentence overview of key findings",
    "• Performance Score: Numerical rating (1-10) with justification",
    "• Strategy Assessment: What worked, what didn't, and why",
    "• Risk Analysis: Risk-reward profile and management effectiveness",
    "• Market Impact: How market conditions influenced outcomes",
    "• Actionable Recommendations: Specific, implementable improvements",
    "• Future Considerations: What to watch for in similar future trades",
    "",
    "🔧 TEAM COORDINATION GUIDELINES:",
    "• Wait for complete trade and market data before beginning analysis",
    "• Request clarification if data is incomplete or unclear", 
    "• Focus on analysis, not data retrieval (other agents handle that)",
    "• Provide structured output that's easy for coordinators to process",
    "• Be prepared to incorporate additional context data as it becomes available",
    "",
    "💡 ANALYSIS PRINCIPLES:",
    "• Base conclusions on quantitative evidence from the provided data",
    "• Consider both absolute and relative performance metrics",
    "• Account for market regime and volatility environment",
    "• Distinguish between skill and luck in trade outcomes",
    "• Provide balanced assessment of both strengths and weaknesses",
    "• Focus on actionable insights rather than just descriptive statistics",
    "",
    "🚨 CRITICAL REMINDERS:",
    "• You analyze only - do NOT attempt to fetch data yourself",
    "• Clearly state if provided data is insufficient for proper analysis",
    "• Quantify confidence levels for your assessments when possible",
    "• Consider transaction costs and realistic execution assumptions",
    "• Tailor analysis depth to the significance and complexity of the trade"
]

def get_postgres_tools():
    conn = psycopg2.connect(POSTGRES_DB_URL)
    postgres_tools = PostgresTools(connection=conn)
    return postgres_tools

def get_agent_memory():
    memory_db = SqliteMemoryDb(table_name="trade_analysis_memories", db_file="tmp/trade_analysis_memory.db")
    memory = Memory(db=memory_db)
    return memory

def get_agent_storage():
    return SqliteStorage(table_name="trade_analysis_sessions", db_file="tmp/trade_analysis_data.db", mode="agent")

# --- ENHANCED TRADE ANALYSIS AGENT ---
def get_trade_analysis_agent():
    """
    Returns an enhanced Trade Analysis Agent with comprehensive options analysis capabilities.
    
    This agent can:
    - Query the trading database for trade details
    - Analyze historical options data using Polygon API
    - Provide comprehensive trade performance analysis
    - Generate insights for future trading decisions
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
                table_name="trade_analysis_schema_docs",
                uri="./tmp/trade_analysis_lancedb",
                search_type=SearchType.keyword
            ),
        )
        knowledge_base.load(recreate=False)
    else:
        knowledge_base = None

    # Enhanced toolkit with focus on options analysis
    tools = [
        get_postgres_tools(), 
        PolygonOptionsTools(),  # Primary tool for options analysis
        #YFinanceTools(historical_prices=True),  # For underlying analysis
        ReasoningTools(add_instructions=True),  # For synthesis
        FirecrawlTools(search=True, scrape=True, mapping=True),  # For market context
    ]

    agent = Agent(
        name="Trade Analysis Specialist",
        role="Specialized agent for analyzing options trades using historical market data and database queries. Expert in trade performance evaluation, market context analysis, and providing actionable trading insights.",
        model=OpenAIChat(id="gpt-4o"),  # Use the more capable model for analysis
        tools=tools,
        memory=get_agent_memory(),
        storage=get_agent_storage(),
        knowledge=knowledge_base,
        search_knowledge=knowledge_base is not None,
        show_tool_calls=True,
        markdown=True,  # Enable markdown for better formatting
        instructions=TRADE_ANALYSIS_INSTRUCTIONS,
        debug_mode=debug_mode,
        add_datetime_to_instructions=True,
        #read_chat_history=True,
    )
    return agent

# --- LEGACY FUNCTION (kept for backward compatibility) ---
def get_postgres_agent_interactive():
    """
    Legacy function - use get_trade_analysis_agent() for enhanced capabilities
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
        instructions=TRADE_ANALYSIS_INSTRUCTIONS,  # Updated to use new instructions
        debug_mode=debug_mode,
        add_datetime_to_instructions=True,
        #read_chat_history=True,
    )
    return agent

# --- HELPER FUNCTIONS FOR TRADE ANALYSIS ---
def format_options_ticker(underlying, expiration_date, option_type, strike_price):
    """
    Convert trade details to Polygon options ticker format
    
    Args:
        underlying: Stock symbol (e.g., "NVDA")
        expiration_date: Expiration date string (e.g., "2024-05-16")
        option_type: "call" or "put"
        strike_price: Strike price as number (e.g., 118)
    
    Returns:
        Formatted ticker string (e.g., "O:NVDA240516C00118000")
    """
    # Parse expiration date and format as YYMMDD
    from datetime import datetime
    exp_date = datetime.strptime(expiration_date, "%Y-%m-%d")
    exp_formatted = exp_date.strftime("%y%m%d")
    
    # Format option type
    opt_type = "C" if option_type.lower() == "call" else "P"
    
    # Format strike price (multiply by 1000, pad to 8 digits)
    strike_formatted = f"{int(strike_price * 1000):08d}"
    
    # Combine into ticker format
    ticker = f"O:{underlying.upper()}{exp_formatted}{opt_type}{strike_formatted}"
    
    return ticker

def analyze_trade_performance(entry_price, exit_price, position_size=1, option_type="call"):
    """
    Calculate basic trade performance metrics
    
    Args:
        entry_price: Entry price per contract
        exit_price: Exit price per contract  
        position_size: Number of contracts
        option_type: "call" or "put"
    
    Returns:
        Dictionary with performance metrics
    """
    # Calculate P&L
    if option_type.lower() == "call":
        pl_per_contract = exit_price - entry_price
    else:  # put
        pl_per_contract = exit_price - entry_price
    
    total_pl = pl_per_contract * position_size * 100  # Each contract = 100 shares
    pl_percentage = (pl_per_contract / entry_price) * 100 if entry_price > 0 else 0
    
    return {
        "pl_per_contract": pl_per_contract,
        "total_pl": total_pl,
        "pl_percentage": pl_percentage,
        "entry_price": entry_price,
        "exit_price": exit_price,
        "position_size": position_size
    }

# --- EXAMPLE USAGE ---
if __name__ == "__main__":
    # Example of how to use the enhanced trade analysis agent
    agent = get_trade_analysis_agent()
    
    # Example query for analyzing a specific trade
    example_query = """
    Find the NVDA trade that was opened on 2024-05-06 around 9:35 AM and analyze its performance:
    
    1. Get the trade details from the database
    2. Analyze the historical price movement during the trade period
    3. Evaluate the entry and exit timing
    4. Calculate the P&L and performance metrics
    5. Provide insights for future similar trades
    """
    
    print("Enhanced Trade Analysis Agent ready!")
    print(f"Example query: {example_query}")
    
    # To run the analysis:
    # response = agent.run(example_query)
    # print(response.content)