# Project layout

```
ai-inquiry-processing-agent/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   ├── agents/            # inquiry analysis / planner / tool selection
│   │   ├── tools/             # Excel LDAP/GAC helpers
│   │   ├── registry/          # tool catalog + executor
│   │   ├── workflow/          # state machine + repository
│   │   ├── services/
│   │   ├── providers/         # Ollama / mock AI / approval / web / PowerShell
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── database/
│   │   └── config/
│   ├── alembic/
│   ├── tests/
│   └── requirements.txt
├── frontend/                  # Next.js UI
├── data/sample/               # sample Excel
├── templates/replies/
├── demo/                      # screenshots (+ local video, gitignored)
├── evaluations/
├── docs/
├── scripts/
├── .env.example
├── .gitignore
├── README.md
└── docker-compose.yml
```
