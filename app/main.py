"""AI TabTool FastAPI application.

Phase 2 exposes the job API, tab exports and the local audio stream. The
pipeline runs in a background worker (``app.jobs``), routes never call it
directly.
"""

from __future__ import annotations

import asyncio
import json
import os
import queue
import shutil
from dataclasses import replace
from pathlib import Path
from typing import AsyncIterator
from urllib.parse import urlparse

from fastapi import FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from app import __version__, db, jobs, library, tab_download, tab_import
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
from app.tuning import describe_key

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


def _import_tab_payload(raw: bytes, filename: str) -> dict[str, object]:
    """Map tab import failures to HTTP errors."""
    try:
        return tab_import.import_tab_bytes(raw, filename)
    except tab_import.TabTooLarge as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    except tab_import.UnsupportedTab as exc:
        raise HTTPException(status_code=415, detail=str(exc)) from exc
    except tab_import.TabParseError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 - reported to the user
        raise HTTPException(
            status_code=422, detail=f"Tab import failed: {exc}"
        ) from exc


def _download_tab(url: str) -> dict[str, object]:
    """Fetch a GP5/MusicXML link on the server and import it."""
    try:
        raw, filename = tab_download.download_tab_bytes(url)
    except tab_download.TabDownloadTooLarge as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    except tab_download.TabDownloadError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _import_tab_payload(raw, filename)


def _queue_audio_job(
    tab: dict[str, object],
    youtube_url: str,
    options: jobs.JobOptions,
) -> dict[str, object]:
    """Download YouTube audio and attach it to an already imported tab."""
    audio_options = replace(
        options, audio_only=True, attach_tab_id=str(tab["id"])
    )
    job = jobs.submit_job(
        source_type="youtube",
        source_ref=youtube_url,
        title=str(tab.get("title") or ""),
        artist=str(tab.get("artist") or ""),
        fingerprint=jobs.youtube_fingerprint(youtube_url),
        audio_path=None,
        options=audio_options,
        tab_id=str(tab["id"]),
    )
    job["tab"] = _tab_summary(tab)
    return job


def _sse(payload: object) -> bytes:
    return f"data: {json.dumps(payload)}\n\n".encode("utf-8")


@app.post("/api/jobs", status_code=202, tags=["jobs"])
async def create_job(
    request: Request,
    file: UploadFile | None = File(default=None),
    youtube_url: str = Form(default=""),
    local_path: str = Form(default=""),
    gp5_url: str = Form(default=""),
    title: str = Form(default=""),
    artist: str = Form(default=""),
    regenerate: bool = Form(default=False),
    options: str = Form(default="{}"),
) -> dict[str, object]:
    """Queue a tab generation job from an upload, a YouTube URL or a local file."""
    parsed = _parse_options(options)
    youtube_url = youtube_url.strip()
    local_path = local_path.strip()
    gp5_url = gp5_url.strip()

    if gp5_url:
        # A ready-made GP5 wins over AI transcription: import it and only
        # download/attach the YouTube audio (and optional MP3 copy).
        has_upload = bool(file is not None and file.filename)
        if has_upload or local_path:
            raise HTTPException(
                status_code=422,
                detail="GP5-linkki toimii vain YouTube-linkin kanssa.",
            )
        if not youtube_url:
            raise HTTPException(
                status_code=422,
                detail="Liitä YouTube-linkki, jotta GP5-tabiin saadaan audio.",
            )
        if not _is_youtube_url(youtube_url):
            raise HTTPException(
                status_code=422, detail="youtube_url must be a YouTube link"
            )
        tab = _download_tab(gp5_url)
        return _queue_audio_job(tab, youtube_url, parsed)

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
                if payload is None:
                    return
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
    keys = (
        "id",
        "title",
        "artist",
        "bpm",
        "measure_count",
        "note_count",
        "created_at",
        "title_override",
        "original_title",
        "locked",
        "archived",
    )
    summary = {key: tab.get(key) for key in keys}
    meta = tab.get("meta")
    summary["source_type"] = (
        meta.get("source_type") if isinstance(meta, dict) else ""
    )
    # Which YouTube upload the tab was built from: different uploads of the
    # same song have different edits, so the GP5 may only fit one of them.
    summary["channel"] = (
        str(meta.get("youtube_channel") or "") if isinstance(meta, dict) else ""
    )
    tuning_key = str(tab.get("tuning") or "")
    label = str(meta.get("tuning_label") or "") if isinstance(meta, dict) else ""
    override = (
        str(meta.get("tuning_override") or "") if isinstance(meta, dict) else ""
    )
    summary["tuning"] = tuning_key
    summary["tuning_override"] = override
    summary["tuning_label"] = override or label or describe_key(tuning_key)
    variant_list = meta.get("variants") if isinstance(meta, dict) else None
    variants = []
    if isinstance(variant_list, list):
        for entry in variant_list:
            if not isinstance(entry, dict):
                continue
            play = (
                entry.get("playability")
                if isinstance(entry.get("playability"), dict)
                else {}
            )
            variants.append(
                {
                    "id": entry.get("id"),
                    "label": entry.get("label"),
                    "track": entry.get("track"),
                    "score": play.get("score"),
                }
            )
    summary["variants"] = variants
    summary["default_variant"] = (
        str(meta.get("default_variant") or "") if isinstance(meta, dict) else ""
    )
    summary["selected_variant"] = (
        str(meta.get("selected_variant") or "") if isinstance(meta, dict) else ""
    )
    summary["variant_finalized"] = (
        bool(meta.get("variant_finalized")) if isinstance(meta, dict) else False
    )
    return summary


def _format_seconds(value: float) -> str:
    total = max(0, int(round(float(value))))
    return f"{total // 60}:{total % 60:02d}"


def _load_tab(tab_id: str) -> dict[str, object] | None:
    tab = db.get_tab(tab_id)
    if tab is None:
        db.import_tabs_from_disk()
        tab = db.get_tab(tab_id)
    return tab


# A locked tab is read-only (v1.70): the lock protects every stored setting
# (name, tuning, archive flag, BPM, SYNC/SIIRTO, attached audio), not only
# deletion. The library editor is the single place that may clear the lock.
_LOCKED_DETAIL = "Tab is locked. Unlock it in the library first."


def _require_unlocked(tab: dict[str, object]) -> None:
    if tab.get("locked"):
        raise HTTPException(status_code=409, detail=_LOCKED_DETAIL)


@app.get("/api/tabs", tags=["tabs"])
def list_tabs(limit: int = Query(default=20, ge=1, le=200)) -> list[dict[str, object]]:
    db.import_tabs_from_disk()
    return [_tab_summary(tab) for tab in db.list_tabs(limit)]


@app.post("/api/tabs/import", tags=["tabs"])
async def import_tab(
    file: UploadFile = File(...),
    youtube_url: str = Form(default=""),
    options: str = Form(default="{}"),
) -> dict[str, object]:
    """Import a GP5/MusicXML tab and optionally attach YouTube audio.

    Without ``youtube_url`` the tab is imported alone (no audio). With it,
    the response is the audio job (``status``/``stage``/``tab_id``) and the
    audio is attached when the job finishes.
    """
    youtube_url = youtube_url.strip()
    parsed = _parse_options(options)
    if youtube_url and not _is_youtube_url(youtube_url):
        raise HTTPException(
            status_code=422, detail="youtube_url must be a YouTube link"
        )
    raw = await file.read()
    tab = _import_tab_payload(raw, file.filename or "tab.gp5")
    if youtube_url:
        return _queue_audio_job(tab, youtube_url, parsed)
    return _tab_summary(tab)


@app.post("/api/tabs/import-url", tags=["tabs"])
def import_tab_from_url(url: str = Form(...)) -> dict[str, object]:
    """Download a GP5/MusicXML link on the server and import it."""
    tab = _download_tab(url)
    return _tab_summary(tab)


@app.delete("/api/tabs/{tab_id}", tags=["tabs"])
def delete_tab(tab_id: str) -> dict[str, object]:
    """Delete a tab with its audio and stems; the MP3 copy is kept."""
    tab = _load_tab(tab_id)
    if tab is not None:
        _require_unlocked(tab)
    try:
        return library.delete_tab_data(tab_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="Unknown tab") from exc


@app.post("/api/tabs/{tab_id}/library", tags=["tabs"])
def tab_library(
    tab_id: str,
    title: str | None = Form(default=None),
    locked: bool | None = Form(default=None),
    archived: bool | None = Form(default=None),
    tuning: str | None = Form(default=None),
    tuning_clear: bool = Form(default=False),
) -> dict[str, object]:
    """Rename, lock, archive or annotate a tab without touching its tab data."""
    tab = _load_tab(tab_id)
    if tab is None:
        raise HTTPException(status_code=404, detail="Unknown tab")
    # A locked tab is read-only. Only an explicit unlock (locked=false) may
    # write, and it may carry the new name/tuning/archive flag in the same
    # request, so one save can unlock and edit at once.
    if tab.get("locked") and locked is not False:
        raise HTTPException(status_code=409, detail=_LOCKED_DETAIL)
    meta = None
    if tuning_clear:
        meta = dict(tab.get("meta") or {})
        meta.pop("tuning_override", None)
    elif tuning is not None:
        value = str(tuning).strip()
        if value:
            meta = dict(tab.get("meta") or {})
            meta["tuning_override"] = value
    if meta is not None:
        db.update_tab_meta(tab_id, meta)
        tab = db.get_tab(tab_id) or tab
    changes: dict[str, object] = {}
    if title is not None:
        changes["title_override"] = title
    if locked is not None:
        changes["locked"] = locked
    if archived is not None:
        changes["archived"] = archived
    updated = db.update_tab_library(tab_id, **changes)
    if updated is None:  # pragma: no cover - deleted between the two calls
        raise HTTPException(status_code=404, detail="Unknown tab")
    return _tab_summary(updated)


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


@app.post("/api/tabs/{tab_id}/section", tags=["tabs"])
def tab_section(
    tab_id: str,
    start_seconds: float = Form(...),
    clip_seconds: float = Form(...),
) -> dict[str, object]:
    """Create a new tab job for one section of an existing tab's audio."""
    tab = _load_tab(tab_id)
    if tab is None:
        raise HTTPException(status_code=404, detail="Unknown tab")
    if not tab.get("audio_path"):
        raise HTTPException(status_code=422, detail="Tab has no audio")
    try:
        path = db.resolve_under_data(str(tab["audio_path"]))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Audio not found") from exc
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Audio not found")

    meta = tab.get("meta") if isinstance(tab.get("meta"), dict) else {}
    payload = dict(meta.get("options") or {})
    payload["start_seconds"] = max(0.0, float(start_seconds))
    payload["clip_seconds"] = max(1.0, min(900.0, float(clip_seconds)))
    try:
        options = jobs.JobOptions.from_mapping(payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    start = float(options.start_seconds or 0.0)
    length = int(round(float(options.clip_seconds or 0.0)))
    title = f"{tab['title']} [{_format_seconds(start)} +{length}s]"
    return jobs.submit_job(
        source_type="local",
        source_ref=str(path.resolve()),
        title=jobs.clean_title(title, str(tab.get("title") or "Tab")),
        artist=str(tab.get("artist") or ""),
        fingerprint=jobs.local_fingerprint(path),
        audio_path=path,
        options=options,
    )


@app.post("/api/tabs/{tab_id}/attach-audio", tags=["tabs"])
def tab_attach_audio(tab_id: str) -> dict[str, object]:
    """Attach the audio of a same-named tab to a tab that has no audio."""
    target = _load_tab(tab_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Unknown tab")
    _require_unlocked(target)
    if target.get("audio_path"):
        return _tab_summary(target)

    title = str(target.get("title") or "").strip().lower()
    artist = str(target.get("artist") or "").strip().lower()
    candidates = [
        tab
        for tab in db.list_tabs(200)
        if tab.get("id") != tab_id and tab.get("audio_path")
    ]
    matches = [
        tab
        for tab in candidates
        if str(tab.get("title") or "").strip().lower() == title
    ]
    if artist:
        artist_matches = [
            tab
            for tab in matches
            if str(tab.get("artist") or "").strip().lower() == artist
        ]
        if artist_matches:
            matches = artist_matches
    source = matches[0] if matches else None
    if source is None:
        raise HTTPException(
            status_code=404,
            detail="Samannimistä audiota ei löytynyt. Tuo AI-tabi samasta kappaleesta ensin.",
        )

    source_audio = str(source["audio_path"])
    try:
        source_path = db.resolve_under_data(source_audio)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Audio not found") from exc
    if not source_path.is_file():
        raise HTTPException(status_code=404, detail="Audio not found")

    meta = dict(target.get("meta") or {})
    meta["audio_path"] = source_audio
    source_meta = source.get("meta") or {}
    if isinstance(source_meta, dict) and source_meta.get("duration_seconds"):
        meta["duration_seconds"] = source_meta["duration_seconds"]
    meta["audio_source_tab"] = source.get("id")

    updated = db.update_tab_audio(tab_id, source_audio, meta)
    if updated is None:
        raise HTTPException(status_code=404, detail="Unknown tab")
    summary = _tab_summary(updated)
    summary["source_bpm"] = source.get("bpm")
    summary["source_id"] = source.get("id")
    return summary


@app.post("/api/tabs/{tab_id}/tempo", tags=["tabs"])
def tab_tempo(tab_id: str, bpm: float = Form(...)) -> dict[str, object]:
    """Rewrite a GP5 tab tempo so the tab matches the song's real BPM."""
    tab = _load_tab(tab_id)
    if tab is None:
        raise HTTPException(status_code=404, detail="Unknown tab")
    _require_unlocked(tab)
    if not 20.0 <= float(bpm) <= 400.0:
        raise HTTPException(status_code=422, detail="BPM must be between 20 and 400")
    meta = dict(tab.get("meta") or {})
    files = meta.get("files") if isinstance(meta.get("files"), dict) else {}
    gp5_name = files.get("gp5") if files else None
    if not gp5_name:
        raise HTTPException(
            status_code=422,
            detail="Tempo voidaan asettaa vain GP5-tabille.",
        )
    try:
        directory = db.resolve_under_data(str(tab["directory"]))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Tab file not found") from exc
    path = directory / Path(str(gp5_name)).name
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Tab file not found")

    try:
        import guitarpro

        song = guitarpro.parse(str(path), encoding="utf-8")
        # GP5 stores an integer tempo; the fractional part is kept in the
        # metadata and applied as a playback correction by the viewer.
        notated_tempo = int(float(bpm) + 0.5)
        song.tempo = notated_tempo
        temporary = path.with_name(path.name + ".tmp")
        guitarpro.write(song, str(temporary), encoding="utf-8")
        temporary.replace(path)
    except Exception as exc:  # noqa: BLE001 - reported to the user
        raise HTTPException(
            status_code=422, detail=f"Tempon asetus epäonnistui: {exc}"
        ) from exc

    meta["bpm"] = float(bpm)
    meta["gp5_tempo"] = notated_tempo
    meta["tempo_override"] = float(bpm)
    updated = db.update_tab_tempo(tab_id, float(bpm), meta)
    if updated is None:
        raise HTTPException(status_code=404, detail="Unknown tab")
    return _tab_summary(updated)


@app.post("/api/tabs/{tab_id}/sync", tags=["tabs"])
def tab_sync(
    tab_id: str,
    drift: float = Form(...),
    offset_bars: float = Form(0.0),
) -> dict[str, object]:
    """Store manual tab alignment (playback drift and whole-bar shift)."""
    tab = _load_tab(tab_id)
    if tab is None:
        raise HTTPException(status_code=404, detail="Unknown tab")
    _require_unlocked(tab)
    value = float(drift)
    if not -0.1 <= value <= 0.1:
        raise HTTPException(
            status_code=422,
            detail="SYNC must be between -10 and 10 percent",
        )
    bars = float(offset_bars)
    if not -64.0 <= bars <= 64.0:
        raise HTTPException(
            status_code=422,
            detail="SIIRTO must be between -64 and 64 bars",
        )
    meta = dict(tab.get("meta") or {})
    meta["sync_offset_bars"] = bars
    updated = db.update_tab_sync(tab_id, value, meta)
    if updated is None:
        raise HTTPException(status_code=404, detail="Unknown tab")
    summary = _tab_summary(updated)
    summary["meta"] = updated.get("meta") or {}
    return summary


@app.post("/api/tabs/{tab_id}/variant", tags=["tabs"])
def tab_variant(tab_id: str, variant: str = Form(...)) -> dict[str, object]:
    """Keep one generated fingering variant and delete the others (v1.72)."""
    from app.pipeline.export_gp5 import export_gp5
    from app.pipeline.export_midi import export_midi
    from app.pipeline.export_musicxml import export_musicxml
    from app.pipeline.variant_store import restore_document

    tab = _load_tab(tab_id)
    if tab is None:
        raise HTTPException(status_code=404, detail="Unknown tab")
    _require_unlocked(tab)
    meta = dict(tab.get("meta") or {})
    variants = [
        entry for entry in (meta.get("variants") or []) if isinstance(entry, dict)
    ]
    if not variants:
        raise HTTPException(
            status_code=422, detail="Tässä tabissa ei ole valittavia versioita."
        )
    if meta.get("variant_finalized"):
        if meta.get("selected_variant") == variant:
            return _tab_summary(tab)
        raise HTTPException(status_code=422, detail="Versio on jo valittu.")
    chosen = next((entry for entry in variants if entry.get("id") == variant), None)
    if chosen is None:
        raise HTTPException(status_code=422, detail=f"Tuntematon versio: {variant}")

    directory = db.resolve_under_data(str(tab["directory"]))
    source_path = directory / str(chosen["source"])
    if not source_path.is_file():
        raise HTTPException(status_code=404, detail="Version tiedostoa ei löytynyt.")
    snapshot = json.loads(source_path.read_text(encoding="utf-8"))
    document = restore_document(snapshot)
    # The user may have adjusted TAB BPM after generation; finalize at the
    # current BPM so the chosen variant keeps the correct tempo.
    document = replace(document, bpm=float(meta.get("bpm") or document.bpm))

    for name, exporter in (
        ("tab.gp5", export_gp5),
        ("tab.musicxml", export_musicxml),
        ("tab.mid", export_midi),
    ):
        final = directory / name
        temporary = directory / (name + ".tmp")
        exporter(document, temporary)
        os.replace(temporary, final)

    variants_dir = directory / "variants"
    if variants_dir.is_dir():
        shutil.rmtree(variants_dir)

    meta["selected_variant"] = chosen["id"]
    meta["variant_finalized"] = True
    meta["variants"] = [chosen]
    meta["playability"] = chosen.get("playability")
    updated = db.update_tab_finalize(tab_id, meta, document.note_count)
    if updated is None:  # pragma: no cover - deleted between the two calls
        raise HTTPException(status_code=404, detail="Unknown tab")
    return _tab_summary(updated)


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
