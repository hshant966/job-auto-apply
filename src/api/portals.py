"""Portal adapter management API."""
from __future__ import annotations
from fastapi import APIRouter
from src.api.app import get_config

router = APIRouter()

PORTALS = {
    "ssc": {"name": "SSC", "url": "https://ssc.gov.in", "type": "government", "description": "Staff Selection Commission"},
    "upsc": {"name": "UPSC", "url": "https://upsc.gov.in", "type": "government", "description": "Union Public Service Commission"},
    "rrb": {"name": "RRB", "url": "https://www.rrbcdg.gov.in", "type": "government", "description": "Railway Recruitment Board"},
    "ibps": {"name": "IBPS", "url": "https://www.ibps.in", "type": "government", "description": "Institute of Banking Personnel Selection"},
    "linkedin": {"name": "LinkedIn", "url": "https://www.linkedin.com", "type": "private", "description": "LinkedIn Jobs (Easy Apply)"},
    "naukri": {"name": "Naukri", "url": "https://www.naukri.com", "type": "private", "description": "Naukri.com"},
    "indeed": {"name": "Indeed", "url": "https://in.indeed.com", "type": "private", "description": "Indeed India"},
}


@router.get("/")
async def list_portals():
    """List all available portal adapters."""
    return {"portals": PORTALS}


@router.get("/{portal_name}")
async def get_portal(portal_name: str):
    """Get details for a specific portal."""
    if portal_name not in PORTALS:
        from fastapi import HTTPException
        raise HTTPException(404, "Portal not found")
    return {"portal": PORTALS[portal_name], "portal_id": portal_name}


@router.get("/{portal_name}/status")
async def portal_status(portal_name: str):
    """Check portal connection status."""
    if portal_name not in PORTALS:
        from fastapi import HTTPException
        raise HTTPException(404, "Portal not found")
    # Basic connectivity check
    import httpx
    url = PORTALS[portal_name]["url"]
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.head(url, follow_redirects=True)
            return {
                "portal": portal_name,
                "reachable": resp.status_code < 500,
                "status_code": resp.status_code,
            }
    except Exception as e:
        return {"portal": portal_name, "reachable": False, "error": str(e)}
