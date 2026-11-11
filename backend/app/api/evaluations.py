from __future__ import annotations

from fastapi import APIRouter

from app.services.evaluation import load_latest_evaluation, run_synthetic_evaluation

router = APIRouter()


@router.post("/run")
async def run_evaluation():
    return await run_synthetic_evaluation()


@router.get("/latest")
def latest_evaluation():
    return load_latest_evaluation()
