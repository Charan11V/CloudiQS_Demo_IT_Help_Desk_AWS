"""Enterprise API client with session-based auth."""
import httpx
from typing import Optional, Any
from app.config import ENTERPRISE_API_URL


class EnterpriseClient:
    """Client for enterprise mock API with bearer token auth."""
    
    def __init__(self, bearer_token: str, tenant_id: str):
        self.bearer_token = bearer_token
        self.tenant_id = tenant_id
        self.base_url = ENTERPRISE_API_URL
        self.headers = {
            "Authorization": f"Bearer {bearer_token}",
            "Content-Type": "application/json"
        }
    
    async def get(self, path: str, params: Optional[dict] = None) -> dict:
        """GET request."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.base_url}{path}",
                params=params,
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
    
    async def post(self, path: str, json: dict, extra_headers: Optional[dict] = None) -> dict:
        """POST request."""
        headers = self.headers.copy()
        if extra_headers:
            headers.update(extra_headers)
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}{path}",
                json=json,
                headers=headers
            )
            response.raise_for_status()
            return response.json()
    
    async def patch(self, path: str, json: dict) -> dict:
        """PATCH request."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.patch(
                f"{self.base_url}{path}",
                json=json,
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
    
    # Convenience methods
    
    async def get_identity(self) -> dict:
        """Get current user identity."""
        return await self.get("/v1/me")
    
    async def get_identity_account(self, user_id: str) -> dict:
        """Get identity account details."""
        return await self.get(f"/v1/identity/accounts/{user_id}")
    
    async def get_signin_history(self, user_id: str) -> list:
        """Get sign-in history."""
        return await self.get(f"/v1/identity/signins/{user_id}")
    
    async def list_devices(self, user_id: Optional[str] = None) -> list:
        """List devices."""
        params = {"user_id": user_id} if user_id else {}
        return await self.get("/v1/devices", params=params)
    
    async def get_device_diagnostics(self, device_id: str) -> dict:
        """Get device diagnostics."""
        return await self.get(f"/v1/devices/{device_id}/diagnostics")
    
    async def get_vpn_sessions(self, user_id: Optional[str] = None) -> list:
        """Get VPN sessions."""
        params = {"user_id": user_id} if user_id else {}
        return await self.get("/v1/vpn/sessions", params=params)
    
    async def get_service_outages(self) -> list:
        """Get service outages."""
        return await self.get("/v1/services/outages")
    
    async def get_service_catalog(self) -> list:
        """Get service catalog."""
        return await self.get("/v1/service-catalog")
    
    async def search_knowledge(self, query: str, include_superseded: bool = False) -> list:
        """Search knowledge base."""
        params = {"q": query, "include_superseded": include_superseded}
        return await self.get("/v1/knowledge/search", params=params)
    
    async def list_tickets(self, status: Optional[str] = None, limit: int = 100) -> list:
        """List tickets."""
        params = {"limit": limit}
        if status:
            params["status"] = status
        return await self.get("/v1/tickets", params=params)
    
    async def get_ticket(self, ticket_id: str) -> dict:
        """Get ticket details."""
        return await self.get(f"/v1/tickets/{ticket_id}")
    
    async def create_ticket(self, summary: str, description: str, category: str, 
                          priority: str = "P3", requester_id: Optional[str] = None,
                          idempotency_key: Optional[str] = None,
                          fault: Optional[str] = None) -> dict:
        """Create a new ticket."""
        payload = {
            "summary": summary,
            "description": description,
            "category": category,
            "priority": priority
        }
        if requester_id:
            payload["requester_id"] = requester_id
        
        headers = {}
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        if fault:
            headers["X-Demo-Fault"] = fault
        
        return await self.post("/v1/tickets", json=payload, extra_headers=headers)
    
    async def create_approval(self, action_type: str, target_user_id: str,
                            device_id: Optional[str], rationale: str) -> dict:
        """Create approval request."""
        payload = {
            "action_type": action_type,
            "target_user_id": target_user_id,
            "device_id": device_id,
            "rationale": rationale
        }
        return await self.post("/v1/approvals", json=payload)
    
    async def list_approvals(self, status: Optional[str] = None) -> list:
        """List approvals."""
        params = {"status": status} if status else {}
        return await self.get("/v1/approvals", params=params)
    
    async def decide_approval(self, approval_id: str, decision: str, reason: str) -> dict:
        """Approve or reject an approval."""
        payload = {"decision": decision, "reason": reason}
        return await self.post(f"/v1/approvals/{approval_id}/decision", json=payload)
    
    async def execute_approval(self, approval_id: str) -> dict:
        """Execute an approved action."""
        return await self.post(f"/v1/approvals/{approval_id}/execute", json={})
    
    async def get_analytics(self) -> dict:
        """Get analytics data."""
        return await self.get("/v1/analytics")
    
    async def get_integrations(self) -> list:
        """Get integrations."""
        return await self.get("/v1/admin/integrations")
    
    async def get_policy(self) -> dict:
        """Get tenant policy."""
        return await self.get("/v1/admin/policy")
    
    async def get_audit_log(self, limit: int = 50) -> list:
        """Get audit log."""
        return await self.get("/v1/audit", params={"limit": limit})


def get_enterprise_client(session: dict) -> EnterpriseClient:
    """Create enterprise client from session."""
    return EnterpriseClient(
        bearer_token=session["bearer_token"],
        tenant_id=session["tenant_id"]
    )
