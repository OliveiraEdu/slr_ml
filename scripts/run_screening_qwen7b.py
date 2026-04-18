#!/usr/bin/env python3
"""Run LLM screening with incremental saves."""

import asyncio
import json
import time
import sys

sys.path.insert(0, "/home/eduardo/Git/slr_ml")

from src.ml.ensemble_classifier import EnsembleVoter
from src.models.schemas import Paper

PAPERS_FILE = (
    "/home/eduardo/Git/d-OSPv2/docs/papers/search-results/deduplicated-papers.json"
)
OUTPUT_FILE = "/home/eduardo/Git/d-OSPv2/docs/papers/search-results/llm_qwen7b.json"
SAVE_INTERVAL = 50


async def main():
    # Load papers
    with open(PAPERS_FILE) as f:
        paper_data = json.load(f)

    papers = [Paper(**p) for p in paper_data]
    total = len(papers)
    print(f"Total papers: {total}", flush=True)

    # Load existing progress if any
    try:
        with open(OUTPUT_FILE) as f:
            existing = json.load(f)
        start_idx = len(existing.get("papers", []))
        results = existing.get("papers", [])
        patterns = existing.get("patterns", {})
        print(f"Resuming from: {start_idx}", flush=True)
    except FileNotFoundError:
        start_idx = 0
        results = []
        patterns = {}

    if start_idx >= total:
        print("Already complete!")
        return

    voter = EnsembleVoter(num_agents=4)
    start = time.time()

    for i in range(start_idx, total):
        p = papers[i]
        result = await voter.classify(p.title or "", p.abstract or "")
        v = result.get("votes", {})
        pat = f"{v.get('INCLUDE', 0)}-{v.get('EXCLUDE', 0)}"
        patterns[pat] = patterns.get(pat, 0) + 1

        results.append(
            {
                "title": p.title,
                "year": p.year,
                "doi": p.doi,
                "decision": result["decision"].value,
                "votes": v,
                "pattern": pat,
                "weighted_score": result.get("weighted_score", 0),
            }
        )

        if (i + 1) % SAVE_INTERVAL == 0:
            elapsed = time.time() - start
            rate = (i + 1 - start_idx) / elapsed if elapsed > 0 else 0
            remaining = (total - i - 1) / rate / 60 if rate > 0 else 0

            print(
                f"{i + 1}/{total} ({rate:.2f}/s, ~{remaining:.1f}min left)", flush=True
            )

            # Save progress
            with open(OUTPUT_FILE, "w") as f:
                json.dump(
                    {
                        "total": total,
                        "runtime_minutes": elapsed / 60,
                        "patterns": patterns,
                        "papers": results,
                    },
                    f,
                    default=str,
                )

    # Final save
    with open(OUTPUT_FILE, "w") as f:
        json.dump(
            {
                "total": total,
                "runtime_minutes": (time.time() - start) / 60,
                "patterns": patterns,
                "papers": results,
            },
            f,
            default=str,
            indent=2,
        )

    print(f"Done!", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
