# PRISMA 2020 Systematic Literature Review Engine

A configuration-driven systematic literature review engine that automates paper retrieval, screening, and classification following PRISMA 2020 guidelines using SciBERT for zero-shot classification.

## Features

- **Multi-source import**: BibTeX and CSV files from WoS, IEEE Xplore, ACM, and Scopus
- **arXiv integration**: Real-time API queries for preprints
- **ML-powered screening**: SciBERT zero-shot classification using PICOC criteria
- **PRISMA 2020 compliance**: Automated flow diagram generation and full report generation
- **Automatic extraction**: Study characteristics (blockchain platform, research focus, storage)
- **Quality assessment**: MMAT-based quality scoring for included studies
- **DOI enrichment**: CrossRef and DataCite API integration for citation counts and metadata
- **Configuration-driven**: All settings via YAML files - no hardcoded values
- **REST API**: FastAPI with OpenAPI/Swagger documentation

## Supported Sources

| Source | Input Method | Formats |
|--------|-------------|---------|
| Web of Science | User-provided file | BibTeX, CSV |
| IEEE Xplore | User-provided file | BibTeX, CSV |
| ACM Digital Library | User-provided file | BibTeX, CSV |
| Scopus | User-provided file | BibTeX, CSV |
| arXiv | API query | Real-time |

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Sources

Edit `config/sources.yaml` to specify input files and arXiv queries.

### 3. Configure Classification

Edit `config/classification.yaml` to set PICOC criteria and thresholds.

### 4. Run the API

```bash
uvicorn src.api.main:app --reload
```

### 5. Access API Documentation

Open `http://localhost:8000/docs` for Swagger UI.

## Configuration

All configuration is managed through YAML files in the `config/` directory:

| File | Purpose |
|------|---------|
| `sources.yaml` | Data sources, file paths, and arXiv queries |
| `classification.yaml` | PICOC labels, prompts, and classification thresholds |
| `prisma.yaml` | PRISMA reporting settings |
| `extraction.yaml` | Extraction keywords and MMAT quality criteria |
| `convert.yaml` | Markdown to LaTeX converter settings |

## Pipeline

```
┌─────────────┐    ┌──────────────┐    ┌──────────────────┐
│   YAML      │───▶│   Loader     │───▶│  Deduplication   │
│   Configs   │    │  (BibTeX/CSV)│    │  (DOI + Title)  │
└─────────────┘    └──────────────┘    └────────┬─────────┘
                                               │
┌─────────────┐    ┌──────────────┐            ▼
│   arXiv     │───▶│   API Client  │───▶  ┌─────────────┐
│   Query     │    │               │      │  Unified    │
└─────────────┘    └──────────────┘      │  Paper DB   │
                                          └──────┬────────┘
                                                 │
                            ┌─────────────────────┴─────────────────────┐
                            │         SCREENING STAGE (PRISMA)           │
                            │  Title/Abstract → Full-text → INCLUDED    │
                            └────────────────────────────────────────────┘
                                              │
                                              ▼
                            ┌─────────────────────────────────────────────┐
                            │         EXTRACTION & QUALITY               │
                            │  Study Characteristics → MMAT Assessment   │
                            └────────────────────────────────────────────┘
                                              │
                                              ▼
                             ┌─────────────────────────────────────────────┐
                             │         REPORT GENERATION                   │
                             │  PRISMA Flow → Markdown Report             │
                             └────────────────────────────────────────────┘
                                               │
                                               ▼
                             ┌─────────────────────────────────────────────┐
                             │         MARKDOWN TO LATEX                   │
                             │  Convert reports to LaTeX for publication  │
                             └─────────────────────────────────────────────┘
```

## API Endpoints

### Core Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check (API + ml-worker) |
| `/` | GET | API info |

### Configuration

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/config/load` | POST | Load YAML configs |
| `/config/status` | GET | Get config status |
| `/config/classification` | GET | Get classification config |
| `/config/classification` | PUT | Update classification config |

### Papers

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/papers/import` | POST | Import from file |
| `/papers/import-directory` | POST | Import all files from directory |
| `/papers/arxiv` | POST | Query arXiv API |
| `/papers/list` | GET | List loaded papers |
| `/papers/dedupe` | POST | Run deduplication |
| `/papers/clear` | POST | Clear all papers |
| `/papers/enrich` | POST | Enrich papers with DOI metadata (CrossRef/DataCite) |
| `/papers/enrich/{paper_id}` | GET | Enrich single paper by ID |

### Screening

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/screening/run` | POST | Run ML screening |
| `/screening/results` | GET | Get screening results |
| `/screening/rank` | GET | Rank papers by relevance |

### PRISMA & Reporting

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/prisma/flow` | GET | Get PRISMA flow data |
| `/prisma/export` | GET | Export flow diagram (JSON/CSV) |
| `/prisma/extract` | POST | Extract study data & quality |
| `/prisma/report` | GET | Generate full PRISMA report (Markdown/JSON) |
| `/prisma/extraction` | GET | Get extraction data |
| `/prisma/quality` | GET | Get quality assessment data |

### Markdown to LaTeX Converter

Convert PRISMA reports from Markdown to LaTeX for publication:

```bash
# Using config file (outputs to config/convert.yaml output.file)
python scripts/md_to_latex.py outputs/prisma/report_latest.md

# Override output file
python scripts/md_to_latex.py outputs/prisma/report_latest.md -o outputs/prisma/report.tex

# Ignore config, use CLI only
python scripts/md_to_latex.py inputs/report.md -o outputs/custom.tex --no-config
```

**Configuration** (`config/convert.yaml`):

```yaml
output:
  file: "outputs/prisma/report.tex"  # Target LaTeX file

title: "Systematic Review Findings Report"

options:
  wrap_document: true   # Include LaTeX document structure
  tables: true          # Convert tables
  figures: true        # Convert images
  mermaid: false       # Skip mermaid diagrams
```

**Supported conversions:**
- Headers (all levels)
- Bold and italic text
- Ordered and unordered lists
- Tables (to `table` + `tabular` environment)
- Code blocks (to `verbatim`)
- Images (to `figure`)
- Links (as plain text)

---

## DOI Enrichment

Enrich papers with metadata from CrossRef and DataCite APIs:

```bash
# Enrich all papers with DOIs
curl -X POST http://localhost:8000/papers/enrich

# Include email for higher rate limits (50/sec)
curl -X POST "http://localhost:8000/papers/enrich?email=your@email.com"

# Re-enrich papers even with existing citations
curl -X POST "http://localhost:8000/papers/enrich?skip_existing=false"
```

**Rate Limits (free tier)**:
- CrossRef: 10 requests/second (50 with email)
- DataCite: 10 requests/second

**Enriched data**:
- Citation counts (`is-referenced-by-count`)
- Reference list (`referenced_works`)
- Publication date
- Publisher
- Authors (with ORCID)
- Journal/container title

## Usage Example

### Full Pipeline via API

```bash
# 1. Load configuration
curl -X POST http://localhost:8000/config/load -H "Content-Type: application/json" -d '{"config_dir": "config"}'

# 2. Import papers
curl -X POST http://localhost:8000/papers/import-directory -H "Content-Type: application/json" -d '{"directory": "inputs"}'

# 3. Run deduplication
curl -X POST http://localhost:8000/papers/dedupe -H "Content-Type: application/json" -d '{}'

# 4. Run screening
curl -X POST http://localhost:8000/screening/run -H "Content-Type: application/json" -d '{}'

# 5. Extract data and quality assessment
curl -X POST http://localhost:8000/prisma/extract

# 6. Generate full report
curl http://localhost:8000/prisma/report?format=markdown
```

### Using the Pipeline Script

```bash
./run_pipeline.sh
```

## Report Sections

The generated PRISMA 2020 report includes:

1. **Executive Summary** - Overview of the review
2. **PRISMA Flow Diagram** - Visual flowchart with statistics
3. **Methods** - Search strategy and eligibility criteria
4. **Study Characteristics** - Year distribution, sources, research focus, platforms
5. **Quality Assessment** - MMAT ratings and scores
6. **Included Studies** - Table with study details
7. **Limitations** - Review limitations

## License

MIT License - see LICENSE file.
