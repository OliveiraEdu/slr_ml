"""Enhanced screening router with active learning and fine-tuning."""
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from src.models.schemas import Paper, ScreeningDecision
from src.ml.keyword_filter import KeywordFilter, create_keyword_filter
from src.ml.active_learning import (
    ActiveLearningPipeline,
    CitationRanker,
    CertaintyBasedScreen,
    ActiveLearningConfig,
    SamplingStrategy,
    create_active_learning_pipeline,
)
from src.ml.fine_tuning import SciBERTFineTuner, FineTuningConfig, create_fine_tuner
from src.ml.snowballing import SnowballingSearcher, SnowballingConfig, create_snowballer

router = APIRouter(prefix="/enhanced", tags=["enhanced"])


class KeywordFilterRequest(BaseModel):
    papers: Optional[list[Paper]] = None
    paper_ids: Optional[list[str]] = None
    keywords_config: Optional[dict] = None


class KeywordFilterResponse(BaseModel):
    total: int
    passed: int
    failed: int
    pass_rate: float
    sample_passed: list[dict] = Field(default_factory=list)
    sample_failed: list[dict] = Field(default_factory=list)


@router.post("/filter/keywords", response_model=KeywordFilterResponse)
async def filter_papers_keywords(request: KeywordFilterRequest):
    """Filter papers using keyword-based pre-screening.
    
    This endpoint pre-screens papers based on keyword matching:
    - Required keywords: All must be present
    - Relevant keywords: Boost score
    - Exclusion keywords: Immediate exclude
    """
    if not request.papers:
        raise HTTPException(status_code=400, detail="No papers provided")
    
    keywords_config = request.keywords_config or {
        "keywords": {
            "required": ["blockchain", "maDMP", "data management plan", "provenance"],
            "relevant": ["FAIR", "metadata", "smart contract", "IPFS"],
            "exclusion": ["supply chain", "finance", "opinion paper"],
        }
    }
    
    kf = create_keyword_filter(keywords_config)
    result = kf.batch_filter(request.papers)
    
    return KeywordFilterResponse(
        total=result["total"],
        passed=result["passed"],
        failed=result["failed"],
        pass_rate=result["pass_rate"],
        sample_passed=result["papers"][:10],
        sample_failed=result["filtered"][:10],
    )


class ActiveLearningRequest(BaseModel):
    papers: list[Paper]
    initial_labels: list[dict] = Field(default_factory=list)
    config: Optional[dict] = None


class ActiveLearningResponse(BaseModel):
    statistics: dict
    samples_for_review: list[dict]
    training_data_count: int


@router.post("/active-learning", response_model=ActiveLearningResponse)
async def run_active_learning(request: ActiveLearningRequest):
    """Run active learning to select most informative papers for manual review.
    
    Active learning iteratively:
    1. Selects papers most uncertain to the model
    2. Presents them for manual labeling
    3. Retrains with new labels
    """
    config = request.config or {}
    al_config = ActiveLearningConfig(
        initial_training_size=config.get("initial_training_size", 50),
        batch_size=config.get("batch_size", 20),
        max_iterations=config.get("max_iterations", 10),
        confidence_threshold=config.get("confidence_threshold", 0.15),
        sampling_strategy=SamplingStrategy(config.get("sampling_strategy", "least_confident")),
    )
    
    pipeline = ActiveLearningPipeline(config=al_config)
    
    initial_labels = [
        (label["paper_id"], ScreeningDecision(label["decision"]))
        for label in request.initial_labels
        if "paper_id" in label and "decision" in label
    ]
    
    if initial_labels:
        pipeline.initialize_training_set(request.papers, initial_labels)
    
    samples = pipeline.select_samples_for_review(request.papers, [])
    
    samples_for_review = [
        {
            "paper_id": p.id,
            "title": p.title,
            "authors": p.authors[:3] if p.authors else [],
            "year": p.year,
            "doi": p.doi,
        }
        for p in samples
    ]
    
    return ActiveLearningResponse(
        statistics=pipeline.get_statistics(),
        samples_for_review=samples_for_review,
        training_data_count=len(pipeline.labeled_samples),
    )


class FineTuningRequest(BaseModel):
    texts: list[str]
    labels: list[int]
    eval_texts: Optional[list[str]] = None
    eval_labels: Optional[list[int]] = None
    config: Optional[dict] = None


class FineTuningResponse(BaseModel):
    status: str
    metrics: dict
    model_path: str


@router.post("/fine-tune", response_model=FineTuningResponse)
async def fine_tune_model(request: FineTuningRequest):
    """Fine-tune SciBERT on labeled paper data.
    
    Uses a small set of labeled papers to fine-tune the model
    for improved classification accuracy.
    """
    if len(request.texts) != len(request.labels):
        raise HTTPException(status_code=400, detail="texts and labels must have same length")
    
    if len(request.texts) < 20:
        raise HTTPException(status_code=400, detail="Need at least 20 labeled samples")
    
    config = request.config or {}
    ft_config = FineTuningConfig(
        model_name=config.get("model_name", "allenai/scibert_scivocab_uncased"),
        output_dir=config.get("output_dir", "models/fine_tuned"),
        num_epochs=config.get("num_epochs", 3),
        per_device_batch_size=config.get("per_device_batch_size", 8),
        learning_rate=config.get("learning_rate", 2e-5),
        fp16=config.get("fp16", True),
    )
    
    fine_tuner = SciBERTFineTuner(config=ft_config)
    
    metrics = fine_tuner.train(
        train_texts=request.texts,
        train_labels=request.labels,
        eval_texts=request.eval_texts,
        eval_labels=request.eval_labels,
    )
    
    return FineTuningResponse(
        status="trained",
        metrics=metrics,
        model_path=fine_tuner.config.output_dir,
    )


class SnowballingRequest(BaseModel):
    papers: list[Paper]
    existing_paper_ids: Optional[list[str]] = None
    config: Optional[dict] = None


class SnowballingResponse(BaseModel):
    status: str
    papers_found: int
    papers: list[dict]
    statistics: dict


@router.post("/snowballing", response_model=SnowballingResponse)
async def run_snowballing(request: SnowballingRequest):
    """Run snowballing search to find additional relevant papers.
    
    Backward snowballing: Extracts references from included papers
    Forward snowballing: Finds papers that cite included papers
    """
    config = request.config or {
        "max_depth": 2,
        "max_papers_per_source": 50,
        "include_references": True,
        "include_citations": True,
    }
    
    snow_config = SnowballingConfig(
        max_depth=config.get("max_depth", 2),
        max_papers_per_source=config.get("max_papers_per_source", 50),
        include_references=config.get("include_references", True),
        include_citations=config.get("include_citations", True),
    )
    
    searcher = SnowballingSearcher(config=snow_config)
    
    existing_ids = set(request.existing_paper_ids or [])
    
    found_papers = searcher.search(
        included_papers=request.papers,
        existing_paper_ids=existing_ids,
    )
    
    papers_data = [
        {
            "id": p.id,
            "title": p.title,
            "authors": p.authors[:3] if p.authors else [],
            "year": p.year,
            "doi": p.doi,
            "journal": p.journal,
            "source": p.source,
        }
        for p in found_papers
    ]
    
    return SnowballingResponse(
        status="completed",
        papers_found=len(found_papers),
        papers=papers_data,
        statistics=searcher.get_statistics(),
    )


class CertaintyScreeningRequest(BaseModel):
    results: list[dict]
    exclude_confidence: float = 0.80
    include_confidence: float = 0.80
    auto_exclude: bool = True
    auto_include: bool = True


class CertaintyScreeningResponse(BaseModel):
    auto_decisions: int
    need_review: int
    breakdown: dict


@router.post("/certainty-screening", response_model=CertaintyScreeningResponse)
async def apply_certainty_screening(request: CertaintyScreeningRequest):
    """Apply certainty-based automated screening decisions.
    
    Automatically makes decisions for papers with high confidence:
    - High confidence exclusion: Papers clearly not relevant
    - High confidence inclusion: Papers clearly relevant
    """
    from src.models.schemas import ScreeningResult, ConfidenceBand
    
    screen = CertaintyBasedScreen(
        exclude_confidence=request.exclude_confidence,
        include_confidence=request.include_confidence,
        auto_exclude=request.auto_exclude,
        auto_include=request.auto_include,
    )
    
    results = []
    for r in request.results:
        result = ScreeningResult(
            paper_id=r["paper_id"],
            relevance_score=r.get("relevance_score", 0.5),
            confidence=r.get("confidence", 0.0),
            decision=ScreeningDecision(r.get("decision", "uncertain")),
        )
        results.append(result)
    
    auto_decisions, need_review = screen.apply_certainty_decisions(results)
    
    breakdown = {
        "auto_included": sum(1 for r in auto_decisions if r.decision == ScreeningDecision.INCLUDE),
        "auto_excluded": sum(1 for r in auto_decisions if r.decision == ScreeningDecision.EXCLUDE),
        "high_confidence": len(auto_decisions),
        "needs_manual_review": len(need_review),
    }
    
    return CertaintyScreeningResponse(
        auto_decisions=len(auto_decisions),
        need_review=len(need_review),
        breakdown=breakdown,
    )


class RankingRequest(BaseModel):
    papers: list[Paper]
    n: int = 50
    min_citations: int = 0
    include_threshold: float = 0.0


class RankingResponse(BaseModel):
    ranked_papers: list[dict]
    statistics: dict


@router.post("/rank/citations", response_model=RankingResponse)
async def rank_by_citations(request: RankingRequest):
    """Rank papers by citation-based relevance.
    
    Prioritizes papers with:
    - Higher citation counts
    - More recent publications
    - Combined relevance score
    """
    ranker = CitationRanker(min_citations=request.min_citations)
    
    ranked = ranker.rank_papers(request.papers)
    top_papers = ranker.get_top_papers(
        request.papers,
        n=request.n,
        include_threshold=request.include_threshold,
    )
    
    papers_data = [
        {
            "paper_id": p.id,
            "title": p.title,
            "authors": p.authors[:3] if p.authors else [],
            "year": p.year,
            "doi": p.doi,
            "citations": getattr(p, "citations", 0) or 0,
            "journal": p.journal,
        }
        for p in top_papers
    ]
    
    citations = [getattr(p, "citations", 0) or 0 for p in request.papers]
    
    return RankingResponse(
        ranked_papers=papers_data,
        statistics={
            "total_papers": len(request.papers),
            "top_n": len(top_papers),
            "avg_citations": sum(citations) / len(citations) if citations else 0,
            "max_citations": max(citations) if citations else 0,
            "papers_with_citations": sum(1 for c in citations if c > 0),
        },
    )


class EnhancedScreeningRequest(BaseModel):
    papers: list[Paper]
    strategy: str = "full"
    keywords_config: Optional[dict] = None
    active_learning_config: Optional[dict] = None
    snowballing_config: Optional[dict] = None


class EnhancedScreeningResponse(BaseModel):
    status: str
    phases_completed: list[str]
    results: dict


@router.post("/screening/full", response_model=EnhancedScreeningResponse)
async def run_enhanced_screening(request: EnhancedScreeningRequest):
    """Run full enhanced screening pipeline.
    
    Combines:
    1. Keyword pre-filtering
    2. Active learning for uncertain papers
    3. Citation-based ranking
    4. Snowballing for included papers
    """
    phases_completed = []
    results = {}
    
    if request.keywords_config:
        kf = create_keyword_filter(request.keywords_config)
        filter_result = kf.batch_filter(request.papers)
        phases_completed.append("keyword_filtering")
        results["keyword_filter"] = {
            "passed": filter_result["passed"],
            "failed": filter_result["failed"],
            "pass_rate": filter_result["pass_rate"],
        }
        request.papers = [Paper(**p) for p in filter_result.get("papers", []) if isinstance(p, dict)]
    
    if request.active_learning_config:
        phases_completed.append("active_learning")
        results["active_learning"] = {
            "status": "configured",
            "config": request.active_learning_config,
        }
    
    if request.snowballing_config and request.strategy == "full":
        snow_config = request.snowballing_config
        snow_searcher = create_snowballer(snow_config)
        phases_completed.append("snowballing")
        results["snowballing"] = {
            "status": "configured",
            "config": snow_config,
        }
    
    phases_completed.append("screening")
    
    return EnhancedScreeningResponse(
        status="completed",
        phases_completed=phases_completed,
        results=results,
    )
