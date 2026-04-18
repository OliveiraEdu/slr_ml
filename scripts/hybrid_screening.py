#!/usr/bin/env python3
"""Hybrid SLR Screening Workflow with Human-in-the-Loop.

This workflow combines automated LLM screening with human expert review
for uncertain/edge cases, following PRISMA guidelines.
"""

import asyncio
import json
import time
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Optional

import sys

sys.path.insert(0, "/home/eduardo/Git/slr_ml")

from src.ml.ensemble_classifier import EnsembleVoter, Decision
from src.models.schemas import Paper


class ConfidenceLevel(Enum):
    HIGH = "high"  # Unanimous (4-0, 0-4)
    MEDIUM = "medium"  # Majority (3-1, 1-3)
    LOW = "low"  # Split (2-2)


class ReviewStatus(Enum):
    PENDING = "pending"
    INCLUDE_REVIEWED = "include_reviewed"
    EXCLUDE_REVIEWED = "exclude_reviewed"
    CONFIRMED = "confirmed"
    OVERRIDED = "overrided"


@dataclass
class ScreeningResult:
    """Result with confidence scoring."""

    title: str
    year: Optional[int]
    doi: Optional[str]
    abstract: str
    decision: str
    confidence_level: str
    auto_decide: bool
    votes: dict
    weighted_score: float
    pattern: str
    human_review_required: bool
    human_decision: Optional[str] = None
    human_reason: Optional[str] = None
    review_status: str = "pending"


class HybridScreeningWorkflow:
    """Hybrid workflow with automated screening + human review."""

    # Confidence thresholds
    HIGH_CONFIDENCE_PATTERNS = ["4-0", "0-4"]
    MEDIUM_CONFIDENCE_PATTERNS = ["3-1", "1-3"]
    LOW_CONFIDENCE_PATTERNS = ["2-2"]

    # Human review queues
    HIGH_CONFIDENCE_AUTO = 0.85  # Auto-decide threshold for high confidence
    MEDIUM_CONFIDENCE_AUTO = 0.75  # Auto-decide threshold for medium

    def __init__(self, num_agents: int = 4):
        self.num_agents = num_agents
        self.voter = EnsembleVoter(num_agents=num_agents)

    def _get_confidence_level(
        self, votes: dict, pattern: str
    ) -> tuple[ConfidenceLevel, bool]:
        """Determine confidence level and whether to auto-decide."""
        include_votes = votes.get("INCLUDE", 0)
        exclude_votes = votes.get("EXCLUDE", 0)

        if pattern in self.HIGH_CONFIDENCE_PATTERNS:
            return ConfidenceLevel.HIGH, True
        elif pattern in self.MEDIUM_CONFIDENCE_PATTERNS:
            return ConfidenceLevel.MEDIUM, True
        else:
            return ConfidenceLevel.LOW, False  # Always requires human review

    async def screen_paper(
        self,
        title: str,
        abstract: str,
        include_reason: str = "",
        exclude_reason: str = "",
    ) -> ScreeningResult:
        """Screen a single paper."""
        result = await self.voter.classify(title, abstract)
        votes = result.get("votes", {})
        pattern = f"{votes.get('INCLUDE', 0)}-{votes.get('EXCLUDE', 0)}"

        confidence_level, auto_decide = self._get_confidence_level(votes, pattern)

        return ScreeningResult(
            title=title[:200] if title else "",
            year=None,
            doi=None,
            abstract=abstract[:1000] if abstract else "",
            decision=result["decision"].value,
            confidence_level=confidence_level.value,
            auto_decide=auto_decide,
            votes=votes,
            weighted_score=result.get("weighted_scores", {}).get("include", 0),
            pattern=pattern,
            human_review_required=not auto_decide,
        )

    async def screen_corpus(
        self,
        papers: list[Paper],
        save_interval: int = 50,
        output_path: str = "/home/eduardo/Git/d-OSPv2/docs/papers/search-results/hybrid_screening.json",
    ) -> dict:
        """Screen entire corpus with hybrid workflow."""
        total = len(papers)
        results = []
        stats = {"auto_include": 0, "auto_exclude": 0, "human_review": 0}

        print(f"Starting hybrid screening of {total} papers...")
        start = time.time()

        for i, paper in enumerate(papers):
            result = await self.screen_paper(paper.title or "", paper.abstract or "")
            result.year = paper.year
            result.doi = paper.doi

            # Update stats
            if result.auto_decide:
                if result.decision == "INCLUDE":
                    stats["auto_include"] += 1
                else:
                    stats["auto_exclude"] += 1
            else:
                stats["human_review"] += 1

            results.append(asdict(result))

            # Progress
            if (i + 1) % 50 == 0:
                elapsed = time.time() - start
                rate = (i + 1) / elapsed
                remaining = (total - i - 1) / rate / 60
                print(f"{i + 1}/{total} ({rate:.2f}/s, ~{remaining:.0f}min remaining)")
                print(
                    f"  → Auto-INCLUDE: {stats['auto_include']}, Auto-EXCLUDE: {stats['auto_exclude']}, Human Review: {stats['human_review']}"
                )

                # Save incremental
                self._save_results(results, stats, output_path)

        elapsed = time.time() - start

        # Final save
        self._save_results(results, stats, output_path)

        return {
            "total": total,
            "runtime_minutes": elapsed / 60,
            "stats": stats,
            "confidence_distribution": self._get_confidence_dist(results),
        }

    def _save_results(self, results: list, stats: dict, output_path: str):
        """Save results to file."""
        with open(output_path, "w") as f:
            json.dump({"stats": stats, "results": results}, f, default=str, indent=2)

    def _get_confidence_dist(self, results: list) -> dict:
        """Get confidence distribution."""
        dist = {"high": 0, "medium": 0, "low": 0}
        for r in results:
            dist[r.get("confidence_level", "low")] += 1
        return dist


async def main():
    """Run hybrid workflow."""
    # Load papers
    papers_file = (
        "/home/eduardo/Git/d-OSPv2/docs/papers/search-results/deduplicated-papers.json"
    )
    with open(papers_file) as f:
        paper_data = json.load(f)

    papers = [Paper(**p) for p in paper_data]
    print(f"Loaded {len(papers)} papers")

    # Run hybrid screening
    workflow = HybridScreeningWorkflow(num_agents=4)
    summary = await workflow.screen_corpus(papers)

    print(f"\n=== HYBRID SCREENING COMPLETE ===")
    print(f"Total: {summary['total']}")
    print(f"Runtime: {summary['runtime_minutes']:.1f} minutes")
    print(f"\nResults:")
    print(f"  Auto-INCLUDE:    {summary['stats']['auto_include']}")
    print(f"  Auto-EXCLUDE:   {summary['stats']['auto_exclude']}")
    print(f"  Human Review:  {summary['stats']['human_review']}")
    print(f"\nConfidence:")
    print(f"  High:    {summary['confidence_distribution']['high']}")
    print(f"  Medium:  {summary['confidence_distribution']['medium']}")
    print(f"  Low:    {summary['confidence_distribution']['low']}")


if __name__ == "__main__":
    asyncio.run(main())
