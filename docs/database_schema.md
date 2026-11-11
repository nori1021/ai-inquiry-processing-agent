# Database schema

SQLite via SQLAlchemy. Migrations managed by Alembic. Tables are **not** recreated on every application startup.

## Core tables

### `audit_events`

Lightweight audit log for lookups and workflow actions.

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | Auto-increment |
| `event_type` | VARCHAR(64) | e.g. `lookup.ldap_user` |
| `payload_json` | TEXT | JSON summary |
| `created_at` | DATETIME | UTC |
| `workflow_id` | INTEGER nullable | Correlation when present |

### `lookup_cache_meta`

Tracks last successful Excel load times for observability.

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `source_name` | VARCHAR(64) UNIQUE | `ldap_users`, `gac_users`, `ldap_companies` |
| `loaded_at` | DATETIME | |
| `row_count` | INTEGER | |
| `file_path` | VARCHAR(512) | |

Lookup truth for the demo remains the Excel files. These tables support audit/ops.

## Workflow tables

### `workflow_instances`

Persisted workflow: `state`, inquiry fields, `context_json`, `retry_count`, `tool_call_count`, timestamps.

### `workflow_transitions`

Append-only transition log: `from_state`, `to_state`, `reason`.

### `approval_requests`

`approval_type` (`decision`|`email`), `status`, `summary`, `external_ref`, `replan_requested`, decision metadata.

## Migration policy

- Revisions: `001_initial`, `002_workflow`.
- Startup runs Alembic `upgrade head`.
- Future PostgreSQL: change `DATABASE_URL`; keep models portable.
