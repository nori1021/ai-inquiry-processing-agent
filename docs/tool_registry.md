# Tool Registry

## Decision

**REST API-based web tools only.** Browser automation is out of scope.

## What gets registered

Every executable capability is registered with:

| Field | Purpose |
|---|---|
| `name` | Stable tool id (e.g. `lookup_ldap_user`) |
| `kind` | `web_api` \| `powershell` \| `python_local` |
| `description` | Short purpose text (also used when the model picks tools) |
| `input_schema` | JSON Schema / Pydantic model for validated params |
| `output_schema` | Expected response shape |
| `permissions` | Who/what may invoke |
| `execution_policy` | Approved endpoint or script id, timeout, auth profile |
| `enabled` | Kill switch without code changes |

**Hard rules**

1. Only registered tools may execute.
2. Web API calls go only to **approved endpoints** — never model-generated URLs.
3. PowerShell-style tools run only **approved script ids** with validated params — never free-form shell.
4. Auth, timeouts, error handling, response validation, and audit hooks wrap every execution.
5. Email send always needs human approval; tools never bypass that gate.

## Providers (demo)

| Provider | Behavior |
|---|---|
| `MockWebAPIProvider` | In-process synthetic JSON for web tools |
| `MockPowerShellProvider` | Delegates to Python Excel LDAP/GAC tools |
| `HttpxWebAPIProvider` | Stub for a future real HTTP path |

## Initial registered tools

### Web API

| Name | Mock purpose |
|---|---|
| `search_past_inquiries` | Search synthetic past tickets by keyword |
| `search_knowledge_base` | Search synthetic KB articles |
| `get_reply_template` | Return a reply template by id |
| `get_inquiry_history` | History for a given inquiry/email |

### PowerShell-named (Excel-backed in the demo)

| Name | Maps to |
|---|---|
| `lookup_ldap_user` | `get_ldap_user(email)` |
| `lookup_gac_user` | `get_gac_user(email)` |
| `lookup_ldap_company` | `get_ldap_company` / `get_company_by_domain` |
| `lookup_gac_company_users` | `get_gac_users_by_domain` |

### Python local — registration checks

| Name | Purpose |
|---|---|
| `check_ldap_registration` | Exact email/UserID → `yes` / `no` / `unknown` |
| `check_gac_registration` | Same for GAC Excel |
| `check_ldap_gac_registration` | Combined `LDAP_AND_GAC` / `LDAP_ONLY` / `GAC_ONLY` / `NEITHER` / `UNKNOWN` |

Results are not fabricated — they follow Excel hit / miss / source failure only.

## How the model uses tools

```
Inquiry → model suggests tool names + args
       → registry lists enabled tools + schemas
       → executor validates args
       → provider runs approved endpoint/script only
       → response validated + audited
       → workflow continues / escalates
```

## Email approval

No outbound email without explicit human approval, regardless of AI confidence.
