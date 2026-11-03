# Interview Demo Walkthrough (5–7 minutes)

**Public URL (current):** http://ec2-3-80-12-216.compute-1.amazonaws.com  
**HTTPS / CloudFront:** deferred — plain HTTP on the Graviton EC2 origin is intentional for this cost-capped demo. Demo-gate and session cookies are set **without** the `Secure` flag on HTTP so browsers keep them.  
**Outer gate:** shared demo access secret (SSM `/cloudiqs-demo/DEMO_ACCESS_SECRET`)  
**Persona:** Asha Rao · `northstar-asha` · `northstar-EMP-0001` · device `northstar-DEV-0001`

## Bedrock prerequisite (current console)

See **`docs/BEDROCK_AUTH.md`**. Short version:

1. Bedrock console (**us-east-1**) → **API keys** → short-term key.
2. Use case: **Generate text → Converse** (not Mantle / OpenAI Responses).
3. Put the key in `AWS_BEARER_TOKEN_BEDROCK` on agent-api (not `OPENAI_API_KEY`).
4. Confirm: `GET /api-backend/health/model` → `"verified_live": true`.

Until live Converse works, freeform may soft-fall back to the offline simulator; guided bakery / tickets still work.

## Script

1. **Open the HTTP demo URL** — single Graviton EC2 → Docker Compose (web / agent-api / private mock-api) + Bedrock via instance role (no access keys). Mention CloudFront/HTTPS as optional polish, not current path.
2. **Demo access gate** — enter secret; explain Bedrock cost protection without replacing persona model.
3. **Choose Asha** — tenant Northstar only.
4. **Ask about VPN / laptop issues** — agent investigates via real tools (not chat inventing facts). *Requires Bedrock model access.*
5. **Show conflicting evidence** — expired VPN/device cert, high CPU, low disk, MDM noncompliance, stale CMDB, wrong password hypotheses.
6. **Citations** — evidence resolves to synthetic sources.
7. **Ticket** — at most one; idempotent (works even if Bedrock is blocked).
8. **Approval** — sensitive action needs human approval; wrong persona cannot approve.
9. **Blocked renewal** — certificate renewal blocked while MDM prerequisite fails.
10. **Switch to IT support** — queue / trace / audit.
11. **CloudWatch** — open dashboard `CloudiQSDemo` or recent log group `/cloudiqs-demo/agent-api` for the run id.
12. **Close** — IaC in `infra/cdk`, cost model under ~$20–25/mo running, `make aws-stop-demo` when idle.

Keep the **user journey** primary; AWS console is supporting evidence only.
