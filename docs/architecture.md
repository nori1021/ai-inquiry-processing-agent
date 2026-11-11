# Architecture

## Idea

Keep **lookups and safety rules in Python**, and use the LLM mainly for understanding the ticket and suggesting what to check next.

- Web tools are allowlisted REST-style calls only (no browser automation).
- Default AI is local Ollama (`qwen3:4b`, fallback `qwen3:1.7b`). CI uses `AI_PROVIDER=mock`.
- One inference at a time. Context 4096, temperature 0.1.

```
┌─────────────┐   HTTP    ┌─────────────────────────────────────────┐
│  Next.js UI │──────────▶│  FastAPI                                │
│             │           │  /lookup /tools /inquiry/analyze        │
│             │           │  /workflows                             │
└─────────────┘           └──────────────┬──────────────────────────┘
                                         │
                    ┌────────────────────┼────────────────────┐
                    ▼                    ▼                    ▼
            Ollama or mock          Tool Registry        Python gates
            structured JSON         LDAP/GAC + REST      confidence /
                                    allowlisted only     conflicts
```

The UI shows whether the last run used a real local model or the mock path. Tool / RAG panels only show data that was actually executed or retrieved.

## Backend layout

| Area | Role |
|---|---|
| `api/` | HTTP routes |
| `agents/` | Inquiry analysis, planner, tool selection |
| `registry/` | Tool catalog + executor |
| `tools/` | Deterministic Excel lookups |
| `services/` | Validation, RAG helpers |
| `providers/` | Ollama / mock AI / web / PowerShell / approval / email |
| `workflow/` | Persistent state machine |
| `models/` / `schemas/` | ORM + Pydantic |
| `database/` | Engine, sessions, Alembic |
| `config/` | Settings from env |

## Lookup results

| Result | Meaning |
|---|---|
| Found | Excel readable and email/company matched |
| `NOT_REGISTERED` | Excel readable; no matching row |
| `UNKNOWN` | File missing / unreadable — do **not** treat as “not registered” |

## Persistence

- SQLite via `DATABASE_URL` (default under `data/app.db`)
- Schema changes go through Alembic
- Sample LDAP/GAC data stays in Excel for the demo; interfaces leave room to swap later

## Out of scope for this demo

- Production Microsoft Graph send
- Real Teams tenant wiring as the only path
- Browser automation
- Loading several large models at once

See also: [tool_registry.md](./tool_registry.md), [demo.md](./demo.md), [ollama_runtime.md](./ollama_runtime.md).
