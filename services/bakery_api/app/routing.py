"""Category / issue_code → specialist team routing for bakery tickets."""

from __future__ import annotations

# Skill/capacity-style demo routing (deterministic, tenant-agnostic labels)
ISSUE_TEAM: dict[str, str] = {
    "ID-01": "Identity Desk",
    "ID-02": "Identity Desk",
    "ID-06": "Identity Desk",
    "NET-01": "Network / VPN Desk",
    "NET-02": "Network / VPN Desk",
    "NET-04": "Network / VPN Desk",
    "DEV-01": "Endpoint Desk",
    "DEV-04": "Endpoint Desk",
    "APP-01": "Application Support",
    "APP-04": "Application Support",
    "PRINT-02": "Print Services",
    "SEC-01": "Security Operations",
    "REQ-01": "Service Catalog Desk",
    "GEN-UNKNOWN": "IT Service Desk",
}

CATEGORY_TEAM: dict[str, str] = {
    "identity": "Identity Desk",
    "account": "Identity Desk",
    "network": "Network / VPN Desk",
    "vpn": "Network / VPN Desk",
    "device": "Endpoint Desk",
    "devices": "Endpoint Desk",
    "laptop": "Endpoint Desk",
    "apps": "Application Support",
    "application": "Application Support",
    "email": "Application Support",
    "printing": "Print Services",
    "print": "Print Services",
    "security": "Security Operations",
    "hardware": "Hardware Desk",
    "requests": "Service Catalog Desk",
    "software": "Service Catalog Desk",
}


# Desk → preferred owner role. Anything else falls through to it_engineer.
TEAM_OWNER_ROLE: dict[str, str] = {
    "Security Operations": "security_analyst",
    "Identity Desk": "it_engineer",
    "Network / VPN Desk": "it_engineer",
    "Endpoint Desk": "it_engineer",
    "Application Support": "it_engineer",
    "Print Services": "it_engineer",
    "Service Catalog Desk": "it_engineer",
    "Hardware Desk": "it_engineer",
    "IT Service Desk": "it_engineer",
}


def route_owner(db, tenant_id: str, team: str) -> tuple[str, str]:
    """Return (user_id, display_name) who must own the ticket.

    Prefer the specialist role for the desk. If that role is absent, use the
    first active IT engineer, then IT manager, then tenant admin.
    """
    from sqlalchemy import select

    from .models import User

    preferred = TEAM_OWNER_ROLE.get(team, "it_engineer")
    role_order = [preferred]
    for role in ("it_engineer", "it_manager", "tenant_admin", "security_analyst"):
        if role not in role_order:
            role_order.append(role)

    users = db.execute(
        select(User)
        .where(User.tenant_id == tenant_id, User.is_active == True)  # noqa: E712
        .order_by(User.user_id.asc())
    ).scalars().all()
    by_role: dict[str, User] = {}
    for user in users:
        by_role.setdefault(user.role, user)
    for role in role_order:
        owner = by_role.get(role)
        if owner:
            return owner.user_id, owner.display_name
    raise RuntimeError(f"No IT owner available for tenant {tenant_id}")


def route_team(*, issue_code: str | None = None, category: str | None = None, summary: str | None = None) -> str:
    if issue_code and issue_code in ISSUE_TEAM:
        return ISSUE_TEAM[issue_code]
    cat = (category or "").strip().lower()
    if cat in CATEGORY_TEAM:
        return CATEGORY_TEAM[cat]
    text = f"{issue_code or ''} {category or ''} {summary or ''}".lower()
    for key, team in CATEGORY_TEAM.items():
        if key in text:
            return team
    return "IT Service Desk"
