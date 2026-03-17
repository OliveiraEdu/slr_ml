FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install ctranslate2 for fast BERT inference
RUN pip install --no-cache-dir ctranslate2

# Install transformers for tokenizer
RUN pip install --no-cache-dir transformers huggingface-hub

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY config/ ./config/
COPY scripts/ ./scripts/
COPY models/ ./models/

ENV PYTHONUNBUFFERED=1
ENV TRANSFORMERS_CACHE=/app/models

# Build with: docker build -f Dockerfile.ml -t slr-ml .
# Run with converted model in ./models/
# Ensure the script is copied (it should be covered by your COPY scripts/ ./scripts/ line)
CMD ["python", "scripts/worker_node.py"]