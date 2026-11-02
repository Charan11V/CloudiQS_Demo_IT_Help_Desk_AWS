# Guided IT Helpdesk — Design Package

Specification and synthetic data for the CloudiQS guided IT helpdesk demo.

## Contents

- `MASTER_SPEC.md` — product and engineering specification: guided journeys, issue catalogue, state mutations, authorisation, verification, sample dialogues, and test expectations
- `guided_flow_catalog.json` — machine-readable navigation tree and tool/approval metadata for supported issue types
- `demo_seed.json` — deterministic synthetic tenant data (people, devices, accounts, tickets)
- `evaluation_cases.json` — expected-case contracts for automated evaluation
- `validate_package.py` — validates package references and fixture integrity
- `build_assets.py` — optional deterministic generator for JSON assets

## Setup

1. Keep this package under `specs/agentic_bakery_helpdesk/` in the repository root.
2. Run `python specs/agentic_bakery_helpdesk/validate_package.py` before schema or seed changes.
3. Prefer vertical slices in this order: ID-01, DEV-01, then NET-01 (approval path), then remaining catalogue paths.

## Integrations note

No live Entra, Jira, ServiceNow, MDM, or mail systems are connected. Mutations apply to synthetic demo state only. Do not present demo remediations as changes to real enterprise systems.
