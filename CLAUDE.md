# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a LinkedIn-Microsoft Dynamics CRM synchronization system that uses MCP (Model Context Protocol) servers to integrate with both platforms. The project synchronizes LinkedIn contacts with Microsoft Dynamics CRM using their respective APIs.

## APIs and Integrations

- **LinkedIn**: Uses the Member Snapshot API from LinkedIn's Data Portability API
  - API Documentation: https://learn.microsoft.com/en-us/linkedin/dma/member-data-portability/shared/member-snapshot-api?view=li-dma-data-portability-2024-11&tabs=curl
- **Microsoft Dynamics CRM**: Uses the official Dynamics CRM Web API
- **MCP Framework**: Built using the official Python SDK from https://github.com/modelcontextprotocol/python-sdk

## Development Commands

- **Install dependencies**: `uv sync` (installs all dependencies including dev)
- **Run LinkedIn MCP server**: `uv run python -m mcp_servers.linkedin`
- **Run Dynamics CRM MCP server**: `uv run python -m mcp_servers.dynamics_crm`
- **Run CLI**: `uv run linkedin-sync --help`
- **Test connectivity**: `uv run python test_runner.py` or `uv run pytest tests/test_connectivity.py -v`
- **Test AI duplicate detection**: `uv run python test_ai_duplicate_detection.py`
- **Test AI synchronization**: `uv run python test_ai_sync.py`
- **CLI AI test**: `uv run linkedin-sync test-ai-detection`
- **Run all tests**: `uv run pytest`
- **Format code**: `uv run black .`
- **Lint code**: `uv run ruff check .`

## AI Duplicate Detection

The system includes AI-powered duplicate detection using PydanticAI and Ollama:

### Setup Requirements:
- **Ollama server**: Must be running locally (`ollama serve`)
- **Mistral model**: Install with `ollama pull mistral-small:24b`
- **Dependencies**: Install with `uv sync`

### AI Features:
- **Smart duplicate detection**: Compares LinkedIn contacts with CRM contacts using AI
- **Confidence scoring**: HIGH/MEDIUM/LOW confidence levels for matches  
- **Intelligent sync**: Automatically syncs safe contacts, flags others for review
- **Detailed reasoning**: AI provides explanations for its decisions

### CLI Commands with AI:
- **Sync with AI**: `uv run linkedin-sync sync-connections --ai-detection`
- **Auto-sync safe contacts**: `uv run linkedin-sync sync-connections --ai-detection --auto-sync`
- **Test AI**: `uv run linkedin-sync test-ai-detection`

## Project Structure

- `mcp_servers/` - Contains MCP server implementations
  - `linkedin/` - LinkedIn MCP server for Member Snapshot API
  - `dynamics_crm/` - Microsoft Dynamics CRM MCP server
- `sync/` - Synchronization logic between LinkedIn and Dynamics CRM
- `pyproject.toml` - Python project configuration with MCP SDK dependencies

## Architecture

The system uses two separate MCP servers:
1. **LinkedIn MCP Server**: Handles authentication and data retrieval from LinkedIn's Member Snapshot API
2. **Dynamics CRM MCP Server**: Manages connections and data operations with Microsoft Dynamics CRM
3. **Synchronization Layer**: Orchestrates data flow between the two systems

## Python Requirements

- Requires Python >=3.11 as specified in pyproject.toml
- Uses MCP Python SDK for server implementations