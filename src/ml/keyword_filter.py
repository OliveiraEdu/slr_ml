"""Keyword-based pre-filter for SLR screening.

This module provides keyword filtering to pre-screen papers before ML classification,
reducing noise and improving screening efficiency.
"""
import re
from typing import Optional

from src.models.schemas import Paper


class KeywordFilter:
    """Keyword-based filter for SLR paper screening.
    
    Implements a multi-tier keyword matching system:
    - Required keywords: All must be present (AND logic)
    - Relevant keywords: Any should be present (OR logic)  
    - Exclusion keywords: Any present = immediate exclude
    
    Scoring:
    - Required match: +0.5
    - Relevant match: +0.35 (per keyword, normalized)
    - Exclusion match: -0.15 (per keyword)
    - Compound phrase boost: +0.05
    """

    def __init__(
        self,
        required_keywords: Optional[list[str]] = None,
        relevant_keywords: Optional[list[str]] = None,
        exclusion_keywords: Optional[list[str]] = None,
        required_match_all: bool = True,
    ):
        self.required_keywords = [k.lower() for k in (required_keywords or [])]
        self.relevant_keywords = [k.lower() for k in (relevant_keywords or [])]
        self.exclusion_keywords = [k.lower() for k in (exclusion_keywords or [])]
        self.required_match_all = required_match_all

    def filter_paper(self, paper: Paper) -> tuple[bool, float, dict]:
        """Filter a paper based on keyword matching.
        
        Args:
            paper: Paper to filter
            
        Returns:
            Tuple of (passes_filter, score, details)
        """
        text = self._prepare_text(paper).lower()
        details = {
            "required_matches": [],
            "required_missing": [],
            "relevant_matches": [],
            "exclusion_matches": [],
        }
        
        has_exclusion = self._check_exclusions(text, details)
        if has_exclusion:
            details["exclusion_penalty"] = min(len(details["exclusion_matches"]) * 0.15, 0.5)
            return False, 0.0, details
        
        required_pass = self._check_required(text, details)
        if not required_pass:
            details["required_penalty"] = 0.5
            return False, 0.0, details
        
        relevant_score = self._calculate_relevant_score(text, details)
        required_score = self._calculate_required_score(text, details)
        compound_boost = self._calculate_compound_boost(text)
        
        score = (required_score * 0.5) + (relevant_score * 0.35) + compound_boost
        score = max(0.0, min(1.0, score))
        
        return True, score, details

    def _check_exclusions(self, text: str, details: dict) -> bool:
        """Check for exclusion keywords."""
        for kw in self.exclusion_keywords:
            if kw in text:
                details["exclusion_matches"].append(kw)
        return len(details["exclusion_matches"]) > 0

    def _check_required(self, text: str, details: dict) -> bool:
        """Check if required keywords are present."""
        if not self.required_keywords:
            return True
            
        matched = []
        missing = []
        
        for kw in self.required_keywords:
            if kw in text:
                matched.append(kw)
            else:
                missing.append(kw)
        
        details["required_matches"] = matched
        details["required_missing"] = missing
        
        if self.required_match_all:
            return len(missing) == 0
        else:
            return len(matched) > 0

    def _calculate_required_score(self, text: str, details: dict) -> float:
        """Calculate score based on required keyword matches."""
        if not self.required_keywords:
            return 1.0
        
        matches = details.get("required_matches", [])
        return min(len(matches) / len(self.required_keywords), 1.0)

    def _calculate_relevant_score(self, text: str, details: dict) -> float:
        """Calculate score based on relevant keyword matches."""
        if not self.relevant_keywords:
            return 0.5
        
        matches = []
        for kw in self.relevant_keywords:
            if kw in text:
                count = min(text.count(kw), 3)
                matches.extend([kw] * count)
        
        details["relevant_matches"] = list(set(matches))
        
        if not matches:
            return 0.0
        
        unique_matches = len(set(matches))
        return min(unique_matches / len(self.relevant_keywords), 1.0)

    def _calculate_compound_boost(self, text: str) -> float:
        """Calculate boost for compound phrases (more specific matches)."""
        boost = 0.0
        all_keywords = self.required_keywords + self.relevant_keywords
        
        for kw in all_keywords:
            if ('-' in kw or '_' in kw or ' ' in kw) and kw in text:
                boost += 0.05
        
        return min(boost, 0.15)

    def _prepare_text(self, paper: Paper) -> str:
        """Prepare text from paper for keyword matching."""
        parts = []
        if paper.title:
            parts.append(paper.title)
        if paper.abstract:
            parts.append(paper.abstract)
        if paper.keywords:
            parts.extend(paper.keywords)
        
        text = " ".join(parts)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def batch_filter(self, papers: list[Paper]) -> dict:
        """Filter multiple papers and return statistics.
        
        Returns:
            Dictionary with filter results and statistics
        """
        passed = []
        failed = []
        
        for paper in papers:
            passes, score, details = self.filter_paper(paper)
            paper_data = {
                "paper_id": paper.id,
                "title": paper.title,
                "score": score,
                "details": details,
            }
            if passes:
                passed.append(paper_data)
            else:
                failed.append(paper_data)
        
        return {
            "total": len(papers),
            "passed": len(passed),
            "failed": len(failed),
            "pass_rate": len(passed) / len(papers) if papers else 0,
            "papers": passed,
            "filtered": failed,
        }


def create_keyword_filter(config: dict) -> KeywordFilter:
    """Create KeywordFilter from configuration dictionary."""
    keywords = config.get("keywords", {})
    
    return KeywordFilter(
        required_keywords=keywords.get("required", []),
        relevant_keywords=keywords.get("relevant", []),
        exclusion_keywords=keywords.get("exclusion", []),
        required_match_all=True,
    )
