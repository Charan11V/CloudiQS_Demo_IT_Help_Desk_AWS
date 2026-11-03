# Infrastructure — CloudiQS HELIO AWS demo

- `bootstrap/` — one-time IAM deploy role + permissions boundary (`create_deploy_role.py`)
- `cdk/` — AWS CDK app (`CloudiQSDemoStack`)
- Root `compose.aws.yaml` — production Compose on EC2
- Root `scripts/aws/` — push images, deploy via SSM, ops helpers
- Docs: `docs/AWS_ARCHITECTURE.md`, `AWS_COST_MODEL.md`, `AWS_DEPLOYMENT.md`, `AWS_DEMO_WALKTHROUGH.md`

Default region: **us-east-1**. No NAT / RDS / EKS.
