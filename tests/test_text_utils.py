"""Tests for text utility functions."""
import pytest

from src.utils.text_utils import (
    clean_text,
    clean_bibtex_text,
    clean_doi,
    normalize_doi,
    generate_paper_id,
    generate_bibtex_id,
)


class TestCleanText:
    """Tests for clean_text function."""

    def test_clean_text_normalizes_whitespace(self):
        assert clean_text("hello  world") == "hello world"
        assert clean_text("hello\n\tworld") == "hello world"
        assert clean_text("  hello  ") == "hello"

    def test_clean_text_empty_string(self):
        assert clean_text("") == ""

    def test_clean_text_none_returns_empty(self):
        assert clean_text(None) == ""

    def test_clean_text_no_change_needed(self):
        assert clean_text("hello world") == "hello world"


class TestCleanBibtexText:
    """Tests for clean_bibtex_text function."""

    def test_clean_bibtex_text_removes_braces(self):
        assert clean_bibtex_text("{Hello World}") == "Hello World"

    def test_clean_bibtex_text_normalizes_whitespace(self):
        assert clean_bibtex_text("{  Hello  }  {  World  }") == "  Hello  }  {  World"

    def test_clean_bibtex_text_empty_string(self):
        assert clean_bibtex_text("") == ""

    def test_clean_bibtex_text_none_returns_empty(self):
        assert clean_bibtex_text(None) == ""


class TestCleanDoi:
    """Tests for clean_doi function."""

    def test_clean_doi_removes_https_doi_org(self):
        assert clean_doi("https://doi.org/10.1234/test") == "10.1234/test"
        assert clean_doi("http://doi.org/10.1234/test") == "10.1234/test"

    def test_clean_doi_removes_dx_doi_org(self):
        assert clean_doi("https://dx.doi.org/10.1234/test") == "10.1234/test"

    def test_clean_doi_removes_doi_prefix(self):
        assert clean_doi("doi:10.1234/test") == "10.1234/test"

    def test_clean_doi_trims_whitespace(self):
        assert clean_doi("  10.1234/test  ") == "10.1234/test"

    def test_clean_doi_empty_returns_none(self):
        assert clean_doi("") is None
        assert clean_doi("   ") is None

    def test_clean_doi_none_returns_none(self):
        assert clean_doi(None) is None

    def test_clean_doi_passthrough(self):
        assert clean_doi("10.1234/test") == "10.1234/test"


class TestNormalizeDoi:
    """Tests for normalize_doi function (alias of clean_doi)."""

    def test_normalize_doi_same_as_clean_doi(self):
        assert normalize_doi("https://doi.org/10.1234/test") == "10.1234/test"
        assert normalize_doi("10.1234/test") == "10.1234/test"


class TestGeneratePaperId:
    """Tests for generate_paper_id function."""

    def test_generate_paper_id_length(self):
        paper_id = generate_paper_id("Test Title")
        assert len(paper_id) == 16

    def test_generate_paper_id_deterministic(self):
        id1 = generate_paper_id("Test Title", "10.1234/test")
        id2 = generate_paper_id("Test Title", "10.1234/test")
        assert id1 == id2

    def test_generate_paper_id_different_inputs(self):
        id1 = generate_paper_id("Title 1")
        id2 = generate_paper_id("Title 2")
        assert id1 != id2

    def test_generate_paper_id_with_authors(self):
        id1 = generate_paper_id("Title", authors=["Author 1", "Author 2"])
        id2 = generate_paper_id("Title", authors=["Author 1", "Author 2"])
        assert id1 == id2

    def test_generate_paper_id_none_doi(self):
        id1 = generate_paper_id("Title", None)
        assert len(id1) == 16


class TestGenerateBibtexId:
    """Tests for generate_bibtex_id function."""

    def test_generate_bibtex_id_length(self):
        entry = {"title": "Test", "doi": "10.1234/test", "author": "John Doe"}
        paper_id = generate_bibtex_id(entry)
        assert len(paper_id) == 16

    def test_generate_bibtex_id_deterministic(self):
        entry = {"title": "Test", "doi": "10.1234/test", "author": "John Doe"}
        id1 = generate_bibtex_id(entry)
        id2 = generate_bibtex_id(entry)
        assert id1 == id2

    def test_generate_bibtex_id_empty_fields(self):
        entry = {}
        paper_id = generate_bibtex_id(entry)
        assert len(paper_id) == 16
