"""Full-text management router."""
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src.pipeline.fulltext_retriever import FullTextRetriever, PDFTextExtractor
from src.models.schemas import Paper

router = APIRouter(prefix="/fulltext", tags=["fulltext"])


class RetrieveFulltextRequest(BaseModel):
    paper_id: str
    force: bool = False


class BatchRetrieveRequest(BaseModel):
    paper_ids: list[str]
    force: bool = False


def get_app_state():
    from src.api.main import app_state
    return app_state


@router.post("/retrieve")
async def retrieve_paper_fulltext(request: RetrieveFulltextRequest):
    """Retrieve full-text for a single paper."""
    app_state = get_app_state()
    
    paper = next((p for p in app_state.get("papers", []) if p.id == request.paper_id), None)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    
    retriever = FullTextRetriever(
        cache_dir="cache/fulltext",
        output_dir="outputs/fulltext",
    )
    
    result = retriever.retrieve_for_paper(
        paper_id=request.paper_id,
        doi=paper.doi,
        arxiv_id=None,
        force=request.force,
    )
    
    if result.success:
        paper.full_text_retrievable = True
        paper.full_text_path = result.path
        
        for i, screening_result in enumerate(app_state.get("results", [])):
            if screening_result.paper_id == request.paper_id:
                app_state["results"][i].full_text_retrieved = True
                break
    
    return {
        "paper_id": request.paper_id,
        "success": result.success,
        "source": result.source,
        "path": result.path,
        "cached": result.cached,
        "error": result.error,
    }


@router.post("/retrieve/batch")
async def batch_retrieve_fulltext(request: BatchRetrieveRequest):
    """Retrieve full-text for multiple papers."""
    app_state = get_app_state()
    papers = app_state.get("papers", [])
    
    papers_to_retrieve = [
        {"id": p.id, "doi": p.doi}
        for p in papers
        if p.id in request.paper_ids
    ]
    
    if not papers_to_retrieve:
        raise HTTPException(status_code=404, detail="No papers found matching IDs")
    
    retriever = FullTextRetriever()
    
    results = retriever.batch_retrieve(
        papers=papers_to_retrieve,
        delay=1.0,
        max_retries=2,
    )
    
    for success in results["successful"]:
        paper_id = success["paper_id"]
        for i, paper in enumerate(papers):
            if paper.id == paper_id:
                app_state["papers"][i].full_text_path = success["path"]
                break
    
    return results


@router.get("/progress")
async def get_fulltext_progress():
    """Get full-text retrieval progress."""
    app_state = get_app_state()
    papers = app_state.get("papers", [])
    results = app_state.get("results", [])
    
    from src.models.schemas import ScreeningDecision, ScreeningPhase
    included_ids = {
        r.paper_id for r in results 
        if r.decision == ScreeningDecision.INCLUDE
        and r.phase == ScreeningPhase.TITLE_ABSTRACT
    }
    
    total_needed = sum(1 for p in papers if p.id in included_ids)
    retrieved = 0
    pending = 0
    failed = 0
    
    for paper in papers:
        if paper.id not in included_ids:
            continue
        
        if paper.full_text or paper.full_text_path:
            retrieved += 1
        elif paper.flagged_reason:
            failed += 1
        else:
            pending += 1
    
    return {
        "total_needed": total_needed,
        "retrieved": retrieved,
        "pending": pending,
        "failed": failed,
        "progress_percent": round((retrieved / total_needed * 100) if total_needed > 0 else 0, 1),
    }


@router.get("/{paper_id}/extract-text")
async def extract_text_from_pdf(paper_id: str):
    """Extract text from a paper's PDF."""
    app_state = get_app_state()
    
    paper = next((p for p in app_state.get("papers", []) if p.id == paper_id), None)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    
    if not paper.full_text_path:
        raise HTTPException(status_code=400, detail="No PDF path found for paper")
    
    extractor = PDFTextExtractor()
    text = extractor.extract(paper.full_text_path)
    
    if text:
        paper.full_text = text
        
        for i, result in enumerate(app_state.get("results", [])):
            if result.paper_id == paper_id:
                app_state["results"][i].full_text_retrieved = True
                break
        
        return {
            "paper_id": paper_id,
            "success": True,
            "text_length": len(text),
            "text_preview": text[:1000] if text else None,
        }
    
    return {
        "paper_id": paper_id,
        "success": False,
        "error": "Failed to extract text from PDF",
    }


@router.get("/{paper_id}/status")
async def get_fulltext_status(paper_id: str):
    """Get full-text status for a paper."""
    app_state = get_app_state()
    
    paper = next((p for p in app_state.get("papers", []) if p.id == paper_id), None)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    
    return {
        "paper_id": paper_id,
        "has_fulltext": bool(paper.full_text),
        "has_path": bool(paper.full_text_path),
        "path": paper.full_text_path,
        "retrievable": paper.full_text_retrievable,
        "flagged": bool(paper.flagged_reason),
    }
