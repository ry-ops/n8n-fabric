# Fabric Coordination Guide

How to wire n8n-fabric, git-steer, and aiana MCP servers together.

## Overview

The ry-ops fabric ecosystem consists of three independent MCP servers that can work together:

| Fabric | Port/Transport | Role |
|--------|----------------|------|
| **n8n-fabric** | stdio | Workflow execution, playbooks |
| **git-steer** | stdio | Repo lifecycle, version control |
| **aiana** | stdio | Semantic memory, pattern recall |

## Claude Desktop Configuration

Add all three fabrics to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "n8n-fabric": {
      "command": "uv",
      "args": ["run", "n8n-fabric-mcp"],
      "cwd": "/path/to/n8n-fabric",
      "env": {
        "N8N_URL": "http://localhost:5678",
        "N8N_API_KEY": "your-api-key",
        "QDRANT_URL": "http://localhost:6343",
        "REDIS_URL": "redis://localhost:6389"
      }
    },
    "git-steer": {
      "command": "node",
      "args": ["/path/to/git-steer/dist/index.js", "start", "--stdio"]
    },
    "aiana": {
      "command": "uv",
      "args": ["run", "aiana", "mcp"],
      "cwd": "/path/to/aiana"
    }
  }
}
```

## Cross-Fabric Operations

With all three fabrics connected, you can perform coordinated operations:

### Recall and Execute

```
User: "Run my Slack notification workflow"

Flow:
1. aiana → memory_search("Slack notification workflow")
2. aiana returns: workflow_id = "abc123"
3. n8n-fabric → workflow_execute(workflow_id="abc123")
4. Result returned to user
```

### Create and Commit

```
User: "Create a webhook-to-Slack workflow and save it to the automation repo"

Flow:
1. n8n-fabric → workflow_create({name: "Webhook to Slack", nodes: [...], connections: {...}})
2. n8n-fabric returns: workflow created with id "xyz789"
3. n8n-fabric → workflow_get("xyz789") to get full JSON
4. git-steer → repo_commit({
     owner: "ry-ops",
     repo: "automation-workflows",
     files: [{path: "workflows/webhook-to-slack.json", content: workflow_json}],
     message: "Add webhook to Slack workflow"
   })
5. aiana → memory_add("Created webhook-to-Slack workflow in automation-workflows repo")
```

### Playbook Discovery

```
User: "What deployment workflows have I built?"

Flow:
1. aiana → memory_search("deployment workflow")
2. aiana returns: patterns mentioning deployments
3. n8n-fabric → workflow_search("deployment") (semantic search in Qdrant)
4. Combined results returned to user
```

## Environment Setup

### Prerequisites

1. **Docker** - For running n8n stack
2. **Node.js 22+** - For git-steer
3. **Python 3.10+ with uv** - For n8n-fabric and aiana
4. **GitHub App** - For git-steer authentication

### Start All Services

```bash
# Terminal 1: n8n-fabric Docker stack
cd /path/to/n8n-fabric
docker compose up -d

# Verify services
curl http://localhost:5678/healthz  # n8n
curl http://localhost:6343/healthz  # Qdrant
docker exec n8n-fabric-redis redis-cli ping  # Redis

# Terminal 2: Install n8n-fabric
cd /path/to/n8n-fabric
uv sync

# Terminal 3: Verify git-steer
cd /path/to/git-steer
npm install
npx git-steer status

# Terminal 4: Verify aiana
cd /path/to/aiana
uv sync
uv run aiana status
```

### Generate n8n API Key

1. Open n8n UI: http://localhost:5678
2. Create owner account on first run
3. Go to Settings → API → Create API Key
4. Add key to your environment or Claude config

## Tool Reference

### n8n-fabric Tools

| Tool | Description |
|------|-------------|
| `workflow_list` | List all workflows |
| `workflow_get` | Get workflow by ID |
| `workflow_create` | Create workflow |
| `workflow_execute` | Execute workflow |
| `workflow_search` | Semantic search |
| `execution_list` | List executions |
| `execution_retry` | Retry failed execution |
| `credential_list` | List credentials |
| `fabric_status` | Health check |

### git-steer Tools

| Tool | Description |
|------|-------------|
| `repo_list` | List repositories |
| `repo_commit` | Commit files |
| `repo_read_file` | Read file from repo |
| `security_scan` | Scan for vulnerabilities |
| `steer_status` | Health check |

### aiana Tools

| Tool | Description |
|------|-------------|
| `memory_search` | Semantic memory search |
| `memory_add` | Add memory |
| `memory_recall` | Get project context |
| `session_list` | List sessions |
| `aiana_status` | Health check |

## Troubleshooting

### n8n API 401 Unauthorized

- Verify `N8N_API_KEY` is set correctly
- Regenerate API key in n8n UI

### Qdrant Connection Refused

- Check Docker: `docker compose ps`
- Verify port: `curl http://localhost:6343/healthz`

### Redis Connection Failed

- Check container: `docker exec n8n-fabric-redis redis-cli ping`
- Verify port 6389 is not blocked

### git-steer Authentication Failed

- Run `npx git-steer status` to check credentials
- Re-run `npx git-steer init` if needed
