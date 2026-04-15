# PRISMA 2020 Systematic Literature Review Engine

**Version**: 0.7.0

A configuration-driven systematic literature review engine that automates paper retrieval, screening, and classification following PRISMA 2020 guidelines. Supports both SciBERT zero-shot classification and LLM agentic screening with multi-agent ensemble voting.

## LLM Agentic Screening (v0.7.0+)

New in v0.7.0: Multi-agent LLM ensemble for automated paper screening using local Qwen2.5-1.5B model.

```bash
# Full LLM screening workflow (~55 min)
make llama-start       # Start llama-server
make llm-test          # Test with samples
make llm-screen-tuned  # Run 4-agent screening
make llama-stop       # Stop server

# Or single command
make llm-workflow     # Full workflow
```

### Results
- **Total**: 1,158 papers
- **Auto-INCLUDE**: 605 (52.2%)
- **Auto-EXCLUDE**: 440 (38.0%)
- **Manual review**: 113 (9.8%)
- **Confidence**: 59.9% unanimous decisions

## Features

- **Multi-source import**: BibTeX and CSV files from Web of Science, IEEE Xplore, ACM Digital Library, Scopus, PubMed, and arXiv
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

# LLM Agentic Screening (v0.7.0+)
make llama-start          # Start llama-server with Qwen2.5-1.5B
make llama-stop          # Stop llama-server
make llama-status        # Check server status
make llm-test           # Test with sample papers
make llm-screen         # Run 3-agent screening
make llm-screen-tuned  # Run 4-agent ensemble screening
make llm-workflow       # Full automated LLM workflow
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

### Papers Management
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/papers/import` | POST | Import from file |
| `/papers/arxiv` | POST | Query arXiv API |
| `/papers/dedupe` | POST | Remove duplicates |
| `/papers/filter` | POST | **Filter by year, source, keywords** |
| `/papers/list` | GET | List papers |
| `/papers/enrich` | POST | DOI metadata enrichment |
| `/papers/enrich/{id}` | GET | Enrich single paper |

### PROSPERO & Gray Literature
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/prospero/search` | POST | Search PROSPERO registry |
| `/prospero/check-papers` | POST | Check papers for protocol |
| `/prospero/status/{id}` | GET | Get PROSPERO status |

### MeSH (Biomedical)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/mesh/search/{keyword}` | GET | Search MeSH terms |
| `/mesh/match` | POST | Match papers to MeSH |
| `/mesh/expand` | POST | Expand keywords with MeSH |

### Citation Analysis
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/citations/enrich-semantic` | POST | Semantic Scholar enrichment |
| `/citations/network/{id}` | GET | Citation network |
| `/citations/rank-influence` | POST | Rank by influential citations |
| `/citations/pivotal` | POST | Find pivotal papers |

### GRADE Assessment
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/grade/assess` | POST | GRADE assessment |
| `/grade/batch` | POST | Batch GRADE |
| `/grade/summary` | GET | GRADE summary |
| `/grade/levels` | GET | GRADE level descriptions |

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

## Threshold Selection Guide

The classification threshold controls the sensitivity of the ML screening:

| Threshold | Use Case | Recall | Precision | Manual Review |
|-----------|----------|--------|-----------|---------------|
| **0.15** | Recent papers (2023-2026), high recall | High | Lower | ~309 papers |
| **0.35** | Solo PhD, comprehensive capture | High | Lower | More papers |
| **0.50** | Team review, balanced | Medium | Medium | Moderate |
| **0.60** | Conservative, high confidence | Lower | High | Fewer papers |

### Time Range Considerations

For recent papers (last 3 years), the local ctransformate2 model produces lower scores. Recommended approach:

- **2023-2026 (3 years)**: Use threshold **0.15** for best results (~309 papers to review)
- **Full dataset**: Use threshold **0.35** for comprehensive capture
- **Filter before screening**: Reduce workload by filtering to target time range first

### Confidence Bands

With threshold 0.35, confidence bands are:

- **HIGH**: score ≥ 0.55 or ≤ 0.15 (confident decisions)
- **MEDIUM**: score ≥ 0.45 or ≤ 0.25 (reasonably confident)
- **LOW**: score between 0.25 and 0.45 (manual review recommended)

For recent papers (threshold 0.15), adjust bands accordingly:

- **HIGH**: score ≥ 0.35 or ≤ 0.05
- **MEDIUM**: score ≥ 0.25 or ≤ 0.10
- **LOW**: score between 0.10 and 0.25

### Recommended Workflow

1. **Import & dedupe**: Load papers from all sources, remove duplicates
2. **Filter by date**: Use `/papers/filter` to narrow to target years
3. **Initial screening**: Use threshold 0.15 (recent) or 0.35 (full)
4. **Export uncertain**: Get papers in LOW confidence band for manual review
5. **Refine threshold**: Run sensitivity analysis to find optimal threshold
6. **Final screening**: Use optimized threshold for final decisions

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
