# slr_ml Workflow Documentation

## Hybrid LLM + Human Review Workflow

This document describes the automated LLM screening with human expert review workflow.

## Workflow Stages

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    HYBRID WORKFLOW                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  STAGE 1: Database Search                                                  │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ - Query IEEE Xplore, ACM, Web of Science, Scopus, arXiv                 │    │
│  │ - Export BibTeX/CSV files                                           │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                     │
│                                    ▼                                     │
│  STAGE 2: Import & Deduplicate                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ - Parse BibTeX/CSV                                                  │    │
│  │ - Remove duplicates based on DOI/title                              │    │
│  │ - Output: deduplicated-papers.json (1,158 papers)                  │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                     │
│                                    ▼                                     │
│  STAGE 3: LLM Agentic Screening                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ - 4 agents: Strict, Balanced, Detailed, Lenient                     │    │
│  │ - Vote on each paper (INCLUDE/EXCLUDE)                             │    │
│  │ - Output patterns: 4-0, 3-1, 2-2, 1-3, 0-4                  │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                     │
│                                    ▼                                     │
│  STAGE 4: Confidence-Based Routing                                        │
│  ┌─────────────────────────────────────────��───────────────────────────┐    │
│  │ HIGH (4-0, 0-4) → Auto-decide                                   │    │
│  │ MEDIUM (3-1, 1-3) → Human review                               │    │
│  │ LOW (2-2) → Human review                                        │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Current Results

| Stage | Papers | % |
|-------|--------|---|
| Identified | 1,158 | 100% |
| Auto-INCLUDE | 481 | 41.5% |
| Auto-EXCLUDE | 213 | 18.4% |
| Human Review | 464 | 40.1% |

### Vote Pattern Distribution

| Pattern | Count | Description | Action |
|---------|-------|-------------|--------|
| 4-0 | 481 | Unanimous INCLUDE | Auto-INCLUDE |
| 3-1 | 124 | Majority INCLUDE | Human review |
| 2-2 | 113 | Split decision | Human review |
| 1-3 | 227 | Majority EXCLUDE | Human review |
| 0-4 | 213 | Unanimous EXCLUDE | Auto-EXCLUDE |

## Commands

### Running the Workflow

```bash
# Start LLM server
make llama-start

# Run screening
make llm-screen-tuned

# Export results
make export
```

### Manual Steps

1. **Review human queue**: Edit `docs/human_review_queue.csv`
2. **Fill decisions**: Add `expert_decision` (INCLUDE/EXCLUDE)
3. **Add reasons**: Fill `expert_reason` column
4. **Regenerate PRISMA**: `make prisma-flow`

## Files Generated

| File | Description |
|------|-------------|
| `outputs/deduplicated-papers.json` | 1,158 deduplicated papers |
| `outputs/llm_detailed_results.json` | Full LLM screening results |
| `docs/human_review_queue.csv` | 464 papers for review |
| `docs/PRISMA_FLOW.md` | PRISMA flow diagram |

## Human Review Process

### Reviewers should:
1. Read title and abstract
2. Check full text if uncertain
3. Make INCLUDE/EXCLUDE decision
4. Provide brief justification

### Decision Criteria

**INCLUDE if:**
- Technical implementation of blockchain for scientific data
- Data provenance/writing/traceability
- Machine-actionable Data Management Plans

**EXCLUDE if:**
- Non-research domain (supply chain, finance, crypto)
- Opinion/editorial
- No blockchain component
- No scientific data context

## Integration with d-OSPv2

slr_ml is independent of d-OSPv2. For scholarly use:
- Export human review queue
- Use in any reference manager
- Cite using standard formats

For d-OSPv2 authentication, see d-OSPv2 documentation (separate project).