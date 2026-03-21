# TODO - Next Session

## Priority 1: Completed ✅

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
