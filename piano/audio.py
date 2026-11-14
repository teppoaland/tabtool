"""Audio for PianoCapture: one cached source per URL, mono slices per window.

The download itself is TabTool's proven yt-dlp wrapper
(``app.pipeline.audio_source``); this module only adds the piano tool's cache
layout and the mono slice used by both the analyser and the player.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from app.pipeline.audio_source import (
    download_youtube,
    ensure_ffmpeg,
    fetch_youtube_details,
    probe_duration,
)

from piano import config


def source_key(value: str) -> str:
    return hashlib.sha1(str(value).strip().encode("utf-8")).hexdigest()[:12]


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=creationflags,
    )
    if result.returncode != 0:
        tail = (result.stderr or result.stdout or "").strip().splitlines()[-8:]
        raise RuntimeError(
            f"Command failed ({result.returncode}): {' '.join(command)}\n"
            + "\n".join(tail)
        )
    return result


def slice_wav(
    source: str | Path,
    target: str | Path,
    start: float = 0.0,
    length: float = 0.0,
) -> float:
    """Write a mono 44.1 kHz WAV slice and return its duration in seconds."""
    ensure_ffmpeg()
    src = Path(source)
    dst = Path(target)
    dst.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(src),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "44100",
        "-c:a",
        "pcm_s16le",
    ]
    if start and float(start) > 0:
        command += ["-ss", f"{float(start):.3f}"]
    if length and float(length) > 0:
        command += ["-t", f"{float(length):.3f}"]
    command.append(str(dst))
    _run(command)
    return probe_duration(dst)


def _read_meta(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _write_meta(path: Path, meta: dict) -> dict:
    path.write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return meta


def prepare_source(url_or_path: str) -> dict:
    """Download a YouTube URL once (or accept a local file) and cache it.

    Returns the source metadata dict; ``wav`` names the cached mono file under
    ``data_piano/sources``. Repeats are cheap: no second download.
    """
    raw = str(url_or_path or "").strip()
    if not raw:
        raise ValueError("Anna YouTube-linkki tai äänitiedoston polku.")

    if raw.startswith(("http://", "https://")):
        key = source_key(raw)
        meta_path = config.SOURCES_DIR / f"{key}.json"
        wav_path = config.SOURCES_DIR / f"{key}.wav"
        meta = _read_meta(meta_path)
        if meta and wav_path.exists():
            return meta

        config.SOURCES_DIR.mkdir(parents=True, exist_ok=True)
        try:
            details = fetch_youtube_details(raw)
            title = details.title or "YouTube audio"
            artist = details.artist
            channel = details.channel
        except Exception:
            # Metadata is nice to have; the download decides if the URL works.
            title, artist, channel = "YouTube audio", "", ""

        downloaded = Path(download_youtube(raw, config.SOURCES_DIR))
        duration = probe_duration(downloaded)
        slice_wav(downloaded, wav_path, 0.0, min(duration, config.MAX_SOURCE_SECONDS))
        try:
            if downloaded.resolve() != wav_path.resolve():
                downloaded.unlink()
        except OSError:
            pass
        meta = {
            "source_type": "youtube",
            "url": raw,
            "title": title,
            "artist": artist,
            "channel": channel,
            "duration": probe_duration(wav_path),
            "wav": wav_path.name,
        }
        return _write_meta(meta_path, meta)

    path = Path(raw).expanduser()
    if not path.exists():
        raise FileNotFoundError(path)
    key = source_key(str(path.resolve()))
    meta_path = config.SOURCES_DIR / f"local-{key}.json"
    wav_path = config.SOURCES_DIR / f"local-{key}.wav"
    meta = _read_meta(meta_path)
    if meta and wav_path.exists():
        return meta

    config.SOURCES_DIR.mkdir(parents=True, exist_ok=True)
    duration = slice_wav(
        path, wav_path, 0.0, min(probe_duration(path), config.MAX_SOURCE_SECONDS)
    )
    return _write_meta(
        meta_path,
        {
            "source_type": "local",
            "url": str(path.resolve()),
            "title": path.stem,
            "artist": "",
            "channel": "",
            "duration": duration,
            "wav": wav_path.name,
        },
    )


def source_wav(meta: dict) -> Path:
    return config.SOURCES_DIR / str(meta["wav"])


def probe_window(source: Path, probe_seconds: float) -> Path:
    """Write the beginning of the source into ``tmp`` for the analyser."""
    config.TMP_DIR.mkdir(parents=True, exist_ok=True)
    target = config.TMP_DIR / f"probe-{source_key(str(source))}-{int(probe_seconds)}.wav"
    slice_wav(source, target, 0.0, probe_seconds)
    return target
