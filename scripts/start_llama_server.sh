#!/bin/bash
# Start llama-server for SLR screening
# Usage: ./start_llama_server.sh

cd /home/eduardo/Git/llama.cpp

CUDA_DEVICE_WAITS_ON_EXTERNAL_RESOURCE=1 GGML_CUDA_NO_VHM=1 ./bin/llama-server \
  -m ../models/Qwen3.5-4B-Q4_K_M.gguf \
  --host 0.0.0.0 \
  --port 9080 \
  --ctx-size 8192 \
  --n-gpu-layers 99 \
  --parallel 4 \
  --flash-attn \
  --threads $(nproc) \
  --cont-batching \
  --metrics \
  --slot-save-path /tmp/llama_slots/