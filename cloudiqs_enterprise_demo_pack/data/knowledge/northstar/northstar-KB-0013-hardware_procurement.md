# Hardware refresh and battery warranty

**Document ID:** northstar-KB-0013  
**Organisation:** Northstar Technologies  
**Classification:** internal  
**Version:** 1.2  
**Effective date:** 2026-10-17  
**Service:** hardware_procurement

## Purpose
This controlled internal document defines the approved investigation workflow for hardware refresh and battery warranty. It is synthetic content for an enterprise AI demonstration and does not grant an agent any authority.

## Authoritative policy
Check asset ownership, purchase record, warranty, device health history and manager approval. Purchase orders are never authorised by the helpdesk LLM.

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
