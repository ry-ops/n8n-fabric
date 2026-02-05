"""MCP Server for n8n-fabric with full n8n API access."""

import asyncio
import json
import os
from typing import Any, Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from n8n_fabric.mcp.n8n_client import N8nClient

# Tool definitions
TOOLS = [
    # ========== Workflow Tools ==========
    Tool(
        name="workflow_list",
        description="List all n8n workflows with metadata",
        inputSchema={
            "type": "object",
            "properties": {
                "active": {"type": "boolean", "description": "Filter by active status"},
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Filter by tags",
                },
                "limit": {"type": "integer", "default": 100},
            },
        },
    ),
    Tool(
        name="workflow_get",
        description="Get a workflow by ID (returns full workflow JSON)",
        inputSchema={
            "type": "object",
            "properties": {
                "workflow_id": {"type": "string", "description": "Workflow ID"},
            },
            "required": ["workflow_id"],
        },
    ),
    Tool(
        name="workflow_create",
        description="Create a new workflow from JSON definition",
        inputSchema={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Workflow name"},
                "nodes": {"type": "array", "description": "Array of node definitions"},
                "connections": {"type": "object", "description": "Node connections"},
                "settings": {"type": "object", "description": "Workflow settings"},
            },
            "required": ["name", "nodes"],
        },
    ),
    Tool(
        name="workflow_update",
        description="Update an existing workflow",
        inputSchema={
            "type": "object",
            "properties": {
                "workflow_id": {"type": "string", "description": "Workflow ID"},
                "workflow": {"type": "object", "description": "Updated workflow definition"},
            },
            "required": ["workflow_id", "workflow"],
        },
    ),
    Tool(
        name="workflow_delete",
        description="Delete a workflow",
        inputSchema={
            "type": "object",
            "properties": {
                "workflow_id": {"type": "string", "description": "Workflow ID"},
            },
            "required": ["workflow_id"],
        },
    ),
    Tool(
        name="workflow_activate",
        description="Activate a workflow",
        inputSchema={
            "type": "object",
            "properties": {
                "workflow_id": {"type": "string", "description": "Workflow ID"},
            },
            "required": ["workflow_id"],
        },
    ),
    Tool(
        name="workflow_deactivate",
        description="Deactivate a workflow",
        inputSchema={
            "type": "object",
            "properties": {
                "workflow_id": {"type": "string", "description": "Workflow ID"},
            },
            "required": ["workflow_id"],
        },
    ),
    Tool(
        name="workflow_execute",
        description="Execute a workflow manually with optional input data",
        inputSchema={
            "type": "object",
            "properties": {
                "workflow_id": {"type": "string", "description": "Workflow ID"},
                "data": {"type": "object", "description": "Input data for execution"},
            },
            "required": ["workflow_id"],
        },
    ),
    # ========== Execution Tools ==========
    Tool(
        name="execution_list",
        description="List workflow executions",
        inputSchema={
            "type": "object",
            "properties": {
                "workflow_id": {"type": "string", "description": "Filter by workflow ID"},
                "status": {
                    "type": "string",
                    "enum": ["success", "error", "running", "waiting"],
                    "description": "Filter by status",
                },
                "limit": {"type": "integer", "default": 100},
            },
        },
    ),
    Tool(
        name="execution_get",
        description="Get execution details including input/output data",
        inputSchema={
            "type": "object",
            "properties": {
                "execution_id": {"type": "string", "description": "Execution ID"},
                "include_data": {"type": "boolean", "default": True},
            },
            "required": ["execution_id"],
        },
    ),
    Tool(
        name="execution_delete",
        description="Delete an execution",
        inputSchema={
            "type": "object",
            "properties": {
                "execution_id": {"type": "string", "description": "Execution ID"},
            },
            "required": ["execution_id"],
        },
    ),
    Tool(
        name="execution_retry",
        description="Retry a failed execution",
        inputSchema={
            "type": "object",
            "properties": {
                "execution_id": {"type": "string", "description": "Execution ID"},
            },
            "required": ["execution_id"],
        },
    ),
    Tool(
        name="execution_stop",
        description="Stop a running execution",
        inputSchema={
            "type": "object",
            "properties": {
                "execution_id": {"type": "string", "description": "Execution ID"},
            },
            "required": ["execution_id"],
        },
    ),
    # ========== Credential Tools ==========
    Tool(
        name="credential_list",
        description="List credentials (names and types only, no secrets)",
        inputSchema={
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "default": 100},
            },
        },
    ),
    Tool(
        name="credential_create",
        description="Create a new credential",
        inputSchema={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Credential name"},
                "type": {"type": "string", "description": "Credential type"},
                "data": {"type": "object", "description": "Credential data"},
            },
            "required": ["name", "type", "data"],
        },
    ),
    Tool(
        name="credential_delete",
        description="Delete a credential",
        inputSchema={
            "type": "object",
            "properties": {
                "credential_id": {"type": "string", "description": "Credential ID"},
            },
            "required": ["credential_id"],
        },
    ),
    Tool(
        name="credential_schema",
        description="Get the schema for a credential type",
        inputSchema={
            "type": "object",
            "properties": {
                "credential_type": {"type": "string", "description": "Credential type name"},
            },
            "required": ["credential_type"],
        },
    ),
    # ========== Tag Tools ==========
    Tool(
        name="tag_list",
        description="List all tags",
        inputSchema={
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "default": 100},
            },
        },
    ),
    Tool(
        name="tag_create",
        description="Create a new tag",
        inputSchema={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Tag name"},
            },
            "required": ["name"],
        },
    ),
    Tool(
        name="tag_delete",
        description="Delete a tag",
        inputSchema={
            "type": "object",
            "properties": {
                "tag_id": {"type": "string", "description": "Tag ID"},
            },
            "required": ["tag_id"],
        },
    ),
    # ========== Variable Tools ==========
    Tool(
        name="variable_list",
        description="List all variables",
        inputSchema={
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "default": 100},
            },
        },
    ),
    Tool(
        name="variable_get",
        description="Get a variable by ID",
        inputSchema={
            "type": "object",
            "properties": {
                "variable_id": {"type": "string", "description": "Variable ID"},
            },
            "required": ["variable_id"],
        },
    ),
    Tool(
        name="variable_create",
        description="Create a new variable",
        inputSchema={
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Variable key"},
                "value": {"type": "string", "description": "Variable value"},
            },
            "required": ["key", "value"],
        },
    ),
    Tool(
        name="variable_delete",
        description="Delete a variable",
        inputSchema={
            "type": "object",
            "properties": {
                "variable_id": {"type": "string", "description": "Variable ID"},
            },
            "required": ["variable_id"],
        },
    ),
    # ========== Project Tools ==========
    Tool(
        name="project_list",
        description="List all projects",
        inputSchema={
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "default": 100},
            },
        },
    ),
    Tool(
        name="project_create",
        description="Create a new project",
        inputSchema={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Project name"},
            },
            "required": ["name"],
        },
    ),
    Tool(
        name="project_delete",
        description="Delete a project",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {"type": "string", "description": "Project ID"},
            },
            "required": ["project_id"],
        },
    ),
    # ========== User Tools ==========
    Tool(
        name="user_list",
        description="List all users",
        inputSchema={
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "default": 100},
            },
        },
    ),
    # ========== Community Nodes ==========
    Tool(
        name="community_node_list",
        description="List installed community node packages",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="community_node_install",
        description="Install a community node package",
        inputSchema={
            "type": "object",
            "properties": {
                "package_name": {"type": "string", "description": "npm package name"},
            },
            "required": ["package_name"],
        },
    ),
    Tool(
        name="community_node_uninstall",
        description="Uninstall a community node package",
        inputSchema={
            "type": "object",
            "properties": {
                "package_name": {"type": "string", "description": "npm package name"},
            },
            "required": ["package_name"],
        },
    ),
    # ========== Source Control ==========
    Tool(
        name="source_control_pull",
        description="Pull workflows from source control",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="source_control_push",
        description="Push workflows to source control",
        inputSchema={
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "Commit message"},
            },
        },
    ),
    Tool(
        name="source_control_status",
        description="Get source control status",
        inputSchema={"type": "object", "properties": {}},
    ),
    # ========== Audit & System ==========
    Tool(
        name="audit_logs",
        description="Get audit logs",
        inputSchema={
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "default": 100},
                "event_type": {"type": "string", "description": "Filter by event type"},
            },
        },
    ),
    Tool(
        name="n8n_status",
        description="Get n8n health status and version",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="fabric_status",
        description="Get full fabric status (n8n + Qdrant + Redis)",
        inputSchema={"type": "object", "properties": {}},
    ),
]


class N8nFabricMCP:
    """MCP Server for n8n-fabric."""

    def __init__(self):
        self.server = Server("n8n-fabric")
        self.n8n = N8nClient()
        self._setup_handlers()

    def _setup_handlers(self):
        """Set up MCP request handlers."""

        @self.server.list_tools()
        async def list_tools():
            return TOOLS

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict) -> list[TextContent]:
            try:
                result = await self._execute_tool(name, arguments)
                return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]
            except Exception as e:
                return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def _execute_tool(self, name: str, args: dict) -> Any:
        """Execute a tool and return the result."""
        # Workflow tools
        if name == "workflow_list":
            return self.n8n.workflow_list(
                active=args.get("active"),
                tags=args.get("tags"),
                limit=args.get("limit", 100),
            )
        elif name == "workflow_get":
            return self.n8n.workflow_get(args["workflow_id"])
        elif name == "workflow_create":
            workflow = {
                "name": args["name"],
                "nodes": args.get("nodes", []),
                "connections": args.get("connections", {}),
                "settings": args.get("settings", {}),
            }
            return self.n8n.workflow_create(workflow)
        elif name == "workflow_update":
            return self.n8n.workflow_update(args["workflow_id"], args["workflow"])
        elif name == "workflow_delete":
            return self.n8n.workflow_delete(args["workflow_id"])
        elif name == "workflow_activate":
            return self.n8n.workflow_activate(args["workflow_id"])
        elif name == "workflow_deactivate":
            return self.n8n.workflow_deactivate(args["workflow_id"])
        elif name == "workflow_execute":
            return self.n8n.workflow_execute(args["workflow_id"], args.get("data"))

        # Execution tools
        elif name == "execution_list":
            return self.n8n.execution_list(
                workflow_id=args.get("workflow_id"),
                status=args.get("status"),
                limit=args.get("limit", 100),
            )
        elif name == "execution_get":
            return self.n8n.execution_get(
                args["execution_id"],
                include_data=args.get("include_data", True),
            )
        elif name == "execution_delete":
            return self.n8n.execution_delete(args["execution_id"])
        elif name == "execution_retry":
            return self.n8n.execution_retry(args["execution_id"])
        elif name == "execution_stop":
            return self.n8n.execution_stop(args["execution_id"])

        # Credential tools
        elif name == "credential_list":
            return self.n8n.credential_list(limit=args.get("limit", 100))
        elif name == "credential_create":
            return self.n8n.credential_create({
                "name": args["name"],
                "type": args["type"],
                "data": args["data"],
            })
        elif name == "credential_delete":
            return self.n8n.credential_delete(args["credential_id"])
        elif name == "credential_schema":
            return self.n8n.credential_schema(args["credential_type"])

        # Tag tools
        elif name == "tag_list":
            return self.n8n.tag_list(limit=args.get("limit", 100))
        elif name == "tag_create":
            return self.n8n.tag_create(args["name"])
        elif name == "tag_delete":
            return self.n8n.tag_delete(args["tag_id"])

        # Variable tools
        elif name == "variable_list":
            return self.n8n.variable_list(limit=args.get("limit", 100))
        elif name == "variable_get":
            return self.n8n.variable_get(args["variable_id"])
        elif name == "variable_create":
            return self.n8n.variable_create(args["key"], args["value"])
        elif name == "variable_delete":
            return self.n8n.variable_delete(args["variable_id"])

        # Project tools
        elif name == "project_list":
            return self.n8n.project_list(limit=args.get("limit", 100))
        elif name == "project_create":
            return self.n8n.project_create(args["name"])
        elif name == "project_delete":
            return self.n8n.project_delete(args["project_id"])

        # User tools
        elif name == "user_list":
            return self.n8n.user_list(limit=args.get("limit", 100))

        # Community nodes
        elif name == "community_node_list":
            return self.n8n.community_node_list()
        elif name == "community_node_install":
            return self.n8n.community_node_install(args["package_name"])
        elif name == "community_node_uninstall":
            return self.n8n.community_node_uninstall(args["package_name"])

        # Source control
        elif name == "source_control_pull":
            return self.n8n.source_control_pull()
        elif name == "source_control_push":
            return self.n8n.source_control_push(args.get("message"))
        elif name == "source_control_status":
            return self.n8n.source_control_status()

        # Audit & system
        elif name == "audit_logs":
            return self.n8n.audit_logs(
                limit=args.get("limit", 100),
                event_type=args.get("event_type"),
            )
        elif name == "n8n_status":
            health = self.n8n.health()
            try:
                version = self.n8n.version()
            except Exception:
                version = {"version": "unknown"}
            return {"health": health, "version": version}
        elif name == "fabric_status":
            return self._get_fabric_status()

        else:
            raise ValueError(f"Unknown tool: {name}")

    def _get_fabric_status(self) -> dict:
        """Get status of all fabric components."""
        status = {
            "n8n": self.n8n.health(),
            "qdrant": {"healthy": False},
            "redis": {"healthy": False},
        }

        # Check Qdrant
        try:
            import httpx
            qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
            response = httpx.get(f"{qdrant_url}/healthz", timeout=5.0)
            status["qdrant"] = {"healthy": response.status_code == 200}
        except Exception as e:
            status["qdrant"] = {"healthy": False, "error": str(e)}

        # Check Redis
        try:
            import redis
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
            r = redis.from_url(redis_url)
            r.ping()
            status["redis"] = {"healthy": True}
        except Exception as e:
            status["redis"] = {"healthy": False, "error": str(e)}

        return status

    async def run(self):
        """Run the MCP server."""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(read_stream, write_stream, self.server.create_initialization_options())


def main():
    """Entry point for MCP server."""
    mcp = N8nFabricMCP()
    asyncio.run(mcp.run())


if __name__ == "__main__":
    main()
