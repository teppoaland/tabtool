"""Tuning descriptions: presets, letter names and custom tunings (v1.68)."""

from __future__ import annotations

from app.tuning import describe_key, describe_pitches, note_name, open_strings


def test_describe_known_tunings() -> None:
    standard = describe_pitches([40, 45, 50, 55, 59, 64])
    assert standard["key"] == "standard"
    assert standard["text"] == "Standard E · EADGBE"

    drop_d = describe_pitches([38, 45, 50, 55, 59, 64])
    assert drop_d["key"] == "drop_d"
    assert drop_d["text"] == "Drop D · DADGBE"

    d_standard = describe_pitches([38, 43, 48, 53, 57, 62])
    assert d_standard["key"] == "d_standard"
    assert d_standard["text"] == "D Standard · DGCFAD"

    eb = describe_pitches([39, 44, 49, 54, 58, 63])
    assert eb["key"] == "eb_standard"
    assert eb["text"] == "Eb Standard · EbAbDbGbBbEb"

    open_g = describe_pitches([38, 43, 50, 55, 59, 62])
    assert open_g["key"] == "open_g"


def test_describe_custom_tuning_keeps_letters() -> None:
    custom = describe_pitches([40, 45, 50, 55, 59, 65])
    assert custom["key"] == "custom"
    assert custom["label"] == "Custom"
    assert custom["text"].endswith("F")
    assert custom["notes"][-1] == "F4"


def test_note_name_uses_flats() -> None:
    assert note_name(38) == "D2"
    assert note_name(39) == "Eb2"
    assert note_name(64) == "E4"


def test_describe_key_falls_back_to_key() -> None:
    assert describe_key("drop_d") == "Drop D"
    assert describe_key("d_standard") == "D Standard"
    assert describe_key("custom") == "Custom"
    assert describe_key("weird") == "Weird"


class _Strings:
    def __init__(self, values: list[int]) -> None:
        # GP5 numbers the strings from the high string (1) down to the low one.
        self.items = [
            type("S", (), {"number": index + 1, "value": value})
            for index, value in enumerate(values)
        ]


class _Track:
    def __init__(self, name: str, strings: list[int], notes: int) -> None:
        self.name = name
        self.strings = _Strings(strings).items
        beat = type("B", (), {"notes": [None] * notes})
        voice = type("V", (), {"beats": [beat]})
        measure = type("M", (), {"voices": [voice]})
        self.measures = [measure]


class _Song:
    def __init__(self, tracks: list[_Track]) -> None:
        self.tracks = tracks


def test_open_strings_prefers_the_guitar_track() -> None:
    """A vocals track listed first must not decide the guitar tuning (v1.79)."""
    song = _Song(
        [
            _Track("Vocals", [64, 59, 55, 50, 45, 40], notes=3),
            _Track("Guitar 1", [64, 59, 55, 50, 45, 38], notes=400),
            _Track("Bass", [43, 38, 33, 26], notes=200),
            _Track("Drums", [0, 0, 0, 0, 0, 0], notes=500),
        ]
    )
    pitches = open_strings(song)
    assert pitches == [38, 45, 50, 55, 59, 64]
    assert describe_pitches(pitches)["text"] == "Drop D · DADGBE"


def test_open_strings_skips_percussion_and_keeps_the_first_fallback() -> None:
    song = _Song(
        [
            _Track("Drums", [0, 0, 0, 0, 0, 0], notes=900),
            _Track("Bass", [43, 38, 33, 26], notes=0),
        ]
    )
    assert open_strings(song) == [26, 33, 38, 43]
    assert open_strings(_Song([])) == []
