"""Qdrant vector storage for workflow embeddings."""

import hashlib
import json
import os
from typing import Any, Optional
from uuid import UUID, uuid4

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams
from sentence_transformers import SentenceTransformer


def string_to_uuid(s: str) -> str:
    """Convert a string to a deterministic UUID."""
    # Create a deterministic UUID from the string using MD5 hash
    hash_bytes = hashlib.md5(s.encode()).digest()
    return str(UUID(bytes=hash_bytes))


class WorkflowVectorStore:
    """Store and search workflow embeddings in Qdrant."""

    COLLECTION_NAME = "n8n_workflows"
    EMBEDDING_DIM = 384  # all-MiniLM-L6-v2

    def __init__(
        self,
        qdrant_url: Optional[str] = None,
        collection_name: Optional[str] = None,
    ):
        self.qdrant_url = qdrant_url or os.getenv("QDRANT_URL", "http://localhost:6333")
        self.collection_name = collection_name or self.COLLECTION_NAME
        self.client = QdrantClient(url=self.qdrant_url)
        self.embedder = SentenceTransformer("all-MiniLM-L6-v2")
        self._ensure_collection()

    def _ensure_collection(self):
        """Ensure the collection exists."""
        collections = self.client.get_collections().collections
        exists = any(c.name == self.collection_name for c in collections)

        if not exists:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.EMBEDDING_DIM,
                    distance=Distance.COSINE,
                ),
            )

    def _workflow_to_text(self, workflow: dict) -> str:
        """Convert workflow to searchable text."""
        parts = [
            f"Workflow: {workflow.get('name', 'Unnamed')}",
        ]

        # Add tags
        tags = workflow.get("tags", [])
        if tags:
            tag_names = [t.get("name", t) if isinstance(t, dict) else t for t in tags]
            parts.append(f"Tags: {', '.join(tag_names)}")

        # Add node descriptions
        nodes = workflow.get("nodes", [])
        for node in nodes:
            node_name = node.get("name", "")
            node_type = node.get("type", "").split(".")[-1]  # Get last part of type
            parts.append(f"Node: {node_name} ({node_type})")

        # Add connection patterns
        connections = workflow.get("connections", {})
        for source, targets in connections.items():
            for target_list in targets.values():
                for target_group in target_list:
                    for target in target_group:
                        parts.append(f"Connection: {source} -> {target.get('node', '')}")

        return "\n".join(parts)

    def index_workflow(self, workflow: dict, workflow_id: Optional[str] = None) -> str:
        """Index a workflow for semantic search."""
        wf_id = workflow_id or workflow.get("id") or str(uuid4())
        # Convert string ID to UUID for Qdrant compatibility
        point_id = string_to_uuid(wf_id)
        text = self._workflow_to_text(workflow)
        embedding = self.embedder.encode(text).tolist()

        point = PointStruct(
            id=point_id,
            vector=embedding,
            payload={
                "workflow_id": wf_id,
                "name": workflow.get("name", ""),
                "active": workflow.get("active", False),
                "tags": [t.get("name", t) if isinstance(t, dict) else t for t in workflow.get("tags", [])],
                "node_count": len(workflow.get("nodes", [])),
                "node_types": list(set(n.get("type", "") for n in workflow.get("nodes", []))),
                "indexed_text": text,
                "workflow_json": json.dumps(workflow),
            },
        )

        self.client.upsert(
            collection_name=self.collection_name,
            points=[point],
        )

        return wf_id

    def search(
        self,
        query: str,
        limit: int = 10,
        active_only: bool = False,
        tags: Optional[list[str]] = None,
    ) -> list[dict]:
        """Search workflows by semantic similarity."""
        from qdrant_client.models import Filter, FieldCondition, MatchValue

        embedding = self.embedder.encode(query).tolist()

        # Build filter
        must_conditions = []
        if active_only:
            must_conditions.append(FieldCondition(key="active", match=MatchValue(value=True)))
        if tags:
            for tag in tags:
                must_conditions.append(FieldCondition(key="tags", match=MatchValue(value=tag)))

        filter_obj = Filter(must=must_conditions) if must_conditions else None

        results = self.client.query_points(
            collection_name=self.collection_name,
            query=embedding,
            limit=limit,
            query_filter=filter_obj,
            with_payload=True,
        )

        return [
            {
                "workflow_id": r.payload.get("workflow_id"),
                "name": r.payload.get("name"),
                "score": r.score,
                "active": r.payload.get("active"),
                "tags": r.payload.get("tags"),
                "node_count": r.payload.get("node_count"),
                "node_types": r.payload.get("node_types"),
            }
            for r in results.points
        ]

    def get_workflow(self, workflow_id: str) -> Optional[dict]:
        """Get indexed workflow by ID."""
        point_id = string_to_uuid(workflow_id)
        results = self.client.retrieve(
            collection_name=self.collection_name,
            ids=[point_id],
        )

        if results:
            payload = results[0].payload
            return json.loads(payload.get("workflow_json", "{}"))
        return None

    def delete_workflow(self, workflow_id: str):
        """Delete a workflow from the index."""
        point_id = string_to_uuid(workflow_id)
        self.client.delete(
            collection_name=self.collection_name,
            points_selector={"points": [point_id]},
        )

    def get_stats(self) -> dict:
        """Get collection statistics."""
        info = self.client.get_collection(self.collection_name)
        return {
            "collection": self.collection_name,
            "points_count": info.points_count,
        }

    def health_check(self) -> bool:
        """Check Qdrant health."""
        try:
            self.client.get_collections()
            return True
        except Exception:
            return False
