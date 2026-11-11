# Teams / Power Automate Setup (Optional)

Local demo works **without** Microsoft 365. Mock path:

1. Backend creates approval with `external_ref` like `mock-teams-decision-…`
2. UI or `POST /api/v1/teams/mock/notify` records a local notification
3. `POST /api/v1/teams/callbacks/approval` with header `X-Teams-Secret` applies the decision

## Real M365 (not required for demo)

1. Create a Power Automate flow triggered by HTTP webhook / Teams Adaptive Card action.
2. Set `TEAMS_WEBHOOK_URL` in `.env` to the flow HTTP URL.
3. Set a strong `TEAMS_CALLBACK_SECRET` shared with the flow.
4. Flow posts back to `https://<your-host>/api/v1/teams/callbacks/approval` with:
   - Header `X-Teams-Secret`
   - JSON: `workflow_id`, `approval_id`, `decision` (`approved`|`rejected`), optional `external_ref`, `request_replan`
5. Keep Graph email send disabled unless you intentionally turn on the Graph stub (`EMAIL_PROVIDER=graph`, `GRAPH_ENABLED=true`) — still not a production send path.

## Auth notes

- Callback rejects missing/invalid secrets (401).
- State recovery remains SQLite-backed; callbacks are idempotent only if approval still pending.
