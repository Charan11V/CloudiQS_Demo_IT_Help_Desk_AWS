# Account lockout and identity proofing

**Document ID:** beacon-KB-0002  
**Organisation:** Beacon Retail Group  
**Classification:** employees  
**Version:** 3.0  
**Effective date:** 2026-10-28  
**Service:** identity_and_access

## Purpose
This controlled internal document defines the approved investigation workflow for account lockout and identity proofing. It is synthetic content for an enterprise AI demonstration and does not grant an agent any authority.

## Authoritative policy
Self-service account recovery starts with verified sign-in context. Locked accounts may be unlocked only after an independent identity assurance step and a separately approved action. MFA reset is not supported by the autonomous agent.

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
