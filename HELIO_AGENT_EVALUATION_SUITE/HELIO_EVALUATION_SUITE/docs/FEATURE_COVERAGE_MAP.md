# Capability-to-Evaluation Coverage Map

Original enterprise fixture advertises 114 capabilities, not 114 features already built. A test case is **not** evidence of implementation or successful evaluation.

| Coverage label | Count |
|---|---:|
| explicit_test_case | 65 |
| legacy_exploratory_only | 2 |
| not_explicitly_tested | 31 |
| ui_acceptance_defined_not_automated | 16 |

## Per-feature mapping

| Feature | Capability | Test cases | Status |
|---|---|---|---|
| FEAT-001 | Employee account lookup | S-005, S-042 | explicit_test_case |
| FEAT-002 | Account lockout diagnosis | S-005, M-003 | explicit_test_case |
| FEAT-003 | Self-service account unlock request | S-005, S-013 | explicit_test_case |
| FEAT-004 | MFA prompt investigation | S-007, M-004 | explicit_test_case |
| FEAT-005 | MFA factor recovery | S-006, M-004 | explicit_test_case |
| FEAT-006 | Federated sign-in error investigation | S-005 | explicit_test_case |
| FEAT-007 | Privileged identity access request | S-011, M-019 | explicit_test_case |
| FEAT-008 | Inactive account detection | S-016 | explicit_test_case |
| FEAT-009 | Device-bound conditional access diagnosis | S-004, S-027 | explicit_test_case |
| FEAT-010 | Passwordless credential support | — | not_explicitly_tested |
| FEAT-011 | Device assignment lookup | S-018, M-022 | explicit_test_case |
| FEAT-012 | Endpoint CPU and memory diagnosis | S-002, S-036 | explicit_test_case |
| FEAT-013 | Low disk remediation planning | S-002 | explicit_test_case |
| FEAT-014 | OS update troubleshooting | — | not_explicitly_tested |
| FEAT-015 | Device encryption failure escalation | S-027 | explicit_test_case |
| FEAT-016 | Endpoint protection alert triage | — | not_explicitly_tested |
| FEAT-017 | Managed device certificate renewal | S-004, M-002 | explicit_test_case |
| FEAT-018 | Device replacement recommendation | — | not_explicitly_tested |
| FEAT-019 | Remote wipe request | — | not_explicitly_tested |
| FEAT-020 | App installation suitability | S-021 | explicit_test_case |
| FEAT-021 | VPN session diagnosis | S-001, M-001 | explicit_test_case |
| FEAT-022 | Expired certificate handling | S-001, S-004 | explicit_test_case |
| FEAT-023 | VPN MFA challenge timeout | — | not_explicitly_tested |
| FEAT-024 | Wi-Fi RADIUS EAP-TLS failure | S-026 | explicit_test_case |
| FEAT-025 | DNS resolver performance | — | not_explicitly_tested |
| FEAT-026 | IP lease conflict detection | — | not_explicitly_tested |
| FEAT-027 | Regional gateway outage correlation | S-019, M-006 | explicit_test_case |
| FEAT-028 | VPN client version mismatch | — | not_explicitly_tested |
| FEAT-029 | Proxy and firewall restriction investigation | — | not_explicitly_tested |
| FEAT-030 | Network change impact analysis | — | not_explicitly_tested |
| FEAT-031 | Ticket creation with idempotency | S-031, S-032, S-033 | explicit_test_case |
| FEAT-032 | My tickets and updates | S-043 | explicit_test_case |
| FEAT-033 | IT ticket assignment | — | not_explicitly_tested |
| FEAT-034 | Priority and impact classification | S-023 | explicit_test_case |
| FEAT-035 | SLA breach identification | S-024 | explicit_test_case |
| FEAT-036 | Problem management clustering | — | not_explicitly_tested |
| FEAT-037 | Root cause evidence graph | S-001, S-036 | explicit_test_case |
| FEAT-038 | Change approval workflow | — | not_explicitly_tested |
| FEAT-039 | Major incident bridge escalation | S-023 | explicit_test_case |
| FEAT-040 | Post-incident review preparation | — | not_explicitly_tested |
| FEAT-041 | Standard SaaS access requests | S-021 | explicit_test_case |
| FEAT-042 | License inventory lookup | S-021, S-022 | explicit_test_case |
| FEAT-043 | Entitlement discrepancy review | S-021 | explicit_test_case |
| FEAT-044 | Cloud-console role request | S-011 | explicit_test_case |
| FEAT-045 | Developer tool access approval | — | not_explicitly_tested |
| FEAT-046 | Application role troubleshooting | — | not_explicitly_tested |
| FEAT-047 | Temporary access expiry | — | not_explicitly_tested |
| FEAT-048 | Software renewal cost visibility | — | not_explicitly_tested |
| FEAT-049 | New employee onboarding plan | LEG-CASE-013 | legacy_exploratory_only |
| FEAT-050 | Contractor start and expiry | — | not_explicitly_tested |
| FEAT-051 | Offboarding stale account alert | S-016, M-015 | explicit_test_case |
| FEAT-052 | Device handover workflow | LEG-CASE-040 | legacy_exploratory_only |
| FEAT-053 | Shared service ownership transfer | — | not_explicitly_tested |
| FEAT-054 | Manager change update | — | not_explicitly_tested |
| FEAT-055 | Employment leave access policy | — | not_explicitly_tested |
| FEAT-056 | Suspicious sign-in correlation | S-037, S-007 | explicit_test_case |
| FEAT-057 | MFA fatigue detection | S-007 | explicit_test_case |
| FEAT-058 | High-impact action control | S-012, S-027 | explicit_test_case |
| FEAT-059 | Cross-tenant API denial | S-008, S-010, S-034 | explicit_test_case |
| FEAT-060 | Cross-tenant knowledge ACL | S-008 | explicit_test_case |
| FEAT-061 | Sensitive document classification | UI-013 | ui_acceptance_defined_not_automated |
| FEAT-062 | Prompt injection containment | S-020, S-039, ADV-001 | explicit_test_case |
| FEAT-063 | Audit export and investigation | UI-014 | ui_acceptance_defined_not_automated |
| FEAT-064 | Separation of duties | S-012, S-049 | explicit_test_case |
| FEAT-065 | Action payload hash integrity | S-030, UI-019 | explicit_test_case |
| FEAT-066 | Relevant document retrieval | S-020, S-003 | explicit_test_case |
| FEAT-067 | Source citation in answers | UI-005 | ui_acceptance_defined_not_automated |
| FEAT-068 | Latest approved policy precedence | S-003, M-013 | explicit_test_case |
| FEAT-069 | Vendor document provenance | S-020 | explicit_test_case |
| FEAT-070 | Cross-system contradictory evidence | S-018, S-036 | explicit_test_case |
| FEAT-071 | Historical resolution retrieval | S-041 | explicit_test_case |
| FEAT-072 | Restricted admin runbooks | UI-014 | ui_acceptance_defined_not_automated |
| FEAT-073 | Document version rollback | — | not_explicitly_tested |
| FEAT-074 | Low-confidence answer escalation | S-028, M-018 | explicit_test_case |
| FEAT-075 | Agent tool allowlist | S-027, S-029 | explicit_test_case |
| FEAT-076 | Action plan preview | UI-015 | ui_acceptance_defined_not_automated |
| FEAT-077 | Human approval request | S-005, S-013, UI-015 | explicit_test_case |
| FEAT-078 | Approval expiry and revocation | S-030, UI-018 | explicit_test_case |
| FEAT-079 | Approved-action execution | S-013, UI-017 | explicit_test_case |
| FEAT-080 | Idempotent write replay | S-031, M-010 | explicit_test_case |
| FEAT-081 | Timeout-after-commit reconciliation | S-031 | explicit_test_case |
| FEAT-082 | Circuit-breaker handling | S-033 | explicit_test_case |
| FEAT-083 | Multi-step partial failure | M-017 | explicit_test_case |
| FEAT-084 | Duplicate event delivery | S-031 | explicit_test_case |
| FEAT-085 | Cancellation safety | S-040, M-017 | explicit_test_case |
| FEAT-086 | Model version release gate | — | not_explicitly_tested |
| FEAT-087 | Incident volumes and SLA analytics | S-024, UI-020 | explicit_test_case |
| FEAT-088 | Agent case resolution metrics | S-044, M-032 | explicit_test_case |
| FEAT-089 | Integration health overview | UI-012 | ui_acceptance_defined_not_automated |
| FEAT-090 | Model token and cost attribution | S-045 | explicit_test_case |
| FEAT-091 | Request budget enforcement | S-029 | explicit_test_case |
| FEAT-092 | Distributed execution tracing | UI-035 | ui_acceptance_defined_not_automated |
| FEAT-093 | API 429 backoff | S-032 | explicit_test_case |
| FEAT-094 | Unexpected API 504 handling | S-031 | explicit_test_case |
| FEAT-095 | Knowledge indexing freshness | UI-014 | ui_acceptance_defined_not_automated |
| FEAT-096 | Managed service monitoring | UI-029 | ui_acceptance_defined_not_automated |
| FEAT-097 | Web chat support | UI-004 | ui_acceptance_defined_not_automated |
| FEAT-098 | Teams and Slack requests | — | not_explicitly_tested |
| FEAT-099 | Email-to-ticket intake | — | not_explicitly_tested |
| FEAT-100 | Incident notifications | UI-026 | ui_acceptance_defined_not_automated |
| FEAT-101 | Customer updates and handoff | M-018 | explicit_test_case |
| FEAT-102 | Survey capture | — | not_explicitly_tested |
| FEAT-103 | Multi-turn conversational continuity | M-001, M-009 | explicit_test_case |
| FEAT-104 | Agent-to-human handoff | M-018 | explicit_test_case |
| FEAT-105 | Mock IdP integration configuration | UI-011 | ui_acceptance_defined_not_automated |
| FEAT-106 | Mock ITSM connector configuration | UI-012 | ui_acceptance_defined_not_automated |
| FEAT-107 | Source-to-field mapping | — | not_explicitly_tested |
| FEAT-108 | Role assignment | UI-011 | ui_acceptance_defined_not_automated |
| FEAT-109 | Per-tenant agent tool policy | S-012, UI-011 | explicit_test_case |
| FEAT-110 | Knowledge publish and classification | UI-013 | ui_acceptance_defined_not_automated |
| FEAT-111 | Audit of policy edits | UI-011 | ui_acceptance_defined_not_automated |
| FEAT-112 | Customer account deployment plan | — | not_explicitly_tested |
| FEAT-113 | Tenant specific branding | — | not_explicitly_tested |
| FEAT-114 | Managed-service access controls | S-050 | explicit_test_case |

Unmapped features should be marked as gaps in the evaluation UI and implemented/tested if part of the application scope. Do not silently count them as complete.
