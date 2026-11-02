# Security model (local demo)

## Implemented
- Session cookies (HttpOnly, SameSite=Lax); server-side bearer mapping
- Tenant scoping on every agent-api and mock route
- Role ACL for tickets, KB, sources, admin, analytics, security
- Approval SoD + expiry + payload hash; Vikram cannot approve unlock merely as admin
- Beacon unlock requires `security_analyst`
- Cross-tenant reads return 404 without existence leak
- Forbidden agent actions: MFA reset, remote wipe, admin role grant (policy `disallowed_for_agent`)
- Idempotent ticket writes; 504-after-commit recovery with same key
- Evaluator oracle isolated from agent runtime
- No real password/MFA reset APIs

## Explicitly not production
- Demo tokens are public fixtures
- No Cognito/OIDC/JWT federation
- No AgentCore Gateway/Identity
- Logical tenants in one SQLite DB
- Localhost-bound ports only in compose
