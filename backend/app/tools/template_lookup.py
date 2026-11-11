"""Template reply lookup — stub for Phase 1."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from app.config.settings import PROJECT_ROOT


def find_reply_template(template_id: str) -> Optional[Path]:
    """
    Locate a reply template under templates/replies/.
    Phase 1 stub: returns path if file exists, else None.
    """
    safe_name = (template_id or "").strip().replace("..", "")
    if not safe_name:
        return None
    path = PROJECT_ROOT / "templates" / "replies" / safe_name
    return path if path.is_file() else None


def list_reply_templates() -> list[str]:
    """List available reply template filenames (Phase 1 stub)."""
    folder = PROJECT_ROOT / "templates" / "replies"
    if not folder.is_dir():
        return []
    return sorted(p.name for p in folder.iterdir() if p.is_file())
