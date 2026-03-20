"""Citation-based ranking and active learning for SLR screening.

This module provides:
- Citation network analysis for ranking papers
- Active learning pipeline for iterative screening
- Certainty-based screening decisions
"""
from dataclasses import dataclass
from enum import Enum
from typing import Optional
import random

from src.models.schemas import Paper, ScreeningResult, ScreeningDecision


class SamplingStrategy(str, Enum):
    LEAST_CONFIDENT = "least_confident"
    MARGIN_SAMPLING = "margin"
    RANDOM = "random"
    UNCERTAINTY = "uncertainty"


@dataclass
class ActiveLearningConfig:
    initial_training_size: int = 50
    batch_size: int = 20
    max_iterations: int = 10
    confidence_threshold: float = 0.15
    sampling_strategy: SamplingStrategy = SamplingStrategy.LEAST_CONFIDENT


class CitationRanker:
    """Rank papers based on citation network analysis."""
    
    def __init__(self, min_citations: int = 0, normalize: bool = True):
        self.min_citations = min_citations
        self.normalize = normalize
    
    def rank_papers(self, papers: list[Paper]) -> list[tuple[Paper, float]]:
        """Rank papers by citation-based score.
        
        Returns:
            List of (paper, score) tuples sorted by score descending
        """
        scored = []
        
        for paper in papers:
            score = self._calculate_citation_score(paper)
            if self.min_citations > 0 and score < self.min_citations:
                continue
            scored.append((paper, score))
        
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored
    
    def _calculate_citation_score(self, paper: Paper) -> float:
        """Calculate normalized citation score."""
        citations = getattr(paper, 'citations', 0) or 0
        
        if citations == 0:
            return 0.0
        
        if self.normalize:
            max_citations = 100
            return min(citations / max_citations, 1.0)
        
        return float(citations)
    
    def get_top_papers(
        self, 
        papers: list[Paper], 
        n: int = 50,
        include_threshold: float = 0.0
    ) -> list[Paper]:
        """Get top N papers by citation score."""
        ranked = self.rank_papers(papers)
        filtered = [p for p, s in ranked if s >= include_threshold]
        return filtered[:n]


class ActiveLearningPipeline:
    """Active learning pipeline for iterative paper screening.
    
    Implements an iterative process where:
    1. Initial training set is selected
    2. Model is trained on labeled samples
    3. Most informative samples are selected for manual review
    4. Process repeats until stopping criteria met
    """
    
    def __init__(self, config: Optional[ActiveLearningConfig] = None):
        self.config = config or ActiveLearningConfig()
        self.labeled_samples: list[tuple[Paper, ScreeningDecision]] = []
        self.iteration = 0
    
    def initialize_training_set(
        self, 
        papers: list[Paper],
        initial_labels: list[tuple[str, ScreeningDecision]]
    ) -> list[Paper]:
        """Initialize training set with pre-labeled papers.
        
        Args:
            papers: All papers to screen
            initial_labels: List of (paper_id, decision) tuples
            
        Returns:
            Papers that should be manually reviewed first
        """
        self.labeled_samples = []
        
        paper_map = {p.id: p for p in papers}
        
        for paper_id, decision in initial_labels:
            if paper_id in paper_map:
                self.labeled_samples.append((paper_map[paper_id], decision))
        
        self.iteration = 0
        return [p for p, _ in self.labeled_samples]
    
    def select_samples_for_review(
        self,
        papers: list[Paper],
        results: list[ScreeningResult]
    ) -> list[Paper]:
        """Select samples most valuable for learning.
        
        Args:
            papers: Candidate papers
            results: Screening results with relevance scores
            
        Returns:
            Papers to review next
        """
        if self.iteration == 0 and len(self.labeled_samples) < self.config.initial_training_size:
            return self._select_initial_samples(papers)
        
        return self._select_informative_samples(papers, results)
    
    def _select_initial_samples(self, papers: list[Paper]) -> list[Paper]:
        """Select diverse initial samples for training."""
        selected = []
        remaining = list(papers)
        
        while len(selected) < self.config.initial_training_size and remaining:
            idx = random.randint(0, len(remaining) - 1)
            selected.append(remaining.pop(idx))
        
        return selected
    
    def _select_informative_samples(
        self,
        papers: list[Paper],
        results: list[ScreeningResult]
    ) -> list[Paper]:
        """Select most informative samples based on uncertainty."""
        result_map = {r.paper_id: r for r in results}
        unlabeled = [p for p in papers if p.id not in [ls[0].id for ls in self.labeled_samples]]
        
        if not unlabeled:
            return []
        
        scored_samples = []
        
        for paper in unlabeled:
            result = result_map.get(paper.id)
            if result:
                uncertainty = self._calculate_uncertainty(result)
                scored_samples.append((paper, uncertainty))
        
        scored_samples.sort(key=lambda x: x[1], reverse=True)
        
        selected = [p for p, _ in scored_samples[:self.config.batch_size]]
        
        if len(selected) < self.config.batch_size:
            remaining = [p for p in unlabeled if p not in selected]
            random.shuffle(remaining)
            selected.extend(remaining[:self.config.batch_size - len(selected)])
        
        return selected
    
    def _calculate_uncertainty(self, result: ScreeningResult) -> float:
        """Calculate uncertainty score for a result."""
        strategy = self.config.sampling_strategy
        
        if strategy == SamplingStrategy.LEAST_CONFIDENT:
            score = result.relevance_score
            return min(score, 1 - score)
        
        elif strategy == SamplingStrategy.MARGIN_SAMPLING:
            score = result.relevance_score
            margin = abs(score - 0.5)
            return 1 - margin
        
        elif strategy == SamplingStrategy.UNCERTAINTY:
            return 1 - result.confidence
        
        else:
            return 0.5
    
    def add_labeled_sample(
        self, 
        paper: Paper, 
        decision: ScreeningDecision
    ):
        """Add a manually labeled sample to training set."""
        self.labeled_samples.append((paper, decision))
    
    def get_training_data(self) -> tuple[list[str], list[int]]:
        """Get training data in format suitable for fine-tuning.
        
        Returns:
            Tuple of (texts, labels) where labels are 1=include, 0=exclude
        """
        texts = []
        labels = []
        
        for paper, decision in self.labeled_samples:
            text = self._prepare_text(paper)
            texts.append(text)
            
            if decision == ScreeningDecision.INCLUDE:
                labels.append(1)
            else:
                labels.append(0)
        
        return texts, labels
    
    def _prepare_text(self, paper: Paper) -> str:
        """Prepare text from paper."""
        parts = []
        if paper.title:
            parts.append(paper.title)
        if paper.abstract:
            parts.append(paper.abstract)
        return " ".join(parts)
    
    def should_stop(self) -> bool:
        """Check if active learning should stop."""
        self.iteration += 1
        
        if self.iteration >= self.config.max_iterations:
            return True
        
        if len(self.labeled_samples) >= len(self.labeled_samples) * 0.2:
            high_confidence = sum(
                1 for _, d in self.labeled_samples 
                if d != ScreeningDecision.UNCERTAIN
            )
            if high_confidence / len(self.labeled_samples) > 0.8:
                return True
        
        return False
    
    def get_statistics(self) -> dict:
        """Get statistics about the active learning process."""
        included = sum(1 for _, d in self.labeled_samples if d == ScreeningDecision.INCLUDE)
        excluded = sum(1 for _, d in self.labeled_samples if d == ScreeningDecision.EXCLUDE)
        uncertain = sum(1 for _, d in self.labeled_samples if d == ScreeningDecision.UNCERTAIN)
        
        return {
            "iteration": self.iteration,
            "total_labeled": len(self.labeled_samples),
            "included": included,
            "excluded": excluded,
            "uncertain": uncertain,
            "inclusion_rate": included / len(self.labeled_samples) if self.labeled_samples else 0,
        }


class CertaintyBasedScreen:
    """Certainty-based screening for automated decisions.
    
    Automatically makes screening decisions for papers with
    high confidence in exclusion or inclusion.
    """
    
    def __init__(
        self,
        exclude_confidence: float = 0.80,
        include_confidence: float = 0.80,
        auto_exclude: bool = True,
        auto_include: bool = True,
    ):
        self.exclude_confidence = exclude_confidence
        self.include_confidence = include_confidence
        self.auto_exclude = auto_exclude
        self.auto_include = auto_include
    
    def apply_certainty_decisions(
        self,
        results: list[ScreeningResult]
    ) -> tuple[list[ScreeningResult], list[ScreeningResult]]:
        """Apply certainty-based automated decisions.
        
        Returns:
            Tuple of (auto_decisions, need_review) papers
        """
        auto_decisions = []
        need_review = []
        
        for result in results:
            if self._should_auto_decide(result):
                result = self._apply_auto_decision(result)
                auto_decisions.append(result)
            else:
                need_review.append(result)
        
        return auto_decisions, need_review
    
    def _should_auto_decide(self, result: ScreeningResult) -> bool:
        """Check if result qualifies for automatic decision."""
        if result.decision != ScreeningDecision.UNCERTAIN:
            return False
        
        score = result.relevance_score
        confidence = result.confidence
        
        if self.auto_exclude and score < 0.35 and confidence >= self.exclude_confidence:
            return True
        
        if self.auto_include and score > 0.65 and confidence >= self.include_confidence:
            return True
        
        return False
    
    def _apply_auto_decision(self, result: ScreeningResult) -> ScreeningResult:
        """Apply automatic decision to result."""
        if result.relevance_score < 0.35:
            result.decision = ScreeningDecision.EXCLUDE
        else:
            result.decision = ScreeningDecision.INCLUDE
        return result


def create_citation_ranker(min_citations: int = 0) -> CitationRanker:
    """Factory function to create CitationRanker."""
    return CitationRanker(min_citations=min_citations)


def create_active_learning_pipeline(config: dict) -> ActiveLearningPipeline:
    """Create ActiveLearningPipeline from configuration."""
    al_config = ActiveLearningConfig(
        initial_training_size=config.get("initial_training_size", 50),
        batch_size=config.get("batch_size", 20),
        max_iterations=config.get("max_iterations", 10),
        confidence_threshold=config.get("confidence_threshold", 0.15),
        sampling_strategy=SamplingStrategy(config.get("sampling_strategy", "least_confident")),
    )
    return ActiveLearningPipeline(config=al_config)
