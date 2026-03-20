"""arXiv API connector for retrieving preprints."""
import re
from datetime import datetime
from typing import Optional

import arxiv

from src.models.schemas import Paper, SourceName
from src.utils.text_utils import clean_text


class ArxivConnector:
    """Connector for arXiv API."""

    def __init__(self):
        self._client = None

    def _get_client(self) -> arxiv.Client:
        """Get or create arXiv client."""
        if self._client is None:
            self._client = arxiv.Client()
        return self._client

    def search(
        self,
        query: str,
        max_results: int = 50,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        categories: Optional[list[str]] = None,
    ) -> list[Paper]:
        """Search arXiv for papers matching query."""
        client = self._get_client()

        search_query = query
        if categories:
            cat_query = " OR ".join([f"cat:{c}" for c in categories])
            search_query = f"({query}) AND ({cat_query})"

        if date_from or date_to:
            date_parts = []
            if date_from:
                date_parts.append(f"submittedDate:[{date_from} TO *]")
            if date_to:
                date_parts.append(f"submittedDate:[* TO {date_to}]")
            search_query += f" AND ({' AND '.join(date_parts)})"

        search = arxiv.Search(
            query=search_query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.Relevance,
        )

        papers = []
        for result in client.results(search):
            paper = self._parse_result(result)
            papers.append(paper)

        return papers

    def _parse_result(self, result: arxiv.Result) -> Paper:
        """Parse arXiv result into Paper object."""
        paper_id = self._extract_arxiv_id(result.entry_id)

        title = result.title
        if title:
            title = self._clean_text(title)

        authors = [author.name for author in result.authors]

        abstract = result.summary
        if abstract:
            abstract = self._clean_text(abstract)

        year = result.published.year if result.published else None

        doi = None
        for link in result.links:
            if link.title == "doi":
                doi = link.href
                break

        url = result.entry_id

        journal = result.pdf_url.split("/")[-1] if result.pdf_url else None

        categories = result.categories

        return Paper(
            id=paper_id,
            source=SourceName.ARXIV,
            title=title,
            authors=authors,
            abstract=abstract,
            year=year,
            doi=doi,
            url=url,
            journal="arXiv",
            keywords=categories,
            raw_metadata={
                "arxiv_id": paper_id,
                "pdf_url": result.pdf_url,
                "comment": result.comment,
                "categories": categories,
                "published": result.published.isoformat() if result.published else None,
            },
        )

    def _extract_arxiv_id(self, entry_id: str) -> str:
        """Extract arXiv ID from entry URL."""
        match = re.search(r"(\d{4}\.\d{4,5})", entry_id)
        if match:
            return match.group(1)
        return entry_id.split("/")[-1]

    def _clean_text(self, text: str) -> str:
        """Clean text field."""
        return clean_text(text)


def search_arxiv(
    query: str,
    max_results: int = 50,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    categories: Optional[list[str]] = None,
) -> list[Paper]:
    """Convenience function to search arXiv."""
    connector = ArxivConnector()
    return connector.search(query, max_results, date_from, date_to, categories)
