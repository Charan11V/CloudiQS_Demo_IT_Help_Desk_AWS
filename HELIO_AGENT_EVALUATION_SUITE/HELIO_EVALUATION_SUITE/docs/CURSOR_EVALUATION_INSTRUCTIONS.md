# CURSOR MASTER TASK — IMPLEMENT FULL HELIO EVALUATION

You are building HELIO, an AWS-aligned Docker-local enterprise IT helpdesk agent, and must now implement **real, independent, repeatable evaluation** using the attached HELIO_EVALUATION_SUITE. Do not stop after importing case files or displaying an attractive evaluation dashboard.

## Non-negotiable process

1. Read `HELIO_EVALUATION_SUITE/README.md`, `docs/RESPONSE_CONTRACT.md`, `docs/JUDGE_RUBRIC.md`, and `docs/MODEL_AND_ENV_SETUP.md` completely. Read the original `cloudiqs_enterprise_demo_pack/docs/REFERENCE_FLOWS.md` and `SOURCE_AUTHORITY.md`.
2. Validate the suite using `python tools/validate_suite.py` and run its Python unit tests. If any existing cases conflict with actual fixture data, preserve the raw dataset, log the conflict, and correct the case oracle explicitly with provenance. Never rewrite business evidence merely to improve passing scores.
3. **Implement a real adapter**, `tools/helio_adapter.py` with `invoke_case(case, turn_index, user_text, session_id)`. Connect to HELIO's actual authenticated chat endpoint. Identify actor from a trusted demo session/token, submit the actual user text, retain conversation context across turns, await real completion, extract VERBATIM agent answer, real provider/model, actual persisted tool events and source refs.
4. Every scenario starts from a clean, reproducible seed state unless it deliberately tests multi-turn state persistence. Reset between cases, not between turns. Store a fixed scenario clock or clearly label historical fixture timestamps; use isolated databases for parallel tests.
5. Implement `fault_injection` settings using **the existing mock service's supported faults** or additional strictly local failure controls. A requested fault that is not implemented must be `SKIPPED_UNSUPPORTED`, never treated as tested. Do not inject fabricated tool events.
6. For actions, gather **independent before/after state snapshots** of authoritative tables/API outcomes (tickets, approvals, actions, user accounts and audit logs) and add `verified_effects` / `state_assertions`. A 200 HTTP or affirmative text isn't enough. Implement exact idempotency, approval expiry, self-approval, tenant-scope and altered-payload checks.
7. Keep the private oracle in a **separate evaluator-only Docker container** and deny its access to the agent process, any agent tool, web/public assets, uploads and knowledge index. Test this isolation.
8. Support provider modes honestly. For Bedrock, call the actual configured Bedrock model and capture the real run. For simulator, test deterministic workflows but **never call simulator output LLM accuracy**. AgentCore is NOT running merely because Strands runs inside Docker.
9. Implement independent AI judging (`tools/score_responses.py`) with separate model credentials/config. Judge the COMPLETE conversation with private gold and recorded evidence. Use a Bedrock or OpenAI-compatible judge as documented. No API key in code.
10. Run the 105-case core regression first (real-model runs may incur cost). Then 50 strict cases, 36 multi-turn, 51 adversarial, 36 metamorphic. Keep 160 older exploratory cases separate; their oracle is provisional.
11. Build **all 36 UI/workflow acceptance tests** as Playwright + backend/API checks against the actual app. Introduce stable selectors and verify meaningful state, not just element visibility. At least one mobile view, keyboard controls, light/dark, wrong-role deep links and independent tenant boundary checks.
12. Integrate evaluator into HELIO's Evaluation Lab UI with real run progress, type/provider labels, per-category success rates, failure drill-down, trace IDs, source citations, current prompt version, comparison runs, cost and latency. The UI must render honest empty/error/skipped states, not generated passing figures.
13. Generate all outputs under `reports/<run_id>/`: `responses.jsonl`, `grades.jsonl`, `summary.json`, `report.md`, `review_bundle.jsonl`, logs and Playwright screenshots. Never leak oracle into review bundle or static build.
14. After any critical failure, fix the code/policy, rerun the failed case on a fresh state, and rerun related regressions. Verify the fix across Northstar and Beacon.
15. Create an operator command (`make eval-core` and `make eval-all`, or equivalent), document model/provider setup, limits and reproducibility, and show a real test run with explicit counts and unresolved failures. **Do not mark incomplete tests as passed.**

## Deliverables checklist

- [ ] Runnable adapter invoking genuine HELIO agent and preserving all turns.
- [ ] Independent evaluator-only access to private oracle.
- [ ] Real provider and model provenance in every response record.
- [ ] Verifiable tool traces, state readback, and hard safety vetoes.
- [ ] AI judging and calibrated written feedback, with failed judge calls visible.
- [ ] Truthful results page and persisted run history.
- [ ] Browser/API checks for 36 UI cases, not simply screenshots.
- [ ] Deterministic seed reset, fault setup and teardown.
- [ ] All tests actually executed or clearly marked skipped with reasons.
- [ ] Sanitised export for external review (`review_bundle.jsonl` + `report.md`).

**Definition of completion:** The real agent has been evaluated with recorded input/output, trustworthy evidence of business state, an independent model judge, and inspectable reports. A dashboard with fake green badges is not completion. Do the work in the Docker-local app first; no need to deploy AgentCore Runtime for this phase.
