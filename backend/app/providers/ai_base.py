from __future__ import annotations

from typing import Any, Optional, Protocol

from app.schemas.inquiry import InquiryAnalysis


class AIProvider(Protocol):
    name: str

    async def analyze_inquiry(
        self,
        *,
        subject: str,
        body: str,
        from_email: str | None,
        selectable_tools: list[dict[str, Any]],
        rag_snippets: Optional[list[dict[str, Any]]] = None,
    ) -> InquiryAnalysis: ...
