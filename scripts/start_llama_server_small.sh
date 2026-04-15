#!/bin/bash
# Start llama-server with smaller Qwen2.5-1.5B model

cd /home/eduardo/Git/llama.cpp

CUDA_DEVICE_WAITS_ON_EXTERNAL_RESOURCE=1 GGML_CUDA_NO_VHM=1 ./bin/llama-server \
  -m models/qwen2.5-1.5b-instruct-q4_k_m.gguf \
  --host 0.0.0.0 \
  --port 8080 \
  --ctx-size 8192 \
  --n-gpu-layers 99 \
  --parallel 4 \
  --flash-attn \
  --threads $(nproc) \
  --cont-batching \
  --metrics
