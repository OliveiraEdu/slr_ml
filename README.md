# PRISMA 2020 Systematic Literature Review Engine

**Version**: 0.6.0

A configuration-driven systematic literature review engine that automates paper retrieval, screening, and classification following PRISMA 2020 guidelines using SciBERT for zero-shot classification.

## Features

- **Multi-source import**: BibTeX and CSV files from WoS, IEEE Xplore, ACM, Scopus, and PubMed
- **URL Download**: Download paper exports directly from remote URLs
- **arXiv integration**: Real-time API queries for preprints
- **ML-powered screening**: SciBERT zero-shot classification with confidence bands
- **Enhanced screening (Option B)**:
  - Keyword pre-filtering (required/relevant/exclusion keywords)
  - Active learning for iterative manual review
  - Citation-based ranking
  - SciBERT fine-tuning capability
  - Backward/forward snowballing
  - Certainty-based automated decisions
- **Two-stage screening**: Title/abstract → Full-text workflow
- **PRISMA 2020 compliance**: Automated flow diagram, 27-item checklist, full reports
- **Data extraction**: 35+ maDMP/blockchain fields for included studies
- **Quality assessment**: MMAT-based quality scoring
- **Synthesis**: Platform analysis, research gaps, trend identification
- **DOI enrichment**: CrossRef and DataCite API integration
- **CSV export**: Export extraction and quality data for thesis appendix
- **Configuration-driven**: All settings via YAML files - no hardcoded values
- **REST API**: FastAPI with OpenAPI/Swagger documentation

## Quick Start

```bash
# 1. Build and start
make build && make up

# 2. Wait for startup
sleep 5 && make health

# 3. Import and screen papers
make import-sample
make screen

# 4. View results
make stats
make prisma-report
```

## Docker Deployment

```bash
# Build containers
make build

# Start services
make up

# Check health
make health

# View logs
make logs
```

## Makefile Commands

### Testing
```bash
make test               # Unit tests only
make test-integration   # Integration tests (requires running API)
make test-all          # All tests
make coverage           # Tests with coverage report
make verify-api        # Verify API is accessible
make smoke-test        # Comprehensive API smoke test (7 endpoints)
```

### Workflow
```bash
make import-sample      # Import from inputs/
make screen            # Run ML screening
make queue             # Get uncertain papers
make stats             # Screening statistics
make rank              # Top papers by relevance

# Two-stage screening
make ft-retrievable    # Papers needing FT
make stage2-queue     # Stage 2 eligible
make stage2-screen    # Run Stage 2

# Enhanced screening (Option B)
make keyword-filter    # Keyword pre-filtering
make al-select        # Active learning selection
make snowballing      # Snowballing search
make certainty        # Certainty-based auto decisions
make cite-rank        # Citation ranking
make enhanced-full    # Full enhanced pipeline
make enhanced-workflow  # Complete workflow

# PRISMA
make checklist         # PRISMA 2020 checklist
make prisma-flow       # Flow diagram
make prisma-report     # Full report
```

### Data Sources
```bash
make sources            # List configured sources
make download-all       # Download all sources
```

## API Endpoints (~40 total)

### Papers
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/papers/list` | GET | List papers |
| `/papers/import` | POST | Import from file |
| `/papers/import-directory` | POST | Import from directory |
| `/papers/arxiv` | POST | Query arXiv |
| `/papers/sources` | GET | List configured sources |
| `/papers/download-all` | POST | Download from URLs |
| `/papers/flagged` | GET | Papers without DOI |
| `/papers/retrievable` | GET | Papers with DOI |
| `/papers/{id}/fulltext` | GET/POST | Full-text management |

### Screening
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/screening/run` | POST | Run ML screening |
| `/screening/queue/uncertain` | GET | Manual review queue |
| `/screening/review` | POST | Update single decision |
| `/screening/review/batch` | POST | Batch update |
| `/screening/statistics` | GET | PRISMA statistics |
| `/screening/progression` | GET | Stage progression |
| `/screening/stage2` | POST | Run Stage 2 screening |

### PRISMA
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/prisma/flow` | GET | Flow diagram data |
| `/prisma/checklist` | GET | 27-item checklist |
| `/prisma/checklist/item` | PUT | Update checklist item |
| `/prisma/report/full` | POST | Full PRISMA report |
| `/prisma/extraction/template` | GET | Extraction form |
| `/prisma/extraction/{id}` | GET/PUT | Extraction data |
| `/prisma/extraction/export` | GET | Export as CSV |
| `/prisma/synthesis` | GET | Synthesis statistics |
| `/prisma/synthesis/platforms` | GET | Platform analysis |
| `/prisma/synthesis/gaps` | GET | Research gaps |
| `/prisma/quality/assess` | POST | Run quality assessment |
| `/prisma/quality/export` | GET | Export quality as CSV |

### Enhanced Screening (Option B)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/enhanced/filter/keywords` | POST | Keyword pre-filtering |
| `/enhanced/active-learning` | POST | Sample selection for review |
| `/enhanced/fine-tune` | POST | Fine-tune SciBERT |
| `/enhanced/snowballing` | POST | Reference chasing |
| `/enhanced/certainty-screening` | POST | Auto decisions |
| `/enhanced/rank/citations` | POST | Citation ranking |
| `/enhanced/screening/full` | POST | Full enhanced pipeline |

### Configuration
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/config/status` | GET | Config status |
| `/config/classification` | GET/PUT | Classification config |

## Configuration

All settings via YAML files in `config/`:

| File | Purpose |
|------|---------|
| `sources.yaml` | Data sources, file paths |
| `data_sources.yaml` | Remote URL downloads |
| `classification.yaml` | Keywords, thresholds, confidence bands |
| `prisma.yaml` | PRISMA settings, exclusion reasons |
| `extraction.yaml` | Extraction keywords, MMAT criteria |

## Architecture

```
INPUT → DEDUP → ML SCREENING → CONFIDENCE → MANUAL → INCLUDED
          ↓           ↓           BANDS       REVIEW
       Papers    High/Med/Low    Filter
```

```
Stage 1 (Title/Abstract) → Stage 2 (Full-Text) → Extraction → Synthesis
```

## API Documentation

- **Local**: http://localhost:8000/docs
- **Swagger UI**: http://localhost:8000/docs

## Testing

Tests run from host machine against running API:

```bash
# Ensure API is running
make up

# Run tests
pytest -v tests/test_integration.py
```

## License

MIT License
