# 智慧校园消息管理系统 🚀

> 面向智慧校园场景的大语言模型（LLM）全流程解决方案，覆盖数据采集、模型轻量化微调、高性能推理、Web 交互与服务部署全链路，为智慧校园提供问答、总结、内容生成等智能化能力。

## 快速开始

### 1. 环境准备

```bash
# 安装依赖
pip install -r requirements.txt

# 配置本地环境变量（模型路径、API密钥等）
bash set_local_env.sh
```

### 2. 启动服务

```bash
# 一键启动全流程服务（模型推理+API+前端）
bash start.sh
```

## 核心模块

| 模块 / 目录 | 核心能力 |
|------|------|
| **lora/** | LLM 轻量化微调（LoRA）、模型训练、Qwen2.5-7B 适配 |
| **grab_news/** | 智慧校园新闻/通知爬取，为模型提供场景化语料 |
| **nlp/** | LLM 客户端封装、校园场景 Prompt 模板、NLP 通用工具 |
| **services/** | RAG 检索增强、差异化总结生成、后端业务逻辑 |
| **web/** | 可视化 Web 交互界面（问答/新闻查询/身份切换） |
| **scripts/** | 数据集构建、定时任务调度、全链路测试 |
| **api.py** | 后端 API 接口层，对外暴露 LLM 推理、新闻查询等核心能力 |

## 技术栈

- **基座模型**：Qwen2.5-7B-Instruct
- **微调方法**：LoRA (r=8, alpha=32, dropout=0.1)
- **训练框架**：PyTorch + Transformers + bfloat16 混合精度
- **后端**：Python + FastAPI
- **数据存储**：JSONL 格式化记忆库

## 配置说明

详细配置指南请参考 [CONFIG_GUIDE.md](CONFIG_GUIDE.md)
