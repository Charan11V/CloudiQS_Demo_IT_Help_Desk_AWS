#!/usr/bin/env python3
"""Push AgentCore env into the running EC2 compose env via SSM (no DB wipe)."""
from __future__ import annotations

import sys
import time
from pathlib import Path

from common import SSM_PREFIX, boto_session


SCRIPT = r'''set -euo pipefail
REGION_APP="us-east-1"
SSM_PREFIX="SSM_PREFIX_PLACEHOLDER"
BRIDGE_FALLBACK="BRIDGE_FALLBACK_PLACEHOLDER"

getp() {
  local name="$1"
  aws ssm get-parameter --region "$REGION_APP" --name "$name" --with-decryption --query Parameter.Value --output text 2>/dev/null || true
}

. /opt/cloudiqs-demo/env.sh

# Compose file expects *_IMAGE names; bootstrap env.sh uses ECR_WEB/AGENT/MOCK.
export ECR_WEB_IMAGE="${ECR_WEB_IMAGE:-${ECR_WEB}:latest}"
export ECR_AGENT_IMAGE="${ECR_AGENT_IMAGE:-${ECR_AGENT}:latest}"
export ECR_MOCK_IMAGE="${ECR_MOCK_IMAGE:-${ECR_MOCK}:latest}"
# Prefer already-built local tags if present from fast_deploy
if docker image inspect cloudiqs-demo-agent-api:local >/dev/null 2>&1; then
  export ECR_AGENT_IMAGE="cloudiqs-demo-agent-api:local"
fi
if docker image inspect cloudiqs-demo-web:local >/dev/null 2>&1; then
  export ECR_WEB_IMAGE="cloudiqs-demo-web:local"
fi
if docker image inspect cloudiqs-demo-mock-api:local >/dev/null 2>&1; then
  export ECR_MOCK_IMAGE="cloudiqs-demo-mock-api:local"
fi
if docker image inspect bakery-api:local >/dev/null 2>&1; then
  export ECR_BAKERY_IMAGE="bakery-api:local"
fi

export APP_SESSION_SIGNING_KEY="$(getp ${SSM_PREFIX}/APP_SESSION_SIGNING_KEY)"
export DEMO_ACCESS_SECRET="$(getp ${SSM_PREFIX}/DEMO_ACCESS_SECRET)"
export MODEL_PROVIDER="$(getp ${SSM_PREFIX}/MODEL_PROVIDER)"; export MODEL_PROVIDER="${MODEL_PROVIDER:-openai_compatible}"
export OPENAI_BASE_URL="$(getp ${SSM_PREFIX}/OPENAI_BASE_URL)"; export OPENAI_BASE_URL="${OPENAI_BASE_URL:-https://api.groq.com/openai/v1}"
export OPENAI_MODEL_ID="$(getp ${SSM_PREFIX}/OPENAI_MODEL_ID)"; export OPENAI_MODEL_ID="${OPENAI_MODEL_ID:-openai/gpt-oss-20b}"
export OPENAI_API_KEY="$(getp ${SSM_PREFIX}/OPENAI_API_KEY)"
export AGENTCORE_ENABLED="$(getp ${SSM_PREFIX}/AGENTCORE_ENABLED)"; export AGENTCORE_ENABLED="${AGENTCORE_ENABLED:-1}"
export AGENTCORE_RUNTIME_ARN="$(getp ${SSM_PREFIX}/AGENTCORE_RUNTIME_ARN)"
export AGENTCORE_REGION="$(getp ${SSM_PREFIX}/AGENTCORE_REGION)"; export AGENTCORE_REGION="${AGENTCORE_REGION:-ap-south-2}"
export TOOL_BRIDGE_PUBLIC_URL="$(getp ${SSM_PREFIX}/TOOL_BRIDGE_PUBLIC_URL)"; export TOOL_BRIDGE_PUBLIC_URL="${TOOL_BRIDGE_PUBLIC_URL:-$BRIDGE_FALLBACK}"
export TOOL_BRIDGE_SECRET="$(getp ${SSM_PREFIX}/TOOL_BRIDGE_SECRET)"

ENVF=/opt/cloudiqs-demo/compose/.env.agentcore
umask 077
cat > "$ENVF" <<EOF
ECR_WEB_IMAGE=${ECR_WEB_IMAGE}
ECR_AGENT_IMAGE=${ECR_AGENT_IMAGE}
ECR_MOCK_IMAGE=${ECR_MOCK_IMAGE}
ECR_BAKERY_IMAGE=${ECR_BAKERY_IMAGE:-bakery-api:local}
APP_SESSION_SIGNING_KEY=${APP_SESSION_SIGNING_KEY}
DEMO_ACCESS_SECRET=${DEMO_ACCESS_SECRET}
MODEL_PROVIDER=${MODEL_PROVIDER}
OPENAI_BASE_URL=${OPENAI_BASE_URL}
OPENAI_MODEL_ID=${OPENAI_MODEL_ID}
OPENAI_API_KEY=${OPENAI_API_KEY}
AGENTCORE_ENABLED=${AGENTCORE_ENABLED}
AGENTCORE_RUNTIME_ARN=${AGENTCORE_RUNTIME_ARN}
AGENTCORE_REGION=${AGENTCORE_REGION}
TOOL_BRIDGE_PUBLIC_URL=${TOOL_BRIDGE_PUBLIC_URL}
TOOL_BRIDGE_SECRET=${TOOL_BRIDGE_SECRET}
AWS_REGION=${AWS_REGION:-us-east-1}
EOF
chmod 600 "$ENVF"

cd /opt/cloudiqs-demo/compose
docker compose -f compose.aws.yaml --env-file "$ENVF" up -d --no-deps --force-recreate agent-api
curl -sf http://127.0.0.1:8001/health/ready || docker compose -f compose.aws.yaml --env-file "$ENVF" exec -T agent-api curl -sf http://127.0.0.1:8001/health/ready || true
echo PATCH_OK region=${AGENTCORE_REGION} arn_prefix=$(printf '%s' "$AGENTCORE_RUNTIME_ARN" | cut -c1-72)
'''


def main() -> int:
    # App stack + SSM live in us-east-1; AgentCore Runtime lives in ap-south-2.
    app_region = "us-east-1"
    import boto3

    cfn = boto3.client("cloudformation", region_name=app_region)
    ssm = boto3.client("ssm", region_name=app_region)
    outs = cfn.describe_stacks(StackName="CloudiQSDemoStack")["Stacks"][0]["Outputs"]
    instance_id = next(o["OutputValue"] for o in outs if o["OutputKey"] == "InstanceId")
    demo_url = next(o["OutputValue"] for o in outs if o["OutputKey"] == "DemoUrl")
    bridge = f"{demo_url.rstrip('/')}/api-backend/internal/agentcore/tools"
    remote = (
        SCRIPT.replace("SSM_PREFIX_PLACEHOLDER", SSM_PREFIX)
        .replace("BRIDGE_FALLBACK_PLACEHOLDER", bridge)
    )
    resp = ssm.send_command(
        InstanceIds=[instance_id],
        DocumentName="AWS-RunShellScript",
        Parameters={"commands": [remote]},
        Comment="HELIO AgentCore env patch",
    )
    command_id = resp["Command"]["CommandId"]
    print(f"SSM command {command_id} on {instance_id}")
    for _ in range(50):
        time.sleep(3)
        inv = ssm.get_command_invocation(CommandId=command_id, InstanceId=instance_id)
        status = inv["Status"]
        if status in {"Success", "Cancelled", "TimedOut", "Failed"}:
            print(inv.get("StandardOutputContent", "")[-2500:])
            err = inv.get("StandardErrorContent", "")
            if err:
                print(err[-1500:])
            return 0 if status == "Success" else 1
    print("Timed out waiting for SSM")
    return 1


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    raise SystemExit(main())
