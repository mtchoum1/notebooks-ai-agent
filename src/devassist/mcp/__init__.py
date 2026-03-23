"""MCP (Model Context Protocol) integration for DevAssist.

This module provides the MCP client and server registry for
connecting to external tools via the Model Context Protocol.
"""

from devassist.mcp.client import MCPClient
from devassist.mcp.registry import MCPRegistry, MCPServerConfig

__all__ = ["MCPClient", "MCPRegistry", "MCPServerConfig"]
