"""Archive the existing library into TABTOOL_EXTERNAL_DIR (one-shot)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import config, db  # noqa: E402
from app.external_store import archive_external, archive_mp3  # noqa: E402


def _archive_audio(tab: dict[str, object]) -> Path | None:
    meta = tab.get("meta") if isinstance(tab.get("meta"), dict) else {}
    if str(meta.get("source_type") or "") != "youtube":
        return None
    audio = str(tab.get("audio_path") or "")
    if not audio:
        return None
    try:
        path = db.resolve_under_data(audio)
    except ValueError:
        return None
    if not path.is_file():
        return None
    return archive_external(
        path, "audio", str(tab.get("artist") or ""), str(tab.get("title") or "")
    )


def _archive_tab(tab: dict[str, object]) -> Path | None:
    meta = tab.get("meta") if isinstance(tab.get("meta"), dict) else {}
    if str(meta.get("source_type") or "") != "import":
        return None
    files = meta.get("files") if isinstance(meta.get("files"), dict) else {}
    name = files.get("gp5") or files.get("musicxml")
    if not name:
        return None
    try:
        path = db.resolve_under_data(
            Path(str(tab.get("directory") or "")) / Path(str(name)).name
        )
    except (ValueError, OSError):
        return None
    if not path.is_file():
        return None
    return archive_external(
        path, "tabs", str(tab.get("artist") or ""), str(tab.get("title") or "")
    )


def _archive_mp3(tab: dict[str, object], seen: set[str]) -> Path | None:
    meta = tab.get("meta") if isinstance(tab.get("meta"), dict) else {}
    if str(meta.get("source_type") or "") != "youtube":
        return None
    audio = str(tab.get("audio_path") or "")
    if not audio:
        return None
    try:
        path = db.resolve_under_data(audio)
    except ValueError:
        return None
    if not path.is_file():
        return None
    key = str(path.resolve())
    if key in seen:
        return None
    seen.add(key)
    return archive_mp3(
        path, str(tab.get("artist") or ""), str(tab.get("title") or "")
    )


def main() -> int:
    db.import_tabs_from_disk()
    tabs = db.list_tabs(500)
    archived = 0
    seen_mp3: set[str] = set()
    for tab in tabs:
        results = (
            _archive_audio(tab),
            _archive_tab(tab),
            _archive_mp3(tab, seen_mp3),
        )
        for result in results:
            if result is not None:
                archived += 1
                print(result)
    print(f"Archived {archived} file(s) into {config.EXTERNAL_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
