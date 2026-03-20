"""Enrichment router - handles DOI metadata enrichment."""
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src.models.schemas import Paper
from src.connectors.doi_connector import DOIMetadataConnector

router = APIRouter(prefix="/papers", tags=["enrichment"])


def get_app_state():
    from src.api.main import app_state
    return app_state


@router.post("/enrich")
async def enrich_papers_with_doi(
    skip_existing: bool = True,
    email: Optional[str] = None,
    limit: Optional[int] = None,
):
    """Enrich paper metadata using CrossRef and DataCite APIs."""
    app_state = get_app_state()
    papers = app_state.get("papers", [])
    papers_with_doi = [p for p in papers if p.doi]

    if not papers_with_doi:
        return {
            "status": "no_dois",
            "message": "No papers with DOIs found",
            "total_papers": len(papers),
            "papers_with_doi": 0,
        }

    if limit:
        papers_with_doi = papers_with_doi[:limit]

    connector = DOIMetadataConnector(email=email, rate_limit=0.1)
    enriched_papers = connector.batch_enrich(papers_with_doi, skip_existing=skip_existing)

    total_citations = sum(p.citations for p in enriched_papers)
    enriched_count = sum(1 for p in enriched_papers if p.raw_metadata.get("doi_source"))

    paper_map = {p.id: p for p in papers}
    paper_map.update({p.id: p for p in enriched_papers})
    app_state["papers"] = list(paper_map.values())

    return {
        "status": "enriched",
        "total_papers": len(enriched_papers),
        "papers_with_doi": len(papers_with_doi),
        "newly_enriched": enriched_count,
        "total_citations": total_citations,
    }


@router.get("/enrich/{paper_id}")
async def enrich_single_paper(
    paper_id: str,
    email: Optional[str] = None,
):
    """Enrich a single paper by ID using CrossRef/DataCite."""
    app_state = get_app_state()
    papers = app_state.get("papers", [])
    paper = next((p for p in papers if p.id == paper_id), None)

    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    if not paper.doi:
        return {
            "status": "no_doi",
            "message": "Paper has no DOI",
            "paper_id": paper_id,
        }

    connector = DOIMetadataConnector(email=email, rate_limit=0.1)
    enriched_paper = connector.enrich_paper(paper)

    for i, p in enumerate(papers):
        if p.id == paper_id:
            papers[i] = enriched_paper
            break

    return {
        "status": "enriched",
        "paper_id": paper_id,
        "doi": enriched_paper.doi,
        "citations": enriched_paper.citations,
        "publisher": enriched_paper.raw_metadata.get("publisher"),
        "publication_date": enriched_paper.raw_metadata.get("publication_date"),
        "source": enriched_paper.raw_metadata.get("doi_source"),
    }
