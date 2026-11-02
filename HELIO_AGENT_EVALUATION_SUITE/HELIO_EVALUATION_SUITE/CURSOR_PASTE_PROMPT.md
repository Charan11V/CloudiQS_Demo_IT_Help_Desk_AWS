# Paste this into Cursor Agent after extracting the evaluation suite into the HELIO project

You are now responsible for making HELIO measurable and verifiably correct, not simply good-looking. Build and run the independent evaluation system in `HELIO_EVALUATION_SUITE/` end-to-end against the real Docker-local app.

Read these files in full before changing code:
- `HELIO_EVALUATION_SUITE/README.md`
- `HELIO_EVALUATION_SUITE/docs/CURSOR_EVALUATION_INSTRUCTIONS.md`
- `HELIO_EVALUATION_SUITE/docs/RESPONSE_CONTRACT.md`
- `HELIO_EVALUATION_SUITE/docs/JUDGE_RUBRIC.md`
- `HELIO_EVALUATION_SUITE/docs/FEATURE_COVERAGE_MAP.md`
- The original enterprise dataset's `docs/REFERENCE_FLOWS.md` and `docs/SOURCE_AUTHORITY.md`

## Execute, don't just explain

1. Validate the 369-case suite; run and fix evaluator unit tests first.
2. Inspect the actual HELIO FastAPI/chat/SSE/auth interfaces and implement `tools/helio_adapter.py` to call the REAL Strands agent with the selected actor and tenant, preserving state across each multi-turn case and resetting seed state between cases. Keep original backend security controls intact.
3. The adapter must capture verbatim responses, model/provider/prompt version, retrieved evidence refs, tool calls, trace IDs, persisted audit events, error handling, latency and actual external mock business state. Do not simulate an agent response during an actual LLM evaluation run.
4. Make deterministic test setup and independent before/after state verification, especially for cross-tenant access, approval self-grant, expiry, payload substitution, ticket timeout-after-commit, idempotent replay, rate limits, cancelled operations, source conflicts and malicious retrieved documents.
5. Enforce strict separation: the Strands agent, its tools, RAG index and browser must never access `cases/private_oracle`. Put the gold file only in a separate evaluator process/container. Verify the agent cannot read it.
6. Use a separate independently configured LLM-as-judge to grade agent answers against gold expectations, with six rubric dimensions, structured JSON output, failure reasons, and corrected-answer suggestions. The judge is not allowed to invent action outcomes. Handle invalid judge output and outages visibly.
7. Use `tools/score_responses.py` and hard vetoes from verified server effects so an eloquent response cannot receive a pass after an unsafe mutation. Missing trace/snapshot is UNVERIFIED rather than PASS.
8. Run `CORE_REGRESSION.jsonl` first; then strict gold, multi-turn, adversarial, metamorphic. Treat the existing 160-case legacy catalogue as exploratory, since its old oracle is not verified for hard correctness.
9. Implement executable Playwright/API tests for all 36 `ui_e2e` cases with actual assertions, role/session boundaries and persistence; no screenshot-only success.
10. Add real evaluation-run history to the HELIO dashboard: progress, counts by category, actual judge mode, prompt/model version, traces, error states, failures, rerun actions, comparable release candidates, and explicit unsupported/skipped cases.
11. Check `docs/FEATURE_COVERAGE_MAP.md` against built features. Add explicit cases for implemented but uncovered features before declaring them complete; never count fixture support as deployed functionality.
12. Run the app in Docker and independently verify what actually happened. Fix each issue, rerun targeted regressions and the core suite, and export `reports/<run_id>/review_bundle.jsonl` plus `report.md` for external human review.
13. Final report MUST state: number of actual agent cases executed, actual model/provider and costs if known, judge cases completed, judge errors, Playwright tests passing, verified safety failures, unverified cases, skipped cases/reasons, git commit and known limitations.
14. Do not silently replace Bedrock with deterministic simulation. If model credentials are not configured, run only documented offline API/testing mode and report the missing dependency. Do not claim that AgentCore is running because Strands runs in Docker.
15. Do not stop at the initial integration. Use all available tools to implement, execute, inspect, debug, and retest. If genuinely blocked, record the blocker and provide completed work and exact remaining tasks. Do not invent completion or a benchmark score.

Prioritise **correctness, traceability, multi-tenant boundaries, controlled actions, precise evidence, and usable UI** over cosmetic green checkmarks. The entire point is to impress a real CloudiQS engineer by showing reproducible production-oriented failure engineering.
