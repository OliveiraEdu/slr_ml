# TODO - Next Session

## Priority 1: Testing & Verification

- [ ] Test enhanced screening endpoints after rebuild
  ```bash
  make rebuild
  make smoke-test
  make enhanced-workflow
  ```

- [ ] Verify API health after datasets dependency fix
  ```bash
  curl http://api:8000/health
  curl http://api:8000/openapi.json | grep -o '"/enhanced[^"]*"'
  ```

- [ ] Run full workflow test with all sources
  ```bash
  make import-sample
  make keyword-filter
  make screen
  make stats
  make prisma-flow
  ```

## Priority 2: Fine-tuning Pipeline

- [ ] Implement GPU-enabled Dockerfile.ml for RTX 3500
  - Add CUDA support to `Dockerfile.ml`
  - Test fine-tuning on RTX 3500

- [ ] Create fine-tuning workflow
  - Use included papers (416) as training data
  - Add ~200 excluded papers as negative samples
  - Fine-tune SciBERT for 3 epochs

## Priority 3: Active Learning Integration

- [ ] Connect active learning to screening workflow
- [ ] Implement manual labeling interface
- [ ] Add iterative retraining capability

## Priority 4: Snowballing Integration

- [ ] Test snowballing on included papers
- [ ] Verify Semantic Scholar API integration
- [ ] Add snowballing results to PRISMA flow

## Priority 5: Quality Improvements

- [ ] Adjust thresholds based on screening results
- [ ] Implement WSS@95% stopping criteria
- [ ] Add PRISMA quality metrics

## Notes

- API version should be updated to 0.6.0 after testing
- CHANGELOG.md already updated with v0.6.0 section
