"""Evidence reconciler implementing SOURCE_AUTHORITY rules."""
from typing import Dict, List, Any, Optional, Tuple


# Source authority rules for multi-feed reconciliation
SOURCE_AUTHORITY = {
    "employment_status": "hris_employee_records",
    "account_enabled": "identity_directory",
    "account_lockout": "identity_directory",
    "signin_activity": "identity_signins",
    "device_ownership": "mdm_managed_devices",
    "device_compliance": "mdm_managed_devices",
    "vpn_certificate_status": "vpn_sessions",
    "vpn_connection_failures": "vpn_sessions",
    "device_telemetry": "endpoint_telemetry",
    "patch_compliance": "device_patch_compliance",
    "service_outage": "service_health_outages",
    "ticket_state": "itsm_tickets",
    "approval_state": "approvals",
    "current_policy": "policy_current",
    "current_knowledge": "knowledge_documents"
}


class EvidenceReconciler:
    """Reconcile evidence according to source authority rules."""
    
    @staticmethod
    def get_authoritative_source(field: str) -> Optional[str]:
        """Get authoritative source for a field."""
        return SOURCE_AUTHORITY.get(field)
    
    @staticmethod
    def resolve_conflict(field: str, evidence_items: List[Dict]) -> Dict:
        """Resolve conflict using source authority.
        
        Args:
            field: Field name with conflict
            evidence_items: List of evidence items from different sources
            
        Returns:
            Authoritative evidence item or conflict indicator
        """
        authoritative_source = SOURCE_AUTHORITY.get(field)
        
        if not authoritative_source:
            return {
                "resolved": False,
                "reason": "no_authority_rule",
                "items": evidence_items
            }
        
        # Find authoritative item
        for item in evidence_items:
            if item.get("source") == authoritative_source:
                return {
                    "resolved": True,
                    "authoritative": item,
                    "authority_source": authoritative_source,
                    "conflicting_sources": [
                        e.get("source") for e in evidence_items 
                        if e.get("source") != authoritative_source
                    ]
                }
        
        return {
            "resolved": False,
            "reason": "authority_source_missing",
            "expected_source": authoritative_source,
            "available_sources": [e.get("source") for e in evidence_items]
        }
    
    @staticmethod
    def check_staleness(evidence: Dict, max_age_minutes: int = 60) -> bool:
        """Check if evidence is stale.
        
        Args:
            evidence: Evidence item with timestamps
            max_age_minutes: Maximum age in minutes
            
        Returns:
            True if stale
        """
        from datetime import datetime, timezone, timedelta
        
        last_synced = evidence.get("last_synced_at")
        if not last_synced:
            return True
        
        try:
            synced_dt = datetime.fromisoformat(last_synced.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            age = now - synced_dt
            return age > timedelta(minutes=max_age_minutes)
        except Exception:
            return True
    
    @staticmethod
    def rank_evidence(evidence_items: List[Dict], field: Optional[str] = None) -> List[Dict]:
        """Rank evidence items by authority and freshness.
        
        Args:
            evidence_items: List of evidence items
            field: Optional field for authority ranking
            
        Returns:
            Sorted list with highest authority first
        """
        authoritative_source = SOURCE_AUTHORITY.get(field) if field else None
        
        def score(item: Dict) -> Tuple[int, int, int]:
            # Authority match
            authority_score = 100 if item.get("source") == authoritative_source else 0
            
            # Trust level
            trust = item.get("trust_level", "")
            if "verified" in trust:
                trust_score = 50
            elif "unverified" in trust:
                trust_score = 10
            else:
                trust_score = 25
            
            # Freshness (inverse of staleness)
            freshness_score = 0 if EvidenceReconciler.check_staleness(item) else 25
            
            return (authority_score, trust_score, freshness_score)
        
        return sorted(evidence_items, key=score, reverse=True)
