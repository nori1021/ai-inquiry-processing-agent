from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from threading import Lock
from typing import Optional

import pandas as pd


class ExcelSourceStatus(str, Enum):
    OK = "OK"
    UNKNOWN = "UNKNOWN"


class ExcelLoadError(Exception):
    """Raised when Excel cannot be read; callers map this to UNKNOWN."""


@dataclass
class LoadedFrame:
    status: ExcelSourceStatus
    frame: Optional[pd.DataFrame]
    detail: str = ""


_cache: dict[str, LoadedFrame] = {}
_lock = Lock()


def clear_excel_cache() -> None:
    with _lock:
        _cache.clear()


def load_dataframe(
    path: Path,
    required_columns: list[str],
    *,
    cache_key: str | None = None,
    force_reload: bool = False,
) -> LoadedFrame:
    """Load an Excel workbook. Missing/unreadable → UNKNOWN (never NOT_REGISTERED)."""
    key = cache_key or str(path.resolve()) if path else "missing"

    with _lock:
        if not force_reload and key in _cache:
            return _cache[key]

    if path is None or not path.exists():
        result = LoadedFrame(
            status=ExcelSourceStatus.UNKNOWN,
            frame=None,
            detail=f"Excel file missing: {path}",
        )
        with _lock:
            _cache[key] = result
        return result

    try:
        frame = pd.read_excel(path, engine="openpyxl")
        frame.columns = [str(c).strip() for c in frame.columns]
        missing = [c for c in required_columns if c not in frame.columns]
        if missing:
            result = LoadedFrame(
                status=ExcelSourceStatus.UNKNOWN,
                frame=None,
                detail=f"Excel missing columns {missing}: {path}",
            )
        else:
            # Normalize string cells; keep as object dtype
            for col in required_columns:
                frame[col] = frame[col].map(
                    lambda v: "" if pd.isna(v) else str(v).strip()
                )
            result = LoadedFrame(status=ExcelSourceStatus.OK, frame=frame, detail="ok")
    except Exception as exc:  # noqa: BLE001 — map any read failure to UNKNOWN
        result = LoadedFrame(
            status=ExcelSourceStatus.UNKNOWN,
            frame=None,
            detail=f"Excel unreadable: {path} ({exc})",
        )

    with _lock:
        _cache[key] = result
    return result
