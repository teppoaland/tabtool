"""PianoCapture web app - a separate FastAPI app next to AI TabTool.

Run it with its own port (default 8020):

    .venv\\Scripts\\python.exe -m uvicorn piano.main:app --port 8020
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from piano import __version__, config, jobs, pipeline, store

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
        return store.load_piece(piece_id)
    except (FileNotFoundError, ValueError):
        raise HTTPException(status_code=404, detail="Pätkää ei löytynyt.")


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


@app.get("/api/piano/pieces/{piece_id}/midi", tags=["pieces"])
def piece_midi(piece_id: str) -> FileResponse:
    try:
        path = store.piece_midi(piece_id)
    except (FileNotFoundError, ValueError):
        path = None
    if path is None:
        raise HTTPException(status_code=404, detail="MIDIä ei löytynyt.")
    return FileResponse(path, media_type="audio/midi", filename=f"{piece_id}.mid")


if __name__ == "__main__":  # pragma: no cover - manual start
    import uvicorn

    uvicorn.run(app, host=config.HOST, port=config.PORT)
