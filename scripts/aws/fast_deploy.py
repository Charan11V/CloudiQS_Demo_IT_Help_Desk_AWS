#!/usr/bin/env python3
"""Cost-neutral fast deploy: build on the existing Graviton EC2 (native ARM), no QEMU.

Usage:
  python scripts/aws/fast_deploy.py --service web
  python scripts/aws/fast_deploy.py --service agent
  python scripts/aws/fast_deploy.py --service bakery
  python scripts/aws/fast_deploy.py --service all

Flow: tar source → S3 (existing backup bucket) → SSM docker build on instance →
compose recreate that service using a *local* image tag (no ECR push required).
Same EC2 / no new AWS services → same monthly cost profile.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys
import tarfile
import time
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

ROOT = Path(__file__).resolve().parents[2]
REGION = os.environ.get("AWS_REGION", "us-east-1")
PROFILE = os.environ.get("AWS_PROFILE", "cloudiqs-demo-deployer")

SERVICES = {
    "web": {
        "context": ROOT / "apps" / "web",
        "dockerfile": "Dockerfile",
        "image": "cloudiqs-demo-web:local",
        "compose_service": "web",
        "build_args": {
            "AGENT_API_URL": "http://agent-api:8001",
            "BAKERY_API_URL": "http://bakery-api:8000",
        },
        "exclude": {"node_modules", ".next", ".git"},
    },
    "agent": {
        "context": ROOT / "services" / "agent_api",
        "dockerfile": "Dockerfile",
        "image": "cloudiqs-demo-agent-api:local",
        "compose_service": "agent-api",
        "build_args": {},
        "exclude": {".git", "__pycache__", ".venv", "venv"},
    },
    "mock": {
        "context": ROOT / "cloudiqs_enterprise_demo_pack",
        "dockerfile": "Dockerfile",
        "image": "cloudiqs-demo-mock-api:local",
        "compose_service": "enterprise-mock-api",
        "build_args": {},
        "exclude": {".git", "__pycache__"},
    },
    "bakery": {
        "context": ROOT / "services" / "bakery_api",
        "dockerfile": "Dockerfile",
        "image": "bakery-api:local",
        "compose_service": "bakery-api",
        "build_args": {},
        "exclude": {".git", "__pycache__", ".venv"},
        "needs_specs": True,
    },
}


def session() -> boto3.Session:
    if os.environ.get("AWS_ACCESS_KEY_ID"):
        return boto3.Session(region_name=REGION)
    try:
        return boto3.Session(profile_name=PROFILE, region_name=REGION)
    except Exception:
        return boto3.Session(region_name=REGION)


def stack_outputs(cfn) -> dict:
    stacks = cfn.describe_stacks(StackName="CloudiQSDemoStack")["Stacks"]
    return {o["OutputKey"]: o["OutputValue"] for o in stacks[0].get("Outputs", [])}


def get_param(ssm, name: str, default: str = "") -> str:
    try:
        return ssm.get_parameter(Name=name, WithDecryption=True)["Parameter"]["Value"]
    except ClientError:
        return default


def make_tarball(context: Path, exclude: set[str]) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for path in context.rglob("*"):
            if not path.is_file():
                continue
            rel = path.relative_to(context)
            if any(part in exclude for part in rel.parts):
                continue
            tar.add(path, arcname=str(rel).replace("\\", "/"))
    return buf.getvalue()


def wait_cmd(ssm, cmd_id: str, instance_id: str, timeout_s: int = 1800) -> int:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        time.sleep(8)
        inv = ssm.get_command_invocation(CommandId=cmd_id, InstanceId=instance_id)
        st = inv["Status"]
        if st in ("Success", "Cancelled", "TimedOut", "Failed"):
            out = inv.get("StandardOutputContent") or ""
            err = inv.get("StandardErrorContent") or ""
            # Avoid Windows charmap crashes on fancy build glyphs
            sys.stdout.buffer.write(out.encode("utf-8", errors="replace")[-8000:])
            sys.stdout.buffer.write(b"\n")
            if err:
                sys.stderr.buffer.write(err.encode("utf-8", errors="replace")[-4000:])
                sys.stderr.buffer.write(b"\n")
            return 0 if st == "Success" else 1
    print("SSM wait timeout", file=sys.stderr)
    return 1


def env_export_snippet() -> list[str]:
    """Preserve secrets from running containers / SSM-backed env on the instance."""
    return [
        "set -euo pipefail",
        "cd /opt/cloudiqs-demo/compose",
        "set +e; source /opt/cloudiqs-demo/env.sh 2>/dev/null; set -e",
        "REGISTRY=$(aws sts get-caller-identity --query Account --output text).dkr.ecr.${AWS_REGION:-us-east-1}.amazonaws.com",
        # Prefer local fast-deploy tags when present; else fall back to ECR :latest
        "export ECR_WEB_IMAGE=${ECR_WEB_IMAGE:-cloudiqs-demo-web:local}",
        "docker image inspect \"$ECR_WEB_IMAGE\" >/dev/null 2>&1 || export ECR_WEB_IMAGE=$REGISTRY/cloudiqs-demo-web:latest",
        "export ECR_AGENT_IMAGE=${ECR_AGENT_IMAGE:-cloudiqs-demo-agent-api:local}",
        "docker image inspect \"$ECR_AGENT_IMAGE\" >/dev/null 2>&1 || export ECR_AGENT_IMAGE=$REGISTRY/cloudiqs-demo-agent-api:latest",
        "export ECR_MOCK_IMAGE=${ECR_MOCK_IMAGE:-cloudiqs-demo-mock-api:local}",
        "docker image inspect \"$ECR_MOCK_IMAGE\" >/dev/null 2>&1 || export ECR_MOCK_IMAGE=$REGISTRY/cloudiqs-demo-mock-api:latest",
        "export ECR_BAKERY_IMAGE=${ECR_BAKERY_IMAGE:-bakery-api:local}",
        "WEB_CID=$(docker ps -qf name=compose-web | head -1 || true)",
        "AGENT_CID=$(docker ps -qf name=agent-api | head -1 || true)",
        'if [ -n "$WEB_CID" ]; then',
        "  while IFS= read -r line; do",
        "    case \"$line\" in",
        "      DEMO_ACCESS_SECRET=*|DEMO_GATE_ENABLED=*|ORIGIN_VERIFY_TOKEN=*|NEXT_PUBLIC_RUNTIME_BADGE=*|AWS_REGION=*|APP_SESSION_SIGNING_KEY=*) export \"$line\" ;;",
        "    esac",
        "  done < <(docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' \"$WEB_CID\")",
        "fi",
        'if [ -n "$AGENT_CID" ]; then',
        "  while IFS= read -r line; do",
        "    case \"$line\" in",
        "      MODEL_PROVIDER=*|BEDROCK_MODEL_ID=*|AWS_BEARER_TOKEN_BEDROCK=*|OPENAI_API_KEY=*|GROQ_API_KEY=*|OPENAI_BASE_URL=*|OPENAI_MODEL_ID=*|APP_SESSION_SIGNING_KEY=*|DEMO_NOW=*|LOG_LEVEL=*|AGENTCORE_ENABLED=*|AGENTCORE_RUNTIME_ARN=*|AGENTCORE_REGION=*|AGENTCORE_QUALIFIER=*|TOOL_BRIDGE_PUBLIC_URL=*|TOOL_BRIDGE_SECRET=*) export \"$line\" ;;",
        "    esac",
        "  done < <(docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' \"$AGENT_CID\")",
        "fi",
        # Prefer dedicated AgentCore env file written by patch_ec2_agentcore_env.py
        'if [ -f /opt/cloudiqs-demo/compose/.env.agentcore ]; then set -a; . /opt/cloudiqs-demo/compose/.env.agentcore; set +a; fi',
        # Fall back to SSM for AgentCore wiring if still unset
        'SSM_P=/cloudiqs-demo',
        'getp(){ aws ssm get-parameter --region "${AWS_REGION:-us-east-1}" --name "$1" --with-decryption --query Parameter.Value --output text 2>/dev/null || true; }',
        'export AGENTCORE_ENABLED=${AGENTCORE_ENABLED:-$(getp $SSM_P/AGENTCORE_ENABLED)}',
        'export AGENTCORE_ENABLED=${AGENTCORE_ENABLED:-1}',
        'export AGENTCORE_RUNTIME_ARN=${AGENTCORE_RUNTIME_ARN:-$(getp $SSM_P/AGENTCORE_RUNTIME_ARN)}',
        'export AGENTCORE_REGION=${AGENTCORE_REGION:-$(getp $SSM_P/AGENTCORE_REGION)}',
        'export AGENTCORE_REGION=${AGENTCORE_REGION:-ap-south-2}',
        'export TOOL_BRIDGE_PUBLIC_URL=${TOOL_BRIDGE_PUBLIC_URL:-$(getp $SSM_P/TOOL_BRIDGE_PUBLIC_URL)}',
        'export TOOL_BRIDGE_SECRET=${TOOL_BRIDGE_SECRET:-$(getp $SSM_P/TOOL_BRIDGE_SECRET)}',
        "export DEMO_GATE_ENABLED=${DEMO_GATE_ENABLED:-1}",
        "export MODEL_PROVIDER=${MODEL_PROVIDER:-openai_compatible}",
        "export BEDROCK_MODEL_ID=${BEDROCK_MODEL_ID:-amazon.nova-lite-v1:0}",
        "export OPENAI_BASE_URL=${OPENAI_BASE_URL:-https://api.groq.com/openai/v1}",
        "export OPENAI_MODEL_ID=${OPENAI_MODEL_ID:-openai/gpt-oss-20b}",
        "export NEXT_PUBLIC_RUNTIME_BADGE=${NEXT_PUBLIC_RUNTIME_BADGE:-AWS}",
    ]


def build_remote_script(service: str, bucket: str, cfg: dict) -> str:
    image = cfg["image"]
    compose_svc = cfg["compose_service"]
    build_args = " ".join(f"--build-arg {k}={v}" for k, v in cfg.get("build_args", {}).items())
    key = f"deploys/{service}-src.tgz"
    lines = [
        "set -euo pipefail",
        f"BUCKET={bucket}",
        f"SVC={service}",
        f"IMAGE={image}",
        f"COMPOSE_SVC={compose_svc}",
        "mkdir -p /opt/cloudiqs-demo/build/$SVC /opt/cloudiqs-demo/compose /opt/cloudiqs-demo/specs",
        f"aws s3 cp s3://$BUCKET/{key} /opt/cloudiqs-demo/build/$SVC/src.tgz",
        "rm -rf /opt/cloudiqs-demo/build/$SVC/src && mkdir -p /opt/cloudiqs-demo/build/$SVC/src",
        "tar -xzf /opt/cloudiqs-demo/build/$SVC/src.tgz -C /opt/cloudiqs-demo/build/$SVC/src",
        f"aws s3 cp s3://$BUCKET/deploy/compose.aws.yaml /opt/cloudiqs-demo/compose/compose.aws.yaml",
    ]
    if cfg.get("needs_specs"):
        lines += [
            f"aws s3 cp s3://$BUCKET/deploys/specs.tgz /tmp/specs.tgz",
            "rm -rf /opt/cloudiqs-demo/specs/*",
            "tar -xzf /tmp/specs.tgz -C /opt/cloudiqs-demo/specs",
        ]
    lines += [
        f"docker build {build_args} -f /opt/cloudiqs-demo/build/$SVC/src/{cfg['dockerfile']} "
        f"-t $IMAGE /opt/cloudiqs-demo/build/$SVC/src",
    ]
    lines += env_export_snippet()
    # Force this service's image env
    if service == "web":
        lines.append(f"export ECR_WEB_IMAGE={image}")
    elif service == "agent":
        lines.append(f"export ECR_AGENT_IMAGE={image}")
    elif service == "mock":
        lines.append(f"export ECR_MOCK_IMAGE={image}")
    elif service == "bakery":
        lines.append(f"export ECR_BAKERY_IMAGE={image}")
        lines.append("docker compose -f compose.aws.yaml up -d bakery-postgres")
        lines.append("docker compose -f compose.aws.yaml up -d --no-deps --force-recreate bakery-api")
        lines.append("sleep 12")
        lines.append(
            "docker compose -f compose.aws.yaml exec -T bakery-api "
            "python -c \"import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/health').read().decode())\""
        )
        lines.append("echo FAST_DEPLOY_OK bakery")
        return "\n".join(lines) + "\n"

    lines += [
        f"docker compose -f compose.aws.yaml up -d --no-deps --force-recreate $COMPOSE_SVC",
        "sleep 8",
        "curl -sf http://127.0.0.1/api/health || true",
        "echo",
        f"echo FAST_DEPLOY_OK {service}",
    ]
    return "\n".join(lines) + "\n"


def deploy_one(s, outs: dict, service: str) -> int:
    cfg = SERVICES[service]
    bucket = outs["BackupBucketName"]
    iid = outs["InstanceId"]
    s3 = s.client("s3")
    ssm = s.client("ssm")

    print(f"[fast] packing {service} from {cfg['context']} …")
    blob = make_tarball(cfg["context"], cfg.get("exclude") or set())
    key = f"deploys/{service}-src.tgz"
    s3.put_object(Bucket=bucket, Key=key, Body=blob)
    print(f"[fast] uploaded s3://{bucket}/{key} ({len(blob)} bytes)")

    # Always refresh compose
    s3.put_object(
        Bucket=bucket,
        Key="deploy/compose.aws.yaml",
        Body=(ROOT / "compose.aws.yaml").read_bytes(),
    )

    if cfg.get("needs_specs"):
        specs_blob = make_tarball(ROOT / "specs", {".git"})
        s3.put_object(Bucket=bucket, Key="deploys/specs.tgz", Body=specs_blob)
        print(f"[fast] uploaded specs ({len(specs_blob)} bytes)")

    script = build_remote_script(service, bucket, cfg)
    print(f"[fast] SSM native build+recreate {service} on {iid} …")
    resp = ssm.send_command(
        InstanceIds=[iid],
        DocumentName="AWS-RunShellScript",
        Parameters={"commands": [script]},
        TimeoutSeconds=1800,
    )
    cmd_id = resp["Command"]["CommandId"]
    print("SSM CommandId:", cmd_id)
    return wait_cmd(ssm, cmd_id, iid)


def main() -> int:
    ap = argparse.ArgumentParser(description="Fast native-on-EC2 deploy (no QEMU)")
    ap.add_argument(
        "--service",
        required=True,
        choices=[*SERVICES.keys(), "all"],
        help="Service to rebuild on the Graviton host",
    )
    args = ap.parse_args()

    s = session()
    cfn = s.client("cloudformation")
    outs = stack_outputs(cfn)
    if not outs.get("InstanceId") or not outs.get("BackupBucketName"):
        print("Missing InstanceId/BackupBucketName stack outputs", file=sys.stderr)
        return 1

    order = ["mock", "agent", "bakery", "web"] if args.service == "all" else [args.service]
    # Prefer bakery before web so guided proxy target is healthy after web recreate
    if args.service == "all":
        order = ["bakery", "agent", "web"]

    rc = 0
    for svc in order:
        code = deploy_one(s, outs, svc)
        if code != 0:
            print(f"[fast] FAILED {svc}", file=sys.stderr)
            return code
        print(f"[fast] OK {svc}")
    print(json.dumps({"ok": True, "services": order, "url_hint": "http://<ec2-public-dns>/"}))
    return rc


if __name__ == "__main__":
    sys.exit(main())
