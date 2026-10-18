"""TabTool FastAPI application.

Phase 0 exposes only health/version endpoints and the static shell.
The search, job and tab APIs arrive in later phases.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.config import (
    APP_NAME,
    HOST,
    PORT,
    SPOTIFY_CLIENT_ID,
    STATIC_DIR,
    VERSION,
    ensure_data_dirs,
)

ensure_data_dirs()

app = FastAPI(
    title=APP_NAME,
    version=VERSION,
    description="Local guitar tab generator and viewer.",
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def _html(name: str) -> FileResponse:
    return FileResponse(
        STATIC_DIR / name,
        media_type="text/html",
        headers={"Cache-Control": "no-store"},
    )


@app.get("/api/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "app": APP_NAME, "version": __version__}


@app.get("/api/version", tags=["system"])
def version() -> dict[str, str]:
    return {"version": __version__}


@app.get("/api/config", tags=["system"])
def config() -> dict[str, object]:
    """Public, non-sensitive configuration for the frontend."""
    return {
        "app": APP_NAME,
        "version": __version__,
        "spotify_configured": bool(SPOTIFY_CLIENT_ID),
    }


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return _html("index.html")


@app.get("/display", include_in_schema=False)
def display() -> FileResponse:
    return _html("index.html")


@app.get("/remote", include_in_schema=False)
def remote() -> FileResponse:
    return _html("remote.html")


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> FileResponse:
    return FileResponse(STATIC_DIR / "favicon.svg", media_type="image/svg+xml")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=False)
