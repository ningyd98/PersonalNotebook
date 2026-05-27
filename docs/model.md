# 模型服务文档

## Model Gateway 架构

独立于业务后端的模型网关，统一封装 LLM / Embedding / Rerank API。

```
业务后端 → model-gateway → Ollama / vLLM / OpenAI
```

## Provider 配置

### Ollama

```bash
# 安装
curl -fsSL https://ollama.com/install.sh | sh

# 拉取模型
ollama pull qwen3:8b
ollama pull bge-m3
ollama pull qwen3-reranker-0.6b

# 默认地址
OLLAMA_BASE_URL=http://localhost:11434
```

### vLLM

```bash
# 环境变量
VLLM_BASE_URL=http://localhost:8000/v1
```

### OpenAI-compatible

```bash
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_API_KEY=sk-xxxx
```

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /model/chat | LLM 对话生成 |
| POST | /model/embed | 文本向量化 |
| POST | /model/rerank | 文档重排序 |
| GET | /model/status | 服务状态 |

## 推荐模型

| 用途 | 模型 | 维度 |
|------|------|------|
| LLM | Qwen3-8B-Instruct | — |
| LLM | Qwen3-14B-Instruct | — |
| Embedding | bge-m3 | 1024 |
| Embedding | Qwen3-Embedding-0.6B | 1024 |
| Rerank | Qwen3-Reranker-0.6B | — |
| Rerank | bge-reranker-v2-m3 | — |

## 模型切换

通过环境变量或知识库设置切换模型：

```
DEFAULT_LLM=qwen3:14b
DEFAULT_EMBEDDING=qwen3-embedding-4b
DEFAULT_RERANK=qwen3-reranker-0.6b
```
