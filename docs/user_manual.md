# PRISMA 2020 SLR Engine - User Manual

This manual provides detailed instructions for using the PRISMA 2020 Systematic Literature Review Engine.

## Table of Contents

1. [Installation](#installation)
2. [Configuration](#configuration)
3. [Running the API](#running-the-api)
4. [Pipeline Workflow](#pipeline-workflow)
5. [Solo PhD Workflow](#solo-phd-workflow)
6. [CSV Manual Review Workflow](#csv-manual-review-workflow)
7. [Advanced Features](#advanced-features)
8. [API Endpoints Reference](#api-endpoints-reference)
9. [Report Generation](#report-generation)
10. [Markdown to LaTeX Conversion](#markdown-to-latex-conversion)
11. [Troubleshooting](#troubleshooting)

---

## Installation

### Prerequisites

- Python 3.10+
- pip package manager
- Docker & Docker Compose (for containerized deployment)

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
  # Web of Science
  wos:
    enabled: true
    file_path: "inputs/wos.bib"
    format: "bibtex"

  # IEEE Xplore
  ieee:
    enabled: true
    file_path: "inputs/ieee.csv"
    format: "csv"

  # ACM Digital Library
  acm:
    enabled: true
    file_path: "inputs/acm.bib"
    format: "bibtex"

  # Scopus
  scopus:
    enabled: true
    file_path: "inputs/scopus.csv"
    format: "csv"

  # PubMed
  pubmed:
    enabled: true
    file_path: "inputs/pubmed.bib"
    format: "bibtex"

  # arXiv (live API queries)
  arxiv:
    enabled: true
    max_results: 100
    queries:
      - query: "blockchain provenance scientific data"
        max_results: 50
      - query: "maDMP data management plan"
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

**For Solo PhD**: Use a lower threshold (e.g., 0.35) to capture more papers, then manually filter.

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

### Docker Deployment (Recommended)

```bash
# Build and start
make build && make up

# Check health
make health

# View logs
make logs
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

Import from all configured sources (recommended):
```bash
curl -X POST http://localhost:8000/papers/import-directory \
  -H "Content-Type: application/json" \
  -d '{"directory": "inputs"}'
```

Or import specific files by source:

```bash
# Web of Science (BibTeX)
curl -X POST http://localhost:8000/papers/import \
  -H "Content-Type: application/json" \
  -d '{"source": "wos", "file_path": "inputs/wos.bib", "format": "bibtex"}'

# IEEE Xplore (CSV)
curl -X POST http://localhost:8000/papers/import \
  -H "Content-Type: application/json" \
  -d '{"source": "ieee", "file_path": "inputs/ieee.csv", "format": "csv"}'

# ACM Digital Library (BibTeX)
curl -X POST http://localhost:8000/papers/import \
  -H "Content-Type: application/json" \
  -d '{"source": "acm", "file_path": "inputs/acm.bib", "format": "bibtex"}'

# Scopus (CSV)
curl -X POST http://localhost:8000/papers/import \
  -H "Content-Type: application/json" \
  -d '{"source": "scopus", "file_path": "inputs/scopus.csv", "format": "csv"}'

# PubMed (BibTeX)
curl -X POST http://localhost:8000/papers/import \
  -H "Content-Type: application/json" \
  -d '{"source": "pubmed", "file_path": "inputs/pubmed.bib", "format": "bibtex"}'

# arXiv (Live API query)
curl -X POST http://localhost:8000/papers/arxiv \
  -H "Content-Type: application/json" \
  -d '{"query": "blockchain provenance scientific data", "max_results": 50}'

# From URLs (remote download)
curl -X POST http://localhost:8000/papers/download-all \
  -H "Content-Type: application/json" \
  -d '{"source": "wos", "url": "https://example.com/export.ris"}'
```

#### Step 3: Deduplicate

```bash
curl -X POST http://localhost:8000/papers/dedupe
```

#### Step 4: Run Screening

```bash
curl -X POST http://localhost:8000/screening/run \
  -H "Content-Type: application/json" \
  -d '{"threshold": 0.5}'
```

#### Step 5: Extract Data & Quality Assessment

```bash
curl -X POST http://localhost:8000/prisma/extract
```

#### Step 6: Generate Report

```bash
# Markdown report
curl -X POST http://localhost:8000/prisma/report/full

# JSON report
curl http://localhost:8000/prisma/report?format=json
```

---

## Solo PhD Workflow

This workflow is optimized for single-researcher execution while maintaining publication quality.

### Recommended Process

```
┌─────────────────────────────────────────────────────────────────┐
│                    SOLO PhD WORKFLOW                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  PHASE 1: AUTOMATED (No Human Required)                          │
│  ─────────────────────────────────────────────                   │
│  ✓ Import papers from BibTeX/CSV files                           │
│  ✓ Automatic deduplication                                       │
│  ✓ ML screening with lower threshold (0.35)                     │
│  ✓ DOI metadata enrichment                                       │
│  ✓ Automatic data extraction                                    │
│  ✓ Quality assessment (MMAT)                                     │
│  ✓ PRISMA flow diagram generation                                │
│                                                                  │
│  PHASE 2: HUMAN REVIEW (Your Effort)                             │
│  ─────────────────────────────────                               │
│  ✓ Review uncertain papers (~10-30% of total)                   │
│  ✓ Validate top-ranked ML-included papers                        │
│  ✓ Complete PRISMA 2020 checklist (26 items)                    │
│                                                                  │
│  PHASE 3: FINALIZATION                                           │
│  ────────────────────                                            │
│  ✓ Generate full PRISMA report                                   │
│  ✓ Export extraction data for thesis                            │
│  ✓ Conduct sensitivity analysis                                 │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Step-by-Step Commands

```bash
# 1. Clear previous data
curl -X POST http://localhost:8000/papers/clear

# 2. Import from ALL configured sources
# Web of Science
curl -X POST http://localhost:8000/papers/import \
  -d '{"source": "wos", "file_path": "inputs/wos.bib", "format": "bibtex"}'

# IEEE Xplore
curl -X POST http://localhost:8000/papers/import \
  -d '{"source": "ieee", "file_path": "inputs/ieee.csv", "format": "csv"}'

# ACM Digital Library
curl -X POST http://localhost:8000/papers/import \
  -d '{"source": "acm", "file_path": "inputs/acm.bib", "format": "bibtex"}'

# Scopus
curl -X POST http://localhost:8000/papers/import \
  -d '{"source": "scopus", "file_path": "inputs/scopus.csv", "format": "csv"}'

# arXiv (live queries)
curl -X POST http://localhost:8000/papers/arxiv \
  -d '{"query": "blockchain provenance scientific data management", "max_results": 100}'

# 3. Deduplicate
curl -X POST http://localhost:8000/papers/dedupe

# 4. Screen with LOWER threshold (captures more, you filter manually)
curl -X POST http://localhost:8000/screening/run \
  -H "Content-Type: application/json" \
  -d '{"threshold": 0.35}'

# 5. Check statistics
curl http://localhost:8000/screening/statistics

# 6. Extract data and assess quality
curl -X POST http://localhost:8000/prisma/extract

# 7. Get PRISMA synthesis
curl http://localhost:8000/prisma/synthesis

# 8. Generate PRISMA report
curl -X POST http://localhost:8000/prisma/report/full

# 9. Export uncertain papers for manual review (see next section)
```

### Time Estimate

| Task | Papers | Time |
|------|--------|------|
| Automated ML screening | 479 | ~5 min |
| Manual review queue | 50-100 | ~3-4 hours |
| PRISMA checklist completion | 26 items | ~2-3 hours |
| Quality verification | Included papers | ~1-2 hours |

**Total: ~6-10 hours of focused work**

---

## CSV Manual Review Workflow

### Export Queue to CSV

```bash
# Download as file attachment (recommended)
curl -O http://localhost:8000/screening/queue/uncertain/csv

# Or specify limit
curl -O "http://localhost:8000/screening/queue/uncertain/csv?limit=100"
```

### CSV Format

```csv
review_order,paper_id,title,authors,year,doi,journal,source,ml_decision,ml_score,confidence_band,screened_by,manual_decision,review_reason
1,abc123456789,"Paper Title Here","Author1; Author2",2023,10.1234/example,"Journal Name",acm,uncertain,0.5432,low,ml,,   ← FILL THESE
2,def987654321,"Another Paper","Smith J; Jones K",2022,10.5678/test,"Conf Name",ieee,uncertain,0.5234,low,ml,,
```

### Review in Excel/Google Sheets

1. Open `manual_review_queue.csv` in Excel or Google Sheets
2. Fill `manual_decision` column: `include` or `exclude`
3. Fill `review_reason` column with brief justification
4. Save as CSV

### Import Reviewed Decisions

```bash
# Via API endpoint
curl -X POST http://localhost:8000/screening/review/import-csv \
  -H "Content-Type: text/plain" \
  --data-binary @reviewed_queue.csv

# Via Python script (alternative)
python3 scripts/export_review_queue.py import reviewed_queue.csv
```

### Batch Review via API (Alternative to CSV)

```bash
curl -X POST http://localhost:8000/screening/review/batch \
  -H "Content-Type: application/json" \
  -d '{
    "reviews": [
      {"paper_id": "abc123456789", "decision": "include", "reason": "Relevant to blockchain provenance"},
      {"paper_id": "def987654321", "decision": "exclude", "reason": "Not relevant"},
      {"paper_id": "ghi456789012", "decision": "include", "reason": "maDMP implementation"}
    ]
  }'
```

---

## Advanced Features

### Dual Screening (For Teams)

For research teams with multiple reviewers:

```bash
# Add screening result from Reviewer 1
curl -X POST http://localhost:8000/advanced/dual-screening/add \
  -H "Content-Type: application/json" \
  -d '{"paper_id": "abc123", "reviewer_id": "reviewer_1", "decision": "include", "confidence": 0.8}'

# Add screening result from Reviewer 2
curl -X POST http://localhost:8000/advanced/dual-screening/add \
  -H "Content-Type: application/json" \
  -d '{"paper_id": "abc123", "reviewer_id": "reviewer_2", "decision": "include", "confidence": 0.9}'

# Calculate Cohen's Kappa
curl -X POST http://localhost:8000/advanced/dual-screening/kappa \
  -H "Content-Type: application/json" \
  -d '{
    "reviewer_1_results": {"paper1": "include", "paper2": "exclude", "paper3": "include"},
    "reviewer_2_results": {"paper1": "include", "paper2": "include", "paper3": "exclude"}
  }'

# Get conflicts
curl http://localhost:8000/advanced/dual-screening/conflicts
```

### Sensitivity Analysis

```bash
# Threshold sensitivity
curl http://localhost:8000/advanced/sensitivity/threshold

# Confidence sensitivity
curl http://localhost:8000/advanced/sensitivity/confidence
```

### Risk of Bias Assessment

```bash
# Single paper
curl http://localhost:8000/advanced/risk-of-bias/abc123?study_type=nrt

# Batch assessment
curl -X POST http://localhost:8000/advanced/risk-of-bias/batch \
  -H "Content-Type: application/json" \
  -d '{"study_type": "nrt"}'
```

### Full-Text Retrieval

```bash
# Retrieve single paper PDF
curl -X POST http://localhost:8000/fulltext/retrieve \
  -H "Content-Type: application/json" \
  -d '{"paper_id": "abc123"}'

# Batch retrieval
curl -X POST http://localhost:8000/fulltext/retrieve/batch \
  -H "Content-Type: application/json" \
  -d '{"paper_ids": ["abc123", "def456"], "force": false}'

# Check progress
curl http://localhost:8000/fulltext/progress
```

### World-Class Readiness Assessment

```bash
curl http://localhost:8000/advanced/readiness
```

Returns assessment of PRISMA 2020 compliance and recommendations.

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
- `decision` - Filter by decision (include|exclude|uncertain)
- `limit` - Number of results (max 1000)
- `offset` - Offset for pagination

```bash
# List all included papers
curl "http://localhost:8000/papers/list?decision=include&limit=500"

# List papers from specific source
curl "http://localhost:8000/papers/list?source=arxiv&limit=100"
```

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

**GET /screening/queue/uncertain**

Get papers requiring manual review.

Query parameters:
- `limit` - Number of papers (1-500)
- `sort_by` - Sort method (relevance|composite|citations)

**GET /screening/queue/uncertain/csv**

Download uncertain papers as CSV file attachment for manual review.

**POST /screening/review/import-csv**

Import manually reviewed CSV decisions.

Request: Raw CSV content with `paper_id,manual_decision` columns.

**GET /screening/rank**

Get papers ranked by composite score.

Query parameters:
- `n` - Number of papers (1-500)
- `decision` - Filter by decision (include/exclude/uncertain)
- `sort_by` - Sort method (composite|relevance|citations|recency)

### PRISMA & Reporting

**GET /prisma/checklist**

Returns the 27-item PRISMA 2020 checklist with completion status.

**PUT /prisma/checklist/item**

Update a checklist item status.

```bash
curl -X PUT http://localhost:8000/prisma/checklist/item \
  -H "Content-Type: application/json" \
  -d '{
    "item_number": 1,
    "status": "reported",
    "page_reference": "1",
    "notes": "Title properly identifies as systematic review"
  }'
```

Status options: `reported`, `not_applicable`, `not_reported`

**POST /prisma/extract**

Run extraction and quality assessment on included studies.

**GET /prisma/report/full**

Generate full PRISMA 2020 report.

```bash
# Markdown report
curl -X POST http://localhost:8000/prisma/report/full

# JSON report
curl http://localhost:8000/prisma/report?format=json
```

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

#### 5. CSV download saves as JSON

- Use `-O` flag with curl: `curl -O http://.../uncertain/csv`
- Or redirect output: `curl http://.../uncertain/csv > file.csv`

### Logs

View API logs:
```bash
uvicorn src.api.main:app --reload
```

---

## Support

For issues and questions, please open an issue on the project repository.
