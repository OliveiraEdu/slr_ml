"""Screening router - handles ML screening and ranking."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel, Field

from src.models.schemas import (
    Paper, RankingWeights, ConfidenceBand, 
    ScreeningDecision, ScreeningPhase, ScreeningMethod
)
from src.ml.classifier import SciBERTClassifier, BackendType

router = APIRouter(prefix="/screening", tags=["screening"])


class ScreenRequest(BaseModel):
    papers: Optional[list[Paper]] = None
    phase: ScreeningPhase = ScreeningPhase.TITLE_ABSTRACT
    include_prompt: str = "This paper is relevant to the research question"
    exclude_prompt: str = "This paper is not relevant to the research question"
    threshold: float = 0.5
    relevant_keywords: Optional[list[str]] = None
    exclusion_keywords: Optional[list[str]] = None


class ManualReviewRequest(BaseModel):
    paper_id: str
    decision: ScreeningDecision
    reason: Optional[str] = None
    notes: Optional[str] = None


class BatchReviewRequest(BaseModel):
    reviews: list[ManualReviewRequest]


def get_app_state():
    from src.api.main import app_state
    return app_state


@router.post("/run")
async def run_screening(
    request: ScreenRequest = Body(default=ScreenRequest()),
):
    """Run ML screening on papers with confidence calibration."""
    app_state = get_app_state()
    try:
        papers_to_screen = request.papers if request.papers else app_state["papers"]
        
        if not papers_to_screen:
            return {
                "status": "no_papers",
                "message": "No papers to screen",
            }
        
        keywords = {}
        if app_state.get("classification_config") and app_state["classification_config"].keywords:
            keywords = {
                "required": app_state["classification_config"].keywords.required or [],
                "optional": app_state["classification_config"].keywords.optional or [],
            }
        
        ranking_weights = RankingWeights()
        if app_state.get("classification_config") and app_state["classification_config"].ranking_weights:
            ranking_weights = app_state["classification_config"].ranking_weights
        
        classifier = SciBERTClassifier(
            model_name="allenai/scibert_scivocab_uncased",
            device="auto",
            backend=BackendType.AUTO,
            keywords=keywords,
            ranking_weights=ranking_weights,
        )

        results = []
        for paper in papers_to_screen:
            result = classifier.classify_relevance(
                paper=paper,
                include_prompt=request.include_prompt,
                exclude_prompt=request.exclude_prompt,
                threshold=request.threshold,
                phase=request.phase,
            )
            results.append(result)

        if not request.papers:
            app_state["results"] = results
        else:
            app_state["results"].extend(results)

        # Count by decision
        included = sum(1 for r in results if r.decision == ScreeningDecision.INCLUDE)
        excluded = sum(1 for r in results if r.decision == ScreeningDecision.EXCLUDE)
        uncertain = sum(1 for r in results if r.decision == ScreeningDecision.UNCERTAIN)
        
        # Count by confidence band
        high_confidence = sum(1 for r in results if r.confidence_band == ConfidenceBand.HIGH)
        medium_confidence = sum(1 for r in results if r.confidence_band == ConfidenceBand.MEDIUM)
        low_confidence = sum(1 for r in results if r.confidence_band == ConfidenceBand.LOW)

        classifier.unload()

        return {
            "status": "screening_complete",
            "phase": request.phase.value,
            "total_screened": len(results),
            "decisions": {
                "included": included,
                "excluded": excluded,
                "uncertain": uncertain,
            },
            "confidence_bands": {
                "high": high_confidence,
                "medium": medium_confidence,
                "low": low_confidence,
            },
            "manual_review_count": uncertain + low_confidence,
            "backend": classifier.backend.value if hasattr(classifier.backend, 'value') else str(classifier.backend),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/results")
async def get_screening_results(
    decision: Optional[str] = None,
    confidence_band: Optional[str] = Query(None, description="Filter by confidence band: high, medium, low"),
    limit: int = Query(100, le=1000),
):
    """Get screening results with optional filtering."""
    app_state = get_app_state()
    results = app_state["results"]

    if decision:
        results = [r for r in results if r.decision.value == decision]
    
    if confidence_band:
        band = ConfidenceBand(confidence_band.lower())
        results = [r for r in results if r.confidence_band == band]

    return {
        "total": len(results),
        "results": [r.model_dump() for r in results[:limit]],
    }


@router.get("/queue/uncertain")
async def get_uncertain_papers(
    limit: int = Query(50, ge=1, le=500),
    sort_by: str = Query("relevance", regex="^(relevance|composite|citations)$"),
):
    """Get papers requiring manual review (uncertain or low confidence)."""
    app_state = get_app_state()
    results = app_state["results"]
    papers = app_state["papers"]
    
    uncertain_results = [
        r for r in results 
        if r.decision == ScreeningDecision.UNCERTAIN 
        or r.confidence_band == ConfidenceBand.LOW
    ]
    
    paper_map = {p.id: p for p in papers}
    
    queue = []
    for r in uncertain_results:
        p = paper_map.get(r.paper_id)
        if p:
            queue.append({
                "paper": p.model_dump(),
                "result": r.model_dump(),
            })
    
    if sort_by == "relevance":
        queue.sort(key=lambda x: x["result"]["relevance_score"], reverse=True)
    elif sort_by == "citations":
        queue.sort(key=lambda x: x["result"]["citation_score"], reverse=True)
    else:
        queue.sort(key=lambda x: x["result"]["composite_score"], reverse=True)
    
    return {
        "total": len(queue),
        "manual_review_required": len(queue),
        "sort_by": sort_by,
        "papers": queue[:limit],
    }


@router.post("/review")
async def manual_review(
    request: ManualReviewRequest,
):
    """Update a paper's screening decision manually."""
    app_state = get_app_state()
    results = app_state["results"]
    
    for i, result in enumerate(results):
        if result.paper_id == request.paper_id:
            results[i].decision = request.decision
            results[i].screened_by = ScreeningMethod.MANUAL
            results[i].reason = request.reason
            results[i].notes = request.notes
            results[i].reviewed_at = str(datetime.now().isoformat())
            
            return {
                "status": "updated",
                "paper_id": request.paper_id,
                "new_decision": request.decision.value,
                "screened_by": "manual",
            }
    
    raise HTTPException(status_code=404, detail="Paper not found in screening results")


@router.post("/review/batch")
async def batch_manual_review(request: BatchReviewRequest):
    """Update multiple papers' screening decisions in batch."""
    app_state = get_app_state()
    results = app_state["results"]
    
    result_map = {r.paper_id: i for i, r in enumerate(results)}
    
    updated = []
    not_found = []
    
    for review in request.reviews:
        if review.paper_id in result_map:
            idx = result_map[review.paper_id]
            results[idx].decision = review.decision
            results[idx].screened_by = ScreeningMethod.MANUAL
            results[idx].reason = review.reason
            results[idx].notes = review.notes
            results[idx].reviewed_at = str(datetime.now().isoformat())
            updated.append(review.paper_id)
        else:
            not_found.append(review.paper_id)
    
    return {
        "status": "batch_complete",
        "updated_count": len(updated),
        "not_found_count": len(not_found),
        "updated": updated,
        "not_found": not_found,
    }


@router.get("/rank")
async def rank_papers(
    n: int = Query(50, ge=1, le=500, description="Number of top papers to return"),
    decision: Optional[str] = Query(None, description="Filter by decision"),
    sort_by: str = Query("composite", regex="^(composite|relevance|citations|recency)$"),
):
    """Get top N papers ranked by composite score."""
    app_state = get_app_state()
    results = app_state["results"]
    papers = app_state["papers"]
    
    if decision:
        results = [r for r in results if r.decision.value == decision]
    
    paper_map = {p.id: p for p in papers}
    
    ranked = []
    for r in results:
        p = paper_map.get(r.paper_id)
        if p:
            ranked.append({
                "paper": p.model_dump(),
                "result": r.model_dump(),
            })
    
    if sort_by == "relevance":
        ranked.sort(key=lambda x: x["result"]["relevance_score"], reverse=True)
    elif sort_by == "citations":
        ranked.sort(key=lambda x: x["result"]["citation_score"], reverse=True)
    elif sort_by == "recency":
        ranked.sort(key=lambda x: x["result"]["recency_score"], reverse=True)
    else:
        ranked.sort(key=lambda x: x["result"]["composite_score"], reverse=True)
    
    return {
        "total": len(ranked),
        "top_n": n,
        "sort_by": sort_by,
        "papers": ranked[:n],
    }


@router.get("/statistics")
async def get_screening_statistics():
    """Get comprehensive screening statistics for PRISMA reporting."""
    app_state = get_app_state()
    results = app_state["results"]
    papers = app_state["papers"]
    
    if not results:
        return {
            "status": "no_results",
            "message": "No screening results available",
        }
    
    # Decision breakdown
    decisions = {
        "include": sum(1 for r in results if r.decision == ScreeningDecision.INCLUDE),
        "exclude": sum(1 for r in results if r.decision == ScreeningDecision.EXCLUDE),
        "uncertain": sum(1 for r in results if r.decision == ScreeningDecision.UNCERTAIN),
        "pending": sum(1 for r in results if r.decision == ScreeningDecision.PENDING),
    }
    
    # Confidence band breakdown
    confidence_bands = {
        "high": sum(1 for r in results if r.confidence_band == ConfidenceBand.HIGH),
        "medium": sum(1 for r in results if r.confidence_band == ConfidenceBand.MEDIUM),
        "low": sum(1 for r in results if r.confidence_band == ConfidenceBand.LOW),
    }
    
    # Screening method breakdown
    methods = {
        "ml": sum(1 for r in results if r.screened_by == ScreeningMethod.ML),
        "manual": sum(1 for r in results if r.screened_by == ScreeningMethod.MANUAL),
        "hybrid": sum(1 for r in results if r.screened_by == ScreeningMethod.HYBRID),
    }
    
    # Score distribution
    scores = [r.relevance_score for r in results]
    score_stats = {
        "mean": sum(scores) / len(scores) if scores else 0,
        "min": min(scores) if scores else 0,
        "max": max(scores) if scores else 0,
    }
    
    return {
        "total_papers": len(papers),
        "total_screened": len(results),
        "decisions": decisions,
        "confidence_bands": confidence_bands,
        "screening_methods": methods,
        "score_distribution": score_stats,
        "prisma_ready": {
            "identified": len(papers),
            "after_duplicates": len(set(p.id for p in papers)),
            "screened": len(results),
            "included": decisions["include"],
            "excluded": decisions["exclude"] + decisions["uncertain"],
            "manual_review_required": confidence_bands["low"] + decisions["uncertain"],
        }
    }


# Two-Stage Screening Workflow Endpoints

@router.get("/progression")
async def get_screening_progression():
    """Get paper progression through screening stages."""
    app_state = get_app_state()
    results = app_state["results"]
    papers = app_state["papers"]
    
    stage_1_results = [r for r in results if r.phase == ScreeningPhase.TITLE_ABSTRACT]
    stage_2_results = [r for r in results if r.phase == ScreeningPhase.FULL_TEXT]
    
    # Stage 1 breakdown
    stage_1_included = sum(1 for r in stage_1_results if r.decision == ScreeningDecision.INCLUDE)
    stage_1_excluded = sum(1 for r in stage_1_results if r.decision == ScreeningDecision.EXCLUDE)
    stage_1_uncertain = sum(1 for r in stage_1_results if r.decision == ScreeningDecision.UNCERTAIN)
    
    # Stage 2 breakdown
    stage_2_included = sum(1 for r in stage_2_results if r.decision == ScreeningDecision.INCLUDE)
    stage_2_excluded = sum(1 for r in stage_2_results if r.decision == ScreeningDecision.EXCLUDE)
    
    # Papers needing Stage 2
    stage_2_eligible = stage_1_included
    stage_2_progressed = sum(1 for r in stage_1_results if r.progressed_to_stage_2)
    
    # Papers requiring FT retrieval
    ft_needed = sum(1 for r in stage_1_results if r.decision == ScreeningDecision.INCLUDE)
    ft_retrieved = sum(1 for r in results if r.full_text_retrieved)
    ft_flagged = sum(1 for r in stage_1_results if r.flagged_for_no_ft)
    
    return {
        "stage_1": {
            "total_screened": len(stage_1_results),
            "included": stage_1_included,
            "excluded": stage_1_excluded,
            "uncertain": stage_1_uncertain,
        },
        "stage_2": {
            "eligible": stage_2_eligible,
            "progressed": stage_2_progressed,
            "screened": len(stage_2_results),
            "included": stage_2_included,
            "excluded": stage_2_excluded,
        },
        "full_text": {
            "needed": ft_needed,
            "retrieved": ft_retrieved,
            "flagged_no_doi": ft_flagged,
            "pending": ft_needed - ft_retrieved - ft_flagged,
        },
        "final_included": stage_2_included if stage_2_results else stage_1_included,
    }


@router.get("/queue/uncertain/csv")
async def export_uncertain_queue_csv(
    limit: int = Query(500, ge=1, le=500),
    sort_by: str = Query("relevance", regex="^(relevance|composite|citations)$"),
):
    """Export uncertain papers queue to CSV for manual review."""
    from fastapi.responses import StreamingResponse
    from io import StringIO
    
    app_state = get_app_state()
    results = app_state["results"]
    papers = app_state["papers"]
    
    uncertain_results = [
        r for r in results 
        if r.decision == ScreeningDecision.UNCERTAIN 
        or r.confidence_band == ConfidenceBand.LOW
    ]
    
    paper_map = {p.id: p for p in papers}
    
    queue = []
    for r in uncertain_results:
        p = paper_map.get(r.paper_id)
        if p:
            queue.append({
                "paper": p,
                "result": r,
            })
    
    if sort_by == "relevance":
        queue.sort(key=lambda x: x["result"].relevance_score, reverse=True)
    elif sort_by == "citations":
        queue.sort(key=lambda x: x["result"].citation_score, reverse=True)
    else:
        queue.sort(key=lambda x: x["result"].composite_score, reverse=True)
    
    csv_lines = []
    csv_lines.append("review_order,paper_id,title,authors,year,doi,journal,source,ml_decision,ml_score,confidence_band,screened_by,manual_decision,review_notes")
    
    for idx, item in enumerate(queue[:limit], 1):
        p = item["paper"]
        r = item["result"]
        
        title = (p.title or "").replace('"', '""').replace('\n', ' ')
        authors = "; ".join(p.authors or []).replace('"', '""')
        journal = (p.journal or "").replace('"', '""')
        notes = ""
        
        csv_lines.append(
            f'{idx},'
            f'{p.id},'
            f'"{title}",'
            f'"{authors}",'
            f'{p.year or ""},'
            f'{p.doi or ""},'
            f'"{journal}",'
            f'{p.source.value if p.source else ""},'
            f'{r.decision.value},'
            f'{r.relevance_score:.4f},'
            f'{r.confidence_band.value},'
            f'{r.screened_by.value},'
            f','
            f'"{notes}"'
        )
    
    csv_content = "\n".join(csv_lines)
    
    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=manual_review_queue.csv"}
    )


@router.get("/queue/all/csv")
async def export_all_papers_csv(
    decision: Optional[str] = Query(None, description="Filter by decision: include, exclude, uncertain"),
):
    """Export all screened papers to CSV."""
    app_state = get_app_state()
    results = app_state["results"]
    papers = app_state["papers"]
    
    if decision:
        results = [r for r in results if r.decision.value == decision]
    
    paper_map = {p.id: p for p in papers}
    
    csv_lines = []
    csv_lines.append("paper_id,title,authors,year,doi,journal,source,abstract_length,decision,relevance_score,composite_score,confidence_band,screened_by,reason,reviewed_at")
    
    for r in results:
        p = paper_map.get(r.paper_id)
        if not p:
            continue
        
        title = (p.title or "").replace('"', '""').replace('\n', ' ')
        authors = "; ".join(p.authors or []).replace('"', '""')
        journal = (p.journal or "").replace('"', '""')
        abstract = (p.abstract or "")[:200].replace('"', '""')
        reason = (r.reason or "").replace('"', '""')
        reviewed = r.reviewed_at or ""
        
        csv_lines.append(
            f'{p.id},'
            f'"{title}",'
            f'"{authors}",'
            f'{p.year or ""},'
            f'{p.doi or ""},'
            f'"{journal}",'
            f'{p.source.value if p.source else ""},'
            f'{len(p.abstract or "")},'
            f'{r.decision.value},'
            f'{r.relevance_score:.4f},'
            f'{r.composite_score:.4f},'
            f'{r.confidence_band.value},'
            f'{r.screened_by.value},'
            f'"{reason}",'
            f'{reviewed}'
        )
    
    csv_content = "\n".join(csv_lines)
    
    return {
        "total": len(results),
        "csv": csv_content,
    }


@router.get("/queue/stage2")
async def get_stage2_queue(
    limit: int = Query(100, ge=1, le=500),
    sort_by: str = Query("relevance", regex="^(relevance|composite|citations)$"),
):
    """Get papers eligible for Stage 2 (full-text) screening."""
    app_state = get_app_state()
    results = app_state["results"]
    papers = app_state["papers"]
    
    stage_1_included_ids = {
        r.paper_id for r in results 
        if r.phase == ScreeningPhase.TITLE_ABSTRACT 
        and r.decision == ScreeningDecision.INCLUDE
    }
    
    already_screened_stage2 = {
        r.paper_id for r in results 
        if r.phase == ScreeningPhase.FULL_TEXT
    }
    
    eligible_papers = []
    for paper_id in stage_1_included_ids:
        if paper_id in already_screened_stage2:
            continue
        
        paper = next((p for p in papers if p.id == paper_id), None)
        result = next((r for r in results if r.paper_id == paper_id), None)
        
        if paper and result:
            eligible_papers.append({
                "paper": paper.model_dump(),
                "result": result.model_dump(),
                "has_fulltext": bool(paper.full_text or paper.full_text_path),
                "flagged": bool(paper.flagged_reason),
                "source": paper.source.value,
                "has_doi": bool(paper.doi),
            })
    
    if sort_by == "relevance":
        eligible_papers.sort(key=lambda x: x["result"]["relevance_score"], reverse=True)
    elif sort_by == "citations":
        eligible_papers.sort(key=lambda x: x["result"]["citation_score"], reverse=True)
    else:
        eligible_papers.sort(key=lambda x: x["result"]["composite_score"], reverse=True)
    
    return {
        "total_eligible": len(eligible_papers),
        "with_fulltext": sum(1 for p in eligible_papers if p["has_fulltext"]),
        "without_fulltext": sum(1 for p in eligible_papers if not p["has_fulltext"]),
        "flagged": sum(1 for p in eligible_papers if p["flagged"]),
        "papers": eligible_papers[:limit],
    }


@router.post("/review/import-csv")
async def import_review_csv(
    decisions: str = Body(..., description="CSV content with paper_id,manual_decision columns"),
):
    """Import manual review decisions from CSV format.
    
    CSV format expected:
    paper_id,manual_decision,review_notes
    abc123,include,Relevant to research question
    def456,exclude,Not relevant
    """
    import csv
    from io import StringIO
    
    app_state = get_app_state()
    results = app_state["results"]
    
    reader = csv.DictReader(StringIO(decisions))
    
    result_map = {r.paper_id: i for i, r in enumerate(results)}
    
    updated = []
    not_found = []
    invalid_decision = []
    
    for row in reader:
        paper_id = row.get("paper_id", "").strip()
        manual_decision = row.get("manual_decision", "").strip().lower()
        review_notes = row.get("review_notes", row.get("notes", "")).strip()
        
        if not paper_id:
            continue
        
        if paper_id not in result_map:
            not_found.append(paper_id)
            continue
        
        if manual_decision not in ["include", "exclude"]:
            invalid_decision.append({"paper_id": paper_id, "decision": manual_decision})
            continue
        
        idx = result_map[paper_id]
        
        decision = ScreeningDecision.INCLUDE if manual_decision == "include" else ScreeningDecision.EXCLUDE
        results[idx].decision = decision
        results[idx].screened_by = ScreeningMethod.MANUAL
        results[idx].reason = review_notes
        results[idx].notes = review_notes
        results[idx].reviewed_at = str(datetime.now().isoformat())
        
        updated.append(paper_id)
    
    return {
        "status": "import_complete",
        "updated_count": len(updated),
        "not_found_count": len(not_found),
        "invalid_decision_count": len(invalid_decision),
        "updated": updated,
        "not_found": not_found,
        "invalid_decisions": invalid_decision[:10],
    }


@router.post("/stage2")
async def screen_stage2(
    request: ScreenRequest = Body(default=ScreenRequest()),
):
    """Run Stage 2 (full-text) screening on eligible papers."""
    app_state = get_app_state()
    results = app_state["results"]
    papers = app_state["papers"]
    
    stage_1_included_ids = {
        r.paper_id for r in results 
        if r.phase == ScreeningPhase.TITLE_ABSTRACT 
        and r.decision == ScreeningDecision.INCLUDE
    }
    
    keywords = {}
    if app_state.get("classification_config") and app_state["classification_config"].keywords:
        keywords = {
            "required": app_state["classification_config"].keywords.required or [],
            "optional": app_state["classification_config"].keywords.optional or [],
        }
    
    ranking_weights = RankingWeights()
    if app_state.get("classification_config") and app_state["classification_config"].ranking_weights:
        ranking_weights = app_state["classification_config"].ranking_weights
    
    classifier = SciBERTClassifier(
        model_name="allenai/scibert_scivocab_uncased",
        device="auto",
        backend=BackendType.AUTO,
        keywords=keywords,
        ranking_weights=ranking_weights,
    )
    
    screened_stage2 = []
    for paper in papers:
        if paper.id not in stage_1_included_ids:
            continue
        
        if paper.flagged_reason:
            continue
        
        stage1_result = next((r for r in results if r.paper_id == paper.id), None)
        
        result = classifier.classify_relevance(
            paper=paper,
            include_prompt=request.include_prompt,
            exclude_prompt=request.exclude_prompt,
            threshold=request.threshold,
            phase=ScreeningPhase.FULL_TEXT,
        )
        
        result.stage_1_decision = ScreeningDecision.INCLUDE
        result.stage_1_confidence = stage1_result.confidence if stage1_result else None
        result.stage_1_reviewed_at = stage1_result.reviewed_at if stage1_result else None
        result.progressed_to_stage_2 = True
        result.full_text_retrieved = bool(paper.full_text or paper.full_text_path)
        
        screened_stage2.append(result)
        results.append(result)
    
    included = sum(1 for r in screened_stage2 if r.decision == ScreeningDecision.INCLUDE)
    excluded = sum(1 for r in screened_stage2 if r.decision == ScreeningDecision.EXCLUDE)
    
    classifier.unload()
    
    return {
        "status": "stage2_complete",
        "total_screened": len(screened_stage2),
        "included": included,
        "excluded": excluded,
        "phase": "full_text",
    }
