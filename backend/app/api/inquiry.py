from __future__ import annotations

from fastapi import APIRouter

from app.agents.inquiry_agent import analyze_and_investigate
from app.schemas.inquiry import InquiryAnalyzeRequest, InquiryAnalyzeResponse

router = APIRouter()


@router.post("/analyze", response_model=InquiryAnalyzeResponse)
async def analyze_inquiry(body: InquiryAnalyzeRequest) -> InquiryAnalyzeResponse:
    """
    Analyze an inquiry, plan selective investigation, execute registered tools,
    and apply Python validation/confidence gates.
    """
    return await analyze_and_investigate(body)
