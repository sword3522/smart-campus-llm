# LLM 配置切换指南

本项目支持两种 LLM 调用方式：
1. **本地微调模型**：使用本地微调好的 LoRA 模型
2. **远程 API**：使用阿里云通义千问等在线服务

## 快速切换

### 方式一：使用脚本切换（推荐）

#### 切换到本地模型
```bash
source set_local_env.sh
```

#### 切换到远程 API
```bash
source set_remote_env.sh
```

**注意**：必须使用 `source` 命令（或 `.` 命令），否则环境变量不会生效到当前 shell。

### 方式二：手动设置环境变量

#### 使用本地模型
```bash
export LLM_PROVIDER=local
export LOCAL_MODEL_PATH=/root/autodl-tmp/qwen/Qwen2.5-7B-Instruct/
export LOCAL_LORA_PATH=/root/NLP/lora/output/Qwen2.5_smart_campus/checkpoint-237
unset LLM_API_KEY
unset LLM_API_BASE
unset LLM_MODEL
```

#### 使用远程 API
```bash
export LLM_PROVIDER=openai
export LLM_API_KEY=sk-a91d2da7aeaa4b34abaf6e58d6586d7b
export LLM_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1
export LLM_MODEL=qwen-plus
```

## 验证配置

运行以下命令查看当前配置：
```bash
echo "Provider: $LLM_PROVIDER"
echo "Local Model: $LOCAL_MODEL_PATH"
echo "Local LoRA: $LOCAL_LORA_PATH"
echo "API Base: $LLM_API_BASE"
echo "Model: $LLM_MODEL"
```

## 测试配置

### 测试本地模型
```bash
# 1. 切换到本地模型
source set_local_env.sh

# 2. 运行每日任务测试
python main.py daily-job

# 3. 或者测试问答
python main.py ask "最近有什么竞赛？"
```

### 测试远程 API
```bash
# 1. 切换到远程 API
source set_remote_env.sh

# 2. 运行相同的测试
python main.py daily-job
```

## 依赖检查

### 本地模型所需依赖
使用本地模型需要安装以下包：
```bash
pip install torch transformers peft accelerate
```

检查是否已安装：
```python
python -c "import torch; import transformers; import peft; print('✓ 依赖已安装')"
```

### 远程 API 所需依赖
远程 API 只需要基本的 HTTP 请求库（已内置）。

## 配置文件说明

相关配置文件：
- `nlp/config.py`: 配置类定义，从环境变量读取配置
- `nlp/llm_client.py`: LLM 客户端实现，支持多种 provider
- `set_local_env.sh`: 快速切换到本地模型的脚本
- `set_remote_env.sh`: 快速切换到远程 API 的脚本

## 本地模型路径配置

如果你的模型路径不同，修改以下文件：
- 编辑 `set_local_env.sh`
- 或修改 `nlp/config.py` 中的默认路径

当前配置的路径：
- **基座模型**: `/root/autodl-tmp/qwen/Qwen2.5-7B-Instruct/`
- **LoRA 权重**: `/root/NLP/lora/output/Qwen2.5_smart_campus/checkpoint-237`

## 常见问题

### Q: 切换后还是调用了错误的模型？
A: 确保使用 `source` 命令运行脚本，而不是直接 `./set_local_env.sh`

### Q: 本地模型加载失败？
A: 检查：
1. 模型路径是否正确
2. 是否安装了 torch, transformers, peft
3. GPU 内存是否足够

### Q: 如何永久设置？
A: 将环境变量添加到 `~/.bashrc` 或 `~/.zshrc`：
```bash
echo 'export LLM_PROVIDER=local' >> ~/.bashrc
source ~/.bashrc
```

## 性能对比

| 方式 | 优点 | 缺点 |
|------|------|------|
| 本地模型 | 无需网络，数据私密，可定制 | 需要 GPU，加载时间长 |
| 远程 API | 即开即用，无需硬件 | 需要网络，有费用，延迟 |

根据你的使用场景选择合适的配置方式。
