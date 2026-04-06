"""Semantic Scholar router - handles citation tracking and enrichment."""
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src.models.schemas import Paper
from src.connectors.semantic_scholar_connector import SemanticScholarConnector, CitationAnalyzer

router = APIRouter(prefix="/citations", tags=["citations"])


def get_app_state():
    from src.api.main import app_state
    return app_state


class SemanticScholarEnrichRequest(BaseModel):
    skip_existing: bool = True
    limit: Optional[int] = None


class CitationNetworkRequest(BaseModel):
    paper_id: str
    depth: int = 2


@router.post("/enrich-semantic")
async def enrich_with_semantic_scholar(
    skip_existing: bool = True,
    limit: Optional[int] = None,
):
    """Enrich paper metadata using Semantic Scholar API."""
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

    connector = SemanticScholarConnector(rate_limit=1.0)
    enriched_papers = []
    
    for paper in papers_with_doi:
        if skip_existing and paper.raw_metadata.get("semantic_scholar_id"):
            enriched_papers.append(paper)
            continue
        
        enriched = connector.enrich_paper_with_citations(paper)
        enriched_papers.append(enriched)

    total_citations = sum(p.citations for p in enriched_papers if p.citations)
    total_influential = sum(
        p.raw_metadata.get("influential_citations", 0) 
        for p in enriched_papers
    )

    paper_map = {p.id: p for p in papers}
    paper_map.update({p.id: p for p in enriched_papers})
    app_state["papers"] = list(paper_map.values())

    return {
        "status": "enriched",
        "total_papers": len(enriched_papers),
        "papers_with_doi": len(papers_with_doi),
        "total_citations": total_citations,
        "total_influential_citations": total_influential,
    }


@router.get("/network/{paper_id}")
async def get_citation_network(
    paper_id: str,
    depth: int = 2,
):
    """Get citation network for a paper."""
    analyzer = CitationAnalyzer()
    
    try:
        network = analyzer.get_citation_network(paper_id, depth=depth)
        return network
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rank-influence")
async def rank_by_influential_citations(
    paper_ids: list[str],
):
    """Rank papers by influential citation count."""
    analyzer = CitationAnalyzer()
    
    try:
        ranked = analyzer.rank_by_influence(paper_ids)
        return {
            "total_papers": len(ranked),
            "ranked_papers": [
                {"paper_id": pid, "influential_citations": score}
                for pid, score in ranked
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pivotal")
async def find_pivotal_papers(
    paper_ids: list[str],
    min_influential: int = 5,
):
    """Find pivotal papers in citation network."""
    analyzer = CitationAnalyzer()
    
    try:
        pivotal = analyzer.find_pivotal_papers(paper_ids, min_influential)
        return {
            "total_pivotal": len(pivotal),
            "min_influential": min_influential,
            "pivotal_papers": pivotal,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/paper/{paper_id}")
async def get_semantic_scholar_data(
    paper_id: str,
):
    """Get full Semantic Scholar data for a paper."""
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
    
    connector = SemanticScholarConnector()
    ss_paper = connector.get_paper_by_doi(paper.doi)
    
    if not ss_paper:
        return {
            "status": "not_found",
            "message": "Paper not found in Semantic Scholar",
            "paper_id": paper_id,
            "doi": paper.doi,
        }
    
    return {
        "paper_id": paper_id,
        "semantic_scholar_id": ss_paper.paper_id,
        "title": ss_paper.title,
        "citation_count": ss_paper.citation_count,
        "reference_count": ss_paper.reference_count,
        "influential_citation_count": ss_paper.influential_citation_count,
        "is_open_access": ss_paper.is_open_access,
        "open_access_pdf": ss_paper.open_access_pdf,
        "fields_of_study": ss_paper.fields_of_study,
        "publication_date": ss_paper.publication_date,
    }
