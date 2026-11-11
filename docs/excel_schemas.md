# Excel Data Schemas

Sample files live under `data/sample/`.

## `ldap_users.xlsx`

| Column | Type | Required | Notes |
|---|---|---|---|
| UserID | string | yes | Unique user id |
| Email | string | yes | Matched case-insensitively after trim + lower |
| CompanyID | string | yes | FK-like to companies |
| CompanyName | string | yes | Denormalized display name |
| Status | string | yes | e.g. `Active`, `Inactive` |

## `gac_users.xlsx`

Same columns as `ldap_users.xlsx`.

## `ldap_companies.xlsx`

| Column | Type | Required | Notes |
|---|---|---|---|
| CompanyID | string | yes | Unique |
| CompanyName | string | yes | |
| EmailDomain | string | yes | e.g. `acme.com` (no `@`); matched case-insensitively |
| Status | string | yes | e.g. `Active` |

## Matching rules

- **Users:** exact email equality after `email.strip().lower()`. No fuzzy user match.
- **Companies by id:** exact `CompanyID` string match.
- **Companies by domain:** exact domain equality after normalize (strip, lower, strip leading `@`).
- **Similar domains:** RapidFuzz `ratio` / partial ratio against all `EmailDomain` values; results are candidates only.
- Missing or unreadable workbook → tool returns `UNKNOWN`.
