# Model Configuration

PersonalNotebook 支持四种模型部署模式。

## DashScope Mode (阿里云通义千问)

通过阿里云 DashScope API 调用通义千问系列模型。Chat/Embedding 走 OpenAI 兼容模式，Rerank 走 DashScope 专用 API。

```bash
MODEL_PROVIDER=dashscope
DASHSCOPE_API_KEY=sk-xxxx
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
DEFAULT_LLM=qwen-plus
DEFAULT_EMBEDDING=text-embedding-v3
DEFAULT_RERANK=gte-rerank
```

### 可用 DashScope 模型

| 模型 | 用途 | 说明 |
|------|------|------|
| `qwen-plus` | 默认 LLM — 高质量中文生成 | 128K |
| `qwen-turbo` | 快速响应，成本更低 | 128K |
| `qwen-max` | 最高质量，复杂推理 | 32K |
| `qwen3:8b` | 本地 Ollama + DashScope 混合 | — |
| `text-embedding-v3` | 文本嵌入 | 1024 维 |
| `gte-rerank` | 重排序 | — |

### DashScope Rerank 说明

DashScope 的 Rerank 使用专用 API 端点，不走 OpenAI 兼容模式：

```
POST https://dashscope.aliyuncs.com/api/v1/services/aigc/text-rerank/rerank
请求: {"model": "gte-rerank", "input": {"query": "...", "documents": [...]}}
响应: {"output": {"results": [{"index": 0, "relevance_score": 0.9}]}}
```

## Hybrid Mode (DeepSeek API)

Retrieval and indexing run locally. Only evidence chunks are sent to DeepSeek API for answer generation.

```bash
MODEL_PROVIDER=openai_compatible
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_API_KEY=sk-xxxx
DEFAULT_LLM=deepseek-v4-flash
DEFAULT_EMBEDDING=text-embedding-3-small
DEFAULT_RERANK=deepseek-v4-flash
```

### Available DeepSeek Models

| Model | Use | Context |
|-------|-----|---------|
| `deepseek-v4-flash` | Default — fast, cost-effective | 128K |
| `deepseek-v4-pro` | High quality, complex reasoning | 128K |

### Privacy Note
In Hybrid Mode, evidence chunks (document snippets matching your query) are sent to DeepSeek API. Full documents stay on your local Core. If you need complete data locality, use Local Mode.

## Local Mode (Ollama)

All processing runs locally. No data leaves your machine.

```bash
MODEL_PROVIDER=ollama
DEFAULT_LLM=qwen3:8b
DEFAULT_EMBEDDING=bge-m3
DEFAULT_RERANK=qwen3-reranker-0.6b
```

### Setup
```bash
ollama serve
ollama pull qwen3:8b
ollama pull bge-m3
ollama pull qwen3-reranker-0.6b
```

## vLLM Mode

使用 vLLM 自托管模型，适合 GPU 服务器部署。

```bash
MODEL_PROVIDER=vllm
VLLM_BASE_URL=http://localhost:8001
DEFAULT_LLM=qwen3:8b
```

## Switching Modes

1. Edit `.env` and set `MODEL_PROVIDER` to `dashscope`, `deepseek`, `ollama`, `openai_compatible`, or `vllm`
2. Restart model-gateway: `uvicorn model-gateway.main:app --port 8900`
3. Flutter App Settings → API Key field (leave empty for Ollama)

## Provider 优先级

Model Gateway 根据模型名和环境变量自动选择 provider：

1. 如果设置了 `MODEL_PROVIDER` 环境变量，优先使用指定 provider
2. `qwen*` / `gte-rerank*` 开头的模型 → DashScope
3. `gpt-*` / `o1*` / `o3*` / `deepseek*` 开头的模型 → OpenAI-compatible
4. 默认按优先级: DashScope > OpenAI-compatible > vLLM > Ollama

## Tokenize 端点

Model Gateway 提供 `/model/tokenize` 端点，用于计算文本的 token 数量。

```bash
curl -X POST http://localhost:8900/model/tokenize \
  -H "Content-Type: application/json" \
  -d '{"text": "需要计算token的文本", "model": ""}'
```

**响应：**

```json
{
  "token_count": 8,
  "model": "cl100k_base"
}
```

**用途：**
- 切片前预估文档 token 数量，优化 chunk 大小
- 检查 LLM 上下文窗口是否足够
- 估算 API 调用成本

**实现：** 使用 tiktoken `cl100k_base` 编码器；如不可用，回退到字符数 / 4 粗略估算。

## 推荐模型配置

| 场景 | LLM | Embedding | Rerank |
|------|-----|-----------|--------|
| 本地开发（8GB VRAM） | qwen3:8b (Ollama) | bge-m3 (Ollama) | qwen3-reranker-0.6b |
| 本地开发（16GB+ VRAM） | qwen3:14b (Ollama) | bge-m3 (Ollama) | qwen3-reranker-0.6b |
| 云端中文优化 | qwen-plus (DashScope) | text-embedding-v3 (DashScope) | gte-rerank (DashScope) |
| 云端成本优先 | qwen-turbo (DashScope) | text-embedding-v3 (DashScope) | gte-rerank (DashScope) |
| 云端英文 | deepseek-v4-flash | text-embedding-3-small | deepseek-v4-flash |

## Flutter App Display

- Settings shows: "当前模式: Hybrid" or "当前模式: Local"
- API Key field: fill → Hybrid, empty → Local
