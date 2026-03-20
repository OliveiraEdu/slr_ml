# Architectural Decision Records (ADR)

## ADR-001: Configuration-Driven Architecture

**Date:** 2026-03-16  
**Status:** Accepted

### Context

The SLR Engine needs to be flexible enough to support different research topics, classification criteria, and reporting requirements without code changes.

### Decision

Use YAML configuration files for all settings:
- `config/sources.yaml` - Data sources and file paths
- `config/classification.yaml` - Classification criteria and prompts
- `config/prisma.yaml` - PRISMA reporting settings
- `config/extraction.yaml` - Extraction keywords and quality criteria

### Consequences

**Positive:**
- No code changes needed to adapt to new research topics
- Users can modify behavior via config files
- Easy to maintain and version control configurations
- Supports different PRISMA review types

**Negative:**
- More complex initial setup
- Configuration validation becomes important

---

## ADR-002: REST API as Primary Interface

**Date:** 2026-03-16  
**Status:** Accepted

### Context

The system needs to be accessible from various clients (web UI, scripts, other tools).

### Decision

Use FastAPI with OpenAPI/Swagger documentation as the primary interface.

### Consequences

**Positive:**
- Self-documenting API
- Easy integration with other tools
- Built-in request validation
- Swagger UI for testing

**Negative:**
- HTTP overhead for batch operations

---

## ADR-003: Keyword-Based Classification with Fallback

**Date:** 2026-03-16  
**Status:** Accepted

### Context

ML models (SciBERT) may not be available in all environments.

### Decision

1. Primary: SciBERT zero-shot classification
2. Fallback: Keyword-based matching when ML unavailable

### Consequences

**Positive:**
- Works without ML dependencies
- Fast keyword fallback
- Gradual degradation

**Negative:**
- Keyword accuracy lower than ML

---

## ADR-004: In-Memory State Management

**Date:** 2026-03-16  
**Status:** Accepted

### Context

The system processes papers in a session-based workflow.

### Decision

Use in-memory `app_state` dictionary for papers, results, and config.

### Consequences

**Positive:**
- Fast access
- Simple implementation
- No database setup required

**Negative:**
- State lost on restart
- Not suitable for long-running multi-user deployments

---

## ADR-005: Health Check for Distributed Services

**Date:** 2026-03-17  
**Status:** Accepted

### Context

The system has multiple containers (API and ml-worker) that need health monitoring.

### Decision

- `/health` endpoint checks both API and ml-worker
- ml-worker exposes health endpoint on port 8001
- Returns "healthy" or "degraded" based on service availability

### Consequences

**Positive:**
- Container orchestration can monitor health
- Clear status reporting
- Early failure detection

**Negative:**
- Additional complexity in ml-worker

---

## ADR-006: Automatic Study Extraction

**Date:** 2026-03-17  
**Status:** Accepted

### Context

PRISMA 2020 reports require detailed study characteristics (blockchain platform, research focus, etc.).

### Decision

- Configurable keyword-based extraction from paper metadata
- Extraction keywords in `config/extraction.yaml`
- Auto-extract: research focus, blockchain platform, storage integration, permission model

### Consequences

**Positive:**
- Automated extraction saves manual work
- Configurable for different domains
- Produces structured data for analysis

**Negative:**
- Keyword-based extraction less accurate than manual extraction

---

## ADR-007: MMAT-Based Quality Assessment

**Date:** 2026-03-17  
**Status:** Accepted

### Context

PRISMA 2020 requires quality assessment of included studies.

### Decision

- Auto-assess quality using MMAT criteria keywords
- Rate papers based on presence of methodology-related terms
- Rating: Excellent/Good/Acceptable/Poor/Very Poor

### Consequences

**Positive:**
- Automated quality scoring
- Configurable criteria
- Consistent with PRISMA 2020

**Negative:**
- Less accurate than expert manual assessment

---

## ADR-008: Markdown Report Generation

**Date:** 2026-03-17  
**Status:** Accepted

### Context

Users need human-readable PRISMA 2020 reports.

### Decision

- Generate markdown reports with embedded Mermaid diagrams
- Configurable sections
- Export both JSON and markdown formats

### Consequences

**Positive:**
- Human-readable output
- Mermaid diagrams render in GitHub/GitLab
- Easy to version control

**Negative:**
- Limited styling options in markdown

---

## ADR-009: Modular Router Architecture

**Date:** 2026-03-20  
**Status:** Accepted

### Context

The original `main.py` grew to 882 lines with mixed concerns (papers, screening, PRISMA, config, enrichment, converters).

### Decision

Split main.py into modular routers:
- `routers/papers.py` - Paper import, export, DOI management
- `routers/screening.py` - ML screening, review, statistics
- `routers/prisma.py` - PRISMA reports, checklist, extraction
- `routers/enrichment.py` - DOI metadata enrichment
- `routers/config.py` - Configuration management
- `routers/converters.py` - Document format conversion

### Consequences

**Positive:**
- Each router has single responsibility
- Easier to maintain and test
- Clear separation of concerns
- Team can work on routers independently

**Negative:**
- More files to manage
- Cross-cutting concerns need careful handling

---

## ADR-010: Two-Stage Screening Workflow

**Date:** 2026-03-20  
**Status:** Accepted

### Context

Single-stage screening doesn't reflect PRISMA 2020 methodology. Full-text review requires DOI-based retrieval.

### Decision

Implement two-stage screening:
1. **Stage 1** (Title/Abstract): ML screens all papers
2. **Stage 2** (Full-Text): Manual review of included papers with DOI

Papers without DOI are flagged and excluded from Stage 2 (except ArXiv preprints).

### Consequences

**Positive:**
- PRISMA 2020 compliant workflow
- Clear progression tracking
- Handles DOI availability limitations

**Negative:**
- More complex state management
- Additional endpoints required

---

## ADR-011: Confidence Bands for ML Classification

**Date:** 2026-03-20  
**Status:** Accepted

### Context

Binary include/exclude decisions from ML lack interpretability for solo PhD review.

### Decision

Use confidence bands with thresholds:
- **High**: score ≥ 0.75 or ≤ 0.25 (auto-decide)
- **Medium**: score ≥ 0.55 or ≤ 0.45 (review recommended)
- **Low**: score 0.45-0.55 (manual review required)

### Consequences

**Positive:**
- Interpretable ML confidence
- Reduces manual review burden
- Clear workflow for reviewers

**Negative:**
- Threshold tuning required
- May miss edge cases

---

## ADR-012: Auto-Config Loading on Startup

**Date:** 2026-03-20  
**Status:** Accepted

### Context

Manual config loading via `/config/load` endpoint was required before using the system.

### Decision

Load configuration automatically on FastAPI startup event:
- Sources, classification, and PRISMA configs loaded from YAML
- No manual initialization required
- Fallback to empty config on failure

### Consequences

**Positive:**
- Zero-configuration startup
- Fewer setup steps for users
- Consistent initial state

**Negative:**
- Startup errors harder to debug
- Less control over config timing

---

## ADR-013: Host-Based Integration Testing

**Date:** 2026-03-20  
**Status:** Accepted

### Context

Tests cannot run from inside Docker containers (no curl installed).

### Decision

Run integration tests from host machine against running API at localhost:8000:
- Separate `test_integration.py` from unit tests
- `make test` - Unit tests only
- `make test-integration` - Integration tests (requires running API)
- `make test-all` - All tests

### Consequences

**Positive:**
- Tests run in dev environment
- Can use local curl/pytest
- CI/CD friendly

**Negative:**
- Requires API to be running
- More complex test setup

---

## ADR-014: URL-Based Data Source Downloads

**Date:** 2026-03-20  
**Status:** Accepted

### Context

Paper data needed to be downloaded from remote repositories (GitHub, etc.) in addition to local files.

### Decision

Create URL downloader connector:
- `config/data_sources.yaml` - Remote URL configuration
- Download BibTeX/CSV directly from URLs
- Cache downloads locally
- Import + download in one step

### Consequences

**Positive:**
- Automated data fetching
- Reproducible paper collection
- GitHub-hosted data integration

**Negative:**
- Network dependency
- URL availability issues

---

## ADR-015: CSV Export for Thesis Appendix

**Date:** 2026-03-20  
**Status:** Accepted

### Context

PhD thesis requires data tables in appendix (extraction data, quality assessments).

### Decision

Add CSV export endpoints:
- `GET /prisma/extraction/export` - Extraction data as CSV
- `GET /prisma/quality/export` - Quality assessments as CSV

### Consequences

**Positive:**
- Thesis-ready data tables
- Easy import to Excel/LaTeX
- Audit trail for extracted data

**Negative:**
- Limited formatting options
- Requires careful column naming
