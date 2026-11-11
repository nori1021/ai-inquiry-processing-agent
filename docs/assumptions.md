# Assumptions

A few choices I locked in while building the demo:

1. **Status values** use `FOUND`, `NOT_REGISTERED`, and `UNKNOWN` as string literals.
2. **Email normalization** = strip + lower-case the whole address.
3. **Domain normalization** = strip whitespace, optional leading `@`, lower-case.
4. **RapidFuzz metric** = `fuzz.ratio` (0–100). Default threshold `80` via `SIMILARITY_THRESHOLD`.
5. **Similar domains** exclude exact matches (exact match uses `get_company_by_domain`).
6. **CompanyID match** is exact string equality (sample ids like `COMP001`).
7. **GAC users by domain** derive domain from each user’s email.
8. **Excel caching** is in-process; restart reloads files. Missing/corrupt → `UNKNOWN`.
9. **Alembic** runs `upgrade head` once at startup for local DX; `create_all` is not the source of truth.
10. **Audit tables** exist; lookup endpoints do not require an audit write to succeed.
11. **Python 3.11+** is the target.
12. **docker-compose** runs the API for convenience; unit tests do not need it.
13. **No fuzzy user identification** — only exact normalized email equality.
14. **Web tools** are REST/JSON only; browser automation is out of scope.
15. **PowerShell-named tools** in the demo map to Python Excel backends (no live `powershell.exe`).
16. **Approved endpoints** are static strings in the registry; the mock web provider does not do network I/O.
17. **AI tool selection** only keeps registry entries with `allow_ai_selection=true`.
18. **Default AI** is Ollama `qwen3:4b` with fallback `qwen3:1.7b`; OpenAI is optional.
19. **Confidence gate**: `confidence <= 0.99` (default) or missing/invalid → human review. Similar-domain candidates and LDAP/GAC conflicts force review too.
20. **Single-flight inference**: one Ollama call at a time.
21. **Local RAG** returns at most `RAG_TOP_K` snippets (default 3, hard cap 5).
22. **Tests** force `AI_PROVIDER=mock` so pytest does not need a running Ollama.
23. **Workflow states**: `RECEIVED`, `ANALYZING`, `INVESTIGATING`, `AWAITING_DECISION_APPROVAL`, `REPLANNING`, `AWAITING_EMAIL_APPROVAL`, `COMPLETED`, `FAILED`, `CANCELLED`.
24. **Mock Teams** = in-process provider with `mock-teams-*` refs (no network).
