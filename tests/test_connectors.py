"""Tests for DOI and ArXiv connectors."""
import pytest
from unittest.mock import patch, MagicMock

from src.models.schemas import Paper, SourceName


class TestDOIMetadataConnector:
    """Tests for DOIMetadataConnector class."""

    def test_clean_doi(self):
        from src.connectors.doi_connector import DOIMetadataConnector
        
        connector = DOIMetadataConnector()
        
        assert connector._clean_doi("10.1234/test") == "10.1234/test"
        assert connector._clean_doi("https://doi.org/10.1234/test") == "10.1234/test"
        assert connector._clean_doi("doi:10.1234/test") == "10.1234/test"
        assert connector._clean_doi("") is None
        assert connector._clean_doi(None) is None

    def test_rate_limiting(self):
        from src.connectors.doi_connector import DOIMetadataConnector
        import time
        
        connector = DOIMetadataConnector(rate_limit=0.01)
        
        start = time.time()
        connector._rate_limit()
        connector._rate_limit()
        elapsed = time.time() - start
        
        assert elapsed >= 0.01

    @patch('requests.get')
    def test_query_crossref_success(self, mock_get):
        from src.connectors.doi_connector import DOIMetadataConnector
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": {"title": ["Test Paper"]}
        }
        mock_get.return_value = mock_response
        
        connector = DOIMetadataConnector()
        result = connector._query_crossref("10.1234/test")
        
        assert result is not None
        assert result["title"] == ["Test Paper"]

    @patch('requests.get')
    def test_query_crossref_not_found(self, mock_get):
        from src.connectors.doi_connector import DOIMetadataConnector
        
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        connector = DOIMetadataConnector()
        result = connector._query_crossref("10.1234/notfound")
        
        assert result is None

    @patch('requests.get')
    def test_query_crossref_request_exception(self, mock_get):
        from src.connectors.doi_connector import DOIMetadataConnector
        import requests
        
        mock_get.side_effect = requests.RequestException("Network error")
        
        connector = DOIMetadataConnector()
        result = connector._query_crossref("10.1234/test")
        
        assert result is None

    def test_lookup_doi_invalid(self):
        from src.connectors.doi_connector import DOIMetadataConnector
        
        connector = DOIMetadataConnector()
        
        assert connector.lookup_doi("") is None
        assert connector.lookup_doi(None) is None

    def test_enrich_paper_no_doi(self):
        from src.connectors.doi_connector import DOIMetadataConnector
        
        connector = DOIMetadataConnector()
        paper = Paper(
            id="test123",
            source=SourceName.WOS,
            title="Test Paper",
            authors=["John Doe"],
            year=2024,
        )
        
        result = connector.enrich_paper(paper)
        assert result.citations == 0


class TestArxivConnector:
    """Tests for ArxivConnector class."""

    def test_extract_arxiv_id(self):
        from src.connectors.arxiv_connector import ArxivConnector
        
        connector = ArxivConnector()
        
        url = "https://arxiv.org/abs/2301.12345"
        assert connector._extract_arxiv_id(url) == "2301.12345"
        
        url = "https://export.arxiv.org/abs/2301.12345v2"
        assert connector._extract_arxiv_id(url) == "2301.12345"

    def test_clean_text(self):
        from src.connectors.arxiv_connector import ArxivConnector
        
        connector = ArxivConnector()
        
        assert connector._clean_text("hello  world") == "hello world"
        assert connector._clean_text("hello\n\tworld") == "hello world"
        assert connector._clean_text("") == ""
        assert connector._clean_text(None) == ""
