from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


def _run_sample_generator() -> None:
    script = PROJECT_ROOT / "scripts" / "generate_sample_data.py"
    spec = importlib.util.spec_from_file_location("generate_sample_data", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.main()


@pytest.fixture(autouse=True)
def _clear_excel_cache():
    from app.services.excel_loader import clear_excel_cache

    clear_excel_cache()
    yield
    clear_excel_cache()


@pytest.fixture(scope="session", autouse=True)
def _ensure_sample_excel():
    sample = PROJECT_ROOT / "data" / "sample" / "ldap_users.xlsx"
    if not sample.exists():
        _run_sample_generator()
