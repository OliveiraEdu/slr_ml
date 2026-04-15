# Ensemble Multi-Agent LLM Screening

## Overview

The ensemble classifier uses multiple LLM agents with different strictness levels to classify papers for systematic literature review (SLR) screening. It applies voting consensus with confidence-weighted scoring for automated decisions.

## Architecture

**Model**: Qwen2.5-1.5B (via llama-server)  
**Location**: `/home/eduardo/Git/llama.cpp/models/qwen2.5-1.5b-instruct-q4_k_m.gguf`  
**Server**: llama-server on port 8080  

### 4-Agent Ensemble

| Agent | Strictness | Weight | Role |
|-------|-----------|--------|------|
| Strict-A | strict | 1.0 | Conservative, requires strong match |
| Balanced-B | balanced | 1.2 | Neutral, slight boost for inclusion |
| Detailed-D | detailed | 1.1 | Thorough analysis |
| Lenient-C | lenient | 0.8 | More permissive |

## Screening Criteria

**TOPIC**: Blockchain-anchored machine-actionable Data Management Plans (maDMPs) for scientific data provenance

### Inclusion Criteria (I1-I5)
- I1: English language
- I2: Journal, conference, or arXiv preprint
- I3: Published 2020-2026
- I4: Technical implementation (not conceptual)
- I5: maDMP OR (blockchain + provenance + scientific/research data)

### Exclusion Criteria (E1-E7)
- E1: Opinion/editorial pieces
- E2: Non-research: supply chain, finance, cryptocurrency
- E3: No technical implementation
- E4: Duplicate
- E5: Full text unavailable
- E6: No blockchain component
- E7: No scientific data context

## Usage

### Makefile Commands

```bash
cd /home/eduardo/Git/slr_ml
source .venv/bin/activate

# Start LLM server
make llama-start

# Test with sample papers
make llm-test

# Run screening
make llm-screen-tuned

# Full workflow
make llm-workflow

# Stop server
make llama-stop
```

### Python API

```python
from src.ml.ensemble_classifier import EnsembleVoter
from src.models.schemas import Paper

voter = EnsembleVoter(num_agents=4)
result = await voter.classify(title, abstract)

print(result["decision"])  # INCLUDE/EXCLUDE
print(result["votes"])  # {'INCLUDE': 3, 'EXCLUDE': 1}
print(result["weighted_score"])  # 0.78
```

## Vote Patterns & Auto-Decide

| Pattern | Votes | Decision | Auto-Decide |
|---------|-------|----------|------------|
| 4-0 | All INCLUDE | INCLUDE | ✅ |
| 3-1 | Majority INCLUDE | INCLUDE | ✅ |
| 2-2 | Split | UNCERTAIN | ❌ Manual |
| 1-3 | Majority EXCLUDE | EXCLUDE | ✅ |
| 0-4 | All EXCLUDE | EXCLUDE | ✅ |

**Auto-decide threshold**: weighted_score ≥ 0.75

## Results (April 2026)

| Pattern | Count | % | Decision |
|---------|-------|---|----------|
| 4-0 | 481 | 41.5% | INCLUDE |
| 3-1 | 124 | 10.7% | INCLUDE |
| 2-2 | 113 | 9.8% | MANUAL |
| 1-3 | 227 | 19.6% | EXCLUDE |
| 0-4 | 213 | 18.4% | EXCLUDE |

**Summary** (1,158 papers):
- Auto-INCLUDE: 605 (52.2%)
- Auto-EXCLUDE: 440 (38.0%)
- Manual review: 113 (9.8%)

**Confidence**:
- High (unanimous): 694 (59.9%)
- Medium (majority): 351 (30.3%)
- Low (split): 113 (9.8%)

## Performance

- **Speed**: ~0.35 papers/second
- **Runtime**: ~55 minutes for 1,158 papers
- **Model**: Qwen2.5-1.5B GGUF (~1.1GB)

## Files

| File | Description |
|------|-------------|
| `src/ml/ensemble_classifier.py` | Main classifier implementation |
| `scripts/run_screening_batch.py` | Batch processing script |
| `scripts/start_llama_server_small.sh` | Server startup script |
| `search-results/llm_detailed_results.json` | Full results with votes |
| `search-results/split_decision_queue.json` | Manual review queue |

## Next Steps

1. Run manual review on 113 split-decision papers
2. Generate final PRISMA flow diagram
3. Export included papers for citation analysis
4. Fine-tune agent prompts based on review feedback