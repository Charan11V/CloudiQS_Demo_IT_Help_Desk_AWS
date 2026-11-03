"""Load non-Bedrock secrets from SSM at runtime (never from env literals in control plane)."""
from __future__ import annotations

import os
from functools import lru_cache
from typing import Optional


@lru_cache(maxsize=8)
def _get_ssm_param(name: str, with_decryption: bool = True) -> str:
    import boto3

    region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "us-east-1"
    client = boto3.client("ssm", region_name=region)
    resp = client.get_parameter(Name=name, WithDecryption=with_decryption)
    return resp["Parameter"]["Value"]


def openai_api_key() -> str:
    """Groq / OpenAI-compatible API key. Prefer SSM; allow local env for `agentcore dev`."""
    direct = os.getenv("OPENAI_API_KEY") or os.getenv("GROQ_API_KEY") or ""
    if direct:
        return direct
    param = os.getenv("OPENAI_API_KEY_SSM", "/cloudiqs-demo/OPENAI_API_KEY")
    return _get_ssm_param(param)


def tool_bridge_secret() -> str:
    direct = os.getenv("TOOL_BRIDGE_SECRET") or ""
    if direct:
        return direct
    param = os.getenv("TOOL_BRIDGE_SECRET_SSM", "/cloudiqs-demo/TOOL_BRIDGE_SECRET")
    return _get_ssm_param(param)


def openai_base_url() -> str:
    return os.getenv("OPENAI_BASE_URL", "https://api.groq.com/openai/v1")


def openai_model_id() -> str:
    return os.getenv("OPENAI_MODEL_ID", "openai/gpt-oss-20b")


def clear_secret_cache() -> None:
    _get_ssm_param.cache_clear()
