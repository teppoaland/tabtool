"""Prepare local or YouTube audio as a normalized WAV file."""

from __future__ import annotations

import hashlib
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AudioSource:
    path: Path
    duration: float
    source_type: str
    source_ref: str
    title: str
    artist: str = ""


_YOUTUBE_SUFFIX = re.compile(
    r"\s*[\(\[]\s*(?:official\s*(?:music\s*)?video|official\s*audio|"
    r"lyrics?|remaster(?:ed)?|hd|hq|4k|visualizer|audio)\s*[\)\]]\s*$",
    re.IGNORECASE,
)


def clean_youtube_title(value: str) -> str:
    """Drop common parenthesised YouTube suffixes, e.g. ``(Remastered)``."""
    original = str(value or "").strip()
    text = " ".join(original.split())
    previous = None
    while text and text != previous:
        previous = text
        text = _YOUTUBE_SUFFIX.sub("", text).strip(" -–—")
    return text or original


def slugify(value: str, fallback: str = "audio") -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)
    return (slug or fallback)[:80]


def ensure_ffmpeg() -> None:
    missing = [name for name in ("ffmpeg", "ffprobe") if shutil.which(name) is None]
    if missing:
        raise RuntimeError(
            f"Missing required executable(s): {', '.join(missing)}. "
            "Install FFmpeg and add it to PATH."
        )


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


def probe_duration(path: str | Path) -> float:
    result = _run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ]
    )
    try:
        return float(result.stdout.strip().splitlines()[0])
    except (ValueError, IndexError) as exc:
        raise RuntimeError(f"Could not read duration from {path}") from exc


def fetch_youtube_metadata(url: str) -> tuple[str, str]:
    """Return a cleaned video title and artist/uploader without downloading."""
    result = _run(
        [
            sys.executable,
            "-m",
            "yt_dlp",
            "--skip-download",
            "--no-playlist",
            "--print",
            "%(title)s",
            "--print",
            "%(artist)s",
            "--print",
            "%(uploader)s",
            url,
        ]
    )
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    title = clean_youtube_title(lines[0]) if lines else ""
    artist = ""
    for line in lines[1:]:
        if line and line.upper() != "NA":
            artist = line
            break
    return title, artist


def normalize_audio(
    input_path: str | Path,
    output_wav: str | Path,
    clip_seconds: float | None = None,
    start_seconds: float | None = None,
) -> float:
    ensure_ffmpeg()
    output = Path(output_wav)
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_path),
        "-vn",
        "-ac",
        "2",
        "-ar",
        "44100",
        "-c:a",
        "pcm_s16le",
    ]
    if start_seconds is not None and start_seconds > 0:
        command += ["-ss", str(float(start_seconds))]
    if clip_seconds is not None and clip_seconds > 0:
        command += ["-t", str(float(clip_seconds))]
    command.append(str(output))
    _run(command)
    return probe_duration(output)


def download_youtube(
    url: str,
    dest_dir: str | Path,
    clip_seconds: float | None = None,
    start_seconds: float | None = None,
) -> Path:
    ensure_ffmpeg()
    directory = Path(dest_dir)
    directory.mkdir(parents=True, exist_ok=True)
    slug = "yt-" + hashlib.sha1(url.encode("utf-8")).hexdigest()[:10]
    template = str(directory / f"{slug}.%(ext)s")
    result = _run(
        [
            sys.executable,
            "-m",
            "yt_dlp",
            "-x",
            "--audio-format",
            "wav",
            "--audio-quality",
            "0",
            "--no-playlist",
            "--print",
            "after_move:filepath",
            "-o",
            template,
            url,
        ]
    )
    printed = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    downloaded = Path(printed[-1]) if printed else None
    if downloaded is None or not downloaded.exists():
        candidates = sorted(
            directory.glob(f"{slug}.*"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        downloaded = candidates[0] if candidates else None
    if downloaded is None or not downloaded.exists():
        raise RuntimeError(f"yt-dlp did not produce an audio file for {url}")

    if (clip_seconds is not None and clip_seconds > 0) or (
        start_seconds is not None and start_seconds > 0
    ):
        clipped = directory / f"{slug}-clip.wav"
        normalize_audio(
            downloaded,
            clipped,
            clip_seconds=clip_seconds,
            start_seconds=start_seconds,
        )
        return clipped
    return downloaded


def prepare_audio(
    source: str,
    dest_dir: str | Path,
    clip_seconds: float | None = None,
    start_seconds: float | None = None,
    title: str | None = None,
) -> AudioSource:
    """Normalize a local file or download a URL into the private audio dir."""
    directory = Path(dest_dir)
    directory.mkdir(parents=True, exist_ok=True)
    source = source.strip()
    if source.startswith(("http://", "https://")):
        metadata_title = ""
        metadata_artist = ""
        try:
            metadata_title, metadata_artist = fetch_youtube_metadata(source)
        except Exception:
            metadata_title = ""
            metadata_artist = ""
        downloaded = download_youtube(
            source,
            directory,
            clip_seconds=clip_seconds,
            start_seconds=start_seconds,
        )
        output = directory / f"{slugify(downloaded.stem, 'youtube')}.wav"
        if downloaded.resolve() != output.resolve():
            duration = normalize_audio(
                downloaded,
                output,
                clip_seconds=clip_seconds,
                start_seconds=start_seconds,
            )
        else:
            duration = probe_duration(downloaded)
        return AudioSource(
            path=output if output.exists() else downloaded,
            duration=duration,
            source_type="youtube",
            source_ref=source,
            title=title or metadata_title or "YouTube audio",
            artist=metadata_artist,
        )

    input_path = Path(source).expanduser()
    if not input_path.exists():
        raise FileNotFoundError(input_path)
    output = directory / f"{slugify(input_path.stem, 'local-audio')}.wav"
    duration = normalize_audio(
        input_path,
        output,
        clip_seconds=clip_seconds,
        start_seconds=start_seconds,
    )
    return AudioSource(
        path=output,
        duration=duration,
        source_type="local",
        source_ref=str(input_path.resolve()),
        title=title or input_path.stem,
    )
