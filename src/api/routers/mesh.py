"""MeSH router - handles MeSH term matching for biomedical queries."""
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src.models.schemas import Paper
from src.connectors.mesh_connector import MeSHConnector, MeSHMatcher

router = APIRouter(prefix="/mesh", tags=["mesh"])


def get_app_state():
    from src.api.main import app_state
    return app_state


class MeSHMatchRequest(BaseModel):
    paper_ids: list[str] = []
    mesh_terms: list[str] = []
    threshold: float = 0.3


class MeSHExpandRequest(BaseModel):
    keywords: list[str] = []


@router.post("/match")
async def match_papers_to_mesh(
    paper_ids: list[str],
    mesh_terms: list[str],
    threshold: float = 0.3,
):
    """Match papers against target MeSH terms."""
    app_state = get_app_state()
    papers = app_state.get("papers", [])
    
    paper_map = {p.id: p for p in papers}
    target_papers = [paper_map[pid] for pid in paper_ids if pid in paper_map]
    
    if not target_papers:
        raise HTTPException(
            status_code=404,
            detail="No papers found for provided IDs"
        )
    
    matcher = MeSHMatcher()
    results = matcher.batch_match(target_papers, mesh_terms, threshold)
    
    above_threshold = [r for r in results if r["above_threshold"]]
    
    return {
        "total_papers": len(results),
        "above_threshold": len(above_threshold),
        "results": results,
    }


@router.post("/expand")
async def expand_keywords_with_mesh(
    keywords: list[str],
):
    """Expand keywords using MeSH terms."""
    connector = MeSHConnector()
    expanded = connector.expand_keywords_with_mesh(keywords)
    
    return {
        "original_count": len(keywords),
        "expanded_count": len(expanded),
        "original_keywords": keywords,
        "expanded_keywords": expanded,
    }


@router.get("/search/{keyword}")
async def search_mesh_term(
    keyword: str,
):
    """Search MeSH for terms matching keyword."""
    connector = MeSHConnector()
    terms = connector.search_by_keyword(keyword)
    
    return {
        "keyword": keyword,
        "count": len(terms),
        "terms": [
            {
                "term": t.term,
                "ui": t.ui,
                "tree_number": t.tree_number,
                "qualifier": t.qualifier,
            }
            for t in terms
        ],
    }


@router.get("/paper/{paper_id}")
async def get_paper_mesh_terms(
    paper_id: str,
):
    """Get MeSH terms for a specific paper."""
    app_state = get_app_state()
    papers = app_state.get("papers", [])
    
    paper = next((p for p in papers if p.id == paper_id), None)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    
    connector = MeSHConnector()
    terms = connector.get_terms_for_paper(paper)
    
    return {
        "paper_id": paper_id,
        "title": paper.title,
        "count": len(terms),
        "mesh_terms": [
            {
                "term": t.term,
                "ui": t.ui,
                "tree_number": t.tree_number,
            }
            for t in terms
        ],
    }
