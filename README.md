# Honeypot-RQ — Behavioral Brain (Hybrid Architecture)

This repository implements the **Behavioral Brain** for an agentic honeypot system. In the hybrid architecture, this Python service owns behavioral evaluation, session state, and intent/constraint selection, while the **Deception Layer** (also included) handles orchestration, durable reporting, and ops surfaces.

## Hybrid Architecture
- **Behavioral Brain (app/):** Python-based authoritative brain for session state, intent logic, red-flag tagging, and behavioral scoring.
- **Deception Layer (deception_layer/):** 
  - **Orchestration:** High-level control plane and policy enforcement.
  - **Worker:** Durable callback delivery and reporting handoff.
  - **Ops:** Real-time visibility and administrative surface.
- **Mojo (Optional):** Profiled hot-paths for high-performance extraction (see `app/intel/fast_digits.mojo`).

## Project Structure
```text
├── app/                # Behavioral Brain (Python)
├── deception_layer/    # Orchestration, Worker, Ops (FastAPI)
├── collector/          # Evidence collection utilities
├── matrix_bot/         # Optional Matrix integration
└── tests/              # Comprehensive test suite
```

## API Surfaces

### 1. Behavioral Brain API (Internal/Hybrid)
Advanced endpoints for hybrid integration:
- `POST /behavior/evaluate`: Stateless message evaluation.
- `POST /behavior/session/{session_id}/update`: Stateful session advancement.
- `GET /behavior/session/{session_id}/state`: Current behavioral state and scores.
- `GET /behavior/session/{session_id}/trajectory`: Chronological behavior history.

### 2. Deception Layer API (External)
Orchestration and administrative surfaces:
- `POST /api/orchestration/evaluate`: Orchestrated trigger evaluation.
- `GET /api/ops/session/{session_id}`: Live session state view.
- `GET /api/worker/health`: Reporting worker health status.

### 3. Compatibility Honeypot API (Legacy)
Preserved for backward compatibility with existing honeypot evaluators:
- `POST /api/honeypot` (primary)
- `POST /detect` (compat)

## Setup (Local)

### 1) Prerequisites
- Python 3.9+
- Redis (required for session state and locking)

### 2) Quick Start (Docker)
```bash
docker-compose up --build
```

### 3) Manual Python Setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# Set EXTERNAL_REPORTING_MODE=true in .env for hybrid mode
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## External Reporting Mode
When `EXTERNAL_REPORTING_MODE=true` is enabled in the Brain:
1. Python builds and persists the final evidence report.
2. Status is marked as `prepared`.
3. Python does NOT attempt delivery; it hands off the durable delivery concern to the Deception Layer worker.

## Environment Variables
Key variables in `.env.example`:
- `EXTERNAL_REPORTING_MODE`: Enable hybrid reporting handoff.
- `FINAL_OUTPUT_MODE`: `sync`, `rq`, or `hybrid`.
- `GUVI_CALLBACK_URL`: Target for internal (non-external) callbacks.

