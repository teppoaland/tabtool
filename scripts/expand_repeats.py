"""Write every repeat block of a GP5 tab out as real bars.

Why: the viewer's clock is the *notated* timeline (`scoreEndTimeMs()` from the
master bars) while alphaTab expands repeats only at playback time. A 96-bar
tab with 48 repeated bars therefore ended the clock at 3:26 (205.7 s) even
though the performance is 5:08 — the cursor froze at bar 68 while the audio
kept playing (Slayer – Dead Skin Mask, 31.10.2026).

`scripts/expand_repeat.py` handles one block and requires that no repeat mark
is left in the file, so it cannot tidy a song with several blocks. This script
finds *all* blocks (repeat open + repeat close, alternate endings included),
writes each one out as real bars, removes the marks, renumbers the song and
validates the result by replaying the original bar order.

The original GP5 is copied to `data/backups/<id>-<timestamp>/` first, the file
is written atomically and read back, and the written bars must match the bars
the player would have played (per track note counts).

Usage:
    .venv\\Scripts\\python.exe scripts\\expand_repeats.py --tab <id> --dry-run
    .venv\\Scripts\\python.exe scripts\\expand_repeats.py --tab <id>
    .venv\\Scripts\\python.exe scripts\\expand_repeats.py --file song.gp5 --out fixed.gp5
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import config, db, tab_edit  # noqa: E402


def find_blocks(song) -> list[dict[str, object]]:
    """Repeat blocks as (start, close, plays, endings), 0-based indexes.

    ``plays`` follows the player: GP's repeatClose value is the number of
    *extra* passes, so a close value of 3 means the block is played 4 times.
    ``endings`` maps a bar index to its alternate-ending bitmask.
    """
    headers = list(getattr(song, "measureHeaders", []) or [])
    blocks: list[dict[str, object]] = []
    start = 0
    for index, header in enumerate(headers):
        if bool(getattr(header, "isRepeatOpen", False)):
            start = index
        close = getattr(header, "repeatClose", -1)
        if close is None or int(close) <= 0:
            # GP stores 0 (or -1) for "no repeat"; a real repeat keeps its
            # extra-pass count, so 1 means the block is played twice.
            continue
        endings = {}
        for offset in range(start, index + 1):
            mask = int(getattr(headers[offset], "repeatAlternative", 0) or 0)
            if mask:
                endings[offset] = mask
        blocks.append(
            {
                "start": start,
                "close": index,
                "plays": int(close) + 1,
                "endings": endings,
            }
        )
        start = index + 1
    return blocks


def signature(song) -> list[list[int]]:
    """Per bar, per track note counts (the music, without texts)."""
    rows: list[list[int]] = []
    for index in range(len(song.measureHeaders)):
        counts = []
        for track in song.tracks:
            measure = track.measures[index]
            counts.append(
                sum(
                    len(beat.notes)
                    for voice in measure.voices
                    for beat in voice.beats
                )
            )
        rows.append(counts)
    return rows


def played_order(bar_count: int, blocks: list[dict[str, object]]) -> list[int]:
    """The written bars in the order the player would play them."""
    order: list[int] = []
    cursor = 0
    for block in blocks:
        start = int(block["start"])
        close = int(block["close"])
        plays = int(block["plays"])
        endings = block["endings"]
        order.extend(range(cursor, start))
        for pass_index in range(plays):
            for index in range(start, close + 1):
                mask = int(endings.get(index, 0)) if endings else 0
                if mask and not mask & (1 << pass_index):
                    continue
                order.append(index)
        cursor = close + 1
    order.extend(range(cursor, bar_count))
    return order


def _update_meta(meta_path: Path, stats: dict[str, int]) -> None:
    """Keep meta.json counts in step: a rebuilt database reads them back."""
    if not meta_path.is_file():
        return
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return
    if not isinstance(meta, dict):
        return
    meta["measures"] = int(stats["bars_after"])
    meta["tab_notes"] = int(stats["notes_after"])
    temporary = meta_path.with_name(meta_path.name + ".tmp")
    temporary.write_text(
        json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    os.replace(temporary, meta_path)


def _clear_marks(headers, start: int, close: int) -> None:
    for index in range(start, close + 1):
        header = headers[index]
        header.isRepeatOpen = False
        header.repeatClose = -1
        header.repeatAlternative = 0


def expand_blocks(song, blocks, keep_text: bool = False) -> dict[str, int]:
    """Expand every block, last first so the earlier bar numbers stay valid."""
    bars_before = len(song.measureHeaders)
    notes_before = tab_edit.count_notes(song)
    removed = 0
    for block in reversed(blocks):
        start = int(block["start"])
        close = int(block["close"])
        plays = int(block["plays"])
        endings = block["endings"]
        length = close - start + 1
        if plays < 2:
            _clear_marks(song.measureHeaders, start, close)
            continue
        tab_edit.expand_repeat(
            song,
            bar=start + 1,
            times=plays,
            close_bar=close + 1,
            keep_text=keep_text,
        )
        if not endings:
            continue
        # Alternate endings are gone from the copies, so drop the copies of a
        # bar that the player would not have played on that pass.
        drop: list[int] = []
        for pass_index in range(plays):
            base = start + pass_index * length
            for offset, mask in endings.items():
                if int(mask) & (1 << pass_index):
                    continue
                drop.append(base + (int(offset) - start) + 1)
        if drop:
            tab_edit.remove_bars(song, drop)
            removed += len(drop)
    # Nothing may be left for the player to expand: the marks are data now.
    _clear_marks(song.measureHeaders, 0, len(song.measureHeaders) - 1)
    return {
        "bars_before": bars_before,
        "bars_after": len(song.measureHeaders),
        "notes_before": notes_before,
        "notes_after": tab_edit.count_notes(song),
        "bars_removed": removed,
        "blocks": len(blocks),
    }


def _resolve(args: argparse.Namespace) -> tuple[Path, str]:
    if args.file:
        path = Path(args.file).expanduser()
        if not path.is_file():
            raise SystemExit(f"Tiedostoa ei löytynyt: {path}")
        return path, path.stem
    try:
        return tab_edit.resolve_tab_gp5(args.tab), args.tab
    except tab_edit.TabEditError as exc:
        raise SystemExit(str(exc)) from exc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--tab", help="Tab id in the library")
    source.add_argument("--file", help="GP5 file path")
    parser.add_argument("--out", help="Written file (default: in place)")
    parser.add_argument(
        "--keep-text",
        action="store_true",
        help="Keep the beat texts in the copied bars too",
    )
    parser.add_argument("--dry-run", action="store_true", help="Only report")
    args = parser.parse_args()

    path, key = _resolve(args)
    destination = Path(args.out).expanduser() if args.out else path
    song = tab_edit.read_song(path)
    blocks = find_blocks(song)
    if not blocks:
        raise SystemExit("Tabissa ei ole toistomerkintöjä – ei tehtävää.")

    original = tab_edit.read_song(path)
    original_signature = signature(original)
    expected = [
        original_signature[index]
        for index in played_order(len(original.measureHeaders), blocks)
    ]
    plan = {
        "file": str(path),
        "tab_id": args.tab or None,
        "blocks": [
            {
                "bars": f"{int(b['start']) + 1}-{int(b['close']) + 1}",
                "plays": int(b["plays"]),
                "endings": {
                    str(int(offset) + 1): int(mask)
                    for offset, mask in (b["endings"] or {}).items()
                },
            }
            for b in blocks
        ],
        "bars_before": len(original.measureHeaders),
        "bars_expected": len(expected),
        "notes_before": tab_edit.count_notes(original),
    }
    if args.dry_run:
        print(json.dumps({**plan, "dry_run": True}, indent=2, ensure_ascii=False))
        return 0

    stats = expand_blocks(song, blocks, keep_text=args.keep_text)
    backup = tab_edit.backup_file(path, key)
    try:
        tab_edit.save_song(destination, song, stats["bars_after"])
        stored = tab_edit.read_song(destination)
        for header in stored.measureHeaders:
            repeat_close = getattr(header, "repeatClose", -1)
            if (
                bool(getattr(header, "isRepeatOpen", False))
                or (repeat_close is not None and int(repeat_close) > 0)
                or int(getattr(header, "repeatAlternative", 0) or 0)
            ):
                raise ValueError("toistomerkintöjä jäi tiedostoon")
        if signature(stored) != expected:
            raise ValueError("tahdit eivät vastaa soitettua järjestystä")
    except Exception as exc:  # noqa: BLE001 - restore and report
        shutil.copy2(backup, path)
        raise SystemExit(f"Kirjoitus epäonnistui, alkuperäinen palautettu: {exc}") from exc

    if args.tab:
        with db.connection() as conn:
            conn.execute(
                "UPDATE tabs SET measure_count = ?, note_count = ? WHERE id = ?",
                (stats["bars_after"], stats["notes_after"], args.tab),
            )
        _update_meta(
            Path(config.DATA_DIR) / "tabs" / args.tab / "meta.json", stats
        )
    print(
        json.dumps(
            {**plan, **stats, "backup": str(backup), "written": str(destination)},
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
