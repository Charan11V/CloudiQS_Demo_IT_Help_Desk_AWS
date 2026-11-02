# Ticket priority and SLA

**Document ID:** northstar-KB-0017  
**Organisation:** Northstar Technologies  
**Classification:** internal  
**Version:** 1.2  
**Effective date:** 2026-10-13  
**Service:** business_apps

## Purpose
This controlled internal document defines the approved investigation workflow for ticket priority and sla. It is synthetic content for an enterprise AI demonstration and does not grant an agent any authority.

## Authoritative policy
Priority comes from business impact and urgency. P1 requires 24x7 response. Waiting on vendor may pause some SLAs but not all. Escalation must follow the configured support calendar.

## Triage checklist
1. Verify the caller and tenant through the authenticated application session.
2. Obtain only the authorised records relevant to the reported symptoms.
3. Correlate recent device, identity, ticket and service-health evidence; note conflicting or stale sources.
4. Separate confirmed observations from hypotheses and record references.
5. For any business-state mutation, check the policy engine and create the required approval request.
6. Re-read the affected system after the operation and update the linked ticket with the verified outcome.

## Escalation
If data sources disagree, a security alert is present, or side-effect status is unknown, stop autonomous mutations and escalate to the owning service team. For P1 major incidents notify on-call.

## Data handling
Never expose another tenant's records. Keep internal diagnostic details out of employee-visible responses. Redact tokens, OTPs, credentials, and personal messages in traces.

## Example follow-up question
What changed between the last known good session and the first failed attempt?
