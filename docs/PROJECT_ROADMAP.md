# Project Roadmap: ML-Assisted Systematic Literature Review

**Project**: Blockchain-Provenance SLR for Machine-Actionable Data Management Plans  
**Research Question**: "How can machine-actionable Data Management Plans (maDMPs) be persisted on a blockchain to enable verifiable provenance tracking for scientific data?"  
**Estimated Paper Volume**: ~8,000 records  
**Target Venues**: Computer Science PhD Thesis  
**Version**: 0.5.0

---

## Quick Start

```bash
# 1. Clone and build
git clone <repo>
make build

# 2. Start services
make up

# 3. Wait for startup, then check health
sleep 5 && make health

# 4. Run full workflow
make import-sample    # Import papers
make screen           # Run ML screening
make stats            # View statistics
make prisma-report    # Generate PRISMA report
```

---

## Development Phases

### Phase 1: ML-Assisted Screening (Complete)
**Timeline**: 1-2 weeks  
**Goal**: Make ML useful for high-volume screening with interpretable confidence

#### Features Implemented
- [x] Confidence calibration with bands (high/medium/low)
- [x] Multi-threshold screening
- [x] Domain-specific keyword boosting (3-level: required/relevant/exclusion)
- [x] Manual review queue endpoint (`/screening/queue/uncertain`)
- [x] Screening statistics endpoint (`/screening/statistics`)
- [x] Manual review update endpoint (`/screening/review`)
- [x] Batch review update endpoint (`/screening/review/batch`)
- [x] PRISMA-ready statistics generation

#### Confidence Band Thresholds
- **High**: score ≥ 0.75 or ≤ 0.25
- **Medium**: score ≥ 0.55 or ≤ 0.45  
- **Low**: score between 0.45 and 0.55 (manual review required)

#### Phase 1 Endpoints
| Endpoint | Description |
|----------|-------------|
| `POST /screening/run` | Run ML screening |
| `GET /screening/queue/uncertain` | Papers needing manual review |
| `GET /screening/statistics` | PRISMA-ready statistics |
| `POST /screening/review` | Update single paper decision |
| `POST /screening/review/batch` | Batch update multiple papers |
| `GET /screening/rank` | Rank papers by relevance |

---

### Phase 2: Full PRISMA 2020 Compliance (Complete)
**Timeline**: 3-4 weeks  
**Goal**: Generate defensible PRISMA documentation for thesis

#### Features Implemented
- [x] PRISMA 2020 checklist integration (27 items)
- [x] Protocol documentation with updateable fields
- [x] Checklist item status tracking (reported/not_reported/not_applicable)
- [x] Checklist completeness score calculation
- [x] Full PRISMA report generator with checklist section

#### Phase 2 Endpoints
| Endpoint | Description |
|----------|-------------|
| `GET /prisma/checklist` | Get full 27-item PRISMA 2020 checklist |
| `PUT /prisma/protocol` | Update protocol metadata |
| `PUT /prisma/checklist/item` | Update individual checklist item status |
| `GET /prisma/checklist/report` | Get checklist grouped by section |
| `POST /prisma/report/full` | Generate complete PRISMA report |
| `GET /prisma/flow` | Get PRISMA flow diagram data |

---

### Phase 3: Full-Text Screening Workflow (Complete)
**Timeline**: 5-6 weeks  
**Goal**: Two-stage screening (title/abstract → full text)

#### Features Implemented
- [x] Phase-aware screening (`title_abstract` vs `full_text` stages)
- [x] Paper progression tracking with stage transitions
- [x] DOI retrieval with flagging for papers without DOI
- [x] ArXiv preprints handled separately
- [x] Local storage for full-text content
- [x] Two-stage screening endpoints
- [x] Full-text progress tracking
- [x] Updated PRISMA flow with stage transitions

#### Phase 3 Endpoints
| Endpoint | Description |
|----------|-------------|
| `GET /screening/progression` | Paper flow through stages |
| `GET /screening/queue/stage2` | Papers eligible for Stage 2 |
| `POST /screening/stage2` | Run Stage 2 screening |
| `GET /papers/retrievable` | Papers eligible for FT retrieval |
| `GET /papers/flagged` | Papers flagged for no DOI |
| `GET /papers/progress/fulltext` | FT retrieval progress |
| `POST /papers/{id}/fulltext` | Attach full-text content |

#### Two-Stage Workflow
```
Stage 1 (Title/Abstract)
    ↓
Included papers → FT Retrieval (DOI/ArXiv)
    ↓
Flagged (no DOI) → Excluded from Stage 2
    ↓
Stage 2 (Full-Text)
    ↓
Final Included Studies
```

---

### Phase 4: Data Extraction & Synthesis (Complete)
**Timeline**: 7-8 weeks  
**Goal**: Extract and synthesize findings from included studies

#### Features Implemented
- [x] Enhanced extraction schema with 35+ maDMP/blockchain fields
- [x] Keyword-based extraction from paper text
- [x] Quality assessment using MMAT criteria
- [x] Synthesis statistics generation
- [x] Research gap identification
- [x] Trend analysis
- [x] Full synthesis report generator
- [x] CSV export for extraction and quality data

#### Extraction Fields (35+ fields)
| Category | Fields |
|----------|--------|
| **Blockchain** | platform, type, consensus mechanism, smart contract language |
| **Data Management** | maDMP standard, metadata schema, FAIR compliance |
| **Provenance** | model, approach, verification mechanism |
| **Storage** | integration type, partitioning, encryption |
| **Access Control** | permission model, mechanism |

#### Phase 4 Endpoints
| Endpoint | Description |
|----------|-------------|
| `GET /prisma/extraction/template` | Get maDMP extraction form |
| `GET /prisma/extraction/{paper_id}` | Get extraction data |
| `PUT /prisma/extraction/{paper_id}` | Save extraction data |
| `GET /prisma/extraction/export` | Export as CSV |
| `GET /prisma/synthesis` | Synthesis statistics |
| `GET /prisma/synthesis/platforms` | Platform analysis |
| `GET /prisma/synthesis/distributions` | Distribution stats |
| `GET /prisma/synthesis/gaps` | Research gaps |
| `POST /prisma/synthesis/report` | Generate synthesis report |
| `POST /prisma/quality/assess` | Run quality assessment |
| `GET /prisma/quality/{paper_id}` | Get quality data |
| `PUT /prisma/quality/{paper_id}` | Update quality data |
| `GET /prisma/quality/export` | Export quality as CSV |

---

### Data Source Downloads (Complete)

#### Configuration
File: `config/data_sources.yaml`

Supported sources: WoS, IEEE, ACM, Scopus, PubMed, ArXiv

#### Data Source Endpoints
| Endpoint | Description |
|----------|-------------|
| `GET /papers/sources` | List configured sources |
| `POST /papers/download` | Download from URL |
| `POST /papers/download-all` | Download all enabled sources |
| `POST /papers/import-from-url` | Download and import |

---

### Auto-Config Loading (Complete)

Configuration files are automatically loaded on API startup:
- `config/sources.yaml` - Data source configuration
- `config/classification.yaml` - ML screening settings
- `config/prisma.yaml` - PRISMA report settings

---

## Makefile Commands

### Docker Deployment
```bash
make build              # Build containers
make up                 # Start services
make down               # Stop services
make logs               # View logs
make logs-api           # API logs only
make clean              # Remove containers + volumes
make status             # Check service health
```

### Development
```bash
make run-api            # Run API locally (uvicorn)
make install            # Install dependencies
make lint               # Run black/isort
make typecheck          # Run mypy
```

### Testing (Pending)
```bash
make test               # Unit tests only
make test-integration   # Integration tests (requires running API)
make test-all           # All tests
make coverage           # Tests with coverage report
```

### Workflow Commands
```bash
make health             # Check API health
make import-sample      # Import from inputs/
make screen             # Run ML screening
make queue              # Get uncertain papers
make stats              # Screening statistics
make rank               # Top papers by relevance

# Two-Stage
make ft-retrievable     # Papers needing FT
make ft-flagged         # Flagged papers
make ft-progress        # FT retrieval progress
make stage2-queue       # Stage 2 eligible
make stage2-screen      # Run Stage 2 screening
make progression        # Stage flow stats

# PRISMA
make checklist          # PRISMA 2020 checklist
make prisma-flow        # Flow diagram data
make prisma-report      # Full PRISMA report
```

### Data Sources
```bash
make sources            # List configured sources
make download-all       # Download all sources
make import-downloaded  # Import downloaded files
```

---

## Research Context

### Search Strategy
**Databases**: Web of Science, ACM Digital Library, IEEE Xplore, Scopus, PubMed, ArXiv

**Search String**:
```
(
  ("machine-actionable" OR "maDMP" OR "data management plan" OR "DMP") 
  AND 
  (provenance OR "data lineage" OR "chain of custody" OR verification)
  AND
  (blockchain OR "distributed ledger" OR "smart contract" OR IPFS OR decentralized)
)
```

### Key Vocabulary
- **Core DMP**: Machine-actionable, maDMP, Data Management Plan, FAIR principles
- **Provenance**: Provenance, data lineage, chain of custody, verification
- **Platform**: Blockchain, distributed ledger, smart contract, IPFS

---

## Project Summary

| Phase | Status | Key Deliverables |
|-------|--------|------------------|
| Phase 1 | ✓ Complete | ML screening with confidence bands, batch review |
| Phase 2 | ✓ Complete | PRISMA 2020 checklist, protocol, report generator |
| Phase 3 | ✓ Complete | Two-stage screening, DOI retrieval, FT management |
| Phase 4 | ✓ Complete | Extraction schema, synthesis, quality assessment |
| Data Sources | ✓ Complete | URL downloader, multi-source import |
| Batch Operations | ✓ Complete | Batch review, CSV export |
| Auto-Config | ✓ Complete | Config auto-loads on startup |
| **Testing** | ⏳ Pending | Unit + integration tests |

**Total Endpoints**: ~40 API endpoints

---

## Known Limitations

1. **ML Accuracy**: SciBERT zero-shot not fine-tuned for domain
2. **Ground Truth**: No seed papers yet for similarity search
3. **Dual Review**: Single-reviewer mode (solo PhD)
4. **Protocol Registration**: Not yet registered on PROSPERO
5. **Data Visualization**: Charts/graphs not yet implemented
6. **PDF Export**: Report export not yet implemented

---

## API Access

- **Local**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Docker Hostname**: http://api:8000 (internal)

---

## Project Structure

```
slr_ml/
├── src/
│   ├── api/
│   │   ├── main.py              # FastAPI app
│   │   └── routers/             # Route modules
│   │       ├── papers.py         # Paper import/export
│   │       ├── screening.py      # ML screening workflow
│   │       ├── prisma.py         # PRISMA reporting
│   │       ├── enrichment.py     # DOI enrichment
│   │       ├── config.py         # Configuration
│   │       └── converters.py     # Format conversion
│   ├── ml/                       # ML classifiers
│   ├── pipeline/                 # Processing pipelines
│   ├── loaders/                  # BibTeX, CSV loaders
│   ├── connectors/               # ArXiv, DOI, URL downloader
│   ├── models/                   # Pydantic schemas
│   └── utils/                    # Shared utilities
├── config/                       # YAML configuration
├── inputs/                       # Input papers
├── outputs/                      # Generated reports
├── tests/                        # Test suite
└── docs/                         # Documentation
```
