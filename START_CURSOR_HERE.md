# HELIO / Agentic Bakery-style IT Ops — Build in Cursor

## Your starting point
This ZIP contains the **original validated fictional enterprise dataset and mock API** plus a new detailed, implementation-directing master prompt. You do **not** need to generate sample data again.

1. Extract the ZIP and **open the extracted `cloudiqs_helio_cursor_workspace` folder as the workspace root in Cursor**.
2. In Cursor Agent mode, paste the exact instruction below (or reference `@BUILD_WITH_CURSOR.md` in chat):

> Read **BUILD_WITH_CURSOR.md** in full and execute it as the project's authoritative specification. The existing `cloudiqs_enterprise_demo_pack/` is the complete synthetic enterprise dataset and runnable mock API; reuse it, do not regenerate it. Build and test the **entire end-to-end Docker-local HELIO application** against that dataset. Implement real Strands + Amazon Bedrock mode when AWS credentials are available and a clearly labelled offline scenario-simulator mode otherwise. Do not create decorative or unconnected features. Implement in working vertical slices, run Docker and automated tests, inspect desktop/mobile screenshots, fix errors and continue until all specified hard acceptance gates pass. Do not stop at scaffolding or a plan. Record working features, tests, screenshots and genuine remaining limitations.

3. Check `docker compose up --build -d`; open `http://localhost:3000`; run the test commands described in BUILD_WITH_CURSOR.md.

## Essential expectations
- Local Docker runs web, Python/Strands agent orchestration and fictional enterprise mock API.
- Real external Bedrock inference only when explicitly configured, billed by AWS; **AgentCore Runtime is not running locally**.
- Synthetic dataset spans **47 source feeds, 2,404 records, 27 KB documents, 20 source conflicts and 160 evaluation inputs** (not 160 already evaluated model runs).
- Documentation and test suite clearly distinguish dataset seeding, mock integration behavior, actual Strands/Bedrock agent behavior and later AWS AgentCore deployment.
- The comprehensive master specification replaces the shorter existing Cursor prompt inside the pack.

This is an **independent, original hiring demo** inspired by Agentic Bakery's advertised AWS-native patterns; not an authorised CloudiQS implementation.
