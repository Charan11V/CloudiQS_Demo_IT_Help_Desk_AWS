# Feature and Use-Case Coverage

**114 enterprise capability specifications across 12 modules.**

This is a **scope and data coverage specification**, not a claim that every capability is coded in the mock API. `fixture_supported` means the data supports the capability. `requires_application_implementation` means the application or agent logic must still be built.

## Identity and authentication

- **FEAT-001 Employee account lookup** — read; users: employee / IT support; guardrail: Same tenant and self or authorised support
- **FEAT-002 Account lockout diagnosis** — read; users: employee / IT support; guardrail: Correlate sign-ins, lockout error, policy
- **FEAT-003 Self-service account unlock request** — approval; users: employee; guardrail: Human proofing and approved identity workflow
- **FEAT-004 MFA prompt investigation** — read_escalate; users: employee / Security; guardrail: Escalate suspicious prompt
- **FEAT-005 MFA factor recovery** — restricted; users: Security; guardrail: No autonomous reset
- **FEAT-006 Federated sign-in error investigation** — read; users: IT support; guardrail: Use provider error codes without exposing secrets
- **FEAT-007 Privileged identity access request** — restricted; users: Security / Cloud admin; guardrail: No admin role grants by helpdesk
- **FEAT-008 Inactive account detection** — read_escalate; users: Identity team; guardrail: Match authoritative HR status vs directory
- **FEAT-009 Device-bound conditional access diagnosis** — read; users: IT support; guardrail: Check device compliance
- **FEAT-010 Passwordless credential support** — restricted; users: Identity team; guardrail: Never collect FIDO2 private keys

## Endpoint and device management

- **FEAT-011 Device assignment lookup** — read; users: employee / IT; guardrail: Ownership sources may conflict
- **FEAT-012 Endpoint CPU and memory diagnosis** — read; users: employee / IT; guardrail: Multiple observations
- **FEAT-013 Low disk remediation planning** — propose; users: employee; guardrail: Safe cleanup guidance only
- **FEAT-014 OS update troubleshooting** — read; users: employee / IT; guardrail: Patch and reboot status
- **FEAT-015 Device encryption failure escalation** — escalate; users: Security; guardrail: No security bypass
- **FEAT-016 Endpoint protection alert triage** — read_escalate; users: Security; guardrail: Restricted diagnostics
- **FEAT-017 Managed device certificate renewal** — approval; users: IT support; guardrail: Device compliance prerequisite
- **FEAT-018 Device replacement recommendation** — propose; users: IT; guardrail: Procurement and warranty checks
- **FEAT-019 Remote wipe request** — restricted; users: Security; guardrail: Disabled in helpdesk
- **FEAT-020 App installation suitability** — approval; users: IT / Manager; guardrail: Catalogue and approval

## VPN and network

- **FEAT-021 VPN session diagnosis** — read; users: employee / IT; guardrail: Correlate client, gateway and identity
- **FEAT-022 Expired certificate handling** — approval; users: IT; guardrail: No unapproved renewal
- **FEAT-023 VPN MFA challenge timeout** — read; users: employee; guardrail: Disambiguate from invalid credentials
- **FEAT-024 Wi-Fi RADIUS EAP-TLS failure** — read; users: IT; guardrail: Check cert and AP logs
- **FEAT-025 DNS resolver performance** — read; users: IT; guardrail: Avoid guessing a network issue
- **FEAT-026 IP lease conflict detection** — read; users: IT; guardrail: Check DHCP events
- **FEAT-027 Regional gateway outage correlation** — read_escalate; users: IT; guardrail: Check service health
- **FEAT-028 VPN client version mismatch** — read; users: IT; guardrail: Check approved versions
- **FEAT-029 Proxy and firewall restriction investigation** — read_escalate; users: Network team; guardrail: No unauthorised firewall edits
- **FEAT-030 Network change impact analysis** — read; users: IT; guardrail: Consult change calendar

## Incident, problem and change management

- **FEAT-031 Ticket creation with idempotency** — mutate; users: employee; guardrail: No duplicate tickets
- **FEAT-032 My tickets and updates** — read; users: employee; guardrail: Self visibility only
- **FEAT-033 IT ticket assignment** — mutate; users: IT; guardrail: Scoped to tenant and team
- **FEAT-034 Priority and impact classification** — propose; users: IT; guardrail: P1 human confirmation
- **FEAT-035 SLA breach identification** — read; users: IT / Manager; guardrail: Respect support calendars
- **FEAT-036 Problem management clustering** — read; users: IT; guardrail: Group recurring root cause
- **FEAT-037 Root cause evidence graph** — read; users: IT; guardrail: Trace each source
- **FEAT-038 Change approval workflow** — approval; users: Manager; guardrail: Plan / backout / test
- **FEAT-039 Major incident bridge escalation** — notify; users: IT; guardrail: Notify duty owner
- **FEAT-040 Post-incident review preparation** — propose; users: Manager; guardrail: Evidence-based timeline

## Access requests and software licensing

- **FEAT-041 Standard SaaS access requests** — approval; users: employee; guardrail: Business owner permission
- **FEAT-042 License inventory lookup** — read; users: IT; guardrail: Seat availability not permission
- **FEAT-043 Entitlement discrepancy review** — read_escalate; users: IT / Security; guardrail: Cross-check HR and directory
- **FEAT-044 Cloud-console role request** — restricted; users: Security; guardrail: No direct privileged grants
- **FEAT-045 Developer tool access approval** — approval; users: Manager; guardrail: Licence and policy
- **FEAT-046 Application role troubleshooting** — read; users: employee / IT; guardrail: Use exact scope
- **FEAT-047 Temporary access expiry** — proposal; users: Security; guardrail: Time-bound grant
- **FEAT-048 Software renewal cost visibility** — read; users: Manager; guardrail: No purchase from chat

## People lifecycle

- **FEAT-049 New employee onboarding plan** — propose; users: HR / IT; guardrail: Effective date and baseline entitlements
- **FEAT-050 Contractor start and expiry** — read_escalate; users: HR; guardrail: Limited duration
- **FEAT-051 Offboarding stale account alert** — escalate; users: Security; guardrail: HR status precedence
- **FEAT-052 Device handover workflow** — propose; users: IT; guardrail: Inventory ownership updates
- **FEAT-053 Shared service ownership transfer** — propose; users: Manager; guardrail: Ticket and data handoff
- **FEAT-054 Manager change update** — read; users: HR / IT; guardrail: Avoid stale group memberships
- **FEAT-055 Employment leave access policy** — restricted; users: HR; guardrail: Policy governs suspension

## Security and privacy

- **FEAT-056 Suspicious sign-in correlation** — read_escalate; users: Security; guardrail: Evidence not sole geography
- **FEAT-057 MFA fatigue detection** — escalate; users: Security; guardrail: Immediate risk path
- **FEAT-058 High-impact action control** — deny_or_approve; users: Approver; guardrail: Human-verified policy
- **FEAT-059 Cross-tenant API denial** — deny; users: all; guardrail: Server-enforced tenant scope
- **FEAT-060 Cross-tenant knowledge ACL** — deny; users: all; guardrail: Filter before RAG context
- **FEAT-061 Sensitive document classification** — read; users: Admin; guardrail: Access control by classification
- **FEAT-062 Prompt injection containment** — deny; users: all; guardrail: Tool policy independent of text
- **FEAT-063 Audit export and investigation** — read; users: Admin / Security; guardrail: Access logged
- **FEAT-064 Separation of duties** — deny; users: all; guardrail: Self approval forbidden
- **FEAT-065 Action payload hash integrity** — deny; users: all; guardrail: Changed request needs fresh approval

## Knowledge and retrieval

- **FEAT-066 Relevant document retrieval** — read; users: employee; guardrail: Permission filtered
- **FEAT-067 Source citation in answers** — read; users: all; guardrail: Cite record and KB ID
- **FEAT-068 Latest approved policy precedence** — read; users: all; guardrail: Superseded documents excluded
- **FEAT-069 Vendor document provenance** — read; users: IT; guardrail: Untrusted evidence
- **FEAT-070 Cross-system contradictory evidence** — reconcile; users: IT; guardrail: Report disagreement
- **FEAT-071 Historical resolution retrieval** — read; users: IT; guardrail: Not automatically authoritative
- **FEAT-072 Restricted admin runbooks** — read; users: Admin; guardrail: Not employee visible
- **FEAT-073 Document version rollback** — admin; users: Admin; guardrail: Requires change review
- **FEAT-074 Low-confidence answer escalation** — escalate; users: all; guardrail: Do not fabricate

## Automation, workflow and approvals

- **FEAT-075 Agent tool allowlist** — admin; users: Admin; guardrail: Enforce outside LLM
- **FEAT-076 Action plan preview** — read; users: employee / IT; guardrail: Safe explanations
- **FEAT-077 Human approval request** — approval; users: employee / IT; guardrail: Immutable payload
- **FEAT-078 Approval expiry and revocation** — deny; users: Approver; guardrail: Time bounded
- **FEAT-079 Approved-action execution** — mutate; users: IT / Worker; guardrail: Revalidate at execution
- **FEAT-080 Idempotent write replay** — mutate; users: agent tool; guardrail: Exactly one effect in mock
- **FEAT-081 Timeout-after-commit reconciliation** — reconcile; users: agent tool; guardrail: Unknown outcome safety
- **FEAT-082 Circuit-breaker handling** — recover; users: agent runtime; guardrail: Bounded retries
- **FEAT-083 Multi-step partial failure** — recover; users: agent runtime; guardrail: Durable state / compensation
- **FEAT-084 Duplicate event delivery** — recover; users: agent runtime; guardrail: Deduplicate
- **FEAT-085 Cancellation safety** — recover; users: agent runtime; guardrail: No blind rollback
- **FEAT-086 Model version release gate** — evaluate; users: Engineering; guardrail: Hard invariants

## Operations analytics and platform

- **FEAT-087 Incident volumes and SLA analytics** — read; users: IT Manager; guardrail: Computed from records
- **FEAT-088 Agent case resolution metrics** — read; users: IT Manager; guardrail: Verified tickets only
- **FEAT-089 Integration health overview** — read; users: Admin; guardrail: Healthcheck and freshness
- **FEAT-090 Model token and cost attribution** — read; users: Admin; guardrail: Estimates vs billing
- **FEAT-091 Request budget enforcement** — deny; users: agent runtime; guardrail: Max calls and tokens
- **FEAT-092 Distributed execution tracing** — read; users: IT Engineer; guardrail: Trace IDs
- **FEAT-093 API 429 backoff** — recover; users: agent runtime; guardrail: Retry-After
- **FEAT-094 Unexpected API 504 handling** — recover; users: agent runtime; guardrail: Reconcile write status
- **FEAT-095 Knowledge indexing freshness** — read; users: Admin; guardrail: Last sync
- **FEAT-096 Managed service monitoring** — read; users: CloudiQS operator; guardrail: Aggregate health only

## Customer communication and channels

- **FEAT-097 Web chat support** — interact; users: employee; guardrail: Authenticated session
- **FEAT-098 Teams and Slack requests** — interact; users: employee; guardrail: Verify identity mapping
- **FEAT-099 Email-to-ticket intake** — create; users: employee; guardrail: Avoid spoofed sender
- **FEAT-100 Incident notifications** — notify; users: IT; guardrail: No secret content
- **FEAT-101 Customer updates and handoff** — notify; users: employee; guardrail: Ticket scope
- **FEAT-102 Survey capture** — read; users: Manager; guardrail: Consent/privacy
- **FEAT-103 Multi-turn conversational continuity** — interact; users: employee; guardrail: Session isolation
- **FEAT-104 Agent-to-human handoff** — escalate; users: IT; guardrail: Preserve approved transcript

## Admin and customer deployment

- **FEAT-105 Mock IdP integration configuration** — admin; users: Admin; guardrail: Secrets never in chat
- **FEAT-106 Mock ITSM connector configuration** — admin; users: Admin; guardrail: Least privilege scope
- **FEAT-107 Source-to-field mapping** — admin; users: Admin; guardrail: Provenance mapping
- **FEAT-108 Role assignment** — admin; users: Admin; guardrail: No role self-elevation
- **FEAT-109 Per-tenant agent tool policy** — admin; users: Admin; guardrail: Independent rules
- **FEAT-110 Knowledge publish and classification** — admin; users: Admin; guardrail: Review and version
- **FEAT-111 Audit of policy edits** — read; users: Admin; guardrail: Immutable event
- **FEAT-112 Customer account deployment plan** — propose; users: Cloud engineer; guardrail: Not simulated as working
- **FEAT-113 Tenant specific branding** — admin; users: Admin; guardrail: Isolation unaffected
- **FEAT-114 Managed-service access controls** — admin; users: Admin; guardrail: Time-scoped customer authorisation

