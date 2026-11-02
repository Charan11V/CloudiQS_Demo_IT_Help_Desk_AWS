# Agentic Bakery Pro — Guided IT Helpdesk Design Package

This is an implementation specification and synthetic data package for an AWS-native agentic IT helpdesk **demo**. It is not a completed web application.

## Contents

- `CURSOR_MASTER_SPEC.md` — full, copy-ready engineering brief: guided journeys, 57 issue leaves, exceptional branches, real state mutations, authorisation, verification, sample dialogues, tests, and stepwise build order.
- `guided_flow_catalog.json` — machine-readable navigation tree and exact tool/approval/verification metadata for all 57 issue types. Use this to power menus and backend routing.
- `demo_seed.json` — deterministic synthetic data for two fictional enterprise tenants, with linked employees, devices, accounts, applications, tickets and diagnostic records.
- `evaluation_cases.json` — 20 expected-case contracts. **Only the evaluator** should read their expected assertions; do not index them into the agent's RAG knowledge.
- `validate_package.py` — validates the internal references, counts, and core fixture expectations.
- `build_assets.py` — optional deterministic generator for JSON assets; seeds are reproducible.

## Do this first

1. Put the files in the root of the Cursor project under `specs/agentic_bakery_helpdesk/`.
2. In Cursor Agent, paste the prompt below.
3. Run `python specs/agentic_bakery_helpdesk/validate_package.py` before generating migrations.
4. Start with ID-01 and DEV-01, then NET-01 approval, and only then add more issue paths.

## Cursor Agent starting prompt

> Read `specs/agentic_bakery_helpdesk/CURSOR_MASTER_SPEC.md`, `guided_flow_catalog.json`, `demo_seed.json`, and `evaluation_cases.json` fully. Build the actual running AWS-ready Guided IT Helpdesk app using the specified Next.js/FastAPI/Postgres/Strands architecture, preserving the existing repo. The navigation menu must be generated dynamically from the catalog. Every supported fix must check a real synthetic record, use permission checks and explicit consent, persist a versioned transaction, emit an audit event, verify the resulting state, then show a truthful outcome labeled DEMO MODE. Implement unknown-issue ticket creation, approvals, no duplicate actions, and cross-tenant denial. Build the P0 vertical slices first, including ID-01, DEV-01 and NET-01; wire frontend and backend end to end. Add tests using the evaluator cases. Do not fake success, invent tool IDs, or implement placeholder-only buttons. Any P1 issue without a working adapter must open a truthful ticket. Keep building and testing the actual app until the key demonstration journeys pass; report implemented vs deferred paths accurately.

## Note on live integrations

No real Entra, Jira, ServiceNow, device-management, printer or mail systems are connected. All mutations affect synthetic test state. AWS Bedrock/AgentCore execution can be layered over the same backend action and policy boundaries. Never claim that the demo changed real enterprise systems.
