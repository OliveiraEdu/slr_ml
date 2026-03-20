.PHONY: help install convert build build-api build-ml up down logs clean python-upgrade

# Docker hostnames for internal communication
API_HOST=api
ML_WORKER_HOST=ml-worker
API_PORT=8000
ML_WORKER_PORT=8001

help:
	@echo "PRISMA 2020 SLR Engine - Make Commands"
	@echo ""
	@echo "=== Docker Deployment ==="
	@echo "  make build         Build Docker containers (CPU PyTorch)"
	@echo "  make build-api     Build only API container"
	@echo "  make build-ml     Build only ML worker container"
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

up:
	docker compose up -d
	@echo "Waiting for services to be ready..."
	@sleep 5
	@curl -s http://localhost:8000/health || echo "API not ready yet"

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
	@curl -s http://localhost:8000/health 2>/dev/null | python3 -m json.tool || echo "API not reachable at localhost:8000"

import-sample:
	@echo "Importing sample papers from inputs/ directory..."
	@curl -s -X POST http://localhost:8000/papers/import-directory \
		-H "Content-Type: application/json" \
		-d '{"directory": "inputs", "auto_detect": true}' | python3 -m json.tool

screen:
	@echo "Running ML screening with confidence calibration..."
	@curl -s -X POST http://localhost:8000/screening/run \
		-H "Content-Type: application/json" \
		-d '{"threshold": 0.5}' | python3 -m json.tool

queue:
	@echo "Papers requiring manual review (uncertain/low confidence)..."
	@curl -s "http://localhost:8000/screening/queue/uncertain?limit=20" \
		| python3 -m json.tool

stats:
	@echo "Screening statistics for PRISMA reporting..."
	@curl -s http://localhost:8000/screening/statistics \
		| python3 -m json.tool

rank:
	@echo "Top papers by relevance..."
	@curl -s "http://localhost:8000/screening/rank?n=20&sort_by=relevance" \
		| python3 -m json.tool

prisma-flow:
	@echo "PRISMA flow diagram data..."
	@curl -s http://localhost:8000/prisma/flow \
		| python3 -m json.tool

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
	@curl -s http://localhost:8000/papers/sources \
		| python3 -m json.tool

download-all:
	@echo "Downloading all configured source files..."
	@curl -s -X POST http://localhost:8000/papers/download-all \
		| python3 -m json.tool

download-source:
	@read -p "Enter source name (wos/ieee/acm/scopus/pubmed): " source; \
	curl -s -X POST "http://localhost:8000/papers/download-all" \
		-H "Content-Type: application/json" \
		-d "{\"sources\": [\"$$source\"]}" | python3 -m json.tool

import-downloaded:
	@echo "Importing downloaded files..."
	@curl -s -X POST "http://localhost:8000/papers/import-downloaded?directory=inputs" \
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
	@curl -s http://localhost:8000/papers/retrievable \
		| python3 -m json.tool

ft-flagged:
	@echo "Papers flagged for no DOI (excluded from Stage 2)..."
	@curl -s http://localhost:8000/papers/flagged \
		| python3 -m json.tool

ft-progress:
	@echo "Full-text retrieval progress..."
	@curl -s http://localhost:8000/papers/progress/fulltext \
		| python3 -m json.tool

stage2-queue:
	@echo "Papers eligible for Stage 2 (full-text) screening..."
	@curl -s "http://localhost:8000/screening/queue/stage2?limit=20" \
		| python3 -m json.tool

stage2-screen:
	@echo "Running Stage 2 full-text screening..."
	@curl -s -X POST http://localhost:8000/screening/stage2 \
		-H "Content-Type: application/json" \
		-d '{"threshold": 0.5}' | python3 -m json.tool

progression:
	@echo "Paper progression through screening stages..."
	@curl -s http://localhost:8000/screening/progression \
		| python3 -m json.tool

# PRISMA 2020 commands
checklist:
	@echo "PRISMA 2020 Checklist..."
	@curl -s http://localhost:8000/prisma/checklist \
		| python3 -m json.tool | head -50

prisma-report:
	@echo "Generating full PRISMA 2020 report..."
	@curl -s -X POST "http://localhost:8000/prisma/report/full?format=markdown" \
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
