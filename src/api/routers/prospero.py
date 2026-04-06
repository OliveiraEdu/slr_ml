"""PROSPERO router - handles protocol registration checks."""
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src.models.schemas import Paper
from src.connectors.prospero_connector import PROSPEROConnector

router = APIRouter(prefix="/prospero", tags=["prospero"])


def get_app_state():
    from src.api.main import app_state
    return app_state


class PROSPEROSearchRequest(BaseModel):
    title: Optional[str] = None
    doi: Optional[str] = None


class PROSPEROCheckRequest(BaseModel):
    paper_ids: list[str] = []


@router.post("/search")
async def search_prospero(
    title: Optional[str] = None,
    doi: Optional[str] = None,
):
    """Search PROSPERO for registered protocols."""
    connector = PROSPEROConnector(rate_limit=0.5)
    
    if doi:
        result = connector.search_by_doi(doi)
        if result:
            return {
                "found": True,
                "registration": {
                    "registration_number": result.registration_number,
                    "title": result.title,
                    "status": result.status,
                    "review_type": result.review_type,
                },
            }
        return {"found": False}
    
    if title:
        results = connector.search_by_title(title)
        return {
            "found": len(results) > 0,
            "count": len(results),
            "registrations": [
                {
                    "registration_number": r.registration_number,
                    "title": r.title,
                    "status": r.status,
                    "review_type": r.review_type,
                }
                for r in results
            ],
        }
    
    raise HTTPException(status_code=400, detail="Provide title or doi")


@router.post("/check-papers")
async def check_papers_for_prospero_registration(
    paper_ids: list[str],
):
    """Check multiple papers for PROSPERO protocol registration."""
    app_state = get_app_state()
    papers = app_state.get("papers", [])
    
    connector = PROSPEROConnector(rate_limit=0.5)
    
    results = []
    for paper_id in paper_ids:
        paper = next((p for p in papers if p.id == paper_id), None)
        if not paper:
            results.append({
                "paper_id": paper_id,
                "found": False,
                "error": "Paper not found",
            })
            continue
        
        if paper.title:
            status = connector.get_registration_status(paper.title)
            results.append({
                "paper_id": paper_id,
                "title": paper.title,
                **status,
            })
        else:
            results.append({
                "paper_id": paper_id,
                "found": False,
                "error": "No title available",
            })
    
    registered_count = sum(1 for r in results if r.get("has_registration", False))
    
    return {
        "total_checked": len(results),
        "registered": registered_count,
        "results": results,
    }


@router.get("/status/{paper_id}")
async def check_paper_prospero_status(
    paper_id: str,
):
    """Check a single paper for PROSPERO protocol registration."""
    app_state = get_app_state()
    papers = app_state.get("papers", [])
    
    paper = next((p for p in papers if p.id == paper_id), None)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    
    if not paper.title:
        return {
            "paper_id": paper_id,
            "found": False,
            "error": "No title available",
        }
    
    connector = PROSPEROConnector(rate_limit=0.5)
    status = connector.get_registration_status(paper.title)
    
    return {
        "paper_id": paper_id,
        "title": paper.title,
        **status,
    }
