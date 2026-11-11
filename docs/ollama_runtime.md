# Ollama Runtime (Supported Default)

## Environment

- Windows PC, ~8GB RAM, NVIDIA GPU
- No dedicated cloud server; no paid API required for MVP

## Models

| Role | Model |
|---|---|
| Primary | `qwen3:4b` |
| Fallback | `qwen3:1.7b` |

## Settings (`.env`)

```
AI_PROVIDER=ollama
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen3:4b
OLLAMA_FALLBACK_MODEL=qwen3:1.7b
OLLAMA_TEMPERATURE=0.1
OLLAMA_NUM_CTX=4096
```

For CI / machines without Ollama:

```
AI_PROVIDER=mock
```

## Constraints enforced in code

1. Process-wide `asyncio.Lock` — only one Ollama inference at a time.
2. On primary failure, fallback model runs under the **same** lock (no parallel load race).
3. If Ollama is unreachable, automatic mock heuristic fallback (tests/CI safe).
4. Structured JSON (`format: json`) validated by Pydantic.
5. Unregistered tool names suggested by the model are dropped.
6. Limited RAG top-k only — never full inquiry history in context.
7. Logs inference latency, best-effort memory, and tool-selection accuracy.

## Setup notes

```powershell
ollama pull qwen3:4b
ollama pull qwen3:1.7b
ollama serve
```
