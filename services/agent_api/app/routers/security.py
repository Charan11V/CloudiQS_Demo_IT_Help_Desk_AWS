"""Security analyst routes."""
import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from app.auth.session import get_session_cookie
from app.enterprise.client import get_enterprise_client

router = APIRouter(prefix="/security", tags=["security"])


@router.get("/findings")
async def security_findings(session: dict = Depends(get_session_cookie)):
    client = get_enterprise_client(session)
    me = await client.get_identity()
    if me.get("role") not in ("security_analyst", "tenant_admin"):
        raise HTTPException(403, "Security visibility restricted")
    # Build findings from permitted raw sources
    findings = []
    try:
        hris = await client.get("/v1/sources/hris_employees", params={"limit": 50})
        idp = await client.get("/v1/sources/identity_directory", params={"limit": 50})
        idp_by_emp = {x.get("employee_id"): x for x in idp}
        for person in hris:
            emp = person.get("employee_id") or person.get("user_id")
            status = (person.get("employment_status") or person.get("status") or "").lower()
            account = idp_by_emp.get(emp)
            if status in ("terminated", "inactive", "separated") and account and (
                account.get("accountEnabled") or account.get("account_state") == "active"
            ):
                findings.append(
                    {
                        "finding_id": f"offboard-gap-{emp}",
                        "severity": "high",
                        "title": "Terminated worker still enabled in IdP",
                        "hris_status": status,
                        "idp_state": account.get("account_state"),
                        "idp_enabled": account.get("accountEnabled"),
                        "employee_id": emp,
                        "kind": "offboarding_discrepancy",
                    }
                )
    except Exception as exc:  # noqa: BLE001
        findings.append({"finding_id": "source-error", "severity": "medium", "title": str(exc)})
    try:
        signins = await client.get("/v1/sources/identity_signins", params={"limit": 80})
        for s in signins:
            if s.get("errorCode") in (50074, 50126, "50074", "50126") or "mfa" in str(s).lower():
                if s.get("status", {}).get("errorCode") or s.get("result") == "failure":
                    findings.append(
                        {
                            "finding_id": f"signin-{s.get('id', s.get('createdDateTime', 'x'))}",
                            "severity": "medium",
                            "title": "Suspicious or failed sign-in",
                            "user_id": s.get("user_id") or s.get("userId"),
                            "raw": {k: s.get(k) for k in ("createdDateTime", "errorCode", "status", "ipAddress") if k in s},
                            "kind": "suspicious_signin",
                        }
                    )
    except Exception:
        pass
    return {"findings": findings[:40], "is_simulated_source": True}


class EscalationBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ticket_id: Optional[str] = None
    reason: str = Field(min_length=5, max_length=2000)
    evidence_ids: Optional[List[str]] = None
    severity: str = Field(default="medium", pattern="^(low|medium|high|critical)$")


@router.post("/escalations")
async def create_escalation(body: EscalationBody, session: dict = Depends(get_session_cookie)):
    client = get_enterprise_client(session)
    try:
        return await client.post(
            "/v1/security/escalations",
            json=body.model_dump(exclude_none=True),
        )
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text
        try:
            detail = exc.response.json().get("detail", detail)
        except Exception:
            pass
        raise HTTPException(exc.response.status_code, detail)


@router.get("/escalations")
async def list_escalations(session: dict = Depends(get_session_cookie)):
    client = get_enterprise_client(session)
    try:
        return await client.get("/v1/security/escalations")
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text
        try:
            detail = exc.response.json().get("detail", detail)
        except Exception:
            pass
        raise HTTPException(exc.response.status_code, detail)
