# Implementation Specification
## Agentic Bakery Pro — Guided, Stateful, Data-Consistent Autonomous IT Helpdesk

**Read this entire document, `guided_flow_catalog.json`, `demo_seed.json` and `evaluation_cases.json` before changing code. Implement a functioning system, not illustrative-only screens.**

> Scope clarification: No actual existing database files were supplied. `demo_seed.json` is a newly generated, internally linked synthetic baseline grounded in the previously discussed Northstar and Beacon demo scenario. If a project already has migrations or records, adapt the mapping through migrations; do not silently discard those records.

## 0. Non-negotiable product contract

1. **Guided first, flexible second.** The assistant opens with clear clickable categories, then subcategories, then issue options, then short diagnostic questions. Free text is always allowed. Every menu option has a stable ID from `guided_flow_catalog.json`; never allow the LLM to invent menu IDs or executable operations.
2. **Ask before mutating.** Investigate via read-only mock enterprise APIs; present a plain-English finding and proposed repair; require explicit user confirmation for user-impacting operations and role-based approval for privileged operations. Only emergency, non-disruptive evidence collection may be automatic.
3. **Actual persistent state changes.** A completed operation must change a durable record (or create an appropriate record), generate an audit event, and pass a separate verification read. `"resolved"` is not just a model-generated sentence.
4. **Be truthful about the simulation.** This is a demo with mock identity, device, network, ticketing and licensing systems. Display **“DEMO — simulated enterprise systems”** persistently. Say “I updated the simulated device/account record” rather than claiming that a physical laptop or real Microsoft Entra account was fixed. The exact phrase can be natural, but never conceal the simulation.
5. **One truthful disposition for every issue:** `resolved`, `resolved_after_user_confirmation`, `pending_approval`, `awaiting_user`, `waiting_external`, `ticket_open`, `escalated`, `refused`, `cancelled`, `unresolved`. An open ticket is not a resolution. An approval request is not an executed action.
6. **The database, not the LLM, is the system of record.** LLM handles intent and language; backend controls navigation, identity, policy, executable tool dispatch, write transactions, idempotency, and verification. Never let a model freely edit SQL, tenant IDs, resource IDs, ticket status, prices or counters.
7. **No dead ends.** Every prompt includes a relevant next action plus Back, Start Over, Talk to IT, and Something Else. After two failed clarification attempts, offer a ticket and capture the user's description. No unsupported issue is hallucinated as resolved.
8. **Do not confuse identity.** Authenticated tenant/user/role comes from a verified server-side session; ignore tenant or role supplied in chat. Service tools receive these claims from trusted middleware. Cross-tenant attempts are blocked and auditable.
9. **Safety:** Never reset someone else's MFA, bypass MFA, silently delete user files, disable security software, change payroll, or modify real external accounts. Use only allowlisted simulated operations and explicit approvals.
10. **One-day delivery priority:** Make 10–12 P0 issue paths genuinely work end to end, make the other 45+ catalogue paths navigate and end in an accurate ticket/escalation, and execute the P0 adversarial tests. Prefer correct data transactions over fancy animations.

## 1. Users, authority and surfaces

| Persona | Example login | What they see | Authorised capabilities |
|---|---|---|---|
| Employee | Asha Rao (`NS-001`) | Guided chat, My Tickets, My Devices, resolution steps | Read own records; request support; consent to safe own-device actions; never approve privileged actions |
| IT engineer | Rahul Sharma (`NS-002`) | Queue, investigations, approvals, audit trail | Read assigned tenant cases; approve policy-permitted actions; run scoped support tools |
| IT manager | Priya Menon (`NS-003`) | SLA, problem clusters, team workload, outcomes | Read aggregate tenant analytics; review policy proposals; no implicit superuser rights |
| Tenant admin | Vikram Rao (`NS-004`) | Tenant integration settings, users, policies and catalogue | Change tenant configuration, rotate mock credentials, manage roles, subject to separation of duties |
| Employee (other tenant) | Neha Kapoor (`BC-001`) | Same interface, Beacon-specific records/policies | Cannot access Northstar data |
| IT engineer (other tenant) | David Thomas (`BC-002`) | Beacon queue and approvals only | Cannot manage Northstar requests |
| Tenant admin (other tenant) | Meera Nair (`BC-003`) | Beacon settings only | Cannot change Northstar configs |
| CloudiQS operator | Optional test identity | Platform health and deployment logs | No default access to tenant conversations/content; access must be explicitly authorised |

**Permission examples:** `ticket:create_self`, `ticket:read_own`, `device:read_assigned`, `device:mock_cleanup_self`, `approval:request`, `approval:decide_eligible`, `tenant:manage_integrations`, `analytics:read_aggregate`. Enforce resource ownership, tenant match, current role, and action-specific rules on every route, not just when rendering buttons.

## 2. Full user journey: from hello to final outcome

### 2.1 First entry / welcome

**Agent:** “Hi Asha! I'm your IT support assistant. What would you like help with today? Choose an area below, or describe the problem in your own words.”

**Always show these eight clickable category cards:**

1. Account, password & access
2. VPN, Wi-Fi & internet
3. Laptop performance & updates
4. Applications, email & meetings
5. Printing & scanners
6. Security & suspicious activity
7. Hardware & accessories
8. Software, access & hardware requests

**And always show:** “I'm not sure,” “I can't find my issue,” “Describe my problem,” “My tickets,” “Talk to IT.”

For returning users, show: “Continue your earlier issue,” any pending approval, and the most recent open ticket (if it belongs to this user). No cross-user history.

### 2.2 Category -> subcategory -> specific symptom -> contextual evidence

* On category selection, fetch **subcategories from `guided_flow_catalog.json`**; do not jump straight to long chat.
* On subcategory selection, show **symptom options** (each bound to an `issue_code`).
* On symptom selection, ask the catalogue's `clarifying_question`; offer *Yes / No / Not sure / Something else* where appropriate.
* Select the currently authenticated user's device, account and tenant by server-side identity. If several devices are assigned, ask which device (card: name, platform, asset ID). If no device, offer a ticket.
* Before giving a diagnosis, fetch the relevant authoritative state using read-only tools. Distinguish: evidence supports diagnosis / evidence contradicts it / data missing / service unavailable.
* **If contradicted:** explain briefly, suggest the next best symptom or return to choices; never force a predefined fix.
* **If evidence is missing or mock API unavailable:** use a safe fallback ticket with diagnostic notes. Never invent data.
* **If evidence supports diagnosis:** show a finding card: observed state, supporting record, proposed action, impact, approval requirements, and `Fix this in demo` or `Escalate instead`.
* After consent/approval, execute through tool gateway, save action and event, re-read the authoritative record, assert postconditions, and only then display resolution.
* Ask “Did this solve your problem?” with **Yes / No / Partly**. On Yes, close the case/ticket if verification passed. On No, reopen/continue triage and possibly escalate; on Partly, split remaining symptoms into a linked subcase.
* If the issue cannot be solved autonomously, open a ticket, display its real persisted ID, team, current status, and how to follow up. Do not say “fixed.”

### 2.3 Text input at every step

A user may type at any point instead of using buttons. Classify the utterance into `issue_code` with a confidence rating and suggested option IDs. Resolve against **server-side catalogue IDs**, not free-form LLM instructions.

- Exact, unambiguous phrase -> jump to the matching issue's clarification, showing the selected category/path.
- Two plausible issues -> show 2–3 disambiguation buttons (e.g., “VPN login” vs “Company account login”).
- Low-confidence or unrelated phrase -> ask one clarifying question, then offer the fallback form.
- Multiple complaints -> create a parent conversation with separate issue subcases, each with its own state and outcome; handle security-critical reports first. Do not mark the whole conversation resolved while a subcase remains open.
- User says “agent failed / you didn't fix it” -> do not repeat the same action; show state, ask what still fails, offer another branch or ticket.
- User asks to speak to a person -> create an escalation ticket immediately after obtaining a minimal problem description; do not force the decision tree.
- User goes back -> preserve collected facts unless the target issue changes; invalidate action proposals based on stale information.
- User starts over -> retain ticket and audit history, but reset active guided navigation after confirmation.
- User closes chat -> persist conversation and pending states; let them resume.
- User sends an image / screenshot -> show attachment placeholder and ticket metadata if multimodal analysis is not implemented; don't invent image conclusions.

### 2.4 Distinct final screens

| Outcome | Exact UI behaviour | Example accurate agent wording |
|---|---|---|
| Resolved in demo | Verified before-and-after values, action event, follow-up confirmation | “The simulated VPN certificate was renewed, and the connection test passed. Did that solve the issue you were testing?” |
| Fixed in simulator, user not confirmed | `awaiting_user_confirmation`, show completed action and verification | “The demo system reports success. Can you confirm whether your issue is solved?” |
| Pending approval | Action payload summary, reviewer queue, expiry; nothing executed | “I've requested IT approval. Your account has not been changed yet.” |
| Waiting external | Linked outage status, ticket ID, no fabricated recovery | “The VPN service is currently degraded. I've linked your ticket to the known outage.” |
| Escalated | Real persisted security/hardware/support ticket and assigned queue | “I created ticket INC-… for the security team. I haven't changed your security settings.” |
| Refused | Safe explanation and approved alternative | “I can't disable MFA. I can open a secure recovery request.” |
| Not found | Capture own description, optional category, urgency, attachment; submit | “I couldn't identify a supported automatic fix. Ticket INC-… is open.” |
| Cancelled | Persist cancellation; don't execute pending intent | “I cancelled the proposed action. No change was made.” |
| Partial | Linked subcases with accurate separate statuses | “The simulated device cleanup succeeded, but VPN recovery is waiting for IT approval.” |

## 3. The navigable issue taxonomy

**Machine-readable source of truth:** `guided_flow_catalog.json`. The catalogue contains **8 top-level categories and 57 issue leaves**, each with an issue code, clarifying question, required evidence, allowed tool action, approval policy, verification assertion, and implementation tier. Render it dynamically, not as static hard-coded strings. Below is the human-readable exact map.


### Account, password & access (`identity`)

**Password and login:** `ID-01` Account locked; `ID-02` Forgot password; `ID-03` Password expired; `ID-07` Suspicious sign-in / lock; `ID-09` Disabled employee account.

**MFA and sessions:** `ID-04` MFA push/code not arriving; `ID-05` Lost MFA device; `ID-08` Session expired.

**Application access:** `ID-06` Access denied to application.


### VPN, Wi-Fi & internet (`network`)

**VPN:** `NET-01` VPN certificate expired; `NET-02` Outdated VPN client; `NET-03` VPN sign-in fails due to account; `NET-04` VPN service outage.

**Wi-Fi and internet:** `NET-05` DNS resolution failure; `NET-06` Wi-Fi disabled; `NET-07` Weak Wi-Fi signal; `NET-08` Proxy or firewall issue; `NET-09` Internet provider outage.


### Laptop performance & updates (`device`)

**Performance:** `DEV-01` Low disk space; `DEV-02` High CPU use; `DEV-03` High memory use; `DEV-06` Overheating; `DEV-09` Storage performance slow.

**Updates and reboot:** `DEV-04` Restart pending; `DEV-05` OS patches outdated.

**Hardware health:** `DEV-07` Battery failing; `DEV-08` Device fails to boot.


### Applications, email & meetings (`apps`)

**Application errors:** `APP-01` App crashes on startup; `APP-02` Application outdated; `APP-08` Application provider outage.

**Licences and access:** `APP-03` Software licence unavailable; `APP-04` Missing application permission.

**Email:** `APP-05` Email not syncing; `APP-06` Mailbox full; `APP-09` Undelivered outgoing email.

**Meetings and audio:** `APP-07` Microphone or camera blocked.


### Printing & scanners (`printing`)

**Printer connection:** `PRINT-01` Printer offline; `PRINT-04` Printer driver mismatch.

**Printing queue:** `PRINT-02` My print job is stuck.

**Printer supplies:** `PRINT-03` Out of paper or paper jam; `PRINT-05` Toner low or printer hardware broken.


### Security & suspicious activity (`security`)

**Suspicious messages:** `SEC-01` Report phishing email.

**Malware:** `SEC-02` Endpoint malware alert.

**Lost or stolen:** `SEC-03` Lost or stolen company device.

**Suspicious sign-ins:** `SEC-04` Unrecognised login.

**Data exposure:** `SEC-05` Potential data leak.

**Policy bypass:** `SEC-06` Disable MFA or security controls.


### Hardware & accessories (`hardware`)

**Peripherals:** `HW-01` Camera not detected; `HW-02` Keyboard or mouse not working; `HW-04` Docking station disconnects.

**Physical damage:** `HW-03` Broken screen; `HW-05` Lost hardware.


### Software, access & hardware requests (`requests`)

**Software request:** `REQ-01` Install approved software; `REQ-02` Request restricted software.

**Access request:** `REQ-03` Access shared drive.

**Hardware request:** `REQ-04` Request new laptop/peripheral.

**General service:** `REQ-05` Other service request.

### Universal fallback routes (available at every node)

`GEN-UNKNOWN` (free-text unknown), `GEN-AMBIGUOUS` (ask narrowing question), `GEN-MULTI` (split separate issues), `GEN-OUT-OF-SCOPE` (request support ticket), `GEN-REPEAT` (idempotent read/continue), `GEN-RESUME` (load saved state), `GEN-CANCEL` (cancel only not-yet-committed actions), `GEN-REOPEN` (user reports recurrence), `GEN-ATTACHMENT` (store uploaded attachment metadata or mock reference), `GEN-HUMAN` (create human escalation without forcing guided triage).

**Important:** These generic flow codes are workflow branches, not extra entries in the 57-item symptom catalogue. Treat them as first-class supported state transitions.

## 4. Issue-specific system-of-record read/write/verification contract

The table below is binding. Every automatic mutation must occur through a typed backend function or mock provider adapter with tenant/identity checks. `pending_approval`, `escalated`, `ticket_created`, `waiting_external`, and `refused` **never count as resolved**.


### Account, password & access

| Code / symptom | Evidence or precondition | Allowed action | Approval / user gate | Verify / completion | Build |
|---|---|---|---|---|---|
| `ID-01` Account locked | account.status=locked, lock_reason, sign-in events | `unlock_own_account` | conditional | account.status=active and new login simulation succeeds; **resolved** | P0 |
| `ID-02` Forgot password | verified user identity, reset policy, account state | `issue_self_reset_challenge` | self_verification | reset challenge completed and credentials_version incremented; **resolved_after_user_action** | P0 |
| `ID-03` Password expired | account.password_expired=true | `issue_self_reset_challenge` | self_verification | password_expired=false after confirmed reset; **resolved_after_user_action** | P1 |
| `ID-04` MFA push/code not arriving | mfa method, delivery simulator, sign-in status | `retry_mfa_delivery` | none | mfa_delivery_status=delivered and user confirms; **resolved_after_user_action** | P1 |
| `ID-05` Lost MFA device | mfa methods, sign-in risk flags | `request_mfa_recovery` | security_approval | approved recovery completed and sign-in verified; **pending_approval** | P1 |
| `ID-06` Access denied to application | entitlements, role, licence status, application policy | `request_entitlement_grant` | app_owner_approval | entitlement exists and app permission check succeeds; **pending_approval** | P0 |
| `ID-07` Suspicious sign-in / lock | security events, sign-in risk flags | `create_security_escalation` | security_review | security team explicitly closes incident; **escalated** | P1 |
| `ID-08` Session expired | session token expiry, auth logs | `refresh_mock_session` | none | session.status=active and test access succeeds; **resolved** | P1 |
| `ID-09` Disabled employee account | employment status, account.disabled_reason | `create_identity_ticket` | identity_admin_review | reinstatement verified by authorised admin; **escalated** | P1 |


### VPN, Wi-Fi & internet

| Code / symptom | Evidence or precondition | Allowed action | Approval / user gate | Verify / completion | Build |
|---|---|---|---|---|---|
| `NET-01` VPN certificate expired | vpn certificate expiry, device ownership, VPN log | `renew_mock_vpn_certificate` | it_approval | certificate valid and simulated VPN handshake succeeds; **pending_approval** | P0 |
| `NET-02` Outdated VPN client | installed VPN version vs policy minimum | `update_mock_vpn_client` | none | client version compliant and connection check passes; **resolved** | P0 |
| `NET-03` VPN sign-in fails due to account | identity status, VPN failure codes | `route_identity_flow` | per_identity | resolved by linked identity flow; **routed** | P1 |
| `NET-04` VPN service outage | tenant VPN service health and incident alerts | `create_outage_linked_ticket` | none | service recovered by incident service, then user confirms; **waiting_external** | P0 |
| `NET-05` DNS resolution failure | device dns_status, network tests | `reset_mock_dns_config` | none | dns_status=healthy and lookup simulation passes; **resolved** | P1 |
| `NET-06` Wi-Fi disabled | device.wifi_enabled, adapter state | `enable_mock_wifi` | none | wifi_enabled=true and adapter connects; **resolved** | P1 |
| `NET-07` Weak Wi-Fi signal | signal strength, access point distance | `guided_wifi_steps` | user_confirmation | user confirms connection stable; **awaiting_user** | P1 |
| `NET-08` Proxy or firewall issue | proxy state and policy, network diagnostics | `create_network_escalation` | network_team | network specialist verifies fix; **escalated** | P1 |
| `NET-09` Internet provider outage | external provider incident, network checks | `create_external_outage_ticket` | none | provider marks recovered and user confirms; **waiting_external** | P1 |


### Laptop performance & updates

| Code / symptom | Evidence or precondition | Allowed action | Approval / user gate | Verify / completion | Build |
|---|---|---|---|---|---|
| `DEV-01` Low disk space | device disk_total_gb, disk_free_gb, safe temp files inventory | `run_mock_safe_cleanup` | user_confirmation | disk_free_gb rises by recorded bytes, disk_free_pct above policy; **resolved** | P0 |
| `DEV-02` High CPU use | process list, cpu_percent and protected process list | `restart_mock_noncritical_process` | conditional | cpu_percent below threshold and process state healthy; **resolved** | P1 |
| `DEV-03` High memory use | memory_percent and active app process | `restart_mock_app_process` | user_confirmation | memory_percent falls and application health good; **resolved** | P1 |
| `DEV-04` Restart pending | device.restart_pending and active task state | `perform_mock_restart` | user_confirmation | restart_pending=false, reboot_count incremented and health test passes; **resolved** | P0 |
| `DEV-05` OS patches outdated | device patch level, scheduled updates | `schedule_mock_patch` | it_approval | patch version updated and patch compliance verified; **pending_action** | P1 |
| `DEV-06` Overheating | device temperature sensor and hardware diagnostics | `create_hardware_escalation` | none | technician confirms safe operational state; **escalated** | P1 |
| `DEV-07` Battery failing | device battery_health, safety flag | `create_hardware_escalation` | none | technician confirms physical repair; **escalated** | P1 |
| `DEV-08` Device fails to boot | last heartbeat, boot errors | `create_hardware_escalation` | none | technician validates repair; **escalated** | P1 |
| `DEV-09` Storage performance slow | disk SMART health, I/O alerts | `create_hardware_escalation` | none | storage replacement and data integrity checked; **escalated** | P1 |


### Applications, email & meetings

| Code / symptom | Evidence or precondition | Allowed action | Approval / user gate | Verify / completion | Build |
|---|---|---|---|---|---|
| `APP-01` App crashes on startup | app installation, crash logs, service state | `restart_mock_app_and_cache` | user_confirmation | application status=running and simulated health check passes; **resolved** | P0 |
| `APP-02` Application outdated | installed version, approved version catalogue | `install_mock_app_update` | conditional | installed version >= required and app health pass; **resolved** | P1 |
| `APP-03` Software licence unavailable | licence pool, user assignment, contract status | `request_licence_assignment` | app_owner_approval | licence allocated, remaining capacity nonnegative; **pending_approval** | P1 |
| `APP-04` Missing application permission | user entitlement, group and policy | `request_entitlement_grant` | app_owner_approval | approved entitlement grants correct scope; **pending_approval** | P0 |
| `APP-05` Email not syncing | mailbox token state, sync timestamp, provider health | `refresh_mock_mail_sync` | none | sync_status=healthy and timestamp advanced; **resolved** | P1 |
| `APP-06` Mailbox full | mailbox used_gb, quota_gb, archive candidates | `mock_archive_selected_mail` | user_confirmation | used_gb decreases, archived count increases, quota compliance verified; **resolved** | P1 |
| `APP-07` Microphone or camera blocked | device app permissions, device status | `enable_mock_app_permission` | user_confirmation | permission=allowed and device probe passes; **resolved** | P1 |
| `APP-08` Application provider outage | service incident and provider status | `create_outage_linked_ticket` | none | provider recovery and user confirmation; **waiting_external** | P1 |
| `APP-09` Undelivered outgoing email | SMTP failure status, recipient pattern and policy | `create_email_routing_ticket` | mail_admin_review | mail system verifies successful delivery; **escalated** | P1 |


### Printing & scanners

| Code / symptom | Evidence or precondition | Allowed action | Approval / user gate | Verify / completion | Build |
|---|---|---|---|---|---|
| `PRINT-01` Printer offline | printer current status, queue and network | `restart_mock_printer_service` | conditional | printer.status=online and test page queued; **resolved** | P1 |
| `PRINT-02` My print job is stuck | print_job.owner, status, printer queue health | `retry_or_cancel_own_print_job` | user_confirmation | own job state updated; other users jobs untouched; **resolved** | P0 |
| `PRINT-03` Out of paper or paper jam | printer supplies and jam status | `guided_manual_printer_fix` | user_confirmation | printer sensor simulation confirms ready after user action; **resolved_after_user_action** | P1 |
| `PRINT-04` Printer driver mismatch | driver version, device and printer model | `install_mock_printer_driver` | conditional | driver version compatible and test print passes; **resolved** | P1 |
| `PRINT-05` Toner low or printer hardware broken | printer toner and hardware fault | `create_facilities_ticket` | none | facility confirms replacement or repair; **escalated** | P1 |


### Security & suspicious activity

| Code / symptom | Evidence or precondition | Allowed action | Approval / user gate | Verify / completion | Build |
|---|---|---|---|---|---|
| `SEC-01` Report phishing email | reported message metadata, available indicators | `create_security_incident` | security_review | security analyst closes incident; employee report acknowledged; **escalated** | P0 |
| `SEC-02` Endpoint malware alert | EDR findings, device status | `request_mock_isolation` | security_approval | containment verified and security analyst closes; **pending_approval** | P1 |
| `SEC-03` Lost or stolen company device | ownership, device last heartbeat, sessions | `create_urgent_security_incident` | security_approval | security-led response complete; **escalated** | P1 |
| `SEC-04` Unrecognised login | identity risk events, sign-in history | `create_urgent_security_incident` | security_review | security analyst closes incident; **escalated** | P1 |
| `SEC-05` Potential data leak | reporter statement, file metadata | `create_urgent_security_incident` | security_review | security analyst verifies containment; **escalated** | P1 |
| `SEC-06` Disable MFA or security controls | request and caller permissions | `refuse_and_escalate_security_request` | security_review | no automated bypass; specialist closes request; **refused** | P1 |


### Hardware & accessories

| Code / symptom | Evidence or precondition | Allowed action | Approval / user gate | Verify / completion | Build |
|---|---|---|---|---|---|
| `HW-01` Camera not detected | device camera permission and driver state | `enable_mock_camera_permission` | user_confirmation | mock camera probe succeeds; **resolved** | P1 |
| `HW-02` Keyboard or mouse not working | peripheral connection state, driver health | `restart_mock_peripheral_driver` | user_confirmation | peripheral health probe succeeds; **resolved** | P1 |
| `HW-03` Broken screen | device fault inventory | `create_hardware_escalation` | none | repair verified by technician; **escalated** | P1 |
| `HW-04` Docking station disconnects | dock firmware, connection logs | `refresh_mock_dock_driver` | user_confirmation | dock connection simulation stable; **resolved** | P1 |
| `HW-05` Lost hardware | device asset assignment | `route_lost_device_security` | security_review | security-led resolution; **routed** | P1 |


### Software, access & hardware requests

| Code / symptom | Evidence or precondition | Allowed action | Approval / user gate | Verify / completion | Build |
|---|---|---|---|---|---|
| `REQ-01` Install approved software | software allowlist, device ownership, licence availability | `install_mock_approved_software` | conditional | app installed, assigned licence valid and health check passes; **resolved** | P0 |
| `REQ-02` Request restricted software | catalogue status, business justification | `create_software_approval_request` | app_owner_approval | approved install and verification or denied request; **pending_approval** | P1 |
| `REQ-03` Access shared drive | resource ACL, project membership, owner | `request_shared_drive_access` | resource_owner_approval | authorised ACL grant and test read; **pending_approval** | P1 |
| `REQ-04` Request new laptop/peripheral | asset catalogue, eligibility, manager | `create_procurement_ticket` | manager_approval | asset delivered and assigned; **pending_approval** | P1 |
| `REQ-05` Other service request | user description and allowed categories | `create_general_request_ticket` | triage | support team verifies fulfilment; **ticket_created** | P1 |

## 5. Twelve complete start-to-finish dialogues for implementation

Use scripted trace IDs and real backend data. Below, **E** is employee, **A** is assistant, **UI** is a mandatory user interface state. The backend state is authoritative; sample phrasing can vary.

### Flow 1 — Account locked, self-recovery permitted (`ID-01`)

1. A: “What can I help with?” Options -> **Account, password & access**.
2. E: **Account, password & access** -> **Password and login** -> **Account locked**.
3. A: “Do you see an account locked message?” -> E: **Yes**.
4. Backend checks verified `user_id=NS-001` -> `ACC-NS-001` `status=locked`, `lock_reason=failed_attempts`, `risk_flag=false`, recent failed logins (no security incident requiring review).
5. A: “Your demo account is locked after unsuccessful attempts. I can unlock your own simulated account after identity verification.” -> **Verify and unlock / Open ticket / Back**.
6. E: **Verify and unlock** -> separate mock MFA/identity challenge, not just a verbal claim of identity.
7. Backend checks challenge and policy; creates immutable action intent with actor, target, tenant, expected version, expiry, idempotency key.
8. Backend invokes `unlock_own_account`, conditionally sets status `active`, failed-login counter `0`, lock reason `null`, version+1; writes `action_executions`, `audit_events` in same transaction.
9. Backend re-reads account and optionally simulated login probe; if verified, A: “The simulated account is now unlocked.” UI: **Resolved in demo / Still can't log in / View ticket**.
10. If still failing: go to password/MFA diagnostic, not repeated unlock. If risk flagged at step 4: no automatic unlock; create security escalation instead.

### Flow 2 — Forgot/expired password (`ID-02` / `ID-03`)

User selects account -> password -> Forgot password. Read verified account. Do not display or store a raw password. Issue a **single-use mock reset challenge** with expiry and use a separate confirmation action to complete. Pre-completion state: `password_reset_pending`, not resolved. On successful verification, increment `credentials_version`, clear `password_expired`, invalidate old sessions in the simulated identity provider, and verify test sign-in. Reset/challenge retries must not mint unlimited tokens. If identity proof fails, do not modify credentials; open ticket. The UI should avoid emailing real addresses and label any reset link as demo-only.

### Flow 3 — VPN certificate expiry, approval-gated (`NET-01`)

1. E selects VPN, Wi-Fi & internet -> VPN -> VPN certificate expired.
2. A: “Which assigned device?” -> `DEV-NS-001` shown (if single device, can preselect but make selection clear).
3. Backend checks `VPN-NS-001`, expired certificate, owner = Asha, tenant = Northstar; also service health is healthy.
4. A: “The simulated certificate expired on 20 Oct 2026. A renewal needs IT approval. Request it?” -> **Request renewal / Escalate / Back**.
5. E requests. Persist intent + approval for exactly `renew_mock_vpn_certificate`, exact profile, old version, and requested replacement expiry. Ticket/action state `pending_approval`.
6. IT engineer Rahul signs into IT workspace; sees evidence, requestor, impact; **Approve / Reject**. An ordinary employee cannot access this operation.
7. On approval, recheck current account, policy, resource version and approval hash. Execute renewal only if approved unchanged. Set expiry to policy-defined date, update profile version, append audit event.
8. Re-read certificate; run mock handshake if tenant VPN service is healthy; otherwise say certificate renewed but connection still blocked by outage and keep VPN subissue open.
9. If verification succeeds, tell Asha the **simulated** VPN credential was renewed; ask user to confirm. If rejected, notify user and show ticket route; no mutation.

### Flow 4 — Outdated VPN client plus known outage (`NET-02` + `NET-04`)

Neha (`BC-001`) selects VPN -> client update required. Her simulated version is `4.9`, minimum `5.2`, latest approved `5.3`. Agent offers `Update demo client`. On consent, writes `VPN-BC-001.client_version=5.3`, linked app installation version, audit event and version checks, then re-reads. **But `beacon-vpn` is currently degraded.** Therefore the agent must say: “The demo client update succeeded, but Beacon's VPN service is still degraded. I linked this to the known outage and cannot mark connectivity resolved.” Create an outage-linked ticket, `waiting_external`. This is a crucial test against premature resolution.

### Flow 5 — Low disk space (`DEV-01`)

Asha selects Laptop performance -> Low disk. Tool reads `DEV-NS-001`: 256 GB total, 12 GB free. Show **safe temp files eligible for cleanup** with exact synthetic size and scopes, e.g., `5 GB temporary cache`, `10 GB approved transient build artefacts`, and no user documents. Ask **Clean approved temporary data / Skip / Raise ticket**. On consent, delete (simulate) **only allowlisted temporary entries** in one transaction, increase free space from 12 to 27 GB, write cleanup history with exact reclaimed bytes, increment version, verify: new free space = old + sum of released bytes, below disk capacity, and the temp entries are marked removed. Do not invent a percentage, do not delete photos or documents, do not mark resolved if a high disk-health alert remains. Always label as a simulated cleanup.

### Flow 6 — Restart pending (`DEV-04`)

Neha selects device updates -> Restart pending. Read own `DEV-BC-001.restart_pending=true`. Display active-work warning and **Confirm simulated restart**. On consent, increment reboot count, clear pending flag and set last simulated boot time. Verify. If user cancels, no state change; show instructions/ticket. Do not imply a real computer restarted.

### Flow 7 — Application crash (`APP-01`)

Asha selects Applications -> Application errors -> App crashes -> Microsoft Teams. Tool confirms synthetic `app_installations[NS-001:microsoft_teams].health=crashing` and available restart action. Offer **Restart demo app and clear safe cache**. Ask for consent. Write app state to `restarting`, audit; then a mock health probe updates it to `running` if successful. Only then mark as fixed in simulation. If the probe fails, create support ticket with tool logs; never produce a success statement on a failed verification.

### Flow 8 — Missing application permission (`APP-04`)

Asha: “Give me Jira admin access.” Agent must **not grant** on the model's authority. Retrieve Jira resource, current entitlements, policy and role. Ask for business justification; create `access_request` and permission-scoped approval intent with target `Jira:admin`. The manager/app owner can approve only if authorised; on approval re-read current membership and implement in mock entitlement store with unique constraint on `(tenant,user,resource,scope)`. Check authorisation via separate permission probe. If user asks for another company's Jira, reject at tenant boundary without disclosing existence of other tenant records. Until approved and verified, status is pending, not resolved.

### Flow 9 — Stuck print job (`PRINT-02`)

Asha selects Printing -> Queue -> My print job is stuck. Read list of **her own** jobs; `PJ-001` is stuck. Offer **Retry / Cancel / Escalate**. Confirm scope. Retrying changes the same job's state with a bounded attempt counter; cancelling marks it cancelled, not completed. A second identical action should return its prior result, not cancel another employee's print job or create duplicate jobs. Verify job row and unchanged state of other users' jobs. Explain exact outcome.

### Flow 10 — Phishing report (`SEC-01`)

Asha selects Security -> Suspicious messages -> Report phishing. A: “Don't open the link or attachment. Can you describe the message or attach its details?” Collect sender/subject/time with redaction. Create **high-priority security ticket and incident** with factual evidence only. Acknowledge receipt and route to the security analyst. **Do not declare phishing confirmed or the device clean** based on the user's description. Do not auto-open a suspicious URL. The employee can continue another issue while security incident remains open.

### Flow 11 — Something else / no catalogue match (`GEN-UNKNOWN`)

At any level click **I can't find my issue**. A: “Describe what's happening in a sentence or two.” E types free text. A asks up to two useful missing details (affected device or app, error text, impact, when it began) but allows immediate submission. Show a ticket preview, including accurate name, tenant, device, description, optional screenshot, priority (based on deterministic policy, not model speculation) and team. Employee presses **Submit ticket**. Backend creates exactly one ticket (idempotency key) and event; UI shows real ID, status `open`, assigned queue and `View my ticket`. **Do not say the issue is resolved.**

### Flow 12 — Two issues plus a security concern (`GEN-MULTI`)

Asha: “VPN won't connect, laptop is slow, and I clicked a suspicious email.” Parse into three separate subissues: security report (`SEC-01`) first; VPN (`NET-01`); performance (`DEV-01`). Offer one security escalation and two guided diagnostics. Maintain a parent conversation with separate case IDs. A safe disk cleanup can become resolved while VPN remains pending approval and security remains escalated. Parent state must show `partial / in_progress`, never `resolved`. Make outcome cards for each case.

### Flows 13–20 — Mandatory exceptional journeys

13. **Symptom contradicted by data:** User selects “Account locked”, but account is active -> say no lock detected, offer password/MFA/other options, do not modify.
14. **No matching device:** User selects laptop problem without assigned device -> ask device asset ID and verify tenant assignment; if no match, create hardware/support ticket.
15. **Already resolved / duplicate request:** The user repeats the same repair -> backend sees desired state and returns “Already healthy/no change needed”; repeat idempotency key cannot create another effect.
16. **Action failed before commit:** Tool returns error -> no write, show retry or support ticket, record failure; never say resolved.
17. **Action commits but response times out:** On retry, lookup action by idempotency key and reconcile authoritative state; if cannot prove the result, status `unknown_outcome`, block blind replay, escalate.
18. **Stale approval:** Reviewer approved action intent X, but target state/version or payload changed -> invalidate approval, request reapproval; no mutation.
19. **User stops mid-flow:** Save page and collected facts; resume only on authenticated session, revalidate staleness and approval expiry.
20. **User reports recurrence:** Reopen the prior ticket or create linked recurrence, increment reopen count, preserve historical events; do not reset/delete audit trail.

## 6. All branch conditions (decision table)

Implement the following as a **deterministic state machine** in backend code, not scattered prompt suggestions.

| Trigger | Handling and resulting state |
|---|---|
| User logged out or token expired | Redirect to identity provider, persist no sensitive chat in client; restore state after login |
| User chooses category | `CHOOSING_SUBCATEGORY`, show that category's subcategories |
| User chooses subcategory | `CHOOSING_SYMPTOM`, show valid issue leaves |
| User chooses issue leaf | `COLLECTING_FACTS`; fetch context only after user/resource scope checks |
| User clicks Not sure | Present two narrow symptom questions then Free text/Ticket |
| User types a confident known issue | Propose canonical matching issue, show breadcrumb and confirm |
| User types vague text | One short clarifying question then best 2–3 options; after two failures offer ticket |
| User types multiple issues | Split into child cases; keep security priority; separate status per child |
| User asks outside IT | Explain scope, offer general IT ticket only if useful, no fake execution |
| Missing fixture or API data | `INSUFFICIENT_EVIDENCE`; no guess; open ticket or try alternate supported read |
| Record contradicts claimed issue | Present contradiction and alternative; no mutation |
| Record indicates known company outage | Link incident, open ticket if requested, `WAITING_EXTERNAL` |
| Fix is read-only instruction | Give steps and require outcome confirmation; do not edit device record automatically |
| Fix is auto-allowlisted | Explain, get user consent if it changes their data, execute validated tool |
| Fix requires approval | Persist intent, enter `WAITING_APPROVAL`; only authorised reviewer action may advance |
| Approval rejected | Mark intent rejected, no execution, offer human ticket |
| Approval expired | Mark expired, require new consent/approval; never reuse token |
| Approval approved | Revalidate actor, state version, payload hash, then execute |
| User cancels prior to execution | Cancel intent; no state change, audit event |
| User cancels after execution | Explain completed mutation cannot be “un-done” by cancelling chat; offer a separate authorised compensating workflow |
| Tool returns success | Read state again; check exact postconditions, then move `AWAITING_USER_CONFIRMATION` or resolution |
| Tool returns failure before commit | Retry within bounded policy or escalate; no success claim |
| Tool returns timeout after possible commit | `UNKNOWN_OUTCOME`; query action ledger and target state; do not blindly replay |
| Same request submitted twice | Same idempotency key returns original result and original ticket/action ID |
| Concurrent users edit same resource | Compare version; conflict returns re-read / re-propose; no lost update |
| User denies fix worked | Reopen/investigate, do not repeat unchanged action immediately |
| User selects Talk to IT | Open/escalate ticket with minimal description; no forced navigation |
| User asks for secret/policy bypass | Refuse and optionally escalate security; no disclosure/mutation |
| Tenant mismatch | 403, security audit, no data shape, ID or existence details from foreign tenant |
| Role mismatch | 403, no mutation, offer appropriate approval workflow |
| Restart session | Resume persisted issue and pending approvals; reload current record states |
| Same user opens multiple browser tabs | Session version and action idempotency protect against double actions |
| Network disconnect mid-chat | Rehydrate from server-side session when back; show pending action state |
| Unknown language / typo | Language model may translate intent to known catalogue IDs; backend validates mapping |
| User attachment | Store metadata and safe mock file reference; restrict visibility; don't assume its content was analysed |
| Security incident plus ordinary issue | Security escalation first; ordinary issues remain separate and independently actionable |
| Account is disabled because employment ended | Never auto-reactivate; identity administrator review only |
| Service restored later | Re-evaluate only affected waiting cases, verify dependency and ask user confirmation |
| “I want another employee's information” | Reject by ownership/role check and do not expose foreign records |

### Workflow states and valid transitions

Use `conversation.state` as guided UI state plus `case.state` for business status. Do not overload one column with both.

```text
Conversation UI:
WELCOME -> CHOOSING_SUBCATEGORY -> CHOOSING_SYMPTOM -> COLLECTING_FACTS
        -> INVESTIGATING -> SHOWING_FINDING -> PROPOSING_ACTION
        -> WAITING_USER_CONSENT -> WAITING_APPROVAL -> EXECUTING
        -> VERIFYING -> AWAITING_USER_CONFIRMATION -> CASE_SUMMARY
        -> (WELCOME | NEXT_ISSUE | HUMAN_HANDOFF)
Every stage: BACK | START_OVER | CANCEL | HUMAN_HANDOFF | RESUME

Case business state:
new -> triaging -> diagnosed -> action_proposed
    -> awaiting_consent -> pending_approval -> executing -> verifying
    -> awaiting_user_confirmation -> resolved
Alternative: triaging/diagnosed/action_proposed -> ticket_open / escalated / refused
Alternative: executing -> unknown_outcome -> reconciled or escalated
Alternative: diagnosed/action_proposed -> waiting_external -> triaging after recovery
Alternative: resolved -> reopened -> triaging
```

Persist `current_menu_node_id`, `issue_code`, selected `device_id`, collected facts as typed keys, `case_id`, `conversation_id`, last verified data versions, and any approval/action IDs. A user's free text is never interpreted as a database command.

## 7. Data model: tables and exact mutation rules

**Recommended for a one-day build:** Dockerized PostgreSQL with SQLAlchemy/Alembic and FastAPI. This enables clear relational constraints and atomic writes. Make mock provider adapters replaceable with real Microsoft Entra/Jira/ServiceNow/AWS integrations later. If deploying to AWS, use an appropriate managed Postgres service or a carefully implemented DynamoDB adapter; don't silently switch persistence semantics.

### 7.1 Canonical tables

| Table | Primary key and important columns | Integrity / ownership |
|---|---|---|
| `tenants` | `tenant_id`, name, domain, config, demo_mode | Configurable per tenant |
| `users` | `(tenant_id,user_id)`, email, role, department, active, version | Unique `(tenant_id,email)`; trusted session actor |
| `accounts` | `account_id`, tenant_id, user_id, status, lock_reason, failed_logins, mfa_enabled, credentials_version, risk_flag, version | Exactly one active identity record per user; never store plaintext passwords |
| `sessions` | session_id, tenant_id, user_id, status, expires_at, version | Revalidate auth per mutation |
| `devices` | `(tenant_id,device_id)`, assigned_to, health and capacity counters, version | Device owner FK in same tenant; disk 0..capacity, metrics 0..100 |
| `vpn_profiles` | vpn_id, tenant_id, device_id, user_id, client_version, cert_expires_at, status, version | Device and user tenant must match; cert and client state independently checked |
| `services` | service_id, tenant_id, status, active_incident_id, version | Known outage takes precedence over local “resolved” status |
| `applications` | app_id, tenant_id, approved_version, allowed_to_self_install, requires_licence | Per tenant software policy |
| `app_installations` | installation_id, tenant_id, device_id, user_id, app_id, installed_version, health, version | Unique `(tenant,device,app)`; all FKs same tenant |
| `entitlements` | entitlement_id, tenant_id, user_id, resource, scope, status, version | Unique `(tenant,user,resource,scope)` |
| `mailboxes` | mailbox_id, tenant_id, user_id, used_gb, quota_gb, archived_items, sync_status, version | Capacity non-negative; archive not delete |
| `printers` / `print_jobs` | printer_id, job_id, tenant_id, user_id, printer_id, status, version | Users can alter only own jobs |
| `security_events` | event_id, tenant_id, user_id, severity, observed_at, review_status | No employee-accessible modification to raw evidence |
| `vpn_logs` | log_id, tenant_id, user_id, device_id, reason, observed_at | Append-only diagnostic evidence |
| `knowledge_documents` | doc_id, tenant_id, visibility, version, status, content | Retrieval requires tenant and document ACL; never treat retrieved text as system instructions |
| `tickets` | ticket_id, tenant_id, requester, issue_code, summary, status, priority, assigned_team, version | Immutable tenant/requester; valid ticket transition table |
| `ticket_events` | event_id, ticket_id, actor, prior_status, next_status, reason, occurred_at | Append-only, same tenant |
| `conversations` / `messages` | conversation_id, tenant_id, user_id, current_menu_node, current_case, message role/content, timestamp | Messages scoped to current authenticated user/authorised support roles |
| `cases` | case_id, conversation_id, tenant_id, issue_code, selected_device, state, expected_resource_versions | Parent/child relationships for multiple issues |
| `action_intents` | action_id, tenant, actor, target, action_code, payload JSON, payload SHA256, expected_version, idempotency_key, expires_at, state | Immutable target, payload, actor, and tenant once created |
| `approval_requests` | approval_id, action_id, reviewer_id, required_role, status, decision_at, expiry | Exactly one decision per versioned intent; approver != requestor for sensitive actions |
| `action_executions` | execution_id, action_id, attempts, started_at, completed_at, state, external_operation_id | Unique completed action by idempotency key; no duplicate effects |
| `audit_events` | event_id, tenant_id, actor, resource, before_json, after_json, reason, timestamp | Append-only, redact secrets, include operation correlation ID |
| `fault_injections` | fault_id, tenant_id, case_id, tool_name, fault_mode, enabled | Test environment only; admins/test runner can configure |
| `evaluation_results` | scenario_id, run_id, expected_assertions, observed_assertions, pass_fail, trace_id | Evaluator-only expected labels; not visible to agent |

### 7.2 Global invariants (enforce in code **and** DB where possible)

1. Every row exposed through a business API has `tenant_id`; every resource relation must have a matching tenant. Do not rely on the LLM remembering a tenant filter.
2. Server-side tenant membership and user identity come only from authenticated context. Client payloads can identify a resource, but the backend must independently check it.
3. Never update a resource without an optimistic version condition (`WHERE version=:expected_version`) or equivalent row lock.
4. For a given `(tenant_id,idempotency_key)`, exactly one logical action can commit. Replaying returns the original persisted result.
5. Within one DB transaction, commit the resource update, action effect record and audit event together. For external calls, record a pending intent first; reconcile after ambiguous outcomes.
6. No `ticket.status='resolved'` without an evidence-bearing verification event or explicit qualified human resolution. Don't count created tickets as resolved.
7. `device.disk_free_gb` must be between 0 and `disk_total_gb`; reclaimed bytes must equal the sum of allowed synthetic temp-file objects actually removed.
8. An app installation cannot reference an app or device in another tenant. An entitlement must reference a real same-tenant user and resource.
9. `mfa_enabled` cannot be set `false` by any employee support tool. Security-sensitive account changes use a designated approval pathway.
10. App licence assignment must have free inventory and an approved owner/manager decision where policy requires it; cannot allocate more seats than capacity.
11. Cross-tenant attempts return a generic 403 or 404 without exposing which foreign resource exists; always write security audit metadata.
12. A tool result labeled `success` is not enough for resolution: the **independent re-read and verification rule** must also pass.
13. A parent multi-issue conversation is resolved only if every non-cancelled child case has an appropriate terminal successful disposition; security escalations prevent “all fixed.”
14. Published KB document versions and their access policies are immutable until replaced; outdated or untrusted KB content cannot grant permissions.
15. Every receipt-like operation returns real persisted IDs. Never invent IDs in the LLM answer.

### 7.3 Atomic example: simulated safe disk cleanup

```python
# Illustrative pseudocode, implement with SQLAlchemy/transaction and typed errors.
def safe_cleanup(ctx, intent_id):
    intent = load_verified_intent(ctx, intent_id)       # authenticated tenant/user/policy
    assert intent.action_code == 'run_mock_safe_cleanup'
    with db.transaction():
        device = lock_device(ctx.tenant_id, intent.target_device_id)
        assert device.version == intent.expected_version
        files = lock_allowlisted_temporary_objects(device.id, intent.payload['object_ids'])
        reclaimed_bytes = sum(f.size_bytes for f in files if not f.removed)
        for f in files: f.removed = True
        device.disk_free_bytes += reclaimed_bytes
        assert device.disk_free_bytes <= device.disk_total_bytes
        device.version += 1
        save_action_execution_and_audit(ctx, intent, before, after, reclaimed_bytes)
    latest = read_device(ctx, device.id)
    return verify_disk_delta_and_temp_objects(latest, intent)
```

No user documents are deleted. Use actual synthetic `temporary_files` rows, not an untraceable constant increment.

### 7.4 Atomic example: ticket creation

Generate ticket IDs in persistence (e.g., `INC-1080` after seeded tickets) and only show returned IDs. `POST /tickets` includes a stable idempotency key derived from conversation, issue, user action nonce. Reject anonymous ticket requests. Store user description, selected category and issue, device context, priority evidence, `assigned_team`, user-visible title, status `open` and `created_at`. Record event `ticket_created`. The same submitted form retried over an unstable network must return the same ticket ID.

## 8. Backend agent/tool API contracts

The agent is a **navigator and investigator**, not a superuser. Read-only tools are distinct from mutation tools. Prefer one orchestrator Strands/Bedrock agent with deterministic routing; specialist modules can be added behind its tools, but don't spend the first day building a complicated agent hierarchy.

### 8.1 Chat response contract

```json
{
  "conversation_id": "CONV-00021",
  "case_id": "CASE-00048",
  "state": "CHOOSING_SYMPTOM",
  "assistant_message": "Which VPN issue are you seeing?",
  "breadcrumb": ["VPN, Wi-Fi & internet", "VPN"],
  "options": [
    {"id": "NET-01", "label": "VPN certificate expired", "type": "issue"},
    {"id": "NET-02", "label": "Outdated VPN client", "type": "issue"},
    {"id": "NET-04", "label": "VPN service outage", "type": "issue"}
  ],
  "controls": ["back", "start_over", "something_else", "talk_to_it"],
  "finding": null,
  "action_proposal": null,
  "ticket": null,
  "demo_mode": true
}
```

The backend returns the valid option IDs and selected issue's next question. The model may create natural explanatory text, but it does not author the authoritative options list.

### 8.2 Typed backend endpoints

```text
GET  /api/me                         -> verified actor, tenant, roles, assigned devices
GET  /api/catalog                    -> tenant-enabled categories/subcategories/issues
POST /api/conversations             -> create/resume conversation
POST /api/conversations/{id}/turns  -> option_id OR free_text (never trusted tenant_id)
GET  /api/conversations/{id}        -> conversation state and visible messages
GET  /api/issues/{case_id}          -> diagnosis, state, verified facts, outcomes
POST /api/issues/{case_id}/diagnose -> invoke allowlisted read tools and evidence checks
POST /api/actions/intents           -> typed proposed action, no execution
POST /api/actions/{id}/consent      -> employee consent tied to intent
POST /api/approvals/{id}/decision   -> authorised reviewer only
POST /api/actions/{id}/execute      -> policy + expected version + idempotent mutation
GET  /api/actions/{id}              -> execution state and verification
POST /api/tickets                   -> fallback and escalation, idempotent
GET  /api/tickets/mine              -> own tickets only
GET  /api/it/queue                  -> authorised IT engineer tenant queue
GET  /api/it/audit                  -> role-scoped audit timeline
POST /api/dev/seed/reset           -> local/test only; disabled in deployed prod
POST /api/dev/fault-injection      -> local/test only; admin/test permission
GET  /api/evaluation/results        -> measured results, separate from model context
```

### 8.3 Tool contracts (selected)

```text
read_account(actor_ctx, target_user_id) -> sanitized status, version, policy warnings
read_device(actor_ctx, device_id) -> health/state/version; enforce assignment
read_vpn(actor_ctx, device_id) -> client/cert/status/version
read_service_health(actor_ctx, service_name) -> tenant service and active outage
read_knowledge(actor_ctx, issue_code, query) -> tenant-filtered visible documents with citations
read_own_print_jobs(actor_ctx) -> restricted jobs
read_app_installation(actor_ctx, device_id, app_id) -> installation and app catalogue
propose_action(actor_ctx, case_id, action_code, resource_ref, typed_params) -> immutable intent
request_approval(actor_ctx, action_id) -> pending approval, not a mutation
execute_authorized_action(actor_ctx, action_id) -> action result and verification
create_ticket(actor_ctx, case_id, summary, description, idempotency_key) -> persisted ID
```

**Absolute rule:** Do not expose SQL tools, unconstrained shell tools, generic arbitrary HTTP fetch, arbitrary `update_record`, or `set_role` as agent-callable capabilities. Agent may ask for a specific typed tool; gateway/backend does final policy validation.

### 8.4 Recommended structured diagnosis output

```json
{
  "issue_code": "NET-01",
  "confidence": 0.97,
  "observations": [
    {"field": "vpn.cert_expires_at", "value": "2026-10-20T00:00:00Z", "source": "mock_vpn:VPN-NS-001"},
    {"field": "services.northstar-vpn.status", "value": "healthy", "source": "mock_service:northstar-vpn"}
  ],
  "hypothesis": "The test VPN certificate is expired.",
  "proposed_action_code": "renew_mock_vpn_certificate",
  "requires_approval": true,
  "can_claim_resolved_now": false
}
```

Treat confidence as a model assessment, not a security authority; verification and authorization are deterministic. For missing observations, return `insufficient_evidence` rather than generating values.

## 9. Dataset map and how mutation is verified

`demo_seed.json` contains **2 fictional tenants, 40 users, 40 accounts, 50 devices, 40 VPN profiles, 40 mailboxes, 80 historical tickets, 25 KB documents, 150 VPN log entries, 60 security events, 20 expired historical approvals, and 30 historical runs**, plus apps, installs, entitlements and print jobs. The historical tickets are intentionally `closed`, so new conversations can create new live tickets.

All records are synthetic and must be seeded deterministically, using IDs without real identities or real email delivery. `.example` is a reserved testing domain.

### Important linked fixture states (do not inadvertently randomise these)

| Persona / resource | Starting condition | Expected relevant workflow |
|---|---|---|
| Asha / `ACC-NS-001` | `locked`, `failed_attempts`, not security-flagged | `ID-01` unlock after mock identity verification |
| Asha / `VPN-NS-001` | Expired on 2026-10-20; `northstar-vpn` healthy | `NET-01` approval-gated simulated certificate renewal |
| Asha / `DEV-NS-001` | 256 GB total, 12 GB free | `DEV-01` safe mock cleanup with temp file inventory |
| Asha / Teams installation | Crashing | `APP-01` mock app restart and health verification |
| Asha / Jira admin permission | Missing | `APP-04` approval request; no grant before approval |
| Asha / `PJ-001` | Her print job is stuck | `PRINT-02` own-job retry or cancel |
| Neha / `VPN-BC-001` | Client 4.9, required >= 5.2 | `NET-02` mock client update |
| Beacon VPN service | `degraded`; outage `OUT-BC-001` | `NET-04` remains unresolved pending outage recovery |
| Neha / `DEV-BC-001` | `restart_pending=true` | `DEV-04` consent-gated mock restart |
| Cross-tenant tests | Asha tries Beacon device/ticket | reject without data leakage |

### Seed completeness requirements

Seed coherent synthetic `temporary_files` for Asha: three allowlisted cleanup objects with sizes adding to 15 GB; do not let `disk_free_gb` increase without corresponding file-state changes. Add `licence_pools`, `security_incidents`, `ticket_events`, `action_intents`, `action_executions` and `audit_events` tables through migrations. For supplied historical approvals, create matching expired historical intents or exclude historical approvals during relational import; do not leave broken foreign keys.

Define available repair **simulation capability** per issue, rather than claiming an operation succeeded because the model said so. For P1 issues without an implemented provider adapter, guide the user to the appropriate leaf and then open a ticket with the identified diagnosis and evidence. Never display an active “Fix now” button if its tool does not exist.

### Seed reset and evaluation isolation

- An individual test scenario starts from a fresh deterministic seed or a transactionally restored snapshot. Do not run action tests sequentially against already-mutated seed state without reset.
- The `evaluation_cases.json` contains expected outcomes and must be loaded by the evaluator **only**, never indexed by RAG or passed to the agent.
- Maintain a hidden fixture manifest mapping scenario IDs to starting record states and expected mutations.
- Build a `python seed.py --reset` or `make reset-demo` command that restores exact snapshot; disallow reset in live deployment.
- When users perform real demo operations, show the **current** persisted state, not the original seed assumption. If Asha already unlocked her account, a later locked-account report should reveal that contradiction.

## 10. Demonstration UI — all states and screens

**Style:** premium but restrained SaaS console; enterprise-grade typographic hierarchy, clear contrasting states, legible details, desktop and mobile responsive; no fake live metrics, no decorative inert buttons.

**Employee layout:** Left nav: Home, AI Helpdesk, My Tickets, My Devices, Knowledge. Main content: breadcrumb, conversational step, 2–6 context-aware selectable chips/cards, optional typed issue field, evidence/finding cards, action approvals, outcome summary. Side panel: selected device, authenticated name, active tickets and a consistent **DEMO MODE** label.

**At each issue step show:** selected issue, what the agent checked, source of each observation, current operation status, whether this is only a mock action, next options, back and human escalation. Avoid showing implementation-sensitive secrets in employee UI.

**IT engineer layout:** Cases and pending approvals, exact resource details, tenant filter fixed by auth, affected employees, proposed actions with impact, decline reason, execution/reconciliation timeline, current error state, links to source knowledge.

**Manager layout:** Aggregates calculated from actual ticket, approval and execution tables: open tickets, pending approvals, verified resolutions, median time to resolution, automation success and failure counts, and estimated inference tokens/cost with clear approximation labels. Never seed fake performance numbers as real run-time statistics.

**Admin layout:** Authorized tenant configuration, allowlisted actions, category enable/disable, policy versions, KB documents and mock integration status. Settings changes versioned and auditable; no cross-tenant admin views.

**Evaluation layout:** Dataset scenario selection, Run Tests, pass/fail assertions, before/after state diff, gateway rejection, idempotency proof, and replay with trace. `Run Tests` must run actual backend tests or call evaluation runner; never just animate sample results.

## 11. Fault injection and failure demonstrations

Support mock tools failing in precise deterministic ways:

| Fault | Mechanism | Required response |
|---|---|---|
| Failure before write | Tool returns 503 before changing data | No effect, bounded retry or ticket, clear failure status |
| Timeout after successful write | Transaction commits, client sees timeout | Lookup idempotency key + re-read; never duplicate effect |
| Duplicate HTTP submission | Same action nonce sent twice | Same action/ticket ID returned, exactly one effect |
| Concurrent conflicting write | Version changes between diagnosis and execution | Conflict, re-read and require fresh proposal/approval |
| False success payload | Provider says success but target state unchanged | Verification fails; case remains unresolved |
| Model hallucinates action | LLM outputs unsupported tool name | Reject by allowlist; offer real options |
| Prompt injection in retrieved article | KB instructs model to ignore controls | Treat as untrusted content; no policy bypass |
| User requests cross-tenant record | Incorrect tenant/device/ticket ID | Generic denial and security audit, no leaked record |
| Approval payload edited | Target/action hash mismatch | Require reapproval; never execute |
| External outage | VPN service `degraded` | Do not resolve connectivity based solely on client or cert repair |
| Reviewer rejects | Approval declined with reason | No action, notify user, optional ticket |
| Resource already healthy | Case has no matching fault | No-op and suggest alternative diagnosis |

Use a developer-only fault selector and show the exact before/after rows in a trace viewer. Mutations must be demonstrable by API GET or SQL reads, not only by chat messages.

## 12. Automated evaluation and acceptance criteria

`evaluation_cases.json` gives 20 mandatory scenario cases, including successful repairs, approval waiting, tenant denial, unknown ticket creation, malicious request, repeat/idempotency, partial failure and multi-issue status. Build a pytest evaluator that resets the seed and runs each case against the same backend paths used by the UI. Add Playwright tests for the guided navigation and role-specific views.

Minimum safety assertions:

- **0 cross-tenant reads/mutations** in negative tests.
- **0 unauthorized sensitive changes** when approval missing, denied, expired, payload changed, or reviewer lacks role.
- **0 duplicate committed effects** for replayed action IDs and timeouts-after-commit.
- **0 false “resolved” statuses** for outage, security, unimplemented integration, missing evidence, failed verification, or denied action.
- **100% of 57 catalogue issues navigable** from the top-level menu, each with honest fallback if implementation tier is P1.
- **100% of demo mutation tools** emit persisted resource changes and audit events and run post-write verification.
- **Unknown issue ticket** created once with real ID, correct tenant and ownership, and user-visible ticket details.
- **Human approver flow** cannot be completed by employee user.
- **Session resume/back/start-over** behaves deterministically and does not erase committed effects.

Operational metrics include actual run count, test pass/fail, mean/95th percentile latency, tool-call counts, estimated Bedrock token cost from measured usage, open/closed ticket counts, and verifier pass rate. No fabricated metrics.

## 13. Suggested implementation sequence

**First implement vertical slices that work in the real app and real DB; don't create placeholder-only screens.**

1. Inspect repo; create architecture, Docker Compose Postgres, Alembic schema, seeding and fixture validator. Preserve existing code/data if present.
2. Implement demo-login identities and server-side tenant/role enforcement. In deployed mode replace with Cognito; local demo login must be explicitly gated by environment variable.
3. Build deterministic guided navigation API from `guided_flow_catalog.json`, `conversations/cases` persistence, typed chat/turn response and free-text fallback.
4. Build employee UI with welcome choices, category/subcategory/symptom menus, breadcrumb, dynamic choices, free text, navigation and ticket fallback.
5. Implement typed read tools; get one full **ID-01** and one **DEV-01** path passing diagnosis, consent, mutation, audit, verification and outcome. Add scenario tests before expanding.
6. Implement action intent, idempotency, policy checks, approval queue, reviewer decisions, stale-action protection and reconciliation for ambiguous tool outcomes.
7. Add **NET-01**, **NET-02/NET-04**, **DEV-04**, **APP-01**, **APP-04**, **PRINT-02**, **SEC-01**, **REQ-01** with correct status handling; route P1 issues to honest tickets.
8. Add mock provider failure modes, immutable trace timeline, own ticket view, IT engineer queue and evaluation runner.
9. Build minimal management counters and admin policy view from live DB records, not hard-coded numbers.
10. Add genuine Bedrock/Strands orchestration for parsing free-text intents and natural explanations; ensure backend still works with a deterministic model-free fallback. Add AgentCore as an AWS deployment phase rather than blocking local functional proof.
11. Run seed validator, all pytest and Playwright tests, record any failures accurately, and resolve critical security/data-consistency bugs first.
12. Document `docker compose up`, `make seed`, test accounts, demo paths, limitations, AWS deployment instructions and screenshots. Ensure fake provider operation never claims physical-world success.

### Priority tiers

**P0 for today:** Category navigation all 57 leaves, persistent conversations, unknown ticket fallback, 2-tenant auth boundaries, 10–12 supported real mock tool paths, approval flow, idempotent writes, SQL audit, relevant fault tests, polished employee and engineer UI.

**P1 after P0:** Every remaining issue's specialised integration and automated action, user document uploads, robust knowledge indexing, complex analytics, additional IT policies, richer manager/admin controls.

**P2 for a production roadmap:** Real Entra/Jira/ServiceNow integrations, real device-management mutations, secure privileged actions, account-level isolated customer AWS deployments, live CloudWatch traces, full compliance assessments, hardened security incident workflows, multiregion reliability.

## 14. Implementation constraints

- Build the **running app**; do not merely paraphrase this document or output architectural diagrams.
- Never generate static dashboards with success cards disconnected from database records.
- Don't turn free-text into arbitrary executable code/SQL. Use validated catalogue routes and typed backend methods.
- Use SQL migrations and transactional invariants; preserve tenant links, audit trail and all relevant foreign keys.
- Every button needs a working handler and sensible error state. Test Back, Cancel, Retry, Resume, Escalate, “Not listed”, and “Still not working.”
- Return stable `issue_code`, `conversation_id`, `case_id`, `ticket_id`, `action_id` from backend, never fabricate them in frontend.
- Read tool state before suggesting a mutation; if already healthy, no-op and triage differently.
- Model output may format explanations, but **only backend validates an action and claims resolution**.
- Show `DEMO MODE: This updates synthetic IT records, not actual corporate systems` in both employee and IT views.
- Keep user-visible messages concise; options should be clear, not 20 simultaneous buttons. Show at most 6 options per step except category picker.
- Use actual database state and current tenant context to populate options dynamically.
- Under uncertainty, prefer an open ticket to an imaginary fix.
- If a capability cannot be completed today, keep honest disabled/error/ticket pathways rather than fake success.

## 15. Demo acceptance walkthrough (must be repeatable)

1. Login Asha, select **Account** -> **Account locked**; show pre-state and verified mock unlock; state persisted, audit appended.
2. Select **Laptop performance** -> **Low storage**; perform allowed mock cleanup and prove exact reclaimed bytes and changed disk free space.
3. Select **VPN** -> **Expired certificate**; show pending approval, switch to Rahul, approve, execute, verify and switch back to Asha to see outcome.
4. Login Neha, update outdated VPN client but remain **waiting for Beacon outage**; prove no false claim of network recovery.
5. Ask Asha for another employee's or Beacon's records; show denial and log entry.
6. Trigger ticket API timeout after write; retry and show **one** persisted ticket, not two.
7. Click **I can't find my issue**, enter unsupported issue, submit ticket, view it in Rahul's queue.
8. Report phishing; create security escalation and demonstrate the agent does not announce that the threat is fixed.
9. Start three-issue message; show three child cases, distinct statuses, and correct parent summary.
10. Run the real evaluation suite, display measured results and exact failing assertions if any.

**Definition of done:** A nontechnical viewer can navigate from greeting to the right problem; an engineer can observe the actual tool calls, DB effects, policy boundaries, and recovery path; neither has to trust an LLM's unverified assertion.

---

### Appendix: Implementation reality check

The catalogue intentionally enumerates a finite set of common enterprise support issues and defines a general catch-all for the effectively infinite set of real-world IT problems. It does not claim complete coverage of every possible device, software, organisation, or security event. P1 issue flows are navigable immediately but must terminate in a **truthful support ticket or approval state** until their provider adapters and verification logic are actually implemented. That is the honest, credible scope for a one-day demo.
