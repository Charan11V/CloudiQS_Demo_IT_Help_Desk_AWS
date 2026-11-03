"""Shared helpers for AgentCore deploy/ops scripts."""
from __future__ import annotations

import json
import os
import secrets
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNTIME_DIR = ROOT / "services" / "agentcore_runtime"
STATE_DIR = ROOT / "deploy" / "agentcore"
STATE_FILE = STATE_DIR / "state.json"
ACCOUNT_ID = "672281861394"
AGENT_NAME = os.getenv("HELIO_AGENTCORE_NAME", "helio_gptoss_agent")


def _detect_region() -> str:
    """Prefer explicit env, then saved deploy state (Hyderabad), else us-east-1."""
    env = os.getenv("HELIO_AGENTCORE_REGION") or os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION")
    if env:
        return env
    try:
        if STATE_FILE.exists():
            saved = json.loads(STATE_FILE.read_text(encoding="utf-8")).get("region")
            if saved:
                return saved
    except Exception:
        pass
    return "ap-south-2"  # working AgentCore region for this account


REGION = _detect_region()
CODE_BUCKET = os.getenv(
    "HELIO_AGENTCORE_BUCKET",
    f"bedrock-agentcore-code-{ACCOUNT_ID}-{REGION}",
)
ROLE_NAME = os.getenv("HELIO_AGENTCORE_ROLE", "HelioAgentCoreRuntimeRole")
SSM_PREFIX = "/cloudiqs-demo"
# Prefer HTTPS (Caddy/sslip or CloudFront) when configured; fall back to EC2 HTTP.
DEMO_URL_DEFAULT = "https://3.80.12.216.sslip.io"


def ensure_path():
    """Prefer AWS CLI v2 on Windows."""
    candidates = [
        r"C:\Program Files\Amazon\AWSCLIV2",
        str(Path.home() / ".local" / "bin"),
    ]
    path = os.environ.get("Path") or os.environ.get("PATH") or ""
    for c in candidates:
        if c and c not in path and Path(c).exists():
            path = c + os.pathsep + path
    os.environ["Path"] = path
    os.environ["PATH"] = path
    os.environ.setdefault("AWS_DEFAULT_REGION", REGION)
    os.environ.setdefault("AWS_REGION", REGION)


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {}


def save_state(data: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def boto_session():
    import boto3

    ensure_path()
    return boto3.Session(region_name=REGION)


def random_secret(n: int = 48) -> str:
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    return "".join(secrets.choice(alphabet) for _ in range(n))


def read_dotenv_value(key: str) -> str:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return ""
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        if k.strip() == key:
            return v.strip().strip('"').strip("'")
    return ""


def run(cmd: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess:
    ensure_path()
    print("+", " ".join(cmd))
    return subprocess.run(cmd, cwd=str(cwd or ROOT), check=check)
