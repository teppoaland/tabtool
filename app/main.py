"""AI TabTool FastAPI application.

Phase 2 exposes the job API, tab exports and the local audio stream. The
pipeline runs in a background worker (``app.jobs``), routes never call it
directly.
"""

from __future__ import annotations

import asyncio
import json
import queue
from pathlib import Path
from typing import AsyncIterator
from urllib.parse import urlparse

from fastapi import FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from app import __version__, db, jobs
from app.config import (
    APP_NAME,
    HOST,
    MAX_UPLOAD_MB,
    PORT,
    SPOTIFY_CLIENT_ID,
    STATIC_DIR,
    VERSION,
    ensure_data_dirs,
    is_loopback,
)
from app.pipeline.audio_source import slugify

ensure_data_dirs()

app = FastAPI(
    title=APP_NAME,
    version=VERSION,
    description="Local AI guitar tab generator and viewer.",
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

EXPORT_FORMATS: dict[str, tuple[str, str]] = {
    "gp5": ("tab.gp5", "application/octet-stream"),
    "musicxml": ("tab.musicxml", "application/vnd.recordare.musicxml+xml"),
    "midi": ("tab.mid", "audio/midi"),
}

DOWNLOAD_SUFFIX = {"gp5": ".gp5", "musicxml": ".musicxml", "midi": ".mid"}



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
        "max_upload_mb": MAX_UPLOAD_MB,
        "pipeline_version": jobs.PIPELINE_VERSION,
        "sources": ["upload", "local", "youtube"],
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


def _parse_options(raw: str) -> jobs.JobOptions:
    try:
        payload = json.loads(raw) if raw else {}
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=422, detail="options must be JSON") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=422, detail="options must be an object")
    try:
        return jobs.JobOptions.from_mapping(payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _is_youtube_url(url: str) -> bool:
    parsed = urlparse(url.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return False
    host = parsed.netloc.lower().split(":")[0]
    return host.endswith(("youtube.com", "youtu.be", "youtube-nocookie.com"))


def _sse(payload: object) -> bytes:
    return f"data: {json.dumps(payload)}\n\n".encode("utf-8")


@app.post("/api/jobs", status_code=202, tags=["jobs"])
async def create_job(
    request: Request,
    file: UploadFile | None = File(default=None),
    youtube_url: str = Form(default=""),
    local_path: str = Form(default=""),
    title: str = Form(default=""),
    artist: str = Form(default=""),
    regenerate: bool = Form(default=False),
    options: str = Form(default="{}"),
) -> dict[str, object]:
    """Queue a tab generation job from an upload, a YouTube URL or a local file."""
    parsed = _parse_options(options)
    youtube_url = youtube_url.strip()
    local_path = local_path.strip()
    has_file = bool(file is not None and file.filename)
    provided = sum((has_file, bool(youtube_url), bool(local_path)))
    if provided != 1:
        raise HTTPException(
            status_code=422,
            detail="Provide exactly one source: file, youtube_url or local_path",
        )

    if has_file and file is not None:
        try:
            path, digest, _size = jobs.save_upload(file.file, file.filename or "audio")
        except ValueError as exc:
            status = 413 if "limit" in str(exc) else 415
            raise HTTPException(status_code=status, detail=str(exc)) from exc
        return jobs.submit_job(
            source_type="upload",
            source_ref=db.to_data_relative(path),
            title=jobs.clean_title(title or file.filename),
            artist=artist.strip(),
            fingerprint=jobs.upload_fingerprint(digest),
            audio_path=path,
            options=parsed,
            regenerate=regenerate,
        )

    if youtube_url:
        if not _is_youtube_url(youtube_url):
            raise HTTPException(
                status_code=422, detail="youtube_url must be a YouTube link"
            )
        return jobs.submit_job(
            source_type="youtube",
            source_ref=youtube_url,
            title=jobs.clean_title(title, "YouTube audio"),
            artist=artist.strip(),
            fingerprint=jobs.youtube_fingerprint(youtube_url),
            audio_path=None,
            options=parsed,
            regenerate=regenerate,
        )

    if not is_loopback(request.client.host if request.client else None):
        raise HTTPException(
            status_code=403, detail="local_path is only allowed from localhost"
        )
    path = Path(local_path).expanduser()
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Local audio file not found")
    if path.suffix.lower() not in jobs.AUDIO_EXTENSIONS:
        raise HTTPException(status_code=415, detail="Unsupported audio format")
    return jobs.submit_job(
        source_type="local",
        source_ref=str(path.resolve()),
        title=jobs.clean_title(title or path.name),
        artist=artist.strip(),
        fingerprint=jobs.local_fingerprint(path),
        audio_path=None,
        options=parsed,
        regenerate=regenerate,
    )


@app.get("/api/jobs", tags=["jobs"])
def list_jobs(limit: int = Query(default=20, ge=1, le=200)) -> list[dict[str, object]]:
    return db.list_jobs(limit)


@app.get("/api/jobs/{job_id}", tags=["jobs"])
def get_job(job_id: str) -> dict[str, object]:
    job = db.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Unknown job")
    return job


@app.get("/api/jobs/{job_id}/events", tags=["jobs"])
async def job_events(job_id: str) -> StreamingResponse:
    """Server-sent events with the job snapshot after every stage change."""
    snapshot = db.get_job(job_id)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="Unknown job")

    async def stream() -> AsyncIterator[bytes]:
        subscription = jobs.subscribe(job_id)
        try:
            current = db.get_job(job_id)
            if current is not None:
                yield _sse(current)
            if current is not None and current["status"] in {"ready", "failed"}:
                return
            while True:
                try:
                    payload = await asyncio.to_thread(subscription.get, True, 10.0)
                except queue.Empty:
                    yield b": keep-alive\n\n"
                    continue
                yield _sse(payload)
                if payload is not None and payload["status"] in {"ready", "failed"}:
                    return
        finally:
            jobs.unsubscribe(job_id, subscription)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )


def _tab_summary(tab: dict[str, object]) -> dict[str, object]:
    keys = ("id", "title", "artist", "bpm", "measure_count", "note_count", "created_at")
    return {key: tab.get(key) for key in keys}


def _load_tab(tab_id: str) -> dict[str, object] | None:
    tab = db.get_tab(tab_id)
    if tab is None:
        db.import_tabs_from_disk()
        tab = db.get_tab(tab_id)
    return tab


@app.get("/api/tabs", tags=["tabs"])
def list_tabs(limit: int = Query(default=20, ge=1, le=200)) -> list[dict[str, object]]:
    db.import_tabs_from_disk()
    return [_tab_summary(tab) for tab in db.list_tabs(limit)]


@app.get("/api/tabs/{tab_id}", tags=["tabs"])
def get_tab(tab_id: str) -> dict[str, object]:
    tab = _load_tab(tab_id)
    if tab is None:
        raise HTTPException(status_code=404, detail="Unknown tab")
    return tab


def _tab_file(tab_id: str, fmt: str) -> tuple[dict[str, object], Path]:
    if fmt not in EXPORT_FORMATS:
        raise HTTPException(status_code=404, detail="Unknown format")
    tab = _load_tab(tab_id)
    if tab is None:
        raise HTTPException(status_code=404, detail="Unknown tab")
    default_name = EXPORT_FORMATS[fmt][0]
    meta = tab.get("meta") or {}
    files = meta.get("files") if isinstance(meta, dict) else None
    stored_name = files.get(fmt) if isinstance(files, dict) else None
    filename = Path(str(stored_name or default_name)).name
    try:
        path = db.resolve_under_data(Path(str(tab["directory"])) / filename)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Tab file not found") from exc
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Tab file not found")
    return tab, path


@app.get("/api/tabs/{tab_id}/score/{fmt}", tags=["tabs"])
def tab_score(tab_id: str, fmt: str) -> FileResponse:
    """Inline score data for alphaTab (no attachment headers)."""
    _tab, path = _tab_file(tab_id, fmt)
    return FileResponse(
        path,
        media_type=EXPORT_FORMATS[fmt][1],
        headers={"Cache-Control": "no-store"},
    )


@app.get("/api/tabs/{tab_id}/export/{fmt}", tags=["tabs"])
def tab_export(tab_id: str, fmt: str) -> FileResponse:
    tab, path = _tab_file(tab_id, fmt)
    name = slugify(str(tab["title"]), "tab") + DOWNLOAD_SUFFIX[fmt]
    return FileResponse(
        path,
        media_type=EXPORT_FORMATS[fmt][1],
        filename=name,
        headers={"Cache-Control": "no-store"},
    )


@app.get("/api/tabs/{tab_id}/audio", tags=["tabs"])
def tab_audio(tab_id: str) -> FileResponse:
    """Stream the normalized WAV. FileResponse handles Range requests."""
    tab = _load_tab(tab_id)
    if tab is None or not tab.get("audio_path"):
        raise HTTPException(status_code=404, detail="Audio not found")
    try:
        path = db.resolve_under_data(str(tab["audio_path"]))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Audio not found") from exc
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Audio not found")
    return FileResponse(
        path,
        media_type="audio/wav",
        headers={"Cache-Control": "no-store", "Accept-Ranges": "bytes"},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=False)
