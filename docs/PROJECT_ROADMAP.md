# Project Roadmap: ML-Assisted Systematic Literature Review

**Project**: Blockchain-Provenance SLR for Machine-Actionable Data Management Plans  
**Research Question**: "How can machine-actionable Data Management Plans (maDMPs) be persisted on a blockchain to enable verifiable provenance tracking for scientific data?"  
**Estimated Paper Volume**: ~8,000 records  
**Target Venues**: Computer Science PhD Thesis

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
- [x] PRISMA-ready statistics generation

#### Confidence Band Thresholds
- **High**: score ≥ 0.75 or ≤ 0.25
- **Medium**: score ≥ 0.55 or ≤ 0.45  
- **Low**: score between 0.45 and 0.55 (manual review required)

#### Status: Complete ✓

#### Implementation Log

| Date | Activity | Details |
|------|----------|---------|
| 2026-03-20 | Design discussion | Agreed on incremental approach, solo PhD workflow |
| 2026-03-20 | Technical debt refactor | Split API into routers, created test suite |
| 2026-03-20 | Phase 1 implementation | Confidence bands, keyword boosting, manual review queue |
| 2026-03-20 | Domain config | Updated classification.yaml with maDMP/blockchain keywords |
| 2026-03-20 | PRISMA config | Updated exclusion reasons for domain-specific research |

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

#### New Endpoints
| Endpoint | Description |
|----------|-------------|
| `GET /prisma/checklist` | Get full 27-item PRISMA 2020 checklist |
| `PUT /prisma/protocol` | Update protocol metadata |
| `PUT /prisma/checklist/item` | Update individual checklist item status |
| `GET /prisma/checklist/report` | Get checklist grouped by section |
| `POST /prisma/report/full` | Generate complete PRISMA report |

#### Status: Complete ✓

#### Implementation Log (Phase 2)
| Date | Activity | Details |
|------|----------|---------|
| 2026-03-20 | Checklist schema | Added PrismaChecklist, PrismaChecklistItem, PrismaProtocol models |
| 2026-03-20 | Checklist endpoints | Added CRUD operations for checklist items |
| 2026-03-20 | Report generator | Added full PRISMA report with checklist integration |

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

#### New Endpoints
| Endpoint | Description |
|----------|-------------|
| `GET /screening/progression` | Paper flow through stages |
| `GET /screening/queue/stage2` | Papers eligible for Stage 2 |
| `POST /screening/stage2` | Run Stage 2 screening |
| `POST /screening/review/batch` | Batch update multiple papers |

#### Workflow
1. **Stage 1** (title/abstract): ML screens all papers
2. **Flag & Retrieve**: Papers without DOI are flagged (except ArXiv)
3. **Stage 2** (full-text): Manual review of included papers
4. **Final**: Export PRISMA flow with stage breakdown

#### Status: Complete ✓

#### Implementation Log (Phase 3)
| Date | Activity | Details |
|------|----------|---------|
| 2026-03-20 | Full-text schema | Added FullTextSource enum, paper tracking fields |
| 2026-03-20 | DOI flagging | Papers without DOI flagged and excluded from Stage 2 |
| 2026-03-20 | Progression tracking | Added stage_1/stage_2 decision tracking |
| 2026-03-20 | PRISMA flow | Updated to include stage transitions and FT stats |

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

#### Extraction Fields
| Category | Fields |
|----------|--------|
| **Blockchain** | platform, type, consensus mechanism, smart contract language |
| **Data Management** | maDMP standard, metadata schema, FAIR compliance |
| **Provenance** | model, approach, verification mechanism |
| **Storage** | integration type, partitioning, encryption |
| **Access Control** | permission model, mechanism |

#### New Endpoints
| Endpoint | Description |
|----------|-------------|
| `GET /prisma/extraction/template` | Get maDMP extraction form template |
| `GET /prisma/extraction/{paper_id}` | Get extraction data for paper |
| `PUT /prisma/extraction/{paper_id}` | Save extraction data |
| `GET /prisma/extraction/export` | Export extraction data as CSV |
| `GET /prisma/synthesis` | Get synthesis statistics |
| `GET /prisma/synthesis/platforms` | Platform analysis |
| `GET /prisma/synthesis/distributions` | Distribution statistics |
| `GET /prisma/synthesis/gaps` | Research gaps identification |
| `POST /prisma/synthesis/report` | Generate synthesis report |
| `POST /prisma/quality/assess` | Run quality assessment |
| `GET /prisma/quality/{paper_id}` | Get quality for specific paper |
| `PUT /prisma/quality/{paper_id}` | Update quality assessment |
| `GET /prisma/quality/export` | Export quality data as CSV |

#### Synthesis Generator Methods
- `_analyze_blockchains()`: Platform and consensus analysis
- `_analyze_platforms()`: Technology distribution
- `_analyze_approaches()`: Research approach breakdown
- `_analyze_evaluations()`: Evaluation method analysis
- `_identify_gaps()`: Research gap detection
- `_identify_trends()`: Trend identification

#### Status: Complete ✓

#### Implementation Log (Phase 4)
| Date | Activity | Details |
|------|----------|---------|
| 2026-03-20 | Extraction schema | Added ExtractionData with 35+ fields for maDMP/blockchain |
| 2026-03-20 | Extraction pipeline | Created ExtractionExtractor with keyword-based extraction |
| 2026-03-20 | Quality assessment | Added QualityAssessor with MMAT criteria |
| 2026-03-20 | Synthesis generator | Created SynthesisGenerator with analysis methods |
| 2026-03-20 | Synthesis endpoints | Added synthesis and quality assessment API endpoints |

---

### Data Source Downloads

The system supports automatic download of paper exports from remote URLs.

#### Configuration
File: `config/data_sources.yaml`

```yaml
sources:
  wos:
    enabled: true
    base_url: "https://raw.githubusercontent.com/OliveiraEdu/R/master/data"
    files:
      - "wos.bib"
    format: "bibtex"
```

#### Supported Sources
| Source | Format | Description |
|--------|--------|-------------|
| Web of Science (WoS) | BibTeX | Web of Science exports |
| IEEE Xplore | BibTeX | IEEE Xplore exports |
| ACM Digital Library | BibTeX | ACM Digital Library exports |
| Scopus | BibTeX/CSV | Scopus exports |
| PubMed | BibTeX/CSV | PubMed/MEDLINE exports |
| ArXiv | API | ArXiv preprints via API |

#### New Endpoints
| Endpoint | Description |
|----------|-------------|
| `GET /papers/sources` | List configured data sources |
| `POST /papers/download` | Download a file from URL |
| `POST /papers/download-all` | Download all configured sources |
| `POST /papers/import-from-url` | Download and import in one step |

#### Makefile Commands
```bash
make sources              # List configured sources
make download-all        # Download all sources
make download-and-import  # Download and import
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

**Justification for title-only screening**:
> "Due to the high volume of records identified (>8,000), title-only screening was conducted as the initial phase, with full abstract review of records meeting title inclusion criteria. This approach balances methodological rigor with practical resource constraints, consistent with PRISMA 2020 guidance on feasibility considerations."

### Key Vocabulary

**Core DMP Concepts**:
- Machine-actionable, maDMP, Data Management Plan, DMP
- FAIR principles, metadata standards

**Provenance/Tracking**:
- Provenance, data lineage, chain of custody, verification
- Reproducibility, reproducibility

**Platform/Storage**:
- Blockchain, distributed ledger, smart contract, IPFS
- Decentralized storage, repository

---

## Technical Architecture

```
INPUT → DEDUP → ML SCREENING → CONFIDENCE FILTER → MANUAL REVIEW → INCLUDED
           ↓           ↓               ↓
        Papers    Confidence    High/Med/Low
                   Bands        Threshold
```

### Confidence Band Thresholds
- **High**: score ≥ 0.75 → Auto-include
- **Medium**: 0.55 ≤ score < 0.75 → Manual review recommended
- **Low**: 0.45 ≤ score < 0.55 → Manual review required
- **Exclude**: score < 0.45 → Auto-exclude (if desired)

---

## Current Limitations & Known Gaps

1. **ML Accuracy**: SciBERT zero-shot not fine-tuned for domain
2. **Ground Truth**: No seed papers yet for similarity search
3. **Dual Review**: Single-reviewer mode (solo PhD)
4. **Protocol Registration**: Not yet registered on PROSPERO
5. **Data Visualization**: Charts/graphs not yet implemented
6. **Export Formats**: PDF/LaTeX report export not yet implemented

---

## Completed Workflow

### Full SLR Pipeline
```
1. Import papers from BibTeX/CSV
2. Download from configured sources (WoS, IEEE, ACM, etc.)
3. Deduplicate papers
4. ML-assisted title/abstract screening (Phase 1)
5. Manual review of uncertain papers
6. Stage 1 → Stage 2 progression
7. Full-text retrieval (DOI-based)
8. Stage 2 full-text screening
9. Data extraction with maDMP/blockchain fields (Phase 4)
10. Quality assessment with MMAT criteria
11. Synthesis and trend analysis
12. PRISMA 2020 report generation
```

### API Commands
```bash
# Run full workflow
make run                    # Start API server
make test                   # Run test suite

# Paper management
curl -X GET "http://localhost:8000/papers"  # List papers
curl -X POST "http://localhost:8000/papers/import"  # Import papers

# Screening workflow
curl -X POST "http://localhost:8000/screening/run"  # Run ML screening
curl -X GET "http://localhost:8000/screening/queue"  # Get review queue

# PRISMA reporting
curl -X POST "http://localhost:8000/prisma/report/full"  # Generate PRISMA report
curl -X GET "http://localhost:8000/prisma/synthesis"  # Get synthesis stats
```

---

## Project Summary

| Phase | Status | Key Deliverables |
|-------|--------|------------------|
| Phase 1 | ✓ Complete | ML screening with confidence bands, keyword boosting |
| Phase 2 | ✓ Complete | PRISMA 2020 checklist, protocol, full report generator |
| Phase 3 | ✓ Complete | Two-stage screening, DOI retrieval, FT management |
| Phase 4 | ✓ Complete | Data extraction schema, quality assessment, synthesis |
| Data Sources | ✓ Complete | URL downloader, multi-source import |
| Batch Operations | ✓ Complete | Batch review, CSV export |
| Auto-Config | ✓ Complete | Config auto-loads on startup |

**Total Endpoints**: ~40 API endpoints for full SLR workflow
