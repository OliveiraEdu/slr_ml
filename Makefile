.PHONY: help install convert build up down logs clean

help:
	@echo "PRISMA 2020 SLR Engine - Make Commands"
	@echo ""
	@echo "  make install    Install dependencies (host machine)"
	@echo "  make convert    Download and convert SciBERT model"
	@echo "  make build      Build Docker containers"
	@echo "  make up         Start all services"
	@echo "  make down       Stop all services"
	@echo "  make logs       View logs"
	@echo "  make clean      Clean up containers and volumes"

install:
	pip install -r requirements.txt
	pip install torch transformers ctranslate2

convert:
	python scripts/convert_model.py --model allenai/scibert_scivocab_uncased --output ./models/scibert-ct2

convert-download:
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

run-api:
	uvicorn src.api.main:app --reload --port 8000

test-classifier:
	python -c "from src.ml.classifier import SciBERTClassifier, BackendType; c = SciBERTClassifier(backend='pytorch'); print('OK')"
