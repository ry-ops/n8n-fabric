"""CLI for n8n-fabric."""

import json

import click
from rich.console import Console
from rich.table import Table

from n8n_fabric.mcp.n8n_client import N8nClient
from n8n_fabric.storage.qdrant import WorkflowVectorStore
from n8n_fabric.storage.redis import WorkflowCache

console = Console()


@click.group()
def main():
    """n8n-fabric: Workflow automation fabric layer."""
    pass


@main.command()
def status():
    """Show fabric status."""
    console.print("[bold]n8n-fabric Status[/bold]\n")

    # Check n8n
    try:
        n8n = N8nClient()
        health = n8n.health()
        if health.get("healthy"):
            console.print("[green]n8n: healthy[/green]")
            try:
                version = n8n.version()
                console.print(f"  Version: {version.get('version', 'unknown')}")
            except Exception:
                pass
        else:
            console.print(f"[red]n8n: unhealthy[/red] - {health.get('error', '')}")
    except Exception as e:
        console.print(f"[red]n8n: error[/red] - {e}")

    # Check Qdrant
    try:
        qdrant = WorkflowVectorStore()
        if qdrant.health_check():
            stats = qdrant.get_stats()
            console.print(f"[green]Qdrant: healthy[/green]")
            console.print(f"  Workflows indexed: {stats.get('points_count', 0)}")
        else:
            console.print("[red]Qdrant: unhealthy[/red]")
    except Exception as e:
        console.print(f"[red]Qdrant: error[/red] - {e}")

    # Check Redis
    try:
        redis_cache = WorkflowCache()
        if redis_cache.health_check():
            stats = redis_cache.get_stats()
            console.print(f"[green]Redis: healthy[/green]")
            console.print(f"  Memory: {stats.get('used_memory', 'unknown')}")
            console.print(f"  Active workflows: {stats.get('active_workflows', 0)}")
        else:
            console.print("[red]Redis: unhealthy[/red]")
    except Exception as e:
        console.print(f"[red]Redis: error[/red] - {e}")


@main.group()
def workflows():
    """Workflow management commands."""
    pass


@workflows.command("list")
@click.option("--active", is_flag=True, help="Show only active workflows")
@click.option("--limit", default=50, help="Max workflows to show")
def workflows_list(active: bool, limit: int):
    """List all workflows."""
    n8n = N8nClient()
    result = n8n.workflow_list(active=active if active else None, limit=limit)

    table = Table(title="Workflows")
    table.add_column("ID", style="cyan")
    table.add_column("Name")
    table.add_column("Active", style="green")
    table.add_column("Nodes")
    table.add_column("Tags")

    for wf in result.get("data", []):
        tags = ", ".join([t.get("name", t) if isinstance(t, dict) else t for t in wf.get("tags", [])])
        table.add_row(
            wf.get("id", ""),
            wf.get("name", ""),
            "Yes" if wf.get("active") else "No",
            str(len(wf.get("nodes", []))),
            tags or "-",
        )

    console.print(table)


@workflows.command("get")
@click.argument("workflow_id")
def workflows_get(workflow_id: str):
    """Get workflow details."""
    n8n = N8nClient()
    result = n8n.workflow_get(workflow_id)
    console.print_json(json.dumps(result, indent=2))


@workflows.command("search")
@click.argument("query")
@click.option("--limit", default=10, help="Max results")
def workflows_search(query: str, limit: int):
    """Semantic search for workflows."""
    qdrant = WorkflowVectorStore()
    results = qdrant.search(query, limit=limit)

    table = Table(title=f"Search: '{query}'")
    table.add_column("ID", style="cyan")
    table.add_column("Name")
    table.add_column("Score", style="green")
    table.add_column("Nodes")
    table.add_column("Tags")

    for r in results:
        table.add_row(
            r.get("workflow_id", ""),
            r.get("name", ""),
            f"{r.get('score', 0):.3f}",
            str(r.get("node_count", 0)),
            ", ".join(r.get("tags", [])) or "-",
        )

    console.print(table)


@workflows.command("sync")
def workflows_sync():
    """Sync all workflows to Qdrant index."""
    n8n = N8nClient()
    qdrant = WorkflowVectorStore()

    result = n8n.workflow_list(limit=1000)
    workflows_data = result.get("data", [])

    console.print(f"Syncing {len(workflows_data)} workflows to Qdrant...")

    for wf in workflows_data:
        workflow_id = wf.get("id")
        full_wf = n8n.workflow_get(workflow_id)
        qdrant.index_workflow(full_wf, workflow_id)
        console.print(f"  Indexed: {wf.get('name', workflow_id)}")

    console.print(f"[green]Done! Indexed {len(workflows_data)} workflows.[/green]")


@main.group()
def executions():
    """Execution management commands."""
    pass


@executions.command("list")
@click.option("--workflow-id", help="Filter by workflow ID")
@click.option("--status", type=click.Choice(["success", "error", "running", "waiting"]))
@click.option("--limit", default=20)
def executions_list(workflow_id: str, status: str, limit: int):
    """List executions."""
    n8n = N8nClient()
    result = n8n.execution_list(workflow_id=workflow_id, status=status, limit=limit)

    table = Table(title="Executions")
    table.add_column("ID", style="cyan")
    table.add_column("Workflow")
    table.add_column("Status")
    table.add_column("Started")
    table.add_column("Finished")

    for ex in result.get("data", []):
        status_style = "green" if ex.get("status") == "success" else "red"
        table.add_row(
            ex.get("id", ""),
            ex.get("workflowId", ""),
            f"[{status_style}]{ex.get('status', '')}[/{status_style}]",
            ex.get("startedAt", "")[:19] if ex.get("startedAt") else "-",
            ex.get("stoppedAt", "")[:19] if ex.get("stoppedAt") else "-",
        )

    console.print(table)


if __name__ == "__main__":
    main()
