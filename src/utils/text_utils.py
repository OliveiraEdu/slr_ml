"""Shared utility functions for text processing."""
import re
import hashlib
from typing import Optional


def clean_text(text: str) -> str:
    """Clean text field by normalizing whitespace.
    
    Args:
        text: Input text to clean
        
    Returns:
        Cleaned text with normalized whitespace
    """
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def clean_bibtex_text(text: str) -> str:
    """Clean BibTeX field text (handles braces).
    
    Args:
        text: Input BibTeX text to clean
        
    Returns:
        Cleaned text without surrounding braces
    """
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text)
    text = text.strip("{}")
    return text


def clean_doi(doi: str) -> Optional[str]:
    """Clean and normalize DOI string.
    
    Args:
        doi: DOI string (with or without URL prefix)
        
    Returns:
        Cleaned DOI or None if empty
    """
    if not doi:
        return None
    doi = doi.strip()
    doi = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", doi)
    doi = doi.replace("doi:", "")
    return doi if doi else None


def normalize_doi(doi: str) -> Optional[str]:
    """Alias for clean_doi for API consistency."""
    return clean_doi(doi)


def generate_paper_id(title: str, doi: Optional[str] = "", authors: Optional[list[str]] = None) -> str:
    """Generate a unique paper ID using MD5 hash.
    
    Args:
        title: Paper title
        doi: Paper DOI (optional)
        authors: List of authors (optional, uses first 3)
        
    Returns:
        16-character hex string ID
    """
    if authors:
        author_part = ",".join(authors[:3])
    else:
        author_part = ""
    doi_str = doi if doi else ""
    content = f"{title}{doi_str}{author_part}".encode("utf-8")
    return hashlib.md5(content).hexdigest()[:16]


def generate_bibtex_id(entry: dict) -> str:
    """Generate ID from BibTeX entry fields.
    
    Args:
        entry: BibTeX entry dictionary
        
    Returns:
        16-character hex string ID
    """
    title = entry.get("title", "")
    doi = entry.get("doi", "")
    author = entry.get("author", "")
    content = f"{title}{doi}{author}".encode("utf-8")
    return hashlib.md5(content).hexdigest()[:16]
