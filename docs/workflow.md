# Workflow

## Stateless helpers

Direct lookup / tool / inquiry-analyze routes stay available for simple API checks.

## Persistent workflow

Workflow instances live in SQLite so a restart does not lose progress. Transitions are validated on the server.

### States

`RECEIVED` → `ANALYZING` → `INVESTIGATING` → `AWAITING_DECISION_APPROVAL` and/or `AWAITING_EMAIL_APPROVAL` → `COMPLETED`  

Also: `REPLANNING`, `FAILED`, `CANCELLED`

### Rules

- Illegal transitions are rejected server-side.
- Confidence / validation gates stay in Python; replanning cannot skip them.
- Outbound email always needs `AWAITING_EMAIL_APPROVAL` first.
- While waiting for approval, read-only registry lookups may run; mutating / unregistered tools are blocked.
- Tool calls, retries, and soft step timeouts are bounded.

### Typical path

```
POST /api/v1/workflows
  → analyze + investigate
  → AWAITING_DECISION_APPROVAL (low confidence / validation flags)
  → approve decision
  → AWAITING_EMAIL_APPROVAL
  → approve email
  → COMPLETED (demo uses mock send after approval)
```
