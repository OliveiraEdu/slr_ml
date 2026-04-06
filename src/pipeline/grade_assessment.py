"""GRADE assessment framework for evidence quality.

GRADE (Grading of Recommendations, Assessment, Development and Evaluation)
is a systematic approach to rating the quality of evidence in systematic reviews.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class GRADELevel(str, Enum):
    """GRADE evidence quality levels."""
    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"
    VERY_LOW = "very_low"


class RecommendationStrength(str, Enum):
    """GRADE recommendation strength."""
    STRONG = "strong"
    WEAK = "weak"


@dataclass
class GRADEDomain:
    """Individual GRADE domain assessment."""
    domain_name: str
    factor: str
    description: str
    is_concern: bool = False
    
    def to_dict(self) -> dict:
        return {
            "domain_name": self.domain_name,
            "factor": self.factor,
            "description": self.description,
            "is_concern": self.is_concern,
        }


@dataclass
class GRADEAssessment:
    """Complete GRADE assessment for a study/outcome."""
    study_id: str
    outcome: str
    
    risk_of_bias: GRADEDomain = None
    imprecision: GRADEDomain = None
    indirectness: GRADEDomain = None
    inconsistency: GRADEDomain = None
    publication_bias: GRADEDomain = None
    
    initial_evidence_level: GRADELevel = GRADELevel.HIGH
    final_evidence_level: Optional[GRADELevel] = None
    recommendation_strength: Optional[RecommendationStrength] = None
    
    notes: str = ""
    
    def __post_init__(self):
        if self.risk_of_bias is None:
            self.risk_of_bias = GRADEDomain(
                domain_name="risk_of_bias",
                factor="Risk of bias",
                description="Serious limitations in study design or execution",
            )
        if self.imprecision is None:
            self.imprecision = GRADEDomain(
                domain_name="imprecision",
                factor="Imprecision",
                description="Wide confidence intervals or insufficient sample size",
            )
        if self.indirectness is None:
            self.indirectness = GRADEDomain(
                domain_name="indirectness",
                factor="Indirectness",
                description="Populations, interventions, or outcomes differ from PICO",
            )
        if self.inconsistency is None:
            self.inconsistency = GRADEDomain(
                domain_name="inconsistency",
                factor="Inconsistency",
                description="Variation in estimates across studies",
            )
        if self.publication_bias is None:
            self.publication_bias = GRADEDomain(
                domain_name="publication_bias",
                factor="Publication bias",
                description="Likely unpublished studies affecting results",
            )
    
    def calculate_evidence_level(self) -> GRADELevel:
        """Calculate final evidence level based on downgrades."""
        level = self.initial_evidence_level
        
        downgrade_count = sum([
            self.risk_of_bias.is_concern,
            self.imprecision.is_concern,
            self.indirectness.is_concern,
            self.inconsistency.is_concern,
            self.publication_bias.is_concern,
        ])
        
        if downgrade_count >= 3:
            self.final_evidence_level = GRADELevel.VERY_LOW
        elif downgrade_count == 2:
            self.final_evidence_level = GRADELevel.LOW
        elif downgrade_count == 1:
            self.final_evidence_level = GRADELevel.MODERATE
        else:
            self.final_evidence_level = GRADELevel.HIGH
        
        return self.final_evidence_level
    
    def calculate_recommendation_strength(
        self,
        benefitMagnitude: str = "moderate",
        values_clarity: str = "clear",
        resources: str = "reasonable",
    ) -> RecommendationStrength:
        """Calculate recommendation strength based on GRADE factors."""
        if self.final_evidence_level in [GRADELevel.HIGH, GRADELevel.MODERATE]:
            if benefitMagnitude in ["large", "moderate"] and values_clarity == "clear":
                self.recommendation_strength = RecommendationStrength.STRONG
            else:
                self.recommendation_strength = RecommendationStrength.WEAK
        else:
            self.recommendation_strength = RecommendationStrength.WEAK
        
        return self.recommendation_strength
    
    def to_dict(self) -> dict:
        return {
            "study_id": self.study_id,
            "outcome": self.outcome,
            "domains": {
                "risk_of_bias": self.risk_of_bias.to_dict(),
                "imprecision": self.imprecision.to_dict(),
                "indirectness": self.indirectness.to_dict(),
                "inconsistency": self.inconsistency.to_dict(),
                "publication_bias": self.publication_bias.to_dict(),
            },
            "initial_evidence_level": self.initial_evidence_level.value,
            "final_evidence_level": (
                self.final_evidence_level.value if self.final_evidence_level else None
            ),
            "recommendation_strength": (
                self.recommendation_strength.value if self.recommendation_strength else None
            ),
            "notes": self.notes,
        }


class GRADEProfiler:
    """Profile and summarize GRADE assessments across studies."""
    
    def __init__(self):
        self.assessments: list[GRADEAssessment] = []
    
    def add_assessment(self, assessment: GRADEAssessment):
        """Add a GRADE assessment."""
        self.assessments.append(assessment)
    
    def get_summary(self) -> dict:
        """Get summary of all GRADE assessments."""
        if not self.assessments:
            return {
                "total_studies": 0,
                "evidence_levels": {},
                "recommendation_strengths": {},
            }
        
        level_counts = {
            "high": 0,
            "moderate": 0,
            "low": 0,
            "very_low": 0,
        }
        
        strength_counts = {
            "strong": 0,
            "weak": 0,
        }
        
        for assessment in self.assessments:
            if assessment.final_evidence_level:
                level_counts[assessment.final_evidence_level.value] += 1
            
            if assessment.recommendation_strength:
                strength_counts[assessment.recommendation_strength.value] += 1
        
        return {
            "total_studies": len(self.assessments),
            "evidence_levels": level_counts,
            "recommendation_strengths": strength_counts,
            "assessments": [a.to_dict() for a in self.assessments],
        }
    
    def get_overall_evidence_level(self) -> GRADELevel:
        """Calculate overall evidence level (lowest of all)."""
        if not self.assessments:
            return GRADELevel.VERY_LOW
        
        level_order = [GRADELevel.HIGH, GRADELevel.MODERATE, GRADELevel.LOW, GRADELevel.VERY_LOW]
        
        lowest = GRADELevel.HIGH
        for assessment in self.assessments:
            if assessment.final_evidence_level:
                current_idx = level_order.index(assessment.final_evidence_level)
                lowest_idx = level_order.index(lowest)
                if current_idx > lowest_idx:
                    lowest = assessment.final_evidence_level
        
        return lowest


def create_grade_assessment(
    study_id: str,
    outcome: str,
    risk_of_bias: bool = False,
    imprecision: bool = False,
    indirectness: bool = False,
    inconsistency: bool = False,
    publication_bias: bool = False,
) -> GRADEAssessment:
    """Factory function to create GRADE assessment."""
    assessment = GRADEAssessment(
        study_id=study_id,
        outcome=outcome,
    )
    
    assessment.risk_of_bias.is_concern = risk_of_bias
    assessment.imprecision.is_concern = imprecision
    assessment.indirectness.is_concern = indirectness
    assessment.inconsistency.is_concern = inconsistency
    assessment.publication_bias.is_concern = publication_bias
    
    assessment.calculate_evidence_level()
    
    return assessment
