"""Advanced screening router - dual screening, sensitivity analysis, and completeness tracking."""
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.pipeline.dual_screening import DualScreeningManager, InterRaterReliability
from src.pipeline.sensitivity_analysis import SensitivityAnalyzer, PublicationBiasAnalyzer
from src.pipeline.completeness import WorkflowCompleteness, PRISMACompletenessChecker
from src.pipeline.risk_of_bias import RiskOfBiasAssessor

router = APIRouter(prefix="/advanced", tags=["advanced"])


class DualScreeningRequest(BaseModel):
    paper_id: str
    reviewer_id: str
    decision: str
    confidence: float
    notes: Optional[str] = None


class KappaRequest(BaseModel):
    reviewer_1_results: dict[str, str]
    reviewer_2_results: dict[str, str]


class RiskOfBiasRequest(BaseModel):
    study_type: str = "nrt"


def get_app_state():
    from src.api.main import app_state
    return app_state


@router.post("/dual-screening/add")
async def add_dual_screening(request: DualScreeningRequest):
    """Add a screening result from a reviewer."""
    app_state = get_app_state()
    
    if "dual_screening" not in app_state:
        app_state["dual_screening"] = {
            "manager": DualScreeningManager(),
            "reviewers": {},
        }
    
    manager = app_state["dual_screening"]["manager"]
    manager.add_screening(
        paper_id=request.paper_id,
        reviewer_id=request.reviewer_id,
        decision=request.decision,
        confidence=request.confidence,
        notes=request.notes,
    )
    
    if request.reviewer_id not in app_state["dual_screening"]["reviewers"]:
        app_state["dual_screening"]["reviewers"][request.reviewer_id] = []
    app_state["dual_screening"]["reviewers"][request.reviewer_id].append(request.paper_id)
    
    return {
        "status": "added",
        "paper_id": request.paper_id,
        "reviewer_id": request.reviewer_id,
        "total_reviews_by_reviewer": len(app_state["dual_screening"]["reviewers"][request.reviewer_id]),
    }


@router.post("/dual-screening/kappa")
async def calculate_kappa(request: KappaRequest):
    """Calculate Cohen's Kappa between two reviewers."""
    manager = DualScreeningManager()
    
    kappa_result = manager.calculate_kappa(
        reviewer_1_results=request.reviewer_1_results,
        reviewer_2_results=request.reviewer_2_results,
    )
    
    return kappa_result.to_dict()


@router.get("/dual-screening/conflicts")
async def get_conflicts():
    """Get unresolved conflicts between reviewers."""
    app_state = get_app_state()
    
    if "dual_screening" not in app_state:
        return {"conflicts": [], "message": "No dual screening performed"}
    
    manager = app_state["dual_screening"]["manager"]
    return {
        "conflicts": manager.conflicts,
        "resolved": len(manager.screenings) - len(manager.conflicts),
    }


@router.post("/sensitivity/threshold")
async def analyze_threshold_sensitivity():
    """Analyze sensitivity of inclusion to threshold changes."""
    app_state = get_app_state()
    papers = app_state.get("papers", [])
    results = app_state.get("results", [])
    
    if not results:
        raise HTTPException(status_code=400, detail="No screening results available")
    
    scores = {r.paper_id: r.relevance_score for r in results}
    
    analyzer = SensitivityAnalyzer(min_threshold=0.2, max_threshold=0.8, step=0.05)
    analysis = analyzer.analyze_threshold_sensitivity(papers, scores)
    
    return analysis.to_dict()


@router.get("/sensitivity/confidence")
async def analyze_confidence_sensitivity():
    """Analyze sensitivity to confidence thresholds."""
    app_state = get_app_state()
    results = app_state.get("results", [])
    
    if not results:
        raise HTTPException(status_code=400, detail="No screening results available")
    
    results_dict = [r.model_dump() for r in results]
    
    analyzer = SensitivityAnalyzer()
    analysis = analyzer.analyze_confidence_sensitivity(results_dict)
    
    return analysis


@router.get("/risk-of-bias/{paper_id}")
async def assess_risk_of_bias(paper_id: str, study_type: str = "nrt"):
    """Assess risk of bias for a specific paper."""
    app_state = get_app_state()
    
    paper = next((p for p in app_state.get("papers", []) if p.id == paper_id), None)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    
    assessor = RiskOfBiasAssessor()
    paper_dict = paper.model_dump()
    assessment = assessor.assess_study(paper_dict, study_type)
    
    return assessment.to_dict()


@router.post("/risk-of-bias/batch")
async def batch_risk_of_bias(request: RiskOfBiasRequest):
    """Assess risk of bias for all included papers."""
    app_state = get_app_state()
    results = app_state.get("results", [])
    papers = app_state.get("papers", [])
    
    included_ids = {r.paper_id for r in results if r.decision.value == "include"}
    included_papers = [p for p in papers if p.id in included_ids]
    
    if not included_papers:
        raise HTTPException(status_code=400, detail="No included papers found")
    
    assessor = RiskOfBiasAssessor()
    assessments = []
    
    for paper in included_papers:
        paper_dict = paper.model_dump()
        assessment = assessor.assess_study(paper_dict, request.study_type)
        assessments.append(assessment.to_dict())
    
    rob_distribution = {
        "low": sum(1 for a in assessments if a["overall_rob"] == "low"),
        "moderate": sum(1 for a in assessments if a["overall_rob"] == "moderate"),
        "high": sum(1 for a in assessments if a["overall_rob"] == "high"),
        "critical": sum(1 for a in assessments if a["overall_rob"] == "critical"),
    }
    
    return {
        "total_assessed": len(assessments),
        "rob_distribution": rob_distribution,
        "assessments": assessments,
    }


@router.get("/completeness")
async def get_completeness():
    """Get workflow completeness and PRISMA 2020 readiness."""
    app_state = get_app_state()
    
    completeness = WorkflowCompleteness(
        import_status=app_state.get("import_status", {}),
        screening_status=app_state.get("screening_status", {}),
        extraction_status={"papers_extracted": len(app_state.get("extraction_data", []))},
        quality_status={"papers_assessed": len(app_state.get("quality_data", []))},
        checklist_status={"completion_rate": app_state.get("prisma_checklist", {}).get("completeness_score", 0)},
    )
    
    checker = PRISMACompletenessChecker()
    requirements = checker.check_requirements(completeness)
    
    return {
        "workflow_completeness": completeness.to_dict(),
        "prisma_requirements": requirements,
    }


@router.get("/readiness")
async def get_world_class_readiness():
    """Assess world-class PRISMA 2020 readiness."""
    app_state = get_app_state()
    
    completeness = WorkflowCompleteness(
        import_status=app_state.get("import_status", {}),
        screening_status=app_state.get("screening_status", {}),
        extraction_status={"papers_extracted": len(app_state.get("extraction_data", []))},
        quality_status={"papers_assessed": len(app_state.get("quality_data", []))},
        checklist_status={"completion_rate": app_state.get("prisma_checklist", {}).get("completeness_score", 0)},
        dual_screening_status={"kappa_calculated": False},
    )
    
    return completeness.get_world_class_readiness()
