from agno.agent import Agent
from agno.memory.agent import AgentMemory
from agno.memory.db.sqlite import SqliteMemoryDb
from agno.models.openai import OpenAIChat
from agno.playground import Playground, serve_playground_app
from agno.storage.sqlite import SqliteStorage

from dotenv import load_dotenv

load_dotenv()

agent_storage: str = "tmp/agents.db"

basic_agent = Agent(
    name="Basic Agent",
    model=OpenAIChat(id="gpt-4.1-mini"),
    memory=AgentMemory(
        db=SqliteMemoryDb(
            table_name="agent_memory",
            db_file=agent_storage,
        ),
        create_user_memories=True,
        update_user_memories_after_run=True,
        create_session_summary=True,
        update_session_summary_after_run=True,
    ),
    storage=SqliteStorage(
        table_name="agent_sessions", db_file=agent_storage
    ),
    add_history_to_messages=True,
    num_history_responses=3,
    add_datetime_to_instructions=True,
    markdown=True,
)

app = Playground(
    agents=[
        basic_agent,
    ]
).get_app()

if __name__ == "__main__":
    serve_playground_app("playground:app", reload=True)