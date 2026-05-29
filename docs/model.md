# Model Configuration

PersonalNotebook supports two deployment modes for LLM generation.

## Hybrid Mode (DeepSeek API)

Retrieval and indexing run locally. Only evidence chunks are sent to DeepSeek API for answer generation.

```bash
MODEL_PROVIDER=deepseek
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
DEFAULT_LLM=qwen2.5:7b
DEFAULT_EMBEDDING=bge-m3
DEFAULT_RERANK=qwen3-reranker-0.6b
```

### Setup
```bash
ollama serve
ollama pull qwen2.5:7b
ollama pull bge-m3
ollama pull qwen3-reranker-0.6b
```

## OpenAI Compatible Mode

Works with any OpenAI-compatible endpoint.

```bash
MODEL_PROVIDER=openai_compatible
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_API_KEY=sk-xxxx
DEFAULT_LLM=gpt-4o-mini
```

## Switching Modes

1. Edit `.env` and set `MODEL_PROVIDER` to `deepseek`, `ollama`, or `openai_compatible`
2. Restart model-gateway: `uvicorn model-gateway.main:app --port 8900`
3. Flutter App Settings → API Key field (leave empty for Ollama)

## Flutter App Display

- Settings shows: "当前模式: Hybrid" or "当前模式: Local"
- API Key field: fill → Hybrid, empty → Local
