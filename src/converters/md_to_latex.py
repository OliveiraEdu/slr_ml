"""Markdown to LaTeX converter for PRISMA reports."""
import re
from typing import Optional


def convert_markdown_to_latex(markdown_content: str) -> str:
    """Convert markdown content to LaTeX format."""
    latex = markdown_content

    latex = re.sub(r'^###### (.+)$', r'\\\subsubsection{\1}', latex, flags=re.MULTILINE)
    latex = re.sub(r'^##### (.+)$', r'\\\subsection{\1}', latex, flags=re.MULTILINE)
    latex = re.sub(r'^#### (.+)$', r'\\\section{\1}', latex, flags=re.MULTILINE)
    latex = re.sub(r'^### (.+)$', r'\\\section{\1}', latex, flags=re.MULTILINE)
    latex = re.sub(r'^## (.+)$', r'\\\chapter{\1}', latex, flags=re.MULTILINE)
    latex = re.sub(r'^# (.+)$', r'\\\part{\1}', latex, flags=re.MULTILINE)

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

    latex = re.sub(r'```mermaid\n(.*?)```', r'% Mermaid diagram removed:\n% \1', latex, flags=re.DOTALL)

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

    def replace_table(match):
        lines = match.group(0).strip().split('\n')
        
        if all(re.match(r'[\|-]+$', line) for line in lines):
            return match.group(0)
        
        if not all('|' in line for line in lines):
            return match.group(0)
        
        rows = []
        for line in lines:
            if re.match(r'[\|-]+$', line):
                continue
            cells = [c.strip() for c in line.strip('|').split('|')]
            rows.append(cells)
        
        if len(rows) < 2:
            return match.group(0)
        
        num_cols = len(rows[0])
        col_spec = '|' + 'l|' * num_cols
        
        result = [f'\\begin{{table}}[htbp]']
        result.append('\\centering')
        result.append(f'\\begin{{tabular}}{{{col_spec}}}')
        result.append('\\hline')
        
        result.append(' & '.join(rows[0]) + ' \\\\')
        result.append('\\hline')
        
        for row in rows[1:]:
            result.append(' & '.join(row) + ' \\\\')
            result.append('\\hline')
        
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
