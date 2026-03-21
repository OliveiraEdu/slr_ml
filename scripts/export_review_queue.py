#!/usr/bin/env python3
"""Export and import manual review CSV for SLR screening."""
import csv
import sys
import json
import urllib.request
import urllib.error


API_BASE = "http://172.21.0.1:8000"


def export_uncertain_csv(limit=500, output_file="manual_review_queue.csv"):
    """Export uncertain papers queue to CSV."""
    print(f"Fetching uncertain queue from {API_BASE}...")
    
    url = f"{API_BASE}/screening/queue/uncertain?limit={limit}"
    try:
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode())
    except Exception as e:
        print(f"Error fetching data: {e}")
        return None
    
    queue = data.get("papers", [])
    print(f"Found {data['total']} papers needing manual review")
    
    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        
        writer.writerow([
            "review_order", "paper_id", "title", "authors", "year", 
            "doi", "journal", "source", "ml_decision", "ml_score",
            "composite_score", "confidence_band", "abstract_preview",
            "manual_decision", "review_reason"
        ])
        
        for idx, item in enumerate(queue, 1):
            p = item["paper"]
            r = item["result"]
            
            abstract_preview = (p.get("abstract") or "")[:200].replace("\n", " ")
            authors = "; ".join(p.get("authors") or [])
            
            writer.writerow([
                idx,
                p["id"],
                p.get("title", ""),
                authors,
                p.get("year", ""),
                p.get("doi", ""),
                p.get("journal", ""),
                p.get("source", ""),
                r.get("decision", ""),
                f'{r.get("relevance_score", 0):.4f}',
                f'{r.get("composite_score", 0):.4f}',
                r.get("confidence_band", ""),
                abstract_preview,
                "",  # manual_decision - to be filled
                ""   # review_reason - to be filled
            ])
    
    print(f"Exported {len(queue)} papers to {output_file}")
    print(f"\nFill in 'manual_decision' column with: include, exclude, or skip")
    print(f"Then run: python3 {sys.argv[0]} import reviewed_queue.csv")
    
    return output_file


def import_review_csv(input_file):
    """Import manual review decisions from CSV."""
    print(f"Importing reviews from {input_file}...")
    
    updated = []
    not_found = []
    errors = []
    
    with open(input_file, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            paper_id = row.get("paper_id", "").strip()
            decision = row.get("manual_decision", "").strip().lower()
            reason = row.get("review_reason", "").strip()
            
            if not paper_id or not decision:
                continue
            
            if decision not in ["include", "exclude", "skip"]:
                errors.append({"paper_id": paper_id, "invalid": decision})
                continue
            
            if decision == "skip":
                continue
            
            payload = json.dumps({
                "paper_id": paper_id,
                "decision": decision,
                "reason": reason,
                "notes": reason
            }).encode()
            
            req = urllib.request.Request(
                f"{API_BASE}/screening/review",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            
            try:
                with urllib.request.urlopen(req) as response:
                    result = json.loads(response.read().decode())
                    updated.append(paper_id)
            except urllib.error.HTTPError as e:
                error_body = e.read().decode()
                if "not found" in error_body.lower():
                    not_found.append(paper_id)
                else:
                    errors.append({"paper_id": paper_id, "error": str(e)})
            except Exception as e:
                errors.append({"paper_id": paper_id, "error": str(e)})
    
    print(f"\n=== Import Results ===")
    print(f"Updated: {len(updated)}")
    print(f"Not found: {len(not_found)}")
    print(f"Errors: {len(errors)}")
    
    if errors:
        print(f"\nFirst 5 errors:")
        for e in errors[:5]:
            print(f"  {e}")
    
    return {
        "updated": len(updated),
        "not_found": not_found,
        "errors": errors
    }


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print(f"  Export: python3 {sys.argv[0]} export [limit]")
        print(f"  Import: python3 {sys.argv[0]} import <csv_file>")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "export":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 500
        export_uncertain_csv(limit=limit)
    
    elif command == "import":
        if len(sys.argv) < 3:
            print("Error: specify CSV file to import")
            sys.exit(1)
        import_review_csv(sys.argv[2])
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
