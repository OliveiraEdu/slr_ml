.PHONY: help install convert build build-api build-ml build-all rebuild up down logs clean python-upgrade verify-api smoke-test

# Docker hostnames for internal communication
API_HOST=api
ML_WORKER_HOST=ml-worker
API_PORT=8000
ML_WORKER_PORT=8001

# API URL: Use localhost if accessible, otherwise fallback to Docker hostname
API_URL := $(shell curl -s --connect-timeout 2 http://localhost:8000/health >/dev/null 2>&1 && echo "http://localhost:8000" || echo "http://api:8000")

help:
	@echo "PRISMA 2020 SLR Engine - Make Commands"
	@echo ""
	@echo "=== Docker Deployment ==="
	@echo "  make build         Build Docker containers (CPU PyTorch)"
	@echo "  make build-api     Build only API container"
	@echo "  make build-ml     Build only ML worker container"
	@echo "  make build-all     Build all containers (alias for build)"
	@echo "  make rebuild       Pull latest code and rebuild all services"
	@echo "  make up            Start all services"
	@echo "  make down          Stop all services"
	@echo "  make logs          View logs (all services)"
	@echo "  make logs-api      View API logs"
	@echo "  make logs-ml      View ML worker logs"
	@echo "  make clean         Clean up containers and volumes"
	@echo "  make status        Check service health"
	@echo ""
	@echo "=== Development ==="
	@echo "  make install       Install dependencies locally"
	@echo "  make run-api       Run API locally (for development)"
	@echo "  make lint          Run code linting"
	@echo "  make typecheck     Run mypy type checking"
	@echo ""
	@echo "=== Testing ==="
	@echo "  make test          Run pytest"
	@echo "  make test-watch    Run pytest with watch mode"
	@echo "  make coverage      Run pytest with coverage report"
	@echo ""
	@echo "=== Data Source Download ==="
	@echo "  make sources         List configured data sources"
	@echo "  make download-all    Download all configured sources"
	@echo "  make import-downloaded  Import downloaded files"
	@echo ""
	@echo "=== API Testing (via Docker) ==="
	@echo "  make health        Check API health (via Docker hostname)"
	@echo "  make verify-api    Verify API is accessible (local or Docker)"
	@echo "  make smoke-test    Run comprehensive API smoke test"
	@echo "  make import-sample  Import sample papers for testing"
	@echo "  make screen        Run ML screening on imported papers"
	@echo "  make queue          Get uncertain papers for manual review"
	@echo "  make stats         Get screening statistics"
	@echo ""
	@echo "=== Two-Stage Screening (Phase 3) ==="
	@echo "  make ft-retrievable  Get papers needing full-text retrieval"
	@echo "  make ft-flagged      Get papers flagged for no DOI"
	@echo "  make ft-progress     Full-text retrieval progress"
	@echo "  make stage2-queue    Papers eligible for Stage 2"
	@echo "  make stage2-screen   Run Stage 2 full-text screening"
	@echo "  make progression      Paper flow through all stages"
	@echo ""
	@echo "=== Enhanced Screening (Option B) ==="
	@echo "  make keyword-filter   Filter papers using keyword pre-screening"
	@echo "  make al-select        Select papers for active learning review"
	@echo "  make fine-tune        Fine-tune SciBERT with labeled samples"
	@echo "  make snowballing      Run snowballing on included papers"
	@echo "  make certainty        Apply certainty-based auto decisions"
	@echo "  make cite-rank        Rank papers by citation count"
	@echo "  make enhanced-full    Run full enhanced screening pipeline"
	@echo ""
	@echo "=== PRISMA 2020 ==="
	@echo "  make checklist       Get PRISMA checklist"
	@echo "  make prisma-flow     PRISMA flow diagram"
	@echo "  make prisma-report   Full PRISMA 2020 report"
	@echo ""
	@echo "=== Direct API Access ==="
	@echo "  Local:  curl http://localhost:$(API_PORT)/"
	@echo "  Docker: curl http://$(API_HOST):$(API_PORT)/"
	@echo "  Docs:   http://localhost:$(API_PORT)/docs"

python-upgrade:
	@echo "Checking Python version..."
	@python3 --version 2>&1 | grep -q "3.12" && echo "Python 3.12 already installed" || ( \
		echo "Upgrading Python to 3.12..."; \
		sudo apt-get update && sudo apt-get install -y software-properties-common; \
		sudo add-apt-repository -y ppa:deadsnakes/ppa; \
		sudo apt-get update && sudo apt-get install -y python3.12 python3.12-venv python3.12-dev; \
		echo "Python 3.12 installed. Run: make install" \
	)

install:
	python3 --version 2>&1 | grep -q "3.1[0-9]" || (echo "Warning: Python 3.10+ recommended"; exit 0)
	pip3 install -r requirements.txt || python3 -m pip install -r requirements.txt || echo "Warning: Some dependencies not installed"

install-gpu:
	@echo "Installing PyTorch with CUDA support..."
	pip3 install torch torchvision --index-url https://download.pytorch.org/whl/cu121
	pip3 install transformers huggingface-hub ctranslate2

convert:
	@echo "Downloading SciBERT model for local use..."
	pip3 install torch --break-system-packages 2>/dev/null || \
	python3 -m pip install torch --break-system-packages || \
	echo "Warning: PyTorch not installed (needed for model conversion)"
	pip3 install transformers huggingface-hub --break-system-packages 2>/dev/null || \
	python3 -m pip install transformers huggingface-hub || \
	echo "Warning: Could not install all dependencies"
	@echo "Downloading SciBERT model..."
	python3 scripts/convert_model.py --model allenai/scibert_scivocab_uncased --output ./models/scibert

convert-download:
	python3 scripts/convert_model.py --model allenai/scibert_scivocab_uncased --output ./models/scibert

build:
	docker compose build

build-gpu:
	docker compose build --build-arg GPU_ENABLED=true

build-api:
	docker compose build api

build-ml:
	docker compose build ml-worker

build-all:
	docker compose build

rebuild:
	@echo "=== Rebuilding services with latest code ==="
	@echo "1. Pulling latest changes..."
	@git pull origin main || echo "Git pull skipped (not a git repo or no remote)"
	@echo ""
	@echo "2. Building API container..."
	@docker compose build api
	@echo ""
	@echo "3. Building ML worker container..."
	@docker compose build ml-worker
	@echo ""
	@echo "4. Restarting services..."
	@docker compose up -d api ml-worker
	@echo ""
	@echo "=== Rebuild complete ==="

up:
	docker compose up -d
	@echo "Waiting for services to be ready..."
	@sleep 5
	@curl -s $(API_URL)/health || echo "API not ready yet"

up-gpu:
	docker compose up -d
	@echo "GPU mode enabled - checking CUDA availability..."
	@docker exec $$(docker compose ps -q api) python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')" 2>/dev/null || echo "CUDA check skipped"

down:
	docker compose down

logs:
	docker compose logs -f

logs-api:
	docker compose logs -f api

logs-ml:
	docker compose logs -f ml-worker

clean:
	docker compose down -v
	rm -rf outputs/*

run-api:
	uvicorn src.api.main:app --reload --port 8000

test-classifier:
	python3 -c "from src.ml.classifier import SciBERTClassifier, BackendType; c = SciBERTClassifier(backend='pytorch'); print('OK')"

status:
	@echo "=== Docker Services ==="
	@docker compose ps
	@echo ""
	@echo "=== API Health (via Docker hostname) ==="
	@docker compose exec -T api curl -s http://localhost:8000/health 2>/dev/null | python3 -m json.tool 2>/dev/null || echo "API not reachable via Docker"
	@echo ""
	@echo "=== Local API Health ==="
	@curl -s http://localhost:8000/health 2>/dev/null | python3 -m json.tool 2>/dev/null || echo "API not running locally"

# API Testing commands (executed from within Docker)
health:
	@echo "Checking API health..."
	@curl -s $(API_URL)/health 2>/dev/null | python3 -m json.tool || echo "API not reachable"

verify-api:
	@echo "Verifying API accessibility..."
	@curl -s --connect-timeout 2 $(API_URL)/health >/dev/null && echo "✅ API is accessible at $(API_URL)" || (echo "❌ API not responding at $(API_URL)"; exit 1)

import-sample:
	@echo "Importing sample papers from inputs/ directory..."
	@curl -s -X POST $(API_URL)/papers/import-directory \
		-H "Content-Type: application/json" \
		-d '{"directory": "inputs", "auto_detect": true}' | python3 -m json.tool

screen:
	@echo "Running ML screening with confidence calibration..."
	@curl -s -X POST $(API_URL)/screening/run \
		-H "Content-Type: application/json" \
		-d '{"threshold": 0.5}' | python3 -m json.tool

queue:
	@echo "Papers requiring manual review (uncertain/low confidence)..."
	@curl -s "$(API_URL)/screening/queue/uncertain?limit=20" \
		| python3 -m json.tool

stats:
	@echo "Screening statistics for PRISMA reporting..."
	@curl -s $(API_URL)/screening/statistics \
		| python3 -m json.tool

rank:
	@echo "Top papers by relevance..."
	@curl -s "$(API_URL)/screening/rank?n=20&sort_by=relevance" \
		| python3 -m json.tool

prisma-flow:
	@echo "PRISMA flow diagram data..."
	@curl -s $(API_URL)/prisma/flow \
		| python3 -m json.tool

smoke-test:
	@echo "=== Running API Smoke Test ==="
	@echo ""
	@echo "1. Health check..."
	@curl -s $(API_URL)/health | grep -q '"status".*"healthy"' && echo "✅ Health OK" || (echo "❌ Health check failed"; exit 1)
	@echo ""
	@echo "2. Config status..."
	@curl -s $(API_URL)/config/status | grep -q '"loaded".*true' && echo "✅ Config OK" || (echo "❌ Config check failed"; exit 1)
	@echo ""
	@echo "3. Paper import..."
	@curl -s -X POST $(API_URL)/papers/import -H "Content-Type: application/json" -d '{"source":"acm","file_path":"inputs/acm.bib"}' | grep -q '"status".*"imported"' && echo "✅ Import OK" || (echo "❌ Import failed"; exit 1)
	@echo ""
	@echo "4. Screening..."
	@curl -s -X POST $(API_URL)/screening/run | grep -q '"status".*"screening_complete"' && echo "✅ Screening OK" || (echo "❌ Screening failed"; exit 1)
	@echo ""
	@echo "5. PRISMA flow..."
	@curl -s $(API_URL)/prisma/flow | grep -q 'total_screened' && echo "✅ PRISMA Flow OK" || (echo "❌ PRISMA flow failed"; exit 1)
	@echo ""
	@echo "6. Extraction..."
	@curl -s -X POST $(API_URL)/prisma/extract | grep -q '"status".*"extracted"' && echo "✅ Extraction OK" || (echo "❌ Extraction failed"; exit 1)
	@echo ""
	@echo "7. Synthesis..."
	@curl -s $(API_URL)/prisma/synthesis | grep -q '"overview"' && echo "✅ Synthesis OK" || (echo "❌ Synthesis failed"; exit 1)
	@echo ""
	@echo "=== ✅ All smoke tests passed ==="

# Code quality
lint:
	@echo "Running black formatter check..."
	@python3 -m black --check src/ 2>/dev/null || echo "Install black: pip install black"
	@echo "Running isort check..."
	@python3 -m isort --check src/ 2>/dev/null || echo "Install isort: pip install isort"

typecheck:
	@echo "Running mypy type checker..."
	@python3 -m mypy src/ 2>/dev/null || echo "Install mypy: pip install mypy"

# Test commands (run from host)
test:
	@echo "Running unit tests..."
	@pytest -v tests/ --ignore=tests/test_integration.py

test-integration:
	@echo "Running integration tests against API..."
	@pytest -v tests/test_integration.py -k "test_"

test-all:
	@echo "Running all tests (unit + integration)..."
	@pytest -v tests/

test-watch:
	@pytest -v tests/ --ignore=tests/test_integration.py --watch 2>/dev/null || pytest -v tests/ --ignore=tests/test_integration.py

coverage:
	@pytest --cov=src --cov-report=html --cov-report=term tests/ --ignore=tests/test_integration.py

# Development helpers
enter-api:
	docker compose exec api /bin/bash

enter-ml:
	docker compose exec ml-worker /bin/bash

# Quick workflow for screening
screening-workflow:
	@echo "=== ML-Assisted Screening Workflow ==="
	@echo ""
	@echo "Step 1: Import papers"
	@make import-sample
	@echo ""
	@echo "Step 2: Run screening"
	@make screen
	@echo ""
	@echo "Step 3: Review uncertain papers"
	@make queue
	@echo ""
	@echo "Step 4: Get statistics"
	@make stats

# Data Source Download Commands
sources:
	@echo "Configured data sources from data_sources.yaml..."
	@curl -s $(API_URL)/papers/sources \
		| python3 -m json.tool

download-all:
	@echo "Downloading all configured source files..."
	@curl -s -X POST $(API_URL)/papers/download-all \
		| python3 -m json.tool

download-source:
	@read -p "Enter source name (wos/ieee/acm/scopus/pubmed): " source; \
	curl -s -X POST "$(API_URL)/papers/download-all" \
		-H "Content-Type: application/json" \
		-d "{\"sources\": [\"$$source\"]}" | python3 -m json.tool

import-downloaded:
	@echo "Importing downloaded files..."
	@curl -s -X POST "$(API_URL)/papers/import-downloaded?directory=inputs" \
		| python3 -m json.tool

download-and-import:
	@echo "Downloading sources and importing papers..."
	@make download-all
	@echo ""
	@echo "Importing downloaded files..."
	@make import-downloaded

# Phase 3: Two-Stage Screening Workflow
ft-retrievable:
	@echo "Papers eligible for full-text retrieval..."
	@curl -s $(API_URL)/papers/retrievable \
		| python3 -m json.tool

ft-flagged:
	@echo "Papers flagged for no DOI (excluded from Stage 2)..."
	@curl -s $(API_URL)/papers/flagged \
		| python3 -m json.tool

ft-progress:
	@echo "Full-text retrieval progress..."
	@curl -s $(API_URL)/papers/progress/fulltext \
		| python3 -m json.tool

stage2-queue:
	@echo "Papers eligible for Stage 2 (full-text) screening..."
	@curl -s "$(API_URL)/screening/queue/stage2?limit=20" \
		| python3 -m json.tool

stage2-screen:
	@echo "Running Stage 2 full-text screening..."
	@curl -s -X POST $(API_URL)/screening/stage2 \
		-H "Content-Type: application/json" \
		-d '{"threshold": 0.5}' | python3 -m json.tool

progression:
	@echo "Paper progression through screening stages..."
	@curl -s $(API_URL)/screening/progression \
		| python3 -m json.tool

# PRISMA 2020 commands
checklist:
	@echo "PRISMA 2020 Checklist..."
	@curl -s $(API_URL)/prisma/checklist \
		| python3 -m json.tool | head -50

prisma-report:
	@echo "Generating full PRISMA 2020 report..."
	@curl -s -X POST "$(API_URL)/prisma/report/full?format=markdown" \
		| python3 -m json.tool

# Complete two-stage workflow
two-stage-workflow:
	@echo "=== Two-Stage Screening Workflow ==="
	@echo ""
	@echo "Stage 1: Title/Abstract Screening"
	@make screen
	@echo ""
	@echo "Stage 1: Get retrievable papers"
	@make ft-retrievable
	@echo ""
	@echo "Stage 1: Get flagged papers"
	@make ft-flagged
	@echo ""
	@echo "Stage 1: Get progress"
	@make ft-progress
	@echo ""
	@echo "Stage 2: Get eligible papers"
	@make stage2-queue
	@echo ""
	@echo "Overall: Paper progression"
	@make progression

# === Enhanced Screening Commands (Option B) ===

keyword-filter:
	@echo "Running keyword-based pre-filtering..."
	@curl -s -X POST $(API_URL)/enhanced/filter/keywords \
		-H "Content-Type: application/json" \
		-d '{"papers": [], "keywords_config": {"keywords": {"required": ["blockchain", "maDMP", "data management plan", "provenance"], "relevant": ["FAIR", "metadata", "smart contract", "IPFS"], "exclusion": ["supply chain", "finance", "opinion paper"]}}}' \
		| python3 -m json.tool

al-select:
	@echo "Selecting papers for active learning review..."
	@curl -s -X POST $(API_URL)/enhanced/active-learning \
		-H "Content-Type: application/json" \
		-d '{"papers": [], "config": {"initial_training_size": 50, "batch_size": 20}}' \
		| python3 -m json.tool

fine-tune:
	@echo "Fine-tuning SciBERT (requires labeled samples)..."
	@echo "Use /enhanced/fine-tune endpoint with labeled texts and labels arrays"
	@curl -s -X POST $(API_URL)/enhanced/fine-tune \
		-H "Content-Type: application/json" \
		-d '{"texts": ["sample text 1", "sample text 2"], "labels": [1, 0]}' \
		| python3 -m json.tool

snowballing:
	@echo "Running snowballing on included papers..."
	@curl -s -X POST $(API_URL)/enhanced/snowballing \
		-H "Content-Type: application/json" \
		-d '{"papers": [], "config": {"max_depth": 2, "max_papers_per_source": 50}}' \
		| python3 -m json.tool

certainty:
	@echo "Applying certainty-based screening decisions..."
	@curl -s -X POST $(API_URL)/enhanced/certainty-screening \
		-H "Content-Type: application/json" \
		-d '{"results": [], "exclude_confidence": 0.80, "include_confidence": 0.80}' \
		| python3 -m json.tool

cite-rank:
	@echo "Ranking papers by citation count..."
	@curl -s -X POST $(API_URL)/enhanced/rank/citations \
		-H "Content-Type: application/json" \
		-d '{"papers": [], "n": 50, "min_citations": 0}' \
		| python3 -m json.tool

enhanced-full:
	@echo "Running full enhanced screening pipeline..."
	@curl -s -X POST $(API_URL)/enhanced/screening/full \
		-H "Content-Type: application/json" \
		-d '{"papers": [], "strategy": "full", "keywords_config": {"keywords": {"required": ["blockchain", "maDMP", "provenance"], "relevant": ["FAIR", "metadata"], "exclusion": ["supply chain"]}}}' \
		| python3 -m json.tool

# === Complete Enhanced Screening Workflow ===

enhanced-workflow:
	@echo "=== Enhanced Screening Workflow (Option B) ==="
	@echo ""
	@echo "Step 1: Import papers from sources"
	@make import-sample
	@echo ""
	@echo "Step 2: Keyword pre-filtering"
	@make keyword-filter
	@echo ""
	@echo "Step 3: Run initial ML screening"
	@make screen
	@echo ""
	@echo "Step 4: Apply certainty-based decisions"
	@make certainty
	@echo ""
	@echo "Step 5: Rank by citations"
	@make cite-rank
	@echo ""
	@echo "Step 6: Get screening statistics"
	@make stats
