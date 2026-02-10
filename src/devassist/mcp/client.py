"""MCP Client for DevAssist.

Connects to MCP servers and provides tool execution capabilities.
"""

import asyncio
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

from devassist.mcp.registry import MCPServerConfig

# MCP SDK imports - optional, checked at runtime
try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    from mcp.types import Tool

    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    ClientSession = None  # type: ignore
    StdioServerParameters = None  # type: ignore
    stdio_client = None  # type: ignore
    Tool = None  # type: ignore


@dataclass
class ToolSchema:
    """Schema for a tool available via MCP.

    Attributes:
        name: Tool name (e.g., "github_list_repos")
        description: What the tool does
        server: Which MCP server provides this tool
        input_schema: JSON Schema for the tool's parameters
    """

    name: str
    description: str
    server: str
    input_schema: dict[str, Any] = field(default_factory=dict)

    def to_llm_format(self) -> dict[str, Any]:
        """Convert to format expected by LLM tool calling.

        Returns:
            Dictionary in OpenAI/Anthropic tool format.
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": f"[{self.server}] {self.description}",
                "parameters": self.input_schema,
            },
        }


@dataclass
class ToolResult:
    """Result from executing an MCP tool.

    Attributes:
        tool_name: Name of the tool that was called
        server: Server that executed the tool
        content: Result content (usually text or JSON)
        is_error: Whether the result is an error
    """

    tool_name: str
    server: str
    content: Any
    is_error: bool = False


class MCPClient:
    """Client for connecting to multiple MCP servers.

    Manages connections to MCP servers and provides a unified
    interface for discovering and executing tools.
    """

    def __init__(self) -> None:
        """Initialize the MCP client."""
        self._sessions: dict[str, ClientSession] = {}
        self._tools: dict[str, list[ToolSchema]] = {}
        self._tool_to_server: dict[str, str] = {}

    @property
    def is_available(self) -> bool:
        """Check if MCP SDK is installed."""
        return MCP_AVAILABLE

    @asynccontextmanager
    async def connect(
        self, server_config: MCPServerConfig
    ) -> AsyncIterator["MCPClient"]:
        """Connect to an MCP server.

        Args:
            server_config: Configuration for the server to connect to.

        Yields:
            Self with active connection.

        Raises:
            RuntimeError: If MCP SDK is not available.
        """
        if not MCP_AVAILABLE:
            raise RuntimeError(
                "MCP SDK not installed. Run: pip install mcp"
            )

        # Prepare environment with server's required variables
        env = os.environ.copy()
        env.update(server_config.env)

        server_params = StdioServerParameters(
            command=server_config.command,
            args=server_config.args,
            env=env,
        )

        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                # Initialize the session
                await session.initialize()

                # Store session
                self._sessions[server_config.name] = session

                # Discover tools
                await self._discover_tools(server_config.name, session)

                try:
                    yield self
                finally:
                    # Cleanup
                    del self._sessions[server_config.name]
                    if server_config.name in self._tools:
                        # Remove tool mappings
                        for tool in self._tools[server_config.name]:
                            self._tool_to_server.pop(tool.name, None)
                        del self._tools[server_config.name]

    @asynccontextmanager
    async def connect_all(
        self, server_configs: list[MCPServerConfig]
    ) -> AsyncIterator["MCPClient"]:
        """Connect to multiple MCP servers.

        Args:
            server_configs: List of server configurations.

        Yields:
            Self with all active connections.
        """
        if not server_configs:
            yield self
            return

        # Connect to servers sequentially (could be parallelized)
        # Using a stack of context managers
        async with self.connect(server_configs[0]):
            if len(server_configs) == 1:
                yield self
            else:
                async with self.connect_all(server_configs[1:]):
                    yield self

    # Alias for connect_all
    connect_many = connect_all

    async def _discover_tools(self, server_name: str, session: Any) -> None:
        """Discover available tools from a connected server.

        Args:
            server_name: Name of the server.
            session: Active MCP session.
        """
        if not MCP_AVAILABLE:
            return

        result = await session.list_tools()
        tools = []

        for tool in result.tools:
            schema = ToolSchema(
                name=tool.name,
                description=tool.description or "",
                server=server_name,
                input_schema=tool.inputSchema if hasattr(tool, "inputSchema") else {},
            )
            tools.append(schema)
            self._tool_to_server[tool.name] = server_name

        self._tools[server_name] = tools

    def get_all_tools(self) -> list[ToolSchema]:
        """Get all available tools across all connected servers.

        Returns:
            List of tool schemas.
        """
        all_tools = []
        for tools in self._tools.values():
            all_tools.extend(tools)
        return all_tools

    def get_tools_for_server(self, server_name: str) -> list[ToolSchema]:
        """Get tools available from a specific server.

        Args:
            server_name: Name of the server.

        Returns:
            List of tool schemas from that server.
        """
        return self._tools.get(server_name, [])

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
    ) -> ToolResult:
        """Execute a tool call.

        Args:
            tool_name: Name of the tool to call.
            arguments: Arguments to pass to the tool.

        Returns:
            ToolResult with the execution result.

        Raises:
            ValueError: If tool is not found or server not connected.
        """
        server_name = self._tool_to_server.get(tool_name)
        if not server_name:
            return ToolResult(
                tool_name=tool_name,
                server="unknown",
                content=f"Tool '{tool_name}' not found",
                is_error=True,
            )

        session = self._sessions.get(server_name)
        if not session:
            return ToolResult(
                tool_name=tool_name,
                server=server_name,
                content=f"Server '{server_name}' not connected",
                is_error=True,
            )

        try:
            result = await session.call_tool(tool_name, arguments or {})

            # Extract content from result
            content = ""
            if result.content:
                # MCP returns a list of content blocks
                content_parts = []
                for block in result.content:
                    if hasattr(block, "text"):
                        content_parts.append(block.text)
                    else:
                        content_parts.append(str(block))
                content = "\n".join(content_parts)

            return ToolResult(
                tool_name=tool_name,
                server=server_name,
                content=content,
                is_error=result.isError if hasattr(result, "isError") else False,
            )

        except Exception as e:
            return ToolResult(
                tool_name=tool_name,
                server=server_name,
                content=f"Error calling tool: {e}",
                is_error=True,
            )

    def get_connected_servers(self) -> list[str]:
        """Get names of currently connected servers.

        Returns:
            List of server names.
        """
        return list(self._sessions.keys())
