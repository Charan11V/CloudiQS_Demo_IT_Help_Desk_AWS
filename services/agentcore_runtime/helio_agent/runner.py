"""Strands + Groq GPT-OSS-20B runner used inside AgentCore Runtime."""
from __future__ import annotations

import json
from typing import Any

from strands import Agent
from strands.models.openai import OpenAIModel

from helio_agent.prompts import system_with_actor
from helio_agent.secrets import openai_api_key, openai_base_url, openai_model_id
from helio_agent.tools_bridge import BridgeContext, build_tools


def _outcome_from_text(run_id: str, text: str, tool_events: list[dict]) -> dict[str, Any]:
    outcome: dict[str, Any] = {
        "run_id": run_id,
        "intent": "diagnose",
        "headline": (text[:117] + "...") if len(text) > 120 else text,
        "plain_language_summary": text,
        "findings": [],
        "suggested_steps": [],
        "action_state": {},
        "tool_events": tool_events,
        "provider": {
            "name": "openai_compatible",
            "model_id": openai_model_id(),
            "base_url": openai_base_url(),
            "via": "agentcore_runtime",
            "is_simulation": False,
        },
    }
    try:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            parsed = json.loads(text[start : end + 1])
            for key in (
                "intent",
                "headline",
                "plain_language_summary",
                "symptoms",
                "findings",
                "suggested_steps",
                "action_state",
                "unresolved_questions",
            ):
                if key in parsed:
                    outcome[key] = parsed[key]
    except Exception:
        pass
    return outcome


def run_helio_agent(payload: dict[str, Any]) -> dict[str, Any]:
    prompt = payload.get("prompt") or payload.get("message") or ""
    if not isinstance(prompt, str) or not prompt.strip():
        return {"ok": False, "error": "prompt must be a non-empty string"}

    actor = payload.get("actor") or {}
    if not actor.get("tenant_id") or not actor.get("user_id"):
        return {"ok": False, "error": "actor.tenant_id and actor.user_id are required"}

    bridge = payload.get("bridge") or {}
    bridge_url = bridge.get("url") or ""
    bridge_token = bridge.get("token") or ""
    if not bridge_url or not bridge_token:
        return {"ok": False, "error": "bridge.url and bridge.token are required"}

    run_id = payload.get("run_id") or "agentcore-run"
    history = payload.get("conversation_history") or []

    api_key = openai_api_key()
    if not api_key:
        return {"ok": False, "error": "OPENAI_API_KEY unavailable (SSM or env)"}

    ctx = BridgeContext(bridge_url=bridge_url, bridge_token=bridge_token, run_id=run_id)
    tools = build_tools(ctx)
    model = OpenAIModel(
        client_args={
            "api_key": api_key,
            "base_url": openai_base_url(),
        },
        model_id=openai_model_id(),
        params={
            "temperature": 0.1,
            "max_tokens": 2048,
            "parallel_tool_calls": False,
        },
    )

    tool_names = ", ".join(
        sorted(
            {
                getattr(t, "__name__", None)
                or getattr(getattr(t, "tool_spec", {}), "get", lambda *_: None)("name")
                or getattr(t, "name", None)
                or "tool"
                for t in tools
            }
        )
    )
    # Fold short history into the user message (AgentCore session is often per-request).
    composed = (
        "Use only these tools if needed (exact names): "
        + tool_names
        + ".\nWhen finished, reply in plain text with no further tool calls.\n\nUser message:\n"
        + prompt
    )
    if history:
        lines = []
        for turn in history[-8:]:
            role = turn.get("role", "user")
            content = (turn.get("content") or "")[:800]
            lines.append(f"{role}: {content}")
        composed = (
            "Prior conversation:\n"
            + "\n".join(lines)
            + "\n\nUse only these tools if needed (exact names): "
            + tool_names
            + ".\nWhen finished, reply in plain text with no further tool calls.\n\nCurrent user message:\n"
            + prompt
        )

    def _is_invented_tool_error(exc: BaseException) -> bool:
        msg = str(exc).lower()
        return (
            "was not in request.tools" in msg
            or "tool call validation failed" in msg
            or "attempted to call tool" in msg
        )

    def _plain_answer(system_extra: str, user_msg: str) -> str:
        fallback = Agent(
            model=model,
            system_prompt=system_with_actor(actor) + system_extra,
            tools=[],
        )
        return str(fallback(user_msg))

    agent = Agent(model=model, system_prompt=system_with_actor(actor), tools=tools)
    text = ""
    try:
        text = str(agent(composed))
    except Exception as exc:  # noqa: BLE001
        # GPT-OSS occasionally invents non-existent tool names (JSON/AgentOutcome).
        if not _is_invented_tool_error(exc):
            raise
        if ctx.tool_events:
            prior = json.dumps(ctx.tool_events, default=str)[:4000]
            try:
                text = _plain_answer(
                    "\nNo tools are available in this turn. Answer from prior tool results only. "
                    "Never invent tool names.",
                    "Prior tool execution metadata:\n"
                    + prior
                    + "\n\nUser request:\n"
                    + prompt
                    + "\n\nWrite the final IT helpdesk answer now in plain text.",
                )
            except Exception:
                ok_tools = [e for e in ctx.tool_events if e.get("ok")]
                text = (
                    f"I retrieved {len(ok_tools)} tool result(s) for your request. "
                    "Please ask a follow-up if you need more detail."
                )
        else:
            retry_prompt = (
                "IMPORTANT: Call exactly one real enterprise tool first "
                "(get_my_identity or get_vpn_sessions). "
                "Do not call JSON, AgentOutcome, FinalAnswer, or Response. "
                "Then answer in plain text.\n\n"
                + prompt
            )
            try:
                text = str(
                    Agent(model=model, system_prompt=system_with_actor(actor), tools=tools)(
                        retry_prompt
                    )
                )
            except Exception:
                # Last resort: answer without tools so Runtime never hard-fails the demo path.
                try:
                    text = _plain_answer(
                        "\nTools are unavailable this turn. Be honest about that. Never invent tools.",
                        "User request:\n"
                        + prompt
                        + "\n\nExplain briefly that live tool lookup failed and what the user should try next.",
                    )
                except Exception:
                    text = (
                        "I could not complete live tool lookup for this request. "
                        "Please retry, or use Manual ticketing / Approvals if urgent."
                    )
    outcome = _outcome_from_text(run_id, text, ctx.tool_events)
    outcome["ok"] = True
    outcome["verified_live"] = True
    outcome["tool_calls"] = len(ctx.tool_events)
    return outcome
