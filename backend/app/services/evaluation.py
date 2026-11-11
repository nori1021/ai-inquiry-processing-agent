from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.agents.inquiry_agent import analyze_and_investigate
from app.config.settings import PROJECT_ROOT
from app.schemas.inquiry import InquiryAnalyzeRequest

CASES_PATH = PROJECT_ROOT / "evaluations" / "synthetic_cases.json"
RESULTS_PATH = PROJECT_ROOT / "evaluations" / "latest_results.json"


async def run_synthetic_evaluation() -> dict[str, Any]:
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    results: list[dict[str, Any]] = []
    tool_hits = 0
    tool_cases = 0

    for case in cases:
        analysis = await analyze_and_investigate(
            InquiryAnalyzeRequest(
                subject=case.get("subject") or "",
                body=case["body"],
                from_email=case.get("from_email"),
                execute_tools=True,
            )
        )
        selected = {t.tool for t in analysis.selected_tools}
        expected_any = set(case.get("expect_tools_any") or [])
        hit = bool(selected & expected_any) if expected_any else True
        tool_cases += 1
        if hit:
            tool_hits += 1

        expect_review = bool(case.get("expect_needs_review", True))
        review_ok = analysis.needs_human_review is expect_review
        ok = hit and review_ok and analysis.email_requires_approval
        results.append(
            {
                "id": case["id"],
                "ok": ok,
                "detail": (
                    f"tools={sorted(selected)}; needs_review={analysis.needs_human_review}; "
                    f"hit={hit}; review_ok={review_ok}"
                ),
                "selected_tools": sorted(selected),
            }
        )

    passed = sum(1 for r in results if r["ok"])
    failed = len(results) - passed
    summary = {
        "run_id": uuid.uuid4().hex[:12],
        "ran_at": datetime.now(timezone.utc).isoformat(),
        "total": len(results),
        "passed": passed,
        "failed": failed,
        "metrics": {
            "tool_selection_hit_rate": round(tool_hits / tool_cases, 3)
            if tool_cases
            else 0.0,
            "pass_rate": round(passed / len(results), 3) if results else 0.0,
        },
        "note": (
            "Synthetic local metrics only — not a claimed production accuracy target."
        ),
        "results": results,
    }
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def load_latest_evaluation() -> dict[str, Any]:
    if not RESULTS_PATH.is_file():
        return {
            "run_id": "none",
            "total": 0,
            "passed": 0,
            "failed": 0,
            "metrics": {},
            "note": "No evaluation has been run yet.",
            "results": [],
        }
    return json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
