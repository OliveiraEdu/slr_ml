# TODO - Next Session

## Priority 1: Threshold & Workflow Fixes (Critical for Recall)

- [x] Lower default threshold from 0.6 to 0.35 for initial screening
  - File: `config/classification.yaml:167`
  - Change: `include: 0.35` (maximize recall for solo PhD)
  - Rationale: Better to over-capture and filter manually than miss relevant papers

- [x] Update README with threshold guidance
  - Add section explaining threshold selection by workflow type
  - Solo PhD: 0.35 | Team review: 0.5 | Conservative: 0.6

- [x] Test and validate lower threshold doesn't overwhelm manual review queue

- [x] CSV export/import for manual review workflow
  - Endpoint: `/screening/queue/uncertain/csv` (downloadable)
  - Endpoint: `/screening/review/import-csv` (upload)
  - Endpoint: `/screening/queue/all/csv` (full export)

- [x] Dual screening support with Cohen's Kappa
  - Endpoint: `/advanced/dual-screening/add`
  - Endpoint: `/advanced/dual-screening/kappa`
  - Endpoint: `/advanced/dual-screening/conflicts`

- [x] Sensitivity analysis
  - Endpoint: `/advanced/sensitivity/threshold`
  - Endpoint: `/advanced/sensitivity/confidence`

- [x] Risk of bias assessment
  - Endpoint: `/advanced/risk-of-bias/{id}`
  - Endpoint: `/advanced/risk-of-bias/batch`

- [x] Full-text retrieval
  - Endpoint: `/fulltext/retrieve`
  - Endpoint: `/fulltext/retrieve/batch`
  - Endpoint: `/fulltext/progress`

- [x] World-class readiness assessment
  - Endpoint: `/advanced/readiness`
  - Endpoint: `/advanced/completeness`

- [x] PRISMA completeness tracking
  - Pipeline: `src/pipeline/completeness.py`

- [x] Provenance tracking
  - Pipeline: `src/pipeline/provenance.py`

## Priority 2: Data Sources (Critical for Comprehensiveness)

- [x] Add gray literature sources
  - Add OpenGrey (opensgrey.org) to data_sources.yaml
  - Add EThOS (British Library) for theses
  - Add ClinicalTrials.gov for ongoing trials
  - Rationale: Gray literature can represent 20%+ of relevant studies

- [x] Add PROSPERO registration check
  - Add endpoint to query PROSPERO for protocol registration
  - Helps identify ongoing studies and reduce publication bias

- [x] Verify all configured sources (WoS, IEEE, ACM, Scopus, PubMed, arXiv) are accessible

## Priority 3: Advanced Search (Important for Precision)

- [x] Implement MeSH term matching for biomedical queries
  - Add MeSH lookup for PubMed-sourced papers
  - Enable ontology-based expansion

- [x] Add citation tracking beyond Scopus (CrossRef, Semantic Scholar)
  - Update src/ml/active_learning.py citation logic
  - Add Semantic Scholar API integration

- [x] Increase snowballing depth from 2 to 3-4
  - File: `config/classification.yaml:205`
  - Rationale: Deep citation chaining captures more related work

## Priority 4: Quality Assessment (Important for Rigor)

- [x] Add GRADE assessment support
  - Create src/pipeline/grade_assessment.py
  - Add endpoint `/prisma/quality/grade`
  - Standard for evidence quality in systematic reviews

- [x] Consider ROBIS instead of RoB 2.0/ROBINS-T
  - ROBIS is specifically designed for systematic reviews
  - More appropriate than domain-specific RoB tools

## Priority 5: PRISMA Enhancements (Documentation)

- [ ] Add PRISMA-P (protocol) generation
  - Endpoint to generate protocol for prospective registration
  - Required for publication in many journals

- [ ] Add flow diagram auto-generation as image
  - Current endpoint returns JSON data
  - Add image export (SVG/PNG) for publications

## Priority 6: Future Enhancements (Nice to Have)

- [ ] Implement WSS@95% stopping criterion for active learning
  - Work Saved over Sampling at 95% recall
  - Reduces manual review effort

- [ ] Add conflict of interest detection
  - Scan for funding sources and conflicts

- [ ] Add JBI checklist support (in addition to existing MMAT)
  - More comprehensive quality assessment

## Priority 2: Manual Review Workflow

- [ ] Test CSV import with real reviewed file
  ```bash
  # After reviewing in Excel
  curl -X POST http://localhost:8000/screening/review/import-csv \
    -H "Content-Type: text/plain" \
    --data-binary @reviewed_queue.csv
  ```

- [ ] Verify PRISMA report updates after manual review

## Priority 3: Documentation

- [x] README.md updated with new endpoints
- [x] User manual updated with solo PhD workflow
- [ ] Add script documentation to README
- [ ] Update API documentation screenshots

## Priority 4: Fine-tuning Pipeline (For Future)

- [ ] Implement GPU-enabled Dockerfile.ml for RTX 3500
  - Add CUDA support to `Dockerfile.ml`
  - Test fine-tuning on RTX 3500

- [ ] Create fine-tuning workflow
  - Use included papers as training data
  - Add excluded papers as negative samples
  - Fine-tune SciBERT for 3 epochs

## Priority 5: Active Learning Integration (For Future)

- [ ] Connect active learning to screening workflow
- [ ] Implement iterative retraining capability
- [ ] Add stopping criteria (WSS@95%)

## Notes

- API version: 0.6.0
- All new features committed and pushed
- Rebuild required after pulling changes

## Quick Test Commands

```bash
# Full workflow test
curl -X POST http://localhost:8000/papers/clear
curl -X POST http://localhost:8000/papers/import -d '{"source": "acm", ...}'
curl -X POST http://localhost:8000/papers/dedupe
curl -X POST http://localhost:8000/screening/run -d '{"threshold": 0.35}'
curl http://localhost:8000/screening/statistics
curl -X POST http://localhost:8000/prisma/extract
curl http://localhost:8000/prisma/synthesis

# Download CSV for manual review
curl -O http://localhost:8000/screening/queue/uncertain/csv

# Check new endpoints
curl http://localhost:8000/openapi.json | grep -o '"/advanced[^"]*"'
curl http://localhost:8000/openapi.json | grep -o '"/fulltext[^"]*"'
```
