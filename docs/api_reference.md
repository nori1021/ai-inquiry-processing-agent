# API notes

Base URL: `/api/v1`

Lookup payloads include a `status` field:

| `status` | Meaning |
|---|---|
| `FOUND` | Record(s) returned |
| `NOT_REGISTERED` | Source readable; no match |
| `UNKNOWN` | Source missing/unreadable |

## Health

### `GET /health`

Returns `{ "status": "ok" }`.

## LDAP

### `GET /api/v1/lookup/ldap/users?email=`

Exact case-insensitive email match in `ldap_users.xlsx`.

### `GET /api/v1/lookup/ldap/companies/{company_id}`

Exact `CompanyID` match in `ldap_companies.xlsx`.

### `GET /api/v1/lookup/ldap/companies?domain=`

Exact case-insensitive `EmailDomain` match via `get_company_by_domain`.

## GAC

### `GET /api/v1/lookup/gac/users?email=`

Exact case-insensitive email match in `gac_users.xlsx`.

### `GET /api/v1/lookup/gac/users-by-domain?domain=`

All GAC users whose email domain equals the given domain (case-insensitive).

## Similarity

### `GET /api/v1/lookup/domains/similar?domain=&threshold=`

RapidFuzz similarity against known company email domains. Returns **candidates only**. Default threshold from settings (`SIMILARITY_THRESHOLD`, default `80`). Optional `threshold` query overrides per request (0–100).

## Tool Registry

### `GET /api/v1/tools`

List registered tools (name, kind, description, permissions, execution policy summary, enabled).

### `GET /api/v1/tools/{name}`

Get one tool definition including input schema.

### `POST /api/v1/tools/{name}/execute`

Run a registered tool through its provider (mock web / Excel-backed lookups in the demo).

```json
{ "arguments": { "email": "alice@acme.com" } }
```

Rejected if the tool is unknown, disabled, or arguments fail schema validation. Never accepts arbitrary URLs or shell commands.

## Inquiry analysis

### `POST /api/v1/inquiry/analyze`

Analyze an inquiry with the configured AI provider (default **Ollama**), plan selective investigation, execute registered tools, and apply Python validation gates.

```json
{
  "subject": "Password reset",
  "body": "Please help alice@acme.com reset their password.",
  "from_email": "manager@acme.com",
  "execute_tools": true
}
```

Response includes: `analysis`, `investigation_plan`, `selected_tools`, `tool_results`, `needs_human_review`, `review_flags`, and `email_requires_approval` (always `true`).

## Workflows

### `POST /api/v1/workflows`

Create a persistent workflow (`auto_advance` default true).

### `GET /api/v1/workflows/{id}`

Load current state, context, approvals, transitions (restart-safe).

### `POST /api/v1/workflows/{id}/advance`

Continue automatic steps until an approval gate or terminal state.

### `POST /api/v1/workflows/{id}/approvals/{approval_id}/decide`

```json
{ "decision": "approved", "note": "...", "request_replan": false }
```

`decision` is `approved` or `rejected`. Reject → `CANCELLED`. Approve decision → email gate (or `REPLANNING` if `request_replan`).

### `POST /api/v1/workflows/{id}/investigate-readonly`

Independent read-only tool execution while approval is pending.

### `GET /api/v1/workflows/{id}/audit`

Critical audit events for the workflow.

## Emails

- `GET /api/v1/emails/templates`
- `GET/PUT /api/v1/emails/workflows/{id}/draft`
- `POST /api/v1/emails/workflows/{id}/draft/submit-for-approval`

## Teams (mock)

- `POST /api/v1/teams/mock/notify` (header `X-Teams-Secret`)
- `POST /api/v1/teams/callbacks/approval` (header `X-Teams-Secret`)

## Evaluations

- `POST /api/v1/evaluations/run`
- `GET /api/v1/evaluations/latest`
