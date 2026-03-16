FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu

RUN pip install --no-cache-dir \
    transformers \
    huggingface-hub \
    accelerate \
    sentencepiece \
    protobuf \
    tokenizers

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY config/ ./config/

ENV PYTHONUNBUFFERED=1
ENV TRANSFORMERS_CACHE=/app/models

CMD ["python", "-c", "from src.ml.classifier import SciBERTClassifier; c = SciBERTClassifier(); print('SciBERT ready')"]
