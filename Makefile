.PHONY: help install convert build up down logs clean

help:
	@echo "PRISMA 2020 SLR Engine - Make Commands"
	@echo ""
	@echo "  make install    Install dependencies (host machine)"
	@echo "  make convert    Download and convert SciBERT model"
	@echo "  make build      Build Docker containers"
	@echo "  make up        Start all services"
	@echo "  make down      Stop all services"
	@echo "  make logs      View logs"
	@echo "  make clean     Clean up containers and volumes"

install:
	# Install Python dependencies
	pip install -r requirements.txt
	# Install ML dependencies (optional)
	pip install torch transformers ctranslate2

convert:
	# Run on HOST machine to download/convert SciBERT model
	python scripts/convert_model.py --model allenai/scibert_scivocab_uncased --output ./models/scibert-ct2

convert-download:
	# Just download model without conversion
	python scripts/convert_model.py --model allenai/scibert_scivocab_uncased --download-only

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
	# Keep models/ directory

# Run API locally (without Docker)
run-api:
	uvicorn src.api.main:app --reload --port 8000

# Run classifier test
test-classifier:
	python -c "
from src.ml.classifier import SciBERTClassifier, BackendType

# Test with PyTorch backend
c = SciBERTClassifier(backend='pytorch')
print('PyTorch backend: OK')

# Test ctranslate2 (requires converted model)
try:
    c2 = SciBERTClassifier(backend='ctranslate2')
    print('ctranslate2 backend: OK')
except FileNotFoundError:
    print('ctranslate2: Model not found. Run: make convert')
"
