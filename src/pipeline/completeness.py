"""Completeness tracker for PRISMA 2020 compliance."""
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class ChecklistCompleteness:
    """Track completeness of PRISMA checklist items."""
    section: str
    total_items: int
    completed_items: int
    not_applicable: int
    missing_items: list[dict]
    
    @property
    def completion_rate(self) -> float:
        applicable = self.total_items - self.not_applicable
        if applicable == 0:
            return 1.0
        return self.completed_items / applicable
    
    def to_dict(self) -> dict:
        return {
            "section": self.section,
            "total_items": self.total_items,
            "completed_items": self.completed_items,
            "not_applicable": self.not_applicable,
            "completion_rate": round(self.completion_rate * 100, 1),
            "missing_items": self.missing_items,
        }


@dataclass
class WorkflowCompleteness:
    """Overall workflow completeness tracking."""
    import_status: dict = field(default_factory=dict)
    screening_status: dict = field(default_factory=dict)
    extraction_status: dict = field(default_factory=dict)
    quality_status: dict = field(default_factory=dict)
    risk_of_bias_status: dict = field(default_factory=dict)
    synthesis_status: dict = field(default_factory=dict)
    checklist_status: dict = field(default_factory=dict)
    dual_screening_status: dict = field(default_factory=dict)
    provenance_status: dict = field(default_factory=dict)
    
    def calculate_overall_score(self) -> float:
        """Calculate overall workflow completeness score."""
        weights = {
            "import": 0.10,
            "screening": 0.15,
            "extraction": 0.15,
            "quality": 0.10,
            "risk_of_bias": 0.10,
            "synthesis": 0.10,
            "checklist": 0.20,
            "dual_screening": 0.05,
            "provenance": 0.05,
        }
        
        scores = {}
        
        if self.import_status:
            imported = self.import_status.get("papers_imported", 0)
            scores["import"] = min(1.0, imported / 100)
        
        if self.screening_status:
            screened = self.screening_status.get("screened", 0)
            total = self.import_status.get("papers_imported", 1)
            scores["screening"] = min(1.0, screened / total) if total > 0 else 0
        
        if self.extraction_status:
            scores["extraction"] = 1.0 if self.extraction_status.get("papers_extracted", 0) > 0 else 0
        
        if self.quality_status:
            scores["quality"] = 1.0 if self.quality_status.get("papers_assessed", 0) > 0 else 0
        
        if self.risk_of_bias_status:
            scores["risk_of_bias"] = 1.0 if self.risk_of_bias_status.get("papers_assessed", 0) > 0 else 0
        
        if self.synthesis_status:
            scores["synthesis"] = 1.0 if self.synthesis_status.get("completed", False) else 0
        
        if self.checklist_status:
            scores["checklist"] = self.checklist_status.get("completion_rate", 0) / 100
        
        if self.dual_screening_status:
            scores["dual_screening"] = 1.0 if self.dual_screening_status.get("kappa_calculated", False) else 0
        
        if self.provenance_status:
            scores["provenance"] = 1.0 if self.provenance_status.get("verified", False) else 0
        
        total_weight = sum(weights[k] for k in scores)
        weighted_score = sum(scores.get(k, 0) * weights[k] for k in weights)
        
        return weighted_score / total_weight if total_weight > 0 else 0
    
    def get_world_class_readiness(self) -> dict:
        """Assess world-class PRISMA 2020 readiness."""
        score = self.calculate_overall_score()
        
        requirements = {
            "checklist_100": self.checklist_status.get("completion_rate", 0) >= 100 if self.checklist_status else False,
            "dual_screening": self.dual_screening_status.get("kappa_calculated", False) if self.dual_screening_status else False,
            "full_text_retrieved": self.screening_status.get("full_text_retrieved", 0) > 0 if self.screening_status else False,
            "quality_assessed": self.quality_status.get("papers_assessed", 0) > 0 if self.quality_status else False,
            "rob_assessed": self.risk_of_bias_status.get("papers_assessed", 0) > 0 if self.risk_of_bias_status else False,
            "provenance_tracked": self.provenance_status.get("verified", False) if self.provenance_status else False,
        }
        
        met_count = sum(1 for v in requirements.values() if v)
        
        if score >= 0.9 and met_count >= 5:
            readiness = "WORLD_CLASS"
        elif score >= 0.7 and met_count >= 3:
            readiness = "PUBLICATION_READY"
        elif score >= 0.5:
            readiness = "DRAFT"
        else:
            readiness = "INCOMPLETE"
        
        return {
            "overall_score": round(score * 100, 1),
            "readiness_level": readiness,
            "requirements_met": met_count,
            "total_requirements": len(requirements),
            "requirements": requirements,
            "gaps": [k for k, v in requirements.items() if not v],
            "recommendations": self._get_recommendations(requirements, score),
        }
    
    def _get_recommendations(self, requirements: dict, score: float) -> list[str]:
        """Generate recommendations based on gaps."""
        recommendations = []
        
        if not requirements.get("checklist_100"):
            recommendations.append("Complete PRISMA 2020 checklist - critical for publication")
        if not requirements.get("dual_screening"):
            recommendations.append("Implement dual independent screening with kappa calculation")
        if not requirements.get("full_text_retrieved"):
            recommendations.append("Retrieve full-text for all included papers")
        if not requirements.get("quality_assessed"):
            recommendations.append("Complete quality assessment using MMAT criteria")
        if not requirements.get("rob_assessed"):
            recommendations.append("Conduct risk of bias assessment for included studies")
        if not requirements.get("provenance_tracked"):
            recommendations.append("Enable screening decision provenance tracking")
        
        if score < 0.5:
            recommendations.append("Prioritize completing basic screening workflow")
        elif score < 0.7:
            recommendations.append("Focus on quality assessment and checklist completion")
        
        return recommendations
    
    def to_dict(self) -> dict:
        return {
            "import_status": self.import_status,
            "screening_status": self.screening_status,
            "extraction_status": self.extraction_status,
            "quality_status": self.quality_status,
            "risk_of_bias_status": self.risk_of_bias_status,
            "synthesis_status": self.synthesis_status,
            "checklist_status": self.checklist_status,
            "dual_screening_status": self.dual_screening_status,
            "provenance_status": self.provenance_status,
            "overall_score": round(self.calculate_overall_score() * 100, 1),
            "world_class_readiness": self.get_world_class_readiness(),
        }


class PRISMACompletenessChecker:
    """Check PRISMA 2020 compliance and completeness."""
    
    PRISMA_2020_REQUIREMENTS = {
        "identification": [
            "databases_searched",
            "search_string_reported",
            "date_last_searched",
            "records_after_deduplication",
        ],
        "screening": [
            "screening_criteria_specified",
            "dual_screening_performed",
            "inter_rater_reliability_reported",
            "flow_diagram_included",
        ],
        "included_studies": [
            "study_characteristics_reported",
            "quality_assessment_performed",
            "risk_of_bias_assessed",
        ],
        "synthesis": [
            "methods_of_synthesis_described",
            "sensitivity_analysis_performed",
            "publication_bias_assessed",
        ],
        "reporting": [
            "prisma_checklist_completed",
            "protocol_registration_reported",
            "funding_sources_disclosed",
            "conflicts_of_interest_reported",
        ],
    }
    
    def check_requirements(self, completeness: WorkflowCompleteness) -> dict:
        """Check which PRISMA 2020 requirements are met."""
        results = {}
        
        for section, requirements in self.PRISMA_2020_REQUIREMENTS.items():
            results[section] = {}
            for req in requirements:
                status = self._check_requirement(req, completeness)
                results[section][req] = status
        
        return results
    
    def _check_requirement(self, requirement: str, completeness: WorkflowCompleteness) -> dict:
        """Check a single PRISMA requirement."""
        if "database" in requirement or "search" in requirement:
            return {"met": completeness.import_status.get("databases_searched", 0) > 0, "status": "checked"}
        
        if "deduplication" in requirement:
            return {"met": completeness.import_status.get("duplicates_removed", 0) >= 0, "status": "checked"}
        
        if "dual" in requirement or "inter_rater" in requirement:
            return {
                "met": completeness.dual_screening_status.get("kappa_calculated", False),
                "kappa": completeness.dual_screening_status.get("kappa", 0),
                "status": "checked"
            }
        
        if "quality" in requirement or "risk_of_bias" in requirement:
            if "risk_of_bias" in requirement:
                return {"met": completeness.risk_of_bias_status.get("papers_assessed", 0) > 0, "status": "checked"}
            return {"met": completeness.quality_status.get("papers_assessed", 0) > 0, "status": "checked"}
        
        if "sensitivity" in requirement or "publication_bias" in requirement:
            return {"met": completeness.synthesis_status.get("sensitivity_analysis", False), "status": "checked"}
        
        if "prisma_checklist" in requirement:
            rate = completeness.checklist_status.get("completion_rate", 0)
            return {"met": rate >= 100, "completion_rate": rate, "status": "checked"}
        
        return {"met": False, "status": "not_applicable"}
