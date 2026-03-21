"""Dual screening workflow with inter-rater reliability calculation."""
from dataclasses import dataclass
from typing import Optional
from enum import Enum
import math


class ICRLevel(str, Enum):
    SLIGHT = "slight"
    FAIR = "fair"
    MODERATE = "moderate"
    SUBSTANTIAL = "substantial"
    ALMOST_PERFECT = "almost perfect"


@dataclass
class InterRaterReliability:
    """Inter-rater reliability metrics."""
    cohens_kappa: float
    percent_agreement: float
    icc: float
    kappa_level: ICRLevel
    disagreements: list[dict]
    
    def is_substantial(self) -> bool:
        """Check if kappa indicates substantial agreement."""
        return self.cohens_kappa >= 0.61
    
    def to_dict(self) -> dict:
        return {
            "cohens_kappa": round(self.cohens_kappa, 4),
            "percent_agreement": round(self.percent_agreement, 4),
            "icc": round(self.icc, 4),
            "kappa_level": self.kappa_level.value,
            "interpretation": self._interpret(),
            "disagreements_count": len(self.disagreements),
            "can_proceed": self.is_substantial() or len(self.disagreements) <= 3,
        }
    
    def _interpret(self) -> str:
        if self.cohens_kappa < 0:
            return "Poor - worse than chance"
        elif self.cohens_kappa < 0.20:
            return f"{ICRLevel.SLIGHT.value.title()} agreement"
        elif self.cohens_kappa < 0.40:
            return f"{ICRLevel.FAIR.value.title()} agreement"
        elif self.cohens_kappa < 0.60:
            return f"{ICRLevel.MODERATE.value.title()} agreement"
        elif self.cohens_kappa < 0.80:
            return f"{ICRLevel.SUBSTANTIAL.value.title()} agreement"
        else:
            return f"{ICRLevel.ALMOST_PERFECT.value.title()} agreement"


class DualScreeningManager:
    """Manage dual independent screening workflow."""
    
    def __init__(self, conflict_resolution: str = "consensus"):
        self.conflict_resolution = conflict_resolution  # consensus, third_reviewer, include
        self.screenings: dict[str, dict] = {}
        self.conflicts: list[dict] = []
    
    def add_screening(
        self,
        paper_id: str,
        reviewer_id: str,
        decision: str,
        confidence: float,
        notes: Optional[str] = None,
    ):
        """Add screening result from a reviewer."""
        if paper_id not in self.screenings:
            self.screenings[paper_id] = {}
        self.screenings[paper_id][reviewer_id] = {
            "decision": decision,
            "confidence": confidence,
            "notes": notes,
        }
    
    def resolve_conflicts(self) -> dict[str, str]:
        """Resolve conflicts using configured strategy."""
        resolved = {}
        for paper_id, reviewers in self.screenings.items():
            if len(reviewers) < 2:
                continue
            
            decisions = [r["decision"] for r in reviewers.values()]
            if decisions[0] == decisions[1]:
                resolved[paper_id] = decisions[0]
            else:
                conflict = {
                    "paper_id": paper_id,
                    "reviewer_1": list(reviewers.values())[0],
                    "reviewer_2": list(reviewers.values())[1],
                    "strategy": self.conflict_resolution,
                }
                self.conflicts.append(conflict)
                
                if self.conflict_resolution == "include":
                    resolved[paper_id] = "include"
                elif self.conflict_resolution == "exclude":
                    resolved[paper_id] = "exclude"
        
        return resolved
    
    def calculate_kappa(
        self,
        reviewer_1_results: dict[str, str],
        reviewer_2_results: dict[str, str],
    ) -> InterRaterReliability:
        """Calculate Cohen's Kappa between two reviewers."""
        n = len(reviewer_1_results)
        if n == 0:
            return InterRaterReliability(0, 0, 0, ICRLevel.SLIGHT, [])
        
        categories = set(reviewer_1_results.values()) | set(reviewer_2_results.values())
        
        agreements = sum(
            1 for pid in reviewer_1_results 
            if pid in reviewer_2_results 
            and reviewer_1_results[pid] == reviewer_2_results[pid]
        )
        percent_agreement = agreements / n
        
        Po = percent_agreement
        
        Pe = 0.0
        for cat in categories:
            p1 = sum(1 for d in reviewer_1_results.values() if d == cat) / n
            p2 = sum(1 for d in reviewer_2_results.values() if d == cat) / n
            Pe += p1 * p2
        
        kappa = (Po - Pe) / (1 - Pe) if Pe < 1 else 1.0
        
        if kappa < 0:
            kappa_level = ICRLevel.SLIGHT
        elif kappa < 0.20:
            kappa_level = ICRLevel.SLIGHT
        elif kappa < 0.40:
            kappa_level = ICRLevel.FAIR
        elif kappa < 0.60:
            kappa_level = ICRLevel.MODERATE
        elif kappa < 0.80:
            kappa_level = ICRLevel.SUBSTANTIAL
        else:
            kappa_level = ICRLevel.ALMOST_PERFECT
        
        disagreements = [
            {
                "paper_id": pid,
                "reviewer_1_decision": reviewer_1_results[pid],
                "reviewer_2_decision": reviewer_2_results[pid],
            }
            for pid in reviewer_1_results
            if pid in reviewer_2_results 
            and reviewer_1_results[pid] != reviewer_2_results[pid]
        ]
        
        icc = self._calculate_icc(reviewer_1_results, reviewer_2_results)
        
        return InterRaterReliability(
            cohens_kappa=kappa,
            percent_agreement=percent_agreement,
            icc=icc,
            kappa_level=kappa_level,
            disagreements=disagreements,
        )
    
    def _calculate_icc(
        self,
        results_1: dict[str, float],
        results_2: dict[str, float],
    ) -> float:
        """Calculate Intraclass Correlation Coefficient."""
        common_ids = set(results_1.keys()) & set(results_2.keys())
        if len(common_ids) < 2:
            return 0.0
        
        scores_1 = [results_1[pid] for pid in common_ids]
        scores_2 = [results_2[pid] for pid in common_ids]
        
        mean_1 = sum(scores_1) / len(scores_1)
        mean_2 = sum(scores_2) / len(scores_2)
        grand_mean = (mean_1 + mean_2) / 2
        
        between = sum((s1 - grand_mean) ** 2 + (s2 - grand_mean) ** 2 
                      for s1, s2 in zip(scores_1, scores_2))
        
        within = sum((s1 - mean_1) ** 2 + (s2 - mean_2) ** 2 
                     for s1, s2 in zip(scores_1, scores_2))
        
        n = len(common_ids)
        k = 2
        
        MS_between = between / ((n - 1) * k)
        MS_within = within / (n * (k - 1))
        
        icc = (MS_between - MS_within) / (MS_between + (k - 1) * MS_within)
        return max(0.0, icc)
