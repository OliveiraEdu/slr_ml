"""Snowballing module for systematic literature review.

Implements backward and forward snowballing to find additional relevant
papers through reference chasing and citation analysis.
"""
import re
from dataclasses import dataclass
from typing import Optional
import httpx

from src.models.schemas import Paper


@dataclass
class SnowballingConfig:
    max_depth: int = 2
    max_papers_per_source: int = 50
    include_references: bool = True
    include_citations: bool = True
    use_semantic_scholar: bool = True
    use_crossref: bool = True


class SnowballingSearcher:
    """Search for related papers through snowballing.
    
    Backward snowballing: Extract references from included papers
    Forward snowballing: Find papers that cite included papers
    """
    
    def __init__(self, config: Optional[SnowballingConfig] = None):
        self.config = config or SnowballingConfig()
        self.visited_ids: set[str] = set()
        self.found_papers: list[Paper] = []
        self.references_by_paper: dict[str, list[str]] = {}
        self.citations_by_paper: dict[str, list[str]] = {}
    
    def search(
        self,
        included_papers: list[Paper],
        existing_paper_ids: Optional[set[str]] = None,
    ) -> list[Paper]:
        """Perform snowballing search on included papers.
        
        Args:
            included_papers: Papers to use as seeds
            existing_paper_ids: IDs of already-screened papers to exclude
            
        Returns:
            List of newly found papers through snowballing
        """
        existing_ids = existing_paper_ids or set()
        seed_ids = {p.id for p in included_papers}
        
        self.visited_ids = set()
        self.found_papers = []
        
        for paper in included_papers:
            self._process_paper(paper, depth=0, existing_ids=existing_ids | seed_ids)
        
        return self.found_papers
    
    def _process_paper(
        self,
        paper: Paper,
        depth: int,
        existing_ids: set[str],
    ):
        """Process a single paper for snowballing."""
        if depth >= self.config.max_depth:
            return
        
        if paper.id in self.visited_ids:
            return
        
        self.visited_ids.add(paper.id)
        
        if self.config.include_references:
            self._search_references(paper, depth, existing_ids)
        
        if self.config.include_citations and self.config.use_semantic_scholar:
            self._search_citations(paper, depth, existing_ids)
    
    def _search_references(
        self,
        paper: Paper,
        depth: int,
        existing_ids: set[str],
    ):
        """Extract and search references from paper."""
        references = self._extract_references(paper)
        
        if references:
            self.references_by_paper[paper.id] = references
        
        for ref_doi in references[:self.config.max_papers_per_source]:
            if ref_doi and ref_doi not in existing_ids and ref_doi not in self.visited_ids:
                ref_paper = self._fetch_paper_by_doi(ref_doi)
                if ref_paper:
                    self.found_papers.append(ref_paper)
                    self._process_paper(ref_paper, depth + 1, existing_ids)
    
    def _search_citations(
        self,
        paper: Paper,
        depth: int,
        existing_ids: set[str],
    ):
        """Find papers that cite this paper."""
        citations = self._fetch_citations(paper)
        
        if citations:
            self.citations_by_paper[paper.id] = citations
        
        for cit_doi in citations[:self.config.max_papers_per_source]:
            if cit_doi and cit_doi not in existing_ids and cit_doi not in self.visited_ids:
                cit_paper = self._fetch_paper_by_doi(cit_doi)
                if cit_paper:
                    self.found_papers.append(cit_paper)
                    self._process_paper(cit_paper, depth + 1, existing_ids)
    
    def _extract_references(self, paper: Paper) -> list[str]:
        """Extract DOIs from paper's raw metadata references."""
        dois = []
        
        if paper.raw_metadata:
            refs = paper.raw_metadata.get("references", [])
            for ref in refs:
                if isinstance(ref, dict):
                    doi = ref.get("DOI") or ref.get("doi")
                    if doi:
                        dois.append(doi)
        
        if paper.referenced_works:
            dois.extend(paper.referenced_works)
        
        return list(set(dois))
    
    def _fetch_citations(self, paper: Paper) -> list[str]:
        """Fetch papers that cite this paper via Semantic Scholar."""
        if not paper.doi:
            return []
        
        dois = []
        
        try:
            url = f"https://api.semanticscholar.org/graph/v1/paper/DOI:{paper.doi}/citations"
            params = {
                "fields": "externalIds",
                "limit": self.config.max_papers_per_source,
            }
            
            response = httpx.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                for citation in data.get("data", []):
                    external_ids = citation.get("externalIds", {})
                    doi = external_ids.get("DOI")
                    if doi:
                        dois.append(doi)
        except Exception:
            pass
        
        return dois
    
    def _fetch_paper_by_doi(self, doi: str) -> Optional[Paper]:
        """Fetch paper metadata by DOI."""
        try:
            url = f"https://api.crossref.org/works/{doi}"
            headers = {"Accept": "application/json"}
            
            response = httpx.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json().get("message", {})
                
                from src.utils.text_utils import generate_paper_id
                
                paper_id = generate_paper_id(
                    data.get("title", [""])[0] if data.get("title") else "",
                    doi,
                    []
                )
                
                authors = []
                for author in data.get("author", []):
                    name = f"{author.get('given', '')} {author.get('family', '')}"
                    if name.strip():
                        authors.append(name.strip())
                
                year = None
                if data.get("published-print") or data.get("published-online"):
                    date_parts = (
                        data.get("published-print", {}) or data.get("published-online", {})
                    ).get("date-parts", [[]])
                    if date_parts and date_parts[0]:
                        year = date_parts[0][0]
                
                journal = data.get("container-title", [""])[0] if data.get("container-title") else ""
                
                return Paper(
                    id=paper_id,
                    source="snowballing",
                    title=data.get("title", [""])[0] if data.get("title") else "",
                    authors=authors,
                    abstract=data.get("abstract"),
                    year=year,
                    doi=doi,
                    journal=journal,
                    keywords=[],
                    citations=0,
                    raw_metadata=data,
                )
        except Exception:
            pass
        
        return None
    
    def get_statistics(self) -> dict:
        """Get snowballing statistics."""
        return {
            "papers_processed": len(self.visited_ids),
            "papers_found": len(self.found_papers),
            "references_found": sum(len(r) for r in self.references_by_paper.values()),
            "citations_found": sum(len(c) for c in self.citations_by_paper.values()),
            "papers_by_depth": {
                "references": {k: len(v) for k, v in self.references_by_paper.items()},
                "citations": {k: len(v) for k, v in self.citations_by_paper.items()},
            },
        }


class BackwardSnowballer:
    """Backward snowballing - follow references from included papers."""
    
    def __init__(self, max_depth: int = 1, max_papers: int = 50):
        self.max_depth = max_depth
        self.max_papers = max_papers
    
    def search(self, papers: list[Paper]) -> list[dict]:
        """Find references from papers."""
        references = []
        
        for paper in papers[:self.max_papers]:
            refs = self._extract_citations(paper)
            for ref in refs:
                ref["source_paper_id"] = paper.id
                ref["source_title"] = paper.title
            references.extend(refs)
        
        return references
    
    def _extract_citations(self, paper: Paper) -> list[dict]:
        """Extract citations from paper metadata."""
        citations = []
        
        if paper.raw_metadata and "references" in paper.raw_metadata:
            for ref in paper.raw_metadata["references"]:
                if isinstance(ref, dict):
                    citations.append({
                        "title": ref.get("title", ""),
                        "doi": ref.get("DOI", ""),
                        "year": ref.get("year"),
                    })
        
        if paper.referenced_works:
            for doi in paper.referenced_works:
                citations.append({
                    "title": "",
                    "doi": doi,
                    "year": None,
                })
        
        return citations


class ForwardSnowballer:
    """Forward snowballing - find papers that cite included papers."""
    
    def __init__(self, max_papers: int = 50):
        self.max_papers = max_papers
    
    def search(self, papers: list[Paper]) -> list[dict]:
        """Find papers that cite the given papers."""
        citations = []
        
        for paper in papers[:self.max_papers]:
            if not paper.doi:
                continue
            
            try:
                url = f"https://api.semanticscholar.org/graph/v1/paper/DOI:{paper.doi}/citations"
                params = {
                    "fields": "title,externalIds,year,citationCount",
                    "limit": 20,
                }
                
                response = httpx.get(url, params=params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    for cit in data.get("data", []):
                        external_ids = cit.get("externalIds", {})
                        citations.append({
                            "title": cit.get("title", ""),
                            "doi": external_ids.get("DOI", ""),
                            "year": cit.get("year"),
                            "citations": cit.get("citationCount", 0),
                            "source_paper_id": paper.id,
                        })
            except Exception:
                continue
        
        return citations


def create_snowballer(config: dict) -> SnowballingSearcher:
    """Create snowballer from configuration."""
    snow_config = SnowballingConfig(
        max_depth=config.get("max_depth", 2),
        max_papers_per_source=config.get("max_papers_per_source", 50),
        include_references=config.get("include_references", True),
        include_citations=config.get("include_citations", True),
    )
    return SnowballingSearcher(config=snow_config)
