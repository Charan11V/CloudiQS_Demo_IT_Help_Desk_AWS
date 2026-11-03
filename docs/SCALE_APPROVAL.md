# Approval-gated scale (cost-safe)

## Principle

The hiring demo stays on **one `t4g.small`** until a human explicitly approves more capacity.  
CloudWatch can **notify** you (email/SMS via SNS); it must **not** auto-buy fleet capacity.

## Current control plane

| Piece | Behavior |
|---|---|
| Default capacity | 1× EC2 Compose host |
| Alarm | CPU high → SNS (if email configured on stack) |
| Approve | `python scripts/aws/approve_scale.py --confirm APPROVE_SCALE --tier 2` |
| Effect today | Writes `/cloudiqs-demo/SCALE_APPROVAL` + EC2 tags — **does not start more instances** |
| Real scale-out | Manual/IaC cutover to ALB+ECS/ASG with `desired=N` only after approval |

## Phone / PC approval flow (demo narrative)

1. Alarm email/SMS: “Demo CPU high — approve scale?”
2. On PC/phone: run approve script (or Console → set SSM param / tag).
3. Interviewer sees approval artifact without surprise AWS spend.
4. Optional later: Lambda that only runs after approval token present.

## Why this is “scale-ready” without burning credits

- Architecture boundary is documented (stateless web/agent, managed DB path).
- FinOps gate is real (human approve before spend).
- Product demo remains cheap until you choose otherwise.
