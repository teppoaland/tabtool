"""Phase 1 CLI: audio -> stems -> notes -> tab files.

Examples:
  .venv\\Scripts\\python.exe scripts\\pipeline_smoke.py "C:\\Music\\song.mp3" --clip-seconds 30
  .venv\\Scripts\\python.exe scripts\\pipeline_smoke.py "https://youtu.be/..." --title "Song"
  .venv\\Scripts\\python.exe scripts\\pipeline_smoke.py song.mp3 --no-separation
"""

from __future__ import annotations

import argparse
import json
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import DATA_DIR, ensure_data_dirs  # noqa: E402
from app.pipeline.audio_source import prepare_audio, slugify  # noqa: E402
from app.pipeline.build import build_document  # noqa: E402
from app.pipeline.export_gp5 import export_gp5  # noqa: E402
from app.pipeline.export_midi import export_midi  # noqa: E402
from app.pipeline.export_musicxml import export_musicxml  # noqa: E402
from app.pipeline.fretboard import assign_fretboard  # noqa: E402
from app.pipeline.model import TUNINGS, get_tuning  # noqa: E402
from app.pipeline.quantize import quantize_notes  # noqa: E402
from app.pipeline.separate import separate_stems  # noqa: E402
from app.pipeline.tempo import detect_tempo  # noqa: E402
from app.pipeline.transcribe import transcribe_audio  # noqa: E402


def log(message: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}", flush=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a guitar tab draft from local or YouTube audio."
    )
    parser.add_argument("source", help="Local audio file or YouTube URL")
    parser.add_argument("--title", default=None)
    parser.add_argument("--artist", default="")
    parser.add_argument("--output-dir", default=None)
    parser.add_argument(
        "--clip-seconds",
        type=float,
        default=None,
        help="Trim the input for a quick smoke test",
    )
    parser.add_argument(
        "--start-seconds",
        type=float,
        default=None,
        help="Start the clip at this position",
    )
    parser.add_argument(
        "--no-separation",
        action="store_true",
        help="Skip Demucs and transcribe the full mix (quick, lower quality)",
    )
    parser.add_argument(
        "--model",
        default="htdemucs_6s",
        choices=("htdemucs_6s", "htdemucs", "htdemucs_ft"),
    )
    parser.add_argument(
        "--stem",
        default="guitar",
        choices=("guitar", "other", "bass", "vocals", "drums"),
    )
    parser.add_argument("--device", default="cpu", choices=("cpu", "cuda"))
    parser.add_argument("--segment", type=int, default=None)
    parser.add_argument("--bpm", type=float, default=None)
    parser.add_argument("--time-signature", default="4/4")
    parser.add_argument("--grid", type=int, default=16, choices=(4, 8, 16, 32, 64))
    parser.add_argument(
        "--tuning",
        default="standard",
        choices=tuple(TUNINGS.keys()),
    )
    parser.add_argument("--max-fret", type=int, default=24)
    parser.add_argument("--max-span", type=int, default=5)
    parser.add_argument("--onset-threshold", type=float, default=0.5)
    parser.add_argument("--frame-threshold", type=float, default=0.3)
    parser.add_argument("--min-note-length-ms", type=float, default=58.0)
    parser.add_argument("--min-frequency", type=float, default=80.0)
    parser.add_argument("--max-frequency", type=float, default=1200.0)
    parser.add_argument("--debug", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    ensure_data_dirs()
    tuning = get_tuning(args.tuning)

    try:
        log("Preparing audio ...")
        audio = prepare_audio(
            args.source,
            DATA_DIR / "audio",
            clip_seconds=args.clip_seconds,
            start_seconds=args.start_seconds,
            title=args.title,
        )
        log(f"Audio: {audio.path} ({audio.duration:.1f}s)")

        stems: dict[str, Path] = {}
        if args.no_separation:
            log("Skipping Demucs; transcribing the full mix.")
            transcription_path = audio.path
            tempo_path = audio.path
            stem_name = "full-mix"
        else:
            log(f"Separating stems with {args.model} ...")
            stems = separate_stems(
                audio.path,
                DATA_DIR / "stems",
                model=args.model,
                device=args.device,
                segment=args.segment,
            )
            stem_name = args.stem
            if stem_name not in stems:
                stem_name = "guitar" if "guitar" in stems else "other"
            transcription_path = stems[stem_name]
            tempo_path = stems.get("drums", audio.path)
            log(f"Stems: {', '.join(sorted(stems))}")
            log(f"Transcribing stem: {stem_name} ({transcription_path})")

        if args.bpm:
            bpm = float(args.bpm)
            raw_bpm = bpm
            log(f"Using manual BPM: {bpm:.1f}")
        else:
            log("Detecting tempo ...")
            tempo = detect_tempo(tempo_path, start_bpm=120.0)
            bpm = tempo.bpm
            raw_bpm = tempo.raw_bpm
            log(
                f"Detected BPM: {bpm:.1f} (raw {raw_bpm:.1f}, "
                f"{len(tempo.beat_times)} beats)"
            )

        log("Transcribing with Basic Pitch ...")
        notes = transcribe_audio(
            transcription_path,
            onset_threshold=args.onset_threshold,
            frame_threshold=args.frame_threshold,
            min_note_length_ms=args.min_note_length_ms,
            min_frequency=args.min_frequency,
            max_frequency=args.max_frequency,
        )
        log(f"Detected notes: {len(notes)}")

        log("Quantizing ...")
        quantized = quantize_notes(
            notes,
            bpm,
            time_signature=args.time_signature,
            grid_division=args.grid,
            total_duration_seconds=audio.duration,
        )
        log(
            f"Quantized notes: {len(quantized.notes)} in "
            f"{quantized.measure_count} measures"
        )

        log(f"Assigning strings/frets ({tuning.name}) ...")
        tab_notes, fret_warnings = assign_fretboard(
            quantized.notes,
            tuning,
            max_fret=args.max_fret,
            max_span=args.max_span,
        )
        log(f"Tab notes: {len(tab_notes)}")

        warnings = quantized.warnings + fret_warnings
        document = build_document(
            title=args.title or audio.title,
            artist=args.artist,
            bpm=bpm,
            time_signature=args.time_signature,
            tuning=tuning,
            tab_notes=tab_notes,
            measure_count=quantized.measure_count,
            max_fret=args.max_fret,
            grid_division=args.grid,
            source_audio=str(audio.path),
            warnings=warnings,
        )

        output_dir = (
            Path(args.output_dir)
            if args.output_dir
            else DATA_DIR / "tabs" / slugify(document.title, "tab")
        )
        output_dir.mkdir(parents=True, exist_ok=True)

        log("Writing GP5 / MusicXML / MIDI ...")
        gp5_path = export_gp5(document, output_dir / "tab.gp5")
        xml_path = export_musicxml(document, output_dir / "tab.musicxml")
        midi_path = export_midi(document, output_dir / "tab.mid")

        meta = {
            "title": document.title,
            "artist": document.artist,
            "source": audio.source_ref,
            "source_type": audio.source_type,
            "audio_path": str(audio.path),
            "duration_seconds": audio.duration,
            "start_seconds": args.start_seconds,
            "bpm": bpm,
            "raw_bpm": raw_bpm,
            "time_signature": list(document.time_signature),
            "tuning": tuning.key,
            "grid_division": args.grid,
            "model": None if args.no_separation else args.model,
            "stem": stem_name,
            "detected_notes": len(notes),
            "tab_notes": len(tab_notes),
            "measures": len(document.measures),
            "warnings": warnings,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "files": {
                "gp5": gp5_path.name,
                "musicxml": xml_path.name,
                "midi": midi_path.name,
            },
        }
        (output_dir / "meta.json").write_text(
            json.dumps(meta, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        log("Done.")
        print(json.dumps(meta, indent=2, ensure_ascii=False))
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        if args.debug:
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
