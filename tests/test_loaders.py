"""Tests for BibTeX and CSV loaders."""
import os
import pytest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.models.schemas import SourceName


class TestBibtexLoader:
    """Tests for BibtexLoader class."""

    def test_load_file_not_found(self):
        from src.loaders.bibtex_loader import BibtexLoader
        
        loader = BibtexLoader()
        with pytest.raises(FileNotFoundError):
            loader.load_file("/nonexistent/file.bib", SourceName.WOS)

    def test_load_bibtex_single_entry(self):
        from src.loaders.bibtex_loader import BibtexLoader
        
        bibtex_content = """@article{test2024,
            author = {John Doe},
            title = {Test Paper Title},
            year = {2024},
            journal = {Test Journal},
            doi = {10.1234/test}
        }"""
        
        with TemporaryDirectory() as tmpdir:
            bibtex_path = os.path.join(tmpdir, "test.bib")
            with open(bibtex_path, "w") as f:
                f.write(bibtex_content)
            
            loader = BibtexLoader()
            papers = loader.load_file(bibtex_path, SourceName.WOS)
            
            assert len(papers) == 1
            assert papers[0].title == "Test Paper Title"
            assert papers[0].authors == ["John Doe"]
            assert papers[0].year == 2024
            assert papers[0].journal == "Test Journal"
            assert papers[0].doi == "10.1234/test"

    def test_load_bibtex_multiple_entries(self):
        from src.loaders.bibtex_loader import BibtexLoader
        
        bibtex_content = """@article{paper1,
            author = {John Doe and Jane Smith},
            title = {First Paper},
            year = {2024}
        }
        @inproceedings{paper2,
            author = {Alice Bob},
            title = {Second Paper},
            year = {2023}
        }"""
        
        with TemporaryDirectory() as tmpdir:
            bibtex_path = os.path.join(tmpdir, "test.bib")
            with open(bibtex_path, "w") as f:
                f.write(bibtex_content)
            
            loader = BibtexLoader()
            papers = loader.load_file(bibtex_path, SourceName.IEEE)
            
            assert len(papers) == 2

    def test_load_bibtex_with_abstract(self):
        from src.loaders.bibtex_loader import BibtexLoader
        
        bibtex_content = """@article{test2024,
            author = {John Doe},
            title = {Test Paper},
            year = {2024},
            abstract = {This is a test abstract.}
        }"""
        
        with TemporaryDirectory() as tmpdir:
            bibtex_path = os.path.join(tmpdir, "test.bib")
            with open(bibtex_path, "w") as f:
                f.write(bibtex_content)
            
            loader = BibtexLoader()
            papers = loader.load_file(bibtex_path, SourceName.SCOPUS)
            
            assert len(papers) == 1
            assert papers[0].abstract == "This is a test abstract."

    def test_load_bibtex_with_doi_url(self):
        from src.loaders.bibtex_loader import BibtexLoader
        
        bibtex_content = """@article{test2024,
            author = {John Doe},
            title = {Test Paper},
            year = {2024},
            doi = {https://doi.org/10.1234/test}
        }"""
        
        with TemporaryDirectory() as tmpdir:
            bibtex_path = os.path.join(tmpdir, "test.bib")
            with open(bibtex_path, "w") as f:
                f.write(bibtex_content)
            
            loader = BibtexLoader()
            papers = loader.load_file(bibtex_path, SourceName.WOS)
            
            assert len(papers) == 1
            assert papers[0].doi == "10.1234/test"

    def test_load_bibtex_with_keywords(self):
        from src.loaders.bibtex_loader import BibtexLoader
        
        bibtex_content = """@article{test2024,
            author = {John Doe},
            title = {Test Paper},
            year = {2024},
            keywords = {machine learning, deep learning, neural networks}
        }"""
        
        with TemporaryDirectory() as tmpdir:
            bibtex_path = os.path.join(tmpdir, "test.bib")
            with open(bibtex_path, "w") as f:
                f.write(bibtex_content)
            
            loader = BibtexLoader()
            papers = loader.load_file(bibtex_path, SourceName.ACM)
            
            assert len(papers) == 1
            assert "machine learning" in papers[0].keywords
            assert "deep learning" in papers[0].keywords


class TestCsvLoader:
    """Tests for CsvLoader class."""

    def test_load_file_not_found(self):
        from src.loaders.csv_loader import CsvLoader
        
        loader = CsvLoader()
        with pytest.raises(FileNotFoundError):
            loader.load_file("/nonexistent/file.csv", SourceName.WOS)

    def test_load_csv_generic_format(self):
        from src.loaders.csv_loader import CsvLoader
        
        csv_content = """title,authors,year,journal,doi
"Test Paper","John Doe",2024,"Test Journal","10.1234/test"
"Another Paper","Jane Smith",2023,"Another Journal","10.5678/test2"
"""
        
        with TemporaryDirectory() as tmpdir:
            csv_path = os.path.join(tmpdir, "test.csv")
            with open(csv_path, "w") as f:
                f.write(csv_content)
            
            loader = CsvLoader()
            papers = loader.load_file(csv_path, SourceName.WOS, format_type="generic")
            
            assert len(papers) == 2
            assert papers[0].title == "Test Paper"
            assert papers[0].authors == ["John Doe"]
            assert papers[0].year == 2024

    def test_load_csv_semicolon_separator(self):
        from src.loaders.csv_loader import CsvLoader
        
        csv_content = """title;authors;year
"Test Paper";"John Doe;Jane Smith";2024
"""
        
        with TemporaryDirectory() as tmpdir:
            csv_path = os.path.join(tmpdir, "test.csv")
            with open(csv_path, "w") as f:
                f.write(csv_content)
            
            loader = CsvLoader()
            papers = loader.load_file(csv_path, SourceName.IEEE, format_type="generic")
            
            assert len(papers) == 1
            assert "John Doe" in papers[0].authors
            assert "Jane Smith" in papers[0].authors

    def test_load_csv_comma_separator(self):
        from src.loaders.csv_loader import CsvLoader
        
        csv_content = """title,authors,year
"Test Paper","John Doe,Jane Smith",2024
"""
        
        with TemporaryDirectory() as tmpdir:
            csv_path = os.path.join(tmpdir, "test.csv")
            with open(csv_path, "w") as f:
                f.write(csv_content)
            
            loader = CsvLoader()
            papers = loader.load_file(csv_path, SourceName.SCOPUS, format_type="generic")
            
            assert len(papers) == 1
            assert "John Doe" in papers[0].authors

    def test_load_csv_skips_empty_rows(self):
        from src.loaders.csv_loader import CsvLoader
        
        csv_content = """title,authors,year
"Test Paper","John Doe",2024

"Second Paper","Jane Smith",2023
"""
        
        with TemporaryDirectory() as tmpdir:
            csv_path = os.path.join(tmpdir, "test.csv")
            with open(csv_path, "w") as f:
                f.write(csv_content)
            
            loader = CsvLoader()
            papers = loader.load_file(csv_path, SourceName.WOS, format_type="generic")
            
            assert len(papers) == 2

    def test_load_csv_with_abstract(self):
        from src.loaders.csv_loader import CsvLoader
        
        csv_content = """title,authors,year,abstract
"Test Paper","John Doe",2024,"This is an abstract"
"""
        
        with TemporaryDirectory() as tmpdir:
            csv_path = os.path.join(tmpdir, "test.csv")
            with open(csv_path, "w") as f:
                f.write(csv_content)
            
            loader = CsvLoader()
            papers = loader.load_file(csv_path, SourceName.WOS, format_type="generic")
            
            assert len(papers) == 1
            assert papers[0].abstract == "This is an abstract"

    def test_load_csv_scopus_format(self):
        from src.loaders.csv_loader import CsvLoader
        
        csv_content = """Title,Authors,Year,DOI,Abstract
"Test Paper","John Doe",2024,"10.1234/test","Abstract text"
"""
        
        with TemporaryDirectory() as tmpdir:
            csv_path = os.path.join(tmpdir, "scopus.csv")
            with open(csv_path, "w") as f:
                f.write(csv_content)
            
            loader = CsvLoader()
            papers = loader.load_file(csv_path, SourceName.SCOPUS, format_type="scopus")
            
            assert len(papers) == 1
            assert papers[0].title == "Test Paper"
