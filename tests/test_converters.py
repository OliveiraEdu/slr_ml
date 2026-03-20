"""Tests for markdown to LaTeX converter."""
import pytest
import os
from tempfile import TemporaryDirectory

from src.converters.md_to_latex import (
    convert_markdown_to_latex,
    wrap_in_document,
    _convert_lists,
    _convert_tables,
    _convert_single_table,
    _parse_alignments,
)


class TestConvertMarkdownToLatex:
    """Tests for convert_markdown_to_latex function."""

    def test_convert_headers(self):
        markdown = """# Main Title
## Chapter 1
### Section 1.1
#### Subsection 1.1.1
##### Paragraph
###### Subparagraph"""
        latex = convert_markdown_to_latex(markdown)
        assert "\\part{" in latex
        assert "\\chapter{" in latex
        assert "\\section{" in latex
        assert "\\subsection{" in latex
        assert "\\subsubsection{" in latex

    def test_convert_bold_and_italic(self):
        markdown = """This is **bold** and *italic*.
This is __bold__ and _italic_."""
        latex = convert_markdown_to_latex(markdown)
        assert "\\textbf{" in latex
        assert "\\textit{" in latex

    def test_convert_inline_code(self):
        markdown = "Use `print()` for output."
        latex = convert_markdown_to_latex(markdown)
        assert "\\texttt{" in latex

    def test_convert_verbatim_blocks(self):
        markdown = """```python
def hello():
    print("Hello")
```"""
        latex = convert_markdown_to_latex(markdown)
        assert "\\begin{verbatim}" in latex
        assert "\\end{verbatim}" in latex

    def test_convert_links(self):
        markdown = "[Link Text](https://example.com)"
        latex = convert_markdown_to_latex(markdown)
        assert "Link Text" in latex
        assert "https://example.com" not in latex

    def test_convert_images(self):
        markdown = "![Alt text](image.png)"
        latex = convert_markdown_to_latex(markdown)
        assert "\\includegraphics" in latex
        assert "\\caption{" in latex

    def test_convert_horizontal_rule(self):
        markdown = "Some text\n\n---\n\nMore text"
        latex = convert_markdown_to_latex(markdown)
        assert "\\hline" in latex

    def test_extract_mermaid_diagrams(self):
        markdown = """# Document
```mermaid
graph TD
    A --> B
```"""
        with TemporaryDirectory() as tmpdir:
            latex = convert_markdown_to_latex(
                markdown,
                output_dir=tmpdir,
                base_filename="test_diagram"
            )
            mermaid_files = [f for f in os.listdir(tmpdir) if f.endswith(".mermaid")]
            assert len(mermaid_files) == 1
            assert "test_diagram" in mermaid_files[0]


class TestConvertLists:
    """Tests for _convert_lists function."""

    def test_convert_unordered_list(self):
        markdown = """- Item 1
- Item 2
- Item 3"""
        latex = _convert_lists(markdown)
        assert "\\begin{itemize}" in latex
        assert "\\item Item 1" in latex
        assert "\\end{itemize}" in latex

    def test_convert_ordered_list(self):
        markdown = """1. First
2. Second
3. Third"""
        latex = _convert_lists(markdown)
        assert "\\begin{enumerate}" in latex
        assert "\\item Second" in latex
        assert "\\end{enumerate}" in latex

    def test_convert_nested_lists(self):
        markdown = """- Item 1
    - Nested 1
    - Nested 2
- Item 2"""
        latex = _convert_lists(markdown)
        assert "\\begin{itemize}" in latex


class TestConvertTables:
    """Tests for table conversion functions."""

    def test_parse_alignments(self):
        separator = "| :-- | :---: | --: |"
        alignments = _parse_alignments(separator)
        assert alignments == ['l', 'c', 'r']

    def test_parse_alignments_default(self):
        separator = "| --- | --- |"
        alignments = _parse_alignments(separator)
        assert alignments == ['l', 'l']

    def test_convert_simple_table(self):
        markdown = """| Header 1 | Header 2 |
| --- | --- |
| Cell 1 | Cell 2 |
| Cell 3 | Cell 4 |"""
        latex = _convert_tables(markdown)
        assert "\\begin{table}" in latex
        assert "\\begin{tabular}" in latex
        assert "\\end{tabular}" in latex
        assert "\\end{table}" in latex

    def test_convert_alignment_table(self):
        markdown = """| Left | Center | Right |
| :--- | :-----: | ----: |
| L | C | R |"""
        latex = _convert_tables(markdown)
        assert "\\begin{table}" in latex
        assert "l" in latex
        assert "c" in latex
        assert "r" in latex


class TestWrapInDocument:
    """Tests for wrap_in_document function."""

    def test_wrap_in_document(self):
        latex_content = "\\section{Test}"
        wrapped = wrap_in_document(latex_content, "Test Title")
        assert "\\documentclass" in wrapped
        assert "\\title{Test Title}" in wrapped
        assert "\\begin{document}" in wrapped
        assert "\\end{document}" in wrapped
        assert latex_content in wrapped

    def test_wrap_in_document_with_packages(self):
        latex_content = "\\section{Test}"
        wrapped = wrap_in_document(latex_content)
        assert "\\usepackage" in wrapped
        assert "\\usepackage{graphicx}" in wrapped
        assert "\\usepackage{hyperref}" in wrapped
