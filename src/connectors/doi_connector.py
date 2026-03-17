"""DOI connector for CrossRef and DataCite API lookups."""
import time
from typing import Optional

import requests

from src.models.schemas import Paper


class DOIMetadata:
    """Container for DOI metadata from CrossRef/DataCite."""

    def __init__(
        self,
        doi: str,
        crossref_id: Optional[str] = None,
        datacite_id: Optional[str] = None,
        title: Optional[str] = None,
        publisher: Optional[str] = None,
        publication_date: Optional[str] = None,
        authors: Optional[list[dict]] = None,
        is_referenced_by_count: int = 0,
        referenced_works: Optional[list[str]] = None,
        url: Optional[str] = None,
        container_title: Optional[str] = None,
        type: Optional[str] = None,
        source: Optional[str] = None,
    ):
        self.doi = doi
        self.crossref_id = crossref_id
        self.datacite_id = datacite_id
        self.title = title
        self.publisher = publisher
        self.publication_date = publication_date
        self.authors = authors or []
        self.is_referenced_by_count = is_referenced_by_count
        self.referenced_works = referenced_works or []
        self.url = url
        self.container_title = container_title
        self.type = type
        self.source = source


class DOIMetadataConnector:
    """Connector for CrossRef and DataCite APIs.

    Free tier rate limits:
    - CrossRef: 10 requests/second (50 with email)
    - DataCite: 10 requests/second
    """

    CROSSREF_API = "https://api.crossref.org/works"
    DATACITE_API = "https://api.datacite.org/dois"

    def __init__(
        self,
        email: Optional[str] = None,
        rate_limit: float = 0.1,
    ):
        """Initialize connector.

        Args:
            email: Optional email for CrossRef (higher rate limits)
            rate_limit: Seconds between requests (default 0.1 = 10/sec)
        """
        self.email = email
        self.rate_limit = rate_limit
        self._last_request_time = 0.0

    def _rate_limit(self):
        """Apply rate limiting between requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.rate_limit:
            time.sleep(self.rate_limit - elapsed)
        self._last_request_time = time.time()

    def _get_crossref_headers(self) -> dict:
        """Get headers for CrossRef API."""
        headers = {"Accept": "application/json"}
        if self.email:
            headers["User-Agent"] = f"PRISMA-SLR-Engine/1.0 (mailto:{self.email})"
        return headers

    def lookup_doi(self, doi: str) -> Optional[DOIMetadata]:
        """Look up DOI metadata from CrossRef and DataCite.

        Args:
            doi: DOI string (with or without https://doi.org/)

        Returns:
            DOIMetadata object with combined results, or None if not found
        """
        clean_doi = self._clean_doi(doi)
        if not clean_doi:
            return None

        crossref_data = self._query_crossref(clean_doi)
        datacite_data = self._query_datacite(clean_doi)

        if not crossref_data and not datacite_data:
            return None

        return self._merge_metadata(clean_doi, crossref_data, datacite_data)

    def _clean_doi(self, doi: str) -> Optional[str]:
        """Clean and normalize DOI string."""
        if not doi:
            return None
        doi = doi.strip()
        doi = doi.replace("https://doi.org/", "")
        doi = doi.replace("http://doi.org/", "")
        doi = doi.replace("doi:", "")
        return doi if doi else None

    def _query_crossref(self, doi: str) -> Optional[dict]:
        """Query CrossRef API."""
        self._rate_limit()
        try:
            url = f"{self.CROSSREF_API}/{doi}"
            response = requests.get(url, headers=self._get_crossref_headers(), timeout=10)
            if response.status_code == 200:
                return response.json().get("message", {})
            return None
        except requests.RequestException:
            return None

    def _query_datacite(self, doi: str) -> Optional[dict]:
        """Query DataCite API."""
        self._rate_limit()
        try:
            url = f"{self.DATACITE_API}/{doi}"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                return response.json().get("data", {}).get("attributes", {})
            return None
        except requests.RequestException:
            return None

    def _merge_metadata(
        self,
        doi: str,
        crossref: Optional[dict],
        datacite: Optional[dict],
    ) -> DOIMetadata:
        """Merge metadata from CrossRef and DataCite."""
        title = None
        if crossref:
            title = crossref.get("title", [None])[0] if crossref.get("title") else None
        if not title and datacite:
            title = datacite.get("titles", [{}])[0].get("title")

        publisher = None
        if crossref:
            publisher = crossref.get("publisher")
        if not publisher and datacite:
            publisher = datacite.get("publisher")

        publication_date = None
        if crossref:
            date_parts = crossref.get("published-print") or crossref.get("published-online") or {}
            date_parts = date_parts.get("date-parts", [[None]])[0]
            if date_parts:
                publication_date = "-".join(str(d) for d in date_parts if d)
        if not publication_date and datacite:
            dates = datacite.get("dates", [])
            for d in dates:
                if d.get("dateType") == "Published":
                    publication_date = d.get("date")
                    break

        authors = None
        if crossref:
            authors = [
                {"given": a.get("given", ""), "family": a.get("family", ""), "ORCID": a.get("ORCID")}
                for a in crossref.get("author", [])
            ]
        if not authors and datacite:
            creators = datacite.get("creators", [])
            authors = [
                {"given": c.get("givenName", ""), "family": c.get("familyName", ""), "ORCID": c.get("nameIdentifier")}
                for c in creators
            ]

        citations = 0
        if crossref:
            citations = crossref.get("is-referenced-by-count", 0)

        references = []
        if crossref:
            references = [r.get("DOI") for r in crossref.get("reference", []) if r.get("DOI")]

        url = None
        if crossref:
            url = crossref.get("URL")
        if not url and datacite:
            url = datacite.get("url")

        container = None
        if crossref:
            container = crossref.get("container-title", [None])[0]
        if not container and datacite:
            container = datacite.get("container", [{}])[0].get("title")

        doc_type = None
        if crossref:
            doc_type = crossref.get("type")
        if not doc_type and datacite:
            doc_type = datacite.get("types", {}).get("risType")

        source = "crossref" if crossref else ("datacite" if datacite else None)

        return DOIMetadata(
            doi=doi,
            crossref_id=doi if crossref else None,
            datacite_id=doi if datacite else None,
            title=title,
            publisher=publisher,
            publication_date=publication_date,
            authors=authors,
            is_referenced_by_count=citations,
            referenced_works=references,
            url=url,
            container_title=container,
            type=doc_type,
            source=source,
        )

    def enrich_paper(self, paper: Paper) -> Paper:
        """Enrich a Paper object with DOI metadata.

        Args:
            paper: Paper object to enrich

        Returns:
            Updated Paper object
        """
        if not paper.doi:
            return paper

        metadata = self.lookup_doi(paper.doi)
        if not metadata:
            return paper

        paper_dict = paper.model_dump()

        if metadata.is_referenced_by_count:
            paper_dict["citations"] = metadata.is_referenced_by_count
        if metadata.publisher:
            paper_dict["raw_metadata"]["publisher"] = metadata.publisher
        if metadata.publication_date:
            paper_dict["raw_metadata"]["publication_date"] = metadata.publication_date
        if metadata.referenced_works:
            paper_dict["raw_metadata"]["referenced_works"] = metadata.referenced_works
        if metadata.container_title:
            paper_dict["raw_metadata"]["journal"] = metadata.container_title
        if metadata.url:
            paper_dict["url"] = metadata.url
        if metadata.authors and not paper_dict.get("authors"):
            paper_dict["authors"] = [
                f"{a.get('given', '')} {a.get('family', '')}".strip()
                for a in metadata.authors
            ]
        if metadata.source:
            paper_dict["raw_metadata"]["doi_source"] = metadata.source

        return Paper(**paper_dict)

    def batch_enrich(
        self,
        papers: list[Paper],
        skip_existing: bool = True,
    ) -> list[Paper]:
        """Enrich multiple papers with DOI metadata.

        Args:
            papers: List of papers to enrich
            skip_existing: Skip papers that already have citation counts

        Returns:
            List of enriched papers
        """
        enriched = []
        for paper in papers:
            if skip_existing and paper.doi and paper.citations > 0:
                enriched.append(paper)
                continue
            enriched.append(self.enrich_paper(paper))
        return enriched
