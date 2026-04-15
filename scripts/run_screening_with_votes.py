#!/usr/bin/env python3
"""Run LLM screening with vote tracking - saves incrementally."""

import asyncio
import json
import time
import sys
sys.path.insert(0, '/home/eduardo/Git/slr_ml')

from src.ml.ensemble_classifier import EnsembleVoter, Decision
from src.models.schemas import Paper

SAVE_INTERVAL = 100
OUTPUT_DIR = "/home/eduardo/Git/d-OSPv2/docs/papers/search-results"
PAPERS_FILE = f"{OUTPUT_DIR}/deduplicated-papers.json"

async def main():
    # Load papers
    with open(PAPERS_FILE) as f:
        paper_data = json.load(f)
    
    papers = [Paper(**p) for p in paper_data]
    total = len(papers)
    print(f"Loaded {total} papers", flush=True)
    
    voter = EnsembleVoter(num_agents=4)
    results = []
    start = time.time()
    
    for i, p in enumerate(papers):
        result = await voter.classify(p.title or '', p.abstract or '')
        v = result.get('votes', {})
        pat = f"{v.get('INCLUDE',0)}-{v.get('EXCLUDE',0)}"
        
        results.append({
            'title': p.title,
            'year': p.year,
            'doi': p.doi,
            'decision': result['decision'].value,
            'votes': v,
            'pattern': pat,
            'weighted_score': result.get('weighted_score', 0)
        })
        
        if (i + 1) % 50 == 0:
            elapsed = time.time() - start
            rate = (i + 1) / elapsed
            remaining = (total - i - 1) / rate / 60
            print(f"Progress: {i+1}/{total} ({rate:.2f}/s, ~{remaining:.1f}min left)", flush=True)
            
            # Save incremental
            with open(f"{OUTPUT_DIR}/llm_votes_incremental.json", 'w') as f:
                json.dump(results, f, default=str)
    
    elapsed = time.time() - start
    
    # Analyze patterns
    patterns = {}
    for r in results:
        pat = r['pattern']
        patterns[pat] = patterns.get(pat, 0) + 1
    
    split_decision = [r for r in results if r['pattern'] == '2-2']
    
    print(f"\nDone in {elapsed/60:.1f}min")
    print(f"Patterns: {patterns}")
    print(f"Split (2-2): {len(split_decision)}")
    
    # Save full results
    with open(f"{OUTPUT_DIR}/llm_detailed_results.json", 'w') as f:
        json.dump({
            'total': total,
            'runtime_minutes': elapsed/60,
            'patterns': patterns,
            'papers': results
        }, f, default=str, indent=2)
    
    # Save split-decision queue
    with open(f"{OUTPUT_DIR}/split_decision_queue.json", 'w') as f:
        json.dump({
            'summary': {
                'total': len(split_decision),
                'pattern': '2-2',
                'description': 'Papers needing manual review (2 INCLUDE, 2 EXCLUDE votes)'
            },
            'papers': split_decision
        }, f, default=str, indent=2)
    
    print(f"\nSaved: llm_detailed_results.json, split_decision_queue.json")

if __name__ == "__main__":
    asyncio.run(main())