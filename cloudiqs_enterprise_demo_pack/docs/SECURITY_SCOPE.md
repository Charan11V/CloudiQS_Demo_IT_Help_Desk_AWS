# Security and Claim Boundaries

The dataset and API are for local demonstration, not production access. All named identities and domains (`*.example`) are fictional. Synthetic IPs use documentation ranges where applicable. Never replace these with real credentials or data without a reviewed integration plan.

## Implemented in mock API

- A presented public **demo token** maps to a predefined identity; tenant and role are read from SQLite and NOT from `X-Tenant-ID`.
- Own-account/ticket/device reads and some scoped IT staff reads.
- Tenant filters are applied to each implemented route.
- Current KB classification filters, with admin-only archived view.
- Mock account-unlock and VPN certificate-renewal approval workflow, reviewer role checks, separation of duties, payload integrity and expiry.
- Server-side ticket idempotency, including simulate-timeout-after-commit and same-key replay.
- Persisted audit event records for supported mutations.
- No real enterprise security changes, no external email, no AWS tool execution.

## Intentionally absent from mock

- Real OAuth2/OIDC token verification, JWKS validation, short-lived scopes, MFA and proper enterprise identity assurance.
- True AgentCore Gateway and Policy, IAM role scoping, AWS per-account isolation, secret rotation, managed deployment infrastructure.
- Authentic JWT propagation across each agent/tool invocation, phishing-resistant approvals, encrypted audit storage, resource policies, tamper-evident event chains.
- Full ITIL workflows, billing-grade cost monitoring, multi-node idempotency across external systems, real vendor-specific connector semantics.
- A working multi-agent application, RAG vector database, model evaluations, certified compliance or operational SLAs.

## Threats to test while adding the real agent

1. Cross-tenant IDOR, filters omitted in vector retrieval, guessed ticket IDs and tenant ID spoofing.
2. Prompt injection in KB text, ticket descriptions, Slack message history, and API error strings.
3. Approval payload swap, expired approval, wrong-role approval and self-approval.
4. Model-triggered duplicate writes after timeouts and repeated user prompts.
5. Unauthorized privileged account operations and tool/credential bypass of policy gateway.
6. Stale document versions and quoted historical tickets treated as binding policy.
7. Excess token/tool loops and API 429/503 retries.
8. Cross-user conversation-memory contamination and sensitive traces shown to the wrong role.
9. Implicit trust in AI-generated output or the source feed's asserted `tenant_id`.

## AWS deployment guidance for the job demo

Deploy only a small isolated development stack with budgets/cleanup. Prefer real IAM least-privilege role for Bedrock and limited Strands runtime, authenticated server-backed API, and real AgentCore Runtime/Gateway **only when explicitly wired and tested**. A functioning local FastAPI mock does not demonstrate that AWS deployment has been completed. Do not claim GDPR/HIPAA/SOC2/ISO certification from these fixtures.
