from __future__ import annotations

import logging
import time

from app.agents.planner import build_investigation_plan
from app.agents.tool_selection import (
    domains_for_similarity_check,
    list_selectable_tools,
    select_tools_for_investigation,
)
from app.providers.factory import get_ai_provider
from app.providers.ollama_errors import OllamaProviderError
from app.registry import get_executor
from app.schemas.inquiry import (
    InquiryAnalysis,
    InquiryAnalyzeRequest,
    InquiryAnalyzeResponse,
    RagReference,
    ReviewFlag,
    ToolCallOutcome,
)
from app.services.local_rag import retrieve_limited_snippets
from app.services.password_reset_signals import (
    INTENT_PASSWORD_RESET_FAILED,
    detect_prior_password_reset_failed,
)
from app.services.validation_gates import (
    evaluate_confidence_gate,
    evaluate_inquiry_text_gates,
    evaluate_tool_result_gates,
    merge_review_decision,
)
from app.tools.company_lookup import find_similar_domains

logger = logging.getLogger(__name__)


def _tool_selection_accuracy(
    suggested: list[str],
    executed_ok_tools: list[str],
) -> dict[str, float | int]:
    if not suggested:
        return {"suggested": 0, "executed_ok": 0, "accuracy": 1.0}
    ok_set = set(executed_ok_tools)
    hits = sum(1 for t in suggested if t in ok_set)
    return {
        "suggested": len(suggested),
        "executed_ok_overlap": hits,
        "accuracy": round(hits / len(suggested), 3),
    }


def _classify_ai_mode(provider_name: str, raw_provider: str) -> str:
    raw = (raw_provider or "").lower()
    name = (provider_name or "").lower()
    if "mock_fallback" in raw:
        return "mock_fallback"
    if raw.startswith("ollama_unavailable") or "ollama_unavailable" in raw:
        return "ollama_unavailable"
    if raw.startswith("ollama_error") or "ollama_inference_failed" in raw:
        return "ollama_error"
    if raw.startswith("ollama:") or name == "ollama":
        return "actual_llm"
    if name == "mock" or raw == "mock":
        return "mock_heuristic"
    return "unknown"


async def analyze_and_investigate(
    request: InquiryAnalyzeRequest,
) -> InquiryAnalyzeResponse:
    """
    Local LLM (Ollama) or mock analysis → Python gates → selective Tool Registry execution.
    """
    provider = get_ai_provider()
    selectable = list_selectable_tools()

    rag_query = f"{request.subject} {request.body}".strip()
    rag_snippets = retrieve_limited_snippets(rag_query)
    rag_references = [
        RagReference(
            source=str(s.get("source") or "unknown"),
            id=str(s["id"]) if s.get("id") is not None else None,
            text=str(s.get("text") or ""),
        )
        for s in rag_snippets
    ]

    provider_error: str | None = None
    provider_status = "ok"
    try:
        analysis = await provider.analyze_inquiry(
            subject=request.subject,
            body=request.body,
            from_email=request.from_email,
            selectable_tools=selectable,
            rag_snippets=rag_snippets,
        )
    except OllamaProviderError as exc:
        provider_error = exc.message
        provider_status = (
            "unavailable" if exc.code == "ollama_unavailable" else "error"
        )
        analysis = InquiryAnalysis(
            summary="Ollama inference failed — operator review required",
            intent="unknown",
            category="general",
            confidence=0.0,
            notes=[exc.message, f"ollama_error_code={exc.code}"],
            raw_provider=f"ollama_error:{exc.code}",
        )
        logger.error("ollama_provider_error code=%s msg=%s", exc.code, exc.message)

    # Deterministic override: prior reset failure must not stay as plain password_reset
    if detect_prior_password_reset_failed(request.subject, request.body):
        if (analysis.intent or "").lower() in ("", "password_reset", "access_request"):
            analysis.intent = INTENT_PASSWORD_RESET_FAILED
        note = (
            "User reports prior reset failed; do not re-send standard reset steps."
        )
        if note not in (analysis.notes or []):
            analysis.notes = list(analysis.notes or []) + [note]

    review_flags = evaluate_confidence_gate(analysis)
    review_flags.extend(
        evaluate_inquiry_text_gates(
            subject=request.subject,
            body=request.body,
            analysis=analysis,
        )
    )
    if provider_error:
        review_flags.append(
            ReviewFlag(
                code="ollama_provider_error",
                message=provider_error,
                severity="block",
            )
        )

    plan = build_investigation_plan(analysis)
    selected = select_tools_for_investigation(analysis, plan)

    tool_results: list[ToolCallOutcome] = []
    if request.execute_tools and not provider_error:
        executor = get_executor()
        for call in selected:
            started = time.perf_counter()
            outcome = await executor.execute(call.tool, call.arguments)
            duration_ms = (time.perf_counter() - started) * 1000
            if getattr(outcome, "duration_ms", 0):
                duration_ms = float(outcome.duration_ms)
            tool_results.append(
                ToolCallOutcome(
                    tool=call.tool,
                    arguments=call.arguments,
                    ok=outcome.ok,
                    result=outcome.result,
                    error=outcome.error,
                    provider=outcome.provider,
                    duration_ms=round(duration_ms, 2),
                    status="ok" if outcome.ok else "error",
                )
            )

        for domain in domains_for_similarity_check(analysis):
            started = time.perf_counter()
            similar = find_similar_domains(domain)
            duration_ms = (time.perf_counter() - started) * 1000
            tool_results.append(
                ToolCallOutcome(
                    tool="find_similar_domains",
                    arguments={"domain": domain},
                    ok=True,
                    result=similar.model_dump(mode="json"),
                    provider="python_local",
                    duration_ms=round(duration_ms, 2),
                    status="ok",
                )
            )

        review_flags.extend(evaluate_tool_result_gates(tool_results))

    metrics = getattr(provider, "last_metrics", {}) or {}
    accuracy = _tool_selection_accuracy(
        [c.tool for c in selected],
        [r.tool for r in tool_results if r.ok],
    )
    provider_name = getattr(provider, "name", analysis.raw_provider)
    ai_mode = _classify_ai_mode(provider_name, analysis.raw_provider)
    if ai_mode == "mock_fallback":
        provider_status = "mock"
    elif ai_mode == "mock_heuristic":
        provider_status = "mock"
    elif provider_error:
        pass
    else:
        provider_status = "ok"

    logger.info(
        "inquiry_analyze provider=%s ai_mode=%s status=%s metrics=%s review=%s",
        provider_name,
        ai_mode,
        provider_status,
        metrics,
        [f.code for f in review_flags],
    )

    return InquiryAnalyzeResponse(
        analysis=analysis,
        investigation_plan=plan,
        selected_tools=selected,
        tool_results=tool_results,
        rag_references=rag_references,
        needs_human_review=merge_review_decision(review_flags),
        review_flags=review_flags,
        email_requires_approval=True,
        provider=provider_name,
        ai_mode=ai_mode,
        provider_status=provider_status,
        provider_error=provider_error,
        inference_metrics={**metrics, "tool_selection": accuracy},
    )
