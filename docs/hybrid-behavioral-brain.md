# Hybrid Behavioral Brain Architecture

This document describes the responsibilities and interaction patterns of the Behavioral Brain (Python) in the hybrid honeypot architecture.

## Responsibilities

### Behavioral Brain (Python) - Authoritative Decision Engine
- **Behavioral Evaluation:** Ingests messages and history to determine the scammer's current behavioral state.
- **Session State Management:** Owns the source-of-truth for session transitions, counters, and history.
- **Intent/Constraint Selection:** Selects the appropriate behavioral constraint or "intent" (e.g., `INT_ASK_OTP`) for the response.
- **Ladder & Red-Flag Logic:** Decides when to advance investigative steps or deploy red-flag cues.
- **Intelligence Extraction:** Maps raw text to structured IOCs (emails, phone numbers, links).
- **Termination Policy:** Owns the final decision on when to close or report a session based on evasion or exhaustion.
- **Final Report Generation:** Produces the comprehensive evidence bundle at the end of a session.

### Deception Layer (External) - Orchestration & Mediation
- **Traffic Steering:** Routes traffic from various sources (SMS, Web, WhatsApp) to the appropriate brain instance.
- **Decoy Provisioning:** Manages the lifecycle of deception surfaces (personas, websites, phone numbers).
- **Prompt Mediation:** Shapes the final LLM response using constraints provided by the Brain.
- **Infrastructure:** Auth, rate limiting, and fleet management.

## Integration Boundary

The interface between the two layers is defined by the **Behavioral Brain API**:

### State Updates
- The external layer calls `POST /behavior/session/{session_id}/update` with the latest message.
- The Brain returns the current state, active constraint, behavioral scores, and recommendation.

### Hybrid Metadata
The external layer can inject context via `hybridMetadata`:
- `deceptionNarrative`: Global context about the current deception scenario.
- `availableSurfaces`: Tools available for the agent (e.g., "fake banking portal").
- `externalPersonaHints`: Hints about the persona assigned to the agent.

## Reporting Modes

The Python service supports two reporting modes:
1. **Internal Reporting:** Python handles delivery of the final report via configured callback URLs or RQ workers.
2. **Externalized Reporting:** Python freezes and persists the report but exposes it for external retrieval. The external Deception Layer is responsible for durable callback delivery.

This mode is controlled by the `EXTERNAL_REPORTING_MODE` feature flag.
