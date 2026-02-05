"""Qdrant vector storage for workflow embeddings."""

import json
import os
from typing import Any, Optional
from uuid import uuid4

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams
from sentence_transformers import SentenceTransformer


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
        text = self._workflow_to_text(workflow)
        embedding = self.embedder.encode(text).tolist()

        point = PointStruct(
            id=wf_id,
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
        embedding = self.embedder.encode(query).tolist()

        # Build filter
        must_conditions = []
        if active_only:
            must_conditions.append({"key": "active", "match": {"value": True}})
        if tags:
            for tag in tags:
                must_conditions.append({"key": "tags", "match": {"value": tag}})

        filter_obj = {"must": must_conditions} if must_conditions else None

        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=embedding,
            limit=limit,
            query_filter=filter_obj,
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
            for r in results
        ]

    def get_workflow(self, workflow_id: str) -> Optional[dict]:
        """Get indexed workflow by ID."""
        results = self.client.retrieve(
            collection_name=self.collection_name,
            ids=[workflow_id],
        )

        if results:
            payload = results[0].payload
            return json.loads(payload.get("workflow_json", "{}"))
        return None

    def delete_workflow(self, workflow_id: str):
        """Delete a workflow from the index."""
        self.client.delete(
            collection_name=self.collection_name,
            points_selector={"points": [workflow_id]},
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
