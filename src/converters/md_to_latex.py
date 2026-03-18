"""Markdown to LaTeX converter for PRISMA reports."""
import os
import re
from pathlib import Path
from typing import Optional


def convert_markdown_to_latex(
    markdown_content: str,
    output_dir: Optional[str] = None,
    base_filename: str = "diagram"
) -> str:
    """Convert markdown content to LaTeX format.
    
    Args:
        markdown_content: The markdown text to convert
        output_dir: Directory to save extracted mermaid diagrams (if None, no extraction)
        base_filename: Base name for mermaid diagram files
    """
    latex = markdown_content
    diagram_count = [0]

    def extract_mermaid(match):
        diagram_content = match.group(1).strip()
        diagram_count[0] += 1
        diagram_name = f"{base_filename}_{diagram_count[0]:03d}.mermaid"
        
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            diagram_path = os.path.join(output_dir, diagram_name)
            with open(diagram_path, 'w') as f:
                f.write(diagram_content)
            caption = f"Mermaid diagram {diagram_count[0]}"
            return f'\\begin{{figure}}[htbp]\n\\centering\n\\textbf{{{caption}}}\n\\begin{{verbatim}}\n{diagram_content}\\end{{verbatim}}\n\\caption{{{caption} - see {diagram_name}}}\n\\end{{figure}}'
        
        return f'\\begin{{verbatim}}\n{diagram_content}\\end{{verbatim}}'

    latex = re.sub(r'```mermaid\n(.*?)```', extract_mermaid, latex, flags=re.DOTALL)

    latex = re.sub(r'^###### (.+)$', r'\\subsubsection{\1}', latex, flags=re.MULTILINE)
    latex = re.sub(r'^##### (.+)$', r'\\subsection{\1}', latex, flags=re.MULTILINE)
    latex = re.sub(r'^#### (.+)$', r'\\section{\1}', latex, flags=re.MULTILINE)
    latex = re.sub(r'^### (.+)$', r'\\section{\1}', latex, flags=re.MULTILINE)
    latex = re.sub(r'^## (.+)$', r'\\chapter{\1}', latex, flags=re.MULTILINE)
    latex = re.sub(r'^# (.+)$', r'\\part{\1}', latex, flags=re.MULTILINE)

    latex = re.sub(r'\*\*(.+?)\*\*', r'\\textbf{\1}', latex)
    latex = re.sub(r'\*(.+?)\*', r'\\textit{\1}', latex)
    latex = re.sub(r'__(.+?)__', r'\\textbf{\1}', latex)
    latex = re.sub(r'_(.+?)_', r'\\textit{\1}', latex)

    latex = re.sub(r'```(\w+)?\n(.*?)```', r'\\begin{verbatim}\2\\end{verbatim}', latex, flags=re.DOTALL)

    latex = re.sub(r'`(.+?)`', r'\\texttt{\1}', latex)

    latex = re.sub(r'^---+$', r'\\hline', latex)
    latex = re.sub(r'^\*\*\*+$', r'\\hline', latex)

    latex = re.sub(r'^\s*[-*+] (.+)$', r'\\item \1', latex, flags=re.MULTILINE)

    latex = re.sub(r'^\s*(\d+)\. (.+)$', r'\\item \2', latex, flags=re.MULTILINE)

    latex = _convert_lists(latex)

    latex = _convert_tables(latex)

    latex = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', latex)

    latex = re.sub(r'!\[([^\]]*)\]\(([^\)]+)\)', r'\\begin{figure}[htbp]\n\\centering\n\\includegraphics[width=0.8\\textwidth]{\2}\n\\caption{\1}\n\\end{figure}', latex)

    return latex


def _convert_lists(latex: str) -> str:
    """Convert markdown lists to LaTeX list environments."""
    lines = latex.split('\n')
    result = []
    in_itemize = False
    in_enumerate = False
    indent_stack = [0]

    for i, line in enumerate(lines):
        item_match = re.match(r'^(\t*)(\\item .+)$', line)
        if item_match:
            indent = len(item_match.group(1))
            content = item_match.group(2)

            is_ordered = re.match(r'\\item \d+', content)

            if in_itemize and (is_ordered or indent < indent_stack[-1]):
                result.append('\\end{itemize}')
                in_itemize = False
            if in_enumerate and (not is_ordered or indent < indent_stack[-1]):
                result.append('\\end{enumerate}')
                in_enumerate = False

            if not in_itemize and not is_ordered:
                result.append('\\begin{itemize}')
                in_itemize = True
                in_enumerate = False
            if not in_enumerate and is_ordered:
                result.append('\\begin{enumerate}')
                in_enumerate = True
                in_itemize = False

            indent_stack[-1] = indent
            result.append(content)
        else:
            if in_itemize:
                result.append('\\end{itemize}')
                in_itemize = False
            if in_enumerate:
                result.append('\\end{enumerate}')
                in_enumerate = False
            result.append(line)

    if in_itemize:
        result.append('\\end{itemize}')
    if in_enumerate:
        result.append('\\end{enumerate}')

    return '\n'.join(result)


def _convert_tables(latex: str) -> str:
    """Convert markdown tables to LaTeX format."""
    table_pattern = re.compile(
        r'(\|.+\|\n)+',
        re.MULTILINE
    )

    def parse_alignments(separator_line: str) -> list[str]:
        """Parse column alignments from markdown separator."""
        cells = separator_line.strip('|').split('|')
        alignments = []
        for cell in cells:
            cell = cell.strip()
            if cell.startswith(':') and cell.endswith(':'):
                alignments.append('c')
            elif cell.startswith(':'):
                alignments.append('l')
            elif cell.endswith(':'):
                alignments.append('r')
            else:
                alignments.append('l')
        return alignments

    def replace_table(match):
        lines = match.group(0).strip().split('\n')
        
        separator_idx = None
        for i, line in enumerate(lines):
            stripped = line.strip('|').replace('-', '').replace(':', '').replace(' ', '')
            if not stripped:
                separator_idx = i
                break
        
        if separator_idx is None:
            return match.group(0)
        
        header_lines = lines[:separator_idx]
        body_lines = lines[separator_idx + 1:]
        
        if not header_lines or not body_lines:
            return match.group(0)
        
        alignments = parse_alignments(lines[separator_idx])
        
        rows = []
        for line in header_lines + body_lines:
            if re.match(r'[\|: -]+$', line):
                continue
            cells = [c.strip() for c in line.strip('|').split('|')]
            rows.append(cells)
        
        if len(rows) < 2:
            return match.group(0)
        
        num_cols = len(rows[0])
        col_spec = '|' + ''.join(alignments[:num_cols]) + '|'
        
        result = [f'\\begin{{table}}[htbp]']
        result.append('\\centering')
        result.append('\\caption{Table Title}')
        result.append(f'\\begin{{tabular}}{{{col_spec}}}')
        result.append('\\toprule')
        
        result.append(' & '.join(rows[0]) + ' \\\\')
        result.append('\\midrule')
        
        for row in rows[1:]:
            result.append(' & '.join(row) + ' \\\\')
        
        result.append('\\bottomrule')
        result.append('\\end{tabular}')
        result.append('\\end{table}')
        
        return '\n'.join(result)

    return table_pattern.sub(replace_table, latex)


def wrap_in_document(latex_content: str, title: str = "Document") -> str:
    """Wrap LaTeX content in a full document structure."""
    return f"""\\documentclass[12pt]{{article}}

 \\usepackage[utf8]{{inputenc}}
 \\usepackage{{graphicx}}
 \\usepackage{{hyperref}}
 \\usepackage{{booktabs}}
 \\usepackage{{verbatim}}

 \\hypersetup{{
     colorlinks=true,
     linkcolor=blue,
     filecolor=magenta,
     urlcolor=cyan,
 }}

 \\title{{{title}}}
 \\author{{Systematic Literature Review}}
 \\date{{\\today}}

 \\begin{{document}}

 \\maketitle

 {latex_content}

 \\end{{document}}
 """
