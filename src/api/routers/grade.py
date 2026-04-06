"""GRADE router - handles evidence quality assessment."""
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.pipeline.grade_assessment import (
    GRADEAssessment, GRADEProfiler, GRADELevel, RecommendationStrength,
    create_grade_assessment
)

router = APIRouter(prefix="/grade", tags=["grade"])


def get_app_state():
    from src.api.main import app_state
    return app_state


class GRADEAssessmentRequest(BaseModel):
    study_id: str
    outcome: str
    risk_of_bias: bool = False
    imprecision: bool = False
    indirectness: bool = False
    inconsistency: bool = False
    publication_bias: bool = False


class GRADEBatchRequest(BaseModel):
    assessments: list[GRADEAssessmentRequest]


class GRADERecommendationRequest(BaseModel):
    study_id: str
    outcome: str
    benefit_magnitude: str = "moderate"
    values_clarity: str = "clear"
    resources: str = "reasonable"


@router.post("/assess")
async def assess_evidence_quality(
    study_id: str,
    outcome: str,
    risk_of_bias: bool = False,
    imprecision: bool = False,
    indirectness: bool = False,
    inconsistency: bool = False,
    publication_bias: bool = False,
):
    """Perform GRADE assessment for a single study."""
    assessment = create_grade_assessment(
        study_id=study_id,
        outcome=outcome,
        risk_of_bias=risk_of_bias,
        imprecision=imprecision,
        indirectness=indirectness,
        inconsistency=inconsistency,
        publication_bias=publication_bias,
    )
    
    assessment.calculate_evidence_level()
    
    return assessment.to_dict()


@router.post("/batch")
async def batch_grade_assessment(
    assessments: list[GRADEAssessmentRequest],
):
    """Perform GRADE assessment for multiple studies."""
    profiler = GRADEProfiler()
    
    for req in assessments:
        assessment = create_grade_assessment(
            study_id=req.study_id,
            outcome=req.outcome,
            risk_of_bias=req.risk_of_bias,
            imprecision=req.imprecision,
            indirectness=req.indirectness,
            inconsistency=req.inconsistency,
            publication_bias=req.publication_bias,
        )
        assessment.calculate_evidence_level()
        profiler.add_assessment(assessment)
    
    return profiler.get_summary()


@router.get("/summary")
async def get_grade_summary():
    """Get summary of all GRADE assessments."""
    app_state = get_app_state()
    grade_data = app_state.get("grade_data", [])
    
    profiler = GRADEProfiler()
    for data in grade_data:
        assessment = GRADEAssessment(
            study_id=data.get("study_id", ""),
            outcome=data.get("outcome", ""),
        )
        assessment.risk_of_bias.is_concern = data.get("risk_of_bias", False)
        assessment.imprecision.is_concern = data.get("imprecision", False)
        assessment.indirectness.is_concern = data.get("indirectness", False)
        assessment.inconsistency.is_concern = data.get("inconsistency", False)
        assessment.publication_bias.is_concern = data.get("publication_bias", False)
        assessment.calculate_evidence_level()
        profiler.add_assessment(assessment)
    
    summary = profiler.get_summary()
    summary["overall_evidence_level"] = profiler.get_overall_evidence_level().value
    
    return summary


@router.post("/recommendation")
async def calculate_recommendation_strength(
    study_id: str,
    outcome: str,
    risk_of_bias: bool = False,
    imprecision: bool = False,
    indirectness: bool = False,
    inconsistency: bool = False,
    publication_bias: bool = False,
    benefit_magnitude: str = "moderate",
    values_clarity: str = "clear",
    resources: str = "reasonable",
):
    """Calculate recommendation strength based on GRADE assessment."""
    assessment = create_grade_assessment(
        study_id=study_id,
        outcome=outcome,
        risk_of_bias=risk_of_bias,
        imprecision=imprecision,
        indirectness=indirectness,
        inconsistency=inconsistency,
        publication_bias=publication_bias,
    )
    
    assessment.calculate_evidence_level()
    assessment.calculate_recommendation_strength(
        benefitMagnitude=benefit_magnitude,
        values_clarity=values_clarity,
        resources=resources,
    )
    
    return {
        "study_id": study_id,
        "outcome": outcome,
        "evidence_level": assessment.final_evidence_level.value,
        "recommendation_strength": assessment.recommendation_strength.value,
        "explanation": _get_recommendation_explanation(
            assessment.final_evidence_level,
            assessment.recommendation_strength
        ),
    }


def _get_recommendation_explanation(
    level: GRADELevel,
    strength: RecommendationStrength,
) -> str:
    """Get explanation for recommendation."""
    if strength == RecommendationStrength.STRONG:
        return (
            "Strong recommendation: Benefits clearly outweigh risks or vice versa. "
            "The evidence is of high or moderate quality."
        )
    else:
        return (
            "Weak recommendation: Benefits may not clearly outweigh risks. "
            "The evidence is of low or very low quality, or there is uncertainty."
        )


@router.get("/levels")
async def get_grade_levels():
    """Get GRADE evidence levels description."""
    return {
        "levels": [
            {
                "level": "high",
                "description": "We are very confident that the true effect lies close to that of the estimate of the effect.",
                "downgrades": "No serious limitations expected",
            },
            {
                "level": "moderate",
                "description": "We are moderately confident that the true effect is close to the estimate, but there is a possibility it is substantially different.",
                "downgrades": "One serious limitation",
            },
            {
                "level": "low",
                "description": "Our confidence in the effect estimate is limited: the true effect may be substantially different from the estimate.",
                "downgrades": "Two serious limitations",
            },
            {
                "level": "very_low",
                "description": "We have very little confidence in the effect estimate: the true effect is likely to be substantially different from the estimate.",
                "downgrades": "Three or more serious limitations",
            },
        ],
        "domains": [
            {
                "domain": "risk_of_bias",
                "description": "Limitations in study design or execution",
            },
            {
                "domain": "imprecision",
                "description": "Wide confidence intervals or insufficient sample size",
            },
            {
                "domain": "indirectness",
                "description": "Differences in PICO between studies and the review question",
            },
            {
                "domain": "inconsistency",
                "description": "Variation in study results",
            },
            {
                "domain": "publication_bias",
                "description": "Likely unpublished studies affecting results",
            },
        ],
    }
