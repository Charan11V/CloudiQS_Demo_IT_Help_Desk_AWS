"""Tool registry for agent."""
from typing import Callable, Dict
from app.tools import ActorContext
from app.tools.identity import (
    get_my_identity, GetMyIdentityInput,
    get_identity_account, GetIdentityAccountInput,
    get_signin_history, GetSigninHistoryInput
)
from app.tools.devices import (
    list_assigned_devices, ListAssignedDevicesInput,
    get_device_diagnostics, GetDeviceDiagnosticsInput
)
from app.tools.network import (
    get_vpn_sessions, GetVpnSessionsInput,
    get_service_outages, GetServiceOutagesInput,
    get_service_catalog, GetServiceCatalogInput
)
from app.tools.knowledge import (
    search_current_knowledge, SearchCurrentKnowledgeInput
)
from app.tools.tickets import (
    list_tickets, ListTicketsInput,
    get_ticket, GetTicketInput,
    create_support_ticket, CreateSupportTicketInput,
    propose_account_unlock, ProposeAccountUnlockInput,
    propose_vpn_certificate_renewal, ProposeVpnCertificateRenewalInput
)

# Tool registry
TOOLS = {
    "get_my_identity": {
        "fn": get_my_identity,
        "input_class": GetMyIdentityInput,
        "description": "Get current user identity"
    },
    "get_identity_account": {
        "fn": get_identity_account,
        "input_class": GetIdentityAccountInput,
        "description": "Get identity account details for a user"
    },
    "get_signin_history": {
        "fn": get_signin_history,
        "input_class": GetSigninHistoryInput,
        "description": "Get sign-in history for a user"
    },
    "list_assigned_devices": {
        "fn": list_assigned_devices,
        "input_class": ListAssignedDevicesInput,
        "description": "List devices assigned to a user"
    },
    "get_device_diagnostics": {
        "fn": get_device_diagnostics,
        "input_class": GetDeviceDiagnosticsInput,
        "description": "Get comprehensive device diagnostics including MDM, telemetry, and patches"
    },
    "get_vpn_sessions": {
        "fn": get_vpn_sessions,
        "input_class": GetVpnSessionsInput,
        "description": "Get VPN sessions for a user"
    },
    "get_service_outages": {
        "fn": get_service_outages,
        "input_class": GetServiceOutagesInput,
        "description": "Get current service outages"
    },
    "get_service_catalog": {
        "fn": get_service_catalog,
        "input_class": GetServiceCatalogInput,
        "description": "Get service catalog"
    },
    "search_current_knowledge": {
        "fn": search_current_knowledge,
        "input_class": SearchCurrentKnowledgeInput,
        "description": "Search current knowledge base (excludes superseded documents)"
    },
    "list_tickets": {
        "fn": list_tickets,
        "input_class": ListTicketsInput,
        "description": "List tickets"
    },
    "get_ticket": {
        "fn": get_ticket,
        "input_class": GetTicketInput,
        "description": "Get ticket details"
    },
    "create_support_ticket": {
        "fn": create_support_ticket,
        "input_class": CreateSupportTicketInput,
        "description": "Create a support ticket with idempotency. The service assigns it to the specialist (security analyst for security or cloud access) or the tenant IT engineer by default."
    },
    "propose_account_unlock": {
        "fn": propose_account_unlock,
        "input_class": ProposeAccountUnlockInput,
        "description": "Propose account unlock (requires human approval)"
    },
    "propose_vpn_certificate_renewal": {
        "fn": propose_vpn_certificate_renewal,
        "input_class": ProposeVpnCertificateRenewalInput,
        "description": "Propose VPN certificate renewal (requires approval and compliance check)"
    }
}


def get_tool(name: str) -> Dict:
    """Get tool by name."""
    if name not in TOOLS:
        raise ValueError(f"Unknown tool: {name}")
    return TOOLS[name]


def get_all_tool_names() -> list[str]:
    """Get all tool names."""
    return list(TOOLS.keys())
