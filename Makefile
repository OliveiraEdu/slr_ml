.PHONY: help install convert build build-api build-ml up down logs clean python-upgrade

help:
	@echo "PRISMA 2020 SLR Engine - Make Commands"
	@echo ""
	@echo "=== Development ==="
	@echo "  make python-upgrade  Upgrade Python to 3.12 (required)"
	@echo "  make install        Install dependencies locally"
	@echo "  make convert       Download and convert SciBERT model for ctranslate2"
	@echo "  make run-api       Run API locally (for development)"
	@echo ""
	@echo "=== Docker Deployment ==="
	@echo "  make build         Build all Docker containers (CPU)"
	@echo "  make build-gpu     Build containers with GPU support"
	@echo "  make build-api     Build only API container"
	@echo "  make build-ml      Build only ML worker container"
	@echo "  make up            Start all services"
	@echo "  make down          Stop all services"
	@echo "  make logs          View logs (all services)"
	@echo "  make logs-api      View API logs"
	@echo "  make logs-ml       View ML worker logs"
	@echo "  make clean         Clean up containers and volumes"
	@echo ""
	@echo "=== Testing ==="
	@echo "  make test          Run pytest"
	@echo "  make test-classifier Test SciBERT classifier"

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
	@echo "Installing dependencies for model conversion..."
	pip3 install transformers huggingface-hub ctranslate2 2>/dev/null || \
	python3 -m pip install transformers huggingface-hub ctranslate2 || \
	echo "Warning: Could not install all dependencies"
	@echo "Converting SciBERT model..."
	python3 scripts/convert_model.py --model allenai/scibert_scivocab_uncased --output ./models/scibert-ct2

convert-download:
	python3 scripts/convert_model.py --model allenai/scibert_scivocab_uncased --download-only

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

test:
	pytest -v

test-classifier:
	python3 -c "from src.ml.classifier import SciBERTClassifier, BackendType; c = SciBERTClassifier(backend='pytorch'); print('OK')"

status:
	@echo "=== Docker Services ==="
	@docker compose ps
	@echo ""
	@echo "=== API Health ==="
	@curl -s http://localhost:8000/health | python3 -m json.tool 2>/dev/null || echo "API not running"
