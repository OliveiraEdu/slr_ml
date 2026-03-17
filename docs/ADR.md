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
