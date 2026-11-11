from __future__ import annotations

import json
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.models.audit import AuditEvent


def record_audit(
    *,
    event_type: str,
    payload: dict[str, Any],
    workflow_id: Optional[int] = None,
    db: Optional[Session] = None,
) -> None:
    """Best-effort audit hook for critical events."""
    owns_session = db is None
    session = db or SessionLocal()
    try:
        session.add(
            AuditEvent(
                event_type=event_type,
                payload_json=json.dumps(payload, default=str),
                workflow_id=workflow_id,
            )
        )
        session.commit()
    except Exception:
        if owns_session:
            session.rollback()
    finally:
        if owns_session:
            session.close()


def record_tool_audit(
    *,
    tool_name: str,
    provider: str,
    ok: bool,
    arguments: dict[str, Any],
    error: Optional[str] = None,
    duration_ms: float = 0.0,
    db: Optional[Session] = None,
    workflow_id: Optional[int] = None,
) -> None:
    record_audit(
        event_type="tool.execute",
        payload={
            "tool": tool_name,
            "provider": provider,
            "ok": ok,
            "arguments": arguments,
            "error": error,
            "duration_ms": duration_ms,
        },
        workflow_id=workflow_id,
        db=db,
    )
