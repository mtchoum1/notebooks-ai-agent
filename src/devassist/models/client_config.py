"""Unified CLI / SDK client configuration (ClientConfig)."""

from __future__ import annotations

import os
import warnings
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, field_validator, model_validator

from devassist.models.context import SourceType


def _cfg_logger() -> Any:
    """Resolve logger at call time so tests can patch ``devassist.models.config.logger``."""
    import devassist.models.config as cfg

    return cfg.logger

_AI_ALIASES: dict[str, str] = {
    "opus 4": "claude-opus-4-1@20250805",
    "opus 4.5": "claude-opus-4-5@20251101",
    "sonnet": "claude-sonnet-4-5@20250929",
    "fast": "claude-sonnet-4-5@20250929",
    "best": "claude-opus-4-5@20251101",
}

_DEFAULT_TECHNICAL_MODEL = "claude-sonnet-4@20250514"


def _normalize_ai_model_input(v: Any) -> str:
    if v is None:
        return "Sonnet 4"
    s = str(v).strip()
    low = s.lower()
    if low == "sonnet 4":
        return "Sonnet 4"
    if low in _AI_ALIASES:
        return _AI_ALIASES[low]
    if s.startswith("claude-"):
        return s
    _cfg_logger().warning("Unknown AI model name: %s — using default", s)
    return _DEFAULT_TECHNICAL_MODEL


def _to_resolved_technical(ai_model: str) -> str:
    if ai_model.startswith("claude-"):
        return ai_model
    low = ai_model.strip().lower()
    if low == "sonnet 4":
        return "claude-sonnet-4-5@20250929"
    if low in _AI_ALIASES:
        return _AI_ALIASES[low]
    return _DEFAULT_TECHNICAL_MODEL


class ClientConfig(BaseModel):
    """Unified configuration for Claude client, CLI, and runner."""

    workspace_dir: Path = Field(default_factory=lambda: Path.home() / ".devassist")
    ai_model: str = Field(default="Sonnet 4")
    ai_timeout_seconds: int = Field(default=60)
    output_format: Literal["json", "markdown"] = "markdown"
    permission_mode: str = "bypassPermissions"
    session_id: str | None = None
    session_auto_resume: bool = False
    priority_keywords: list[str] = Field(default_factory=list)
    sources: str | list[str] | list[SourceType] | None = None
    source_configs: dict[str, Any] = Field(default_factory=dict)
    system_prompt: str | None = None

    _resolved_sources_cache: list[SourceType] | None = PrivateAttr(default=None)

    @field_validator("workspace_dir", mode="before")
    @classmethod
    def _expand_workspace(cls, v: Any) -> Path:
        if v is None:
            return Path.home() / ".devassist"
        return Path(v).expanduser()

    @field_validator("ai_model", mode="before")
    @classmethod
    def _ai_model_normalize(cls, v: Any) -> str:
        return _normalize_ai_model_input(v)

    @field_validator("ai_timeout_seconds", mode="before")
    @classmethod
    def _clamp_timeout(cls, v: Any) -> int:
        if v is None:
            return 60
        try:
            n = int(v)
        except (TypeError, ValueError):
            return 60
        return max(10, min(600, n))

    @field_validator("output_format", mode="before")
    @classmethod
    def _fmt(cls, v: Any) -> str:
        if v in ("json", "markdown"):
            return v
        _cfg_logger().warning("Invalid output format: %s — using markdown", v)
        return "markdown"

    @field_validator("permission_mode", mode="before")
    @classmethod
    def _perm(cls, v: Any) -> str:
        if v in ("plan", "bypassPermissions"):
            return v
        _cfg_logger().warning("Invalid permission mode: %s — using bypassPermissions", v)
        return "bypassPermissions"

    @model_validator(mode="after")
    def _session_and_resolved_sources(self) -> ClientConfig:
        if self.session_id is not None and self.session_auto_resume:
            raise ValueError("Cannot specify both session_id and session_auto_resume")
        object.__setattr__(self, "_resolved_sources_cache", self._compute_resolved_sources())
        return self

    def _compute_resolved_sources(self) -> list[SourceType]:
        if self.sources is None or self.sources == "" or self.sources == []:
            return list(self.get_available_sources())
        raw: list[str]
        if isinstance(self.sources, str):
            raw = [p.strip() for p in self.sources.split(",") if p.strip()]
        elif isinstance(self.sources, list):
            raw = [s.value if isinstance(s, SourceType) else str(s).strip() for s in self.sources]
        else:
            raw = []
        out: list[SourceType] = []
        for name in raw:
            try:
                out.append(SourceType(name.lower()))
            except ValueError:
                _cfg_logger().warning("Unknown source type: %s" % name)
        return out

    @property
    def resolved_ai_model(self) -> str:
        return _to_resolved_technical(self.ai_model)

    @property
    def resolved_sources(self) -> list[SourceType]:
        assert self._resolved_sources_cache is not None
        return self._resolved_sources_cache

    @property
    def enabled_sources(self) -> list[SourceType]:
        resolved = self.resolved_sources
        enabled: list[SourceType] = []
        for st in resolved:
            cfg = self.source_configs.get(st.value, {})
            if cfg.get("enabled", True):
                enabled.append(st)
        return enabled

    @property
    def resolved_system_prompt(self) -> str:
        # Import inside property so ``patch('devassist.models.config.get_system_prompt')`` applies.
        from devassist.models.config import get_system_prompt as _load_prompt

        if self.system_prompt is None:
            return _load_prompt()
        p = Path(self.system_prompt).expanduser()
        if ("/" in self.system_prompt or self.system_prompt.startswith("~")) and p.suffix == ".md":
            if p.is_file():
                return p.read_text(encoding="utf-8")
            return _load_prompt()
        if p.is_file():
            return p.read_text(encoding="utf-8")
        return self.system_prompt

    @staticmethod
    def get_available_sources() -> list[SourceType]:
        try:
            from devassist.resources import get_mcp_servers_config

            cfg = get_mcp_servers_config()
            names = {k.lower() for k in cfg}
            result: list[SourceType] = []
            for st in SourceType:
                if st.value in names:
                    result.append(st)
            return result if result else list(SourceType)
        except Exception:
            return list(SourceType)

    @classmethod
    def from_cli_args(
        cls,
        *,
        sources: str | None = None,
        model: str | None = None,
        timeout: int | None = None,
        output_format: str | None = None,
        session_id: str | None = None,
        resume: bool = False,
        system_prompt: str | None = None,
        workspace_dir: Path | str | None = None,
    ) -> ClientConfig:
        env_model = os.environ.get("DEVASSIST_AI_MODEL")
        env_timeout = os.environ.get("DEVASSIST_AI_TIMEOUT_SECONDS")
        env_sources = os.environ.get("DEVASSIST_SOURCES")

        wd = Path(workspace_dir).expanduser() if workspace_dir else Path.home() / ".devassist"
        file_data: dict[str, Any] = {}
        cfg_path = wd / "config.yaml"
        if cfg_path.is_file():
            with open(cfg_path, encoding="utf-8") as f:
                file_data = yaml.safe_load(f) or {}

        raw_sources = file_data.get("sources")
        if isinstance(raw_sources, dict):
            # Legacy shape: ``sources: { github: {...} }`` — treat as source_configs only.
            merged_sources: str | list[str] | list[SourceType] | None = None
            extra_cfg = dict(raw_sources)
        else:
            merged_sources = raw_sources
            extra_cfg = {}

        merged: dict[str, Any] = {
            "workspace_dir": wd,
            "ai_model": file_data.get("ai_model", "Sonnet 4"),
            "ai_timeout_seconds": file_data.get("ai_timeout_seconds", 60),
            "source_configs": {**dict(file_data.get("source_configs", {})), **extra_cfg},
            "sources": merged_sources,
        }
        if file_data.get("output_format"):
            merged["output_format"] = file_data["output_format"]

        if model is not None:
            merged["ai_model"] = model
        elif env_model:
            merged["ai_model"] = env_model
        if timeout is not None:
            merged["ai_timeout_seconds"] = timeout
        elif env_timeout:
            merged["ai_timeout_seconds"] = int(env_timeout)
        if output_format is not None:
            merged["output_format"] = output_format
        if session_id is not None:
            merged["session_id"] = session_id
        if resume:
            merged["session_auto_resume"] = True
        if system_prompt is not None:
            merged["system_prompt"] = system_prompt
        if sources is not None:
            merged["sources"] = sources
        elif env_sources:
            merged["sources"] = env_sources

        return cls(**merged)

    @staticmethod
    def load_from_file(workspace_dir: Path) -> dict[str, Any]:
        path = Path(workspace_dir).expanduser() / "config.yaml"
        if not path.is_file():
            return {}
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data if isinstance(data, dict) else {}

    def save_to_file(self) -> None:
        path = Path(self.workspace_dir).expanduser() / "config.yaml"
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "ai_model": self.resolved_ai_model,
            "sources": [s.value for s in self.resolved_sources],
            "ai_timeout_seconds": self.ai_timeout_seconds,
        }
        with open(path, "w", encoding="utf-8") as f:
            yaml.safe_dump(payload, f, default_flow_style=False)

    @classmethod
    def from_legacy_config(cls, data: dict[str, Any]) -> ClientConfig:
        warnings.warn(
            "from_legacy_config is deprecated",
            DeprecationWarning,
            stacklevel=2,
        )
        wd = data.get("workspace_dir", "~/.devassist")
        return cls(
            workspace_dir=Path(wd).expanduser(),
            ai_model=_normalize_ai_model_input(data.get("ai", {}).get("model", "Sonnet 4")),
            ai_timeout_seconds=int(data.get("ai", {}).get("timeout_seconds", 60)),
            source_configs=data.get("sources", {}),
        )

    model_config = ConfigDict(extra="ignore")
