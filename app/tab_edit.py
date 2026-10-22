"""Model-level tab edits (v1.76).

The viewer's clock is the *notated* timeline: ``scoreEndTimeMs()`` is computed
from the master bars, so a GP5 repeat count only moves alphaTab's playback
timeline and the score would end early. ``expand_repeat`` therefore writes the
repeated block out as real bars, drops the repeat marks and renumbers the rest
of the song, which keeps the tab 1:1 with the recording.

Nothing here touches audio, the database or the files; ``scripts/expand_repeat.py``
does the I/O.
"""

from __future__ import annotations

import copy
from typing import Any


class TabEditError(ValueError):
    """Raised when the requested edit does not fit the tab."""


def count_notes(song: Any) -> int:
    """Total notes of all tracks."""
    total = 0
    for track in getattr(song, "tracks", []) or []:
        for measure in getattr(track, "measures", []) or []:
            for voice in getattr(measure, "voices", []) or []:
                for beat in getattr(voice, "beats", []) or []:
                    total += len(getattr(beat, "notes", []) or [])
    return total


def _repeat_block(song: Any, bar: int, close_bar: int | None) -> tuple[int, int]:
    """Return the zero-based (start, close) indexes of the repeated block."""
    headers = list(getattr(song, "measureHeaders", []) or [])
    if not 1 <= bar <= len(headers):
        raise TabEditError(
            f"Tahtia {bar} ei ole: tabissa on {len(headers)} tahtia."
        )
    start = bar - 1
    if close_bar is not None:
        if not bar <= close_bar <= len(headers):
            raise TabEditError(
                f"Toiston lopputahti {close_bar} ei ole välillä {bar}…{len(headers)}."
            )
        close = close_bar - 1
        if headers[close].repeatClose is None or headers[close].repeatClose < 0:
            raise TabEditError(
                f"Tahdissa {close_bar} ei ole toiston loppumerkintää."
            )
        return start, close

    for index in range(start, len(headers)):
        repeat_close = headers[index].repeatClose
        if repeat_close is not None and repeat_close >= 0:
            return start, index
    raise TabEditError(
        f"Tahdista {bar} alkaen ei löytynyt toiston loppua; anna --close-bar."
    )


def _clone_header(header: Any, song: Any) -> Any:
    """Copy a measure header without dragging the whole song along."""
    return copy.deepcopy(header, {id(song): song})


def _clone_measure(measure: Any, header_copy: Any) -> Any:
    """Copy one measure; its track and new header are reused, not copied."""
    memo = {id(measure.track): measure.track, id(measure.header): header_copy}
    return copy.deepcopy(measure, memo)


def expand_repeat(
    song: Any,
    bar: int,
    times: int,
    close_bar: int | None = None,
    keep_text: bool = False,
) -> dict[str, int]:
    """Write the repeated block out ``times`` times in total.

    ``bar`` and ``close_bar`` are 1-based. The repeat marks are removed, every
    header is renumbered and the bar start ticks are recomputed, so the song
    becomes a plain sequence of bars (no repeat required at playback time).
    """
    if times < 2:
        raise TabEditError("Toistomäärän pitää olla vähintään 2.")

    headers = list(getattr(song, "measureHeaders", []) or [])
    tracks = list(getattr(song, "tracks", []) or [])
    if not tracks:
        raise TabEditError("Tabissa ei ole raitoja.")
    if any(len(track.measures) != len(headers) for track in tracks):
        raise TabEditError("Tahtien määrä ei täsmää raitojen ja otsikoiden välillä.")

    start, close = _repeat_block(song, bar, close_bar)
    block_headers = headers[start : close + 1]
    block_length = sum(header.length for header in block_headers)
    notes_per_block = 0
    for track in tracks:
        for measure in track.measures[start : close + 1]:
            for voice in measure.voices:
                for beat in voice.beats:
                    notes_per_block += len(beat.notes)

    # The block is played `times` in total, so its repeat marks must go.
    for header in block_headers:
        header.isRepeatOpen = False
        header.repeatClose = -1
        header.repeatAlternative = 0

    new_headers = headers[: close + 1]
    per_track = [track.measures[: close + 1] for track in tracks]
    for _ in range(times - 1):
        header_copies = [_clone_header(header, song) for header in block_headers]
        for track_index, track in enumerate(tracks):
            for measure, header_copy in zip(
                track.measures[start : close + 1], header_copies
            ):
                measure_copy = _clone_measure(measure, header_copy)
                if not keep_text:
                    # "Should be played 17 times" belongs to the first bar only.
                    for voice in measure_copy.voices:
                        for beat in voice.beats:
                            beat.text = None
                per_track[track_index].append(measure_copy)
        new_headers.extend(header_copies)
    new_headers.extend(headers[close + 1 :])
    for track_index, track in enumerate(tracks):
        per_track[track_index].extend(track.measures[close + 1 :])

    tick = headers[0].start if headers else 0
    for index, header in enumerate(new_headers):
        header.number = index + 1
        header.start = tick
        tick += header.length

    song.measureHeaders = new_headers
    for track_index, track in enumerate(tracks):
        track.measures = per_track[track_index]

    if any(len(track.measures) != len(new_headers) for track in tracks):
        raise TabEditError("Tahtien lisäys epäonnistui: raidat eivät täsmää.")

    return {
        "bars_before": len(headers),
        "bars_after": len(new_headers),
        "plays": times,
        "notes_added": notes_per_block * (times - 1),
        "ticks_added": block_length * (times - 1),
    }
