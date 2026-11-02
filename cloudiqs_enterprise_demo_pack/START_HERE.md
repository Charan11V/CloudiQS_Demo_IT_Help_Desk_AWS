# Start here: CloudiQS-style Enterprise IT Synthetic Demo Data

**What is this?** A full synthetic enterprise IT environment for building a one-day AI Helpdesk demo with realistic fragmented data and production-style controls. Two fictional companies. **No real private enterprise data.** No installed AWS agent.

## Open files in this order

1. **`explorer.html`** — offline searchable overview of feeds, feature catalogue, conflicts, scenarios, and tool specs.
2. **`README.md`** — setup, security boundaries, data layout and main investigation.
3. **`docs/CURSOR_BUILD_PROMPT.md`** — instructions to hand your AI coding agent.
4. **`docs/REFERENCE_FLOWS.md`** — the exact difficult workflows to demonstrate.
5. **`docs/FEATURE_MATRIX.md`** — 114 capabilities grouped into 12 modules.
6. **`docs/SOURCE_CATALOG.md`** — complete list of the 47 feeds.

## Run API

```bash
python -m pip install -r mock_api/requirements.txt pytest httpx
python -m pytest -q tests/
uvicorn mock_api.app:app --port 8000
```

Browse `http://127.0.0.1:8000/docs`. Try `Authorization: Bearer northstar-asha` and `Authorization: Bearer northstar-rahul`. These **public demo tokens are not production authentication**.

## Main story

Asha (Northstar) cannot connect to VPN and her laptop is slow. Device telemetry, VPN gateway, MDM and an older support comment disagree. A real agent should investigate and cite the correct sources, propose permitted actions, obtain separately authorised approval, and refuse certificate renewal while compliance prerequisites fail. Cross-company requests must be denied. A ticketing API timeout-after-commit must not cause duplicate tickets on retry.

## Actual implementation status in this pack

- **Built:** data generation, 47 source feeds, 27 KB files, 114 capability specifications, 160 evaluation input cases with hidden expected answers, source conflicts, SQLite projection, runnable mock API, selected role checks, approvals, idempotency, tests, offline explorer.
- **Not built:** Next.js UI, actual AI reasoning/Strands, AWS Bedrock/AgentCore deployment, real IdP/ITSM connectors, all 114 application features, LLM evaluation benchmarks. These are what your coding sprint builds next.

Run `python scripts/validate_pack.py` to check integrity, and rerun `python scripts/generate_data.py` to reset seed and API runtime state.
