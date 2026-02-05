# CLAUDE.md - n8n-fabric

## Project Overview

n8n-fabric is a workflow automation fabric layer that wraps n8n with:
- **MCP Server** - Full API access to n8n workflows, executions, credentials
- **Qdrant** - Vector storage for workflow pattern recognition and semantic search
- **Redis** - Caching, session state, workflow metadata

## Architecture

This is one of three fabric layers in the ry-ops ecosystem:
- **n8n-fabric** (this) - Workflow execution, playbooks, lesson plans
- **git-steer** - Repository lifecycle, version control orchestration
- **aiana** - Semantic memory, pattern recognition, context injection

Each fabric has its own MCP server and can operate independently or coordinate via MCP.

## Tech Stack

- **Python 3.10+** with uv for package management
- **n8n** - Workflow automation engine (Docker)
- **Qdrant** - Vector database for workflow embeddings
- **Redis** - Caching and session state
- **MCP** - Model Context Protocol for tool exposure

## Commands

```bash
# Install dependencies
uv sync

# Run MCP server
uv run n8n-fabric-mcp

# CLI commands
uv run n8n-fabric status
uv run n8n-fabric workflows list
uv run n8n-fabric workflows search "slack notification"
```

## Docker Stack

```bash
# Start full stack (n8n + Qdrant + Redis)
docker compose up -d

# Check status
docker compose ps
```

## MCP Tools

The MCP server exposes complete n8n API access:

### Workflow Management
- `workflow_list` - List all workflows
- `workflow_get` - Get workflow by ID
- `workflow_create` - Create new workflow
- `workflow_update` - Update workflow
- `workflow_delete` - Delete workflow
- `workflow_activate` - Activate workflow
- `workflow_deactivate` - Deactivate workflow
- `workflow_execute` - Execute workflow manually
- `workflow_search` - Semantic search across workflows (via Qdrant)

### Execution Management
- `execution_list` - List executions
- `execution_get` - Get execution details
- `execution_delete` - Delete execution
- `execution_retry` - Retry failed execution

### Credential Management
- `credential_list` - List credentials (names only, not secrets)
- `credential_create` - Create credential
- `credential_delete` - Delete credential

### Node Information
- `node_types` - List available node types
- `node_info` - Get node type details

### System
- `n8n_status` - n8n health and version
- `fabric_status` - Full fabric health (n8n + Qdrant + Redis)

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `N8N_URL` | n8n API URL | `http://localhost:5678` |
| `N8N_API_KEY` | n8n API key | (required) |
| `QDRANT_URL` | Qdrant URL | `http://localhost:6333` |
| `REDIS_URL` | Redis URL | `redis://localhost:6379` |

## File Structure

```
n8n-fabric/
├── src/n8n_fabric/
│   ├── mcp/           # MCP server implementation
│   ├── storage/       # Qdrant and Redis integrations
│   ├── workflows/     # Workflow embedding and search
│   └── cli.py         # CLI interface
├── docker-compose.yml # Full stack deployment
├── docs/decisions/    # ADR documents
└── assets/            # Architecture diagrams
```
