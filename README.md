# HELIO — Autonomous Enterprise Service Desk (local Docker demo)

Independent hiring demonstration inspired by AWS-native agent workflows. **Not** an official CloudiQS or Agentic Bakery product. Enterprise connectors are synthetic; agent tools, policies, approvals, persistence and UI are real application code.

## Quick start (Docker only)

```bash
cp .env.example .env
docker compose up --build -d
```

Open **http://localhost:3000** → choose persona **Asha Patel** (Northstar employee).

| Service | URL | Notes |
|---|---|---|
| Web UI | http://localhost:3000 | Bound to localhost |
| Agent API | http://localhost:8001 | Session cookies; OpenAPI `/docs` |
| Enterprise mock API | http://localhost:8000 | Private Docker network preferred; localhost for diagnostics |

Default `MODEL_PROVIDER=simulator` (deterministic golden paths calling **real** mock tools). Set `MODEL_PROVIDER=bedrock` plus AWS credentials for live Strands+Bedrock. AgentCore Runtime is **not** deployed locally.

## Demo personas

Northstar: `northstar-asha`, `northstar-rahul`, `northstar-priya`, `northstar-vikram`, `northstar-arjun-security`  
Beacon: `beacon-neha`, `beacon-david`, `beacon-james`, `beacon-meera`, `beacon-noah-security`  
Denied: `northstar-omar-terminated`

## Useful commands

```bash
docker compose ps
docker compose logs -f agent-api
docker compose exec enterprise-mock-api pytest -q
docker compose exec agent-api pytest -q
# Reset mutable demo state (destructive):
make reset-demo CONFIRM=YES
```

## Architecture

Browser → Next.js (rewrites `/api-backend`) → FastAPI agent control plane → Strands (Bedrock) or Offline Simulator → typed tools → enterprise mock FastAPI → SQLite fixtures.

See `docs/ARCHITECTURE.md`, `docs/SECURITY_MODEL.md`, `docs/DEMO_WALKTHROUGH.md`, `docs/TEST_RESULTS.md`.

## Known limitations

- Offline simulator is labelled and is **not** model inference.
- Bedrock requires account model access; without credentials the UI stays on Offline mode.
- No Cognito/OIDC, no AgentCore Runtime/Gateway, no real MFA reset / remote wipe.
- All identities and remediations are fictional simulations.
