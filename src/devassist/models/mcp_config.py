"""MCP Server configuration models for DevAssist."""

import logging
import os
from typing import Any

from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


class McpServerConfig(BaseModel):
    """MCP Server configuration with environment variable resolution."""

    type: str = Field(default="stdio", description="MCP server type")
    command: str = Field(..., description="Command to run the MCP server")
    args: list[str] = Field(default_factory=list, description="Command arguments")
    description: str = Field(default="", description="Server description")
    env: dict[str, str] = Field(default_factory=dict, description="Environment variables")

    @field_validator("env", mode="before")
    @classmethod
    def resolve_env_variables(cls, v: dict[str, str]) -> dict[str, str]:
        """Resolve environment variables for empty values.

        If a value is empty, fetch it from os.environ using the key name.
        Supports default values for specific variables.

        Args:
            v: Dictionary of environment variables

        Returns:
            Dictionary with resolved environment variables
        """
        if not isinstance(v, dict):
            return v

        # Default values for common environment variables
        defaults = {
            "CONFLUENCE_URL": "https://issues.redhat.com",
            "JIRA_SSL_VERIFY": "false",
            "CONFLUENCE_SSL_VERIFY": "false",
            "JIRA_URL": "https://issues.redhat.com"
        }

        resolved_env = {}
        for key, value in v.items():
            if not value:  # Empty string or None
                # Try to get value from environment
                env_value = os.getenv(key)
                if env_value:
                    resolved_env[key] = env_value
                    logger.debug(f"Resolved {key} from environment: ✓")
                else:
                    # Use default if available
                    default_value = defaults.get(key, "")
                    resolved_env[key] = default_value
                    logger.debug(f"Resolved {key} to default: {'✓' if default_value else '✗'}")
                if not resolved_env[key]:
                    logger.warning("MCP env variable %s is missing; using empty string", key)
                    resolved_env[key] = ""
            elif value.startswith("${") and value.endswith("}"):
                # Handle placeholder syntax like ${JIRA_URL}
                env_var_name = value[2:-1]  # Remove ${ and }
                env_value = os.getenv(env_var_name)
                if env_value:
                    resolved_env[key] = env_value
                    logger.debug(f"Resolved {key} from placeholder ${env_var_name}: ✓")
                else:
                    # Use default if available for the env var name
                    default_value = defaults.get(env_var_name, "")
                    resolved_env[key] = default_value
                    logger.debug(f"Resolved {key} placeholder ${env_var_name} to default: {'✓' if default_value else '✗'}")
            else:
                resolved_env[key] = value

        return resolved_env


def expand_env_vars(obj: Any) -> Any:
    """Recursively expand ``${VAR}`` placeholders in strings (see unit tests)."""
    import re

    if isinstance(obj, str):

        def _repl(match: re.Match[str]) -> str:
            return os.environ.get(match.group(1), "")

        return re.sub(r"\$\{([^}]+)\}", _repl, obj)
    if isinstance(obj, dict):
        return {k: expand_env_vars(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [expand_env_vars(i) for i in obj]
    return obj


class ClaudeConfig(BaseModel):
    """Claude API settings under ``.mcp.json`` / MCPConfig."""

    api_key: str | None = None
    model: str = "claude-sonnet-4-5-20250929"
    max_tokens: int = 4096
    temperature: float = 0.7


class VertexConfig(BaseModel):
    """Vertex AI settings under MCPConfig."""

    api_key: str | None = None
    project_id: str = ""
    location: str = "us-central1"
    model: str = "gemini-2.5-flash"


class AIProviderConfig(BaseModel):
    """AI provider block."""

    provider: str = "claude"
    claude: ClaudeConfig = Field(default_factory=ClaudeConfig)
    vertex: VertexConfig = Field(default_factory=VertexConfig)

    @field_validator("provider")
    @classmethod
    def _provider(cls, v: str) -> str:
        if v not in ("claude", "vertex"):
            raise ValueError("provider must be 'claude' or 'vertex'")
        return v


class RunnerConfig(BaseModel):
    """Background runner block in MCP configuration."""

    enabled: bool = False
    interval_minutes: int = 5
    prompt: str = "Review my context and summarize urgent items."
    last_run: Any = None
    status: str = "stopped"
    last_error: Any = None
    output_destination: str = "~/.devassist/runner-output.md"
    notify_on_completion: bool = False
    sources: list[str] = Field(default_factory=list)

    @field_validator("status")
    @classmethod
    def _status(cls, v: str) -> str:
        if v not in ("stopped", "running"):
            raise ValueError("invalid runner status")
        return v


class MCPConfig(BaseModel):
    """Top-level MCP + AI + runner configuration."""

    version: str = "1.0"
    mcp_servers: dict[str, Any] = Field(default_factory=dict)
    ai: AIProviderConfig = Field(default_factory=AIProviderConfig)
    runner: RunnerConfig = Field(default_factory=RunnerConfig)
    sources: dict[str, Any] = Field(default_factory=dict)


# Alias expected by unit tests (capital MCP)
MCPServerConfig = McpServerConfig