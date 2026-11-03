#!/usr/bin/env python3
"""Package + upload CodeZip and create/update AgentCore Runtime (idempotent)."""
from __future__ import annotations

import json
import sys
import time
import uuid
from pathlib import Path

from common import (
    AGENT_NAME,
    CODE_BUCKET,
    DEMO_URL_DEFAULT,
    REGION,
    ROLE_NAME,
    RUNTIME_DIR,
    SSM_PREFIX,
    STATE_DIR,
    boto_session,
    load_state,
    save_state,
)
from package_codezip import ZIP_PATH, main as package_main
from setup_iam_and_secrets import main as setup_main


def upload_zip() -> str:
    s3 = boto_session().client("s3")
    version = (RUNTIME_DIR / "VERSION").read_text(encoding="utf-8").strip()
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    key = f"{AGENT_NAME}/v{version}-{stamp}/deployment_package.zip"
    latest = f"{AGENT_NAME}/deployment_package.zip"
    print(f"Uploading to s3://{CODE_BUCKET}/{key}")
    s3.upload_file(
        str(ZIP_PATH),
        CODE_BUCKET,
        key,
        ExtraArgs={"ExpectedBucketOwner": load_state().get("account_id", "672281861394")},
    )
    s3.copy_object(
        Bucket=CODE_BUCKET,
        CopySource={"Bucket": CODE_BUCKET, "Key": key},
        Key=latest,
        ExpectedBucketOwner=load_state().get("account_id", "672281861394"),
    )
    return latest


def artifact(prefix: str) -> dict:
    return {
        "codeConfiguration": {
            "code": {"s3": {"bucket": CODE_BUCKET, "prefix": prefix}},
            "runtime": "PYTHON_3_13",
            "entryPoint": ["main.py"],
        }
    }


def wait_runtime(control, runtime_id: str, timeout: int = 600) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        resp = control.get_agent_runtime(agentRuntimeId=runtime_id)
        status = resp.get("status") or resp.get("agentRuntimeStatus")
        print(f"  runtime status={status}")
        if status in {"READY", "ACTIVE", "CREATE_COMPLETE", "UPDATE_COMPLETE"}:
            return resp
        if status in {"CREATE_FAILED", "UPDATE_FAILED", "FAILED", "DELETED"}:
            raise RuntimeError(f"Runtime entered failed status: {status} -> {resp}")
        time.sleep(8)
    raise TimeoutError(f"Runtime {runtime_id} not ready within {timeout}s")


def ensure_endpoint(control, runtime_id: str) -> dict:
    name = "DEFAULT"
    try:
        existing = control.list_agent_runtime_endpoints(agentRuntimeId=runtime_id)
        endpoints = existing.get("runtimeEndpoints") or existing.get("agentRuntimeEndpoints") or []
        for ep in endpoints:
            if ep.get("name") == name or ep.get("endpointName") == name:
                print(f"Endpoint exists: {ep.get('endpointId') or ep.get('name')}")
                return ep
    except Exception as exc:
        print(f"list endpoints note: {exc}")

    try:
        resp = control.create_agent_runtime_endpoint(
            agentRuntimeId=runtime_id,
            name=name,
            description="HELIO default endpoint",
        )
        print(f"Created endpoint: {resp}")
        return resp
    except Exception as exc:
        # Some accounts auto-create DEFAULT endpoint with the runtime.
        print(f"create endpoint note (may already exist): {exc}")
        return {"name": name}


def put_runtime_ssm(arn: str) -> None:
    # App wiring lives in us-east-1 (EC2 demo stack); Runtime itself is often ap-south-2.
    import boto3

    app_region = "us-east-1"
    ssm = boto3.client("ssm", region_name=app_region)
    demo_url = DEMO_URL_DEFAULT
    try:
        cfn = boto3.client("cloudformation", region_name=app_region)
        outs = cfn.describe_stacks(StackName="CloudiQSDemoStack")["Stacks"][0].get("Outputs", [])
        for o in outs:
            if o["OutputKey"] == "DemoUrl":
                demo_url = o["OutputValue"]
    except Exception:
        pass
    bridge_url = f"{demo_url.rstrip('/')}/api-backend/internal/agentcore/tools"
    agentcore_region = load_state().get("region") or REGION
    pairs = {
        f"{SSM_PREFIX}/AGENTCORE_RUNTIME_ARN": arn,
        f"{SSM_PREFIX}/AGENTCORE_ENABLED": "1",
        f"{SSM_PREFIX}/AGENTCORE_REGION": agentcore_region,
        f"{SSM_PREFIX}/TOOL_BRIDGE_PUBLIC_URL": bridge_url,
        f"{SSM_PREFIX}/AGENTCORE_QUALIFIER": "DEFAULT",
    }
    for name, value in pairs.items():
        secure = "SECRET" in name or "KEY" in name
        ssm.put_parameter(
            Name=name,
            Value=value,
            Type="SecureString" if secure else "String",
            Overwrite=True,
        )
        print(f"SSM put {name} ({app_region})")


def smoke_invoke(arn: str) -> dict:
    """Direct Runtime invoke without tool bridge (expects bridge failure or prompt error handled)."""
    data = boto_session().client("bedrock-agentcore")
    # Minimal probe: missing bridge should return structured error from our entrypoint, proving Runtime+Python work.
    payload = {
        "prompt": "Reply with exactly: AGENTCORE_OK",
        "actor": {"tenant_id": "t_probe", "user_id": "u_probe", "role": "employee", "session_id": "s_probe"},
        "bridge": {"url": "http://127.0.0.1/invalid", "token": "probe"},
        "run_id": "probe-" + uuid.uuid4().hex,
    }
    # For a true GPT-OSS probe we need a reachable bridge; still verify Runtime boots & returns JSON.
    resp = data.invoke_agent_runtime(
        agentRuntimeArn=arn,
        runtimeSessionId=("probe-" + uuid.uuid4().hex + "-" + uuid.uuid4().hex)[:64],
        payload=json.dumps(payload).encode("utf-8"),
        qualifier="DEFAULT",
    )
    chunks = []
    for chunk in resp.get("response", []):
        if isinstance(chunk, (bytes, bytearray)):
            chunks.append(bytes(chunk))
        elif isinstance(chunk, dict) and "chunk" in chunk:
            part = chunk["chunk"]
            if isinstance(part, dict) and "bytes" in part:
                chunks.append(part["bytes"])
    raw = b"".join(chunks).decode("utf-8", errors="replace")
    print("Smoke invoke raw:", raw[:800])
    try:
        return json.loads(raw) if raw.strip().startswith("{") else {"raw": raw}
    except Exception:
        return {"raw": raw}


def main() -> int:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    setup_main()
    rc = package_main()
    if rc != 0:
        return rc
    prefix = upload_zip()
    state = load_state()
    role_arn = state.get("role_arn") or f"arn:aws:iam::{state.get('account_id')}:role/{ROLE_NAME}"
    control = boto_session().client("bedrock-agentcore-control")

    runtime_id = state.get("agent_runtime_id")
    env_vars = {
        "AWS_REGION": REGION,
        "OPENAI_BASE_URL": state.get("openai_base_url", "https://api.groq.com/openai/v1"),
        "OPENAI_MODEL_ID": state.get("openai_model_id", "openai/gpt-oss-20b"),
        "OPENAI_API_KEY_SSM": f"{SSM_PREFIX}/OPENAI_API_KEY",
        "TOOL_BRIDGE_SECRET_SSM": f"{SSM_PREFIX}/TOOL_BRIDGE_SECRET",
        "LOG_LEVEL": "INFO",
    }

    common_kwargs = {
        "agentRuntimeArtifact": artifact(prefix),
        "roleArn": role_arn,
        "networkConfiguration": {"networkMode": "PUBLIC"},
        "protocolConfiguration": {"serverProtocol": "HTTP"},
        "description": "HELIO Strands + Groq GPT-OSS-20B (no Bedrock FM)",
        "environmentVariables": env_vars,
        "lifecycleConfiguration": {
            "idleRuntimeSessionTimeout": 300,
            "maxLifetime": 1800,
        },
    }

    if runtime_id:
        print(f"Updating existing runtime {runtime_id}")
        try:
            resp = control.update_agent_runtime(agentRuntimeId=runtime_id, **common_kwargs)
        except TypeError:
            # Older botocore may not accept lifecycleConfiguration
            common_kwargs.pop("lifecycleConfiguration", None)
            resp = control.update_agent_runtime(agentRuntimeId=runtime_id, **common_kwargs)
        arn = resp.get("agentRuntimeArn") or state.get("agent_runtime_arn")
    else:
        # Find by name if previously created outside state file
        found = None
        try:
            listed = control.list_agent_runtimes().get("agentRuntimes") or []
            for item in listed:
                if item.get("agentRuntimeName") == AGENT_NAME:
                    found = item
                    break
        except Exception as exc:
            print(f"list runtimes note: {exc}")

        if found:
            runtime_id = found.get("agentRuntimeId")
            print(f"Found runtime by name: {runtime_id}")
            try:
                resp = control.update_agent_runtime(agentRuntimeId=runtime_id, **common_kwargs)
            except TypeError:
                common_kwargs.pop("lifecycleConfiguration", None)
                resp = control.update_agent_runtime(agentRuntimeId=runtime_id, **common_kwargs)
            arn = resp.get("agentRuntimeArn") or found.get("agentRuntimeArn")
        else:
            print(f"Creating runtime {AGENT_NAME}")
            create_kwargs = {"agentRuntimeName": AGENT_NAME, **common_kwargs}
            try:
                # Prefer New Runtime (V2) when supported
                create_kwargs["platformVersion"] = "V2"
                resp = control.create_agent_runtime(**create_kwargs)
            except Exception as exc:
                print(f"create with platformVersion=V2 failed ({exc}); retrying without")
                create_kwargs.pop("platformVersion", None)
                create_kwargs.pop("lifecycleConfiguration", None)
                resp = control.create_agent_runtime(**create_kwargs)
            runtime_id = resp["agentRuntimeId"]
            arn = resp["agentRuntimeArn"]

    wait_runtime(control, runtime_id)
    ensure_endpoint(control, runtime_id)
    # Re-fetch ARN
    got = control.get_agent_runtime(agentRuntimeId=runtime_id)
    arn = got.get("agentRuntimeArn") or arn

    versions = state.get("versions") or []
    versions.append(
        {
            "runtime_id": runtime_id,
            "arn": arn,
            "prefix": prefix,
            "deployed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "version": (RUNTIME_DIR / "VERSION").read_text(encoding="utf-8").strip(),
        }
    )
    state.update(
        {
            "agent_runtime_id": runtime_id,
            "agent_runtime_arn": arn,
            "code_prefix": prefix,
            "versions": versions[-10:],
            "previous_code_prefix": state.get("code_prefix"),
        }
    )
    save_state(state)
    put_runtime_ssm(arn)

    print(json.dumps({"agent_runtime_id": runtime_id, "agent_runtime_arn": arn, "prefix": prefix}, indent=2))
    try:
        smoke = smoke_invoke(arn)
        state["last_smoke"] = {"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "result_keys": list(smoke.keys())}
        save_state(state)
    except Exception as exc:
        print(f"Smoke invoke warning: {exc}")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    raise SystemExit(main())
