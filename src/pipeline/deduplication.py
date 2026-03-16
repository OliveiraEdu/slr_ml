"""Deduplication pipeline for removing duplicate papers."""
import re
from collections import defaultdict
from typing import Optional

from rapidfuzz import fuzz

from src.models.schemas import Paper


class Deduplicator:
    """Handles deduplication of papers from multiple sources."""

    def __init__(self, doi_threshold: float = 0.95, title_threshold: float = 0.85):
        self.doi_threshold = doi_threshold
        self.title_threshold = title_threshold

    def deduplicate(self, papers: list[Paper]) -> tuple[list[Paper], dict]:
        """Remove duplicate papers from the list."""
        if not papers:
            return [], {"duplicates_removed": 0, "duplicate_groups": []}

        doi_groups = self._group_by_doi(papers)
        doi_duplicates = self._find_doi_duplicates(doi_groups)

        papers_to_remove = set()
        duplicate_groups = []

        for group in doi_duplicates:
            for p in group[1:]:
                papers_to_remove.add(p.id)
            duplicate_groups.append({
                "representative": group[0].id,
                "duplicates": [p.id for p in group[1:]],
                "method": "doi",
            })

        remaining = [p for p in papers if p.id not in papers_to_remove]
        title_duplicates = self._find_title_duplicates(remaining)

        for group in title_duplicates:
            for p in group[1:]:
                papers_to_remove.add(p.id)
            duplicate_groups.append({
                "representative": group[0].id,
                "duplicates": [p.id for p in group[1:]],
                "method": "title",
            })

        final_papers = [p for p in papers if p.id not in papers_to_remove]

        report = {
            "original_count": len(papers),
            "duplicates_removed": len(papers_to_remove),
            "final_count": len(final_papers),
            "duplicate_groups": duplicate_groups,
        }

        return final_papers, report

    def _group_by_doi(self, papers: list[Paper]) -> dict[str, list[Paper]]:
        """Group papers by DOI."""
        groups = defaultdict(list)
        for paper in papers:
            doi = self._normalize_doi(paper.doi)
            if doi:
                groups[doi].append(paper)
        return groups

    def _normalize_doi(self, doi: Optional[str]) -> Optional[str]:
        """Normalize DOI for comparison."""
        if not doi:
            return None
        doi = doi.lower().strip()
        doi = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", doi)
        return doi

    def _find_doi_duplicates(
        self, doi_groups: dict[str, list[Paper]]
    ) -> list[list[Paper]]:
        """Find duplicate groups by DOI."""
        duplicates = []
        for doi, group in doi_groups.items():
            if len(group) > 1:
                duplicates.append(group)
        return duplicates

    def _find_title_duplicates(self, papers: list[Paper]) -> list[list[Paper]]:
        """Find duplicate groups by title similarity."""
        if len(papers) < 2:
            return []

        duplicates = []
        processed = set()

        for i, paper1 in enumerate(papers):
            if paper1.id in processed:
                continue

            group = [paper1]
            title1 = self._normalize_title(paper1.title)

            if not title1:
                continue

            for paper2 in papers[i + 1:]:
                if paper2.id in processed:
                    continue

                title2 = self._normalize_title(paper2.title)
                if not title2:
                    continue

                similarity = fuzz.ratio(title1, title2) / 100.0
                if similarity >= self.title_threshold:
                    group.append(paper2)
                    processed.add(paper2.id)

            if len(group) > 1:
                duplicates.append(group)
                processed.add(paper1.id)

        return duplicates

    def _normalize_title(self, title: Optional[str]) -> Optional[str]:
        """Normalize title for comparison."""
        if not title:
            return None
        title = title.lower().strip()
        title = re.sub(r"[^\w\s]", "", title)
        title = re.sub(r"\s+", " ", title)
        return title


def deduplicate(papers: list[Paper]) -> tuple[list[Paper], dict]:
    """Convenience function to deduplicate papers."""
    dedup = Deduplicator()
    return dedup.deduplicate(papers)
