# AWS Architecture — CloudiQS HELIO Demo

Independent CloudiQS / Agentic Bakery-**inspired** prototype with synthetic enterprise data.  
Not CloudiQS proprietary software.

## CURRENT IMPLEMENTED DEMO

```
Internet
    │
    ▼
EC2 t4g.small (Amazon Linux 2023 ARM, public subnet)  ← HTTP :80 (CloudFront/HTTPS deferred)
    │  Docker Compose (helio network)
    ├─ web (Next.js)             published :80
    ├─ agent-api (FastAPI)       private
    ├─ enterprise-mock-api       private + SQLite
    ├─ bakery-api (guided)       private
    └─ bakery-postgres           private volume (persists across recreate; seed-if-empty)
         │
         ├─ EBS gp3 ~20 GiB  (SQLite + specs)
         ├─ IAM instance role → Bedrock, SSM, ECR pull, CW, S3 backups
         ├─ CW alarm CPU→SNS (notify only; no auto scale-out)
         └─ SSM Session Manager (no SSH)
```

Fast deploy: `scripts/aws/fast_deploy.py` builds **on the instance** (native ARM) via S3+SSM — same cost profile as QEMU-less iteration.

CloudFront + origin-verify header remain in CDK as optional polish; they are **not** required for the live hiring demo URL.

### Services actually used

| AWS service | Role in demo |
|---|---|
| VPC + IGW + 1 public subnet | Networking (**no NAT**) |
| EC2 Graviton | Single compose host (public HTTP demo URL) |
| EBS gp3 | Persist `runtime.sqlite` + `app.sqlite` |
| ECR | `cloudiqs-demo-{web,agent-api,mock-api}` |
| CloudFront | **Deferred** — optional HTTPS polish, not on the live path |
| IAM roles | Deployer + Runtime (no app access keys) |
| SSM Parameter Store | Config / secrets (Standard) |
| SSM Session Manager | Admin / deploy / reset |
| S3 | Private backups + eval artifacts (14d lifecycle) |
| CloudWatch Logs + Dashboard | Container/instance signals |
| AWS Budgets | Spend alerts |
| Amazon Bedrock | Live agent mode (requires account model access) |

### Security boundaries

1. Public visitor → **demo access gate** (HttpOnly cookie, server-side secret) → persona chooser → session cookie  
2. `enterprise-mock-api` never published to host network  
3. Tenant/role from server session only — never from chat  
4. Approvals / policy enforced in backend  
5. No SSH (port 22 closed)  
6. No long-lived AWS keys in repo, images, or app env  

### Credential model

```
Human (aws login temporary session)
  → assume CloudiQSDemoDeployRole (profile cloudiqs-demo-deployer)
  → CDK / CLI / scripts

EC2 instance profile CloudiQSDemoRuntimeRole
  → Bedrock InvokeModel
  → SSM GetParameter
  → ECR pull / CloudWatch / S3 backups
```

Cursor → AWS MCP (SigV4) → IAM → AWS APIs → CloudTrail (default trail).

## FUTURE PRODUCTION ARCHITECTURE (not implemented)

- Cognito / OIDC enterprise IdP  
- Private subnets + tighter CloudFront origin controls  
- Managed DB if concurrency warrants  
- Multi-AZ / autoscaling only with measured demand  
- Optional AgentCore Runtime **only** if it preserves tool/policy boundaries without unsafe mock exposure  

## AgentCore status

**Not implemented** in the baseline. Strands + Bedrock on EC2 is the real path.  
Re-evaluate only after golden AWS smoke tests pass and incremental cost stays near-zero.

## Limitations

- Single AZ / single instance  
- SQLite (not multi-writer)  
- Demo personas, not production identity  
- Public IPv4 charge while instance exists  
- CloudFront→IP origin may need refresh if instance is replaced  
