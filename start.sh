#!/bin/bash
# 设置使用本地微调模型的环境变量

export LLM_PROVIDER=local
export LOCAL_MODEL_PATH=/root/autodl-tmp/qwen/Qwen2.5-7B-Instruct/
export LOCAL_LORA_PATH=/root/NLP/lora/output/Qwen2.5_smart_campus/checkpoint-237
export LLM_TEMPERATURE=0.2
export LLM_TIMEOUT_SECONDS=120
export LLM_MAX_RETRIES=5
export SEED=42

# 清除远程API配置
unset LLM_API_KEY
unset LLM_API_BASE
unset LLM_MODEL

echo "✓ 已切换到本地模型模式"
echo "  - Provider: $LLM_PROVIDER"
echo "  - Base Model: $LOCAL_MODEL_PATH"
echo "  - LoRA Path: $LOCAL_LORA_PATH"

echo "Starting main application..."
python main.py serve &

sleep 10

echo "Starting Cloudflare Tunnel..."
cd ~/autodl-tmp || { echo "Directory not found"; exit 1; }
./cloudflared-linux-amd64 tunnel --url http://localhost:8000