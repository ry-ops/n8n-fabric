"""Redis caching for n8n-fabric."""

import json
import os
from typing import Any, Optional

import redis


class WorkflowCache:
    """Redis cache for workflow metadata and execution state."""

    DEFAULT_TTL = 3600  # 1 hour

    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self.client = redis.from_url(self.redis_url, decode_responses=True)

    def _key(self, *parts: str) -> str:
        """Build a Redis key."""
        return ":".join(["n8n_fabric", *parts])

    # ========== Workflow Metadata Cache ==========

    def cache_workflow_meta(self, workflow_id: str, meta: dict, ttl: int = DEFAULT_TTL):
        """Cache workflow metadata."""
        key = self._key("workflow", workflow_id, "meta")
        self.client.setex(key, ttl, json.dumps(meta))

    def get_workflow_meta(self, workflow_id: str) -> Optional[dict]:
        """Get cached workflow metadata."""
        key = self._key("workflow", workflow_id, "meta")
        data = self.client.get(key)
        return json.loads(data) if data else None

    def invalidate_workflow(self, workflow_id: str):
        """Invalidate all cache entries for a workflow."""
        pattern = self._key("workflow", workflow_id, "*")
        keys = self.client.keys(pattern)
        if keys:
            self.client.delete(*keys)

    # ========== Execution Cache ==========

    def cache_execution(self, execution_id: str, data: dict, ttl: int = DEFAULT_TTL):
        """Cache execution data."""
        key = self._key("execution", execution_id)
        self.client.setex(key, ttl, json.dumps(data))

    def get_execution(self, execution_id: str) -> Optional[dict]:
        """Get cached execution data."""
        key = self._key("execution", execution_id)
        data = self.client.get(key)
        return json.loads(data) if data else None

    # ========== Recent Executions ==========

    def add_recent_execution(
        self,
        workflow_id: str,
        execution_id: str,
        status: str,
        max_entries: int = 100,
    ):
        """Add execution to recent list for a workflow."""
        key = self._key("workflow", workflow_id, "recent_executions")
        entry = json.dumps({"execution_id": execution_id, "status": status})
        self.client.lpush(key, entry)
        self.client.ltrim(key, 0, max_entries - 1)

    def get_recent_executions(self, workflow_id: str, limit: int = 10) -> list[dict]:
        """Get recent executions for a workflow."""
        key = self._key("workflow", workflow_id, "recent_executions")
        entries = self.client.lrange(key, 0, limit - 1)
        return [json.loads(e) for e in entries]

    # ========== Active Workflow Tracking ==========

    def mark_workflow_active(self, workflow_id: str):
        """Mark a workflow as active."""
        key = self._key("active_workflows")
        self.client.sadd(key, workflow_id)

    def mark_workflow_inactive(self, workflow_id: str):
        """Mark a workflow as inactive."""
        key = self._key("active_workflows")
        self.client.srem(key, workflow_id)

    def get_active_workflows(self) -> set[str]:
        """Get all active workflow IDs."""
        key = self._key("active_workflows")
        return self.client.smembers(key)

    # ========== Node Type Usage Stats ==========

    def increment_node_usage(self, node_type: str):
        """Increment usage counter for a node type."""
        key = self._key("stats", "node_usage")
        self.client.hincrby(key, node_type, 1)

    def get_node_usage_stats(self) -> dict[str, int]:
        """Get node type usage statistics."""
        key = self._key("stats", "node_usage")
        stats = self.client.hgetall(key)
        return {k: int(v) for k, v in stats.items()}

    # ========== Health & Stats ==========

    def health_check(self) -> bool:
        """Check Redis health."""
        try:
            return self.client.ping()
        except Exception:
            return False

    def get_stats(self) -> dict:
        """Get cache statistics."""
        info = self.client.info("memory")
        return {
            "used_memory": info.get("used_memory_human"),
            "connected_clients": self.client.info("clients").get("connected_clients"),
            "active_workflows": len(self.get_active_workflows()),
        }

    def flush_all(self):
        """Clear all n8n_fabric cache entries."""
        pattern = self._key("*")
        keys = self.client.keys(pattern)
        if keys:
            self.client.delete(*keys)
