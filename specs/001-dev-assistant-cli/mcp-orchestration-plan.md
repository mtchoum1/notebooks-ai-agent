# MCP Orchestration Agent Architecture

## Overview

Transform DevAssist from direct adapters to an **agentic MCP-based architecture** where:
1. User gives a natural language prompt
2. LLM receives: `System Prompt + User Prompt + Available MCP Tools`
3. LLM decides which MCP tool(s) to call
4. MCP Client routes requests to appropriate MCP servers
5. Results are returned and optionally summarized

## New Module Structure

```
src/devassist/
├── mcp/                          # NEW: MCP integration layer
│   ├── __init__.py
│   ├── client.py                 # MCP Client - connects to MCP servers
│   ├── registry.py               # Registry of available MCP servers/tools
│   ├── tool_schema.py            # Tool schema definitions for LLM
│   └── servers/                  # Built-in MCP server configs
│       ├── __init__.py
│       ├── github.py             # GitHub MCP server config
│       ├── jira.py               # JIRA MCP server config
├── orchestrator/                 # NEW: Orchestration agent
│   ├── __init__.py
│   ├── agent.py                  # Main orchestration agent
│   ├── llm_client.py             # LLM client for tool selection
│   ├── prompts.py                # System prompts for orchestration
│   └── tool_executor.py          # Executes MCP tool calls
└── ... (existing modules)
```

## Core Components

### 1. MCP Client (`mcp/client.py`)

Responsibilities:
- Connect to MCP servers (stdio, SSE, or HTTP transport)
- Discover available tools from each server
- Execute tool calls and return results
- Handle connection lifecycle

```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

class MCPClient:
    """Client for connecting to multiple MCP servers."""
    
    def __init__(self):
        self._sessions: dict[str, ClientSession] = {}
        self._tools: dict[str, list[Tool]] = {}
    
    async def connect(self, server_name: str, server_config: ServerConfig) -> None:
        """Connect to an MCP server and discover its tools."""
        ...
    
    async def call_tool(self, server_name: str, tool_name: str, arguments: dict) -> Any:
        """Execute a tool call on the specified server."""
        ...
    
    def get_all_tools(self) -> list[ToolSchema]:
        """Get all available tools across all connected servers."""
        ...
```

### 2. MCP Server Registry (`mcp/registry.py`)

Responsibilities:
- Store MCP server configurations
- Map server names to connection details
- Provide tool discovery metadata

```python
@dataclass
class MCPServerConfig:
    name: str                    # e.g., "github", "jira"
    command: str                 # e.g., "npx", "uvx"
    args: list[str]              # e.g., ["-y", "@modelcontextprotocol/server-github"]
    env: dict[str, str]          # e.g., {"GITHUB_TOKEN": "..."}
    description: str             # Human-readable description

class MCPRegistry:
    """Registry of available MCP servers."""
    
    def __init__(self):
        self._servers: dict[str, MCPServerConfig] = {}
    
    def register(self, config: MCPServerConfig) -> None:
        """Register an MCP server."""
        ...
    
    def get_configured_servers(self) -> list[MCPServerConfig]:
        """Get all servers that have valid credentials configured."""
        ...
```

### 3. Orchestration Agent (`orchestrator/agent.py`)

Responsibilities:
- Receive user prompt
- Build context for LLM (system prompt + tools schema)
- Parse LLM response for tool calls
- Execute tool calls via MCP Client
- Return final response

```python
class OrchestrationAgent:
    """Main orchestration agent that coordinates LLM and MCP."""
    
    def __init__(
        self,
        llm_client: LLMClient,
        mcp_client: MCPClient,
        registry: MCPRegistry,
    ):
        self._llm = llm_client
        self._mcp = mcp_client
        self._registry = registry
    
    async def process(self, user_prompt: str) -> AgentResponse:
        """Process a user prompt through the orchestration pipeline.
        
        Flow:
        1. Get available tools from MCP registry
        2. Build LLM prompt with tools schema
        3. Get LLM response (may include tool calls)
        4. Execute any tool calls via MCP client
        5. If tool results, send back to LLM for final response
        6. Return final response
        """
        # 1. Get available tools
        tools = self._mcp.get_all_tools()
        
        # 2. Build messages for LLM
        messages = [
            {"role": "system", "content": self._build_system_prompt(tools)},
            {"role": "user", "content": user_prompt},
        ]
        
        # 3. Call LLM with tools
        response = await self._llm.chat(messages, tools=tools)
        
        # 4. Execute tool calls if any
        while response.tool_calls:
            tool_results = await self._execute_tool_calls(response.tool_calls)
            messages.append({"role": "assistant", "content": response})
            messages.append({"role": "tool", "content": tool_results})
            response = await self._llm.chat(messages, tools=tools)
        
        # 5. Return final response
        return AgentResponse(content=response.content, sources_used=[...])
```

### 4. LLM Client (`orchestrator/llm_client.py`)

Responsibilities:
- Send prompts to LLM with tool definitions
- Parse tool call responses
- Support multiple LLM providers (Vertex AI, OpenAI, Anthropic)

```python
class LLMClient:
    """Client for LLM interactions with tool calling support."""
    
    async def chat(
        self,
        messages: list[Message],
        tools: list[ToolSchema] | None = None,
    ) -> LLMResponse:
        """Send messages to LLM, optionally with tool definitions.
        
        Returns:
            LLMResponse with content and/or tool_calls
        """
        ...
```

## Data Flow Example

**User**: "What are my unread GitHub notifications?"

```
1. CLI receives: "What are my unread GitHub notifications?"

2. OrchestrationAgent.process() called

3. MCP Client provides available tools:
   [
     {"name": "github_list_notifications", "description": "...", "parameters": {...}},
     {"name": "jira_get_issues", "description": "...", "parameters": {...}},
   ]

4. LLM receives:
   - System Prompt: "You are a developer assistant. Use tools to help users..."
   - User Prompt: "What are my unread GitHub notifications?"
   - Tools: [github_list_notifications, jira_get_issues]

5. LLM responds with tool call:
   {
     "tool_calls": [{
       "name": "github_list_notifications",
       "arguments": {"filter": "unread"}
     }]
   }

6. MCP Client executes tool call → GitHub MCP Server

7. Results returned to LLM for final summarization

8. LLM generates human-readable response:
   "You have 3 unread GitHub notifications:
    - PR review requested on repo/feature-branch
    - Issue mention in repo#123
    - CI failure on main branch"

9. Response returned to CLI
```

## MCP Server Options

### Option A: Use Existing MCP Servers (Recommended to Start)

Use community MCP servers from https://github.com/modelcontextprotocol/servers:

```python
# GitHub MCP Server
MCPServerConfig(
    name="github",
    command="npx",
    args=["-y", "@modelcontextprotocol/server-github"],
    env={"GITHUB_PERSONAL_ACCESS_TOKEN": "..."},
)

```

### Option B: Build Custom MCP Servers

For services without existing MCP servers (some JIRA setups), build custom ones:

```python
# Custom JIRA MCP Server (Python)
from mcp.server import Server
from mcp.types import Tool

server = Server("jira")

@server.list_tools()
async def list_tools():
    return [
        Tool(name="jira_get_issues", description="Get JIRA issues", ...),
        Tool(name="jira_create_issue", description="Create a JIRA issue", ...),
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "jira_get_issues":
        return await fetch_jira_issues(arguments)
    ...
```

## CLI Integration

Update the CLI to use the orchestration agent:

```python
# cli/main.py
@app.command()
def ask(prompt: str):
    """Ask the assistant anything."""
    agent = get_orchestration_agent()
    response = asyncio.run(agent.process(prompt))
    console.print(response.content)

# Example usage:
# devassist ask "What are my GitHub notifications?"
# devassist ask "What JIRA tickets are assigned to me?"
# devassist ask "Give me a morning brief"  # Uses multiple tools
```

## Implementation Order

1. **Phase 1: MCP Client Foundation**
   - Install `mcp` package
   - Implement basic MCPClient that can connect to one server
   - Test with GitHub MCP server

2. **Phase 2: Registry & Multi-Server**
   - Implement MCPRegistry
   - Support connecting to multiple servers
3. **Phase 3: Orchestration Agent**
   - Implement LLMClient with tool calling
   - Implement OrchestrationAgent
   - Wire up the full pipeline

4. **Phase 4: CLI & Polish**
   - Add `devassist ask` command
   - Update `devassist brief` to use orchestrator
   - Add configuration for MCP servers

## Dependencies to Add

```toml
# pyproject.toml
dependencies = [
    # ... existing ...
    "mcp>=1.0.0",              # MCP SDK
    "anthropic>=0.40.0",       # For Claude (best tool calling)
    # OR keep vertex AI for Gemini
]
```

## Questions to Decide

1. **LLM Provider**: Vertex AI (Gemini) vs Anthropic (Claude) vs OpenAI?
   - Claude has best tool calling, Gemini is already set up

2. **MCP Transport**: stdio (local) vs SSE (remote)?
   - Start with stdio for simplicity

3. **Custom vs Community MCP Servers**: Build your own or use existing?
   - Start with community servers (e.g. GitHub) where available
   - Build or configure custom servers for JIRA as needed

4. **Agentic Loop Depth**: How many tool call iterations allowed?
   - Suggest max 5 iterations to prevent runaway
