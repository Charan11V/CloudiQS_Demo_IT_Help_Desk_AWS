# Feature-by-feature scorecard (updated)

Evidence artifacts:

- `docs/SCORECARD_EVIDENCE.json` — `python scripts/qa/scorecard_evidence.py` (**20/20** last run)
- `docs/EVAL_RESULTS.json` — curated evaluation harness pass counts
- `docs/RESTORE_DRILL.json` — `python scripts/aws/restore_drill.py`
- `docs/PERSISTENCE_PROOF.json` — `python scripts/aws/persistence_recreate_proof.py`
- `docs/ui-home-guided.png` — live browser screenshot (guided CONNECTED, 10 options)
- `docs/MCP_AND_AGENTCORE.md` — MCP/AgentCore honesty
- `docs/SCALE_APPROVAL.md` — approval-gated scale (no auto spend)
- `.github/workflows/ci.yml` — quality gate on push/PR

| Requirement | Assessment | Findings / evidence |
|---|---|---|
| AWS deployment | **Implemented** | EC2 Graviton + Docker Compose (`compose.aws.yaml`) |
| Frontend | **Implemented** | Next.js 15, role routes, guided+tickets UX; live screenshot |
| Backend APIs | **Implemented** | agent-api, bakery-api, enterprise-mock-api |
| Infrastructure as code | **Implemented** | AWS CDK (`infra/cdk`) + budgets + CPU→SNS notify |
| Cost controls | **Implemented** | No NAT/RDS/EKS; budgets; stop/start; approval-gated scale |
| Strands agent framework | **Implemented (code)** | Strands+Bedrock wired; live model depends on account access |
| Live Bedrock reasoning | **Blocked / mitigated** | Model-access errors; freeform **simulator fallback**; guided bakery does not need Bedrock |
| Bedrock AgentCore | **Not deployed (documented)** | `docs/MCP_AND_AGENTCORE.md` — intentionally out of cost envelope |
| Guided troubleshooting | **Implemented** | Catalogue-driven bakery; 10 root options in evidence + UI screenshot |
| Free-text AI troubleshooting | **Implemented (demo path)** | Conversation+run API verified; simulator when Bedrock unauthorized |
| Real simulated data mutations | **Implemented (demo)** | Bakery tools mutate Postgres; enterprise mock mutates SQLite; approval execute mutates identity |
| Ticket creation/updates | **Implemented** | Dual sources merged in UI; IT Resolved/Close; In progress/Closed selector |
| Ticket routing to specialists | **Implemented** | `services/bakery_api/app/routing.py` issue/category→team (evidence unit check) |
| Approval workflows | **Implemented (E2E tested)** | Propose → self-approve blocked → IT decide → execute (evidence JSON) |
| Role-based access | **Implemented (tested)** | Employee blocked from admin (403 in evidence) |
| Multi-tenant isolation | **Implemented (tested)** | Beacon session: zero `northstar-` tickets; knowledge scoped |
| Audit trail | **Implemented (bakery)** | `GET /bakery-api/tickets/{id}/events` + UI lineage panel |
| Knowledge retrieval / RAG | **Partial → Implemented (corpus)** | ACL-filtered keyword corpus search (`/knowledge?q=`); **not** vector embeddings |
| MCP integrations | **Not used (documented)** | In-process tools by design — see MCP doc |
| Evaluations | **Implemented (measured)** | `docs/EVAL_RESULTS.json` — 20 executed / 20 passed / 0 failed |
| Observability | **Implemented (demo)** | CW logs + dashboard + **CPU alarm → SNS** (`ScaleNotifyTopicArn` deployed) |
| HTTPS / session transport | **Missing on live URL** | HTTP EC2 DNS; CloudFront deferred (account verification); Secure cookies only on HTTPS |
| CI/CD automation | **Implemented (basic)** | GitHub Actions compile/routing/compose/docs guards |
| Data persistence across redeploy | **Fixed** | Compose seed-if-empty (no `--reset`); recreate proof script |
| Recovery / resilience | **Implemented (drill)** | `restore_drill.py` backup+checksum evidence |
| UI quality and responsiveness | **Implemented (spot-checked)** | Live guided home screenshot `docs/ui-home-guided.png` |
| Documentation | **Implemented** | Architecture, cost, walkthrough, scorecard, scale, MCP/AgentCore |
| Scale-ready without spend | **Control plane Implemented** | Alarm notify + `approve_scale.py` records approval **without** starting extra compute |

## How to refresh evidence

```bash
# after aws login / export-credentials
python scripts/qa/scorecard_evidence.py
python scripts/aws/restore_drill.py
python scripts/aws/persistence_recreate_proof.py
```

## Honest remaining limits

1. **Live Bedrock** — Current console is API-key first; use Converse + `AWS_BEARER_TOKEN_BEDROCK` (see `docs/BEDROCK_AUTH.md`). Soft-falls back to simulator until Converse succeeds.
2. **HTTPS** needs CloudFront/custom domain after account verification (LE cannot issue for `*.amazonaws.com`).
3. **MCP / AgentCore Runtime** deliberately not deployed for this credit-capped hiring demo.
4. **Knowledge** is keyword+ACL retrieval over a synthetic corpus — not Bedrock Knowledge Bases / embeddings.
