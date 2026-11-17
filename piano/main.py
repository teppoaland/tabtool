"""PianoCapture web app - a separate FastAPI app next to AI TabTool.

Run it with its own port (default 8020):

    .venv\\Scripts\\python.exe -m uvicorn piano.main:app --port 8020
"""

from __future__ import annotations

import asyncio
import shutil
import subprocess
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.background import BackgroundTask

from piano import __version__, audio, config, jobs, lan, pattern, pipeline, render, store, update

APP_NAME = "PianoCapture"

config.ensure_data_dirs()

app = FastAPI(
    title=APP_NAME,
    version=__version__,
    description="Turn a YouTube fragment into an 88-key piano view.",
)

STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


class AnalyzeRequest(BaseModel):
    url: str = Field(min_length=1, max_length=2048)
    probe_seconds: float | None = Field(default=None, ge=10.0, le=600.0)


class ProcessRequest(BaseModel):
    url: str = Field(min_length=1, max_length=2048)
    start: float = Field(ge=0.0)
    end: float = Field(gt=0.0)


class PieceUpdateRequest(BaseModel):
    """Only the display name is editable; audio and notes stay untouched."""

    artist: str | None = Field(default=None, max_length=200)
    title: str | None = Field(default=None, max_length=200)


def _validate_source(value: str) -> str:
    source = str(value or "").strip()
    if not source:
        raise HTTPException(status_code=422, detail="Anna YouTube-linkki.")
    if source.startswith(("http://", "https://")):
        return source
    if Path(source).expanduser().exists():
        return source
    raise HTTPException(
        status_code=422,
        detail="Anna YouTube-linkki (http/https) tai olemassa oleva tiedosto.",
    )


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(
        STATIC_DIR / "index.html",
        media_type="text/html",
        headers={"Cache-Control": "no-store"},
    )


@app.get("/favicon.svg", include_in_schema=False)
def favicon() -> FileResponse:
    return FileResponse(
        STATIC_DIR / "favicon.svg", media_type="image/svg+xml"
    )


@app.get("/api/piano/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "app": APP_NAME, "version": __version__}


@app.get("/api/piano/lan", tags=["system"])
def lan_info(request: Request) -> dict:
    """The LAN address a phone or tablet should open (None if unavailable)."""
    port = request.url.port or config.PORT
    url = lan.base_url(port)
    return {
        "ip": lan.lan_ip(),
        "port": port,
        "url": url,
        "qr": "/api/piano/lan/qr.svg" if url else None,
    }


@app.get("/api/piano/update", tags=["system"])
def update_info() -> dict:
    """Whether a newer PianoCapture release exists on GitHub (notify only)."""
    return update.status()


@app.get("/api/piano/lan/qr.svg", include_in_schema=False)
def lan_qr(request: Request) -> Response:
    port = request.url.port or config.PORT
    url = lan.base_url(port)
    if url is None:
        raise HTTPException(status_code=404, detail="LAN-osoitetta ei löytynyt.")
    return Response(
        content=lan.qr_svg(url),
        media_type="image/svg+xml",
        headers={"Cache-Control": "no-store"},
    )


@app.get("/api/piano/pieces/{piece_id}/qr.svg", include_in_schema=False)
def piece_qr(piece_id: str, request: Request) -> Response:
    """QR that opens this exact piece on a phone in front of the piano."""
    try:
        store.load_piece(piece_id)
    except (FileNotFoundError, ValueError):
        raise HTTPException(status_code=404, detail="Pätkää ei löytynyt.")
    port = request.url.port or config.PORT
    base = lan.base_url(port)
    if base is None:
        raise HTTPException(status_code=404, detail="LAN-osoitetta ei löytynyt.")
    url = f"{base}/?piece={piece_id}"
    return Response(
        content=lan.qr_svg(url, scale=5),
        media_type="image/svg+xml",
        headers={"Cache-Control": "no-store"},
    )


@app.post("/api/piano/analyze", tags=["pipeline"])
def analyze(request: AnalyzeRequest) -> dict:
    source = _validate_source(request.url)

    def work(progress):
        return pipeline.analyze_source(
            source, probe_seconds=request.probe_seconds, progress=progress
        )

    return jobs.submit("analyze", work)


@app.post("/api/piano/process", tags=["pipeline"])
def process(request: ProcessRequest) -> dict:
    source = _validate_source(request.url)

    def work(progress):
        return pipeline.process_window(
            source, request.start, request.end, progress=progress
        )

    return jobs.submit("process", work)


@app.get("/api/piano/jobs/{job_id}", tags=["pipeline"])
def job(job_id: str) -> dict:
    record = jobs.get(job_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Työtä ei löytynyt.")
    return record


@app.get("/api/piano/pieces", tags=["pieces"])
def pieces(limit: int = 20) -> list[dict]:
    return store.list_pieces(limit=limit)


@app.get("/api/piano/pieces/{piece_id}", tags=["pieces"])
def piece(piece_id: str) -> dict:
    try:
        record = store.load_piece(piece_id)
    except (FileNotFoundError, ValueError):
        raise HTTPException(status_code=404, detail="Pätkää ei löytynyt.")
    # Pieces made before v0.2 have no cycle; compute it once and keep it.
    if "cycle" not in record:
        try:
            record["cycle"] = pattern.find_cycle(
                store.piece_audio(piece_id),
                (record.get("window") or {}).get("duration"),
            )
        except (OSError, ValueError):
            record["cycle"] = None
        try:
            store.save_piece(record)
        except OSError:
            pass
    return record


@app.patch("/api/piano/pieces/{piece_id}", tags=["pieces"])
def rename_piece(piece_id: str, request: PieceUpdateRequest) -> dict:
    """Rename a generated guide so a messy YouTube title is readable.

    The first edit keeps the automatic title/artist in ``original_title`` /
    ``original_artist``; nothing else in the piece (audio, notes, window) is
    touched. Renaming does not reorder the list.
    """
    try:
        piece = store.load_piece(piece_id)
    except (FileNotFoundError, ValueError):
        raise HTTPException(status_code=404, detail="Pätkää ei löytynyt.")
    source = piece.setdefault("source", {})
    if request.artist is not None:
        artist = request.artist.strip()
        if artist != (source.get("artist") or ""):
            if source.get("artist") and "original_artist" not in source:
                source["original_artist"] = source["artist"]
            source["artist"] = artist
    if request.title is not None:
        title = request.title.strip()
        if not title:
            raise HTTPException(status_code=422, detail="Nimi ei voi olla tyhjä.")
        if title != (source.get("title") or ""):
            if source.get("title") and "original_title" not in source:
                source["original_title"] = source["title"]
            source["title"] = title
    store.save_piece(piece)
    return piece


@app.delete("/api/piano/pieces/{piece_id}", status_code=204, tags=["pieces"])
def delete_piece(piece_id: str) -> Response:
    """Delete a generated guide and its folder. Cannot be undone."""
    try:
        store.load_piece(piece_id)
        directory = store.piece_dir(piece_id)
    except (FileNotFoundError, ValueError):
        raise HTTPException(status_code=404, detail="Pätkää ei löytynyt.")
    try:
        shutil.rmtree(directory)
    except OSError as error:
        raise HTTPException(
            status_code=409, detail=f"Ohjetta ei voitu poistaa: {error}"
        )
    return Response(status_code=204)


@app.get("/api/piano/pieces/{piece_id}/audio", tags=["pieces"])
def piece_audio(piece_id: str) -> FileResponse:
    try:
        path = store.piece_audio(piece_id)
    except (FileNotFoundError, ValueError):
        raise HTTPException(status_code=404, detail="Ääntä ei löytynyt.")
    return FileResponse(
        path,
        media_type="audio/wav",
        filename=f"{piece_id}.wav",
        headers={"Cache-Control": "no-store"},
    )


@app.get("/api/piano/pieces/{piece_id}/audio.mp3", tags=["pieces"])
def piece_audio_mp3(piece_id: str) -> FileResponse:
    """The clip as MP3, cached next to the WAV (easy to copy to a phone)."""
    try:
        source = store.piece_audio(piece_id)
    except (FileNotFoundError, ValueError):
        raise HTTPException(status_code=404, detail="Ääntä ei löytynyt.")
    target = source.with_suffix(".mp3")
    if not target.exists():
        try:
            audio.to_mp3(source, target)
        except RuntimeError as error:
            raise HTTPException(
                status_code=500, detail=f"MP3-koodaus epäonnistui: {error}"
            )
    return FileResponse(
        target,
        media_type="audio/mpeg",
        filename=f"pianocapture-{piece_id}.mp3",
    )


@app.get("/api/piano/pieces/{piece_id}/guide.wav", tags=["pieces"])
def piece_guide_wav(piece_id: str, hand: str = "all", split: int = 60) -> FileResponse:
    """The transcribed notes as audio. ``hand=right|left`` drops the other hand."""
    try:
        piece = store.load_piece(piece_id)
        directory = store.piece_dir(piece_id)
    except (FileNotFoundError, ValueError):
        raise HTTPException(status_code=404, detail="Pätkää ei löytynyt.")
    boundary = max(21, min(108, int(split)))
    suffix = "" if hand not in ("left", "right") else f"-{hand}-{boundary}"
    target = directory / f"guide{suffix}.wav"
    if not target.exists():
        notes = render.filter_notes(piece.get("notes", []), hand, boundary)
        render.render_guide(
            notes,
            (piece.get("window") or {}).get("duration", 0.0),
            target,
        )
    return FileResponse(
        target,
        media_type="audio/wav",
        filename=f"pianocapture-{piece_id}{suffix}-guide.wav",
    )


@app.get("/api/piano/pieces/{piece_id}/guide.mp3", tags=["pieces"])
def piece_guide_mp3(piece_id: str, hand: str = "all", split: int = 60) -> FileResponse:
    """The guide as MP3; the hand filter matches the on-screen view."""
    try:
        piece = store.load_piece(piece_id)
        directory = store.piece_dir(piece_id)
    except (FileNotFoundError, ValueError):
        raise HTTPException(status_code=404, detail="Pätkää ei löytynyt.")
    boundary = max(21, min(108, int(split)))
    suffix = "" if hand not in ("left", "right") else f"-{hand}-{boundary}"
    mp3 = directory / f"guide{suffix}.mp3"
    if not mp3.exists():
        wav = directory / f"guide{suffix}.wav"
        if not wav.exists():
            notes = render.filter_notes(piece.get("notes", []), hand, boundary)
            render.render_guide(
                notes,
                (piece.get("window") or {}).get("duration", 0.0),
                wav,
            )
        try:
            audio.to_mp3(wav, mp3)
        except RuntimeError as error:
            raise HTTPException(
                status_code=500, detail=f"MP3-koodaus epäonnistui: {error}"
            )
    return FileResponse(
        mp3,
        media_type="audio/mpeg",
        filename=f"pianocapture-{piece_id}{suffix}-guide.mp3",
    )


@app.get("/api/piano/pieces/{piece_id}/midi", tags=["pieces"])
def piece_midi(piece_id: str, hand: str = "all", split: int = 60) -> FileResponse:
    """The (optionally hand-filtered) transcription as MIDI."""
    boundary = max(21, min(108, int(split)))
    suffix = "" if hand not in ("left", "right") else f"-{hand}-{boundary}"
    if suffix:
        try:
            piece = store.load_piece(piece_id)
            directory = store.piece_dir(piece_id)
        except (FileNotFoundError, ValueError):
            raise HTTPException(status_code=404, detail="Pätkää ei löytynyt.")
        path = directory / f"notes{suffix}.mid"
        if not path.exists():
            notes = render.filter_notes(piece.get("notes", []), hand, boundary)
            render.render_midi(notes, path)
        return FileResponse(
            path,
            media_type="audio/midi",
            filename=f"pianocapture-{piece_id}{suffix}.mid",
        )
    try:
        path = store.piece_midi(piece_id)
    except (FileNotFoundError, ValueError):
        path = None
    if path is None:
        raise HTTPException(status_code=404, detail="MIDIä ei löytynyt.")
    return FileResponse(path, media_type="audio/midi", filename=f"{piece_id}.mid")


def _cleanup_video_files(*paths: Path) -> None:
    for path in paths:
        try:
            path.unlink()
        except FileNotFoundError:
            pass


@app.post("/api/piano/video", tags=["pieces"])
async def convert_piano_video(request: Request):
    """Convert the browser's canvas recording (WebM) into an MP4."""
    payload = await request.body()
    if not payload:
        raise HTTPException(status_code=400, detail="Tyhjä video.")
    if len(payload) > 250 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Video on liian suuri.")
    try:
        audio.ensure_ffmpeg()
    except Exception as error:  # pragma: no cover - environment dependent
        raise HTTPException(
            status_code=500,
            detail=f"ffmpeg puuttuu: {error}",
        ) from error

    source = config.TMP_DIR / f"video-{uuid.uuid4().hex}.webm"
    target = source.with_suffix(".mp4")
    source.write_bytes(payload)

    def convert() -> None:
        command = [
            "ffmpeg",
            "-y",
            "-i",
            str(source),
            "-map",
            "0:v:0",
            "-map",
            "0:a?",
            "-vf",
            "scale=trunc(iw/2)*2:trunc(ih/2)*2",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "23",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-movflags",
            "+faststart",
            str(target),
        ]
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=300,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if result.returncode != 0:
            lines = (result.stderr or result.stdout or "").strip().splitlines()
            errors = [
                line
                for line in lines
                if any(
                    word in line.lower()
                    for word in ("error", "invalid", "failed", "could not")
                )
            ]
            detail = " | ".join((errors or lines)[-3:])
            raise RuntimeError(detail or "ffmpeg-virhe")

    try:
        await asyncio.to_thread(convert)
        if not target.exists() or target.stat().st_size == 0:
            raise RuntimeError("ffmpeg ei tuottanut videota.")
        return FileResponse(
            target,
            media_type="video/mp4",
            filename="PianoCapture.mp4",
            background=BackgroundTask(_cleanup_video_files, source, target),
        )
    except HTTPException:
        _cleanup_video_files(source, target)
        raise
    except Exception as error:
        _cleanup_video_files(source, target)
        raise HTTPException(
            status_code=500,
            detail=f"Videon muunnos epäonnistui: {error}",
        ) from error


if __name__ == "__main__":  # pragma: no cover - manual start
    import uvicorn

    uvicorn.run(app, host=config.HOST, port=config.PORT)
