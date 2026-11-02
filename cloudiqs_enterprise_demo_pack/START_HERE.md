# Start here: CloudiQS-style Enterprise IT Synthetic Demo Data

**What is this?** A full synthetic enterprise IT environment for the CloudiQS helpdesk demo, with realistic fragmented data and production-style controls. Two fictional companies. **No real private enterprise data.**

## Open files in this order

1. **`explorer.html`** — offline searchable overview of feeds, feature catalogue, conflicts, scenarios, and tool specs.
2. **`README.md`** — setup, security boundaries, data layout and main investigation.
3. **`docs/REFERENCE_FLOWS.md`** — the exact difficult workflows to demonstrate.
4. **`docs/FEATURE_MATRIX.md`** — 114 capabilities grouped into 12 modules.
5. **`docs/SOURCE_CATALOG.md`** — complete list of the 47 feeds.

## Run API

```bash
python -m pip install -r mock_api/requirements.txt pytest httpx
python -m pytest -q tests/
uvicorn mock_api.app:app --port 8000
```

Browse `http://127.0.0.1:8000/docs`. Try `Authorization: Bearer northstar-asha` and `Authorization: Bearer northstar-rahul`. These **public demo tokens are not production authentication**.

## Main story

Asha (Northstar) cannot connect to VPN and her laptop is slow. Device telemetry, VPN gateway, MDM and an older support comment disagree. The helpdesk application should investigate and cite the correct sources, propose permitted actions, obtain separately authorised approval, and refuse certificate renewal while compliance prerequisites fail. Cross-company requests must be denied. A ticketing API timeout-after-commit must not cause duplicate tickets on retry.

## Pack contents

This pack provides data generation, source feeds, knowledge documents, capability specifications, evaluation fixtures, SQLite projection, a runnable mock API, role checks, approvals, idempotency, tests, and an offline explorer. Application UI and orchestration live in the parent repository.

Run `python scripts/validate_pack.py` to check integrity, and rerun `python scripts/generate_data.py` to reset seed and API runtime state.
