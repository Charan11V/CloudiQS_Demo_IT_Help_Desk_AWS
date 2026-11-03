# MCP & Bedrock AgentCore — honest status

## MCP integrations

**Status: Not used in the deployed demo (by design).**

HELIO tools are **in-process Strands/`TOOLS` registry callables** inside `services/agent_api` (local mode), or the same registry executed via an **authenticated application-side tool bridge** when AgentCore Runtime hosts the Strands loop. There is no separate MCP server/client hop and no AgentCore Gateway.

Why not MCP here:

- Keeps the mock API private (no extra gateway surface).
- Preserves “LLM proposes, backend decides” without exposing tools over an additional protocol.
- Avoids AgentCore Gateway / public MCP cost and complexity for a credit-capped hiring demo.

If a future production design needs MCP, wrap the same registry behind an authenticated private MCP server — do not publish enterprise-mock-api.

## Bedrock AgentCore

**Status: Implementation complete; Runtime create blocked by account quota = 0.**

What is ready in-repo and in AWS:

| Piece | Status |
|-------|--------|
| CodeZip Strands agent (`services/agentcore_runtime`) | Packaged (29.6 MiB arm64), uploaded to S3 |
| IAM `HelioAgentCoreRuntimeRole` | Created |
| SSM Groq key + tool-bridge secret | Stored (SecureString) |
| EC2 invoke policy `HelioAgentCoreInvoke` | Attached to runtime instance role |
| agent-api bridge + IAM invoke client | Deployed to EC2 |
| Web middleware allowlist for bridge | Deployed |
| Ops: `make deploy-agent` / `status` / `logs` / `rollback` / `destroy-agentcore` | Implemented |

**Blocker:** Applied quota `Total Agents per Account` = 0. Support/Service Quotas case `179368190700066` opened. Retry: `python scripts/agentcore/wait_and_deploy.py`.

**Model path:** Groq GPT-OSS-20B via OpenAI-compatible API — **not** Bedrock foundation models (account still lacks FM authorization). Verified live: model returns `GPT_OSS_LIVE_OK`.

See `AGENTCORE_DEPLOYMENT.md` for architecture, costs, and commands.

## Knowledge / RAG (related honesty)

**Status: Keyword + ACL corpus retrieval — not vector RAG / Bedrock Knowledge Bases.**

`search_current_knowledge` and `GET /api-backend/knowledge?q=` score title/body term hits per tenant with classification visibility. Evidence: `knowledge_search_vpn` in `docs/SCORECARD_EVIDENCE.json`.
