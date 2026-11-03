# AWS Cost Model — CloudiQS HELIO Demo

**Region:** `us-east-1`  
**Pricing sources:** AWS public list prices / aggregator snapshots (verify before deploy; prices change).  
**Constraint:** ~$100 credits hard ceiling; target **<$20–25/mo** if left running; one-week demo a few dollars; Bedrock eval **<$5**.

> Billing data lags. Budgets are not real-time hard stops.

## Architecture under cost control

| Service | Resource | Dimension | Fixed/Usage | Est. hourly | Est. daily | Est. 7-day | Est. monthly (730h) |
|---|---|---|---|---|---|---|---|
| EC2 | 1× `t4g.small` (Graviton) | On-Demand Linux | Usage (stops when instance stopped) | $0.0168 | $0.40 | $2.82 | **$12.26** |
| EBS | 20 GiB gp3 encrypted | $/GB-mo | Fixed while volume exists | ~$0.0022 | $0.053 | $0.37 | **$1.60** |
| Public IPv4 | 1 address | $0.005/hr | Usage while allocated | $0.005 | $0.12 | $0.84 | **$3.65** |
| CloudFront | Price class 100 | Requests + egress | Usage | ~$0 | low | ~$0.10–1 | **~$0.50–2** (light demo) |
| ECR | 3 repos, lifecycle keep 5 | Storage | Usage | ~$0 | low | low | **~$0.10–0.50** |
| S3 | Private backup bucket, 14d expiry | Storage/API | Usage | ~$0 | low | low | **<$0.20** |
| SSM Parameter Store | Standard parameters | Standard tier | Free at demo scale | $0 | $0 | $0 | **$0** |
| CloudWatch Logs | 3 groups, 7-day retention | Ingestion + storage | Usage | low | low | low | **~$0.50–1** |
| CloudWatch Dashboard | 1 dashboard | First 3 dashboards free | Free | $0 | $0 | $0 | **$0** |
| AWS Budgets | 1 budget | First 2 free | Free | $0 | $0 | $0 | **$0** |
| Bedrock | On-demand Nova Lite (or successor) | Tokens | Usage | variable | variable | **budget <$5 total eval** | keep low |
| VPC/IGW/SG | Minimal public VPC | — | Free | $0 | $0 | $0 | **$0** |

### Totals (approximate, instance **running**)

| Window | Estimate |
|---|---|
| Hourly | ~$0.025 (compute + IPv4 + tiny fixed) |
| Daily | ~$0.60 |
| 7-day | ~$4–6 (+ Bedrock tokens) |
| Monthly | **~$18–22** + Bedrock |

### Totals (instance **stopped**)

Continues: EBS (~$1.60), public IPv4 (~$3.65), ECR/S3/CF residual → roughly **~$5–7/mo**.  
**Action:** `make aws-stop-demo` between sessions.

## Why we did NOT use …

| Service | Why skipped |
|---|---|
| NAT Gateway | ~$32+/mo fixed — unjustified for one public demo host |
| RDS / Aurora | SQLite is intentional for synthetic low-concurrency demo |
| EKS / ECS Fargate multi-service | Extra control plane / task cost; Compose on one EC2 is enough |
| ALB/NLB | CloudFront + single origin sufficient |
| OpenSearch / ElastiCache / MSK / Redshift | Not used by the app |
| SageMaker endpoints / GPU | No model hosting required; Bedrock on-demand |
| Bedrock Provisioned Throughput | Expensive reserved capacity; on-demand only |
| Secrets Manager for every value | Parameter Store Standard SecureString is enough |
| Multi-AZ | Single-node demo; availability not the goal |

## Cost guardrails in IAM / architecture

- Deploy role permissions boundary denies NAT, EKS, RDS, OpenSearch, ElastiCache, Redshift, MSK, SageMaker, provisioned Bedrock, large instance types
- Allowed EC2: `t4g.micro|small|medium` (+ small t3/t3a fallback)
- EBS capped at 30 GiB in CDK (default 20)
- Budgets alerts at $10 / $25 / $50 / $75 / $90 (email if configured)
- Application caps: max tool calls, run duration, concurrency, demo access gate

## Bedrock token budget

Start with the cheapest Amazon Nova-class model that passes golden flows.  
Record final model ID, region, and eval token estimates in `docs/AWS_ARCHITECTURE.md` after benchmarking.

## Cleanup

`make aws-destroy-demo CONFIRM_DESTROY=CloudiQSDemo` lists tagged resources then destroys the CDK stack.  
Verify leftover EIP/EBS/snapshots after destroy.
