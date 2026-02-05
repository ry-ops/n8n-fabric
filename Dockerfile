# n8n-fabric - Workflow Automation Fabric MCP Server
# Multi-stage build using uv for fast, reproducible installs

FROM python:3.12-slim AS builder

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml uv.lock README.md LICENSE ./
COPY src/ ./src/

# Install dependencies with uv (frozen = use lockfile exactly)
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
RUN uv sync --frozen --no-dev

# Production stage
FROM python:3.12-slim

LABEL org.opencontainers.image.title="n8n-fabric"
LABEL org.opencontainers.image.description="n8n workflow automation fabric with MCP server, Qdrant vector storage, and Redis caching"
LABEL org.opencontainers.image.source="https://github.com/ry-ops/n8n-fabric"
LABEL org.opencontainers.image.licenses="MIT"

# Create non-root user
RUN useradd --create-home --shell /bin/bash n8nfabric

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY --chown=n8nfabric:n8nfabric src/ ./src/
COPY --chown=n8nfabric:n8nfabric pyproject.toml README.md LICENSE ./

# Set environment
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Default environment variables (override at runtime)
ENV N8N_URL="http://localhost:5678"
ENV QDRANT_URL="http://localhost:6333"
ENV REDIS_URL="redis://localhost:6379"

# Switch to non-root user
USER n8nfabric

# Health check using CLI
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD n8n-fabric status || exit 1

# The MCP server runs on stdio
ENTRYPOINT ["n8n-fabric-mcp"]
