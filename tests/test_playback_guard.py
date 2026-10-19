"""Guards rule #1: the count-in must stay outside the playback chain.

The playback/cursor alignment is validated by ear, not by pytest, so these
tests only enforce the structural boundary that keeps it from breaking:
the count-in may not call the alphaTab API or write to the audio element,
and the playback-chain functions may not learn about the count-in.
"""

import re
from pathlib import Path

APP_JS = Path(__file__).resolve().parents[1] / "app" / "static" / "app.js"


def _source() -> str:
    return APP_JS.read_text(encoding="utf-8")


def _code_only(text: str) -> str:
    """Drop comments so documentation may name audio/api without failing."""
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return re.sub(r"//[^\n]*", "", text)


def _block(source: str, start: int) -> str:
    """Return the brace-balanced body after the first '{' following start."""
    opening = source.index("{", start)
    depth = 0
    for index in range(opening, len(source)):
        char = source[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[opening + 1 : index]
    raise AssertionError("unbalanced braces in app.js")


def _function_body(source: str, name: str) -> str:
    return _block(source, source.index(f"function {name}("))


def _object_body(source: str, marker: str) -> str:
    return _block(source, source.index(marker))


PLAYBACK_FUNCTIONS = (
    "togglePlayback",
    "syncPosition",
    "seekTo",
    "seekBy",
    "syncTimeMs",
    "scoreEndTimeMs",
    "barDurationMs",
    "bpmDrift",
)

COUNT_IN_FUNCTIONS = (
    "drawCountIn",
    "beginCountIn",
    "cancelCountIn",
    "shouldRunCountIn",
)


def test_count_in_never_calls_playback_or_alphatab():
    source = _source()
    for name in COUNT_IN_FUNCTIONS:
        body = _code_only(_function_body(source, name))
        assert "api." not in body, f"{name} must not call the alphaTab API"
        assert "audio" not in body, f"{name} must not touch the audio element"
        assert (
            "togglePlayback" not in body
        ), f"{name} must not start playback directly"

    # alphaTab pre-positions the audio while loading, so the skip decision
    # must come from an explicit UI seek, never from audio.currentTime.
    skip = _code_only(_function_body(source, "shouldRunCountIn"))
    assert "countInSkipped" in skip


def test_count_in_finishes_through_the_unchanged_playback_path():
    source = _source()
    finish = _function_body(source, "finishCountIn")
    assert finish.count("togglePlayback()") == 1
    assert "api." not in finish
    assert "audio.play" not in finish

    handler = _function_body(source, "handlePlayButton")
    # Fullscreen is requested on the user gesture, not at the end of the count.
    assert "enterViewerFullscreen()" in handler
    assert "beginCountIn()" in handler
    assert "togglePlayback()" in handler


def test_playback_chain_has_no_count_in_code():
    source = _source()
    for name in PLAYBACK_FUNCTIONS:
        body = _function_body(source, name)
        assert "countIn" not in body, f"{name} must not contain count-in code"
        assert "countdown" not in body.lower()

    media_handler = _object_body(source, "const mediaHandler =")
    assert "countIn" not in media_handler
    assert "countdown" not in media_handler.lower()
