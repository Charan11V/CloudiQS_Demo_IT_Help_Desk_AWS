from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import json
import os
from ..auth.session import get_current_user
from ..config import get_settings

router = APIRouter(prefix="/api", tags=["catalog"])
settings = get_settings()

# Load catalog at startup
_catalog_cache = None


def load_catalog():
    """Load guided flow catalog from JSON file"""
    global _catalog_cache
    
    if _catalog_cache is not None:
        return _catalog_cache
    
    catalog_path = os.path.join(settings.SPECS_PATH, "agentic_bakery_helpdesk", "guided_flow_catalog.json")
    
    # Fallback to local path
    if not os.path.exists(catalog_path):
        catalog_path = "../../specs/agentic_bakery_helpdesk/guided_flow_catalog.json"
    
    if not os.path.exists(catalog_path):
        # Return minimal catalog if file not found
        return {
            "schema_version": "1.0",
            "intro": "Hi! I'm your IT assistant. What would you like help with?",
            "root_options": [],
            "global_options": [],
            "common_controls": ["Back", "Start over", "Something else", "Talk to IT"],
            "issues": []
        }
    
    with open(catalog_path, 'r', encoding='utf-8') as f:
        _catalog_cache = json.load(f)
    
    return _catalog_cache


class CatalogResponse(BaseModel):
    schema_version: str
    intro: str
    root_options: list[dict]
    global_options: list[dict]
    common_controls: list[str]
    issues: list[dict]


def _opening_global_options(catalog: dict) -> list[dict]:
    """Global options for clients; omit retired 'I'm not sure'."""
    cleaned: list[dict] = []
    for opt in catalog.get("global_options") or []:
        if not isinstance(opt, dict):
            continue
        oid = (opt.get("id") or "").lower()
        label = (opt.get("label") or "").strip().lower()
        if oid == "not_sure" or label in ("i'm not sure", "i’m not sure", "im not sure"):
            continue
        cleaned.append(opt)
    return cleaned


@router.get("/catalog", response_model=CatalogResponse)
async def get_catalog(current_user: dict = Depends(get_current_user)):
    """Get the guided flow catalog (all 57 issues)"""
    catalog = load_catalog()
    payload = dict(catalog)
    payload["global_options"] = _opening_global_options(catalog)
    return CatalogResponse(**payload)


@router.get("/catalog/issues/{issue_code}")
async def get_issue(issue_code: str, current_user: dict = Depends(get_current_user)):
    """Get details for a specific issue"""
    catalog = load_catalog()
    
    for issue in catalog.get("issues", []):
        if issue.get("issue_code") == issue_code:
            return issue
    
    raise HTTPException(status_code=404, detail=f"Issue {issue_code} not found")
