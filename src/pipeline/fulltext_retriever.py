"""Full-text retrieval system for systematic literature reviews."""
from dataclasses import dataclass
from typing import Optional
from pathlib import Path
import logging
import time

import httpx


@dataclass
class FullTextResult:
    """Result of full-text retrieval attempt."""
    paper_id: str
    success: bool
    content: Optional[str] = None
    source: Optional[str] = None
    path: Optional[str] = None
    error: Optional[str] = None
    cached: bool = False


class FullTextRetriever:
    """Retrieve full-text for papers using multiple strategies."""
    
    def __init__(
        self,
        cache_dir: str = "cache/fulltext",
        output_dir: str = "outputs/fulltext",
        timeout: int = 30,
    ):
        self.cache_dir = Path(cache_dir)
        self.output_dir = Path(output_dir)
        self.timeout = timeout
        self.logger = logging.getLogger(__name__)
        
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def retrieve_for_paper(
        self,
        paper_id: str,
        doi: Optional[str] = None,
        arxiv_id: Optional[str] = None,
        force: bool = False,
    ) -> FullTextResult:
        """Retrieve full-text for a single paper."""
        cache_path = self.cache_dir / f"{paper_id}.pdf"
        
        if cache_path.exists() and not force:
            return FullTextResult(
                paper_id=paper_id,
                success=True,
                source="cache",
                path=str(cache_path),
                cached=True,
            )
        
        if doi:
            result = self._retrieve_from_doi(doi, paper_id)
            if result.success:
                return result
        
        if arxiv_id:
            result = self._retrieve_from_arxiv(arxiv_id, paper_id)
            if result.success:
                return result
        
        return FullTextResult(
            paper_id=paper_id,
            success=False,
            error="No retrieval strategy succeeded",
        )
    
    def _retrieve_from_doi(self, doi: str, paper_id: str) -> FullTextResult:
        """Retrieve full-text via DOI."""
        url = f"https://doi.org/{doi}"
        
        try:
            with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
                response = client.get(url)
                
                if response.status_code == 200:
                    content_type = response.headers.get("content-type", "")
                    
                    if "pdf" in content_type.lower():
                        return self._save_pdf(response.content, paper_id, "doi")
                    
                    html = response.text
                    pdf_url = self._extract_pdf_url(html)
                    
                    if pdf_url:
                        pdf_response = client.get(pdf_url)
                        if pdf_response.status_code == 200:
                            return self._save_pdf(pdf_response.content, paper_id, "doi_pdf")
                    
                    return FullTextResult(
                        paper_id=paper_id,
                        success=False,
                        error="DOI resolved but no PDF found",
                    )
                else:
                    return FullTextResult(
                        paper_id=paper_id,
                        success=False,
                        error=f"DOI request failed: {response.status_code}",
                    )
                    
        except Exception as e:
            self.logger.error(f"DOI retrieval failed for {doi}: {e}")
            return FullTextResult(
                paper_id=paper_id,
                success=False,
                error=str(e),
            )
    
    def _retrieve_from_arxiv(self, arxiv_id: str, paper_id: str) -> FullTextResult:
        """Retrieve full-text from arXiv."""
        clean_id = arxiv_id.replace("arXiv:", "").strip()
        
        urls = [
            f"https://arxiv.org/pdf/{clean_id}.pdf",
            f"https://arxiv.org/e-print/{clean_id}",
        ]
        
        for url in urls:
            try:
                with httpx.Client(timeout=self.timeout * 2) as client:
                    response = client.get(url)
                    
                    if response.status_code == 200:
                        content_type = response.headers.get("content-type", "")
                        
                        if "pdf" in content_type.lower() or len(response.content) > 10000:
                            return self._save_pdf(response.content, paper_id, "arxiv")
                    
            except Exception as e:
                self.logger.debug(f"ArXiv attempt failed: {e}")
                continue
        
        return FullTextResult(
            paper_id=paper_id,
            success=False,
            error="ArXiv PDF not found",
        )
    
    def _extract_pdf_url(self, html: str) -> Optional[str]:
        """Extract PDF URL from HTML page."""
        import re
        
        patterns = [
            r'href="([^"]*\.pdf[^"]*)"',
            r'data-href="([^"]*\.pdf[^"]*)"',
            r'"pdfUrl"\s*:\s*"([^"]+)"',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def _save_pdf(self, content: bytes, paper_id: str, source: str) -> FullTextResult:
        """Save PDF content to cache."""
        cache_path = self.cache_dir / f"{paper_id}.pdf"
        output_path = self.output_dir / f"{paper_id}.pdf"
        
        cache_path.write_bytes(content)
        output_path.write_bytes(content)
        
        return FullTextResult(
            paper_id=paper_id,
            success=True,
            source=source,
            path=str(output_path),
        )
    
    def batch_retrieve(
        self,
        papers: list[dict],
        delay: float = 1.0,
        max_retries: int = 2,
    ) -> dict:
        """Retrieve full-text for multiple papers."""
        results = {
            "successful": [],
            "failed": [],
            "total": len(papers),
        }
        
        for i, paper in enumerate(papers):
            paper_id = paper.get("id") or paper.get("paper_id")
            doi = paper.get("doi")
            arxiv_id = paper.get("arxiv_id")
            
            for attempt in range(max_retries):
                result = self.retrieve_for_paper(paper_id, doi, arxiv_id)
                
                if result.success:
                    results["successful"].append({
                        "paper_id": paper_id,
                        "source": result.source,
                        "path": result.path,
                    })
                    break
                else:
                    if attempt < max_retries - 1:
                        time.sleep(delay)
                    else:
                        results["failed"].append({
                            "paper_id": paper_id,
                            "doi": doi,
                            "error": result.error,
                        })
            
            if (i + 1) % 10 == 0:
                self.logger.info(f"Progress: {i + 1}/{len(papers)} papers processed")
        
        return results


class PDFTextExtractor:
    """Extract text from PDF files."""
    
    def extract(self, pdf_path: str) -> Optional[str]:
        """Extract text from PDF file."""
        try:
            import PyPDF2
        except ImportError:
            self._try_pdfplumber(pdf_path)
            return None
        
        try:
            with open(pdf_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                text_parts = []
                
                for page in reader.pages:
                    text = page.extract_text()
                    if text:
                        text_parts.append(text)
                
                return "\n\n".join(text_parts)
        except Exception as e:
            logging.getLogger(__name__).error(f"PDF extraction failed: {e}")
            return None
    
    def _try_pdfplumber(self, pdf_path: str) -> Optional[str]:
        """Fallback extraction using pdfplumber."""
        try:
            import pdfplumber
            
            with pdfplumber.open(pdf_path) as pdf:
                text_parts = []
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        text_parts.append(text)
                return "\n\n".join(text_parts)
        except ImportError:
            return None
        except Exception:
            return None
