# How I walk through the app

Short checklist I use when showing the project locally.

## Start

```bat
scripts\seed-and-start.bat
```

Or with mock AI (no Ollama):

```bat
set AI_PROVIDER=mock && scripts\seed-and-start.bat
```

Open http://127.0.0.1:3000

## Walkthrough

1. **Dashboard** — pending decision / email approvals and the inquiry list.
2. **Open a seeded inquiry** (or create one under New Inquiry).
3. **Inquiry detail** — category, who to investigate, tool runs, and any RAG snippets.
4. **Approve the decision** when the UI asks for operator judgment.
5. **Review the email draft** — edit if needed (editing clears email approval).
6. **Approve email** — mock provider marks it sent and the workflow completes.
7. Optional: **Evaluations** page to run a few synthetic cases.

## Useful sample

Subject: `Demo: GAC registration check`  
Body that mentions `frank@acme.com` (investigate) and `grace@globex.com` on CC (usually not investigated).

## If something fails

| Symptom | What I check |
|---|---|
| Badge says mock / fallback | `ollama serve`, `ollama pull qwen3:4b`, restart backend with `AI_PROVIDER=ollama` |
| Empty list | `python scripts\seed_demo.py` |
| API down | `uvicorn app.main:app --reload --host 127.0.0.1 --port 8000` |
| Ports stuck | `scripts\stop-demo.bat` |

More setup detail: [demo_guide.md](./demo_guide.md), [ollama_runtime.md](./ollama_runtime.md).
