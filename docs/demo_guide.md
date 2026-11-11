# Demo guide (Windows)

## One-command start

```bat
cd C:\Project\ai-inquiry-processing-agent
scripts\start-demo.bat
```

Defaults:

| Variable | Default |
|---|---|
| `AI_PROVIDER` | `ollama` |
| `OLLAMA_MODEL` | `qwen3:4b` |
| `NEXT_PUBLIC_API_BASE` | `http://127.0.0.1:8000` |

```bat
set AI_PROVIDER=mock && scripts\start-demo.bat
scripts\seed-and-start.bat
scripts\stop-demo.bat
```

UI: http://127.0.0.1:3000 — API docs: http://127.0.0.1:8000/docs

## Backend (manual)

```powershell
cd C:\Project\ai-inquiry-processing-agent
.\.venv\Scripts\Activate.ps1
$env:AI_PROVIDER="ollama"
$env:OLLAMA_MODEL="qwen3:4b"
python scripts\generate_sample_data.py
cd backend
alembic upgrade head
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Optional seed:

```powershell
.\.venv\Scripts\python.exe scripts\seed_demo.py
```

## Frontend (manual)

```powershell
cd C:\Project\ai-inquiry-processing-agent\frontend
npm install
$env:NEXT_PUBLIC_API_BASE="http://127.0.0.1:8000"
npm run dev
```

## Suggested click path

1. Dashboard → open a seeded inquiry (or New Inquiry)
2. Check the AI mode badge (local LLM vs mock)
3. Read decision summary, registration snapshot, tool / RAG viewers
4. Approve decision when prompted
5. Review email draft → approve → mock send → completed
6. Optional: Evaluations → run synthetic cases

Shorter version: [demo.md](./demo.md). Ollama notes: [ollama_runtime.md](./ollama_runtime.md).

## Mock vs real

| Capability | Demo default |
|---|---|
| AI analysis | Ollama locally; `mock` for CI |
| Tool results / RAG | Real local execution / retrieval |
| LDAP / GAC | Sample Excel + mock providers |
| Teams / email send | Mock |
