# ADR-001: Fabric Architecture for n8n Integration

## Status
Accepted

## Date
2026-02-04

## Context

We need to integrate n8n workflow automation into the ry-ops ecosystem alongside git-steer (repo management) and aiana (semantic memory). The question is how to structure this integration.

## Decision

We adopt a **Fabric Layer Architecture** where each tool operates as an independent, loosely-coupled layer:

```
┌─────────────────────────────────────────────────────────────┐
│                    Fabric Ecosystem                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   n8n-fabric          git-steer           aiana              │
│   ┌─────────┐        ┌─────────┐        ┌─────────┐         │
│   │ MCP     │        │ MCP     │        │ MCP     │         │
│   │ Server  │◄──────►│ Server  │◄──────►│ Server  │         │
│   └────┬────┘        └────┬────┘        └────┬────┘         │
│        │                  │                  │               │
│   ┌────┴────┐        ┌────┴────┐        ┌────┴────┐         │
│   │ Qdrant  │        │ Qdrant  │        │ Qdrant  │         │
│   │ Redis   │        │ State   │        │ Mem0    │         │
│   └─────────┘        └─────────┘        └─────────┘         │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Key Principles

1. **Independent Operation**: Each fabric can operate standalone without the others
2. **MCP as Interface**: All cross-fabric communication happens via MCP protocol
3. **Isolated Storage**: Each fabric owns its own Qdrant collection and Redis namespace
4. **No Tight Coupling**: Fabrics don't reach into each other's internals

## Consequences

### Positive

- **Substitutability**: Can swap n8n for Temporal, Prefect, or custom solution
- **Independent Evolution**: Each fabric can be updated without affecting others
- **Clear Boundaries**: Easy to understand what each fabric owns
- **Flexible Deployment**: Can run all together or separately as needed

### Negative

- **More Infrastructure**: Each fabric needs its own storage setup
- **Coordination Overhead**: Cross-fabric operations require explicit orchestration
- **Potential Duplication**: Some patterns might be reimplemented across fabrics

## Alternatives Considered

### Monolithic Integration
Embed n8n directly into aiana as a sub-module.

**Rejected because**: Tight coupling, harder to evolve independently, violates separation of concerns.

### Shared Storage
All fabrics share a single Qdrant instance and Redis.

**Rejected because**: Creates hidden dependencies, harder to isolate failures, complicates schema evolution.

## Related Decisions

- ADR-001 in aiana: Dependency Integration Strategy (wrapper pattern)
- git-steer: Bare Tin Foil Architecture

## Notes

The fabric architecture emerged from observing how the tools naturally compose. Rather than designing an orchestration layer upfront, we built the primitives first and let the patterns emerge.
