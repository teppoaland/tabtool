"""Retune a tab and move the frets so the music stays exactly the same.

Use case: the guitars at home are in D Standard (DGCFAD) but the tab was
written for Drop D. This script gives the matching tracks the new tuning and
shifts every fret by the same amount as its string, so the tab sounds
identical and shows where to play it. Tracks with a different tuning (vocals,
bass) are left untouched.

The original GP5 is copied to `data/backups/<id>-<timestamp>/` first and the
written file is validated by comparing every note's sounding pitch.

Usage:
    .venv\\\\Scripts\\\\python.exe scripts\\\\retune_tab.py --tab <id> --from drop_d --to d_standard --dry-run
    .venv\\\\Scripts\\\\python.exe scripts\\\\retune_tab.py --tab <id> --from drop_d --to d_standard --clear-override
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import db, tab_edit  # noqa: E402
from app.pipeline.model import TUNINGS  # noqa: E402
from app.tuning import describe_pitches, open_strings  # noqa: E402


def _open_pitches(key: str) -> list[int]:
    """Open strings of a preset, from the highest string (1) to the lowest."""
    tuning = TUNINGS.get(str(key or "").strip().lower())
    if tuning is None:
        raise SystemExit(
            f"Tuntematon viritys: {key}. Käytä esim. standard, drop_d, "
            "eb_standard, d_standard tai open_g."
        )
    return [int(pitch) for _number, pitch in sorted(tuning.strings)]


def _pitches(song) -> list[tuple[int, int, int, int]]:
    """Every note as (track, bar, beat start, sounding pitch)."""
    signature = []
    for track_index, track in enumerate(getattr(song, "tracks", []) or []):
        for bar_index, measure in enumerate(getattr(track, "measures", []) or []):
            for voice in getattr(measure, "voices", []) or []:
                for beat in getattr(voice, "beats", []) or []:
                    for note in getattr(beat, "notes", []) or []:
                        signature.append(
                            (
                                track_index,
                                bar_index,
                                int(beat.start),
                                int(note.realValue),
                            )
                        )
    return signature


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--tab", help="Tab id in the library")
    source.add_argument("--file", help="GP5 file path")
    parser.add_argument("--from", dest="source_key", required=True, help="Current tuning key")
    parser.add_argument("--to", dest="target_key", required=True, help="New tuning key")
    parser.add_argument(
        "--clear-override",
        action="store_true",
        help="Remove a manual tuning override (tab id only)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Only report")
    args = parser.parse_args()

    from_pitches = _open_pitches(args.source_key)
    to_pitches = _open_pitches(args.target_key)

    try:
        path = (
            tab_edit.resolve_tab_gp5(args.tab)
            if args.tab
            else Path(args.file).expanduser()
        )
    except tab_edit.TabEditError as exc:
        raise SystemExit(f"Ei voitu avata: {exc}") from exc
    if not path.is_file():
        raise SystemExit(f"Tiedostoa ei löytynyt: {path}")

    song = tab_edit.read_song(path)
    before = _pitches(song)
    try:
        stats = tab_edit.retune_tracks(song, from_pitches, to_pitches)
    except tab_edit.TabEditError as exc:
        raise SystemExit(f"Ei voitu virittää: {exc}") from exc

    summary = {
        "file": str(path),
        "tab_id": args.tab or None,
        f"from_{args.source_key}": from_pitches,
        f"to_{args.target_key}": to_pitches,
        "tracks": stats["tracks"],
        "notes_moved": stats["notes_moved"],
        "max_fret": stats["max_fret"],
        "dry_run": bool(args.dry_run),
    }
    if args.dry_run:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        return 0

    backup = tab_edit.backup_file(path, args.tab or path.stem)
    summary["backup"] = str(backup)
    try:
        tab_edit.save_song(path, song, len(song.measureHeaders))
        stored = tab_edit.read_song(path)
        if _pitches(stored) != before:
            raise ValueError("sävelet muuttuivat virityksen yhteydessä")
    except Exception as exc:  # noqa: BLE001 - restore and report
        shutil.copy2(backup, path)
        raise SystemExit(
            f"Kirjoitus epäonnistui, alkuperäinen palautettu: {exc}"
        ) from exc

    info = describe_pitches(open_strings(stored))
    summary["tuning_label"] = info["text"]

    if args.tab:
        meta = dict((db.get_tab(args.tab) or {}).get("meta") or {})
        meta["tuning_label"] = info["text"]
        meta["tuning_notes"] = info["notes"]
        if args.clear_override:
            meta.pop("tuning_override", None)
        db.update_tab_meta(args.tab, meta)
        db.update_tab_tuning(args.tab, str(info["key"]))
        directory = tab_edit.resolve_tab_gp5(args.tab).parent
        meta_path = directory / "meta.json"
        temporary = meta_path.with_name(meta_path.name + ".tmp")
        temporary.write_text(
            json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        temporary.replace(meta_path)

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
