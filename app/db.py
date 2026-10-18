"""SQLite persistence for AI TabTool.

Everything lives inside the private ``data/`` directory. Paths are stored
relative to ``DATA_DIR`` so the folder can be moved without breaking tabs.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

import app.config as config

SCHEMA = """
CREATE TABLE IF NOT EXISTS tracks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    artist TEXT NOT NULL DEFAULT '',
    source_type TEXT NOT NULL,
    source_ref TEXT NOT NULL,
    fingerprint TEXT NOT NULL,
    audio_path TEXT,
    duration_seconds REAL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_tracks_fingerprint ON tracks(fingerprint);

CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    track_id INTEGER NOT NULL REFERENCES tracks(id) ON DELETE CASCADE,
    status TEXT NOT NULL,
    stage TEXT NOT NULL,
    progress REAL NOT NULL DEFAULT 0,
    cache_key TEXT,
    tab_id TEXT,
    cached INTEGER NOT NULL DEFAULT 0,
    error TEXT,
    options_json TEXT NOT NULL DEFAULT '{}',
    warnings_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_jobs_created ON jobs(created_at DESC);

CREATE TABLE IF NOT EXISTS tabs (
    id TEXT PRIMARY KEY,
    track_id INTEGER NOT NULL REFERENCES tracks(id) ON DELETE CASCADE,
    cache_key TEXT NOT NULL UNIQUE,
    directory TEXT NOT NULL,
    title TEXT NOT NULL,
    artist TEXT NOT NULL DEFAULT '',
    bpm REAL NOT NULL DEFAULT 0,
    tuning TEXT NOT NULL DEFAULT 'standard',
    time_signature TEXT NOT NULL DEFAULT '4/4',
    measure_count INTEGER NOT NULL DEFAULT 0,
    note_count INTEGER NOT NULL DEFAULT 0,
    audio_path TEXT NOT NULL DEFAULT '',
    meta_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_tabs_created ON tabs(created_at DESC);

CREATE TABLE IF NOT EXISTS oauth_tokens (
    provider TEXT PRIMARY KEY,
    access_token TEXT NOT NULL,
    refresh_token TEXT NOT NULL DEFAULT '',
    token_type TEXT NOT NULL DEFAULT 'Bearer',
    scope TEXT NOT NULL DEFAULT '',
    expires_at REAL NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""

_initialized: set[str] = set()
_UNSET = object()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id() -> str:
    return uuid.uuid4().hex


def db_path() -> Path:
    return Path(config.DATA_DIR) / "tabtool.sqlite3"


@contextmanager
def connection() -> Iterator[sqlite3.Connection]:
    """Open a short-lived connection; commit on success, roll back on error."""
    Path(config.DATA_DIR).mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path()), timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """Create the schema once per database file (idempotent, cheap to call)."""
    path = db_path()
    if str(path) in _initialized:
        return
    Path(config.DATA_DIR).mkdir(parents=True, exist_ok=True)
    with connection() as conn:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.executescript(SCHEMA)
    _initialized.add(str(path))


def create_job(
    *,
    job_id: str,
    track_id: int,
    options: dict[str, Any],
    status: str = "queued",
    stage: str = "queued",
    progress: float = 0.0,
    cache_key: str | None = None,
    tab_id: str | None = None,
    cached: bool = False,
) -> dict[str, Any]:
    init_db()
    now = utc_now()
    with connection() as conn:
        conn.execute(
            """
            INSERT INTO jobs
                (id, track_id, status, stage, progress, cache_key, tab_id,
                 cached, error, options_json, warnings_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, '[]', ?, ?)
            """,
            (
                job_id,
                track_id,
                status,
                stage,
                float(progress),
                cache_key,
                tab_id,
                1 if cached else 0,
                json.dumps(options, sort_keys=True),
                now,
                now,
            ),
        )
    job = get_job(job_id)
    if job is None:  # pragma: no cover - defensive
        raise RuntimeError(f"Job {job_id} disappeared after insert")
    return job


def update_job(
    job_id: str,
    *,
    status: str | object = _UNSET,
    stage: str | object = _UNSET,
    progress: float | object = _UNSET,
    tab_id: str | None | object = _UNSET,
    cached: bool | object = _UNSET,
    error: str | None | object = _UNSET,
    warnings: list[str] | object = _UNSET,
) -> dict[str, Any] | None:
    fields: dict[str, Any] = {}
    if status is not _UNSET:
        fields["status"] = status
    if stage is not _UNSET:
        fields["stage"] = stage
    if progress is not _UNSET:
        fields["progress"] = float(progress)  # type: ignore[arg-type]
    if tab_id is not _UNSET:
        fields["tab_id"] = tab_id
    if cached is not _UNSET:
        fields["cached"] = 1 if cached else 0
    if error is not _UNSET:
        fields["error"] = error
    if warnings is not _UNSET:
        fields["warnings_json"] = json.dumps(warnings)
    if not fields:
        return get_job(job_id)
    fields["updated_at"] = utc_now()
    assignments = ", ".join(f"{name} = ?" for name in fields)
    with connection() as conn:
        conn.execute(
            f"UPDATE jobs SET {assignments} WHERE id = ?",
            (*fields.values(), job_id),
        )
    return get_job(job_id)


_JOB_SELECT = """
SELECT j.*, t.title AS title, t.artist AS artist,
       t.source_type AS source_type, t.source_ref AS source_ref
FROM jobs j
JOIN tracks t ON t.id = j.track_id
"""


def get_job(job_id: str) -> dict[str, Any] | None:
    init_db()
    with connection() as conn:
        row = conn.execute(_JOB_SELECT + " WHERE j.id = ?", (job_id,)).fetchone()
    return _job_row(row) if row else None


def list_jobs(limit: int = 20) -> list[dict[str, Any]]:
    init_db()
    limit = max(1, min(int(limit), 200))
    with connection() as conn:
        rows = conn.execute(
            _JOB_SELECT + " ORDER BY j.created_at DESC, j.rowid DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [_job_row(row) for row in rows]


def find_cached_tab(cache_key: str) -> dict[str, Any] | None:
    init_db()
    with connection() as conn:
        row = conn.execute(
            "SELECT * FROM tabs WHERE cache_key = ?", (cache_key,)
        ).fetchone()
    return _tab_row(row) if row else None


def create_tab(
    *,
    tab_id: str,
    track_id: int,
    cache_key: str,
    directory: str,
    title: str,
    artist: str,
    bpm: float,
    tuning: str,
    time_signature: str,
    measure_count: int,
    note_count: int,
    audio_path: str,
    meta: dict[str, Any],
) -> dict[str, Any]:
    init_db()
    with connection() as conn:
        conn.execute(
            """
            INSERT INTO tabs
                (id, track_id, cache_key, directory, title, artist, bpm, tuning,
                 time_signature, measure_count, note_count, audio_path,
                 meta_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                tab_id,
                track_id,
                cache_key,
                directory,
                title,
                artist,
                float(bpm),
                tuning,
                time_signature,
                int(measure_count),
                int(note_count),
                audio_path,
                json.dumps(meta, ensure_ascii=False),
                utc_now(),
            ),
        )
    tab = get_tab(tab_id)
    if tab is None:  # pragma: no cover - defensive
        raise RuntimeError(f"Tab {tab_id} disappeared after insert")
    return tab


def get_tab(tab_id: str) -> dict[str, Any] | None:
    init_db()
    with connection() as conn:
        row = conn.execute("SELECT * FROM tabs WHERE id = ?", (tab_id,)).fetchone()
    return _tab_row(row) if row else None


def update_tab_audio(
    tab_id: str,
    audio_path: str,
    meta: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Attach an existing private audio file to a tab."""
    tab = get_tab(tab_id)
    if tab is None:
        return None
    init_db()
    with connection() as conn:
        if meta is not None:
            conn.execute(
                "UPDATE tabs SET audio_path = ?, meta_json = ? WHERE id = ?",
                (
                    audio_path,
                    json.dumps(meta, ensure_ascii=False),
                    tab_id,
                ),
            )
        else:
            conn.execute(
                "UPDATE tabs SET audio_path = ? WHERE id = ?",
                (audio_path, tab_id),
            )
        conn.execute(
            "UPDATE tracks SET audio_path = ? WHERE id = ?",
            (audio_path, int(tab["track_id"])),
        )
    if meta is not None:
        try:
            directory = resolve_under_data(str(tab["directory"]))
            meta_path = directory / "meta.json"
            if meta_path.is_file():
                temporary = meta_path.with_name(meta_path.name + ".tmp")
                temporary.write_text(
                    json.dumps(meta, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
                temporary.replace(meta_path)
        except (OSError, ValueError):
            pass
    return get_tab(tab_id)


def update_tab_tempo(
    tab_id: str,
    bpm: float,
    meta: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Store a corrected tab tempo and update the cached metadata."""
    tab = get_tab(tab_id)
    if tab is None:
        return None
    init_db()
    with connection() as conn:
        if meta is not None:
            conn.execute(
                "UPDATE tabs SET bpm = ?, meta_json = ? WHERE id = ?",
                (float(bpm), json.dumps(meta, ensure_ascii=False), tab_id),
            )
        else:
            conn.execute(
                "UPDATE tabs SET bpm = ? WHERE id = ?",
                (float(bpm), tab_id),
            )
    if meta is not None:
        try:
            directory = resolve_under_data(str(tab["directory"]))
            meta_path = directory / "meta.json"
            if meta_path.is_file():
                temporary = meta_path.with_name(meta_path.name + ".tmp")
                temporary.write_text(
                    json.dumps(meta, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
                temporary.replace(meta_path)
        except (OSError, ValueError):
            pass
    return get_tab(tab_id)


def update_tab_sync(
    tab_id: str,
    drift: float,
    meta: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Store a manual tab/audio alignment factor (fraction of playback time)."""
    tab = get_tab(tab_id)
    if tab is None:
        return None
    if meta is None:
        meta = dict(tab.get("meta") or {})
    meta["sync_drift"] = float(drift)
    init_db()
    with connection() as conn:
        conn.execute(
            "UPDATE tabs SET meta_json = ? WHERE id = ?",
            (json.dumps(meta, ensure_ascii=False), tab_id),
        )
    try:
        directory = resolve_under_data(str(tab["directory"]))
        meta_path = directory / "meta.json"
        if meta_path.is_file():
            temporary = meta_path.with_name(meta_path.name + ".tmp")
            temporary.write_text(
                json.dumps(meta, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            temporary.replace(meta_path)
    except (OSError, ValueError):
        pass
    return get_tab(tab_id)


def delete_tab(tab_id: str) -> dict[str, Any] | None:
    """Remove a tab row (used when an explicit regenerate supersedes it)."""
    tab = get_tab(tab_id)
    if tab is None:
        return None
    with connection() as conn:
        conn.execute("DELETE FROM tabs WHERE id = ?", (tab_id,))
    return tab


def audio_reference_count(audio_path: str) -> int:
    """Count tabs and tracks that still point at ``audio_path``."""
    if not audio_path:
        return 0
    init_db()
    with connection() as conn:
        tabs = conn.execute(
            "SELECT COUNT(*) FROM tabs WHERE audio_path = ?", (audio_path,)
        ).fetchone()[0]
        tracks = conn.execute(
            "SELECT COUNT(*) FROM tracks WHERE audio_path = ?", (audio_path,)
        ).fetchone()[0]
    return int(tabs) + int(tracks)


def delete_tab_records(tab_id: str) -> dict[str, Any]:
    """Delete a tab, its jobs and any track rows left without references."""
    tab = get_tab(tab_id)
    if tab is None:
        return {"deleted": False, "track_ids": []}
    track_id = int(tab["track_id"])
    with connection() as conn:
        rows = conn.execute(
            "SELECT DISTINCT track_id FROM jobs WHERE tab_id = ? OR track_id = ?",
            (tab_id, track_id),
        ).fetchall()
        track_ids = {int(row["track_id"]) for row in rows}
        track_ids.add(track_id)
        conn.execute(
            "DELETE FROM jobs WHERE tab_id = ? OR track_id = ?",
            (tab_id, track_id),
        )
        conn.execute("DELETE FROM tabs WHERE id = ?", (tab_id,))
        removed: list[int] = []
        for candidate in sorted(track_ids):
            tab_count = int(
                conn.execute(
                    "SELECT COUNT(*) FROM tabs WHERE track_id = ?", (candidate,)
                ).fetchone()[0]
            )
            job_count = int(
                conn.execute(
                    "SELECT COUNT(*) FROM jobs WHERE track_id = ?", (candidate,)
                ).fetchone()[0]
            )
            if tab_count == 0 and job_count == 0:
                conn.execute("DELETE FROM tracks WHERE id = ?", (candidate,))
                removed.append(candidate)
    return {"deleted": True, "track_ids": removed}


def _time_signature_text(value: Any) -> str:
    if isinstance(value, (list, tuple)) and len(value) == 2:
        return f"{int(value[0])}/{int(value[1])}"
    text = str(value or "4/4").strip()
    return text or "4/4"


def import_tabs_from_disk() -> int:
    """Register tabs produced by the CLI (``data/tabs/<name>/meta.json``)."""
    init_db()
    tabs_root = Path(config.DATA_DIR) / "tabs"
    if not tabs_root.is_dir():
        return 0
    imported = 0
    for directory in sorted(tabs_root.iterdir()):
        if not directory.is_dir() or directory.name.startswith("."):
            continue
        meta_path = directory / "meta.json"
        if not meta_path.is_file():
            continue
        tab_id = directory.name
        if get_tab(tab_id) is not None:
            continue
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(meta, dict):
            continue
        try:
            relative_dir = to_data_relative(directory)
        except ValueError:
            continue

        title = str(meta.get("title") or directory.name)
        artist = str(meta.get("artist") or "")
        audio_path = ""
        if meta.get("audio_path"):
            try:
                audio_path = to_data_relative(str(meta["audio_path"]))
            except ValueError:
                audio_path = ""
        track_id = create_track(
            title=title,
            artist=artist,
            source_type=str(meta.get("source_type") or "local"),
            source_ref=str(meta.get("source") or relative_dir),
            fingerprint=f"import:{tab_id}",
            audio_path=audio_path or None,
            duration_seconds=meta.get("duration_seconds"),
        )
        try:
            create_tab(
                tab_id=tab_id,
                track_id=track_id,
                cache_key=f"import:{tab_id}",
                directory=relative_dir,
                title=title,
                artist=artist,
                bpm=float(meta.get("bpm") or 0.0),
                tuning=str(meta.get("tuning") or "standard"),
                time_signature=_time_signature_text(meta.get("time_signature")),
                measure_count=int(meta.get("measures") or 0),
                note_count=int(meta.get("tab_notes") or 0),
                audio_path=audio_path,
                meta=meta,
            )
        except (TypeError, ValueError):
            continue
        imported += 1
    return imported


def list_tabs(limit: int = 20) -> list[dict[str, Any]]:
    init_db()
    limit = max(1, min(int(limit), 200))
    with connection() as conn:
        rows = conn.execute(
            "SELECT * FROM tabs ORDER BY created_at DESC, rowid DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [_tab_row(row) for row in rows]


def get_setting(key: str, default: str | None = None) -> str | None:
    init_db()
    with connection() as conn:
        row = conn.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        ).fetchone()
    return row["value"] if row else default


def set_setting(key: str, value: str) -> None:
    init_db()
    with connection() as conn:
        conn.execute(
            """
            INSERT INTO settings (key, value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value,
                                           updated_at = excluded.updated_at
            """,
            (key, value, utc_now()),
        )


def data_root() -> Path:
    return Path(config.DATA_DIR).resolve()


def resolve_under_data(relative: str | Path) -> Path:
    """Resolve a stored path and refuse anything that escapes ``data/``."""
    root = data_root()
    target = (root / relative).resolve()
    if target != root and root not in target.parents:
        raise ValueError(f"Path escapes the data directory: {relative!r}")
    return target


def to_data_relative(path: str | Path) -> str:
    """Convert an absolute path under ``data/`` to a stored relative path."""
    root = data_root()
    resolved = Path(path).resolve()
    if resolved != root and root not in resolved.parents:
        raise ValueError(f"Path is outside the data directory: {path!r}")
    return resolved.relative_to(root).as_posix()


def _loads(value: Any, default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return default


def _job_row(row: sqlite3.Row) -> dict[str, Any]:
    data = dict(row)
    data["options"] = _loads(data.pop("options_json", "{}"), {})
    data["warnings"] = _loads(data.pop("warnings_json", "[]"), [])
    data["cached"] = bool(data.get("cached", 0))
    data.setdefault("title", "")
    data.setdefault("artist", "")
    return data


def _tab_row(row: sqlite3.Row) -> dict[str, Any]:
    data = dict(row)
    data["meta"] = _loads(data.pop("meta_json", "{}"), {})
    return data


def create_track(
    *,
    title: str,
    artist: str,
    source_type: str,
    source_ref: str,
    fingerprint: str,
    audio_path: str | None = None,
    duration_seconds: float | None = None,
) -> int:
    init_db()
    with connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO tracks
                (title, artist, source_type, source_ref, fingerprint,
                 audio_path, duration_seconds, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                title,
                artist,
                source_type,
                source_ref,
                fingerprint,
                audio_path,
                duration_seconds,
                utc_now(),
            ),
        )
        return int(cursor.lastrowid)


def update_track(
    track_id: int,
    *,
    title: str | object = _UNSET,
    artist: str | object = _UNSET,
    audio_path: str | None | object = _UNSET,
    duration_seconds: float | None | object = _UNSET,
) -> None:
    fields: dict[str, Any] = {}
    if title is not _UNSET:
        fields["title"] = title
    if artist is not _UNSET:
        fields["artist"] = artist
    if audio_path is not _UNSET:
        fields["audio_path"] = audio_path
    if duration_seconds is not _UNSET:
        fields["duration_seconds"] = duration_seconds
    if not fields:
        return
    assignments = ", ".join(f"{name} = ?" for name in fields)
    with connection() as conn:
        conn.execute(
            f"UPDATE tracks SET {assignments} WHERE id = ?",
            (*fields.values(), track_id),
        )


def get_track(track_id: int) -> dict[str, Any] | None:
    init_db()
    with connection() as conn:
        row = conn.execute("SELECT * FROM tracks WHERE id = ?", (track_id,)).fetchone()
    return dict(row) if row else None
