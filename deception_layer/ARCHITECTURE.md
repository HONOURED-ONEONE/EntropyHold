# Deception Layer Architecture Plan

## Overview
This architecture strictly enforces a hybrid model where the external **Deception Layer** acts as the API gateway, orchestration boundary, and operational interface, leaving the **Python Behavioral Brain** as the sole authority for state machines, heuristics, session trajectories, and LLM evaluations.

## Principles
1. **Python Authority:** The Deception Layer must *never* implement behavioral heuristics or autonomous state transitions. It simply orchestrates, applies static rules (like bans or schema validation), and defers logic to the Python Brain.
2. **Strict Boundary:** Communication between the Deception Layer and the Brain relies on typed HTTP/REST (or gRPC) contracts. Mojo is permitted *only* for specialized hot-path optimization directly interacting with the Python core, not for the control plane.

## Proposed Modules
- **`contracts/`**: Shared schemas (e.g., Pydantic models or OpenAPI specs) representing requests, responses, state updates, and worker tasks.
- **`orchestration/`**: The control plane API. Responsible for trigger ingestion, pre-flight policy checks (auth, basic bans), and request enrichment before forwarding to the Brain.
- **`worker/`**: An asynchronous, durable processor dedicated to reliable callback delivery and final report dispatch, consuming payloads the Brain marks as "final".
- **`ops/`**: A real-time admin interface (WebSocket/REST) that streams live trajectory data from the Brain to security analysts.

## Integration Details
- **Orchestration to Brain**: Synchronous HTTP calls (`/api/internal/evaluate`).
- **Brain to Worker**: The Brain pushes tasks to a shared queue (e.g., Redis, RabbitMQ), which the external worker consumes.
- **Brain to Ops**: The Brain pushes telemetry updates via Webhooks (or PubSub) to the Ops service, which relays it over WebSockets.

## Risks & Considerations
- **Network Latency:** Moving orchestration out of the Python monolith introduces serialization and network hops.
- **Contract Drift:** The shared models between layers must be versioned rigorously to prevent schema mismatches during deployments.
