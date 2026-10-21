"""Add the YouTube channel to tabs that were created before v1.67.

Older tabs stored only the video URL. This script re-reads the channel with
yt-dlp and writes it into the tab metadata, so the library shows
``YT: <kanava>`` for existing songs too. Nothing is downloaded or re-rendered.

Usage:
    .venv\\Scripts\\python.exe scripts\\backfill_youtube_channel.py --dry-run
    .venv\\Scripts\\python.exe scripts\\backfill_youtube_channel.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import db  # noqa: E402
from app.pipeline.audio_source import fetch_youtube_details  # noqa: E402


def _youtube_url(tab: dict) -> str:
    meta = tab.get("meta") if isinstance(tab.get("meta"), dict) else {}
    if str(meta.get("source_type") or "") != "youtube":
        return ""
    url = str(meta.get("source") or "").strip()
    return url if url.startswith(("http://", "https://")) else ""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Only list the tabs")
    args = parser.parse_args()

    updated: list[dict[str, str]] = []
    skipped: list[dict[str, str]] = []
    failed: list[dict[str, str]] = []

    for tab in db.list_tabs(200):
        meta = tab.get("meta") if isinstance(tab.get("meta"), dict) else {}
        if str(meta.get("source_type") or "") != "youtube":
            continue
        url = _youtube_url(tab)
        if not url:
            skipped.append({"tab_id": str(tab["id"]), "reason": "no url"})
            continue
        if str(meta.get("youtube_channel") or "").strip():
            skipped.append({"tab_id": str(tab["id"]), "reason": "already set"})
            continue
        if args.dry_run:
            updated.append({"tab_id": str(tab["id"]), "url": url, "channel": "(dry run)"})
            continue
        try:
            details = fetch_youtube_details(url)
        except Exception as exc:  # noqa: BLE001 - report and continue
            failed.append({"tab_id": str(tab["id"]), "error": str(exc)})
            continue
        if not details.channel:
            failed.append({"tab_id": str(tab["id"]), "error": "channel not found"})
            continue
        meta["youtube_channel"] = details.channel
        audio_path = str(tab.get("audio_path") or "") or str(meta.get("audio_path") or "")
        db.update_tab_audio(str(tab["id"]), audio_path, meta)
        updated.append(
            {
                "tab_id": str(tab["id"]),
                "title": str(tab.get("title") or ""),
                "url": url,
                "channel": details.channel,
            }
        )

    print(
        json.dumps(
            {"updated": updated, "skipped": skipped, "failed": failed},
            indent=2,
            ensure_ascii=False,
        )
    )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
