"""Store the audio source link on tabs that were created before v2.03.

The Tiedot dialog shows where a tab came from (Audiolähde / Tablähde). Jobs
created before v2.03 kept the YouTube link only in the job and track rows, so
this script copies it into ``meta.audio_source_url``. The tab-file link
(``tab_source_url``) was never stored before v2.03 and cannot be recovered.

Nothing is downloaded, re-rendered or moved.

Usage:
    .venv\\Scripts\\python.exe scripts\\backfill_source_url.py --dry-run
    .venv\\Scripts\\python.exe scripts\\backfill_source_url.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import db  # noqa: E402


def _http(value: object) -> str:
    text = str(value or "").strip()
    return text if text.startswith(("http://", "https://")) else ""


def _job_urls() -> dict[str, str]:
    """tab_id -> the newest YouTube link a job for that tab used."""
    with db.connection() as conn:
        rows = conn.execute(
            """
            SELECT j.tab_id AS tab_id, t.source_ref AS source_ref
            FROM jobs j
            JOIN tracks t ON t.id = j.track_id
            WHERE j.tab_id IS NOT NULL AND j.tab_id <> ''
              AND t.source_type = 'youtube'
            ORDER BY j.created_at ASC
            """
        ).fetchall()
    urls: dict[str, str] = {}
    for row in rows:
        tab_id = str(row["tab_id"] or "")
        url = _http(row["source_ref"])
        if tab_id and url:
            urls[tab_id] = url
    return urls


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Only list the tabs")
    args = parser.parse_args()

    urls = _job_urls()
    updated: list[dict[str, str]] = []
    skipped: list[dict[str, str]] = []

    for tab in db.list_tabs(200):
        tab_id = str(tab["id"])
        meta = tab.get("meta") if isinstance(tab.get("meta"), dict) else {}
        if _http(meta.get("audio_source_url")) or _http(meta.get("source")):
            skipped.append({"tab_id": tab_id, "reason": "already set"})
            continue
        url = urls.get(tab_id, "")
        if not url:
            continue
        meta = dict(meta)
        meta["audio_source_url"] = url
        meta.setdefault("audio_source_type", "youtube")
        updated.append(
            {"tab_id": tab_id, "title": str(tab.get("title") or ""), "url": url}
        )
        if not args.dry_run:
            db.update_tab_meta(tab_id, meta)

    print(
        json.dumps(
            {"dry_run": args.dry_run, "updated": updated, "skipped": skipped},
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
