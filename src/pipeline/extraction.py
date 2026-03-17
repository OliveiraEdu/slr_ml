"""Data extraction for included studies."""
import yaml
from pathlib import Path
from typing import Optional

from src.models.schemas import (
    Paper, ExtractionData, QualityRating, QualityAssessment, MMATScore
)


class ExtractionExtractor:
    """Extract study characteristics from papers using config-based keyword matching."""

    def __init__(self, config_path: str = "config/extraction.yaml"):
        self.config = self._load_config(config_path)
        self.research_focus_keywords = self.config.get("extraction", {}).get("research_focus_keywords", {})
        self.blockchain_platforms = self.config.get("extraction", {}).get("blockchain_platforms", [])
        self.storage_integration = self.config.get("extraction", {}).get("storage_integration", [])
        self.permission_models = self.config.get("extraction", {}).get("permission_models", [])
        self.evaluation_methods = self.config.get("extraction", {}).get("evaluation_methods", [])

    def _load_config(self, config_path: str) -> dict:
        """Load extraction config from YAML file."""
        path = Path(config_path)
        if path.exists():
            with open(path) as f:
                return yaml.safe_load(f) or {}
        return {}

    def extract(self, papers: list[Paper]) -> list[ExtractionData]:
        """Extract data from included papers."""
        extracted = []
        for idx, paper in enumerate(papers, start=1):
            data = self._extract_from_paper(paper, idx)
            extracted.append(data)
        return extracted

    def _extract_from_paper(self, paper: Paper, index: int) -> ExtractionData:
        """Extract data from a single paper."""
        text = f"{paper.title} {paper.abstract or ''} {' '.join(paper.keywords)}".lower()

        research_focus = self._extract_research_focus(text)
        blockchain_platform = self._extract_blockchain_platform(text)
        storage = self._extract_storage_integration(text)
        permission = self._extract_permission_model(text)
        evaluation = self._extract_evaluation_method(text)

        return ExtractionData(
            study_id=f"REV{index:03d}",
            paper_id=paper.id,
            research_focus=research_focus,
            system_name=None,
            blockchain_platform=blockchain_platform,
            storage_integration=storage,
            permission_model=permission,
            provenance_model="None",
            madmp_support="None",
            evaluation_method=evaluation,
            key_findings=None,
            limitations=None,
            quality_score=None,
        )

    def _extract_research_focus(self, text: str) -> str:
        """Extract research focus from text."""
        scores = {}
        for focus, keywords in self.research_focus_keywords.items():
            score = sum(1 for kw in keywords if kw.lower() in text)
            scores[focus] = score

        if scores.get("provenance", 0) > 0 and scores.get("blockchain", 0) > 0:
            return "Provenance; Blockchain"
        elif scores.get("provenance", 0) > 0:
            return "Provenance"
        elif scores.get("blockchain", 0) > 0:
            return "Blockchain"
        return "Other"

    def _extract_blockchain_platform(self, text: str) -> str:
        """Extract blockchain platform from text."""
        platforms_found = []
        text_lower = text.lower()

        platform_keywords = {
            "Hyperledger Fabric": ["hyperledger fabric"],
            "Hyperledger": ["hyperledger"],
            "Ethereum": ["ethereum"],
            "Corda": ["corda"],
            "Solana": ["solana"],
            "Polygon": ["polygon"],
        }

        for platform, keywords in platform_keywords.items():
            if any(kw in text_lower for kw in keywords):
                platforms_found.append(platform)

        if not platforms_found:
            return "Not specified"
        return "; ".join(platforms_found)

    def _extract_storage_integration(self, text: str) -> str:
        """Extract storage integration type."""
        text_lower = text.lower()

        if "ipfs" in text_lower and "blockchain" in text_lower:
            return "IPFS + blockchain"
        elif "ipfs" in text_lower:
            return "IPFS"
        elif "external database" in text_lower or "external db" in text_lower:
            return "External DB"
        elif "hybrid" in text_lower:
            return "Hybrid"
        return "Not specified"

    def _extract_permission_model(self, text: str) -> str:
        """Extract permission model."""
        text_lower = text.lower()

        if "permissioned" in text_lower and "permissionless" in text_lower:
            return "Hybrid"
        elif "permissioned" in text_lower:
            return "Permissioned"
        elif "permissionless" in text_lower or "public" in text_lower:
            return "Permissionless"
        return "Not specified"

    def _extract_evaluation_method(self, text: str) -> str:
        """Extract evaluation method."""
        text_lower = text.lower()

        if "experiment" in text_lower or "empirical" in text_lower:
            return "Experiment"
        elif "case study" in text_lower:
            return "Case study"
        elif "simulation" in text_lower:
            return "Simulation"
        elif "benchmark" in text_lower or "performance evaluation" in text_lower:
            return "Benchmark"
        return "Not clear"


class QualityAssessor:
    """Quality assessment using MMAT criteria from config."""

    def __init__(self, config_path: str = "config/extraction.yaml"):
        self.config = self._load_config(config_path)
        self.mmat_criteria = self.config.get("quality_assessment", {}).get("mmat_criteria", {})
        self.rating_thresholds = self.config.get("quality_assessment", {}).get("rating_thresholds", {})

    def _load_config(self, config_path: str) -> dict:
        """Load extraction config from YAML file."""
        path = Path(config_path)
        if path.exists():
            with open(path) as f:
                return yaml.safe_load(f) or {}
        return {}

    def assess(self, papers: list[Paper]) -> list[QualityAssessment]:
        """Assess quality for included papers."""
        assessments = []
        for paper in papers:
            assessment = self._assess_paper(paper)
            assessments.append(assessment)
        return assessments

    def _assess_paper(self, paper: Paper) -> QualityAssessment:
        """Assess quality of a single paper."""
        text = f"{paper.title} {paper.abstract or ''}".lower()

        mmat = MMATScore()
        yes_count = 0

        for criterion, keywords in self.mmat_criteria.items():
            found = any(kw.lower() in text for kw in keywords)
            setattr(mmat, criterion, "Yes" if found else "Can't tell")
            if found:
                yes_count += 1

        overall_score = yes_count / 5.0 if self.mmat_criteria else 0

        rating = self._calculate_rating(overall_score)

        return QualityAssessment(
            paper_id=paper.id,
            mmat_score=mmat,
            rating=rating,
            overall_score=overall_score,
            notes=None,
        )

    def _calculate_rating(self, score: float) -> QualityRating:
        """Calculate quality rating based on score."""
        thresholds = self.rating_thresholds
        if score >= thresholds.get("excellent", 0.8):
            return QualityRating.EXCELLENT
        elif score >= thresholds.get("good", 0.6):
            return QualityRating.GOOD
        elif score >= thresholds.get("acceptable", 0.4):
            return QualityRating.ACCEPTABLE
        elif score >= thresholds.get("poor", 0.2):
            return QualityRating.POOR
        else:
            return QualityRating.VERY_POOR
