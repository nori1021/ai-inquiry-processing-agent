from __future__ import annotations

import json
from typing import Any, Optional

import httpx

from app.providers.mock_ai import MockAIProvider
from app.schemas.inquiry import InquiryAnalysis

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
"""


class OpenAIProvider:
    """OpenAI Chat Completions integration with structured JSON output."""

    name = "openai"

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "gpt-4o-mini",
        base_url: str = "https://api.openai.com/v1",
        timeout_seconds: float = 30.0,
        fallback: Optional[MockAIProvider] = None,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.fallback = fallback or MockAIProvider()

    async def analyze_inquiry(
        self,
        *,
        subject: str,
        body: str,
        from_email: Optional[str],
        selectable_tools: list[dict[str, Any]],
        rag_snippets: Optional[list[dict[str, Any]]] = None,
    ) -> InquiryAnalysis:
        """Optional provider — not the MVP default (Ollama is)."""
        if not self.api_key:
            analysis = await self.fallback.analyze_inquiry(
                subject=subject,
                body=body,
                from_email=from_email,
                selectable_tools=selectable_tools,
                rag_snippets=rag_snippets,
            )
            analysis.raw_provider = "mock_fallback_no_key"
            analysis.notes = list(analysis.notes) + ["openai key missing; used mock"]
            return analysis

        tool_catalog = [
            {
                "name": t["name"],
                "description": t.get("description"),
                "input_schema": t.get("input_schema"),
            }
            for t in selectable_tools
        ]
        user_payload = {
            "subject": subject,
            "body": body,
            "from_email": from_email,
            "selectable_tools": tool_catalog,
            "rag_snippets": (rag_snippets or [])[:3],
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "temperature": 0,
                        "response_format": {"type": "json_object"},
                        "messages": [
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {
                                "role": "user",
                                "content": json.dumps(user_payload, ensure_ascii=False),
                            },
                        ],
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                parsed = json.loads(content)
                analysis = InquiryAnalysis.model_validate(parsed)
                analysis.raw_provider = self.name
                allowed = {t["name"] for t in selectable_tools}
                analysis.planned_tools = [
                    p for p in analysis.planned_tools if p.tool in allowed
                ]
                return analysis
        except Exception as exc:  # noqa: BLE001 — offline-safe fallback
            analysis = await self.fallback.analyze_inquiry(
                subject=subject,
                body=body,
                from_email=from_email,
                selectable_tools=selectable_tools,
                rag_snippets=rag_snippets,
            )
            analysis.raw_provider = "mock_fallback_openai_error"
            analysis.notes = list(analysis.notes) + [f"openai error fallback: {exc}"]
            return analysis
