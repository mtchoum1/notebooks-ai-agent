# Implementation Plan: Developer Assistant CLI

**Branch**: `python-cli` | **Date**: 2026-01-27 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-dev-assistant-cli/spec.md`

## Summary

A Python CLI application that aggregates context from multiple developer tools (Gmail, Slack, JIRA, GitHub) and uses GCP Vertex AI (Gemini) to generate a Unified Morning Brief and other productivity features. Built with Typer/Click for CLI, using a modular adapter pattern for context sources, with local file-based caching and configuration.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: Typer (CLI), httpx (async HTTP), google-cloud-aiplatform (Vertex AI), pydantic (data models), rich (terminal output)
**Storage**: Local JSON/YAML files for config and cache (unencrypted, dev mode)
**Testing**: pytest with pytest-asyncio, pytest-mock
**Target Platform**: Linux/macOS/Windows CLI
**Project Type**: Single Python package with CLI entrypoint
**Performance Goals**: Morning brief generation < 60 seconds for 4 sources
**Constraints**: 15-minute cache TTL, graceful degradation on source failures
**Scale/Scope**: Single user, 4 MVP context sources, local execution

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| Library-First | PASS | Core services separated from CLI layer |
| CLI Interface | PASS | Typer-based CLI with JSON + human-readable output |
| Test-First | PASS | pytest with unit/integration test structure |
| Integration Testing | PASS | Contract tests for each context source adapter |
| Simplicity | PASS | Minimal dependencies, no over-engineering |

**Gate Status**: PASSED - No violations requiring justification.

## Project Structure

### Documentation (this feature)

```text
specs/001-dev-assistant-cli/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── context-source.md
│   └── ai-service.md
└── checklists/
    └── requirements.md
```

### Source Code (repository root)

```text
src/
├── devassist/
│   ├── __init__.py
│   ├── cli/
│   │   ├── __init__.py
│   │   ├── main.py          # Typer app entrypoint
│   │   ├── brief.py         # brief command
│   │   ├── config.py        # config commands
│   │   └── sandbox.py       # EC2 sandbox commands
│   ├── core/
│   │   ├── __init__.py
│   │   ├── brief_service.py # Morning brief orchestration
│   │   ├── config_manager.py
│   │   └── cache_manager.py
│   ├── adapters/
│   │   ├── __init__.py
│   │   ├── base.py          # Abstract ContextSource
│   │   ├── gmail.py         # Gmail adapter
│   │   ├── slack.py         # Slack adapter
│   │   ├── jira.py          # JIRA adapter
│   │   └── github.py        # GitHub adapter
│   ├── ai/
│   │   ├── __init__.py
│   │   ├── vertex_client.py # Vertex AI Gemini client
│   │   └── prompts.py       # Prompt templates
│   └── models/
│       ├── __init__.py
│       ├── context.py       # ContextItem, ContextSource
│       ├── config.py        # Configuration models
│       └── brief.py         # Brief, BriefItem

tests/
├── unit/
│   ├── test_brief_service.py
│   ├── test_config_manager.py
│   └── test_cache_manager.py
├── integration/
│   ├── test_gmail_adapter.py
│   ├── test_slack_adapter.py
│   ├── test_jira_adapter.py
│   └── test_github_adapter.py
└── contract/
    └── test_context_source_contract.py

pyproject.toml
README.md
```

**Structure Decision**: Single Python package with clear separation between CLI layer (`cli/`), core services (`core/`), external integrations (`adapters/`), and AI integration (`ai/`). This enables future UI additions by reusing the core services.

## Complexity Tracking

No violations requiring justification.

## Implementation Phases

### Phase 0: Research (Complete)
See [research.md](./research.md)

### Phase 1: Design & Contracts (Complete)
See [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

### Phase 2: Task Generation
Run `/speckit.tasks` to generate actionable task list.

### Phase 3: Implementation
Run `/speckit.implement` to execute tasks.
