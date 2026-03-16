.PHONY: help install convert build up down logs clean python-upgrade

help:
	@echo "PRISMA 2020 SLR Engine - Make Commands"
	@echo ""
	@echo "  make python-upgrade  Upgrade Python to 3.12 (required)"
	@echo "  make install       Install dependencies (after Python upgrade)"
	@echo "  make convert       Download and convert SciBERT model"
	@echo "  make build         Build Docker containers"
	@echo "  make up            Start all services"
	@echo "  make down          Stop all services"
	@echo "  make logs          View logs"
	@echo "  make clean         Clean up containers and volumes"

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
	pip3 install -r requirements.txt || python3 -m pip install -r requirements.txt
	pip3 install torch transformers ctranslate2 || python3 -m pip install torch transformers ctranslate2 || echo "Warning: ML dependencies not installed"

convert:
	python3 scripts/convert_model.py --model allenai/scibert_scivocab_uncased --output ./models/scibert-ct2

convert-download:
	python3 scripts/convert_model.py --model allenai/scibert_scivocab_uncased --download-only

build:
	docker-compose build

up:
	docker-compose up -d

down:
	docker-compose down

logs:
	docker-compose logs -f

clean:
	docker-compose down -v
	rm -rf outputs/*

run-api:
	uvicorn src.api.main:app --reload --port 8000

test-classifier:
	python3 -c "from src.ml.classifier import SciBERTClassifier, BackendType; c = SciBERTClassifier(backend='pytorch'); print('OK')"
