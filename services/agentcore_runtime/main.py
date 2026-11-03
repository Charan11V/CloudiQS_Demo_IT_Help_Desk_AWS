"""
HELIO AgentCore Runtime entrypoint (HTTP protocol via BedrockAgentCoreApp).

Deployed as Python CodeZip to Amazon Bedrock AgentCore Runtime.
Preserves Groq GPT-OSS-20B (OpenAI-compatible) — does NOT use Bedrock foundation models.
"""
from __future__ import annotations

import signal
import sys

from bedrock_agentcore.runtime import BedrockAgentCoreApp

from helio_agent.runner import run_helio_agent

app = BedrockAgentCoreApp()


@app.entrypoint
def invoke(payload, context=None):
    """AgentCore invocation handler."""
    if not isinstance(payload, dict):
        return {"ok": False, "error": "payload must be a JSON object"}
    try:
        return run_helio_agent(payload)
    except Exception as exc:  # noqa: BLE001
        # Do not include secrets; message only.
        return {
            "ok": False,
            "error": f"agent_failed: {type(exc).__name__}: {exc}",
            "verified_live": False,
            "is_simulation": False,
        }


def _shutdown(sig, frame):
    sys.exit(0)


signal.signal(signal.SIGTERM, _shutdown)


if __name__ == "__main__":
    app.run()
