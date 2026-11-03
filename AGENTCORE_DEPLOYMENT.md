# HELIO → Amazon Bedrock AgentCore Deployment

Genuine **AgentCore Runtime** hosting for the HELIO Strands agent, while the existing Next.js + FastAPI + enterprise-mock Docker/EC2 application stays intact.

## Architecture

```
Browser → Next.js (EC2 us-east-1) → agent-api (FastAPI)
                                        │
                                        │ IAM InvokeAgentRuntime (instance role)
                                        ▼
                          AgentCore Runtime (CodeZip, ARM64 microVM, ap-south-2)
                                        │  Strands + Groq GPT-OSS-20B
                                        │  (OpenAI-compatible API — NOT Bedrock FMs)
                                        │
                                        │ HMAC + ephemeral SQLite bridge token
                                        ▼
                agent-api /internal/agentcore/tools  →  enterprise-mock-api (Docker DNS)
```

**Why an application-side tool bridge?**  
AgentCore cannot resolve Docker names like `enterprise-mock-api`. VPC/NAT/Lattice would add large fixed cost. The bridge keeps the mock API private, never sends enterprise bearer tokens to AgentCore, and uses HMAC + short-lived per-run tokens persisted in SQLite (so callbacks work across processes/workers).

**HTTPS:** CloudFront create is still blocked (`account must be verified`). Interim TLS uses **Caddy + Let's Encrypt/ZeroSSL** on `https://<eip>.sslip.io` (see `scripts/aws/enable_https_caddy.py`). After AWS verifies the account, run `scripts/aws/enable_https_cloudfront.py` for `*.cloudfront.net` and update the tool-bridge URL.

**What we deliberately did not deploy:** AgentCore Gateway, Memory, Policy, Evaluations, VPC mode, NAT, ALB, RDS, EKS, Bedrock foundation models.

## GPT-OSS-20B

| Setting | Value |
|--------|--------|
| Provider | Groq (OpenAI-compatible) |
| Base URL | `https://api.groq.com/openai/v1` |
| Model ID | `openai/gpt-oss-20b` |
| Secret store | SSM SecureString `/cloudiqs-demo/OPENAI_API_KEY` in **both** `us-east-1` and `ap-south-2` |
| Retrieval | Runtime role `ssm:GetParameter` at invoke time (region = Runtime `AWS_REGION`) |

## Local development (no AgentCore)

```powershell
$env:Path = "C:\Program Files\Amazon\AWSCLIV2;$env:USERPROFILE\.local\bin;$env:Path"
copy .env.example .env   # if needed; set OPENAI_API_KEY
make dev
# or: python scripts/agentcore/helio_ops.py dev
```

`AGENTCORE_ENABLED=0` by default in local Compose. Local path: Strands inside `agent-api` → Docker `enterprise-mock-api`.

## Region choice (important)

| Region | AgentCore `Total Agents` quota | Bedrock FM invoke | Notes |
|--------|--------------------------------|-------------------|-------|
| `us-east-1` | **0** (case still open) | `NOT_AUTHORIZED` | Existing EC2 demo host |
| `us-west-2` | **0** | `NOT_AUTHORIZED` | Same account soft-limit |
| **`ap-south-2` (Hyderabad)** | **1000** | Catalog visible; invoke still `NOT_AUTHORIZED` | **Runtime deployed here** |

**Live Runtime:** `arn:aws:bedrock-agentcore:ap-south-2:672281861394:runtime/helio_gptoss_agent-EAdCtN2scG`  
GPT-OSS-20B (Groq) verified inside that Runtime. EC2 app in `us-east-1` invokes cross-region via IAM; tool bridge callbacks hit the demo URL in `us-east-1`.

## Deploy AgentCore only (fast updates)

```powershell
$env:Path = "C:\Program Files\Amazon\AWSCLIV2;$env:USERPROFILE\.local\bin;$env:Path"
$env:HELIO_AGENTCORE_REGION = "ap-south-2"
aws sts get-caller-identity   # aws login if needed
# Preferred fast path (existing Hyd runtime):
python scripts/agentcore/update_runtime_hyd.py
# Or unified ops:
make deploy-agent
```

This will:

1. Ensure IAM role `HelioAgentCoreRuntimeRole` + S3 code bucket in `ap-south-2`  
2. Mirror Groq key / bridge secret into SSM (never uploads `.env`)  
3. `uv pip install` **Linux arm64** wheels into a CodeZip (no Docker/QEMU)  
4. Create/update AgentCore Runtime + DEFAULT endpoint  
5. Write runtime ARN / bridge URL into SSM (`us-east-1` for the app)

Bump `services/agentcore_runtime/VERSION` before each intentional release. Typical update: tens of seconds after packaging.

## Wire EC2 app to AgentCore

```powershell
python scripts/agentcore/patch_ec2_agentcore_env.py
# After agent-api / middleware changes:
python scripts/aws/fast_deploy.py --service agent
make deploy-web
# Or everything:
make deploy-all
```

`fast_deploy.py` now preserves `AGENTCORE_*` and `TOOL_BRIDGE_*` from `.env.agentcore` / SSM so recreates do not drop Runtime wiring.

## Ops commands

| Command | Purpose |
|---------|---------|
| `make dev` / `python scripts/agentcore/helio_ops.py dev` | Local Docker + GPT-OSS |
| `make deploy-agent` / `update_runtime_hyd.py` | AgentCore CodeZip only |
| `make deploy-web` | Frontend fast deploy on EC2 |
| `make deploy-all` | Agent + EC2 env patch + compose services |
| `make agentcore-status` | Runtime / SSM / versions |
| `make agentcore-logs` | CloudWatch agent logs (7-day retention) |
| `make agentcore-rollback` / `rollback.py` | Previous **versioned** CodeZip |
| `make destroy-agentcore CONFIRM=DESTROY_AGENTCORE` | Delete Runtime/role/code objects only |

State file: `deploy/agentcore/state.json` (runtime id, ARN, version history).

### Verification scripts

```powershell
python scripts/agentcore/diag_bridge.py          # signed bridge → get_my_identity
python scripts/agentcore/debug_tool_invoke.py    # AgentCore → bridge tool
python scripts/agentcore/e2e_agentcore_tools.py  # identity + VPN tools
python scripts/agentcore/e2e_app_path.py         # UI/API → AgentCore → tools
```

## Security

- No AWS keys in browser; InvokeAgentRuntime uses EC2 instance role.  
- No Groq key in AgentCore control-plane env vars; loaded from SSM at runtime.  
- Tool bridge: HMAC-SHA256 + 5‑minute skew + ephemeral bridge token stored in SQLite (`agentcore_bridge_sessions`). Enterprise bearer stays on agent-api.  
- Demo gate allowlists `/api-backend/internal/agentcore/*` for Runtime callbacks only.  
- CloudWatch retention 7 days; avoid logging secrets.  
- Existing budget `CloudiQSDemo-Monthly` **alerts only** — not a hard spend cap.

## Cost (incremental, hiring-demo traffic)

Assumptions: Runtime in `ap-south-2`, app in `us-east-1`, <500 agent invocations/month, CodeZip <50 MiB, no NAT/ALB/Gateway/Memory.

| Item | Estimate |
|------|----------|
| AgentCore Runtime (pay-per-use) | Low single-digit USD at demo traffic (verify current [AgentCore pricing](https://aws.amazon.com/bedrock/agentcore/pricing/)) |
| S3 CodeZip storage | << $0.05 / month |
| SSM SecureString params | Free tier / negligible |
| Cross-region invoke (us-east-1 → ap-south-2) | Negligible at demo volume |
| CloudWatch Logs (7d) | Typically < $1 at demo volume |
| Groq GPT-OSS | Billed by Groq, not AWS |
| Avoided | NAT (~$32+/mo), ALB, Always-on AgentCore capacity, Bedrock FM |

EC2 / EBS / public IPv4 already exist for the demo stack and are **not** incremental to AgentCore.

## Teardown

```powershell
make destroy-agentcore CONFIRM=DESTROY_AGENTCORE
```

Does **not** destroy CloudiQSDemoStack, EC2, SQLite, ECR images, or bakery data.

## Troubleshooting

| Symptom | Check |
|---------|--------|
| Runtime CREATE_FAILED | `make agentcore-logs`; zip must be arm64 wheels |
| Tools fail `invalid bridge authentication` | `TOOL_BRIDGE_SECRET` on EC2 vs Hyd SSM; re-run `patch_ec2_agentcore_env.py` |
| Tools fail `bridge session expired or unknown` | Bridge sessions must be SQLite-backed; redeploy agent-api |
| Soft “GPT-OSS unavailable” from UI | AgentCore path threw; check Runtime logs; do not rely on local fallback when AgentCore is configured |
| AccessDenied on invoke | Instance role policy `HelioAgentCoreInvoke` for `ap-south-2` ARN |
| Empty smoke response | Confirm endpoint DEFAULT READY; session id ≥ 33 chars |
| CFN stack not found from patch script | App stack is in **us-east-1**; patch script must not use Hyd as default for CFN |

## Layout

```
services/agentcore_runtime/        # CodeZip Strands agent
services/agent_api/app/agentcore/   # IAM client + SQLite bridge sessions
scripts/agentcore/                  # deploy / ops / e2e
deploy/agentcore/state.json         # deployment state
```

## Verified status (2026-11-03)

- Runtime **READY** `helio_gptoss_agent-EAdCtN2scG` in `ap-south-2`, CodeZip **v1.0.3**
- Live Groq GPT-OSS-20B inside AgentCore (`verified_live: true`, not simulator)
- Tool bridge: `get_my_identity` + `get_vpn_sessions` HTTP 200 from Runtime
- App path: conversation run `mode=agentcore` diagnosed VPN cert expiry with 5 tool events including approval proposals
- Tenant isolation: cross-tenant conversation access denied
- Local Docker path unchanged (`AGENTCORE_ENABLED=0`)
