"""Read-only diagnosis helpers for guided issue flows."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import (
    Account,
    AppInstallation,
    Device,
    Entitlement,
    PrintJob,
    Service,
    TemporaryFile,
    VpnProfile,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def diagnose_issue(
    db: Session,
    tenant_id: str,
    user_id: str,
    issue_code: str,
    issue_meta: dict,
) -> dict[str, Any]:
    """Return finding + optional action proposal based on live DB state."""
    action_code = issue_meta.get("action_code")
    approval_type = issue_meta.get("approval_type")
    tier = issue_meta.get("tier", "P1")

    if issue_code == "ID-01":
        return _diag_id01(db, tenant_id, user_id, action_code, approval_type)
    if issue_code == "DEV-01":
        return _diag_dev01(db, tenant_id, user_id, action_code, approval_type)
    if issue_code == "NET-01":
        return _diag_net01(db, tenant_id, user_id, action_code, approval_type)
    if issue_code == "NET-02":
        return _diag_net02(db, tenant_id, user_id, action_code, approval_type)
    if issue_code == "DEV-04":
        return _diag_dev04(db, tenant_id, user_id, action_code, approval_type)
    if issue_code == "APP-01":
        return _diag_app01(db, tenant_id, user_id, action_code, approval_type)
    if issue_code in ("APP-04", "ID-06"):
        return _diag_entitlement(db, tenant_id, user_id, issue_code, action_code, approval_type)
    if issue_code == "PRINT-02":
        return _diag_print02(db, tenant_id, user_id, action_code, approval_type)
    if issue_code == "SEC-01":
        return _diag_sec01(issue_code, action_code)
    if issue_code == "REQ-01":
        return _diag_req01(db, tenant_id, user_id, action_code, approval_type)
    if issue_code == "NET-04":
        return _diag_net04(db, tenant_id, user_id)

    # P1 / unimplemented specialised adapters → ticket pathway
    label = issue_meta.get("label") or issue_code
    return {
        "state": "AWAITING_TICKET_DETAILS",
        "assistant_message": (
            f"**{label}**: raise a ticket to continue with IT."
        ),
        "finding": {
            "issue_code": issue_code,
            "confidence": 0.5,
            "observations": [],
            "hypothesis": f"Catalogue match for {issue_code}; specialised tool unavailable",
            "can_claim_resolved_now": False,
            "requires_ticket": True,
        },
        "action_proposal": None,
        "options": [
            {"id": "open_ticket", "label": "Raise a ticket", "type": "action"},
        ],
        "controls": ["back", "start_over", "talk_to_it"],
        "demo_mode": True,
    }


def _svc_status(db: Session, tenant_id: str, service_id: str) -> Optional[str]:
    row = db.execute(
        select(Service).where(Service.tenant_id == tenant_id, Service.service_id == service_id)
    ).scalar_one_or_none()
    return row.status if row else None


def _diag_id01(db, tenant_id, user_id, action_code, approval_type):
    acct = db.execute(
        select(Account).where(Account.tenant_id == tenant_id, Account.user_id == user_id)
    ).scalar_one_or_none()
    if not acct:
        return _insufficient("Account record missing")
    obs = [
        {"field": "account.status", "value": acct.status, "source": f"mock_account:{acct.account_id}"},
        {"field": "account.lock_reason", "value": acct.lock_reason, "source": f"mock_account:{acct.account_id}"},
        {"field": "account.risk_flag", "value": acct.risk_flag, "source": f"mock_account:{acct.account_id}"},
        {"field": "account.failed_logins", "value": acct.failed_logins, "source": f"mock_account:{acct.account_id}"},
    ]
    if acct.status != "locked":
        return {
            "state": "SHOWING_FINDING",
            "assistant_message": (
                f"I checked your simulated account ({acct.account_id}). It is currently "
                f"**{acct.status}**, not locked. I will not change it. "
                "Would you like password/MFA help or a ticket instead?"
            ),
            "finding": {
                "issue_code": "ID-01",
                "confidence": 0.95,
                "observations": obs,
                "hypothesis": "Claimed lock contradicted by account status",
                "can_claim_resolved_now": False,
            },
            "action_proposal": None,
            "options": [
                {"id": "ID-02", "label": "Forgot password", "type": "issue"},
                {"id": "open_ticket", "label": "Open ticket", "type": "action"},
            ],
            "controls": ["back", "start_over", "talk_to_it"],
            "demo_mode": True,
        }
    if acct.risk_flag:
        return {
            "state": "SHOWING_FINDING",
            "assistant_message": (
                "Your simulated account is locked and flagged for security review. "
                "I cannot auto-unlock it. I should escalate to security."
            ),
            "finding": {
                "issue_code": "ID-01",
                "confidence": 0.97,
                "observations": obs,
                "hypothesis": "Locked with risk_flag: escalate",
                "can_claim_resolved_now": False,
                "requires_ticket": True,
            },
            "options": [{"id": "open_ticket", "label": "Escalate to security", "type": "action"}],
            "controls": ["back", "start_over", "talk_to_it"],
            "demo_mode": True,
        }
    return {
        "state": "PROPOSING_ACTION",
        "assistant_message": (
            f"Your demo account {acct.account_id} is locked after unsuccessful attempts "
            f"({acct.lock_reason}). I can unlock your own simulated account after you confirm. "
            "DEMO MODE: this updates synthetic records only."
        ),
        "finding": {
            "issue_code": "ID-01",
            "confidence": 0.98,
            "observations": obs,
            "hypothesis": "Account locked due to failed attempts",
            "proposed_action_code": action_code,
            "requires_approval": False,
            "can_claim_resolved_now": False,
        },
        "action_proposal": {
            "action_code": action_code,
            "target": acct.account_id,
            "expected_version": acct.version,
            "approval_type": approval_type,
            "impact": "Set account.status=active, clear lock_reason, reset failed_logins",
            "label": "Verify and unlock simulated account",
        },
        "options": [
            {"id": "consent_execute", "label": "Verify and unlock", "type": "action"},
            {"id": "open_ticket", "label": "Open ticket instead", "type": "action"},
        ],
        "controls": ["back", "start_over", "talk_to_it"],
        "demo_mode": True,
    }


def _diag_dev01(db, tenant_id, user_id, action_code, approval_type):
    device = db.execute(
        select(Device).where(Device.tenant_id == tenant_id, Device.assigned_to == user_id)
    ).scalars().first()
    if not device:
        return _insufficient("No assigned device found")
    temps = db.execute(
        select(TemporaryFile).where(
            TemporaryFile.tenant_id == tenant_id,
            TemporaryFile.device_id == device.device_id,
            TemporaryFile.removed.is_(False),
        )
    ).scalars().all()
    reclaim = sum(
        float(t.size_gb if t.size_gb is not None else (t.size_bytes or 0) / (1024 ** 3))
        for t in temps
    )
    obs = [
        {"field": "device.disk_total_gb", "value": device.disk_total_gb, "source": f"mock_device:{device.device_id}"},
        {"field": "device.disk_free_gb", "value": device.disk_free_gb, "source": f"mock_device:{device.device_id}"},
        {
            "field": "temporary_files.reclaimable_gb",
            "value": reclaim,
            "source": f"mock_temp:{device.device_id}",
        },
    ]
    if float(device.disk_free_gb or 0) > 40 and reclaim <= 0:
        return {
            "state": "SHOWING_FINDING",
            "assistant_message": (
                f"Device {device.device_id} already has {device.disk_free_gb} GB free and no "
                "allowlisted temp files to remove. No cleanup needed."
            ),
            "finding": {"issue_code": "DEV-01", "observations": obs, "can_claim_resolved_now": False},
            "options": [{"id": "open_ticket", "label": "Open ticket", "type": "action"}],
            "controls": ["back", "start_over"],
            "demo_mode": True,
        }
    file_list = [
        {
            "object_id": t.object_id or str(t.id),
            "path_label": t.path_label or t.file_path,
            "size_gb": t.size_gb if t.size_gb is not None else round((t.size_bytes or 0) / (1024 ** 3), 2),
        }
        for t in temps
    ]
    return {
        "state": "PROPOSING_ACTION",
        "assistant_message": (
            f"Simulated device {device.device_id}: {device.disk_free_gb} GB free of "
            f"{device.disk_total_gb} GB. I found {len(temps)} allowlisted temporary objects "
            f"({reclaim} GB). I can clean only those, not your documents."
        ),
        "finding": {
            "issue_code": "DEV-01",
            "observations": obs,
            "temp_files": file_list,
            "proposed_action_code": action_code,
            "can_claim_resolved_now": False,
        },
        "action_proposal": {
            "action_code": action_code,
            "target": device.device_id,
            "expected_version": device.version,
            "approval_type": approval_type,
            "payload": {"object_ids": [t.object_id or str(t.id) for t in temps]},
            "impact": f"Reclaim ~{reclaim} GB of allowlisted temp data",
            "label": "Clean approved temporary data",
        },
        "options": [
            {"id": "consent_execute", "label": "Clean approved temporary data", "type": "action"},
            {"id": "open_ticket", "label": "Raise ticket", "type": "action"},
        ],
        "controls": ["back", "start_over", "talk_to_it"],
        "demo_mode": True,
    }


def _diag_net01(db, tenant_id, user_id, action_code, approval_type):
    vpn = db.execute(
        select(VpnProfile).where(VpnProfile.tenant_id == tenant_id, VpnProfile.user_id == user_id)
    ).scalars().first()
    if not vpn:
        return _insufficient("No VPN profile for user")
    svc = _svc_status(db, tenant_id, f"{tenant_id}-vpn") or _svc_status(db, tenant_id, "northstar-vpn")
    obs = [
        {"field": "vpn.cert_expires_at", "value": str(vpn.cert_expires_at), "source": f"mock_vpn:{vpn.vpn_id}"},
        {"field": "vpn.last_failure", "value": vpn.last_failure, "source": f"mock_vpn:{vpn.vpn_id}"},
        {"field": "service.status", "value": svc, "source": f"mock_service:{tenant_id}-vpn"},
    ]
    expired = True
    if vpn.cert_expires_at:
        exp = vpn.cert_expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        expired = exp < _now()
    if not expired and vpn.last_failure != "CERT_EXPIRED":
        return {
            "state": "SHOWING_FINDING",
            "assistant_message": "Your simulated VPN certificate does not appear expired. Want to check the client or service health?",
            "finding": {"issue_code": "NET-01", "observations": obs, "can_claim_resolved_now": False},
            "options": [
                {"id": "NET-02", "label": "Outdated VPN client", "type": "issue"},
                {"id": "NET-04", "label": "VPN service outage", "type": "issue"},
            ],
            "controls": ["back", "start_over"],
            "demo_mode": True,
        }
    return {
        "state": "PROPOSING_ACTION",
        "assistant_message": (
            f"The simulated VPN certificate on {vpn.vpn_id} expired "
            f"({vpn.cert_expires_at}). Renewal needs IT approval. Your account has not been changed yet."
        ),
        "finding": {
            "issue_code": "NET-01",
            "observations": obs,
            "proposed_action_code": action_code,
            "requires_approval": True,
            "can_claim_resolved_now": False,
        },
        "action_proposal": {
            "action_code": action_code,
            "target": vpn.vpn_id,
            "expected_version": vpn.version,
            "approval_type": "it_approval",
            "impact": "Renew mock VPN certificate after IT approval",
            "label": "Request certificate renewal approval",
        },
        "options": [
            {"id": "consent_execute", "label": "Request renewal approval", "type": "action"},
            {"id": "open_ticket", "label": "Escalate", "type": "action"},
        ],
        "controls": ["back", "start_over", "talk_to_it"],
        "demo_mode": True,
    }


def _diag_net02(db, tenant_id, user_id, action_code, approval_type):
    vpn = db.execute(
        select(VpnProfile).where(VpnProfile.tenant_id == tenant_id, VpnProfile.user_id == user_id)
    ).scalars().first()
    if not vpn:
        return _insufficient("No VPN profile")
    svc = _svc_status(db, tenant_id, f"{tenant_id}-vpn") or _svc_status(db, tenant_id, "beacon-vpn")
    obs = [
        {"field": "vpn.client_version", "value": vpn.client_version, "source": f"mock_vpn:{vpn.vpn_id}"},
        {"field": "vpn.min_client_version", "value": vpn.min_client_version, "source": f"mock_vpn:{vpn.vpn_id}"},
        {"field": "service.status", "value": svc, "source": "mock_service"},
    ]
    return {
        "state": "PROPOSING_ACTION",
        "assistant_message": (
            f"Simulated VPN client is {vpn.client_version} (minimum {vpn.min_client_version}). "
            f"Tenant VPN service status: {svc or 'unknown'}. "
            "I can update the demo client; connectivity may still wait on service health."
        ),
        "finding": {"issue_code": "NET-02", "observations": obs, "service_status": svc},
        "action_proposal": {
            "action_code": action_code,
            "target": vpn.vpn_id,
            "expected_version": vpn.version,
            "approval_type": approval_type,
            "impact": "Update mock VPN client version",
            "label": "Update demo VPN client",
            "service_status": svc,
        },
        "options": [
            {"id": "consent_execute", "label": "Update demo client", "type": "action"},
            {"id": "open_ticket", "label": "Open ticket", "type": "action"},
        ],
        "controls": ["back", "start_over"],
        "demo_mode": True,
    }


def _diag_net04(db, tenant_id, user_id):
    svc_id = f"{tenant_id}-vpn"
    svc = db.execute(
        select(Service).where(Service.tenant_id == tenant_id, Service.service_id == svc_id)
    ).scalar_one_or_none()
    if not svc:
        svc = db.execute(select(Service).where(Service.tenant_id == tenant_id)).scalars().first()
    status = svc.status if svc else "unknown"
    return {
        "state": "SHOWING_FINDING",
        "assistant_message": (
            f"Tenant VPN service is currently **{status}**. "
            "I will not mark connectivity as resolved. I can open an outage-linked ticket."
        ),
        "finding": {
            "issue_code": "NET-04",
            "observations": [{"field": "service.status", "value": status, "source": f"mock_service:{getattr(svc,'service_id',svc_id)}"}],
            "can_claim_resolved_now": False,
            "requires_ticket": True,
            "nominal_outcome": "waiting_external",
        },
        "options": [{"id": "open_ticket", "label": "Create outage-linked ticket", "type": "action"}],
        "controls": ["back", "start_over"],
        "demo_mode": True,
    }


def _diag_dev04(db, tenant_id, user_id, action_code, approval_type):
    device = db.execute(
        select(Device).where(Device.tenant_id == tenant_id, Device.assigned_to == user_id)
    ).scalars().first()
    if not device:
        return _insufficient("No device")
    if not device.restart_pending:
        return {
            "state": "SHOWING_FINDING",
            "assistant_message": f"Device {device.device_id} does not have a pending restart.",
            "finding": {"issue_code": "DEV-04", "observations": [{"field": "restart_pending", "value": False}]},
            "options": [{"id": "open_ticket", "label": "Open ticket", "type": "action"}],
            "controls": ["back", "start_over"],
            "demo_mode": True,
        }
    return {
        "state": "PROPOSING_ACTION",
        "assistant_message": (
            f"Simulated device {device.device_id} has restart_pending=true. "
            "Confirm a simulated restart (this does not reboot a physical laptop)."
        ),
        "finding": {"issue_code": "DEV-04", "observations": [{"field": "restart_pending", "value": True}]},
        "action_proposal": {
            "action_code": action_code,
            "target": device.device_id,
            "expected_version": device.version,
            "approval_type": approval_type,
            "label": "Confirm simulated restart",
            "impact": "Clear restart_pending, increment reboot_count",
        },
        "options": [
            {"id": "consent_execute", "label": "Confirm simulated restart", "type": "action"},
            {"id": "open_ticket", "label": "Skip / ticket", "type": "action"},
        ],
        "controls": ["back", "start_over"],
        "demo_mode": True,
    }


def _diag_app01(db, tenant_id, user_id, action_code, approval_type):
    inst = db.execute(
        select(AppInstallation).where(
            AppInstallation.tenant_id == tenant_id,
            AppInstallation.user_id == user_id,
        )
    ).scalars().all()
    crashing = next((i for i in inst if (i.health or "").lower() in ("crashing", "crash", "failed")), None)
    target = crashing or (inst[0] if inst else None)
    if not target:
        return _insufficient("No app installation found")
    return {
        "state": "PROPOSING_ACTION",
        "assistant_message": (
            f"Simulated installation {target.installation_id} ({target.app_id}) health={target.health}. "
            "I can restart the demo app and clear safe cache."
        ),
        "finding": {
            "issue_code": "APP-01",
            "observations": [
                {"field": "app.health", "value": target.health, "source": f"mock_app:{target.installation_id}"}
            ],
        },
        "action_proposal": {
            "action_code": action_code,
            "target": target.installation_id,
            "expected_version": target.version,
            "approval_type": approval_type,
            "label": "Restart demo app and clear safe cache",
        },
        "options": [
            {"id": "consent_execute", "label": "Restart demo app", "type": "action"},
            {"id": "open_ticket", "label": "Open ticket", "type": "action"},
        ],
        "controls": ["back", "start_over"],
        "demo_mode": True,
    }


def _diag_entitlement(db, tenant_id, user_id, issue_code, action_code, approval_type):
    ents = db.execute(
        select(Entitlement).where(Entitlement.tenant_id == tenant_id, Entitlement.user_id == user_id)
    ).scalars().all()
    return {
        "state": "PROPOSING_ACTION",
        "assistant_message": (
            "I cannot grant application permissions on my own. I can create an approval-scoped "
            "access request for Jira:admin (or similar) for an authorised reviewer."
        ),
        "finding": {
            "issue_code": issue_code,
            "observations": [
                {"field": "entitlement_count", "value": len(ents), "source": "mock_entitlements"}
            ],
            "requires_approval": True,
            "can_claim_resolved_now": False,
        },
        "action_proposal": {
            "action_code": action_code or "request_entitlement_grant",
            "target": f"{user_id}:jira:admin",
            "expected_version": 1,
            "approval_type": "app_owner_approval",
            "payload": {
                "resource": "jira",
                "scope": "admin",
                "justification": "Need admin access to unblock blocked workflow",
            },
            "label": "Request entitlement approval",
        },
        "options": [
            {"id": "consent_execute", "label": "Request access approval", "type": "action"},
            {"id": "open_ticket", "label": "Open ticket", "type": "action"},
        ],
        "controls": ["back", "start_over"],
        "demo_mode": True,
    }


def _diag_print02(db, tenant_id, user_id, action_code, approval_type):
    jobs = db.execute(
        select(PrintJob).where(PrintJob.tenant_id == tenant_id, PrintJob.user_id == user_id)
    ).scalars().all()
    stuck = next((j for j in jobs if (j.status or "").lower() in ("stuck", "error", "held")), None)
    if not stuck:
        return {
            "state": "SHOWING_FINDING",
            "assistant_message": "I don't see a stuck print job owned by you in the demo queue.",
            "finding": {"issue_code": "PRINT-02", "observations": [{"field": "own_jobs", "value": len(jobs)}]},
            "options": [{"id": "open_ticket", "label": "Open ticket", "type": "action"}],
            "controls": ["back", "start_over"],
            "demo_mode": True,
        }
    return {
        "state": "PROPOSING_ACTION",
        "assistant_message": f"Your simulated print job {stuck.job_id} is {stuck.status}. Retry or cancel only this job.",
        "finding": {"issue_code": "PRINT-02", "observations": [{"field": "job.status", "value": stuck.status}]},
        "action_proposal": {
            "action_code": action_code,
            "target": stuck.job_id,
            "expected_version": stuck.version,
            "approval_type": approval_type,
            "payload": {"action": "retry"},
            "label": "Retry my print job",
        },
        "options": [
            {"id": "consent_execute", "label": "Retry job", "type": "action"},
            {"id": "open_ticket", "label": "Escalate", "type": "action"},
        ],
        "controls": ["back", "start_over"],
        "demo_mode": True,
    }


def _diag_sec01(issue_code, action_code):
    return {
        "state": "PROPOSING_ACTION",
        "assistant_message": (
            "Do not open suspicious links. I can create a high-priority security incident ticket. "
            "I will not declare the threat fixed from your description alone."
        ),
        "finding": {
            "issue_code": issue_code,
            "hypothesis": "User-reported phishing",
            "can_claim_resolved_now": False,
            "nominal_outcome": "escalated",
        },
        "action_proposal": {
            "action_code": action_code or "create_security_incident",
            "target": "security_incident",
            "expected_version": 1,
            "approval_type": "security_review",
            "label": "Create security incident",
            "impact": "Escalate to security; no auto remediation",
        },
        "options": [
            {"id": "consent_execute", "label": "Report phishing / create incident", "type": "action"},
        ],
        "controls": ["back", "start_over", "talk_to_it"],
        "demo_mode": True,
    }


def _diag_req01(db, tenant_id, user_id, action_code, approval_type):
    from ..models import Application, AppInstallation

    device = db.execute(
        select(Device).where(Device.tenant_id == tenant_id, Device.assigned_to == user_id)
    ).scalars().first()
    if not device:
        return _insufficient("No assigned device for software install")

    installed = {
        row.app_id
        for row in db.execute(
            select(AppInstallation).where(
                AppInstallation.tenant_id == tenant_id,
                AppInstallation.device_id == device.device_id,
            )
        ).scalars().all()
    }
    candidates = db.execute(
        select(Application).where(
            Application.tenant_id == tenant_id,
            Application.allowed_to_self_install == True,  # noqa: E712
        )
    ).scalars().all()
    app = next((a for a in candidates if a.app_id not in installed), None)
    if not app:
        return {
            "state": "SHOWING_FINDING",
            "assistant_message": (
                "No additional self-installable approved apps remain for your device in the demo catalog. "
                "I can open a software request ticket."
            ),
            "finding": {"issue_code": "REQ-01", "requires_ticket": True, "can_claim_resolved_now": False},
            "options": [{"id": "open_ticket", "label": "Open request ticket", "type": "action"}],
            "controls": ["back", "start_over"],
            "demo_mode": True,
        }

    return {
        "state": "PROPOSING_ACTION",
        "assistant_message": (
            f"I can install allowlisted demo app **{app.app_name}** (`{app.app_id}`) "
            f"on device {device.device_id} if you consent."
        ),
        "finding": {"issue_code": "REQ-01", "can_claim_resolved_now": False, "app_id": app.app_id},
        "action_proposal": {
            "action_code": action_code,
            "target": device.device_id,
            "expected_version": device.version,
            "approval_type": approval_type,
            "payload": {"app_id": app.app_id, "device_id": device.device_id},
            "label": f"Install {app.app_name} (demo)",
        },
        "options": [
            {"id": "consent_execute", "label": f"Install {app.app_name}", "type": "action"},
            {"id": "open_ticket", "label": "Open request ticket", "type": "action"},
        ],
        "controls": ["back", "start_over"],
        "demo_mode": True,
    }


def _insufficient(msg: str) -> dict:
    return {
        "state": "SHOWING_FINDING",
        "assistant_message": f"I couldn't complete an automated check ({msg}). Raise a ticket to continue.",
        "finding": {"insufficient_evidence": True, "can_claim_resolved_now": False, "requires_ticket": True},
        "options": [{"id": "open_ticket", "label": "Raise a ticket", "type": "action"}],
        "controls": ["back", "start_over", "talk_to_it"],
        "demo_mode": True,
    }
