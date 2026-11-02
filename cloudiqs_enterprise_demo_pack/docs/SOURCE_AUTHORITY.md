# Field-Specific Source Authority and Contradictory Evidence

There is **no single system of truth for the entire enterprise**. Use a per-field precedence strategy, timestamps, and evidence provenance.

| Question | Primary authority | Secondary corroboration | Common trap |
|---|---|---|---|
| Is this person employed? | Effective HRIS lifecycle record | Offboarding task | Enabled directory account does NOT mean employed |
| Is an account locked? | Current IdP directory state and sign-in logs | Helpdesk ticket | HRIS status is not identity account state |
| Who owns an assigned managed device? | Current MDM primary-user association plus authorised asset reconciliation | CMDB, procurement | CMDB may be stale or reflect financial custodian rather than user |
| Did VPN fail, and why? | Current VPN gateway events / certificate evidence | Device health, sign-in logs | Historical ticket comment is a hypothesis |
| Is device compliant? | Verified current MDM compliance | EDR, patch data | Healthy antivirus is not complete device compliance |
| Is there an enterprise outage? | Internal service health, incident commander updates | Vendor global status | “Vendor operational” may not cover local enterprise network |
| Is a policy current? | Signed, effective, scoped tenant policy + published latest KB | Historical KB | Old KB, vendor note, and chat should never override approved policy |
| Is an action authorised? | Deterministic server-side policy and valid human approval | Agent rationale | LLM, chat text or admin UI alone never grant privilege |
| Was an external write committed? | Target-system state and idempotency ledger | Request logs | HTTP timeout is NOT evidence of failure |
| Is this expense exact? | Final provider billing or reconciled financial ledger | Agent usage counters | Token usage costs are estimates until billed |
| Has support resolved the issue? | Verified outcome plus agreed ticket completion rule | Agent summary / CSAT | A closed ticket does not prove employee-confirmed fix |

## Specific contradictions built into the source data

See `data/fixtures/conflict_manifest.json` for 20 cross-source conflicts, IDs, risk levels and affected records. Not all disagreements are errors: different systems can each be correct about a different concept. Preserve raw values alongside the reconciled explanation.

## Event-time versus ingestion-time

An identity event can occur before a ticket, yet be ingested after it. A source's `updated_at` may be the sync time, not occurrence. Keep `event_time`, `ingested_at`, `last_synced_at` and agent retrieval time distinct. Define an allowed staleness threshold by source and confidence requirements by action.

## Source security

Apply tenant filtering and document classification **before** passing retrieved content to the model. All external and user-supplied text, including comments and KB documents, should be considered untrusted instructions. Safe actions are determined by the backend policy engine, regardless of retrieved text.
