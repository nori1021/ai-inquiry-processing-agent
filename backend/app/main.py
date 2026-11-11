from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.config import get_settings


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Apply Alembic migrations — do NOT recreate tables via create_all
    from app.database import run_migrations

    try:
        run_migrations()
    except Exception as exc:  # noqa: BLE001
        # Allow app to start for tests that manage DB separately; log in debug
        settings = get_settings()
        if settings.debug:
            print(f"[startup] migration warning: {exc}")
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(api_router)
    return application


app = create_app()
