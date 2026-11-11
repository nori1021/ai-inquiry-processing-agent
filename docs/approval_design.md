# Approval design

## Principle

No outbound email may be sent without explicit human approval. Uncertain identity / company decisions should escalate.

## How it works here

- Approval provider interface (`providers/approval.py`) with a **mock** default that records decisions locally.
- Production target: Microsoft Teams / Power Automate webhook.
- Two approval types: `decision` (confidence / validation review) and `email` (mandatory before send).
- Mock Teams provider records pending approvals with `external_ref`; decisions are applied via API.
- Replanning after a decision approval re-runs analysis gates; it cannot skip email approval.
- Read-only investigations may continue while approvals are pending; dependent ops stay blocked.

## Email (invariant)

All email transmissions need **explicit human approval**, regardless of AI confidence. In the demo, approving email triggers the mock send path — not a live Graph mailbox.
