import os
from dotenv import load_dotenv
# from vanna.integrations.azureopenai import AzureOpenAILlmService
from vanna.integrations.google import GeminiLlmService
from vanna import Agent
from vanna.core.registry import ToolRegistry
from vanna.core.user import UserResolver, User, RequestContext
from vanna.tools import RunSqlTool, VisualizeDataTool
from vanna.tools.agent_memory import SaveQuestionToolArgsTool, SearchSavedCorrectToolUsesTool, SaveTextMemoryTool
from vanna.servers.fastapi import VannaFastAPIServer
from vanna.integrations.postgres import PostgresRunner
from vanna.integrations.local.agent_memory import DemoAgentMemory
from vanna.integrations.pinecone.agent_memory import PineconeAgentMemory
from vanna.core.enhancer import LlmContextEnhancer
from vanna.core.llm import LlmMessage

load_dotenv()



class SchemaEnhancer(LlmContextEnhancer):
    def __init__(self, sql_runner):
        self.sql_runner = sql_runner
        self.schema_cache = None

    async def enhance_system_prompt(
        self,
        system_prompt: str,
        user_message: str,
        user: User
    ) -> str:
        # Cache schema information
        if not self.schema_cache:
            self.schema_cache = await self.sql_runner.get_schema_info()

        # Extract relevant tables mentioned in user message
        relevant_tables = self._find_relevant_tables(
            user_message,
            self.schema_cache
        )

        if not relevant_tables:
            return system_prompt

        # Add schema information to prompt
        schema_section = "\n\n## Relevant Database Schema\n\n"
        for table in relevant_tables:
            schema_section += f"**{table['name']}**\n"
            schema_section += f"Columns: {', '.join(table['columns'])}\n\n"

        return system_prompt + schema_section

    def _find_relevant_tables(self, message: str, schema: dict) -> list:
        # Simple keyword matching (could use embeddings)
        message_lower = message.lower()
        relevant = []

        for table in schema['tables']:
            if table['name'].lower() in message_lower:
                relevant.append(table)

        return relevant

    async def enhance_user_messages(
        self,
        messages: list[LlmMessage],
        user: User
    ) -> list[LlmMessage]:
        return messages



# 2. Configuración para Azure
llm = GeminiLlmService(
    model="gemini-3-flash-preview",
    api_key=os.getenv("GEMINI_API_KEY")
)

db_tool = RunSqlTool(
    sql_runner=PostgresRunner(
        connection_string=os.getenv("SOURCE_DB_URL")
    )
)


# Configure your agent memory
agent_memory = PineconeAgentMemory(
    api_key=os.getenv("PINECONE_API_KEY"),
    environment=os.getenv("PINECONE_ENVIRONMENT"),
    index_name=os.getenv("PINECONE_INDEX_NAME")
)

# Configure user authentication
class SimpleUserResolver(UserResolver):
    async def resolve_user(self, request_context: RequestContext) -> User:
        user_email = request_context.get_cookie('vanna_email') or 'guest@example.com'
        group = 'admin' if user_email == 'admin@example.com' else 'user'
        return User(id=user_email, email=user_email, group_memberships=[group])

user_resolver = SimpleUserResolver()

# Create your agent
tools = ToolRegistry()
tools.register_local_tool(db_tool, access_groups=['admin', 'user'])
tools.register_local_tool(SaveQuestionToolArgsTool(), access_groups=['admin'])
tools.register_local_tool(SearchSavedCorrectToolUsesTool(), access_groups=['admin', 'user'])
tools.register_local_tool(SaveTextMemoryTool(), access_groups=['admin', 'user'])
tools.register_local_tool(VisualizeDataTool(), access_groups=['admin', 'user'])

agent = Agent(
    llm_service=llm,
    tool_registry=tools,
    user_resolver=user_resolver,
    agent_memory=agent_memory,
    llm_context_enhancer=SchemaEnhancer(db_tool.sql_runner)
)

# Run the server
server = VannaFastAPIServer(agent)
server.run()  # Access at http://localhost:8000