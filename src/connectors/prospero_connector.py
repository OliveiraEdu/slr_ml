"""PROSPERO connector for systematic review protocol registration."""
import time
from typing import Optional
import requests

from src.models.schemas import Paper


class PROSPEROMetadata:
    """Container for PROSPERO protocol registration."""

    def __init__(
        self,
        registration_number: str,
        title: str,
        citation: Optional[str] = None,
        review_type: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[str] = None,
        completion_date: Optional[str] = None,
        authors: Optional[list[str]] = None,
        contact_person: Optional[str] = None,
        protocol_link: Optional[str] = None,
        database: Optional[str] = None,
    ):
        self.registration_number = registration_number
        self.title = title
        self.citation = citation
        self.review_type = review_type
        self.status = status
        self.start_date = start_date
        self.completion_date = completion_date
        self.authors = authors or []
        self.contact_person = contact_person
        self.protocol_link = protocol_link
        self.database = database


class PROSPEROConnector:
    """Connector for PROSPERO API.

    PROSPERO is an international register of systematic reviews.
    API allows searching for registered protocols.
    """

    PROSPERO_API = "https://www.crd.york.ac.uk/PROSPERO/"
    PROSPERO_API_V1 = "https://www.crd.york.ac.uk/PROSPERO/api/v1"

    def __init__(
        self,
        rate_limit: float = 0.5,
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

    def search_by_title(self, title: str) -> list[PROSPEROMetadata]:
        """Search PROSPERO for protocols matching title."""
        self._rate_limit()
        
        try:
            search_url = f"{self.PROSPERO_API}search.asp"
            params = {
                "keywords": title,
                "results": 10,
            }
            
            response = requests.get(
                search_url,
                params=params,
                timeout=self.timeout,
            )
            response.raise_for_status()
            
            results = self._parse_search_results(response.text)
            return results
            
        except requests.RequestException as e:
            print(f"PROSPERO search error: {e}")
            return []

    def search_by_doi(self, doi: str) -> Optional[PROSPEROMetadata]:
        """Search PROSPERO for a specific DOI."""
        self._rate_limit()
        
        try:
            search_url = f"{self.PROSPERO_API}search.asp"
            params = {
                "doi": doi,
                "results": 1,
            }
            
            response = requests.get(
                search_url,
                params=params,
                timeout=self.timeout,
            )
            response.raise_for_status()
            
            results = self._parse_search_results(response.text)
            return results[0] if results else None
            
        except requests.RequestException as e:
            print(f"PROSPERO search error: {e}")
            return None

    def check_paper_for_protocol(self, paper: Paper) -> Optional[PROSPEROMetadata]:
        """Check if a paper has a registered protocol in PROSPERO."""
        if paper.title:
            return self.search_by_title(paper.title)
        return None

    def _parse_search_results(self, html: str) -> list[PROSPEROMetadata]:
        """Parse PROSPERO search results HTML."""
        import re
        
        results = []
        
        pattern = r"CRD\d{8}\d+"
        matches = re.findall(pattern, html)
        
        title_pattern = r"<h3>(.*?)</h3>"
        titles = re.findall(title_pattern, html)
        
        for i, match in enumerate(matches):
            metadata = PROSPEROMetadata(
                registration_number=match,
                title=titles[i] if i < len(titles) else "Unknown",
                database="PROSPERO",
                status="Registered" if match else "Unknown",
            )
            results.append(metadata)
        
        return results

    def get_registration_status(self, title: str) -> dict:
        """Get registration status for a title.
        
        Returns:
            Dictionary with has_registration, registration_details
        """
        results = self.search_by_title(title)
        
        if results:
            return {
                "has_registration": True,
                "count": len(results),
                "registrations": [
                    {
                        "registration_number": r.registration_number,
                        "title": r.title,
                        "status": r.status,
                    }
                    for r in results
                ],
            }
        
        return {
            "has_registration": False,
            "count": 0,
            "registrations": [],
        }
