"""CSV loader for importing papers from CSV files."""
import csv
import hashlib
import re
from pathlib import Path
from typing import Optional

from src.models.schemas import Paper, SourceName


class CsvLoader:
    """Loads papers from CSV format files."""

    def __init__(self):
        self._field_mappings = self._get_field_mappings()

    def _get_field_mappings(self) -> dict:
        """Get field mappings for different CSV formats."""
        return {
            "scopus": {
                "title": ["Title"],
                "authors": ["Authors", "Author full names"],
                "abstract": ["Abstract"],
                "year": ["Year"],
                "doi": ["DOI"],
                "url": ["Link"],
                "journal": ["Source title"],
                "keywords": ["Author Keywords", "Index Keywords"],
            },
            "ieee": {
                "title": ["Title"],
                "authors": ["Authors"],
                "abstract": None,
                "year": ["Publication Year"],
                "doi": ["DOI"],
                "url": None,
                "journal": ["Journal/Book"],
                "keywords": None,
            },
            "wos": {
                "title": ["TI", "Title"],
                "authors": ["AU", "Authors"],
                "abstract": ["AB", "Abstract"],
                "year": ["PY", "Year"],
                "doi": ["DI", "DOI"],
                "url": ["URL", "UR"],
                "journal": ["SO", "Journal", "Source"],
                "keywords": ["DE", "Keywords"],
            },
            "generic": {
                "title": ["title", "Title", "TITLE"],
                "authors": ["authors", "Authors", "author", "Author", "AUTHORS"],
                "abstract": ["abstract", "Abstract", "ABSTRACT"],
                "year": ["year", "Year", "YEAR", "publication_year"],
                "doi": ["doi", "DOI", "doi.org"],
                "url": ["url", "URL", "link", "Link"],
                "journal": ["journal", "Journal", "source", "Source", "publication"],
                "keywords": ["keywords", "Keywords", "KEYWORDS"],
            },
        }

    def load_file(
        self, filepath: str, source: SourceName, format_type: str = "generic"
    ) -> list[Paper]:
        """Load papers from a CSV file."""
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"CSV file not found: {filepath}")

        papers = []

        with open(path, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if self._is_valid_row(row):
                    paper = self._parse_row(row, source, format_type)
                    papers.append(paper)

        return papers

    def _is_valid_row(self, row: dict) -> bool:
        """Check if row has valid content."""
        title = row.get("Title", "") or row.get("title", "")
        return bool(title and title.strip())

    def _parse_row(
        self, row: dict, source: SourceName, format_type: str
    ) -> Paper:
        """Parse a single CSV row into a Paper object."""
        mapping = self._field_mappings.get(format_type, self._field_mappings["generic"])

        title = self._get_value(row, mapping["title"])
        if title:
            title = self._clean_text(title)

        authors = self._parse_authors(self._get_value(row, mapping["authors"]))

        abstract = self._get_value(row, mapping["abstract"])
        if abstract:
            abstract = self._clean_text(abstract)

        year_str = self._get_value(row, mapping["year"])
        year = self._parse_year(year_str)

        doi = self._get_value(row, mapping["doi"])
        if doi:
            doi = self._clean_doi(doi)

        url = self._get_value(row, mapping["url"])

        journal = self._get_value(row, mapping["journal"])

        keywords = self._parse_keywords(self._get_value(row, mapping["keywords"]))

        paper_id = self._generate_id(title, doi, authors)

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
            raw_metadata=row,
        )

    def _get_value(self, row: dict, fields: Optional[list]) -> str:
        """Get value from row using field mapping."""
        if fields is None:
            return ""
        for field in fields:
            if field in row and row[field]:
                return row[field]
        return ""

    def _clean_text(self, text: str) -> str:
        """Clean text field."""
        if not text:
            return ""
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def _parse_authors(self, author_str: str) -> list[str]:
        """Parse author string into list."""
        if not author_str:
            return []

        author_str = self._clean_text(author_str)

        for sep in [";", ";"]:
            if sep in author_str:
                authors = author_str.split(sep)
                return [a.strip() for a in authors if a.strip()]

        authors = re.split(r",\s*(?=[A-Z])", author_str)
        return [a.strip() for a in authors if a.strip()]

    def _clean_doi(self, doi: str) -> str:
        """Clean DOI string."""
        doi = doi.strip()
        doi = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", doi)
        return doi

    def _parse_year(self, year_str: str) -> Optional[int]:
        """Parse year from string."""
        if not year_str:
            return None
        match = re.search(r"\d{4}", str(year_str))
        if match:
            return int(match.group())
        return None

    def _parse_keywords(self, keywords_str: str) -> list[str]:
        """Parse keywords string into list."""
        if not keywords_str:
            return []

        keywords = re.split(r"[,;]", keywords_str)
        return [k.strip() for k in keywords if k.strip()]

    def _generate_id(self, title: str, doi: str, authors: list[str]) -> str:
        """Generate unique ID."""
        content = f"{title}{doi}{','.join(authors[:3])}".encode("utf-8")
        return hashlib.md5(content).hexdigest()[:16]


def load_csv(
    filepath: str, source: SourceName, format_type: str = "generic"
) -> list[Paper]:
    """Convenience function to load CSV file."""
    loader = CsvLoader()
    return loader.load_file(filepath, source, format_type)
