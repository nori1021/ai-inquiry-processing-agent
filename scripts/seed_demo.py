"""Seed a few demo workflows for the local UI (uses mock AI)."""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
os.environ.setdefault("AI_PROVIDER", "mock")

from app.database.session import SessionLocal, run_migrations  # noqa: E402
from app.schemas.workflow import WorkflowCreateRequest  # noqa: E402
from app.workflow.engine import WorkflowEngine  # noqa: E402


# Reproducible FDE scenario: analysis → registration tools → RAG → approvals → mock email
DEMOS = [
    {
        "subject": "FDE Demo: GAC registration check",
        "body": (
            "Please confirm whether frank@acme.com is registered in LDAP and GAC. "
            "He cannot access the customer portal.\n"
            "cc: grace@globex.com"
        ),
        "from_email": "alice@acme.com",
    },
    {
        "subject": "Demo: Password reset",
        "body": "Please reset password for alice@acme.com",
        "from_email": "manager@acme.com",
    },
    {
        "subject": "Demo: VPN access",
        "body": "Provision VPN for bob.smith@globex.com",
        "from_email": "grace@globex.com",
    },
]


async def main() -> None:
    run_migrations()
    db = SessionLocal()
    try:
        engine = WorkflowEngine(db)
        ids = []
        for demo in DEMOS:
            view = await engine.create(
                WorkflowCreateRequest(**demo, auto_advance=True)
            )
            ids.append(view.id)
            print(f"seeded workflow #{view.id} state={view.state}")
        print("Demo inquiry IDs:", ids)
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
