"""Authenticated tool-bridge clients — AgentCore never talks to Docker service DNS."""
from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Any, Callable, List

import httpx
from strands import tool

from helio_agent.secrets import tool_bridge_secret

# Tool names must match services/agent_api/app/tools/registry.py
TOOL_SPECS: list[dict[str, Any]] = [
    {"name": "get_my_identity", "description": "Get current user identity", "params": {}},
    {
        "name": "get_identity_account",
        "description": "Get identity account details for a user",
        "params": {"target_user_id": "string"},
    },
    {
        "name": "get_signin_history",
        "description": "Get sign-in history for a user",
        "params": {"target_user_id": "string"},
    },
    {
        "name": "list_assigned_devices",
        "description": "List devices assigned to a user",
        "params": {"target_user_id": "string (optional)"},
    },
    {
        "name": "get_device_diagnostics",
        "description": "Get comprehensive device diagnostics including MDM, telemetry, and patches",
        "params": {"device_id": "string"},
    },
    {
        "name": "get_vpn_sessions",
        "description": "Get VPN sessions for a user",
        "params": {"target_user_id": "string (optional)"},
    },
    {
        "name": "get_service_outages",
        "description": "Get current service outages",
        "params": {},
    },
    {
        "name": "get_service_catalog",
        "description": "Get service catalog",
        "params": {},
    },
    {
        "name": "search_current_knowledge",
        "description": "Search current knowledge base (excludes superseded documents)",
        "params": {"query": "string"},
    },
    {
        "name": "list_tickets",
        "description": "List tickets",
        "params": {"status": "string (optional)"},
    },
    {
        "name": "get_ticket",
        "description": "Get ticket details",
        "params": {"ticket_id": "string"},
    },
    {
        "name": "create_support_ticket",
        "description": "Create a support ticket with idempotency",
        "params": {
            "title": "string",
            "description": "string",
            "priority": "string (optional)",
            "idempotency_key": "string (optional)",
        },
    },
    {
        "name": "propose_account_unlock",
        "description": "Propose account unlock (requires human approval)",
        "params": {"target_user_id": "string", "reason": "string"},
    },
    {
        "name": "propose_vpn_certificate_renewal",
        "description": "Propose VPN certificate renewal (requires approval and compliance check)",
        "params": {"device_id": "string", "reason": "string"},
    },
]


def _sign(secret: str, ts: str, body: bytes) -> str:
    msg = f"{ts}.".encode("utf-8") + body
    return hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()


class BridgeContext:
    def __init__(self, bridge_url: str, bridge_token: str, run_id: str):
        self.bridge_url = bridge_url.rstrip("/")
        self.bridge_token = bridge_token
        self.run_id = run_id
        self.tool_events: list[dict[str, Any]] = []


def call_bridge(ctx: BridgeContext, tool_name: str, arguments: dict[str, Any]) -> str:
    secret = tool_bridge_secret()
    payload = {
        "tool": tool_name,
        "arguments": arguments or {},
        "run_id": ctx.run_id,
    }
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    ts = str(int(time.time()))
    sig = _sign(secret, ts, body)
    headers = {
        "Content-Type": "application/json",
        "X-Helio-Bridge-Token": ctx.bridge_token,
        "X-Helio-Timestamp": ts,
        "X-Helio-Signature": sig,
    }
    with httpx.Client(timeout=45.0) as client:
        resp = client.post(ctx.bridge_url, content=body, headers=headers)
        text = resp.text
        try:
            data = resp.json()
        except Exception:
            data = {"ok": False, "error": {"safe_message": text[:500]}}
        ctx.tool_events.append(
            {
                "tool": tool_name,
                "ok": bool(data.get("ok")) if isinstance(data, dict) else False,
                "http_status": resp.status_code,
            }
        )
        if resp.status_code >= 400:
            return json.dumps(
                {
                    "ok": False,
                    "tool": tool_name,
                    "error": {
                        "code": "bridge_http_error",
                        "safe_message": f"HTTP {resp.status_code}",
                        "detail": data if isinstance(data, dict) else text[:300],
                    },
                },
                default=str,
            )
        return json.dumps(data, default=str)


def build_tools(ctx: BridgeContext) -> List[Callable]:
    """Build Strands @tool wrappers that execute via the application tool bridge."""

    tools: list[Callable] = []

    def _add(name: str, description: str):
        if name == "get_my_identity":

            @tool(name=name, description=description)
            def get_my_identity() -> str:
                return call_bridge(ctx, name, {})

            tools.append(get_my_identity)
        elif name == "get_identity_account":

            @tool(name=name, description=description)
            def get_identity_account(target_user_id: str) -> str:
                return call_bridge(ctx, name, {"target_user_id": target_user_id})

            tools.append(get_identity_account)
        elif name == "get_signin_history":

            @tool(name=name, description=description)
            def get_signin_history(target_user_id: str) -> str:
                return call_bridge(ctx, name, {"target_user_id": target_user_id})

            tools.append(get_signin_history)
        elif name == "list_assigned_devices":

            @tool(name=name, description=description)
            def list_assigned_devices(target_user_id: str = "") -> str:
                args = {"target_user_id": target_user_id} if target_user_id else {}
                return call_bridge(ctx, name, args)

            tools.append(list_assigned_devices)
        elif name == "get_device_diagnostics":

            @tool(name=name, description=description)
            def get_device_diagnostics(device_id: str) -> str:
                return call_bridge(ctx, name, {"device_id": device_id})

            tools.append(get_device_diagnostics)
        elif name == "get_vpn_sessions":

            @tool(name=name, description=description)
            def get_vpn_sessions(target_user_id: str = "") -> str:
                args = {"target_user_id": target_user_id} if target_user_id else {}
                return call_bridge(ctx, name, args)

            tools.append(get_vpn_sessions)
        elif name == "get_service_outages":

            @tool(name=name, description=description)
            def get_service_outages() -> str:
                return call_bridge(ctx, name, {})

            tools.append(get_service_outages)
        elif name == "get_service_catalog":

            @tool(name=name, description=description)
            def get_service_catalog() -> str:
                return call_bridge(ctx, name, {})

            tools.append(get_service_catalog)
        elif name == "search_current_knowledge":

            @tool(name=name, description=description)
            def search_current_knowledge(query: str) -> str:
                return call_bridge(ctx, name, {"query": query})

            tools.append(search_current_knowledge)
        elif name == "list_tickets":

            @tool(name=name, description=description)
            def list_tickets(status: str = "") -> str:
                args = {"status": status} if status else {}
                return call_bridge(ctx, name, args)

            tools.append(list_tickets)
        elif name == "get_ticket":

            @tool(name=name, description=description)
            def get_ticket(ticket_id: str) -> str:
                return call_bridge(ctx, name, {"ticket_id": ticket_id})

            tools.append(get_ticket)
        elif name == "create_support_ticket":

            @tool(name=name, description=description)
            def create_support_ticket(
                title: str,
                description: str,
                priority: str = "medium",
                idempotency_key: str = "",
            ) -> str:
                args = {
                    "title": title,
                    "description": description,
                    "priority": priority or "medium",
                }
                if idempotency_key:
                    args["idempotency_key"] = idempotency_key
                return call_bridge(ctx, name, args)

            tools.append(create_support_ticket)
        elif name == "propose_account_unlock":

            @tool(name=name, description=description)
            def propose_account_unlock(target_user_id: str, reason: str) -> str:
                return call_bridge(
                    ctx, name, {"target_user_id": target_user_id, "reason": reason}
                )

            tools.append(propose_account_unlock)
        elif name == "propose_vpn_certificate_renewal":

            @tool(name=name, description=description)
            def propose_vpn_certificate_renewal(device_id: str, reason: str) -> str:
                return call_bridge(ctx, name, {"device_id": device_id, "reason": reason})

            tools.append(propose_vpn_certificate_renewal)

    for spec in TOOL_SPECS:
        _add(spec["name"], spec["description"])
    return tools
