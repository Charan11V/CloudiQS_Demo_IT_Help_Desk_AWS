# HELIO application documentation

This is the implementation handbook for the CloudiQS HELIO enterprise IT helpdesk demo. It describes the application as it is built: the Next.js UI, two backends, two databases, the freeform agent, the guided helpdesk, ticket assignment, approvals, and both the local Docker layout and the AWS layout.

Synthetic company data (Northstar and Beacon) stands in for HR, identity, devices, VPN, tickets, and knowledge. The application code around that data is real: sessions, policies, idempotency, approvals, persistence, and the agent tool loop.

Related files, each with a narrower job:

| File | Job |
|---|---|
| `docs/APPLICATION.md` | This handbook |
| `docs/CURRENT_RELEASE.md` | What is deployed on AWS as of 3 November 2026 |
| `AGENTCORE_DEPLOYMENT.md` | Commands to deploy and roll back AgentCore |
| `docs/SECURITY_MODEL.md` | Earlier security notes |
| `docs/DEMO_WALKTHROUGH.md` | Click-path for a demo |

`README.md` still describes the original local simulator. Where it disagrees with this file, this file matches the code.

## 1. What the product does

An employee signs in as a fictional persona and can:

- Walk a guided diagnosis (`/support`) that asks choices, checks bakery data, runs safe mock fixes, and raises a ticket owned by one IT person.
- Describe a problem in free text (`/support?mode=describe`). That path runs the HELIO agent, which calls typed tools and may propose an approval. It does not execute the change itself.
- See tickets from both systems on one list.
- See their devices.
- If their role allows it, approve or reject proposed changes, open admin, or open security.

IT staff are the same application with a wider nav. There is no separate IT console.

## 2. Tech stack

| Layer | Choice | Where |
|---|---|---|
| UI | Next.js 15.1.6 App Router, React 19, TypeScript | `apps/web` |
| UI kit | Tailwind CSS 3.4, Radix UI, TanStack Query and Table, Zod, react-hook-form, Recharts, Framer Motion, Lucide | `apps/web/package.json` |
| Browser tests | Playwright | `apps/web` |
| Freeform control plane | FastAPI 0.115, Uvicorn, Pydantic 2, SQLAlchemy 2, SQLite | `services/agent_api` |
| Agent framework | Strands Agents with an OpenAI-compatible model client | `agent_api` and `agentcore_runtime` |
| Live model | Groq `openai/gpt-oss-20b` at `https://api.groq.com/openai/v1` | AWS freeform path |
| Offline model | Deterministic simulator, no network call | `MODEL_PROVIDER=simulator` |
| Optional model paths | Amazon Bedrock via Strands, or local Ollama | `services/agent_api/app/agent/factory.py` |
| Hosted agent | Amazon Bedrock AgentCore Runtime, CodeZip, ARM64, Python 3.13 | `services/agentcore_runtime`, region `ap-south-2` |
| Guided helpdesk | FastAPI 0.104, SQLAlchemy 2, Postgres 15 | `services/bakery_api` |
| Enterprise systems of record | FastAPI mock over SQLite | `cloudiqs_enterprise_demo_pack/mock_api/app.py` |
| AWS app host | One EC2 instance, Docker Compose, Caddy 2.9 | `compose.aws.yaml` |
| IaC | AWS CDK for the demo stack | `infra/` |
| Node | 20 or newer | `apps/web/package.json` engines |

Bedrock foundation models are wired in code and are not used on the current AWS account. Invoke returns `NOT_AUTHORIZED`. The freeform brain on AWS is Groq inside AgentCore, not a Bedrock model.

## 3. Repository map

```
apps/web/                         Next.js UI
apps/bakery_web/                  Older bakery UI, not the HELIO shell
services/agent_api/               Sessions, runs, tools, AgentCore client, bridge
services/agentcore_runtime/       Code that runs inside AgentCore
services/bakery_api/              Guided engine, Postgres models, mock fixes
cloudiqs_enterprise_demo_pack/     Mock enterprise API, CSV seed, canonical SQLite
specs/                            Bakery issue catalogs mounted into bakery-api on AWS
compose.yaml                      Local stack: mock, agent-api, web
compose.aws.yaml                  EC2 stack: postgres, bakery, mock, agent, web, caddy
scripts/aws/                      EC2 deploy, HTTPS
scripts/agentcore/                Runtime package, update, rollback, e2e
deploy/agentcore/state.json       Live Runtime id, ARN, CodeZip history
infra/                            CDK
```

Local Compose does not start bakery. Guided help on a laptop expects bakery at `host.docker.internal:8002` (`compose.yaml` build args). On EC2, bakery is a Compose service and the web container calls `http://bakery-api:8000`.

## 4. Architecture

The browser has one origin. Next.js rewrites split that origin into two APIs. Neither API is published to the internet on EC2. Caddy is the only published process.

![AWS request path](diagrams/01-aws-request-path.svg)

On a laptop there is no Caddy and no AgentCore unless you set the flags. The browser talks to `127.0.0.1:3000`. Next proxies `/api-backend` to `agent-api:8001`. The agent calls `http://enterprise-mock-api:8000` on the Docker network.

![Local Docker path](diagrams/02-local-path.svg)

### Why the tool bridge exists

AgentCore runs in Hyderabad and cannot resolve Docker names such as `enterprise-mock-api`. Putting the mock API on a public port, or adding NAT and a private VPC integration, was rejected for this demo. Instead the Runtime calls a public HTTPS URL that Next already exposes:

`https://3.80.12.216.sslip.io/api-backend/internal/agentcore/tools`

That URL is rewritten to `agent-api`. The handler checks an HMAC and a one-run token, then calls the same tool functions the local agent uses. The enterprise bearer token stays inside `agent-api`.

### Trust boundary

![Trust boundary](diagrams/03-trust-boundary.svg)

The model is not a trust boundary. Ticket owner, tenant scope, approval separation, and knowledge classification are enforced in the APIs after the model has already decided to call a tool.

## 5. AWS deployment shape

| Piece | Value |
|---|---|
| Account | `672281861394` |
| App region | `us-east-1` |
| Instance | `i-0c506bd86c3d0ccd9` in stack `CloudiQSDemoStack` |
| Public URL | `https://3.80.12.216.sslip.io` |
| TLS | Caddy 2.9, ZeroSSL certificate for that host |
| AgentCore region | `ap-south-2` |
| Runtime | `helio_gptoss_agent-EAdCtN2scG`, package 1.0.3 |
| Runtime ARN | `arn:aws:bedrock-agentcore:ap-south-2:672281861394:runtime/helio_gptoss_agent-EAdCtN2scG` |
| Why Hyderabad | `us-east-1` and `us-west-2` AgentCore agent quota is 0 on this account |

Published ports on the instance are 80 and 443, both owned by Caddy. `web` only `expose`s 3000 on the Docker network. Mock, agent, bakery, and Postgres have no host ports.

Host files that survive a container recreate:

| Host path | Mounted as | Holds |
|---|---|---|
| `/opt/cloudiqs-demo/data/runtime.sqlite` | mock `/app/data/runtime.sqlite` | Enterprise tickets, approvals, users |
| `/opt/cloudiqs-demo/data/app.sqlite` | agent `/data/app.sqlite` | Sessions, conversations, runs |
| `/opt/cloudiqs-demo/data/canonical` | mock `/app/data/canonical` read-only | Seed snapshot |
| `/opt/cloudiqs-demo/data/pack` | agent `/pack` read-only | Demo token file |
| `/opt/cloudiqs-demo/specs` | bakery `/specs` read-only | Issue catalogs |
| Docker volume `bakery_pg_data` | Postgres data dir | Guided tickets and cases |
| Docker volumes `caddy_data`, `caddy_config` | Caddy | Certificate |

`bakery-api` starts with `python -m app.seed` and does not reset when the database already has tenants. Recreating the container keeps tickets.

CloudWatch log groups used by the AWS Compose logging driver:

- `/cloudiqs-demo/bakery-postgres`
- `/cloudiqs-demo/bakery-api`
- `/cloudiqs-demo/mock-api`
- `/cloudiqs-demo/agent-api`
- `/cloudiqs-demo/web`
- `/cloudiqs-demo/caddy`

AgentCore logs are separate, in `ap-south-2`, with 7-day retention. SSM parameters under `/cloudiqs-demo` in `us-east-1` hold the app wiring. The Groq key and the bridge secret are SecureStrings in both `us-east-1` and `ap-south-2`. The Runtime reads them in its own region at invoke time. They are not environment variables on the AgentCore control plane.

Not part of this deployment: AgentCore Gateway, Memory, Policy, a VPC mode Runtime, NAT, an ALB, RDS, EKS, and CloudFront. CloudFront create fails until AWS verifies the account.

## 6. UI

`apps/web` is a Next.js App Router app with `output: "standalone"`. Routes:

| URL | Who sees it | What it talks to |
|---|---|---|
| `/demo-access` | Everyone, before the gate | Sets `cloudiqs_demo_access` |
| `/login` | After the gate | `POST /api-backend/auth/demo-login` |
| `/` | Signed-in user | Workspace summary and a guided panel |
| `/support` | Signed-in user | Bakery guided engine |
| `/support?mode=describe` or `mode=freeform` | Signed-in user | Agent API conversations and runs |
| `/tickets`, `/tickets/[id]` | Signed-in user | Merged bakery and enterprise tickets |
| `/devices` | Signed-in user | Agent API `/devices` |
| `/approvals` | IT engineer, IT manager, tenant admin, security analyst | Agent API approval routes |
| `/admin` | Tenant admin | Agent API `/admin` |
| `/security` | Security analyst | Agent API `/security` |
| `/analytics`, `/evaluations` | Pages exist | Not listed in the shell nav |

The shell is `apps/web/components/app-shell.tsx`. Role comes from the HELIO session, not from the bakery user id.

| Role | Nav |
|---|---|
| employee, contractor | Home, Get help, My tickets, My devices |
| it_engineer, it_manager | Those, plus Approvals |
| tenant_admin | Those, plus Admin |
| security_analyst | Base pages, Approvals, Security |

Login personas drawn on the screen (`apps/web/lib/personas.ts`) are Northstar only:

| Key | Name | Role |
|---|---|---|
| `northstar-asha` | Asha Rao | Employee, Engineering |
| `northstar-kiran` | Kiran Desai | Employee, Finance |
| `northstar-leena` | Leena Joseph | Employee, Marketing |
| `northstar-rahul` | Rahul Sharma | IT engineer |
| `northstar-priya` | Priya Menon | IT manager |
| `northstar-vikram` | Vikram Rao | Tenant admin |
| `northstar-arjun-security` | Arjun Nair | Security analyst |

Beacon personas exist in the mock token file and in `services/agent_api/app/auth/session.py`. The login page does not offer them. A terminated persona key is rejected with HTTP 401.

### Rewrites

`apps/web/next.config.ts`:

| Browser path | Proxies to |
|---|---|
| `/api-backend/:path*` | `{AGENT_API_URL}/:path*` |
| `/bakery-api/:path*` | `{BAKERY_API_URL}/api/:path*` |

Local defaults: agent `http://localhost:8001` or `http://agent-api:8001` inside Compose. Bakery local build arg is `http://host.docker.internal:8002`. AWS web env is `http://agent-api:8001` and `http://bakery-api:8000`.

The bakery client strips nothing extra: a call to `/bakery-api/conversations` becomes bakery `POST /api/conversations`.

### Demo gate

`apps/web/middleware.ts` runs when `DEMO_GATE_ENABLED=1` (the AWS default).

1. Public paths skip the gate: `/demo-access`, `/api/demo-access`, `/api/health`, `/api-backend/internal/agentcore`, Next assets.
2. If `ORIGIN_VERIFY_TOKEN` is set, the request must send `x-cloudiqs-origin-verify` with the same value, unless the host is localhost or the path is the AgentCore bridge.
3. Cookie `cloudiqs_demo_access` must equal `DEMO_ACCESS_SECRET`. Comparison is length-checked and XOR-based. A missing secret fails closed: API calls get 503, pages redirect to `/demo-access?error=config`.
4. A missing cookie redirects pages to `/demo-access` and returns 401 for `/api`, `/api-backend`, and `/bakery-api`.

The bridge is public at the gate so AgentCore can call it. Authentication for that route is the HMAC in `agent-api`, not the demo cookie.

## 7. Authentication

There are three independent cookies.

| Cookie | Set by | Meaning |
|---|---|---|
| `cloudiqs_demo_access` | Next demo-access route | Visitor passed the demo gate |
| `helio_session` | agent-api `POST /auth/demo-login` | Freeform session id, HttpOnly, SameSite=Lax, 24h, `secure=False` |
| `bakery_session` | bakery `POST /api/auth/demo-login` | Guided session id |

`helio_session` is the raw `session_id` stored in agent SQLite. It is not the itsdangerous serializer token. The serializer is constructed in `session.py` and the cookie writer does not use it. Lookup is `sessions.session_id`. Expired rows are deleted on the next request.

Demo login flow:

![Sign-in flow](diagrams/04-sign-in.svg)

The bearer sent to the mock API is the persona key (`northstar-asha`), not the employee id. The mock token file maps that key to `northstar-EMP-0001`. Tenant id on the HELIO session is the prefix of the employee id (`northstar`).

The UI then logs into bakery separately. `apps/web/lib/helio-bakery-persona.ts` maps HELIO ids onto bakery seed ids. Bakery login only accepts those seed ids.

| HELIO persona or employee id | Bakery user id |
|---|---|
| Asha `northstar-asha` / `northstar-EMP-0001` | `NS-001` |
| Rahul `northstar-rahul` / `northstar-EMP-0002` | `NS-002` |
| Priya `northstar-priya` / `northstar-EMP-0003` | `NS-003` |
| Vikram `northstar-vikram` / `northstar-EMP-0004` | `NS-004` |
| Kiran | `NS-005` |
| Leena | `NS-006` |
| Arjun `northstar-arjun-security` / `northstar-EMP-0011` | `NS-004` |

Arjun is sent to bakery as Vikram (`NS-004`). The bakery Northstar seed used by this mapping has no distinct security-analyst user. Unknown Northstar ids fall back to `NS-001`. Bakery tenant resolution in this helper always returns `northstar`.

Guided actions therefore run as the bakery user. Freeform tools run as the HELIO employee id. Those are different keys for the same human.

## 8. Guided helpdesk

Default Get help is the bakery engine in `services/bakery_api/app/services/guided_engine.py`. The web panel is `apps/web/components/guided-helpdesk-panel.tsx`.

![Guided helpdesk flow](diagrams/05-guided-flow.svg)

A turn body is one of `option_id`, `option_ids`, `free_text`, or `control`. The engine stores the user text, runs `process_turn`, stores the assistant text, and saves a UI snapshot so refresh can resume via `GET /api/conversations/active`.

States the engine writes:

| State | Meaning |
|---|---|
| `WELCOME` | Top menu |
| `CHOOSING_SUBCATEGORY` | Issue family chosen |
| `CHOOSING_SYMPTOM` | Symptom list |
| `COLLECTING_FACTS` | Engine asked for a typed fact |
| `INVESTIGATING` | Reading devices, VPN, account, and similar rows |
| `WAITING_APPROVAL` | A change is waiting on a person |
| `AWAITING_USER_CONFIRMATION` | User must confirm a fix |
| `CASE_SUMMARY` | Case finished or ticket shown |
| `ASKING_ANYTHING_ELSE` | Another issue, or close |
| `DESCRIBING_OTHER` | Free text that is not on the menu |
| `AWAITING_TICKET_DETAILS` | Talk to IT needs a complaint |
| `AWAITING_UNKNOWN_TICKET_CONFIRM` | Unknown issue, confirm before creating a ticket |
| `CLOSED` | Only Start over continues |

Issue codes map to desks in `services/bakery_api/app/routing.py`. Examples: `ID-*` to Identity Desk, `NET-*` to Network / VPN Desk, `SEC-01` to Security Operations, `GEN-UNKNOWN` to IT Service Desk. Category words (`vpn`, `device`, `security`, and the rest of `CATEGORY_TEAM`) are the fallback when the code is missing.

Guided fixes are functions, not model tool calls:

| Module | Function | Effect |
|---|---|---|
| `tools/unlock_account.py` | `unlock_own_account` | Mock unlock of the caller |
| `tools/vpn_certificate.py` | `renew_mock_vpn_certificate` | Mock VPN certificate renewal |
| `tools/disk_cleanup.py` | `run_mock_safe_cleanup` | Deletes the caller’s temporary files |
| `tools/quick_tools.py` | VPN client update, restart, app cache, print job | Mock endpoint and app fixes |
| `tools/advanced_tools.py` | `create_security_incident` | Ticket assigned to one owner |
| `tools/advanced_tools.py` | `request_entitlement_grant` | Access request |
| `tools/advanced_tools.py` | `install_mock_approved_software` | Mock install |

`services/bakery_api/app/services/others_llm.py` can call Groq when the user picks something off the menu. That call is inside bakery-api. It does not go through AgentCore. If no key is configured, the engine still offers a ticket.

Talk to IT and unknown-issue tickets are inserted in the guided engine with `assigned_team` from `route_team` and `assigned_to` from `route_owner`. Talk to IT uses category `requests`, which routes to Service Catalog Desk, whose preferred owner role is `it_engineer`.

## 9. Freeform agent

`/support?mode=describe` uses the agent API, not the guided engine.

![Freeform agent run](diagrams/06-freeform-run.svg)

`POST /conversations/{id}/runs` checks that the conversation belongs to the session tenant and user, writes the user message and a running `agent_runs` row, and returns immediately. `execute_agent_run` is an `asyncio` task. The UI polls the run.

The run loads the caller from the mock API (`GET /v1/me`) so the tool actor role is the enterprise role, then keeps the last 10 chat messages as history, excluding the current message.

`run_agent` in `services/agent_api/app/agent/factory.py` picks the brain:

![Which brain runs](diagrams/07-which-brain.svg)

AgentCore is configured only when all three are set: `AGENTCORE_ENABLED`, `AGENTCORE_RUNTIME_ARN`, and `TOOL_BRIDGE_PUBLIC_URL`.

Fallback rules:

- Runtime, IAM, network, throttle, or timeout: try the local provider. On AWS that provider is `openai_compatible`, so a second Groq call can run inside `agent-api`. Simulator is used when that is the configured provider.
- Any other AgentCore exception, including a bad model reply: do not switch paths. The error is stored on the run.
- Bedrock failure: the run completes with an honest “Bedrock unavailable” headline. It does not pretend the model answered.
- Ollama failure: fall through to the simulator.

Limits from `services/agent_api/app/config.py`: 25 tool calls and 120 seconds locally; the AWS compose file sets 20 tool calls and 90 seconds. `DEMO_NOW` defaults to `2026-10-31T10:00:00Z` so certificate expiry and similar fixtures stay stable.

### Inside the Runtime

`services/agentcore_runtime/helio_agent/runner.py` builds a Strands `Agent` with `OpenAIModel`:

- API key from SSM in the Runtime region
- Base URL `https://api.groq.com/openai/v1`
- Model `openai/gpt-oss-20b`
- Temperature 0.1, max tokens 2048, parallel tool calls off

The user message is rewritten to list the exact tool names and to ask for a plain-text finish. Up to eight prior turns are prefixed, each truncated to 800 characters. `runtimeSessionId` is a new UUID per invoke, padded to at least 33 characters. It is not the HELIO conversation id, so AgentCore memory is not the chat history. History is whatever `agent-api` put in the payload.

If GPT-OSS calls a tool name that was not offered (`AgentOutcome`, a JSON blob, and similar), and real tool events already exist, the Runtime asks the model once more with no tools, using those events as evidence. If there were no tool events, it retries the tool loop once, then answers with no tools. The point is to return a helpdesk answer instead of failing the microVM.

Package version is the file `services/agentcore_runtime/VERSION` (currently `1.0.3`). The invoke client is `services/agent_api/app/agentcore/client.py` using `bedrock-agentcore` `invoke_agent_runtime` and qualifier `DEFAULT`.

### Simulator

`services/agent_api/app/agent/simulator.py` is a scripted diagnosis. It still calls the real tool functions and the real mock API. The label on the provider says it is not a model. Use it for offline demos and tests.

## 10. Tool bridge

![Tool bridge](diagrams/08-tool-bridge.svg)

Headers:

| Header | Role |
|---|---|
| `X-Helio-Bridge-Token` | Primary key of `agentcore_bridge_sessions` |
| `X-Helio-Timestamp` | Unix time |
| `X-Helio-Signature` | HMAC-SHA256 of `{timestamp}.` + raw body, keyed by `TOOL_BRIDGE_SECRET` |

Skew allowed is 300 seconds. There is no nonce, so a captured request can be replayed inside that window until the session row is revoked. TTL is the greater of `TOOL_BRIDGE_TOKEN_TTL_SECONDS` (default 900) and 900.

The session row is SQLite, not process memory. A `docker exec` health check and the Uvicorn worker share it. Unknown token, bad HMAC, or `run_id` that does not match the session returns 401 or 403. Unknown tool name returns 404. Bad arguments return 422.

`GET /internal/agentcore/ping` is unauthenticated and returns `{ok: true}`. It does not execute a tool.

## 11. Tool catalog

Every freeform tool is registered in `services/agent_api/app/tools/registry.py`. The Runtime bridge imports the same registry. The model cannot call a function that is not in this map.

| Tool | Reads or changes | Notes |
|---|---|---|
| `get_my_identity` | Read | Caller |
| `get_identity_account` | Read | Same tenant only |
| `get_signin_history` | Read | |
| `list_assigned_devices` | Read | |
| `get_device_diagnostics` | Read | MDM, telemetry, patches |
| `get_vpn_sessions` | Read | |
| `get_service_outages` | Read | |
| `get_service_catalog` | Read | |
| `search_current_knowledge` | Read | Current articles; classification follows the caller |
| `list_tickets` | Read | Caller scope |
| `get_ticket` | Read | |
| `create_support_ticket` | Creates a ticket | Owner is chosen by the mock API |
| `propose_account_unlock` | Creates an approval | Does not unlock |
| `propose_vpn_certificate_renewal` | Creates an approval | Execute still checks device compliance |

Each tool returns `ToolResult`: `ok`, `data`, `warnings`, `evidence`, `error`. Evidence rows are stored on the run as `evidence_refs` (source, record id, tenant, classification, trust, version). The system prompt is `services/agent_api/app/agent/prompts/helpdesk_supervisor_v1.md`.

## 12. Tickets

Two stores, one screen. `apps/web/lib/helio-tickets.ts` loads bakery tickets first, then enterprise tickets, and dedupes by id. An id matching `INC-` plus alphanumerics is treated as bakery. Enterprise ids look like `northstar-INC-NEW-…` or the seeded `northstar-INC-0001` style.

### Enterprise mock assignment

`POST /v1/tickets` requires `Idempotency-Key` (1–100 characters). The body is summary, description, category, optional requester, priority default `P3`. Extra fields are rejected. `P1` and creating a ticket for someone else require an IT role. The same key with the same payload replays the first result. The same key with a different payload returns 409.

On first create the API calls `pick_ticket_owner` and inserts `status=assigned`.

![Ticket owner flowchart](diagrams/09-ticket-owner.svg)

“First” means the lowest `user_id` string among active users of that role. Northstar has two engineers and two analysts. New tickets go to the first of each:

| Tenant | Role | Receives new tickets | Also active, not selected |
|---|---|---|---|
| northstar | it_engineer | Rahul Sharma `northstar-EMP-0002` | Kabir Sood `northstar-EMP-0025` |
| northstar | security_analyst | Arjun Nair `northstar-EMP-0011` | Mei Chen `northstar-EMP-0027` |
| northstar | it_manager | Priya Menon `northstar-EMP-0003` | fallback only |
| northstar | tenant_admin | Vikram Rao `northstar-EMP-0004` | fallback only |
| beacon | it_engineer | David Thomas `beacon-EMP-0002` | |
| beacon | security_analyst | Noah Wilson `beacon-EMP-0007` | |
| beacon | it_manager | James Turner `beacon-EMP-0005` | fallback only |
| beacon | tenant_admin | Meera Nair `beacon-EMP-0003` | fallback only |

Categories `identity`, `vpn`, `network`, `device`, `email`, `software`, `business_app`, `onboarding`, `offboarding`, and `procurement` prefer the IT engineer. `security` and `cloud_access` prefer the security analyst. Any unknown category string that still passed validation prefers the IT engineer. The category pattern on the request is the twelve names above, so unknown strings are rejected with 422 before assignment.

Status changes are a separate `PATCH`. Allowed edges are in `VALID_STATUS_TRANSITIONS` in the mock API: `new` can go to `triaged`, `assigned`, or `closed`; `assigned` can go to `in_progress`, `triaged`, or `closed`; and so on through `resolved` and `closed`. Employees cannot patch. IT staff can. A new ticket is already `assigned`, so the next legal step is `in_progress`, not `resolved`.

### Bakery assignment

`route_owner` uses the same idea on Postgres `users` where `is_active` is true, ordered by `user_id`.

| Desk | Preferred role |
|---|---|
| Security Operations | security_analyst |
| Identity Desk, Network / VPN Desk, Endpoint Desk, Application Support, Print Services, Service Catalog Desk, Hardware Desk, IT Service Desk | it_engineer |

The live Northstar bakery database resolves every desk, including Security Operations, to `NS-002` (Rahul Sharma), because that database has an IT engineer and no security analyst. That is the fallback, not a broadcast.

Bakery ticket ids are `INC-` plus a generated suffix. Talk-to-IT tickets are stored as `in_progress` with the owner already set. Enterprise tickets are stored as `assigned`.

## 13. Approvals

Freeform proposals do not change identity or VPN state. They create a row in the mock `approvals` table. Execution is a later call.

![Approval path](diagrams/10-approval.svg)

Rules enforced in the mock API:

- The requester cannot approve their own request.
- A tenant admin cannot approve in place of the engineer.
- Only the approving engineer can execute.
- A second execute of the same approval returns the first result (`idempotent_replay`).
- VPN certificate renewal returns 409 at execution time when the device is non-compliant, even after approval.
- Employees cannot request `mfa_reset`.

The agent API exposes the same lifecycle at `/approvals/...` and `/actions/approvals/...`, and `POST /actions/propose`. The UI approvals page uses those routes. It does not talk to the mock API directly.

Bakery has its own approval tables (`approval_requests`, `action_intents`, `action_executions`) and routes under `/api/approvals` and `/api/actions` (`intents`, `consent`, `execute`). A guided fix that needs a person stops in `WAITING_APPROVAL`. That state is not the enterprise mock approval row.

## 14. Enterprise mock API

Process: `cloudiqs_enterprise_demo_pack/mock_api/app.py`. Database: `ENTERPRISE_DEMO_DB`, default `data/runtime.sqlite` in the pack. Local Compose bind-mounts that file. AWS mounts `/opt/cloudiqs-demo/data/runtime.sqlite`.

Auth: `Authorization: Bearer <persona key>`. The key must exist in `data/fixtures/demo_tokens_INSECURE_PUBLIC.json` and the user must be active. `X-Tenant-ID` does not change the tenant. The tenant is the user’s tenant. A Northstar token requesting a Beacon id gets 404.

`X-Demo-Fault` can simulate `rate_limit` (429) and `timeout_after_commit` (504 after the row is committed) when fault injection is enabled. Local Compose sets `ENABLE_FAULT_INJECTION=1`. AWS compose sets it to `0` on agent-api; the header is still implemented in the mock process itself.

### Routes

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness, mode `synthetic_mock_only` |
| GET | `/v1/me`, `/v1/tenant`, `/v1/users` | Identity |
| GET | `/v1/identity/accounts/{user_id}` | Account state |
| GET | `/v1/identity/signins/{user_id}` | Sign-ins |
| GET | `/v1/devices`, `/v1/devices/{id}/diagnostics` | Devices |
| GET | `/v1/vpn/sessions` | VPN |
| GET | `/v1/tickets`, `/v1/tickets/{id}` | List and read |
| POST | `/v1/tickets` | Create, assign, idempotent |
| PATCH | `/v1/tickets/{id}` | Status, assignee, priority |
| POST, GET | `/v1/tickets/{id}/comments` | Comments |
| POST, GET | `/v1/approvals` and `.../decision`, `.../execute` | Approval lifecycle |
| GET | `/v1/knowledge/search` | Articles, ACL by classification |
| GET | `/v1/services/outages`, `/v1/service-catalog` | Catalog |
| GET | `/v1/analytics` | IT manager scope |
| GET, POST | `/v1/admin/integrations`, `/v1/admin/policy` | Admin |
| GET | `/v1/sources/{source_key}` | Raw source feed, privileged |
| POST, GET | `/v1/security/escalations` | Security queue |
| GET | `/v1/audit`, `/v1/agent/executions` | Audit |

Knowledge: an employee search returns `classification=employees` only. A security analyst also receives `security` articles. `include_superseded=true` is forbidden for an employee.

### SQLite tables

Created by `cloudiqs_enterprise_demo_pack/scripts/generate_data.py` and loaded from CSV into `data/canonical/enterprise.sqlite`, then copied to the runtime file:

| Table | Keys | Holds |
|---|---|---|
| `tenants` | tenant_id | Northstar, Beacon |
| `users` | tenant_id, user_id | People, role, status |
| `devices` | tenant_id, device_id | Owned devices |
| `tickets` | tenant_id, ticket_id | 12 columns; assignee and status live here |
| `knowledge_documents` | tenant_id, document_id | Body, classification, version, status |
| `approvals` | tenant_id, approval_id | Pending and decided actions |
| `actions` | tenant_id, action_id | Executed changes |
| `idempotency` | tenant, actor, operation, key | Replay payload |
| `audit_log` | id | Allow or deny |
| `source_records` | source, tenant, ordinal | HRIS and other feeds |
| `policies` | tenant_id | Policy JSON |
| `integrations` | tenant, integration_key | Connector status |

The running API also creates `ticket_comments` and `escalations` if they are missing.

Ticket insert writes 12 positional columns: tenant, id, requester, assignee, summary, description, category, priority, status, created, updated, attributes JSON.

## 15. Agent API data

SQLite file: `APP_DB_PATH`, default `/data/app.sqlite`. Local Compose uses the named volume `agent_app_db`. AWS bind-mounts `/opt/cloudiqs-demo/data/app.sqlite`.

| Table | Holds |
|---|---|
| `sessions` | session id, tenant, user, persona, bearer, expiry |
| `chat_conversations` | One thread per user |
| `chat_messages` | user and assistant text |
| `agent_runs` | mode, status, model id, input, output JSON, error |
| `run_events` | `run.created`, `run.completed`, `run.failed` |
| `tool_events` | tool name, status, output, error |
| `evidence_refs` | citations attached to a run |
| `action_intents` | proposed actions mirrored for the UI |
| `notifications` | in-app notices |
| `ticket_comments`, `ticket_state_events` | UI-side ticket trail |
| `escalations` | security escalations created through the agent API |
| `connector_changes` | admin enable or disable |
| `policy_versions` | policy edits |
| `knowledge_revisions` | uploaded articles |
| `evaluation_runs`, `evaluation_test_results` | harness output |
| `audit_events` | app audit |
| `usage_events` | usage rows; not a full billing pipeline |
| `agentcore_bridge_sessions` | token, bearer, tenant, user, role, session, run, expiry |

### Agent API routes

Prefixes are on the router. Session cookie required except health and the bridge ping.

| Area | Routes |
|---|---|
| Auth | `POST /auth/demo-login`, `POST /auth/logout`, `GET /auth/session` |
| Health | `GET /health`, `GET /health/ready`, `GET /health/model` |
| Workspace | `GET /workspace/summary` |
| Conversations | `POST/GET /conversations`, `GET /conversations/{id}`, `POST /conversations/{id}/runs` |
| Runs | `GET /runs`, `GET /runs/{id}`, `GET /runs/{id}/events`, `GET /runs/{id}/tool-events` |
| Tickets | `GET/POST /tickets`, `GET/PATCH /tickets/{id}`, comments |
| Devices | `GET /devices`, `GET /devices/{id}` |
| Actions | `POST /actions/propose`, approvals list, decision, execute |
| Approvals | `GET /approvals` |
| Knowledge | `GET/POST /knowledge` |
| Notifications | `GET /notifications`, `POST /notifications/{id}/read` |
| Admin | integrations, users, policy, audit |
| Analytics | `GET /analytics/tickets`, `GET /analytics/agent-runs` |
| Security | `GET /security/findings`, escalations |
| Evaluations | `GET/POST /evaluations/runs`, tests |
| Dev | `POST /dev/reset-demo` (needs confirmation), `GET /dev/status` |
| Bridge | `POST /internal/agentcore/tools`, `GET /internal/agentcore/ping` |

`GET /` reports `synthetic_data: true` and whether AgentCore is configured. CORS allows `localhost:3000`, `127.0.0.1:3000`, and `http://web:3000`.

A run’s `mode` column is `agentcore` when the Runtime is configured, otherwise the `MODEL_PROVIDER` value (`simulator`, `bedrock`, `openai_compatible`, `ollama`).

## 16. Bakery data

Postgres database `bakery`, user `bakery`, password `bakery`, host `bakery-postgres` on the Docker network. This password is the demo default in `compose.aws.yaml`. It is not a production secret.

`services/bakery_api/app/db.py` creates tables on startup and adds `tickets.assigned_to` with `ALTER TABLE` when an older database lacks the column.

| Table | Holds |
|---|---|
| `tenants`, `users`, `accounts`, `sessions` | Northstar demo identity. Users use ids like `NS-002` |
| `devices`, `temporary_files`, `vpn_profiles` | Endpoint and VPN state the guided tools change |
| `services`, `applications`, `app_installations`, `entitlements` | Catalog and access |
| `mailboxes`, `printers`, `print_jobs` | Mail and print cases |
| `security_events` | Security cases |
| `tickets`, `ticket_events` | Guided tickets. `assigned_team` and `assigned_to` |
| `conversations`, `messages`, `cases` | Guided session, including `state` |
| `action_intents`, `approval_requests`, `action_executions` | Guided consent and execution |
| `audit_events` | Guided audit |

### Bakery routes

All are under `/api` on the bakery process, which the browser reaches as `/bakery-api/...`.

| Method | Path |
|---|---|
| POST | `/api/auth/demo-login` |
| GET | `/api/auth/me` |
| POST | `/api/auth/logout` |
| GET | `/api/catalog`, `/api/catalog/issues/{issue_code}` |
| POST | `/api/conversations` |
| GET | `/api/conversations/active`, `/api/conversations/{id}` |
| POST | `/api/conversations/{id}/turns` |
| POST | `/api/actions/intents`, `/{id}/consent`, `/{id}/execute` |
| GET | `/api/actions/{id}` |
| GET | `/api/approvals`, `/pending`, `/{id}` |
| POST | `/api/approvals/{id}/decision` |
| GET | `/api/tickets/mine`, `/{id}`, `/{id}/events` |
| PATCH | `/api/tickets/{id}` |
| POST | `/api/dev/seed/reset` |
| GET | `/api/dev/health`, `/api/dev/stats` |

OpenAPI is `/docs` on the bakery process. From the browser that is `/bakery-api/docs` only if the rewrite is used; the rewrite sends `/bakery-api/docs` to `/api/docs`, not FastAPI’s `/docs`. Use the bakery container directly if you need that schema.

## 17. Configuration

Agent API environment variables that change behavior:

| Variable | Default | Effect |
|---|---|---|
| `MODEL_PROVIDER` | `simulator` local, `openai_compatible` on AWS compose | Local brain when AgentCore is off or down |
| `OPENAI_API_KEY` or `GROQ_API_KEY` | empty | Groq credential for in-process Strands |
| `OPENAI_BASE_URL` | Groq OpenAI URL | |
| `OPENAI_MODEL_ID` | `openai/gpt-oss-20b` | |
| `AGENTCORE_ENABLED` | `0` | Must be on, with ARN and bridge URL, to leave the box |
| `AGENTCORE_RUNTIME_ARN` | empty | Hyd Runtime |
| `AGENTCORE_REGION` | `AWS_REGION` | Must be `ap-south-2` for this account |
| `AGENTCORE_QUALIFIER` | `DEFAULT` | Endpoint name |
| `TOOL_BRIDGE_PUBLIC_URL` | empty | URL the Runtime can reach |
| `TOOL_BRIDGE_SECRET` | empty local default in compose is a dev string | HMAC key |
| `TOOL_BRIDGE_TOKEN_TTL_SECONDS` | `900` | Bridge session life, at least 900 |
| `ENTERPRISE_API_URL` | `http://enterprise-mock-api:8000` | |
| `APP_DB_PATH` | `/data/app.sqlite` | |
| `APP_SESSION_SIGNING_KEY` | dev default | Present; cookie is the raw session id |
| `DEMO_NOW` | `2026-10-31T10:00:00Z` | Clock for fixtures |
| `ENABLE_FAULT_INJECTION` | `1` local, `0` AWS | |
| `BEDROCK_MODEL_ID`, `AWS_BEARER_TOKEN_BEDROCK` | | Only if `MODEL_PROVIDER=bedrock` |
| `EVAL_MODE` | `0` | Evaluation harness |
| `MAX_TOOL_CALLS_PER_RUN` | `25` | AWS compose uses `20` |
| `MAX_RUN_DURATION_SECONDS` | `120` | AWS compose uses `90` |

Web:

| Variable | Effect |
|---|---|
| `AGENT_API_URL`, `BAKERY_API_URL` | Rewrite targets. Read at server start |
| `DEMO_GATE_ENABLED` | `1` on AWS |
| `DEMO_ACCESS_SECRET` | Gate cookie value |
| `ORIGIN_VERIFY_TOKEN` | Optional header check |
| `NEXT_PUBLIC_RUNTIME_BADGE` | `AWS` on the EC2 UI |

Bakery:

| Variable | Effect |
|---|---|
| `DATABASE_URL` | `postgresql+psycopg://bakery:bakery@bakery-postgres:5432/bakery` |
| `ALLOW_DEMO_LOGIN` | `1` |
| `SPECS_PATH` | `/specs` on AWS |
| `OPENAI_*` / `GROQ_API_KEY` | Optional model for off-menu text |

Do not commit `.env`. AWS reads secrets from SSM and from the instance environment. `fast_deploy.py` keeps `AGENTCORE_*` and `TOOL_BRIDGE_*` across recreates.

## 18. How the main clicks are implemented

**Sign in.** Login page posts the persona key to `/api-backend/auth/demo-login`. Agent API inserts `sessions` and sets `helio_session`. The shell calls `GET /auth/session` and then bakery demo-login with the mapped `NS-00x` id, which sets `bakery_session`.

**Guided diagnosis.** The panel creates or resumes a bakery conversation. Each click is a turn. The engine reads Postgres (device, VPN, account, printer, and the rest), may call a mock tool, and either finishes, asks for consent, or inserts one ticket with one `assigned_to`.

**Freeform diagnosis.** The support page creates an agent conversation and posts a run. The background task invokes AgentCore. Tools come back through the bridge into the mock API. The assistant message stored on the conversation is `plain_language_summary`. Poll `GET /runs/{id}` until `completed` or `failed`. Tool names are on `GET /runs/{id}/tool-events`.

**Create a ticket from the agent.** The model calls `create_support_ticket`. The tool posts to mock `/v1/tickets` with a new idempotency key. The response includes `assignee_id`. The model is told in the tool description that security and cloud access go to a security analyst and everything else goes to the IT engineer. The description does not choose the person. The insert does.

**Approve.** The approvals page lists mock approvals via the agent API. Decision and execute are proxied. The mock API checks role, separation of duties, and compliance.

**My tickets.** The page calls bakery `/tickets/mine` and agent `/tickets`, tags `source`, and merges. Opening a bakery id uses bakery ticket routes. Opening an enterprise id uses agent ticket routes.

## 19. Local run and tests

```powershell
copy .env.example .env
docker compose up --build -d
```

Open `http://localhost:3000`. Agent API docs are `http://127.0.0.1:8001/docs`. Mock API is `http://127.0.0.1:8000/docs`. Ports are bound to localhost.

Reset of mutable demo state is destructive and requires `make reset-demo CONFIRM=YES` or `POST /dev/reset-demo` with the confirmation env.

Mock tests must run inside the image. The workstation Python often has a Starlette build that cannot import this FastAPI.

```powershell
docker build -t helio-mock-test .\cloudiqs_enterprise_demo_pack
docker run --rm -e PYTHONPATH=/app helio-mock-test pytest tests/test_mock_api.py -q
```

`PYTHONPATH=/app` is required. Without it, collection fails with `No module named 'mock_api'`.

Agent tests: `docker compose exec agent-api pytest -q`. Web end-to-end: `pnpm test:e2e` in `apps/web` (Playwright). GitHub Actions in `.github/workflows/ci.yml` compiles and checks docs. It does not run these Docker tests.

AWS service rebuild, from the repo root, using AWS CLI v2 (`C:\Program Files\Amazon\AWSCLIV2`), not the pip `aws` entry point:

```powershell
python scripts/aws/fast_deploy.py --service mock
python scripts/aws/fast_deploy.py --service agent
python scripts/aws/fast_deploy.py --service bakery
python scripts/aws/fast_deploy.py --service web
```

Runtime-only update, after bumping `services/agentcore_runtime/VERSION`:

```powershell
$env:HELIO_AGENTCORE_REGION = "ap-south-2"
python scripts/agentcore/update_runtime_hyd.py
```

Rollback uses the previous versioned CodeZip in `deploy/agentcore/state.json`, not the unversioned `deployment_package.zip` alias. `make destroy-agentcore CONFIRM=DESTROY_AGENTCORE` deletes the Runtime and its code. It does not delete EC2, `runtime.sqlite`, or Postgres.

## 20. What is real and what is simulated

| Real in this demo | Simulated |
|---|---|
| HTTP sessions, cookies, role checks | The companies, employees, and devices |
| SQLite and Postgres persistence | HR, IdP, MDM, VPN, and ITSM vendors |
| Idempotency and approval separation | The effect of an unlock or a certificate renewal |
| Strands tool loop and Groq responses on AWS | Bedrock model answers on this account |
| AgentCore Runtime invoke and the HMAC bridge | A production queue or on-call roster |
| Caddy certificate on the sslip.io name | CloudFront |

The agent can be wrong about the words it uses. It cannot bypass the mock API’s tenant filter, and it cannot mark an approval approved by calling a tool. Those checks run in Python after the tool call.

## 21. Limits that are part of the design

- Guided data and freeform data are different databases. The tickets page merges them in the browser. There is no shared ticket primary key.
- Owner selection is the first active user of a role, sorted by id. It is not round-robin, not a queue, and not “everyone in IT”.
- Bakery Northstar in the running demo has no security analyst, so guided security tickets go to the IT engineer `NS-002`. The mock API does have Arjun, so freeform security tickets go to `northstar-EMP-0011`.
- Arjun’s guided session is Vikram’s bakery user.
- The HELIO session cookie is not marked `Secure`.
- Bridge HMAC has a five-minute replay window and no nonce.
- AgentCore does not remember the conversation. The last turns are copied into the prompt.
- The model sometimes calls `propose_vpn_certificate_renewal` more than once in one run.
- One AgentCore runtime serves this demo. It is not a multi-agent platform, and it does not use AgentCore Gateway, Memory, or Policy.
- The $100 budget sends alerts. It does not stop the account.
- Host `pytest` on Windows is not a reliable signal. Run the image.
