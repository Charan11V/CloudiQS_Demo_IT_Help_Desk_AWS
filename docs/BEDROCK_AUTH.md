# Bedrock auth for this demo (current AWS docs)

Sources (current):

- [Quickstart](https://docs.aws.amazon.com/bedrock/latest/userguide/getting-started.html)
- [API keys](https://docs.aws.amazon.com/bedrock/latest/userguide/api-keys.html)
- [Responses API / endpoints](https://docs.aws.amazon.com/bedrock/latest/userguide/inference-responses-api.html)
- [Simplified model access](https://aws.amazon.com/blogs/security/simplified-amazon-bedrock-model-access/) (Model access page retired)

## What the new Bedrock console is showing you

The onboarding UI is **API-key first**. There is no “enable Nova Lite” entitlement page anymore in commercial Regions. That is expected.

You will see choices like:

| Console option | Maps to | Use for HELIO? |
|---|---|---|
| Generate text → **Converse** | `bedrock-runtime` Converse API | **Yes — this app** |
| Generate text → Responses / Invoke | OpenAI-compatible or Invoke | Not needed |
| Stream → Converse | ConverseStream | Optional later |
| `OPENAI_API_KEY` + Groq + `openai/gpt-oss-20b` | OpenAI-compatible Strands path | **Yes — current LLM while Bedrock is blocked** |
| `OPENAI_API_KEY` + `bedrock-mantle` + `openai.gpt-oss-*` | Mantle OpenAI SDK path | Optional later (same account auth hold today) |

## Right path for CloudiQS / HELIO

### Current LLM — GPT-OSS-20B via Groq (`MODEL_PROVIDER=openai_compatible`)

Bedrock Converse is **NOT_AUTHORIZED** on this account (Applied TPM=0). Use Groq’s hosted GPT-OSS-20B:

```bash
MODEL_PROVIDER=openai_compatible
OPENAI_API_KEY="<groq-api-key>"   # or GROQ_API_KEY
OPENAI_BASE_URL=https://api.groq.com/openai/v1
OPENAI_MODEL_ID=openai/gpt-oss-20b
```

Key: https://console.groq.com/keys — verify with `GET /health/model`.

### Bedrock Converse (when account is authorized)

This repo also supports **boto3 + Strands BedrockModel + Converse** (`MODEL_PROVIDER=bedrock`, `BEDROCK_MODEL_ID=amazon.nova-lite-v1:0`, region `us-east-1`).

### Option A — Bedrock API key (matches the new console)

1. Console region: **US East (N. Virginia) `us-east-1`** (same as the demo EC2).
2. Bedrock → **API keys** → generate **short-term** key (preferred) or long-term (exploration only).
3. In the “choose your use case” wizard, pick **Generate text → Converse** (not Mantle/Responses).
4. Set on the **agent-api** container / compose env:

```bash
AWS_BEARER_TOKEN_BEDROCK="<paste-bedrock-api-key>"
MODEL_PROVIDER=bedrock
BEDROCK_MODEL_ID=amazon.nova-lite-v1:0   # or us.amazon.nova-lite-v1:0
AWS_REGION=us-east-1
```

5. Requires **boto3 ≥ 1.39** (older boto3 ignores `AWS_BEARER_TOKEN_BEDROCK`).
6. Verify: `GET /api-backend/health/model` → `"ok": true`, `"verified_live": true`.

Bedrock Mantle (`OPENAI_BASE_URL=https://bedrock-mantle...`) is optional later; today the same account hold blocks it. Prefer Groq for GPT-OSS-20B until Support unlocks Bedrock.

### Option B — IAM instance role (preferred long-term on EC2)

Leave `AWS_BEARER_TOKEN_BEDROCK` empty. The EC2 role `CloudiQSDemoRuntimeRole` already allows `bedrock:InvokeModel*`. Compose blanks static access keys on purpose.

If role-based Converse still fails, use Option A temporarily, then fix role/SCP/payment and remove the key.

## Agent Toolkit

`aws configure agent-toolkit` / Agent Toolkit MCP helps **Cursor** talk to AWS (CLI, skills, MCP). It does **not** replace Bedrock API keys or Converse wiring for the demo containers. Optional for local agent productivity; not required to unblock Nova Lite on EC2.

## Security

- Never commit API keys. Prefer short-term keys.
- If a key was pasted into chat or a ticket, **deactivate/reset** it in Bedrock → API keys.
- Store runtime secrets in SSM / instance env (`/opt/cloudiqs-demo/env.sh`), not git.
