# PRISMA 2020 SLR Engine - User Manual

This manual provides detailed instructions for using the PRISMA 2020 Systematic Literature Review Engine.

## Table of Contents

1. [Installation](#installation)
2. [Configuration](#configuration)
3. [Running the API](#running-the-api)
4. [Pipeline Workflow](#pipeline-workflow)
5. [API Endpoints Reference](#api-endpoints-reference)
6. [Report Generation](#report-generation)
7. [Markdown to LaTeX Conversion](#markdown-to-latex-conversion)
8. [Troubleshooting](#troubleshooting)

---

## Installation

### Prerequisites

- Python 3.10+
- pip package manager

### Steps

1. **Clone the repository**

```bash
git clone <repository-url>
cd slr_ml
```

2. **Create virtual environment (recommended)**

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

4. **Optional: Install ML dependencies**

```bash
pip install torch transformers ctranslate2
```

---

## Configuration

All settings are managed via YAML files in the `config/` directory.

### 1. Sources Configuration (`config/sources.yaml`)

Configure which databases to use and their input files:

```yaml
sources:
  wos:
    enabled: true
    file_path: "inputs/wos.bib"
    format: "bibtex"

  ieee:
    enabled: true
    file_path: "inputs/ieee.csv"
    format: "csv"

  acm:
    enabled: true
    file_path: "inputs/acm.bib"
    format: "bibtex"

  scopus:
    enabled: true
    file_path: "inputs/scopus.csv"
    format: "csv"

  arxiv:
    enabled: false
    max_results: 100
    queries:
      - query: "blockchain provenance scientific data"
        max_results: 50
```

### 2. Classification Configuration (`config/classification.yaml`)

Set the research question and classification criteria:

```yaml
classification:
  research_question: |
    Your research question here...

  relevance:
    enabled: true
    include_prompt: |
      This paper is relevant because...
    exclude_prompt: |
      This paper should be excluded because...
    threshold: 0.5

  keywords:
    required:
      - blockchain
      - provenance
    optional:
      - data management
```

### 3. PRISMA Configuration (`config/prisma.yaml`)

Configure PRISMA reporting:

```yaml
prisma:
  review_type: "original"
  title_abstract_exclusion_reasons:
    - "Not relevant to research question"
    - "Wrong study design"
  # ... more settings
```

### 4. Extraction Configuration (`config/extraction.yaml`)

Configure automatic extraction and quality assessment:

```yaml
extraction:
  research_focus_keywords:
    provenance:
      - provenance
      - lineage
      - chain of custody
    blockchain:
      - blockchain
      - ethereum

  blockchain_platforms:
    - Ethereum
    - Hyperledger Fabric
    - Hyperledger
    # ...

quality_assessment:
  mmat_criteria:
    clear_research_questions:
      - research question
      - objective
    # ...
```

---

## Running the API

### Start the API server

```bash
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

### Access the API

- API Base URL: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

---

## Pipeline Workflow

### Complete Workflow

#### Step 1: Load Configuration

```bash
curl -X POST http://localhost:8000/config/load \
  -H "Content-Type: application/json" \
  -d '{"config_dir": "config"}'
```

#### Step 2: Import Papers

Import from directory:
```bash
curl -X POST http://localhost:8000/papers/import-directory \
  -H "Content-Type: application/json" \
  -d '{"directory": "inputs"}'
```

Or import specific file:
```bash
curl -X POST http://localhost:8000/papers/import \
  -H "Content-Type: application/json" \
  -d '{"source": "wos", "file_path": "inputs/wos.bib", "format": "bibtex"}'
```

#### Step 3: Deduplicate

```bash
curl -X POST http://localhost:8000/papers/dedupe \
  -H "Content-Type: application/json" \
  -d '{}'
```

#### Step 4: Run Screening

```bash
curl -X POST http://localhost:8000/screening/run \
  -H "Content-Type: application/json" \
  -d '{}'
```

#### Step 5: Extract Data & Quality Assessment

```bash
curl -X POST http://localhost:8000/prisma/extract
```

#### Step 6: Generate Report

```bash
# Markdown report
curl http://localhost:8000/prisma/report?format=markdown

# JSON report
curl http://localhost:8000/prisma/report?format=json
```

### Using the Pipeline Script

```bash
./run_pipeline.sh
```

---

## API Endpoints Reference

### Health Check

**GET /health**

Returns health status of API and ml-worker services.

```json
{
  "status": "healthy",
  "services": {
    "api": {"status": "healthy"},
    "ml_worker": {"status": "healthy"}
  },
  "papers_loaded": 100,
  "config_loaded": true
}
```

### Papers

**POST /papers/import-directory**

Import all supported files from a directory.

Request:
```json
{
  "directory": "inputs",
  "auto_detect": true
}
```

**POST /papers/dedupe**

Remove duplicate papers based on DOI and title.

**GET /papers/list**

List loaded papers with pagination.

Query parameters:
- `source` - Filter by source
- `limit` - Number of results (max 1000)
- `offset` - Offset for pagination

### Screening

**POST /screening/run**

Run ML screening on papers.

Request:
```json
{
  "stage": "title_abstract",
  "threshold": 0.5,
  "include_prompt": "This paper is relevant...",
  "exclude_prompt": "This paper is not relevant..."
}
```

**GET /screening/rank**

Get papers ranked by composite score.

Query parameters:
- `n` - Number of papers (1-500)
- `decision` - Filter by decision (include/exclude/uncertain)
- `sort_by` - Sort method (composite|relevance|citations|recency)

### PRISMA & Reporting

**POST /prisma/extract**

Run extraction and quality assessment on included studies.

**GET /prisma/report**

Generate full PRISMA 2020 report.

Query parameters:
- `format` - Output format (markdown|json)

**GET /prisma/extraction**

Get extraction data for included studies.

**GET /prisma/quality**

Get quality assessment data.

---

## Report Generation

### Report Sections

The generated markdown report includes:

1. **Executive Summary** - Overview of findings
2. **PRISMA Flow Diagram** - Visual flowchart with Mermaid
3. **Methods** - Search strategy and eligibility criteria
4. **Study Characteristics**:
   - Publication year distribution
   - Source distribution
   - Research focus distribution
   - Blockchain platform distribution
5. **Quality Assessment**:
   - Quality ratings distribution
   - MMAT item scores
6. **Included Studies** - Table of included papers
7. **Limitations**

### Export Formats

- **Markdown** - Full human-readable report with Mermaid diagrams
- **JSON** - Machine-readable data for further processing

### Output Location

Reports are saved to `outputs/prisma/` with timestamp:

```
outputs/prisma/report_20260317_090824.md
outputs/prisma/flow_diagram_20260317_090824.json
```

---

## Markdown to LaTeX Conversion

The engine includes a utility to convert generated Markdown reports to LaTeX for publication in academic journals.

### Quick Start

```bash
python scripts/md_to_latex.py outputs/prisma/report_latest.md
```

This reads the configuration from `config/convert.yaml` and outputs to the configured path.

### Configuration

Edit `config/convert.yaml`:

```yaml
output:
  file: "outputs/prisma/report.tex"  # Target LaTeX file path

title: "Systematic Review Findings Report"

options:
  wrap_document: true   # Include full LaTeX document structure
  tables: true          # Convert markdown tables to LaTeX
  figures: true         # Convert images to figure environment
  mermaid: false        # Skip mermaid diagrams (comment them out)
```

### CLI Options

| Option | Description |
|--------|-------------|
| `input` | Input markdown file (required) |
| `-o, --output` | Output LaTeX file (overrides config) |
| `-c, --config` | Config file path (default: config/convert.yaml) |
| `--no-config` | Ignore config file, use CLI args only |

### Examples

```bash
# Using default config
python scripts/md_to_latex.py outputs/prisma/report_latest.md

# Specify output file
python scripts/md_to_latex.py outputs/prisma/report_latest.md -o outputs/prisma/report.tex

# Use custom config
python scripts/md_to_latex.py inputs/custom_report.md -c config/my_convert.yaml

# CLI only (no config file)
python scripts/md_to_latex.py inputs/report.md -o outputs/custom.tex --no-config
```

### Supported Conversions

| Markdown Element | LaTeX Output |
|------------------|--------------|
| `# Heading` | `\chapter{}` / `\section{}` |
| `**bold**` | `\textbf{}` |
| `*italic*` | `\textit{}` |
| `- item` | `\item` (in `itemize`) |
| `1. item` | `\item` (in `enumerate`) |
| Table | `table` + `tabular` environment |
| `` `code` `` | `\texttt{}` |
| ```code block``` | `verbatim` environment |
| `![alt](img.png)` | `figure` environment |
| `[link](url)` | Plain text (link removed) |

### Compiling LaTeX

After conversion, compile the LaTeX file:

```bash
pdflatex outputs/prisma/report.tex
```

Or use your preferred LaTeX editor (Overleaf, TeX Shop, etc.).

---

## Troubleshooting

### Common Issues

#### 1. No papers imported

- Check input files exist in the specified directory
- Verify file format matches (bibtex vs csv)
- Check file paths in `config/sources.yaml`

#### 2. All papers excluded during screening

- Review `config/classification.yaml` prompts
- Lower the threshold (e.g., 0.3 instead of 0.5)
- Check that config is loaded before screening

#### 3. ML worker not responding

- Ensure ml-worker container is running
- Check Docker network configuration

#### 4. Report missing sections

- Run `/prisma/extract` before `/prisma/report`
- Ensure screening has completed with included papers

### Logs

View API logs:
```bash
uvicorn src.api.main:app --reload
```

---

## Support

For issues and questions, please open an issue on the project repository.
