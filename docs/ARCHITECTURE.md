# HELIO Architecture

## Services
1. **web** (Next.js 15 App Router) — UI on `:3000`, proxies `/api-backend/*` → agent-api
2. **agent-api** (FastAPI) — sessions, conversations, Strands/simulator orchestration, typed tools, approvals proxy, analytics, eval harness
3. **enterprise-mock-api** (FastAPI) — synthetic Northstar/Beacon SoR, policy, idempotent tickets, approvals/actions

## Data
- Immutable seed: `cloudiqs_enterprise_demo_pack/data/canonical/enterprise.sqlite`
- Mutable mock DB: `data/runtime.sqlite` (bind-mounted)
- App state: Docker volume `agent_app_db` → `/data/app.sqlite` (sessions, runs, tool events, notifications, eval results, KB uploads)

## Auth
Demo persona → HttpOnly `helio_session` cookie. Server maps persona to mock Bearer token. Never expose fixture tokens to the browser. Tenant/role from verified identity.

## Agent
- `MODEL_PROVIDER=simulator` (default): deterministic golden-path orchestration calling **real** enterprise tools
- `MODEL_PROVIDER=bedrock`: Strands Agents + `BedrockModel` with injected typed tools
- Policy and mutations enforced in backend; LLM cannot execute approvals

## Trust boundary
Browser ↛ mock API. Agent tools ↛ raw SQLite bypass. Evaluator oracle loaded only in `/evaluations` routes, never into prompts.
