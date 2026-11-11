from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Optional

import httpx

from app.providers.ollama_errors import OllamaProviderError
from app.schemas.inquiry import InquiryAnalysis

logger = logging.getLogger(__name__)

_INFERENCE_LOCK = asyncio.Lock()

SYSTEM_PROMPT = """You are an IT helpdesk inquiry analyst.
Return ONLY valid JSON matching this shape:
{
  "summary": string,
  "intent": string,
  "category": string,
  "users": [{"email": string|null, "display_name": string|null, "role": "requester"|"affected_user"|"manager"|"technical_contact"|"other"|"unknown", "reason": string, "investigate": "REQUIRED"|"NOT_REQUIRED"|"UNCERTAIN"}],
  "companies": [{"name": string|null, "domain": string|null, "company_id": string|null, "source": string, "investigate": "REQUIRED"|"NOT_REQUIRED"|"UNCERTAIN"}],
  "planned_tools": [{"tool": string, "arguments": object, "reason": string, "need": "REQUIRED"|"NOT_REQUIRED"|"UNCERTAIN"}],
  "confidence": number between 0 and 1,
  "notes": [string]
}
Rules:
- Only include people relevant to the inquiry.
- Prefer company identification from extracted user email domains.
- planned_tools.tool MUST be chosen only from the provided selectable tool names.
- Never invent URLs, shell commands, or unregistered tools.
- investigate=REQUIRED only when lookup is needed for resolution.
- For password_reset / access issues, do NOT plan LDAP/GAC registration tools
  unless the inquiry explicitly requires directory/identity/registration verification.
- If the user says password reset was already tried and failed / does not work,
  set intent to "password_reset_failed" (NOT "password_reset") and note that
  standard reset steps must not be re-sent.
- Keep reasoning compact; context budget is limited.
"""


def _try_memory_mb() -> Optional[float]:
    try:
        import psutil

        return round(psutil.Process().memory_info().rss / (1024 * 1024), 2)
    except Exception:
        return None


class OllamaProvider:
    """Local Ollama LLM. Does not silently fall back to mock heuristics."""

    name = "ollama"

    def __init__(
        self,
        *,
        base_url: str = "http://127.0.0.1:11434",
        model: str = "qwen3:4b",
        fallback_model: str = "qwen3:1.7b",
        temperature: float = 0.1,
        num_ctx: int = 4096,
        timeout_seconds: float = 120.0,
        allow_mock_fallback: bool = False,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.fallback_model = fallback_model
        self.temperature = temperature
        self.num_ctx = num_ctx
        self.timeout_seconds = timeout_seconds
        self.allow_mock_fallback = allow_mock_fallback
        self.last_metrics: dict[str, Any] = {}
        self.last_error: Optional[dict[str, str]] = None

    async def is_available(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                return resp.status_code == 200
        except Exception:
            return False

    async def status(self) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                if resp.status_code != 200:
                    return {
                        "reachable": False,
                        "base_url": self.base_url,
                        "model": self.model,
                        "error": f"HTTP {resp.status_code}",
                    }
                models = [
                    m.get("name") for m in (resp.json().get("models") or [])
                ]
                return {
                    "reachable": True,
                    "base_url": self.base_url,
                    "model": self.model,
                    "fallback_model": self.fallback_model,
                    "models": models,
                    "primary_installed": self.model in models
                    or any(str(m).startswith(self.model) for m in models),
                    "last_error": self.last_error,
                }
        except Exception as exc:  # noqa: BLE001
            return {
                "reachable": False,
                "base_url": self.base_url,
                "model": self.model,
                "error": str(exc),
                "last_error": self.last_error,
            }

    async def analyze_inquiry(
        self,
        *,
        subject: str,
        body: str,
        from_email: Optional[str],
        selectable_tools: list[dict[str, Any]],
        rag_snippets: Optional[list[dict[str, Any]]] = None,
    ) -> InquiryAnalysis:
        if not await self.is_available():
            self.last_error = {
                "code": "ollama_unavailable",
                "message": f"Cannot reach Ollama at {self.base_url}",
            }
            self.last_metrics = {
                "provider": "ollama",
                "status": "unavailable",
                "error": self.last_error,
                "latency_ms": 0,
                "memory_mb": _try_memory_mb(),
                "model": None,
            }
            if self.allow_mock_fallback:
                from app.providers.mock_ai import MockAIProvider

                analysis = await MockAIProvider().analyze_inquiry(
                    subject=subject,
                    body=body,
                    from_email=from_email,
                    selectable_tools=selectable_tools,
                    rag_snippets=rag_snippets,
                )
                analysis.raw_provider = "mock_fallback_ollama_unavailable"
                analysis.notes = list(analysis.notes) + [
                    self.last_error["message"]
                ]
                return analysis
            raise OllamaProviderError(
                "ollama_unavailable",
                self.last_error["message"],
            )

        async with _INFERENCE_LOCK:
            try:
                return await self._analyze_locked(
                    subject=subject,
                    body=body,
                    from_email=from_email,
                    selectable_tools=selectable_tools,
                    rag_snippets=rag_snippets or [],
                    model=self.model,
                )
            except Exception as primary_exc:
                primary_msg = self._format_exc(primary_exc)
                logger.warning(
                    "Ollama primary model %s failed: %s; considering fallback %s",
                    self.model,
                    primary_msg,
                    self.fallback_model,
                )
                status = await self.status()
                models = set(status.get("models") or [])
                fallback_installed = self.fallback_model in models or any(
                    str(m).startswith(self.fallback_model) for m in models
                )
                if not fallback_installed or self.fallback_model == self.model:
                    self.last_error = {
                        "code": "ollama_inference_failed",
                        "message": (
                            f"primary ({self.model}): {primary_msg}; "
                            f"fallback model {self.fallback_model} not installed"
                        ),
                    }
                    self._record_error_metrics()
                    if self.allow_mock_fallback:
                        return await self._mock_fallback_analysis(
                            subject=subject,
                            body=body,
                            from_email=from_email,
                            selectable_tools=selectable_tools,
                            rag_snippets=rag_snippets,
                            raw_provider="mock_fallback_ollama_error",
                        )
                    raise OllamaProviderError(
                        "ollama_inference_failed",
                        self.last_error["message"],
                    ) from primary_exc
                try:
                    return await self._analyze_locked(
                        subject=subject,
                        body=body,
                        from_email=from_email,
                        selectable_tools=selectable_tools,
                        rag_snippets=rag_snippets or [],
                        model=self.fallback_model,
                    )
                except Exception as fallback_exc:
                    self.last_error = {
                        "code": "ollama_inference_failed",
                        "message": (
                            f"primary ({self.model}): {primary_msg}; "
                            f"fallback ({self.fallback_model}): "
                            f"{self._format_exc(fallback_exc)}"
                        ),
                    }
                    self._record_error_metrics()
                    if self.allow_mock_fallback:
                        return await self._mock_fallback_analysis(
                            subject=subject,
                            body=body,
                            from_email=from_email,
                            selectable_tools=selectable_tools,
                            rag_snippets=rag_snippets,
                            raw_provider="mock_fallback_ollama_error",
                        )
                    raise OllamaProviderError(
                        "ollama_inference_failed",
                        self.last_error["message"],
                    ) from fallback_exc

    @staticmethod
    def _format_exc(exc: BaseException) -> str:
        text = str(exc).strip()
        if text:
            return f"{type(exc).__name__}: {text}"
        return repr(exc)

    def _record_error_metrics(self) -> None:
        self.last_metrics = {
            "provider": "ollama",
            "status": "error",
            "error": self.last_error,
            "latency_ms": 0,
            "memory_mb": _try_memory_mb(),
            "model": None,
        }

    async def _mock_fallback_analysis(
        self,
        *,
        subject: str,
        body: str,
        from_email: Optional[str],
        selectable_tools: list[dict[str, Any]],
        rag_snippets: Optional[list[dict[str, Any]]],
        raw_provider: str,
    ) -> InquiryAnalysis:
        from app.providers.mock_ai import MockAIProvider

        analysis = await MockAIProvider().analyze_inquiry(
            subject=subject,
            body=body,
            from_email=from_email,
            selectable_tools=selectable_tools,
            rag_snippets=rag_snippets,
        )
        analysis.raw_provider = raw_provider
        analysis.notes = list(analysis.notes) + [
            (self.last_error or {}).get("message") or "ollama error"
        ]
        return analysis

    async def _analyze_locked(
        self,
        *,
        subject: str,
        body: str,
        from_email: Optional[str],
        selectable_tools: list[dict[str, Any]],
        rag_snippets: list[dict[str, Any]],
        model: str,
    ) -> InquiryAnalysis:
        started = time.perf_counter()
        mem_before = _try_memory_mb()

        # Keep tool catalog compact — full schemas blow latency on 4b thinking models.
        tool_catalog = [
            {
                "name": t["name"],
                "description": (t.get("description") or "")[:160],
            }
            for t in selectable_tools
        ]
        limited_rag = rag_snippets[:3]
        user_payload = {
            "subject": subject,
            "body": body,
            "from_email": from_email,
            "selectable_tools": tool_catalog,
            "rag_snippets": limited_rag,
        }
        # Qwen3 thinking mode is too slow for demo ops console; disable it.
        prompt = (
            SYSTEM_PROMPT
            + "\n\nInquiry JSON:\n"
            + json.dumps(user_payload, ensure_ascii=False)
            + "\n\n/no_think"
        )

        # Thinking models + structured JSON can exceed short read timeouts.
        timeout = httpx.Timeout(
            connect=10.0,
            read=float(self.timeout_seconds),
            write=60.0,
            pool=10.0,
        )
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                    # Qwen3 thinking mode is multi-minute on this host; disable for ops demo.
                    "think": False,
                    "options": {
                        "temperature": self.temperature,
                        "num_ctx": self.num_ctx,
                    },
                },
            )
            resp.raise_for_status()
            data = resp.json()
            raw_text = data.get("response") or ""
            parsed = json.loads(raw_text)
            analysis = InquiryAnalysis.model_validate(parsed)
            analysis.raw_provider = f"ollama:{model}"

            allowed = {t["name"] for t in selectable_tools}
            planned = [p for p in analysis.planned_tools if p.tool in allowed]
            dropped = len(analysis.planned_tools) - len(planned)
            analysis.planned_tools = planned
            if dropped:
                analysis.notes = list(analysis.notes) + [
                    f"dropped {dropped} unregistered tool suggestion(s)"
                ]

            latency_ms = (time.perf_counter() - started) * 1000
            self.last_error = None
            self.last_metrics = {
                "provider": "ollama",
                "status": "ok",
                "model": model,
                "latency_ms": round(latency_ms, 2),
                "memory_mb_before": mem_before,
                "memory_mb_after": _try_memory_mb(),
                "num_ctx": self.num_ctx,
                "temperature": self.temperature,
                "tool_suggestions": len(planned),
                "tools_dropped_unregistered": dropped,
                "rag_snippets_used": len(limited_rag),
            }
            logger.info("ollama_inference metrics=%s", self.last_metrics)
            analysis.notes = list(analysis.notes) + [
                f"latency_ms={self.last_metrics['latency_ms']}",
                f"model={model}",
            ]
            return analysis
