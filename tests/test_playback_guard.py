"""Guards rule #1: the count-in and the score-end guard stay outside the chain.

The playback/cursor alignment is validated by ear, not by pytest, so these
tests only enforce the structural boundary that keeps it from breaking:
the count-in may not call the alphaTab API or write to the audio element,
the score-end guard may not leak into the audio adapter, and the
playback-chain functions may not learn about either of them.
"""

import re
from pathlib import Path

APP_JS = Path(__file__).resolve().parents[1] / "app" / "static" / "app.js"
INDEX_HTML = Path(__file__).resolve().parents[1] / "app" / "static" / "index.html"


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


def test_count_in_switch_only_gates_the_countdown():
    """v1.81: the ON/OFF switch is read in shouldRunCountIn and nowhere else."""
    source = _source()
    gate = _function_body(source, "shouldRunCountIn")
    assert "countInEnabled" in gate
    for name in PLAYBACK_FUNCTIONS:
        assert (
            "countInEnabled" not in _function_body(source, name)
        ), f"{name} must not know about the count-in switch"


def test_count_in_switch_sits_under_the_fullscreen_button():
    html = INDEX_HTML.read_text(encoding="utf-8")
    corner = html[html.index('class="viewer-corner"') :]
    corner = corner[: corner.index("</div>")]
    assert 'id="fullscreen-button"' in corner
    assert 'id="countin-toggle"' in corner
    # Default is on.
    assert "checked" in corner


def test_cursor_feed_never_goes_backwards_while_playing():
    """v1.91: a stale audio.currentTime may not rewind the cursor.

    alphaTab applies every fed position as the cursor position without any
    check, so one repeated or slightly stale read (the browser reports
    currentTime in ~250 ms chunks) hops the cursor a beat forward and back.
    The hold lives in syncPosition only: the clock, the audio adapter and the
    forced syncs keep their behaviour, so rewind and the bar math stay.
    """
    source = _source()
    feed = _code_only(_function_body(source, "syncPosition"))

    assert "lastFedScoreMs" in feed
    assert "lastFedAudioS" in feed
    assert "FEED_JITTER_S" in feed
    # A paused/ended audio, a forced sync or a real backwards seek resets it.
    assert "force" in feed
    assert "audio.paused" in feed

    # The clock keeps its own math: no feed state leaks into it.
    clock = _function_body(source, "syncTimeMs")
    assert "lastFedScoreMs" not in clock
    assert "FEED_JITTER_S" not in clock

    # The audio adapter stays as it was; only the feed knows the baseline.
    media_handler = _object_body(source, "const mediaHandler =")
    assert "lastFedScoreMs" not in media_handler

    # Seeking still rewinds: the transport seek feeds a forced position.
    assert "syncPosition(true)" in _function_body(source, "seekTo")


def test_score_end_guard_keeps_the_audio_playing():
    """v1.69: the clock holds the feed short of the score end.

    alphaTab finishes the song as soon as the fed position reaches the last
    bar: it pauses the output (our audio) and rewinds to tick 0, which cut
    songs whose tab ends before the recording. The guard belongs to the clock
    alone, so the audio adapter and the transport functions stay untouched.
    """
    source = _source()

    clock = _function_body(source, "syncTimeMs")
    assert "SCORE_END_GUARD_MS" in clock
    assert "scoreEndTimeMs()" in clock
    assert "audio.pause" not in clock

    # The audio adapter still pauses and plays exactly as before.
    media_handler = _object_body(source, "const mediaHandler =")
    pause_body = _block(media_handler, media_handler.index("pause()"))
    assert "SCORE_END_GUARD_MS" not in pause_body
    assert "audio.pause()" in pause_body

    # Only the clock clamps; seeking, pausing and toggling stay untouched.
    for name in PLAYBACK_FUNCTIONS:
        if name == "syncTimeMs":
            continue
        body = _function_body(source, name)
        assert "SCORE_END_GUARD_MS" not in body, f"{name} must not clamp the clock"

    toggle = _function_body(source, "togglePlayback")
    assert "audio.ended" not in toggle
    assert "api.stop()" not in toggle

    # After the song has run out, the gatekeeper rewinds once so PLAY restarts.
    handler = _function_body(source, "handlePlayButton")
    assert "audio.ended" in handler
    assert "api.stop()" in handler
    assert "togglePlayback()" in handler
    assert "beginCountIn()" in handler

