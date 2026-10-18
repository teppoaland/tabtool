"""Job queue, worker, cache and progress events for tab generation.

The heavy pipeline is imported lazily so the web app can boot without
TensorFlow, Demucs or Basic Pitch being loaded.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import queue
import shutil
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO, Callable, Mapping

import app.config as config
from app import db
from app.pipeline.model import get_tuning, parse_time_signature

LOGGER = logging.getLogger("tabtool.jobs")

# Bump when the pipeline output changes so old cache entries are not reused.
PIPELINE_VERSION = "1"

SOURCE_TYPES = ("upload", "local", "youtube")
AUDIO_EXTENSIONS = {
    ".mp3",
    ".wav",
    ".flac",
    ".m4a",
    ".aac",
    ".ogg",
    ".opus",
    ".aiff",
    ".aif",
    ".webm",
}
MODELS = ("htdemucs_6s", "htdemucs", "htdemucs_ft")
STEMS = ("guitar", "other", "bass", "vocals", "drums")
GRIDS = (4, 8, 16, 32, 64)

STAGE_QUEUED = "queued"
STAGE_DOWNLOADING = "downloading"
STAGE_SEPARATING = "separating"
STAGE_TRANSCRIBING = "transcribing"
STAGE_BUILDING = "building"
STAGE_READY = "ready"
STAGE_FAILED = "failed"

STAGE_PROGRESS = {
    STAGE_QUEUED: 0.0,
    STAGE_DOWNLOADING: 0.05,
    STAGE_SEPARATING: 0.2,
    STAGE_TRANSCRIBING: 0.55,
    STAGE_BUILDING: 0.85,
    STAGE_READY: 1.0,
}


def _as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off", ""}:
        return False
    raise ValueError(f"Invalid boolean value: {value!r}")


def _as_float(value: Any, default: float | None, name: str) -> float | None:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a number") from exc


def _as_int(value: Any, default: int, name: str) -> int:
    if value is None or value == "":
        return default
    try:
        return int(float(value))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be an integer") from exc


@dataclass(frozen=True)
class JobOptions:
    """Validated pipeline options stored with every job and tab."""

    separate: bool = True
    model: str = "htdemucs_6s"
    stem: str = "guitar"
    device: str = "cpu"
    bpm: float | None = None
    time_signature: str = "4/4"
    grid: int = 16
    tuning: str = "standard"
    max_fret: int = 24
    max_span: int = 5
    clip_seconds: float | None = None
    start_seconds: float | None = None
    onset_threshold: float = 0.5
    frame_threshold: float = 0.3
    min_note_length_ms: float = 58.0
    min_frequency: float = 80.0
    max_frequency: float = 1200.0

    @classmethod
    def from_mapping(cls, values: Mapping[str, Any] | None) -> "JobOptions":
        raw = dict(values or {})
        separate = _as_bool(raw.get("separate"), True)
        model = str(raw.get("model") or "htdemucs_6s").strip()
        if model not in MODELS:
            raise ValueError(f"Unknown model: {model}. Known: {', '.join(MODELS)}")
        stem = str(raw.get("stem") or "guitar").strip()
        if stem not in STEMS:
            raise ValueError(f"Unknown stem: {stem}. Known: {', '.join(STEMS)}")
        device = str(raw.get("device") or "cpu").strip().lower()
        if device not in {"cpu", "cuda"}:
            raise ValueError("Device must be cpu or cuda")

        bpm = _as_float(raw.get("bpm"), None, "bpm")
        if bpm is not None and not 20.0 <= bpm <= 400.0:
            raise ValueError("BPM must be between 20 and 400")

        time_signature = str(raw.get("time_signature") or "4/4").strip()
        numerator, denominator = parse_time_signature(time_signature)

        grid = _as_int(raw.get("grid"), 16, "grid")
        if grid not in GRIDS:
            raise ValueError(f"Grid must be one of {GRIDS}")

        tuning = get_tuning(str(raw.get("tuning") or "standard")).key

        max_fret = _as_int(raw.get("max_fret"), 24, "max_fret")
        if not 1 <= max_fret <= 36:
            raise ValueError("max_fret must be between 1 and 36")
        max_span = _as_int(raw.get("max_span"), 5, "max_span")
        if not 1 <= max_span <= 12:
            raise ValueError("max_span must be between 1 and 12")

        clip_seconds = _as_float(raw.get("clip_seconds"), None, "clip_seconds")
        if clip_seconds is not None and not 1.0 <= clip_seconds <= 900.0:
            raise ValueError("clip_seconds must be between 1 and 900")
        start_seconds = _as_float(raw.get("start_seconds"), None, "start_seconds")
        if start_seconds is not None and start_seconds < 0:
            raise ValueError("start_seconds must be positive")

        onset_threshold = _as_float(raw.get("onset_threshold"), 0.5, "onset_threshold")
        frame_threshold = _as_float(raw.get("frame_threshold"), 0.3, "frame_threshold")
        for name, value in (
            ("onset_threshold", onset_threshold),
            ("frame_threshold", frame_threshold),
        ):
            if value is None or not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be between 0 and 1")

        min_note_length_ms = _as_float(
            raw.get("min_note_length_ms"), 58.0, "min_note_length_ms"
        )
        min_frequency = _as_float(raw.get("min_frequency"), 80.0, "min_frequency")
        max_frequency = _as_float(raw.get("max_frequency"), 1200.0, "max_frequency")
        if min_note_length_ms is None or min_note_length_ms < 10.0:
            raise ValueError("min_note_length_ms must be at least 10")
        if min_frequency is None or min_frequency <= 0:
            raise ValueError("min_frequency must be positive")
        if max_frequency is None or max_frequency <= min_frequency:
            raise ValueError("max_frequency must be greater than min_frequency")

        return cls(
            separate=separate,
            model=model,
            stem=stem,
            device=device,
            bpm=bpm,
            time_signature=f"{numerator}/{denominator}",
            grid=grid,
            tuning=tuning,
            max_fret=max_fret,
            max_span=max_span,
            clip_seconds=clip_seconds,
            start_seconds=start_seconds,
            onset_threshold=onset_threshold,
            frame_threshold=frame_threshold,
            min_note_length_ms=min_note_length_ms,
            min_frequency=min_frequency,
            max_frequency=max_frequency,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "separate": self.separate,
            "model": self.model,
            "stem": self.stem,
            "device": self.device,
            "bpm": self.bpm,
            "time_signature": self.time_signature,
            "grid": self.grid,
            "tuning": self.tuning,
            "max_fret": self.max_fret,
            "max_span": self.max_span,
            "clip_seconds": self.clip_seconds,
            "start_seconds": self.start_seconds,
            "onset_threshold": self.onset_threshold,
            "frame_threshold": self.frame_threshold,
            "min_note_length_ms": self.min_note_length_ms,
            "min_frequency": self.min_frequency,
            "max_frequency": self.max_frequency,
        }


def save_upload(
    stream: BinaryIO,
    filename: str,
    max_bytes: int | None = None,
) -> tuple[Path, str, int]:
    """Store an uploaded audio file under ``data/audio/uploads``.

    Returns ``(path, sha256, size)``. The file name from the browser is only
    used for its extension; the stored name is generated.
    """
    safe_name = Path(filename or "").name
    suffix = Path(safe_name).suffix.lower()
    if suffix not in AUDIO_EXTENSIONS:
        raise ValueError(f"Unsupported audio format: {suffix or safe_name!r}")
    limit = max_bytes if max_bytes is not None else config.MAX_UPLOAD_MB * 1024 * 1024
    upload_dir = Path(config.DATA_DIR) / "audio" / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    target = upload_dir / f"{db.new_id()}{suffix}"
    digest = hashlib.sha256()
    size = 0
    try:
        with target.open("wb") as handle:
            while True:
                chunk = stream.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > limit:
                    raise ValueError(
                        f"Upload exceeds the {limit // (1024 * 1024)} MB limit"
                    )
                digest.update(chunk)
                handle.write(chunk)
        if size == 0:
            raise ValueError("Uploaded file is empty")
    except Exception:
        target.unlink(missing_ok=True)
        raise
    return target, digest.hexdigest(), size


def upload_fingerprint(sha256: str) -> str:
    return f"upload:{sha256}"


def youtube_fingerprint(url: str) -> str:
    return f"youtube:{url.strip()}"


def local_fingerprint(path: Path) -> str:
    stat = path.stat()
    return f"local:{path.resolve()}:{stat.st_size}:{stat.st_mtime_ns}"


def cache_key(fingerprint: str, options: Mapping[str, Any]) -> str:
    """Stable key for the same audio + settings + pipeline version."""
    payload = json.dumps(
        {
            "fingerprint": fingerprint,
            "pipeline": PIPELINE_VERSION,
            "options": dict(options),
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def clean_title(value: str | None, fallback: str = "Tab") -> str:
    """Turn a file name or URL title into a readable tab title."""
    text = str(value or "").strip()
    if text:
        name = Path(text).name
        text = Path(name).stem if "." in name else name
    text = " ".join(text.replace("_", " ").split())
    return (text or fallback)[:120]


def submit_job(
    *,
    source_type: str,
    source_ref: str,
    title: str,
    artist: str = "",
    fingerprint: str,
    audio_path: Path | None,
    duration_seconds: float | None = None,
    options: JobOptions,
    regenerate: bool = False,
) -> dict[str, Any]:
    """Create a track + job row and queue it (unless the cache already has it)."""
    if source_type not in SOURCE_TYPES:
        raise ValueError(f"Unknown source type: {source_type}")
    db.init_db()
    options_dict = options.as_dict()
    track_id = db.create_track(
        title=title,
        artist=artist,
        source_type=source_type,
        source_ref=source_ref,
        fingerprint=fingerprint,
        audio_path=db.to_data_relative(audio_path) if audio_path else None,
        duration_seconds=duration_seconds,
    )
    key = cache_key(fingerprint, options_dict)
    cached_tab = None if regenerate else db.find_cached_tab(key)
    job_id = db.new_id()
    if cached_tab is not None:
        return db.create_job(
            job_id=job_id,
            track_id=track_id,
            options=options_dict,
            status=STAGE_READY,
            stage=STAGE_READY,
            progress=1.0,
            cache_key=key,
            tab_id=cached_tab["id"],
            cached=True,
        )
    job = db.create_job(
        job_id=job_id,
        track_id=track_id,
        options=options_dict,
        status=STAGE_QUEUED,
        stage=STAGE_QUEUED,
        progress=0.0,
        cache_key=key,
    )
    get_manager().submit(job_id)
    return job


class JobManager:
    """Single background worker plus in-memory progress subscriptions."""

    def __init__(self) -> None:
        self._queue: queue.Queue[str | None] = queue.Queue()
        self._subscribers: dict[str, list[queue.Queue]] = {}
        self._lock = threading.Lock()
        self._thread = threading.Thread(
            target=self._loop, name="tabtool-jobs", daemon=True
        )
        self._started = False

    def start(self) -> None:
        with self._lock:
            if self._started:
                return
            self._started = True
            self._thread.start()

    def submit(self, job_id: str) -> None:
        self.start()
        self._queue.put(job_id)

    def subscribe(self, job_id: str) -> queue.Queue:
        subscription: queue.Queue = queue.Queue()
        with self._lock:
            self._subscribers.setdefault(job_id, []).append(subscription)
        return subscription

    def unsubscribe(self, job_id: str, subscription: queue.Queue) -> None:
        with self._lock:
            subscribers = self._subscribers.get(job_id)
            if not subscribers:
                return
            if subscription in subscribers:
                subscribers.remove(subscription)
            if not subscribers:
                self._subscribers.pop(job_id, None)

    def publish(self, job_id: str) -> None:
        snapshot = db.get_job(job_id)
        with self._lock:
            subscribers = list(self._subscribers.get(job_id, []))
        for subscription in subscribers:
            subscription.put(snapshot)

    def _loop(self) -> None:
        while True:
            job_id = self._queue.get()
            try:
                if job_id is None:
                    return
                process_job(job_id)
            except Exception:  # noqa: BLE001 - worker must never die
                LOGGER.exception("Unhandled error while processing job %s", job_id)
            finally:
                self._queue.task_done()


_manager: JobManager | None = None
_manager_lock = threading.Lock()


def get_manager() -> JobManager:
    """Return the process-wide manager, starting its worker on first use."""
    global _manager
    if _manager is None:
        with _manager_lock:
            if _manager is None:
                manager = JobManager()
                manager.start()
                _manager = manager
    return _manager


def subscribe(job_id: str) -> queue.Queue:
    return get_manager().subscribe(job_id)


def unsubscribe(job_id: str, subscription: queue.Queue) -> None:
    get_manager().unsubscribe(job_id, subscription)


def publish(job_id: str) -> None:
    get_manager().publish(job_id)


def run_pipeline(
    job: dict[str, Any],
    options: JobOptions,
    report: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Run the audio-to-tab pipeline and return everything needed for export."""
    from app.pipeline.audio_source import prepare_audio
    from app.pipeline.build import build_document
    from app.pipeline.fretboard import assign_fretboard
    from app.pipeline.quantize import quantize_notes
    from app.pipeline.separate import separate_stems
    from app.pipeline.tempo import detect_tempo
    from app.pipeline.transcribe import transcribe_audio

    notify = report or (lambda stage: None)

    if job["source_type"] == "upload":
        source = str(db.resolve_under_data(job["source_ref"]))
    else:
        source = job["source_ref"]

    notify(STAGE_DOWNLOADING)
    audio = prepare_audio(
        source,
        Path(config.DATA_DIR) / "audio",
        clip_seconds=options.clip_seconds,
        start_seconds=options.start_seconds,
        title=job["title"] or None,
    )

    tuning = get_tuning(options.tuning)
    stems: dict[str, Path] = {}
    if options.separate:
        notify(STAGE_SEPARATING)
        stems = separate_stems(
            audio.path,
            Path(config.DATA_DIR) / "stems",
            model=options.model,
            device=options.device,
        )
        stem_name = options.stem
        if stem_name not in stems:
            stem_name = "guitar" if "guitar" in stems else "other"
        if stem_name not in stems:
            stem_name = next(iter(stems))
        transcription_path = stems[stem_name]
        tempo_path = stems.get("drums", audio.path)
    else:
        stem_name = "full-mix"
        transcription_path = audio.path
        tempo_path = audio.path

    notify(STAGE_TRANSCRIBING)
    if options.bpm:
        bpm = float(options.bpm)
        raw_bpm = bpm
    else:
        tempo = detect_tempo(tempo_path)
        bpm = tempo.bpm
        raw_bpm = tempo.raw_bpm

    notes = transcribe_audio(
        transcription_path,
        onset_threshold=options.onset_threshold,
        frame_threshold=options.frame_threshold,
        min_note_length_ms=options.min_note_length_ms,
        min_frequency=options.min_frequency,
        max_frequency=options.max_frequency,
    )
    quantized = quantize_notes(
        notes,
        bpm,
        time_signature=options.time_signature,
        grid_division=options.grid,
        total_duration_seconds=audio.duration,
    )

    notify(STAGE_BUILDING)
    tab_notes, fret_warnings = assign_fretboard(
        quantized.notes,
        tuning,
        max_fret=options.max_fret,
        max_span=options.max_span,
    )
    warnings = list(quantized.warnings) + list(fret_warnings)
    document = build_document(
        title=job["title"] or audio.title,
        artist=job["artist"],
        bpm=bpm,
        time_signature=options.time_signature,
        tuning=tuning,
        tab_notes=tab_notes,
        measure_count=quantized.measure_count,
        max_fret=options.max_fret,
        grid_division=options.grid,
        source_audio=str(audio.path),
        warnings=warnings,
    )
    return {
        "audio": audio,
        "document": document,
        "warnings": warnings,
        "bpm": bpm,
        "raw_bpm": raw_bpm,
        "stem": stem_name,
        "detected_notes": len(notes),
        "tab_notes": len(tab_notes),
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    os.replace(temporary, path)


def _progress(job_id: str, stage: str) -> None:
    db.update_job(
        job_id,
        status="running",
        stage=stage,
        progress=STAGE_PROGRESS.get(stage, 0.0),
    )
    publish(job_id)


def process_job(job_id: str) -> None:
    """Worker entry point: run the pipeline and store the tab atomically."""
    job = db.get_job(job_id)
    if job is None or job["status"] in {STAGE_READY, STAGE_FAILED}:
        return

    pending_dir = Path(config.DATA_DIR) / "tabs" / f".pending-{job_id}"
    try:
        options = JobOptions.from_mapping(job["options"])
        result = run_pipeline(job, options, lambda stage: _progress(job_id, stage))

        audio = result["audio"]
        document = result["document"]
        tab_id = db.new_id()

        from app.pipeline.export_gp5 import export_gp5
        from app.pipeline.export_midi import export_midi
        from app.pipeline.export_musicxml import export_musicxml

        pending_dir.mkdir(parents=True, exist_ok=False)
        gp5_path = export_gp5(document, pending_dir / "tab.gp5")
        xml_path = export_musicxml(document, pending_dir / "tab.musicxml")
        midi_path = export_midi(document, pending_dir / "tab.mid")

        meta = {
            "title": document.title,
            "artist": document.artist,
            "source": audio.source_ref,
            "source_type": audio.source_type,
            "duration_seconds": audio.duration,
            "bpm": result["bpm"],
            "raw_bpm": result["raw_bpm"],
            "time_signature": list(document.time_signature),
            "tuning": document.tuning.key,
            "grid_division": options.grid,
            "pipeline_version": PIPELINE_VERSION,
            "options": options.as_dict(),
            "model": options.model if options.separate else None,
            "stem": result["stem"],
            "detected_notes": result["detected_notes"],
            "tab_notes": result["tab_notes"],
            "measures": len(document.measures),
            "warnings": result["warnings"],
            "job_id": job_id,
            "created_at": db.utc_now(),
            "files": {
                "gp5": gp5_path.name,
                "musicxml": xml_path.name,
                "midi": midi_path.name,
            },
        }
        _write_json(pending_dir / "meta.json", meta)

        final_dir = Path(config.DATA_DIR) / "tabs" / tab_id
        if final_dir.exists():
            raise RuntimeError(f"Tab directory already exists: {final_dir}")
        os.replace(pending_dir, final_dir)

        cache_value = job["cache_key"] or f"uncached:{job_id}"
        previous = db.find_cached_tab(cache_value)
        if previous is not None:
            db.delete_tab(previous["id"])
            try:
                previous_dir = db.resolve_under_data(previous["directory"])
            except ValueError:
                previous_dir = None
            tabs_root = (Path(config.DATA_DIR) / "tabs").resolve()
            if previous_dir is not None and previous_dir.parent == tabs_root:
                shutil.rmtree(previous_dir, ignore_errors=True)

        db.create_tab(
            tab_id=tab_id,
            track_id=int(job["track_id"]),
            cache_key=cache_value,
            directory=db.to_data_relative(final_dir),
            title=document.title,
            artist=document.artist,
            bpm=result["bpm"],
            tuning=document.tuning.key,
            time_signature=(
                f"{document.time_signature[0]}/{document.time_signature[1]}"
            ),
            measure_count=len(document.measures),
            note_count=document.note_count,
            audio_path=db.to_data_relative(audio.path),
            meta=meta,
        )
        db.update_track(
            int(job["track_id"]),
            audio_path=db.to_data_relative(audio.path),
            duration_seconds=audio.duration,
        )
        db.update_job(
            job_id,
            status=STAGE_READY,
            stage=STAGE_READY,
            progress=1.0,
            tab_id=tab_id,
            warnings=result["warnings"],
            error=None,
        )
        publish(job_id)
    except Exception as exc:  # noqa: BLE001 - reported through the job row
        LOGGER.exception("Job %s failed", job_id)
        shutil.rmtree(pending_dir, ignore_errors=True)
        message = str(exc).strip() or exc.__class__.__name__
        db.update_job(
            job_id,
            status=STAGE_FAILED,
            stage=STAGE_FAILED,
            error=message[:2000],
        )
        publish(job_id)





