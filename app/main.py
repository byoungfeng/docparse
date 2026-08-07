from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.api.routes import router
from app.config import get_settings
from app.jobs.runner import get_job_store

STATIC_DIR = Path(__file__).resolve().parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    store = get_job_store()
    store.fail_orphaned_running()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="DocParse",
        description=(
            "Unified document → Markdown API. "
            "Engines: pdf-inspector (PDF) + anydoc (office). MIT upstream. "
            "Use /v1/parse/async for large / OCR-heavy files."
        ),
        version=__version__,
        lifespan=lifespan,
    )
    app.include_router(router)
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    return app


app = create_app()


def run() -> None:
    settings = get_settings()
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=False)


if __name__ == "__main__":
    run()
