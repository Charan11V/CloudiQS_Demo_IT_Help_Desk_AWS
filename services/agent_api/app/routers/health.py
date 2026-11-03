"""Health check router."""
from fastapi import APIRouter
import httpx
from app.config import (
    AGENTCORE_ENABLED,
    AGENTCORE_RUNTIME_ARN,
    ENTERPRISE_API_URL,
    MODEL_PROVIDER,
    APP_DB_PATH,
    BEDROCK_MODEL_ID,
    BEDROCK_REGION,
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    OPENAI_MODEL_ID,
    TOOL_BRIDGE_PUBLIC_URL,
)
from app.agent.factory import get_provider_info
from app.agentcore.client import agentcore_configured

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/ready")
async def health_ready():
    """Readiness — local deps healthy. Model checked separately at /health/model."""
    status = {
        "ok": True,
        "provider": get_provider_info(),
        "agentcore": {
            "enabled_flag": AGENTCORE_ENABLED,
            "configured": agentcore_configured(),
            "runtime_arn_set": bool(AGENTCORE_RUNTIME_ARN),
            "tool_bridge_url_set": bool(TOOL_BRIDGE_PUBLIC_URL),
        },
        "database": {
            "path": str(APP_DB_PATH),
            "exists": APP_DB_PATH.exists()
        },
        "enterprise_api": {
            "url": ENTERPRISE_API_URL,
            "connected": False
        }
    }

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{ENTERPRISE_API_URL}/health")
            if response.status_code == 200:
                status["enterprise_api"]["connected"] = True
                status["enterprise_api"]["response"] = response.json()
    except Exception as e:
        status["enterprise_api"]["error"] = str(e)
        status["ok"] = False

    return status


@router.get("/model")
async def health_model():
    """Model availability — failure here must NOT take the app down."""
    info = get_provider_info()
    result = {
        "ok": False,
        "provider": info,
        "region": BEDROCK_REGION if MODEL_PROVIDER == "bedrock" else None,
        "model_id": info.get("model_id"),
    }

    if MODEL_PROVIDER == "simulator":
        result["ok"] = True
        result["note"] = "MODEL_PROVIDER=simulator; deterministic golden-path replies"
        return result

    if MODEL_PROVIDER == "openai_compatible":
        result["base_url"] = OPENAI_BASE_URL
        result["model_id"] = OPENAI_MODEL_ID
        if not OPENAI_API_KEY:
            result["error"] = "OPENAI_API_KEY or GROQ_API_KEY is not set"
            result["hint"] = (
                "Create a Groq key at https://console.groq.com/keys , set "
                "OPENAI_API_KEY (or GROQ_API_KEY), MODEL_PROVIDER=openai_compatible, "
                "OPENAI_MODEL_ID=openai/gpt-oss-20b, "
                "OPENAI_BASE_URL=https://api.groq.com/openai/v1"
            )
            return result
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(
                    f"{OPENAI_BASE_URL.rstrip('/')}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {OPENAI_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": OPENAI_MODEL_ID,
                        "messages": [{"role": "user", "content": "ping"}],
                        "max_tokens": 8,
                    },
                )
            if response.status_code >= 400:
                result["error"] = response.text[:500]
                result["status_code"] = response.status_code
                return result
            result["ok"] = True
            result["verified_live"] = True
            result["provider"] = {**info, "verified_live": True}
        except Exception as exc:  # noqa: BLE001
            result["ok"] = False
            result["error"] = str(exc)
        return result

    if MODEL_PROVIDER != "bedrock":
        result["ok"] = True
        result["note"] = f"MODEL_PROVIDER={MODEL_PROVIDER}; no live Bedrock check"
        return result

    try:
        import boto3

        client = boto3.client("bedrock-runtime", region_name=BEDROCK_REGION)
        model_id = BEDROCK_MODEL_ID
        result["credentials"] = "instance_or_env_chain"
        client.converse(
            modelId=model_id,
            messages=[{"role": "user", "content": [{"text": "ping"}]}],
            inferenceConfig={"maxTokens": 1},
        )
        result["ok"] = True
        result["provider"] = {**info, "verified_live": True}
        result["verified_live"] = True
    except Exception as exc:  # noqa: BLE001
        result["ok"] = False
        result["verified_live"] = False
        result["error"] = str(exc)
        result["hint"] = (
            "Bedrock Converse still blocked for this account, or credentials missing. "
            "For GPT-OSS-20B now: set MODEL_PROVIDER=openai_compatible with a Groq key "
            "(OPENAI_API_KEY / GROQ_API_KEY). For Bedrock later: AWS_BEARER_TOKEN_BEDROCK "
            "+ MODEL_PROVIDER=bedrock after account authorization."
        )
    return result
