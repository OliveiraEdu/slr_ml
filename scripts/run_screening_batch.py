#!/usr/bin/env python3
"""Run LLM screening in batches."""

import asyncio
import json
import time
import sys
sys.path.insert(0, '/home/eduardo/Git/slr_ml')

from src.ml.ensemble_classifier import EnsembleVoter
from src.models.schemas import Paper

BATCH_SIZE = 100
OUTPUT_FILE = "/home/eduardo/Git/d-OSPv2/docs/papers/search-results/llm_votes_incremental.json"

async def main():
    with open("/home/eduardo/Git/d-OSPv2/docs/papers/search-results/deduplicated-papers.json") as f:
        paper_data = json.load(f)
    
    papers = [Paper(**p) for p in paper_data]
    total = len(papers)
    print(f"Total papers: {total}", flush=True)
    
    # Load existing progress
    try:
        with open(OUTPUT_FILE) as f:
            existing = json.load(f)
        start_idx = len(existing)
        results = existing
        print(f"Resuming from: {start_idx}", flush=True)
    except FileNotFoundError:
        start_idx = 0
        results = []
    
    if start_idx >= total:
        print("Already complete!")
        return
    
    voter = EnsembleVoter(num_agents=4)
    start = time.time()
    
    for i in range(start_idx, total):
        p = papers[i]
        result = await voter.classify(p.title or '', p.abstract or '')
        v = result.get('votes', {})
        pat = f"{v.get('INCLUDE',0)}-{v.get('EXCLUDE',0)}"
        
        results.append({
            'title': p.title,
            'year': p.year,
            'doi': p.doi,
            'decision': result['decision'].value,
            'votes': v,
            'pattern': pat
        })
        
        if (i + 1) % 20 == 0:
            elapsed = time.time() - start
            rate = (i + 1 - start_idx) / elapsed if elapsed > 0 else 0
            remaining = (total - i - 1) / rate / 60 if rate > 0 else 0
            print(f"{i+1}/{total} ({rate:.2f}/s, ~{remaining:.1f}min)", flush=True)
            
            with open(OUTPUT_FILE, 'w') as f:
                json.dump(results, f, default=str)
    
    # Final save
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(results, f, default=str)
    
    patterns = {}
    for r in results:
        p = r['pattern']
        patterns[p] = patterns.get(p, 0) + 1
    
    print(f"Final: {patterns}")

if __name__ == "__main__":
    asyncio.run(main())