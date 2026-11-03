#!/usr/bin/env python3
"""Enable HTTPS for the HELIO demo via CloudFront (*.cloudfront.net).

No custom domain / ACM needed. Origin remains the existing EC2 HTTP :80.
Idempotent: reuses a distribution tagged Project=CloudiQSDemo if present.

Also:
  - stores ORIGIN_VERIFY_TOKEN + HTTPS Demo URL in SSM
  - updates TOOL_BRIDGE_PUBLIC_URL to https://<cf>/api-backend/internal/agentcore/tools
  - patches EC2 web + agent-api env (ORIGIN_VERIFY_TOKEN, bridge URL)
"""
from __future__ import annotations

import json
import secrets
import sys
import time
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

REGION = "us-east-1"
STACK = "CloudiQSDemoStack"
SSM_PREFIX = "/cloudiqs-demo"
COMMENT = "CloudiQS HELIO demo HTTPS front door"
CALLER_REF_PREFIX = "cloudiqs-demo-https-"


def session():
    return boto3.Session(region_name=REGION)


def stack_outputs(cfn) -> dict:
    outs = cfn.describe_stacks(StackName=STACK)["Stacks"][0].get("Outputs", [])
    return {o["OutputKey"]: o["OutputValue"] for o in outs}


def put_ssm(ssm, name: str, value: str, secure: bool = False) -> None:
    ssm.put_parameter(
        Name=name,
        Value=value,
        Type="SecureString" if secure else "String",
        Overwrite=True,
    )
    print(f"SSM put {name}")


def find_existing_distribution(cf) -> dict | None:
    marker = None
    while True:
        kwargs = {"MaxItems": "100"}
        if marker:
            kwargs["Marker"] = marker
        resp = cf.list_distributions(**kwargs)
        items = (resp.get("DistributionList") or {}).get("Items") or []
        for d in items:
            if d.get("Comment") == COMMENT or (d.get("Comment") or "").startswith("CloudiQS"):
                return d
            # Match our EC2 origin
            origins = (d.get("Origins") or {}).get("Items") or []
            for o in origins:
                if "ec2-" in (o.get("DomainName") or "") and "compute-1.amazonaws.com" in (
                    o.get("DomainName") or ""
                ):
                    return d
        if not (resp.get("DistributionList") or {}).get("IsTruncated"):
            break
        marker = resp["DistributionList"].get("NextMarker")
    return None


def create_distribution(cf, origin_dns: str, origin_token: str) -> dict:
    caller = CALLER_REF_PREFIX + secrets.token_hex(8)
    config = {
        "CallerReference": caller,
        "Comment": COMMENT,
        "Enabled": True,
        "PriceClass": "PriceClass_100",
        "HttpVersion": "http2and3",
        "IsIPV6Enabled": True,
        "Origins": {
            "Quantity": 1,
            "Items": [
                {
                    "Id": "helio-ec2-origin",
                    "DomainName": origin_dns,
                    "CustomOriginConfig": {
                        "HTTPPort": 80,
                        "HTTPSPort": 443,
                        "OriginProtocolPolicy": "http-only",
                        "OriginSslProtocols": {"Quantity": 1, "Items": ["TLSv1.2"]},
                        "OriginReadTimeout": 60,
                        "OriginKeepaliveTimeout": 5,
                    },
                    "CustomHeaders": {
                        "Quantity": 1,
                        "Items": [
                            {
                                "HeaderName": "X-CloudiQS-Origin-Verify",
                                "HeaderValue": origin_token,
                            }
                        ],
                    },
                    "ConnectionAttempts": 3,
                    "ConnectionTimeout": 10,
                    "OriginShield": {"Enabled": False},
                }
            ],
        },
        "DefaultCacheBehavior": {
            "TargetOriginId": "helio-ec2-origin",
            "ViewerProtocolPolicy": "redirect-to-https",
            "AllowedMethods": {
                "Quantity": 7,
                "Items": ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"],
                "CachedMethods": {"Quantity": 2, "Items": ["GET", "HEAD"]},
            },
            # CachingDisabled managed policy — demo is dynamic (sessions, SSE/poll)
            "CachePolicyId": "4135ea2d-6df8-44a3-9df3-4b5a84be39ad",
            # AllViewerExceptHostHeader — forward cookies/auth to origin
            "OriginRequestPolicyId": "b689b0a8-53d0-40ab-baf2-68738e2966ac",
            "Compress": True,
            "SmoothStreaming": False,
            "FieldLevelEncryptionId": "",
            "TrustedSigners": {"Enabled": False, "Quantity": 0},
            "TrustedKeyGroups": {"Enabled": False, "Quantity": 0},
            "LambdaFunctionAssociations": {"Quantity": 0},
            "FunctionAssociations": {"Quantity": 0},
        },
        "CustomErrorResponses": {"Quantity": 0},
        "Restrictions": {
            "GeoRestriction": {"RestrictionType": "none", "Quantity": 0}
        },
        "ViewerCertificate": {
            "CloudFrontDefaultCertificate": True,
            "MinimumProtocolVersion": "TLSv1.2_2021",
        },
    }
    print("Creating CloudFront distribution (may take several minutes)…")
    resp = cf.create_distribution(DistributionConfig=config)
    return resp["Distribution"]


def wait_deployed(cf, dist_id: str, timeout: int = 1800) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        d = cf.get_distribution(Id=dist_id)["Distribution"]
        status = d.get("Status")
        print(f"  status={status}")
        if status == "Deployed":
            return d
        time.sleep(20)
    raise TimeoutError(f"Distribution {dist_id} not Deployed within {timeout}s")


def patch_ec2(ssm_client, instance_id: str, origin_token: str, https_url: str, bridge_url: str) -> int:
    remote = f"""set -euo pipefail
ENVF=/opt/cloudiqs-demo/compose/.env.agentcore
BASE=/opt/cloudiqs-demo/env.sh
ORIGIN_TOKEN='{origin_token}'
HTTPS_URL='{https_url}'
BRIDGE_URL='{bridge_url}'

# Persist into bootstrap env
if [ -f "$BASE" ]; then
  grep -q '^export ORIGIN_VERIFY_TOKEN=' "$BASE" \
    && sed -i "s|^export ORIGIN_VERIFY_TOKEN=.*|export ORIGIN_VERIFY_TOKEN=$ORIGIN_TOKEN|" "$BASE" \
    || echo "export ORIGIN_VERIFY_TOKEN=$ORIGIN_TOKEN" >> "$BASE"
  grep -q '^export DEMO_HTTPS_URL=' "$BASE" \
    && sed -i "s|^export DEMO_HTTPS_URL=.*|export DEMO_HTTPS_URL=$HTTPS_URL|" "$BASE" \
    || echo "export DEMO_HTTPS_URL=$HTTPS_URL" >> "$BASE"
fi

# Merge into compose env file used by agent-api / web
umask 077
touch "$ENVF"
grep -q '^ORIGIN_VERIFY_TOKEN=' "$ENVF" \
  && sed -i "s|^ORIGIN_VERIFY_TOKEN=.*|ORIGIN_VERIFY_TOKEN=$ORIGIN_TOKEN|" "$ENVF" \
  || echo "ORIGIN_VERIFY_TOKEN=$ORIGIN_TOKEN" >> "$ENVF"
grep -q '^TOOL_BRIDGE_PUBLIC_URL=' "$ENVF" \
  && sed -i "s|^TOOL_BRIDGE_PUBLIC_URL=.*|TOOL_BRIDGE_PUBLIC_URL=$BRIDGE_URL|" "$ENVF" \
  || echo "TOOL_BRIDGE_PUBLIC_URL=$BRIDGE_URL" >> "$ENVF"
grep -q '^AGENTCORE_ENABLED=' "$ENVF" || echo "AGENTCORE_ENABLED=1" >> "$ENVF"

# Ensure image tags resolve
. /opt/cloudiqs-demo/env.sh
export ECR_WEB_IMAGE="${{ECR_WEB_IMAGE:-${{ECR_WEB}}:latest}}"
export ECR_AGENT_IMAGE="${{ECR_AGENT_IMAGE:-${{ECR_AGENT}}:latest}}"
export ECR_MOCK_IMAGE="${{ECR_MOCK_IMAGE:-${{ECR_MOCK}}:latest}}"
if docker image inspect cloudiqs-demo-agent-api:local >/dev/null 2>&1; then export ECR_AGENT_IMAGE=cloudiqs-demo-agent-api:local; fi
if docker image inspect cloudiqs-demo-web:local >/dev/null 2>&1; then export ECR_WEB_IMAGE=cloudiqs-demo-web:local; fi
if docker image inspect cloudiqs-demo-mock-api:local >/dev/null 2>&1; then export ECR_MOCK_IMAGE=cloudiqs-demo-mock-api:local; fi
if docker image inspect bakery-api:local >/dev/null 2>&1; then export ECR_BAKERY_IMAGE=bakery-api:local; fi

# Pull secrets already in ENVF / SSM for recreate
set -a
. "$ENVF"
set +a
export ORIGIN_VERIFY_TOKEN="$ORIGIN_TOKEN"
export TOOL_BRIDGE_PUBLIC_URL="$BRIDGE_URL"
export DEMO_GATE_ENABLED=1

cd /opt/cloudiqs-demo/compose
# Recreate web (needs ORIGIN_VERIFY) and agent-api (bridge URL)
docker compose -f compose.aws.yaml --env-file "$ENVF" up -d --no-deps --force-recreate web agent-api
sleep 8
curl -sf -H "X-CloudiQS-Origin-Verify: $ORIGIN_TOKEN" http://127.0.0.1/api/health || true
echo HTTPS_PATCH_OK
"""
    resp = ssm_client.send_command(
        InstanceIds=[instance_id],
        DocumentName="AWS-RunShellScript",
        Parameters={"commands": [remote]},
        Comment="Enable HTTPS CloudFront origin verify + bridge URL",
        TimeoutSeconds=600,
    )
    cid = resp["Command"]["CommandId"]
    print("SSM", cid)
    for _ in range(60):
        time.sleep(5)
        inv = ssm_client.get_command_invocation(CommandId=cid, InstanceId=instance_id)
        st = inv["Status"]
        if st in {"Success", "Failed", "Cancelled", "TimedOut"}:
            print(inv.get("StandardOutputContent", "")[-2000:])
            err = inv.get("StandardErrorContent") or ""
            if err:
                print(err[-1500:])
            return 0 if st == "Success" else 1
    print("SSM timeout")
    return 1


def main() -> int:
    s = session()
    cfn = s.client("cloudformation")
    cf = s.client("cloudfront")
    ssm = s.client("ssm")
    outs = stack_outputs(cfn)
    origin_dns = outs["InstancePublicDns"]
    instance_id = outs["InstanceId"]
    print("Origin EC2 DNS:", origin_dns)

    # Stable origin token: reuse SSM if present, else generate
    token_name = f"{SSM_PREFIX}/ORIGIN_VERIFY_TOKEN"
    try:
        origin_token = ssm.get_parameter(Name=token_name, WithDecryption=True)["Parameter"]["Value"]
        print("Reusing existing ORIGIN_VERIFY_TOKEN")
    except ClientError:
        origin_token = "cf-" + secrets.token_urlsafe(24)
        put_ssm(ssm, token_name, origin_token, secure=True)

    existing = find_existing_distribution(cf)
    if existing:
        dist_id = existing["Id"]
        domain = existing["DomainName"]
        print(f"Reusing distribution {dist_id} → https://{domain}")
        # Ensure Deployed
        d = cf.get_distribution(Id=dist_id)["Distribution"]
        if d.get("Status") != "Deployed":
            d = wait_deployed(cf, dist_id)
        domain = d["DomainName"]
    else:
        try:
            created = create_distribution(cf, origin_dns, origin_token)
        except ClientError as e:
            print("CloudFront create failed:", e)
            print(
                "If this is still account-verification blocked, complete verification in the "
                "AWS console Billing/Account page, then re-run this script."
            )
            return 1
        dist_id = created["Id"]
        domain = created["DomainName"]
        print(f"Created {dist_id} → https://{domain}")
        wait_deployed(cf, dist_id)

    https_url = f"https://{domain}"
    bridge_url = f"{https_url}/api-backend/internal/agentcore/tools"

    put_ssm(ssm, f"{SSM_PREFIX}/DEMO_HTTPS_URL", https_url)
    put_ssm(ssm, f"{SSM_PREFIX}/DEMO_URL", https_url)
    put_ssm(ssm, f"{SSM_PREFIX}/CLOUDFRONT_DISTRIBUTION_ID", dist_id)
    put_ssm(ssm, f"{SSM_PREFIX}/CLOUDFRONT_DOMAIN", domain)
    put_ssm(ssm, f"{SSM_PREFIX}/TOOL_BRIDGE_PUBLIC_URL", bridge_url)
    put_ssm(ssm, token_name, origin_token, secure=True)

    state_dir = Path(__file__).resolve().parents[2] / "deploy" / "https"
    state_dir.mkdir(parents=True, exist_ok=True)
    state = {
        "distribution_id": dist_id,
        "domain": domain,
        "https_url": https_url,
        "bridge_url": bridge_url,
        "origin_dns": origin_dns,
        "instance_id": instance_id,
        "region": REGION,
        "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    (state_dir / "state.json").write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")

    rc = patch_ec2(ssm, instance_id, origin_token, https_url, bridge_url)
    if rc != 0:
        print("WARNING: EC2 patch failed — apply ORIGIN_VERIFY_TOKEN manually")
    print(json.dumps({"ok": rc == 0, **{k: state[k] for k in state if k != "at"}}, indent=2))
    print("\nOpen:", https_url)
    print("HTTP EC2 origin still works for bootstrap; prefer the HTTPS CloudFront URL.")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
