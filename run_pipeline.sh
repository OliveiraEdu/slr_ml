#!/bin/bash
#
# SLR Engine - End-to-End Pipeline Script
# Runs: Import → Deduplicate → Screen → PRISMA Flow
#

set -e

API_URL="${API_URL:-http://localhost:8000}"

echo "=========================================="
echo "PRISMA 2020 SLR Engine - Full Pipeline"
echo "=========================================="

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check if API is running
check_api() {
    log_info "Checking API at $API_URL..."
    if curl -s -f "$API_URL/health" > /dev/null 2>&1; then
        log_info "API is running"
        return 0
    else
        log_error "API not running. Start with: make up"
        return 1
    fi
}

# Step 1: Import papers
import_papers() {
    log_info "Step 1: Importing papers from inputs/ directory..."
    
    RESPONSE=$(curl -s -X POST "$API_URL/papers/import-directory" \
        -H "Content-Type: application/json" \
        -d '{"directory": "inputs"}')
    
    echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
    
    TOTAL=$(echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('total_papers_in_store', 0))" 2>/dev/null || echo "0")
    
    log_info "Total papers imported: $TOTAL"
    echo "$TOTAL"
}

# Step 2: Deduplicate
deduplicate() {
    log_info "Step 2: Deduplicating papers..."
    
    # Get all papers and deduplicate
    RESPONSE=$(curl -s -X POST "$API_URL/papers/dedupe" \
        -H "Content-Type: application/json" \
        -d '{"papers": []}')
    
    echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
    
    REMOVED=$(echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('duplicates_removed', 0))" 2>/dev/null || echo "0")
    FINAL=$(echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('final_count', 0))" 2>/dev/null || echo "0")
    
    log_info "Duplicates removed: $REMOVED"
    log_info "Papers after deduplication: $FINAL"
    echo "$FINAL"
}

# Step 3: Run screening
run_screening() {
    log_info "Step 3: Running ML screening..."
    
    # Get papers for screening
    PAPERS=$(curl -s "$API_URL/papers/list?limit=1000")
    
    # Count papers
    TOTAL=$(echo "$PAPERS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('total', 0))" 2>/dev/null || echo "0")
    
    if [ "$TOTAL" -eq 0 ]; then
        log_warn "No papers to screen"
        return
    fi
    
    log_info "Screening $TOTAL papers..."
    
    # Run screening with papers from API
    RESPONSE=$(curl -s -X POST "$API_URL/screening/run" \
        -H "Content-Type: application/json" \
        -d "{\"papers\": $(echo '$PAPERS' | python3 -c 'import sys,json; d=json.load(sys.stdin); import json; print(json.dumps(d.get(\"papers\", [])[:500]))')}")
    
    echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
    
    INCLUDED=$(echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('included', 0))" 2>/dev/null || echo "0")
    EXCLUDED=$(echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('excluded', 0))" 2>/dev/null || echo "0")
    BACKEND=$(echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('backend', 'unknown'))" 2>/dev/null || echo "unknown")
    
    log_info "Screening complete using: $BACKEND backend"
    log_info "Included: $INCLUDED"
    log_info "Excluded: $EXCLUDED"
}

# Step 4: Generate PRISMA flow
generate_prisma() {
    log_info "Step 4: Generating PRISMA flow diagram..."
    
    RESPONSE=$(curl -s "$API_URL/prisma/flow")
    
    echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
    
    IDENTIFIED=$(echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('identification_identified', 0))" 2>/dev/null || echo "0")
    INCLUDED=$(echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('included_studies', 0))" 2>/dev/null || echo "0")
    
    log_info "PRISMA Flow:"
    log_info "  - Papers identified: $IDENTIFIED"
    log_info "  - Studies included: $INCLUDED"
}

# Step 5: Export PRISMA diagram
export_prisma() {
    log_info "Step 5: Exporting PRISMA diagram..."
    
    RESPONSE=$(curl -s "$API_URL/prisma/export?format=json")
    
    echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
    
    PATH=$(echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('path', ''))" 2>/dev/null || echo "")
    
    if [ -n "$PATH" ]; then
        log_info "Exported to: $PATH"
    fi
}

# Main pipeline
main() {
    # Check API
    check_api || exit 1
    
    echo ""
    
    # Run pipeline steps
    import_papers
    
    echo ""
    
    deduplicate
    
    echo ""
    
    run_screening
    
    echo ""
    
    generate_prisma
    
    echo ""
    
    export_prisma
    
    echo ""
    echo "=========================================="
    log_info "Pipeline complete!"
    echo "=========================================="
}

# Show usage
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --api-url URL    API URL (default: http://localhost:8000)"
    echo "  --skip-import    Skip import step"
    echo "  --skip-dedupe    Skip deduplication"
    echo "  --skip-screen    Skip screening"
    echo "  --help          Show this help"
    echo ""
    echo "Examples:"
    echo "  $0                    # Run full pipeline"
    echo "  $0 --skip-screen     # Run without ML screening"
    echo "  --api-url http://localhost:9000  # Custom API URL"
}

# Parse arguments
SKIP_IMPORT=false
SKIP_DEDUPE=false
SKIP_SCREEN=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --api-url)
            API_URL="$2"
            shift 2
            ;;
        --skip-import)
            SKIP_IMPORT=true
            shift
            ;;
        --skip-dedupe)
            SKIP_DEDUPE=true
            shift
            ;;
        --skip-screen)
            SKIP_SCREEN=true
            shift
            ;;
        --help)
            usage
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

main
