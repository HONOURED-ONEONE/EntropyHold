# Honeypot-RQ — Behavioral Brain (Hybrid Architecture)

This repository implements the **Behavioral Brain** for an agentic honeypot system. In the hybrid architecture, this Python service owns behavioral evaluation, session state, and intent/constraint selection, while an external **Deception Layer** handles orchestration and prompt mediation.

## Hybrid Architecture
- **Behavioral Brain (Python):** Authoritative session state, intent logic, red-flag tagging, and behavioral scoring.
- **Deception Layer (External):** Traffic steering, decoy provisioning, and high-level orchestration.
- **Mojo (Optional):** Profiled hot-paths for high-performance interop.

## API Surface

### 1. Behavioral Brain API (New)
Advanced endpoints for hybrid integration:
- `POST /behavior/evaluate`: Stateless message evaluation.
- `POST /behavior/session/{session_id}/update`: Stateful session advancement.
- `GET /behavior/session/{session_id}/state`: Current behavioral state and scores.
- `GET /behavior/session/{session_id}/trajectory`: Chronological behavior history.

### 2. Compatibility Honeypot API (Legacy)
Preserved for backward compatibility with existing honeypot evaluators:
- `POST /api/honeypot` (primary)
- `POST /detect` (compat)
- `POST /honeypot` (compat)
- `POST /api/detect` (compat)

Health & diagnostics:
- `GET /health`
- `GET /ping`
- `GET /metrics` (Prometheus)

## Setup (Local)
...

### 1) Create a virtual environment
```bash
python -m venv .venv
source .venv/bin/activate
```

### 2) Install dependencies
```bash
pip install -r requirements.txt
```

### 3) Configure environment
Copy `.env.example` to `.env` and fill values as needed.

### 4) Run API
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## API Contract

### Request (POST)
```json
{
  "sessionId": "uuid-v4-string",
  "message": { "sender": "scammer", "text": "message text", "timestamp": 1739279400000 },
  "conversationHistory": [],
  "metadata": { "channel": "SMS", "language": "English", "locale": "IN" }
}
```

### Response (200 OK)
```json
{ "status": "success", "reply": "text reply to scammer" }
```

## Environment Variables
See `.env.example` for the complete list.

## Monitoring
- Enable Prometheus scraping at `/metrics`. Scrapeable in <20ms.
- View lightweight SLO diagnostics at `/admin/slo`.

## Notes on Code Quality
The evaluation rubric reserves a portion of the final score for code quality and requires a valid GitHub repository URL.
