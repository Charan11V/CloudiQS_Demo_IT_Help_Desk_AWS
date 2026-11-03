#!/usr/bin/env python3
"""Enable HTTPS on the existing EC2 demo via Caddy + Let's Encrypt.

CloudFront CreateDistribution is blocked on this account until AWS verifies it.
This path uses <public-ip>.sslip.io (free DNS→IP) so ACME can issue a real cert
without buying a domain. When CloudFront is unblocked, prefer
scripts/aws/enable_https_cloudfront.py instead.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import boto3

ROOT = Path(__file__).resolve().parents[2]
REGION = "us-east-1"
STACK = "CloudiQSDemoStack"
SSM_PREFIX = "/cloudiqs-demo"
CADDYFILE_TEMPLATE = Path(__file__).resolve().parent / "Caddyfile.template"


def put_ssm(ssm, name: str, value: str, secure: bool = False) -> None:
    ssm.put_parameter(
        Name=name,
        Value=value,
        Type="SecureString" if secure else "String",
        Overwrite=True,
    )
    print("SSM put", name)


def ensure_https_ingress(ec2, group_id: str) -> None:
    try:
        ec2.authorize_security_group_ingress(
            GroupId=group_id,
            IpPermissions=[
                {
                    "IpProtocol": "tcp",
                    "FromPort": 443,
                    "ToPort": 443,
                    "IpRanges": [
                        {"CidrIp": "0.0.0.0/0", "Description": "HTTPS Caddy LetsEncrypt"}
                    ],
                    "Ipv6Ranges": [{"CidrIpv6": "::/0", "Description": "HTTPS Caddy IPv6"}],
                }
            ],
        )
        print("Opened TCP 443 on", group_id)
    except ec2.exceptions.ClientError as e:
        if "InvalidPermission.Duplicate" in str(e):
            print("TCP 443 already open on", group_id)
        else:
            raise


def main() -> int:
    s = boto3.Session(region_name=REGION)
    cfn = s.client("cloudformation")
    ec2 = s.client("ec2")
    ssm = s.client("ssm")
    s3 = s.client("s3")

    outs = {
        o["OutputKey"]: o["OutputValue"]
        for o in cfn.describe_stacks(StackName=STACK)["Stacks"][0].get("Outputs", [])
    }
    instance_id = outs["InstanceId"]
    bucket = outs["BackupBucketName"]
    ip = ec2.describe_instances(InstanceIds=[instance_id])["Reservations"][0]["Instances"][0][
        "PublicIpAddress"
    ]
    sg = ec2.describe_instances(InstanceIds=[instance_id])["Reservations"][0]["Instances"][0][
        "SecurityGroups"
    ][0]["GroupId"]
    host = f"{ip}.sslip.io"
    https_url = f"https://{host}"
    bridge_url = f"{https_url}/api-backend/internal/agentcore/tools"
    print("HTTPS host:", host)

    ensure_https_ingress(ec2, sg)

    # Upload compose + Caddyfile
    compose = (ROOT / "compose.aws.yaml").read_bytes()
    caddy = CADDYFILE_TEMPLATE.read_bytes()
    s3.put_object(Bucket=bucket, Key="deploy/compose.aws.yaml", Body=compose)
    s3.put_object(Bucket=bucket, Key="deploy/Caddyfile", Body=caddy)
    print("Uploaded compose + Caddyfile to S3")

    put_ssm(ssm, f"{SSM_PREFIX}/DEMO_HTTPS_URL", https_url)
    put_ssm(ssm, f"{SSM_PREFIX}/DEMO_URL", https_url)
    put_ssm(ssm, f"{SSM_PREFIX}/DEMO_HTTPS_HOST", host)
    put_ssm(ssm, f"{SSM_PREFIX}/TOOL_BRIDGE_PUBLIC_URL", bridge_url)
    put_ssm(ssm, f"{SSM_PREFIX}/HTTPS_MODE", "caddy-sslip")

    remote = f"""set -euo pipefail
BUCKET='{bucket}'
HOST='{host}'
BRIDGE='{bridge_url}'
HTTPS_URL='{https_url}'

. /opt/cloudiqs-demo/env.sh
export ECR_WEB_IMAGE="${{ECR_WEB_IMAGE:-${{ECR_WEB}}:latest}}"
export ECR_AGENT_IMAGE="${{ECR_AGENT_IMAGE:-${{ECR_AGENT}}:latest}}"
export ECR_MOCK_IMAGE="${{ECR_MOCK_IMAGE:-${{ECR_MOCK}}:latest}}"
if docker image inspect cloudiqs-demo-agent-api:local >/dev/null 2>&1; then export ECR_AGENT_IMAGE=cloudiqs-demo-agent-api:local; fi
if docker image inspect cloudiqs-demo-web:local >/dev/null 2>&1; then export ECR_WEB_IMAGE=cloudiqs-demo-web:local; fi
if docker image inspect cloudiqs-demo-mock-api:local >/dev/null 2>&1; then export ECR_MOCK_IMAGE=cloudiqs-demo-mock-api:local; fi
if docker image inspect bakery-api:local >/dev/null 2>&1; then export ECR_BAKERY_IMAGE=bakery-api:local; fi

aws s3 cp "s3://$BUCKET/deploy/compose.aws.yaml" /opt/cloudiqs-demo/compose/compose.aws.yaml
aws s3 cp "s3://$BUCKET/deploy/Caddyfile" /opt/cloudiqs-demo/compose/Caddyfile

ENVF=/opt/cloudiqs-demo/compose/.env.agentcore
umask 077
touch "$ENVF"
# Preserve existing keys; set HTTPS-related ones
set +e
. "$ENVF" 2>/dev/null
set -e
getp() {{ aws ssm get-parameter --region us-east-1 --name "$1" --with-decryption --query Parameter.Value --output text 2>/dev/null || true; }}
export DEMO_ACCESS_SECRET="$(getp {SSM_PREFIX}/DEMO_ACCESS_SECRET)"
export APP_SESSION_SIGNING_KEY="$(getp {SSM_PREFIX}/APP_SESSION_SIGNING_KEY)"
export OPENAI_API_KEY="$(getp {SSM_PREFIX}/OPENAI_API_KEY)"
export TOOL_BRIDGE_SECRET="$(getp {SSM_PREFIX}/TOOL_BRIDGE_SECRET)"
export AGENTCORE_RUNTIME_ARN="$(getp {SSM_PREFIX}/AGENTCORE_RUNTIME_ARN)"
export AGENTCORE_REGION="$(getp {SSM_PREFIX}/AGENTCORE_REGION)"
export AGENTCORE_ENABLED="$(getp {SSM_PREFIX}/AGENTCORE_ENABLED)"; export AGENTCORE_ENABLED="${{AGENTCORE_ENABLED:-1}}"
export MODEL_PROVIDER="$(getp {SSM_PREFIX}/MODEL_PROVIDER)"; export MODEL_PROVIDER="${{MODEL_PROVIDER:-openai_compatible}}"
export OPENAI_BASE_URL="$(getp {SSM_PREFIX}/OPENAI_BASE_URL)"; export OPENAI_BASE_URL="${{OPENAI_BASE_URL:-https://api.groq.com/openai/v1}}"
export OPENAI_MODEL_ID="$(getp {SSM_PREFIX}/OPENAI_MODEL_ID)"; export OPENAI_MODEL_ID="${{OPENAI_MODEL_ID:-openai/gpt-oss-20b}}"
export DEMO_HTTPS_HOST="$HOST"
export TOOL_BRIDGE_PUBLIC_URL="$BRIDGE"
export DEMO_GATE_ENABLED=1
export ORIGIN_VERIFY_TOKEN="${{ORIGIN_VERIFY_TOKEN:-}}"

cat > "$ENVF" <<EOF
ECR_WEB_IMAGE=${{ECR_WEB_IMAGE}}
ECR_AGENT_IMAGE=${{ECR_AGENT_IMAGE}}
ECR_MOCK_IMAGE=${{ECR_MOCK_IMAGE}}
ECR_BAKERY_IMAGE=${{ECR_BAKERY_IMAGE:-bakery-api:local}}
APP_SESSION_SIGNING_KEY=${{APP_SESSION_SIGNING_KEY}}
DEMO_ACCESS_SECRET=${{DEMO_ACCESS_SECRET}}
MODEL_PROVIDER=${{MODEL_PROVIDER}}
OPENAI_BASE_URL=${{OPENAI_BASE_URL}}
OPENAI_MODEL_ID=${{OPENAI_MODEL_ID}}
OPENAI_API_KEY=${{OPENAI_API_KEY}}
AGENTCORE_ENABLED=${{AGENTCORE_ENABLED}}
AGENTCORE_RUNTIME_ARN=${{AGENTCORE_RUNTIME_ARN}}
AGENTCORE_REGION=${{AGENTCORE_REGION:-ap-south-2}}
TOOL_BRIDGE_PUBLIC_URL=${{TOOL_BRIDGE_PUBLIC_URL}}
TOOL_BRIDGE_SECRET=${{TOOL_BRIDGE_SECRET}}
DEMO_HTTPS_HOST=${{DEMO_HTTPS_HOST}}
DEMO_GATE_ENABLED=1
ORIGIN_VERIFY_TOKEN=${{ORIGIN_VERIFY_TOKEN:-}}
AWS_REGION=us-east-1
EOF
chmod 600 "$ENVF"

cd /opt/cloudiqs-demo/compose
# Pull Caddy image then recreate public edge + agent-api (bridge URL)
docker pull caddy:2.9-alpine
docker compose -f compose.aws.yaml --env-file "$ENVF" up -d
# Force recreate edge path
docker compose -f compose.aws.yaml --env-file "$ENVF" up -d --no-deps --force-recreate web caddy agent-api
sleep 15
docker compose -f compose.aws.yaml --env-file "$ENVF" ps
echo '--- caddy logs ---'
docker logs compose-caddy-1 2>&1 | tail -40 || docker logs $(docker ps -qf name=caddy) 2>&1 | tail -40 || true
# Local health via caddy once cert ready
for i in $(seq 1 30); do
  if curl -sfk "https://127.0.0.1/api/health" -H "Host: $HOST" >/tmp/h.json 2>/dev/null; then
    cat /tmp/h.json; echo; break
  fi
  sleep 5
done
curl -sf "http://127.0.0.1/api/health" || true
echo
echo HTTPS_CADDY_OK host=$HOST url=$HTTPS_URL
"""

    resp = ssm.send_command(
        InstanceIds=[instance_id],
        DocumentName="AWS-RunShellScript",
        Parameters={"commands": [remote]},
        TimeoutSeconds=900,
        Comment="Enable Caddy Let's Encrypt HTTPS",
    )
    cid = resp["Command"]["CommandId"]
    print("SSM", cid)
    for _ in range(100):
        time.sleep(6)
        inv = ssm.get_command_invocation(CommandId=cid, InstanceId=instance_id)
        st = inv["Status"]
        if st in {"Success", "Failed", "Cancelled", "TimedOut"}:
            print(inv.get("StandardOutputContent", "")[-4000:])
            err = inv.get("StandardErrorContent") or ""
            if err:
                print("ERR", err[-2000:])
            if st != "Success":
                return 1
            break
    else:
        print("SSM timeout")
        return 1

    state = {
        "mode": "caddy-sslip",
        "https_url": https_url,
        "host": host,
        "bridge_url": bridge_url,
        "public_ip": ip,
        "instance_id": instance_id,
        "note": "CloudFront still blocked; switch to enable_https_cloudfront.py after AWS verifies account",
        "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    out_dir = ROOT / "deploy" / "https"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "state.json").write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")

    # External probe
    import urllib.request
    import ssl

    ctx = ssl.create_default_context()
    try:
        req = urllib.request.Request(f"{https_url}/api/health", headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
            body = resp.read().decode()[:300]
            print("EXTERNAL_HTTPS", resp.status, body)
    except Exception as e:
        print("EXTERNAL_HTTPS_PROBE_FAILED", e)
        print("Cert may still be provisioning — retry in 1–2 minutes:", https_url)

    print(json.dumps(state, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
