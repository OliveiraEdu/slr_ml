"""MeSH term connector for biomedical literature indexing."""
import time
from typing import Optional
import requests

from src.models.schemas import Paper


class MeSHTerm:
    """Container for MeSH term information."""

    def __init__(
        self,
        term: str,
        ui: Optional[str] = None,
        tree_number: Optional[str] = None,
        qualifier: Optional[str] = None,
    ):
        self.term = term
        self.ui = ui
        self.tree_number = tree_number
        self.qualifier = qualifier


class MeSHConnector:
    """Connector for MeSH (Medical Subject Headings) API.

    MeSH is the NLM's controlled vocabulary for indexing biomedical literature.
    Used for PubMed/Medline indexing and literature search enhancement.
    """

    MESH_API = "https://id.nlm.nih.gov/mesh/vocab/2024"
    MESH_LOOKUP = "https://id.nlm.nih.gov/mesh/lookup/descriptor"

    def __init__(
        self,
        rate_limit: float = 0.5,
        timeout: int = 30,
    ):
        self.rate_limit = rate_limit
        self.timeout = timeout
        self._last_request = 0.0
        self._cache = {}

    def _rate_limit(self):
        """Apply rate limiting."""
        elapsed = time.time() - self._last_request
        if elapsed < self.rate_limit:
            time.sleep(self.rate_limit - elapsed)
        self._last_request = time.time()

    def search_by_keyword(self, keyword: str) -> list[MeSHTerm]:
        """Search MeSH for terms matching keyword."""
        self._rate_limit()
        
        if keyword.lower() in self._cache:
            return self._cache[keyword.lower()]
        
        try:
            params = {
                "label": keyword,
                "match": "exact",
            }
            
            response = requests.get(
                self.MESH_LOOKUP,
                params=params,
                timeout=self.timeout,
            )
            response.raise_for_status()
            
            terms = self._parse_response(response.text, keyword)
            self._cache[keyword.lower()] = terms
            return terms
            
        except requests.RequestException as e:
            print(f"MeSH search error: {e}")
            return []

    def get_terms_for_paper(self, paper: Paper) -> list[MeSHTerm]:
        """Extract MeSH terms from paper metadata or title/abstract."""
        mesh_terms = []
        
        if paper.mesh_terms:
            for term in paper.mesh_terms:
                mesh_terms.append(MeSHTerm(term=term))
        
        title_keywords = self._extract_keywords(paper.title)
        abstract_keywords = self._extract_keywords(paper.abstract)
        
        all_keywords = set(title_keywords + abstract_keywords)
        
        for keyword in all_keywords:
            terms = self.search_by_keyword(keyword)
            mesh_terms.extend(terms)
        
        return mesh_terms

    def _extract_keywords(self, text: str) -> list[str]:
        """Extract potential keywords from text."""
        if not text:
            return []
        
        words = text.lower().split()
        
        stop_words = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at",
            "to", "for", "of", "with", "by", "from", "as", "is", "are",
            "was", "were", "be", "been", "being", "have", "has", "had",
            "do", "does", "did", "will", "would", "could", "should",
            "may", "might", "must", "shall", "can", "need", "dare",
            "this", "that", "these", "those", "i", "you", "he", "she",
            "it", "we", "they", "what", "which", "who", "whom", "whose",
        }
        
        keywords = [w for w in words if w not in stop_words and len(w) > 3]
        return keywords

    def _parse_response(self, xml: str, original_keyword: str) -> list[MeSHTerm]:
        """Parse MeSH XML response."""
        import re
        
        terms = []
        
        label_pattern = r"<nif:label[^>]*>([^<]+)</nif:label>"
        ui_pattern = r"resource=\"([^\"]+)\""
        
        labels = re.findall(label_pattern, xml)
        uis = re.findall(ui_pattern, xml)
        
        for i, label in enumerate(labels):
            ui = uis[i] if i < len(uis) else None
            
            tree_number = None
            if ui:
                tree_match = re.search(r"(\d{2}\.\d{2}\.\d{3})", ui)
                if tree_match:
                    tree_number = tree_match.group(1)
            
            term = MeSHTerm(
                term=label.strip(),
                ui=ui,
                tree_number=tree_number,
            )
            terms.append(term)
        
        return terms

    def expand_keywords_with_mesh(
        self,
        keywords: list[str],
    ) -> list[str]:
        """Expand keyword list with related MeSH terms."""
        expanded = list(keywords)
        
        for keyword in keywords:
            mesh_terms = self.search_by_keyword(keyword)
            for term in mesh_terms:
                if term.term.lower() not in [k.lower() for k in expanded]:
                    expanded.append(term.term)
        
        return expanded


class MeSHMatcher:
    """Match papers against MeSH terms for enhanced screening."""

    def __init__(self, mesh_connector: Optional[MeSHConnector] = None):
        self.connector = mesh_connector or MeSHConnector()

    def match_paper_to_mesh(
        self,
        paper: Paper,
        target_mesh_terms: list[str],
        threshold: float = 0.3,
    ) -> dict:
        """Match paper against target MeSH terms.
        
        Args:
            paper: Paper to match
            target_mesh_terms: List of target MeSH terms
            threshold: Minimum match score (0-1)
            
        Returns:
            Dictionary with match score and matched terms
        """
        paper_mesh = self.connector.get_terms_for_paper(paper)
        
        if not paper_mesh or not target_mesh_terms:
            return {
                "match_score": 0.0,
                "matched_terms": [],
                "paper_mesh_terms": [],
                "above_threshold": False,
            }
        
        paper_term_set = set(t.term.lower() for t in paper_mesh)
        target_term_set = set(t.lower() for t in target_mesh_terms)
        
        matches = paper_term_set.intersection(target_term_set)
        
        match_score = len(matches) / len(target_term_set) if target_term_set else 0.0
        
        return {
            "match_score": round(match_score, 3),
            "matched_terms": list(matches),
            "paper_mesh_terms": [t.term for t in paper_mesh],
            "above_threshold": match_score >= threshold,
        }

    def batch_match(
        self,
        papers: list[Paper],
        target_mesh_terms: list[str],
        threshold: float = 0.3,
    ) -> list[dict]:
        """Match multiple papers against target MeSH terms."""
        results = []
        
        for paper in papers:
            match_result = self.match_paper_to_mesh(
                paper, target_mesh_terms, threshold
            )
            match_result["paper_id"] = paper.id
            match_result["title"] = paper.title
            results.append(match_result)
        
        return results
