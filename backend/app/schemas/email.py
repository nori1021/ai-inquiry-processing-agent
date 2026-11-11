from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class EmailDraftView(BaseModel):
    id: int
    workflow_id: int
    version: int
    template_id: str
    to_email: str
    subject: str
    body: str
    content_hash: str
    approved_hash: Optional[str] = None
    is_current: bool
    sent: bool
    sent_at: Optional[datetime] = None
    provider_message_id: Optional[str] = None


class EmailDraftUpdateRequest(BaseModel):
    to_email: Optional[str] = None
    subject: Optional[str] = None
    body: Optional[str] = None
    template_id: Optional[str] = None


class EmailTemplateView(BaseModel):
    template_id: str


class EmailSendResultView(BaseModel):
    ok: bool
    message_id: Optional[str] = None
    error: Optional[str] = None
    provider: str = "mock"
    content_hash: str = ""
