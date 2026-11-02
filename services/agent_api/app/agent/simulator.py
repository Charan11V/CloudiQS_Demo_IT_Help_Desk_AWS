"""Deterministic simulator for golden-path orchestration."""
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any
from app.tools import ActorContext, ToolResult
from app.tools.registry import get_tool
from app.enterprise.client import EnterpriseClient


class AgentOutcome:
    """Agent outcome structure."""
    def __init__(self):
        self.run_id = None
        self.intent = "diagnose"
        self.headline = ""
        self.plain_language_summary = ""
        self.symptoms = []
        self.findings = []
        self.suggested_steps = []
        self.action_state = "none"
        self.cited_sources = []
        self.unresolved_questions = []
        self.escalation_reason = None
        self.user_confirmation_needed = False


async def run_simulator(
    message: str,
    actor: ActorContext,
    client: EnterpriseClient,
    run_id: str,
    conversation_history: list[dict] | None = None
) -> tuple[AgentOutcome, List[ToolResult]]:
    """Run deterministic simulator orchestration.
    
    This is NOT AI reasoning - it's a scripted workflow that calls REAL tools
    to demonstrate the golden paths.
    """
    message_lower = message.lower()
    tool_results = []
    outcome = AgentOutcome()
    outcome.run_id = run_id
    
    # Build context from conversation history
    history_lower = ""
    if conversation_history:
        history_lower = " ".join([msg.get("content", "").lower() for msg in conversation_history])
    
    # Detect VPN context from current message OR recent history
    has_vpn_context = ("vpn" in message_lower or "vpn" in history_lower)
    has_device_context = ("laptop" in message_lower or "slow" in message_lower or 
                         "laptop" in history_lower or "slow" in history_lower or
                         "device" in message_lower or "device" in history_lower)
    
    # Follow-up handlers: if the user said VPN before and now asks "what should I do?" or similar
    is_followup = any(word in message_lower for word in [
        "what do i do", "what should i do", "what now", "next steps", 
        "how do i", "what to do", "help me", "what can i do"
    ])
    
    # VPN + slow laptop scenario (Asha) - now also triggered by follow-ups after VPN diagnosis
    if (has_vpn_context and has_device_context) or (is_followup and has_vpn_context):
        
        # Call real tools
        tool = get_tool("get_my_identity")
        result = await tool["fn"](actor, client, tool["input_class"]())
        tool_results.append(result)
        
        tool = get_tool("list_assigned_devices")
        result = await tool["fn"](actor, client, tool["input_class"]())
        tool_results.append(result)
        
        # Get device ID from result
        if result.ok and result.data:
            device_id = result.data[0].get("device_id") if result.data else None
            if device_id:
                tool = get_tool("get_device_diagnostics")
                result = await tool["fn"](actor, client, tool["input_class"](device_id=device_id))
                tool_results.append(result)
        
        tool = get_tool("get_vpn_sessions")
        result = await tool["fn"](actor, client, tool["input_class"]())
        tool_results.append(result)
        
        tool = get_tool("search_current_knowledge")
        result = await tool["fn"](actor, client, tool["input_class"](query="VPN"))
        tool_results.append(result)
        
        tool = get_tool("get_service_outages")
        result = await tool["fn"](actor, client, tool["input_class"]())
        tool_results.append(result)
        
        # Build outcome from real evidence
        outcome.intent = "diagnose"
        
        # If this is a follow-up, provide concrete next steps
        if is_followup:
            outcome.headline = "Here's what you need to do next"
            outcome.plain_language_summary = (
                "Based on the VPN and device issues we found, here are your concrete next steps:\n\n"
                "1. **Free up disk space immediately** - Your laptop has only 4% disk space remaining. "
                "Delete old downloads, clear cache files, and remove unused applications. This is causing the slowness.\n\n"
                "2. **Create a support ticket** - I can help you document both the VPN certificate expiration "
                "and the device resource issues. This will track the resolution and assign IT staff.\n\n"
                "3. **Request VPN certificate renewal approval** - Your certificate expired, but the automatic renewal "
                "is blocked because your device shows MDM noncompliance. An IT engineer needs to approve manual renewal.\n\n"
                "The disk space issue is urgent and you can address it now. The VPN issue requires IT intervention."
            )
            outcome.suggested_steps = [
                {
                    "title": "Free up disk space NOW (you can do this)",
                    "why": "Only 4% disk remaining is causing severe slowness. Delete downloads, clear caches.",
                    "action_type": "safe_instruction",
                    "requires_confirmation": False
                },
                {
                    "title": "Create support ticket",
                    "why": "Document VPN certificate expiration + device resource pressure for IT tracking",
                    "action_type": "open_ticket",
                    "requires_confirmation": True
                },
                {
                    "title": "Request VPN certificate renewal approval",
                    "why": "Certificate expired but auto-renewal blocked by MDM noncompliance",
                    "action_type": "request_approval",
                    "requires_confirmation": True
                }
            ]
        else:
            outcome.headline = "Multiple issues identified: VPN certificate expired and device resource pressure"
            outcome.plain_language_summary = (
                "I've investigated your VPN connection and laptop performance issues. "
                "I found two distinct problems that need attention: your device's VPN certificate has expired, "
                "and your laptop is experiencing severe resource constraints with 94% CPU usage and only 4% disk space remaining. "
                "Additionally, your device shows MDM noncompliance which blocks automatic certificate renewal."
            )
            outcome.suggested_steps = [
                {
                    "title": "Create support ticket",
                    "why": "Document issues and track resolution",
                    "action_type": "open_ticket",
                    "requires_confirmation": True
                },
                {
                    "title": "Request VPN certificate renewal approval",
                    "why": "Certificate expired but requires compliance remediation first",
                    "action_type": "request_approval",
                    "requires_confirmation": True
                },
                {
                    "title": "Free up disk space",
                    "why": "Critical disk space affecting performance",
                    "action_type": "safe_instruction",
                    "requires_confirmation": False
                }
            ]
        
        outcome.symptoms = [
            "VPN connection failures",
            "Slow laptop performance",
            "Expired device certificate",
            "High CPU usage (94%)",
            "Critical disk space (4% free)"
        ]
        
        outcome.findings = [
            {
                "finding_id": "vpn_cert_expired",
                "label": "VPN Certificate Expired",
                "kind": "confirmed",
                "explanation": "Device northstar-DEV-0001 VPN certificate expired. Gateway rejecting connections.",
                "evidence_refs": [r.request_id for r in tool_results if r.tool == "get_vpn_sessions"],
                "limitations": []
            },
            {
                "finding_id": "resource_pressure",
                "label": "Severe Resource Constraints",
                "kind": "confirmed",
                "explanation": "Endpoint telemetry shows 94% CPU usage and 4% disk free. Performance degradation expected.",
                "evidence_refs": [r.request_id for r in tool_results if r.tool == "get_device_diagnostics"],
                "limitations": []
            },
            {
                "finding_id": "mdm_noncompliant",
                "label": "MDM Noncompliance Blocks Renewal",
                "kind": "confirmed",
                "explanation": "Device marked noncompliant in MDM. Certificate renewal blocked until compliance restored.",
                "evidence_refs": [r.request_id for r in tool_results if r.tool == "get_device_diagnostics"],
                "limitations": ["Automatic renewal blocked by policy"]
            }
        ]
        
        outcome.action_state = "proposed"
        outcome.cited_sources = [r.evidence[0] if r.evidence else None for r in tool_results if r.ok]
        outcome.cited_sources = [s for s in outcome.cited_sources if s]
        outcome.user_confirmation_needed = True
        
    # Account locked scenario
    elif "account" in message_lower and ("lock" in message_lower or "unlock" in message_lower):
        
        tool = get_tool("get_identity_account")
        result = await tool["fn"](actor, client, tool["input_class"](target_user_id=actor.user_id))
        tool_results.append(result)
        
        tool = get_tool("get_signin_history")
        result = await tool["fn"](actor, client, tool["input_class"](target_user_id=actor.user_id))
        tool_results.append(result)
        
        outcome.intent = "request_action"
        outcome.headline = "Account locked - unlock approval required"
        outcome.plain_language_summary = (
            "Your account is currently locked. I can request an unlock approval from an authorized IT engineer. "
            "Once approved, your account will be reactivated."
        )
        
        outcome.findings = [
            {
                "finding_id": "account_locked",
                "label": "Account Status: Locked",
                "kind": "confirmed",
                "explanation": "Identity directory shows account in locked state after multiple failed sign-ins.",
                "evidence_refs": [r.request_id for r in tool_results if r.tool == "get_identity_account"],
                "limitations": []
            }
        ]
        
        outcome.suggested_steps = [
            {
                "title": "Request account unlock",
                "why": "Account locked and requires IT approval to reactivate",
                "action_type": "request_approval",
                "requires_confirmation": True
            }
        ]
        
        outcome.action_state = "proposed"
        outcome.cited_sources = [r.evidence[0] if r.evidence else None for r in tool_results if r.ok]
        outcome.cited_sources = [s for s in outcome.cited_sources if s]
        outcome.user_confirmation_needed = True
        
    else:
        # Generic help - check if there's VPN context from history but vague current message
        if has_vpn_context and not has_device_context and is_followup:
            outcome.intent = "clarify"
            outcome.headline = "I need a bit more detail"
            outcome.plain_language_summary = (
                "I see you mentioned VPN issues earlier. To help you effectively, could you tell me more specifically:\n\n"
                "• Are you unable to connect to VPN at all?\n"
                "• Is your laptop running slowly?\n"
                "• Are you getting any specific error messages?\n"
                "• Is your account locked or having sign-in problems?\n\n"
                "Or if you'd like me to re-run the diagnosis we did before, just say 'check my VPN again'."
            )
        else:
            # Pure generic help
            tool = get_tool("get_my_identity")
            result = await tool["fn"](actor, client, tool["input_class"]())
            tool_results.append(result)
            
            outcome.intent = "clarify"
            outcome.headline = "How can I help with your IT issue?"
            outcome.plain_language_summary = (
                "I'm here to help with IT support issues like VPN problems, account access, "
                "device issues, and more. Could you describe what specific problem you're experiencing?\n\n"
                "For example:\n"
                "• 'My VPN won't connect'\n"
                "• 'My laptop is running very slowly'\n"
                "• 'My account is locked'\n"
                "• 'Check my device status'"
            )
        
        outcome.cited_sources = []
        outcome.user_confirmation_needed = False
    
    return outcome, tool_results
