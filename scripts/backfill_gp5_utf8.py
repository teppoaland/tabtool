"""Re-export variant GP5 files as UTF-8 so alphaTab shows the Finnish labels.

v1.73 wrote GP5 strings as cp1252 while alphaTab reads UTF-8, so 'V1 · Avoimet
kielet' showed as 'V1 � Avoimet kielet'. This script rebuilds the combined
viewer GP5 from the stored variant snapshots with the now-UTF-8 exporter.

Run:  .venv\\Scripts\\python.exe scripts\\backfill_gp5_utf8.py [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import db  # noqa: E402
from app.pipeline.export_gp5 import export_gp5_variants  # noqa: E402
from app.pipeline.variant_store import restore_document  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    fixed = 0
    for tab in db.list_tabs(200):
        meta = tab.get("meta") or {}
        variants = meta.get("variants")
        if not isinstance(variants, list) or len(variants) <= 1:
            continue
        if meta.get("variant_finalized"):
            continue
        try:
            directory = db.resolve_under_data(str(tab["directory"]))
        except ValueError:
            continue
        variants_dir = directory / "variants"
        if not variants_dir.is_dir():
            continue

        documents = []
        for entry in variants:
            if not isinstance(entry, dict):
                continue
            source = variants_dir / str(entry.get("source") or "").split("/")[-1]
            if not source.is_file():
                continue
            snapshot = json.loads(source.read_text(encoding="utf-8"))
            document = restore_document(snapshot)
            document = document.__class__(
                **{
                    **document.__dict__,
                    "bpm": float(meta.get("bpm") or document.bpm),
                }
            )
            documents.append((document, str(entry.get("label") or "Guitar")))

        if not documents:
            continue
        if args.dry_run:
            print(f"would fix {tab['id']} ({len(documents)} variants)")
            fixed += 1
            continue
        export_gp5_variants(documents, directory / "tab.gp5")
        print(f"fixed {tab['id']} ({len(documents)} variants)")
        fixed += 1

    print(f"{'Would fix' if args.dry_run else 'Fixed'} {fixed} tab(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
