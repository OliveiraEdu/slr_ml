"""Screening pipeline for PRISMA-compliant paper screening."""
from typing import Optional

from src.models.schemas import Paper, PrismaFlowData, ScreeningResult


class ScreeningPipeline:
    """Manages the PRISMA screening workflow."""

    def __init__(
        self,
        include_threshold: float = 0.6,
        exclude_threshold: float = 0.3,
        uncertain_threshold: float = 0.3,
        confidence_gap: float = 0.15,
    ):
        self.include_threshold = include_threshold
        self.exclude_threshold = exclude_threshold
        self.uncertain_threshold = uncertain_threshold
        self.confidence_gap = confidence_gap
        self._results: list[ScreeningResult] = []

    def screen_papers(
        self,
        papers: list[Paper],
        results: list[ScreeningResult],
        stage: str = "title_abstract",
    ) -> list[ScreeningResult]:
        """Screen papers based on ML classification results."""
        self._results = results
        prisma_flow = self._calculate_flow(papers, results)

        return self._results

    def _calculate_flow(
        self, papers: list[Paper], results: list[ScreeningResult]
    ) -> PrismaFlowData:
        """Calculate PRISMA flow diagram data."""
        flow = PrismaFlowData()
        flow.identification_identified = len(papers)

        if not results:
            flow.identification_after_duplicates = len(papers)
            return flow

        included = sum(1 for r in results if r.decision == "include")
        excluded = sum(1 for r in results if r.decision == "exclude")
        uncertain = sum(1 for r in results if r.decision == "uncertain")

        flow.screening_sought_retrieval = included
        flow.screening_abstract_excluded = excluded + uncertain
        flow.eligible = included

        return flow

    def make_decision(self, result: ScreeningResult) -> str:
        """Make screening decision based on score and confidence."""
        score = result.relevance_score
        confidence = result.confidence

        if score >= self.include_threshold and confidence >= self.confidence_gap:
            return "include"
        elif score <= self.exclude_threshold and confidence >= self.confidence_gap:
            return "exclude"
        else:
            return "uncertain"

    def update_results_with_decisions(self, results: list[ScreeningResult]) -> list[ScreeningResult]:
        """Update results with screening decisions."""
        for result in results:
            if result.decision == "pending":
                result.decision = self.make_decision(result)
        return results


class ScreeningManager:
    """Manages screening state and results."""

    def __init__(self):
        self.papers: list[Paper] = []
        self.results: list[ScreeningResult] = []
        self.current_stage: str = "title_abstract"

    def set_papers(self, papers: list[Paper]):
        """Set papers for screening."""
        self.papers = papers

    def add_results(self, results: list[ScreeningResult]):
        """Add screening results."""
        self.results.extend(results)

    def get_included(self) -> list[Paper]:
        """Get papers included after screening."""
        included_ids = set(r.paper_id for r in self.results if r.decision == "include")
        return [p for p in self.papers if p.id in included_ids]

    def get_excluded(self) -> list[Paper]:
        """Get papers excluded after screening."""
        excluded_ids = set(r.paper_id for r in self.results if r.decision == "exclude")
        return [p for p in self.papers if p.id in excluded_ids]

    def get_uncertain(self) -> list[Paper]:
        """Get papers requiring manual review."""
        uncertain_ids = set(r.paper_id for r in self.results if r.decision == "uncertain")
        return [p for p in self.papers if p.id in uncertain_ids]

    def generate_flow_data(self) -> PrismaFlowData:
        """Generate PRISMA flow diagram data."""
        flow = PrismaFlowData()
        flow.identification_identified = len(self.papers)

        included = len(self.get_included())
        excluded = len(self.get_excluded())
        uncertain = len(self.get_uncertain())

        flow.identification_after_duplicates = len(self.papers)
        flow.screening_abstract_excluded = excluded + uncertain
        flow.screening_sought_retrieval = included
        flow.eligible = included
        flow.included_studies = included

        flow.total_screened = included + excluded + uncertain
        flow.total_excluded = excluded + uncertain

        return flow
