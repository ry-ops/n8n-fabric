"""n8n API client with full API access."""

import os
from typing import Any, Optional

import httpx


class N8nClient:
    """Client for n8n REST API with full access to all endpoints."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        self.base_url = (base_url or os.getenv("N8N_URL", "http://localhost:5678")).rstrip("/")
        self.api_key = api_key or os.getenv("N8N_API_KEY", "")
        self._client = httpx.Client(
            base_url=self.base_url,
            headers={"X-N8N-API-KEY": self.api_key} if self.api_key else {},
            timeout=30.0,
        )

    def _request(
        self,
        method: str,
        path: str,
        params: Optional[dict] = None,
        json: Optional[dict] = None,
    ) -> Any:
        """Make HTTP request to n8n API."""
        response = self._client.request(method, path, params=params, json=json)
        response.raise_for_status()
        return response.json() if response.content else None

    # ========== Health ==========

    def health(self) -> dict:
        """Check n8n health status."""
        try:
            response = self._client.get("/healthz")
            return {"healthy": response.status_code == 200}
        except Exception as e:
            return {"healthy": False, "error": str(e)}

    def version(self) -> dict:
        """Get n8n version info."""
        return self._request("GET", "/api/v1/version")

    # ========== Workflows ==========

    def workflow_list(
        self,
        active: Optional[bool] = None,
        tags: Optional[list[str]] = None,
        limit: int = 100,
        cursor: Optional[str] = None,
    ) -> dict:
        """List all workflows."""
        params = {"limit": limit}
        if active is not None:
            params["active"] = str(active).lower()
        if tags:
            params["tags"] = ",".join(tags)
        if cursor:
            params["cursor"] = cursor
        return self._request("GET", "/api/v1/workflows", params=params)

    def workflow_get(self, workflow_id: str) -> dict:
        """Get workflow by ID."""
        return self._request("GET", f"/api/v1/workflows/{workflow_id}")

    def workflow_create(self, workflow: dict) -> dict:
        """Create a new workflow."""
        return self._request("POST", "/api/v1/workflows", json=workflow)

    def workflow_update(self, workflow_id: str, workflow: dict) -> dict:
        """Update an existing workflow."""
        return self._request("PUT", f"/api/v1/workflows/{workflow_id}", json=workflow)

    def workflow_delete(self, workflow_id: str) -> dict:
        """Delete a workflow."""
        return self._request("DELETE", f"/api/v1/workflows/{workflow_id}")

    def workflow_activate(self, workflow_id: str) -> dict:
        """Activate a workflow."""
        return self._request("POST", f"/api/v1/workflows/{workflow_id}/activate")

    def workflow_deactivate(self, workflow_id: str) -> dict:
        """Deactivate a workflow."""
        return self._request("POST", f"/api/v1/workflows/{workflow_id}/deactivate")

    def workflow_execute(
        self,
        workflow_id: str,
        data: Optional[dict] = None,
    ) -> dict:
        """Execute a workflow manually."""
        payload = data or {}
        return self._request("POST", f"/api/v1/workflows/{workflow_id}/execute", json=payload)

    def workflow_tags(self, workflow_id: str) -> dict:
        """Get tags for a workflow."""
        return self._request("GET", f"/api/v1/workflows/{workflow_id}/tags")

    def workflow_transfer(self, workflow_id: str, destination_project_id: str) -> dict:
        """Transfer workflow to another project."""
        return self._request(
            "PUT",
            f"/api/v1/workflows/{workflow_id}/transfer",
            json={"destinationProjectId": destination_project_id},
        )

    # ========== Executions ==========

    def execution_list(
        self,
        workflow_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        cursor: Optional[str] = None,
    ) -> dict:
        """List executions."""
        params = {"limit": limit}
        if workflow_id:
            params["workflowId"] = workflow_id
        if status:
            params["status"] = status
        if cursor:
            params["cursor"] = cursor
        return self._request("GET", "/api/v1/executions", params=params)

    def execution_get(self, execution_id: str, include_data: bool = True) -> dict:
        """Get execution details."""
        params = {"includeData": str(include_data).lower()}
        return self._request("GET", f"/api/v1/executions/{execution_id}", params=params)

    def execution_delete(self, execution_id: str) -> dict:
        """Delete an execution."""
        return self._request("DELETE", f"/api/v1/executions/{execution_id}")

    def execution_retry(self, execution_id: str) -> dict:
        """Retry a failed execution."""
        return self._request("POST", f"/api/v1/executions/{execution_id}/retry")

    def execution_stop(self, execution_id: str) -> dict:
        """Stop a running execution."""
        return self._request("POST", f"/api/v1/executions/{execution_id}/stop")

    # ========== Credentials ==========

    def credential_list(self, limit: int = 100, cursor: Optional[str] = None) -> dict:
        """List credentials (names only, no secrets)."""
        params = {"limit": limit}
        if cursor:
            params["cursor"] = cursor
        return self._request("GET", "/api/v1/credentials", params=params)

    def credential_get(self, credential_id: str, include_data: bool = False) -> dict:
        """Get credential by ID."""
        params = {"includeData": str(include_data).lower()}
        return self._request("GET", f"/api/v1/credentials/{credential_id}", params=params)

    def credential_create(self, credential: dict) -> dict:
        """Create a new credential."""
        return self._request("POST", "/api/v1/credentials", json=credential)

    def credential_update(self, credential_id: str, credential: dict) -> dict:
        """Update a credential."""
        return self._request("PATCH", f"/api/v1/credentials/{credential_id}", json=credential)

    def credential_delete(self, credential_id: str) -> dict:
        """Delete a credential."""
        return self._request("DELETE", f"/api/v1/credentials/{credential_id}")

    def credential_schema(self, credential_type: str) -> dict:
        """Get credential type schema."""
        return self._request("GET", f"/api/v1/credentials/schema/{credential_type}")

    def credential_transfer(self, credential_id: str, destination_project_id: str) -> dict:
        """Transfer credential to another project."""
        return self._request(
            "PUT",
            f"/api/v1/credentials/{credential_id}/transfer",
            json={"destinationProjectId": destination_project_id},
        )

    # ========== Tags ==========

    def tag_list(self, limit: int = 100, cursor: Optional[str] = None) -> dict:
        """List all tags."""
        params = {"limit": limit}
        if cursor:
            params["cursor"] = cursor
        return self._request("GET", "/api/v1/tags", params=params)

    def tag_get(self, tag_id: str) -> dict:
        """Get tag by ID."""
        return self._request("GET", f"/api/v1/tags/{tag_id}")

    def tag_create(self, name: str) -> dict:
        """Create a new tag."""
        return self._request("POST", "/api/v1/tags", json={"name": name})

    def tag_update(self, tag_id: str, name: str) -> dict:
        """Update a tag."""
        return self._request("PATCH", f"/api/v1/tags/{tag_id}", json={"name": name})

    def tag_delete(self, tag_id: str) -> dict:
        """Delete a tag."""
        return self._request("DELETE", f"/api/v1/tags/{tag_id}")

    # ========== Users ==========

    def user_list(self, limit: int = 100, cursor: Optional[str] = None) -> dict:
        """List users."""
        params = {"limit": limit}
        if cursor:
            params["cursor"] = cursor
        return self._request("GET", "/api/v1/users", params=params)

    def user_get(self, user_id: str) -> dict:
        """Get user by ID."""
        return self._request("GET", f"/api/v1/users/{user_id}")

    # ========== Projects ==========

    def project_list(self, limit: int = 100, cursor: Optional[str] = None) -> dict:
        """List projects."""
        params = {"limit": limit}
        if cursor:
            params["cursor"] = cursor
        return self._request("GET", "/api/v1/projects", params=params)

    def project_get(self, project_id: str) -> dict:
        """Get project by ID."""
        return self._request("GET", f"/api/v1/projects/{project_id}")

    def project_create(self, name: str) -> dict:
        """Create a new project."""
        return self._request("POST", "/api/v1/projects", json={"name": name})

    def project_update(self, project_id: str, name: str) -> dict:
        """Update a project."""
        return self._request("PATCH", f"/api/v1/projects/{project_id}", json={"name": name})

    def project_delete(self, project_id: str) -> dict:
        """Delete a project."""
        return self._request("DELETE", f"/api/v1/projects/{project_id}")

    # ========== Variables ==========

    def variable_list(self, limit: int = 100, cursor: Optional[str] = None) -> dict:
        """List variables."""
        params = {"limit": limit}
        if cursor:
            params["cursor"] = cursor
        return self._request("GET", "/api/v1/variables", params=params)

    def variable_get(self, variable_id: str) -> dict:
        """Get variable by ID."""
        return self._request("GET", f"/api/v1/variables/{variable_id}")

    def variable_create(self, key: str, value: str) -> dict:
        """Create a new variable."""
        return self._request("POST", "/api/v1/variables", json={"key": key, "value": value})

    def variable_update(self, variable_id: str, key: str, value: str) -> dict:
        """Update a variable."""
        return self._request(
            "PATCH", f"/api/v1/variables/{variable_id}", json={"key": key, "value": value}
        )

    def variable_delete(self, variable_id: str) -> dict:
        """Delete a variable."""
        return self._request("DELETE", f"/api/v1/variables/{variable_id}")

    # ========== Source Control ==========

    def source_control_pull(self) -> dict:
        """Pull from source control."""
        return self._request("POST", "/api/v1/source-control/pull")

    def source_control_push(self, message: Optional[str] = None) -> dict:
        """Push to source control."""
        payload = {}
        if message:
            payload["message"] = message
        return self._request("POST", "/api/v1/source-control/push", json=payload)

    def source_control_status(self) -> dict:
        """Get source control status."""
        return self._request("GET", "/api/v1/source-control/status")

    # ========== Audit Logs ==========

    def audit_logs(
        self,
        limit: int = 100,
        cursor: Optional[str] = None,
        event_type: Optional[str] = None,
    ) -> dict:
        """Get audit logs."""
        params = {"limit": limit}
        if cursor:
            params["cursor"] = cursor
        if event_type:
            params["eventType"] = event_type
        return self._request("GET", "/api/v1/audit-logs", params=params)

    # ========== LDAP ==========

    def ldap_sync(self) -> dict:
        """Trigger LDAP sync."""
        return self._request("POST", "/api/v1/ldap/sync")

    def ldap_config(self) -> dict:
        """Get LDAP configuration."""
        return self._request("GET", "/api/v1/ldap/config")

    # ========== Community Nodes ==========

    def community_node_list(self) -> dict:
        """List installed community nodes."""
        return self._request("GET", "/api/v1/community-packages")

    def community_node_install(self, package_name: str) -> dict:
        """Install a community node package."""
        return self._request("POST", "/api/v1/community-packages", json={"name": package_name})

    def community_node_uninstall(self, package_name: str) -> dict:
        """Uninstall a community node package."""
        return self._request("DELETE", f"/api/v1/community-packages/{package_name}")

    def community_node_update(self, package_name: str) -> dict:
        """Update a community node package."""
        return self._request("PATCH", f"/api/v1/community-packages/{package_name}")

    def close(self):
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
