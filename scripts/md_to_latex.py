"""Markdown to LaTeX converter for PRISMA reports."""
import argparse
import os
import re
from pathlib import Path
from typing import Optional

import yaml


def load_config(config_path: str) -> dict:
    """Load configuration from YAML file."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def convert_markdown_to_latex(markdown_content: str) -> str:
    """Convert markdown content to LaTeX format."""
    latex = markdown_content

    # Headers
    latex = re.sub(r'^###### (.+)$', r'\\\subsubsection{\1}', latex, flags=re.MULTILINE)
    latex = re.sub(r'^##### (.+)$', r'\\\subsection{\1}', latex, flags=re.MULTILINE)
    latex = re.sub(r'^#### (.+)$', r'\\\section{\1}', latex, flags=re.MULTILINE)
    latex = re.sub(r'^### (.+)$', r'\\\section{\1}', latex, flags=re.MULTILINE)
    latex = re.sub(r'^## (.+)$', r'\\\chapter{\1}', latex, flags=re.MULTILINE)
    latex = re.sub(r'^# (.+)$', r'\\\part{\1}', latex, flags=re.MULTILINE)

    # Bold and Italic
    latex = re.sub(r'\*\*(.+?)\*\*', r'\\textbf{\1}', latex)
    latex = re.sub(r'\*(.+?)\*', r'\\textit{\1}', latex)
    latex = re.sub(r'__(.+?)__', r'\\textbf{\1}', latex)
    latex = re.sub(r'_(.+?)_', r'\\textit{\1}', latex)

    # Code blocks
    latex = re.sub(r'```(\w+)?\n(.*?)```', r'\\begin{verbatim}\2\\end{verbatim}', latex, flags=re.DOTALL)

    # Inline code
    latex = re.sub(r'`(.+?)`', r'\\texttt{\1}', latex)

    # Horizontal rules
    latex = re.sub(r'^---+$', r'\\hline', latex)
    latex = re.sub(r'^\*\*\*+$', r'\\hline', latex)

    # Lists - unordered
    latex = re.sub(r'^\s*[-*+] (.+)$', r'\\item \1', latex, flags=re.MULTILINE)

    # Lists - ordered
    latex = re.sub(r'^\s*(\d+)\. (.+)$', r'\\item \2', latex, flags=re.MULTILINE)

    # Wrap lists in environments
    latex = _convert_lists(latex)

    # Tables
    latex = _convert_tables(latex)

    # Links (keep as text)
    latex = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', latex)

    # Images
    latex = re.sub(r'!\[([^\]]*)\]\(([^\)]+)\)', r'\\begin{figure}[htbp]\n\\centering\n\\includegraphics[width=0.8\\textwidth]{\2}\n\\caption{\1}\n\\end{figure}', latex)

    # Mermaid diagrams (comment out)
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

            # Check if ordered list
            is_ordered = re.match(r'\\item \d+', content)

            # Close previous list if needed
            if in_itemize and (is_ordered or indent < indent_stack[-1]):
                result.append('\\end{itemize}')
                in_itemize = False
            if in_enumerate and (not is_ordered or indent < indent_stack[-1]):
                result.append('\\end{enumerate}')
                in_enumerate = False

            # Start new list if needed
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

    # Close any open lists
    if in_itemize:
        result.append('\\end{itemize}')
    if in_enumerate:
        result.append('\\end{enumerate}')

    return '\n'.join(result)


def _convert_tables(latex: str) -> str:
    """Convert markdown tables to LaTeX format."""
    table_pattern = re.compile(
        r'(\|.+\|\n)+',  # Table rows
        re.MULTILINE
    )

    def replace_table(match):
        lines = match.group(0).strip().split('\n')
        
        # Skip if separator line
        if all(re.match(r'[\|-]+$', line) for line in lines):
            return match.group(0)
        
        # Check if it's a proper table (has separators)
        if not all('|' in line for line in lines):
            return match.group(0)
        
        # Parse header and rows
        rows = []
        for line in lines:
            if re.match(r'[\|-]+$', line):
                continue
            cells = [c.strip() for c in line.strip('|').split('|')]
            rows.append(cells)
        
        if len(rows) < 2:
            return match.group(0)
        
        # Build LaTeX table
        num_cols = len(rows[0])
        col_spec = '|' + 'l|' * num_cols
        
        result = [f'\\begin{{table}}[htbp]']
        result.append('\\centering')
        result.append(f'\\begin{{tabular}}{{{col_spec}}}')
        result.append('\\hline')
        
        # Header
        result.append(' & '.join(rows[0]) + ' \\\\')
        result.append('\\hline')
        
        # Body rows
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


def convert_file(
    input_path: str,
    output_path: Optional[str] = None,
    config_path: Optional[str] = None
) -> str:
    """Convert a markdown file to LaTeX."""
    # Load config if provided
    config = {}
    if config_path and os.path.exists(config_path):
        config = load_config(config_path)

    # Read input
    with open(input_path, 'r', encoding='utf-8') as f:
        markdown_content = f.read()

    # Extract title from first heading if not in config
    title = config.get('title')
    if not title:
        title_match = re.search(r'^# (.+)$', markdown_content, re.MULTILINE)
        if title_match:
            title = title_match.group(1)

    # Convert
    latex_content = convert_markdown_to_latex(markdown_content)

    # Wrap in document
    full_document = wrap_in_document(latex_content, title or "Document")

    # Determine output path
    if output_path:
        target_path = output_path
    elif config.get('output', {}).get('file'):
        target_path = config['output']['file']
    else:
        input_name = Path(input_path).stem
        target_path = f"outputs/{input_name}.tex"

    # Ensure output directory exists
    os.makedirs(os.path.dirname(target_path) or '.', exist_ok=True)

    # Write output
    with open(target_path, 'w', encoding='utf-8') as f:
        f.write(full_document)

    return target_path


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Convert Markdown files to LaTeX'
    )
    parser.add_argument(
        'input',
        nargs='?',
        default='outputs/prisma/report_latest.md',
        help='Input markdown file (default: outputs/prisma/report_latest.md)'
    )
    parser.add_argument(
        '-o', '--output',
        help='Output LaTeX file'
    )
    parser.add_argument(
        '-c', '--config',
        default='config/convert.yaml',
        help='Configuration file (default: config/convert.yaml)'
    )
    parser.add_argument(
        '--no-config',
        action='store_true',
        help='Ignore config file and use only CLI arguments'
    )

    args = parser.parse_args()

    # Check for config file
    config_path = None if args.no_config else args.config

    output_path = convert_file(
        input_path=args.input,
        output_path=args.output,
        config_path=config_path
    )

    print(f"Converted: {args.input} -> {output_path}")


if __name__ == '__main__':
    main()
