"""Semantic Scholar connector for citation tracking and paper enrichment."""
import time
from typing import Optional
import requests

from src.models.schemas import Paper


class SemanticScholarPaper:
    """Container for Semantic Scholar paper data."""

    def __init__(
        self,
        paper_id: str,
        title: str,
        citation_count: int = 0,
        reference_count: int = 0,
        influential_citation_count: int = 0,
        is_open_access: bool = False,
        open_access_pdf: Optional[str] = None,
        fields_of_study: Optional[list[str]] = None,
        publication_date: Optional[str] = None,
        authors: Optional[list[dict]] = None,
        citations: Optional[list[dict]] = None,
        references: Optional[list[dict]] = None,
    ):
        self.paper_id = paper_id
        self.title = title
        self.citation_count = citation_count
        self.reference_count = reference_count
        self.influential_citation_count = influential_citation_count
        self.is_open_access = is_open_access
        self.open_access_pdf = open_access_pdf
        self.fields_of_study = fields_of_study or []
        self.publication_date = publication_date
        self.authors = authors or []
        self.citations = citations or []
        self.references = references or []


class SemanticScholarConnector:
    """Connector for Semantic Scholar API.

    Provides citation data, paper metadata, and citation network analysis.
    Free tier: 100 requests/5 minutes.
    """

    API_BASE = "https://api.semanticscholar.org/graph/v1"
    PAPER_ENDPOINT = f"{API_BASE}/paper"
    AUTHOR_ENDPOINT = f"{API_BASE}/author"
    SEARCH_ENDPOINT = f"{API_BASE}/paper/search"

    def __init__(
        self,
        rate_limit: float = 1.0,
        timeout: int = 30,
    ):
        self.rate_limit = rate_limit
        self.timeout = timeout
        self._last_request = 0.0

    def _rate_limit(self):
        """Apply rate limiting."""
        elapsed = time.time() - self._last_request
        if elapsed < self.rate_limit:
            time.sleep(self.rate_limit - elapsed)
        self._last_request = time.time()

    def get_paper_by_doi(self, doi: str) -> Optional[SemanticScholarPaper]:
        """Fetch paper by DOI."""
        self._rate_limit()
        
        try:
            url = f"{self.PAPER_ENDPOINT}/DOI:{doi}"
            params = {
                "fields": "title,citationCount,referenceCount,influentialCitationCount,isOpenAccess,openAccessPdf,fieldsOfStudy,publicationDate,authors,citations.title,references.title",
            }
            
            response = requests.get(
                url,
                params=params,
                timeout=self.timeout,
            )
            response.raise_for_status()
            
            data = response.json()
            return self._parse_paper_response(data)
            
        except requests.RequestException as e:
            print(f"Semantic Scholar lookup error: {e}")
            return None

    def get_paper_by_id(self, paper_id: str) -> Optional[SemanticScholarPaper]:
        """Fetch paper by Semantic Scholar ID."""
        self._rate_limit()
        
        try:
            url = f"{self.PAPER_ENDPOINT}/{paper_id}"
            params = {
                "fields": "title,citationCount,referenceCount,influentialCitationCount,isOpenAccess,openAccessPdf,fieldsOfStudy,publicationDate,authors,citations.title,references.title",
            }
            
            response = requests.get(
                url,
                params=params,
                timeout=self.timeout,
            )
            response.raise_for_status()
            
            data = response.json()
            return self._parse_paper_response(data)
            
        except requests.RequestException as e:
            print(f"Semantic Scholar lookup error: {e}")
            return None

    def get_citations(
        self,
        paper_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict]:
        """Get papers citing the given paper."""
        self._rate_limit()
        
        try:
            url = f"{self.PAPER_ENDPOINT}/{paper_id}/citations"
            params = {
                "fields": "title,authors,year,citationCount",
                "limit": min(limit, 1000),
                "offset": offset,
            }
            
            response = requests.get(
                url,
                params=params,
                timeout=self.timeout,
            )
            response.raise_for_status()
            
            data = response.json()
            return data.get("data", [])
            
        except requests.RequestException as e:
            print(f"Semantic Scholar citations error: {e}")
            return []

    def get_references(
        self,
        paper_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict]:
        """Get papers referenced by the given paper."""
        self._rate_limit()
        
        try:
            url = f"{self.PAPER_ENDPOINT}/{paper_id}/references"
            params = {
                "fields": "title,authors,year,citationCount",
                "limit": min(limit, 1000),
                "offset": offset,
            }
            
            response = requests.get(
                url,
                params=params,
                timeout=self.timeout,
            )
            response.raise_for_status()
            
            data = response.json()
            return data.get("data", [])
            
        except requests.RequestException as e:
            print(f"Semantic Scholar references error: {e}")
            return []

    def search_papers(
        self,
        query: str,
        limit: int = 10,
        offset: int = 0,
    ) -> list[SemanticScholarPaper]:
        """Search for papers by query."""
        self._rate_limit()
        
        try:
            params = {
                "query": query,
                "fields": "title,citationCount,referenceCount,influentialCitationCount,fieldsOfStudy,publicationDate,authors",
                "limit": min(limit, 100),
                "offset": offset,
            }
            
            response = requests.get(
                self.SEARCH_ENDPOINT,
                params=params,
                timeout=self.timeout,
            )
            response.raise_for_status()
            
            data = response.json()
            return [self._parse_paper_response(p) for p in data.get("data", [])]
            
        except requests.RequestException as e:
            print(f"Semantic Scholar search error: {e}")
            return []

    def enrich_paper_with_citations(self, paper: Paper) -> Paper:
        """Enrich a paper with citation data from Semantic Scholar."""
        if not paper.doi:
            return paper
        
        ss_paper = self.get_paper_by_doi(paper.doi)
        
        if ss_paper:
            if ss_paper.citation_count and paper.citations is None:
                paper.citations = ss_paper.citation_count
            
            if ss_paper.is_open_access and ss_paper.open_access_pdf:
                paper.pdf_url = ss_paper.open_access_pdf
            
            if ss_paper.fields_of_study:
                paper.raw_metadata["semantic_scholar_fields"] = ss_paper.fields_of_study
            
            paper.raw_metadata["semantic_scholar_id"] = ss_paper.paper_id
            paper.raw_metadata["influential_citations"] = ss_paper.influential_citation_count
            paper.raw_metadata["reference_count"] = ss_paper.reference_count
        
        return paper

    def _parse_paper_response(self, data: dict) -> SemanticScholarPaper:
        """Parse API response into SemanticScholarPaper."""
        return SemanticScholarPaper(
            paper_id=data.get("paperId", ""),
            title=data.get("title", ""),
            citation_count=data.get("citationCount", 0),
            reference_count=data.get("referenceCount", 0),
            influential_citation_count=data.get("influentialCitationCount", 0),
            is_open_access=data.get("isOpenAccess", False),
            open_access_pdf=data.get("openAccessPdf", {}).get("url") if data.get("openAccessPdf") else None,
            fields_of_study=data.get("fieldsOfStudy", []),
            publication_date=data.get("publicationDate"),
            authors=data.get("authors", []),
            citations=data.get("citations", []),
            references=data.get("references", []),
        )


class CitationAnalyzer:
    """Analyze citation networks using Semantic Scholar data."""

    def __init__(self, ss_connector: Optional[SemanticScholarConnector] = None):
        self.connector = ss_connector or SemanticScholarConnector()

    def get_citation_network(
        self,
        paper_id: str,
        depth: int = 2,
    ) -> dict:
        """Get citation network for a paper."""
        network = {
            "root": paper_id,
            "depth": depth,
            "papers": {},
            "edges": [],
        }
        
        visited = set()
        queue = [(paper_id, 0)]
        
        while queue:
            current_id, current_depth = queue.pop(0)
            
            if current_id in visited or current_depth > depth:
                continue
            
            visited.add(current_id)
            
            paper = self.connector.get_paper_by_id(current_id)
            if paper:
                network["papers"][current_id] = {
                    "title": paper.title,
                    "citation_count": paper.citation_count,
                    "influential_citations": paper.influential_citation_count,
                }
                
                if current_depth < depth:
                    for ref in paper.references:
                        ref_id = ref.get("paperId")
                        if ref_id:
                            network["edges"].append((current_id, ref_id))
                            queue.append((ref_id, current_depth + 1))
                    
                    for cit in paper.citations:
                        cit_id = cit.get("paperId")
                        if cit_id:
                            network["edges"].append((current_id, cit_id))
                            queue.append((cit_id, current_depth + 1))
        
        return network

    def rank_by_influence(
        self,
        paper_ids: list[str],
    ) -> list[tuple[str, float]]:
        """Rank papers by influential citation count."""
        scores = []
        
        for pid in paper_ids:
            paper = self.connector.get_paper_by_id(pid)
            if paper:
                score = paper.influential_citation_count
                scores.append((pid, score))
        
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores

    def find_pivotal_papers(
        self,
        paper_ids: list[str],
        min_influential: int = 5,
    ) -> list[dict]:
        """Find pivotal papers in a citation network."""
        pivotal = []
        
        for pid in paper_ids:
            paper = self.connector.get_paper_by_id(pid)
            if paper and paper.influential_citation_count >= min_influential:
                pivotal.append({
                    "paper_id": pid,
                    "title": paper.title,
                    "citation_count": paper.citation_count,
                    "influential_citations": paper.influential_citation_count,
                    "influence_ratio": paper.influential_citation_count / max(paper.citation_count, 1),
                })
        
        pivotal.sort(key=lambda x: x["influential_citations"], reverse=True)
        return pivotal
