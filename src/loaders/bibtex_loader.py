"""BibTeX loader for importing papers from BibTeX files."""
import hashlib
import re
from pathlib import Path
from typing import Optional

import bibtexparser

from src.models.schemas import Paper, SourceName


class BibtexLoader:
    """Loads papers from BibTeX format files."""

    FIELD_MAPPING = {
        "title": "title",
        "author": "authors",
        "abstract": "abstract",
        "year": "year",
        "doi": "doi",
        "url": "url",
        "journal": "journal",
        "booktitle": "journal",
        "keywords": "keywords",
    }

    def __init__(self):
        self._parser = bibtexparser.bparser.BibTexParser(common_strings=True)

    def load_file(self, filepath: str, source: SourceName) -> list[Paper]:
        """Load papers from a BibTeX file."""
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"BibTeX file not found: {filepath}")

        with open(path, "r", encoding="utf-8") as f:
            bib_database = bibtexparser.load(f, parser=self._parser)

        papers = []
        for entry in bib_database.entries:
            paper = self._parse_entry(entry, source)
            papers.append(paper)

        return papers

    def _parse_entry(self, entry: dict, source: SourceName) -> Paper:
        """Parse a single BibTeX entry into a Paper object."""
        paper_id = self._generate_id(entry)

        title = entry.get("title", "")
        if title:
            title = self._clean_text(title)

        authors = self._parse_authors(entry.get("author", ""))

        abstract = entry.get("abstract", "")
        if abstract:
            abstract = self._clean_text(abstract)

        year_str = entry.get("year", "")
        year = None
        if year_str:
            try:
                year = int(year_str)
            except (ValueError, TypeError):
                pass

        doi = entry.get("doi", "")
        if doi:
            doi = self._clean_doi(doi)

        url = entry.get("url", "")

        journal = entry.get("journal", "") or entry.get("booktitle", "")

        keywords_str = entry.get("keywords", "")
        keywords = self._parse_keywords(keywords_str)

        return Paper(
            id=paper_id,
            source=source,
            title=title,
            authors=authors,
            abstract=abstract,
            year=year,
            doi=doi,
            url=url,
            journal=journal,
            keywords=keywords,
            raw_metadata=entry,
        )

    def _generate_id(self, entry: dict) -> str:
        """Generate a unique ID for the paper."""
        title = entry.get("title", "")
        doi = entry.get("doi", "")
        author = entry.get("author", "")

        content = f"{title}{doi}{author}".encode("utf-8")
        return hashlib.md5(content).hexdigest()[:16]

    def _clean_text(self, text: str) -> str:
        """Clean BibTeX field text."""
        if not text:
            return ""
        text = re.sub(r"\s+", " ", text)
        text = text.strip("{}")
        return text

    def _parse_authors(self, author_str: str) -> list[str]:
        """Parse author string into list of authors."""
        if not author_str:
            return []

        author_str = self._clean_text(author_str)

        authors = re.split(r"\s+and\s+", author_str, flags=re.IGNORECASE)

        cleaned = []
        for author in authors:
            author = author.strip()
            if author:
                cleaned.append(author)

        return cleaned

    def _clean_doi(self, doi: str) -> str:
        """Clean DOI string."""
        doi = doi.strip()
        doi = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", doi)
        return doi

    def _parse_keywords(self, keywords_str: str) -> list[str]:
        """Parse keywords string into list."""
        if not keywords_str:
            return []

        keywords = re.split(r"[,;]", keywords_str)
        return [k.strip() for k in keywords if k.strip()]


def load_bibtex(filepath: str, source: SourceName) -> list[Paper]:
    """Convenience function to load BibTeX file."""
    loader = BibtexLoader()
    return loader.load_file(filepath, source)
