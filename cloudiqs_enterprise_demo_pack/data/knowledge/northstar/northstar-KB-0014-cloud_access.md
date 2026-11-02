# Cloud role access

**Document ID:** northstar-KB-0014  
**Organisation:** Northstar Technologies  
**Classification:** admin  
**Version:** 1.2  
**Effective date:** 2026-10-16  
**Service:** cloud_access

## Purpose
This controlled internal document defines the approved investigation workflow for cloud role access. It is synthetic content for an enterprise AI demonstration and does not grant an agent any authority.

## Authoritative policy
AWS identity federation requests must be approved by business owner and security owner. Never create administrator roles via the helpdesk agent. Use time-bound least-privilege grants.

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
