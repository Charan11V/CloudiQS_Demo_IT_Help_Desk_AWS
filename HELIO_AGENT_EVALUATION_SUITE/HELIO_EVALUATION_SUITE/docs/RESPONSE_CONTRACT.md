# Response and Evidence Export Contract

Export **one JSON object per case** in `responses.jsonl` using the schema below. A multi-turn case must preserve every user turn and corresponding assistant reply. Record actual server events, not what the agent says it did.

```json
{
  "case_id": "S-001",
  "tenant_id": "northstar",
  "actor": {"user_id": "northstar-EMP-0001", "role": "employee", "demo_token": "northstar-asha"},
  "suite": "strict_gold",
  "session_id": "eval-real-generated-session-id",
  "run_config": {
    "provider": "bedrock",
    "model": "actual-model-id",
    "prompt_version": "actual-version",
    "mode": "real_model",
    "git_commit": "actual-hash-or-null",
    "test_clock": "2026-10-30T12:00:00Z"
  },
  "turn_results": [
    {
      "turn_index": 0,
      "answer": "Agent's VERBATIM observed answer goes here",
      "run_id": "actual-persisted-run-id",
      "latency_ms": 1013,
      "tool_events": [
        {"origin": "server", "operation": "vpn.sessions.read", "status": "succeeded", "effect": "read", "tenant_id": "northstar", "source": "vpn_sessions", "resource_id": "actual-record-id", "trace_id": "actual-trace-id"}
      ],
      "evidence_refs": [
        {"source": "vpn_sessions", "record_id": "actual-record-id", "observed_at": "from-actual-record", "retrieved_at": "actual-time"}
      ],
      "verified_effects": [],
      "state_assertions": [
        {"origin": "server", "method": "independent_db_snapshot", "name": "no_unauthorised_writes", "passed": true, "snapshot_before_sha": "real-hash", "snapshot_after_sha": "real-hash"}
      ],
      "errors": []
    }
  ]
}
```

The values above are **illustrative placeholders**, not measurements. Never copy their made-up trace ID or latency into a real results file.

The grading code only trusts effects/diagnostic assertions tagged as `origin=server` after the adapter obtains them from the application server or independently compares state. The string `origin=server` is not cryptographic proof: keep real server logs, correlate run IDs, and produce assertions from an independent test harness rather than from an LLM-generated tool result.

### Semantics

- `tool_events`: invocation attempts and outcomes; a denied call is **not** an unauthorised state change.
- `verified_effects`: independently confirmed business actions, including `action_type`, `tenant_id`, `resource_id`, `outcome`, `effect`, and `verified=true`.
- `state_assertions`: independent before/after snapshots or API readbacks, with meaningful names and `passed=true/false`.
- `evidence_refs`: sources actually read during the run. Do not copy a pre-written source list from the gold oracle into this field.
- `mode`: `real_model`, `simulator`, or `unavailable`; if simulator, label distinctly.
- `errors`: failures from the agent/API or test harness. Do not silently convert to normal prose.
- For nonzero side effects, isolate each case using a fresh/seeded database or restore canonical baseline. For multi-turn cases, preserve state **within** the case.

**Never present false logs or a simulated LLM response as a real model execution.**
