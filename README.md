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
- **Sensitivity analysis**: Threshold sensitivity and publication bias detection
- **Risk of bias assessment**: RoB 2.0 and ROBINS-T support
- **Provenance tracking**: Screening decision audit trail
- **Full-text retrieval**: DOI and arXiv PDF fetching
- **CSV import/export**: Manual review workflow with Excel compatibility
- **Dual screening support**: Cohen's Kappa calculation for inter-rater reliability
- **DOI enrichment**: CrossRef and DataCite API integration
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

### Solo PhD Workflow (Recommended)

```bash
# Run with lower threshold for broader capture
curl -X POST http://localhost:8000/screening/run \
  -H "Content-Type: application/json" \
  -d '{"threshold": 0.35}'

# Export uncertain papers for manual review
curl -O http://localhost:8000/screening/queue/uncertain/csv

# After reviewing in Excel, import decisions
curl -X POST http://localhost:8000/screening/review/import-csv \
  -H "Content-Type: text/plain" \
  --data-binary @reviewed_queue.csv
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

## API Endpoints (~50 total)

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
| `/papers/enrich` | POST | Enrich with DOI metadata |

### Screening
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/screening/run` | POST | Run ML screening |
| `/screening/queue/uncertain` | GET | Manual review queue |
| `/screening/queue/uncertain/csv` | GET | **Download CSV for manual review** |
| `/screening/queue/all/csv` | GET | Export all papers to CSV |
| `/screening/review` | POST | Update single decision |
| `/screening/review/batch` | POST | Batch update decisions |
| `/screening/review/import-csv` | POST | **Import reviewed CSV** |
| `/screening/statistics` | GET | PRISMA statistics |
| `/screening/progression` | GET | Stage progression |
| `/screening/stage2` | POST | Run Stage 2 screening |
| `/screening/rank` | GET | Rank papers by composite score |

### Advanced Screening
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/advanced/dual-screening/add` | POST | Add dual screening result |
| `/advanced/dual-screening/kappa` | POST | Calculate Cohen's Kappa |
| `/advanced/dual-screening/conflicts` | GET | Get reviewer conflicts |
| `/advanced/sensitivity/threshold` | GET | Threshold sensitivity analysis |
| `/advanced/sensitivity/confidence` | GET | Confidence sensitivity analysis |
| `/advanced/risk-of-bias/{id}` | GET | Single paper RoB assessment |
| `/advanced/risk-of-bias/batch` | POST | Batch RoB assessment |
| `/advanced/completeness` | GET | Workflow completeness tracking |
| `/advanced/readiness` | GET | World-class readiness score |

### Full-Text
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/fulltext/retrieve` | POST | Retrieve single paper PDF |
| `/fulltext/retrieve/batch` | POST | Batch PDF retrieval |
| `/fulltext/progress` | GET | Retrieval progress status |
| `/fulltext/{id}/extract-text` | GET | Extract text from PDF |
| `/fulltext/{id}/status` | GET | Paper FT status |

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

### Configuration
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/config/status` | GET | Config status |
| `/config/classification` | GET/PUT | Classification config |

### Converters
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/convert/markdown-to-latex` | POST | MD to LaTeX conversion |

## Configuration

All settings via YAML files in `config/`:

| File | Purpose |
|------|---------|
| `sources.yaml` | Data sources, file paths |
| `data_sources.yaml` | Remote URL downloads |
| `classification.yaml` | Keywords, thresholds, confidence bands |
| `prisma.yaml` | PRISMA settings, exclusion reasons |
| `extraction.yaml` | Extraction keywords, MMAT criteria |

## Solo PhD Workflow

### Recommended Process

```
┌─────────────────────────────────────────────────────────────────┐
│                    SOLO PhD WORKFLOW                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. AUTOMATED (No Human Required)                                 │
│     ✓ Import papers (BibTeX/CSV)                                 │
│     ✓ Deduplication                                              │
│     ✓ ML screening (threshold=0.35)                             │
│     ✓ DOI enrichment                                             │
│     ✓ Data extraction                                            │
│     ✓ Quality assessment                                         │
│                                                                  │
│  2. HUMAN REVIEW (Your Effort)                                   │
│     ✓ Review uncertain papers (export to CSV)                    │
│     ✓ Validate top-ranked included papers                        │
│     ✓ Complete PRISMA checklist (26 items)                       │
│                                                                  │
│  3. DOCUMENTATION                                                │
│     ✓ Generate PRISMA report                                     │
│     ✓ Export extraction data                                     │
│     ✓ Final synthesis                                            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Step-by-Step

```bash
# 1. Clear and import
curl -X POST http://localhost:8000/papers/clear
curl -X POST http://localhost:8000/papers/import -d '{"source": "acm", ...}'
curl -X POST http://localhost:8000/papers/import -d '{"source": "ieee", ...}'

# 2. Deduplicate
curl -X POST http://localhost:8000/papers/dedupe

# 3. Screen with lower threshold (captures more, you filter)
curl -X POST http://localhost:8000/screening/run \
  -H "Content-Type: application/json" \
  -d '{"threshold": 0.35}'

# 4. Get statistics
curl http://localhost:8000/screening/statistics

# 5. Export uncertain queue to CSV
curl -O http://localhost:8000/screening/queue/uncertain/csv

# 6. Review in Excel - fill 'manual_decision' and 'review_reason' columns

# 7. Import reviewed decisions
curl -X POST http://localhost:8000/screening/review/import-csv \
  -H "Content-Type: text/plain" \
  --data-binary @reviewed_queue.csv

# 8. Generate PRISMA report
curl -X POST http://localhost:8000/prisma/report/full
```

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
