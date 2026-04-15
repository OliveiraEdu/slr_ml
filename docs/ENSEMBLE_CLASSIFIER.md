# Ensemble Multi-Agent Screening

## Summary

Created prototype in `src/ml/ensemble_classifier.py`.

### Results

| Paper | Decision | Confidence | Votes |
|-------|----------|------------|-------|
| SciChain (blockchain + provenance + scientific) | **INCLUDE** | 95% | 3/3 |
| Supply Chain for Retail | **EXCLUDE** | 95% | 0/3 |
| Blockchain for Research Provenance | **INCLUDE** | 95% | 3/3 |

### How to Use

```python
from src.ml.ensemble_classifier import EnsembleVoter

voter = EnsembleVoter()
result = await voter.classify(title, abstract)

print(result["decision"])  # INCLUDE/EXCLUDE/UNCERTAIN
print(result["auto_decide"])  # True/False
```

### Auto-Decide Logic

| Condition | Decision | Auto |
|-----------|----------|------|
| 3/3 INCLUDE | INCLUDE | ✅ |
| 2/3 INCLUDE | INCLUDE | ✅ |
| 3/3 EXCLUDE | EXCLUDE | ✅ |
| 2/3 EXCLUDE | EXCLUDE | (configurable) |
| otherwise | UNCERTAIN | ❌ manual |

### Next Steps to Productionize

1. **Replace simulate with real LLM API calls**
2. **Add API endpoint for batch processing**
3. **Add audit trail for PRISMA compliance**
4. **Integrate with screening pipeline**

### Files Created

- `src/ml/ensemble_classifier.py`