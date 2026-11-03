# AWS Deployment Runbook — CloudiQS HELIO Demo

Never paste long-lived `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` into Cursor, `.env`, or git.

## 0. Prerequisites

- AWS CLI **≥ 2.32** (`aws login`) / **≥ 2.35** (`aws configure agent-toolkit`)
- Docker + buildx
- Node 20+, Python 3.11+
- Region: **us-east-1**

## 1. Temporary authentication

```powershell
$env:Path = "C:\Program Files\Amazon\AWSCLIV2;$env:USERPROFILE\.local\bin;$env:Path"
aws login
aws sts get-caller-identity
```

If the session expires later: run `aws login` again. Do not fall back to permanent keys.

## 2. Bootstrap deploy role (once)

```powershell
python infra/bootstrap/create_deploy_role.py
aws sts get-caller-identity --profile cloudiqs-demo-deployer
```

Expect ARN containing `CloudiQSDemoDeployRole`.

```powershell
$env:AWS_PROFILE = "cloudiqs-demo-deployer"
```

## 3. Rotate SSM secrets (before public use)

```powershell
# Generate locally; put as SecureString — do not commit values
$sessionKey = -join ((48..57 + 65..90 + 97..122) | Get-Random -Count 48 | ForEach-Object {[char]$_})
$demoSecret = -join ((48..57 + 65..90 + 97..122) | Get-Random -Count 24 | ForEach-Object {[char]$_})
aws ssm put-parameter --name /cloudiqs-demo/APP_SESSION_SIGNING_KEY --type SecureString --value $sessionKey --overwrite
aws ssm put-parameter --name /cloudiqs-demo/DEMO_ACCESS_SECRET --type SecureString --value $demoSecret --overwrite
# Store $demoSecret in your password manager for the interview gate
```

Optional: `CLOUDIQS_BUDGET_EMAIL=you@example.com` for budget notifications.

## 4. CDK deploy (infrastructure)

```powershell
cd infra/cdk
npm install
npx cdk bootstrap aws://$Account/us-east-1
npx cdk diff
npx cdk deploy --all
cd ../..
```

Record outputs: `CloudFrontUrl`, `InstanceId`, ECR URIs.

## 5. Build & push ARM64 images

```powershell
.\scripts\aws\push_images.ps1 -Profile cloudiqs-demo-deployer -Tag latest
```

## 6. Configure host & start Compose (SSM)

```powershell
make aws-deploy
# or: python scripts/aws/ops.py ssm-run -- ...
```

This pulls images, writes env from SSM, starts `compose.aws.yaml`, runs health checks.

## 7. Verify

```powershell
make aws-health
make smoke-bedrock   # after Bedrock model access enabled
# Browser: CloudFront URL → demo gate → Asha persona
```

## 8. Day-2 operations

| Command | Purpose |
|---|---|
| `make aws-status` | Stack outputs + instance state |
| `make aws-logs` | Tail via SSM / CW |
| `make aws-health` | Container + `/health` + `/health/model` |
| `make aws-backup-demo` | SQLite → S3 |
| `make aws-restore-demo` | Restore from S3 (destructive) |
| `make aws-reset-demo` | Canonical seed reset via SSM |
| `make aws-stop-demo` / `make aws-start-demo` | Cost control |
| `make aws-cost-status` | Burn estimate + CE/Budgets (lagged) |
| `make aws-destroy-demo CONFIRM_DESTROY=CloudiQSDemo` | Tear down |

## 9. Rollback

- Keep previous ECR tag (e.g. `prev`)
- `make aws-backup-demo` before deploy
- Redeploy previous image tags via SSM compose override

## 10. Bedrock auth (current console = API keys)

**Full guide:** [`docs/BEDROCK_AUTH.md`](./BEDROCK_AUTH.md)

The Bedrock console now onboards via **API keys** ([quickstart](https://docs.aws.amazon.com/bedrock/latest/userguide/getting-started.html)). The old Model access page is retired.

For **this** app (boto3 Converse / Strands), not Mantle OpenAI:

1. Console **us-east-1** → Bedrock → **API keys** → short-term key.
2. Wizard: **Generate text → Converse**.
3. Set `AWS_BEARER_TOKEN_BEDROCK` on `agent-api` (compose supports it). Requires **boto3 ≥ 1.39**.
4. Keep `MODEL_PROVIDER=bedrock`, `BEDROCK_MODEL_ID=amazon.nova-lite-v1:0`.
5. **Do not** use `OPENAI_API_KEY` + `bedrock-mantle` + `gpt-oss-*` for HELIO.
6. Long-term on EC2: prefer IAM instance role (`CloudiQSDemoRuntimeRole`) and leave the bearer env empty once Invoke works.

Verify: `GET /api-backend/health/model` → `"ok": true`, `"verified_live": true`.

No provisioned throughput. CloudFront/HTTPS is optional polish; HTTP EC2 origin is the supported demo path until HTTPS is enabled (cookies must omit `Secure` on HTTP).

## Troubleshooting

- **NoCredentials:** `aws login`
- **Cannot assume deployer:** re-run bootstrap; check ExternalId `CloudiQSDemo`
- **SSM offline:** wait for instance userdata; check instance profile
- **Origin 403:** CloudFront header / `ORIGIN_VERIFY_TOKEN` mismatch (only if CloudFront is enabled)
- **Converse Operation not allowed / AccessDenied:** see §10 / `docs/BEDROCK_AUTH.md` (API key region, boto3≥1.39, wrong Mantle/OPENAI_API_KEY path, IAM/SCP)
- **Blank UI after gate/login on HTTP:** ensure demo-access cookie is set without `Secure` (already in `apps/web/app/api/demo-access/route.ts`)
