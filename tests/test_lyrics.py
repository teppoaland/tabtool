"""Sanat (v2.06): the lyrics sidecar stays outside the tab.

The feature is decoupled on purpose: the GP5/MusicXML/MIDI and the tab
metadata are read-only in these tests, and the sidecar is the only file that
may appear. The playback chain (rule 07) is not involved.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import db, lyrics, settings
from app.pipeline.build import build_document
from app.pipeline.export_gp5 import export_gp5
from app.pipeline.model import STANDARD_TUNING, TabNote


def _make_tab(data_dir: Path, tab_id: str = "lyrics-tab") -> Path:
    document = build_document(
        title="Lyric Song",
        artist="Lyric Band",
        bpm=120,
        time_signature="4/4",
        tuning=STANDARD_TUNING,
        tab_notes=[TabNote(40, 6, 0, 0, 960)],
        measure_count=4,
    )
    tab_dir = data_dir / "tabs" / tab_id
    tab_dir.mkdir(parents=True)
    export_gp5(document, tab_dir / "tab.gp5")
    meta = {
        "source_type": "import",
        "files": {"gp5": "tab.gp5"},
        "bpm": 120.0,
    }
    (tab_dir / "meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    track_id = db.create_track(
        title="Lyric Song",
        artist="Lyric Band",
        source_type="import",
        source_ref=f"import:{tab_id}",
        fingerprint=f"lyrics:{tab_id}",
    )
    db.create_tab(
        tab_id=tab_id,
        track_id=track_id,
        cache_key=f"lyrics:{tab_id}",
        directory=f"tabs/{tab_id}",
        title="Lyric Song",
        artist="Lyric Band",
        bpm=120.0,
        tuning="standard",
        time_signature="4/4",
        measure_count=4,
        note_count=1,
        audio_path="",
        meta=meta,
    )
    return tab_dir


def test_lyrics_default_to_empty(client: TestClient, data_dir: Path) -> None:
    _make_tab(data_dir, "lyrics-empty")
    response = client.get("/api/tabs/lyrics-empty/lyrics")
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["tab_id"] == "lyrics-empty"
    assert payload["measures"] == {}
    assert payload["notes"] == ""
    assert payload["bars"] == 4
    assert not (data_dir / "lyrics" / "lyrics-empty.json").exists()


def test_lyrics_unknown_tab(client: TestClient) -> None:
    assert client.get("/api/tabs/does-not-exist/lyrics").status_code == 404
    response = client.put(
        "/api/tabs/does-not-exist/lyrics", json={"measures": {"1": "x"}}
    )
    assert response.status_code == 404


def test_lyrics_round_trip_leaves_the_tab_untouched(
    client: TestClient, data_dir: Path
) -> None:
    tab_dir = _make_tab(data_dir, "lyrics-save")
    gp5_before = (tab_dir / "tab.gp5").read_bytes()
    meta_before = (tab_dir / "meta.json").read_bytes()

    response = client.put(
        "/api/tabs/lyrics-save/lyrics",
        json={"measures": {"10": "Eka rivi", "2": "Toinen rivi", "11": "Jatkuu"}},
    )
    assert response.status_code == 200, response.text
    saved = response.json()
    assert saved["measures"] == {
        "2": "Toinen rivi",
        "10": "Eka rivi",
        "11": "Jatkuu",
    }
    assert saved["bars"] == 4

    stored = client.get("/api/tabs/lyrics-save/lyrics").json()
    assert stored["measures"] == saved["measures"]

    sidecar = json.loads(
        (data_dir / "lyrics" / "lyrics-save.json").read_text(encoding="utf-8")
    )
    assert sidecar["measures"]["10"] == "Eka rivi"
    assert sidecar["updated_at"]

    # The tab itself is input data: lyrics may never rewrite it.
    assert (tab_dir / "tab.gp5").read_bytes() == gp5_before
    assert (tab_dir / "meta.json").read_bytes() == meta_before
    assert db.get_tab("lyrics-save")["meta"]["files"] == {"gp5": "tab.gp5"}


def test_lyrics_normalize_and_drop_empty_lines(
    client: TestClient, data_dir: Path
) -> None:
    _make_tab(data_dir, "lyrics-normalize")
    response = client.put(
        "/api/tabs/lyrics-normalize/lyrics",
        json={"measures": {"3": "  kaksi   sanaa  ", "4": "   ", "05": "viisi"}},
    )
    assert response.status_code == 200, response.text
    assert response.json()["measures"] == {"3": "kaksi sanaa", "5": "viisi"}


@pytest.mark.parametrize(
    "measures",
    [
        {"nolla": "teksti"},
        {"0": "teksti"},
        {"-1": "teksti"},
        {"1": 42},
        {"1": "x" * 301},
        ["ei", "taulukko"],
    ],
)
def test_lyrics_reject_invalid_measures(
    client: TestClient, data_dir: Path, measures: object
) -> None:
    _make_tab(data_dir, "lyrics-invalid")
    response = client.put(
        "/api/tabs/lyrics-invalid/lyrics", json={"measures": measures}
    )
    assert response.status_code == 422, response.text
    assert not (data_dir / "lyrics" / "lyrics-invalid.json").exists()


def test_lyrics_save_is_atomic(client: TestClient, data_dir: Path) -> None:
    _make_tab(data_dir, "lyrics-atomic")
    assert (
        client.put(
            "/api/tabs/lyrics-atomic/lyrics", json={"measures": {"1": "eka"}}
        ).status_code
        == 200
    )
    assert (
        client.put(
            "/api/tabs/lyrics-atomic/lyrics", json={"measures": {"2": "toka"}}
        ).status_code
        == 200
    )
    files = sorted(path.name for path in (data_dir / "lyrics").iterdir())
    assert files == ["lyrics-atomic.json"]
    stored = json.loads(
        (data_dir / "lyrics" / "lyrics-atomic.json").read_text(encoding="utf-8")
    )
    assert stored["measures"] == {"2": "toka"}


def test_locked_tab_still_accepts_lyrics(
    client: TestClient, data_dir: Path
) -> None:
    """The lock protects the tab and its playback settings, not the sidecar."""
    _make_tab(data_dir, "lyrics-locked")
    db.update_tab_library("lyrics-locked", locked=True)
    response = client.put(
        "/api/tabs/lyrics-locked/lyrics", json={"measures": {"1": "lukittu"}}
    )
    assert response.status_code == 200, response.text
    assert response.json()["measures"] == {"1": "lukittu"}


def test_deleting_a_tab_removes_its_lyrics(
    client: TestClient, data_dir: Path
) -> None:
    _make_tab(data_dir, "lyrics-delete")
    sidecar = data_dir / "lyrics" / "lyrics-delete.json"
    assert (
        client.put(
            "/api/tabs/lyrics-delete/lyrics", json={"measures": {"1": "pois"}}
        ).status_code
        == 200
    )
    assert sidecar.is_file()
    assert client.delete("/api/tabs/lyrics-delete").status_code == 200
    assert not sidecar.exists()


def test_lyrics_path_cannot_escape_the_sidecar_folder() -> None:
    with pytest.raises(ValueError):
        lyrics.lyrics_path("../tab")
    with pytest.raises(ValueError):
        lyrics.lyrics_path("..")
    assert lyrics.lyrics_path("abc-123").name == "abc-123.json"


INDEX_HTML = Path(__file__).resolve().parents[1] / "app" / "static" / "index.html"
APP_JS = Path(__file__).resolve().parents[1] / "app" / "static" / "app.js"


def _js_function(source: str, name: str) -> str:
    start = source.index(f"function {name}(")
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
    raise AssertionError(f"unbalanced braces around {name}")


def _js_code(source: str, name: str) -> str:
    """Function body without comments, so docs may name audio/api."""
    body = _js_function(source, name)
    body = re.sub(r"/\*.*?\*/", "", body, flags=re.S)
    return re.sub(r"//[^\n]*", "", body)


def test_lyrics_editor_floats_above_the_player():
    """v2.07: the editor is a draggable panel, not a modal.

    The lyrics have to be placed by ear, so the song must keep playing while
    the editor is open: no backdrop, no body.modal-open (that would hide the
    cursor) and no full-screen click shield.
    """
    html = INDEX_HTML.read_text(encoding="utf-8")
    start = html.index('id="lyrics-dialog"')
    open_tag = html[html.rindex("<div", 0, start) : html.index(">", start)]
    assert "lyrics-float" in open_tag
    assert "modal-backdrop" not in open_tag
    assert "aria-modal" not in open_tag
    assert 'id="lyrics-handle"' in html
    assert 'id="lyrics-bar-badge"' in html

    source = APP_JS.read_text(encoding="utf-8")
    opener = _js_function(source, "openLyricsDialog")
    assert 'classList.add("modal-open")' not in opener
    assert "showLyricsPanel" in opener

    for name in ("startLyricsDrag", "moveLyricsDrag", "placeLyricsPanel", "showLyricsPanel"):
        body = _js_function(source, name)
        assert "audio" not in body, f"{name} must not touch the audio element"
        assert "api." not in body, f"{name} must not call the alphaTab API"

    # Dragging is wired through pointer events on the header only.
    assert 'lyricsHandle.addEventListener("pointerdown", startLyricsDrag)' in source
    assert "pointermove" in source and "pointerup" in source


def test_lyrics_editor_can_be_resized():
    """v2.08–v2.11: the floating editor is resizable from either corner."""
    html = INDEX_HTML.read_text(encoding="utf-8")
    assert html.count('class="lyrics-resize"') == 2
    assert 'data-corner="nw"' in html
    assert 'data-corner="se"' in html

    source = APP_JS.read_text(encoding="utf-8")
    for name in ("startLyricsResize", "moveLyricsResize", "sizeLyricsPanel"):
        body = _js_code(source, name)
        assert "audio" not in body, f"{name} must not touch the audio element"
        assert "api." not in body, f"{name} must not call the alphaTab API"

    # Both grips run the same handler; the corner comes from the element.
    assert 'document.querySelectorAll(".lyrics-resize")' in source
    assert 'grip.addEventListener("pointerdown", startLyricsResize)' in source
    start = _js_code(source, "startLyricsResize")
    assert "dataset.corner" in start
    move = _js_code(source, "moveLyricsResize")
    assert 'lyricsResize.corner === "nw"' in move

    assert "lyricsDialog.style.width" in source
    assert "lyricsDialog.style.height" in source
    saved = _js_function(source, "saveLyricsPanelPosition")
    assert "width" in saved and "height" in saved
    shown = _js_function(source, "showLyricsPanel")
    assert "sizeLyricsPanel" in shown


def test_lyrics_style_settings_drive_the_strip():
    """v2.08–v2.09: Settings -> Sanat -> size (default 200 %) and lift (100 px)."""
    defaults = {field.key: field.default for field in settings.FIELDS}
    assert defaults["lyrics.scale"] == 200
    assert defaults["lyrics.offset_px"] == 100
    scale = next(item for item in settings.FIELDS if item.key == "lyrics.scale")
    assert (scale.minimum, scale.maximum, scale.step) == (100, 400, 25)
    offset = next(
        item for item in settings.FIELDS if item.key == "lyrics.offset_px"
    )
    assert (offset.minimum, offset.maximum, offset.step) == (0, 600, 10)

    source = APP_JS.read_text(encoding="utf-8")
    runtime = _js_function(source, "applyRuntimeSettings")
    assert '"lyrics.scale"' in runtime
    assert '"lyrics.offset_px"' in runtime
    style = _js_code(source, "applyLyricsStyle")
    assert "--lyrics-scale" in style
    assert "--lyrics-offset" in style
    assert "audio" not in style and "api." not in style

    css = (INDEX_HTML.parent / "style.css").read_text(encoding="utf-8")
    assert "var(--lyrics-scale, 2)" in css
    # Fullscreen uses the whole width and the Settings lift.
    assert "var(--lyrics-offset, 100px)" in css
    assert "max-width: 96vw" in css


def test_lyrics_backdrop_is_opaque_black_with_side_padding():
    """v2.10: a solid black band reads better than a translucent one.

    3ch of empty space on both sides and a symmetric em padding keep the
    text centred in a taller band; the old translucent fill is gone.
    """
    css = (INDEX_HTML.parent / "style.css").read_text(encoding="utf-8")
    start = css.index(".lyrics-current {")
    block = css[start : css.index("}", start)]

    assert "background: #000;" in block
    assert "rgba(" not in block, "the backdrop must not be translucent"
    assert "padding: 0.55em 3ch;" in block
    assert "border: 1px" not in block


def test_lyrics_editor_has_playback_controls():
    """v2.12: PLAY/PAUSE, «, −5 s, +5 s and a bar click that seeks.

    The controls call the transport's existing functions and a bar click
    reuses mediaHandler.seekTo (the frozen score-time inverse), so the lyrics
    code keeps no second copy of the clock math.
    """
    html = INDEX_HTML.read_text(encoding="utf-8")
    for element in ("lyrics-play", "lyrics-start", "lyrics-back", "lyrics-forward"):
        assert f'id="{element}"' in html

    source = APP_JS.read_text(encoding="utf-8")
    jump = _js_code(source, "jumpToBar")
    # alphaTab's tick setter owns the tempo map (see the regression test).
    assert "api.tickPosition = startTick" in jump
    assert "masterBars" in jump
    for marker in (
        "syncDrift",
        "bpmDrift",
        "barDurationMs",
        "audio",
        "60000",
        "960",
    ):
        assert marker not in jump, f"jumpToBar must not compute the time itself: {marker}"

    assert (
        'lyricsPlayButton.addEventListener("click", () => handlePlayButton())'
        in source
    )
    assert 'lyricsStartButton.addEventListener("click", () => seekTo(0))' in source
    assert 'lyricsBackButton.addEventListener("click", () => seekBy(-5))' in source
    assert 'lyricsForwardButton.addEventListener("click", () => seekBy(5))' in source
    assert 'chip.addEventListener("click", () => jumpToBar(bar))' in source
    assert 'chip.addEventListener("dblclick", () => insertLyricsBar(bar))' in source

    # The editor button mirrors the real PLAY label instead of audio events.
    label = _js_code(source, "syncLyricsPlayLabel")
    assert "playButton.dataset.state" in label
    assert "audio" not in label


def test_lyrics_bar_list_and_editor_share_the_panel_height():
    """v2.13: taller bar list by default and a splitter that trades height.

    The bar list and the lyric textarea share the panel: growing the list
    shrinks the textarea, so a 258-bar song stays usable.
    """
    html = INDEX_HTML.read_text(encoding="utf-8")
    assert 'id="lyrics-split"' in html

    css = (INDEX_HTML.parent / "style.css").read_text(encoding="utf-8")
    start = css.index(".lyrics-bars {")
    bars = css[start : css.index("}", start)]
    assert "height: 14rem" in bars
    assert "max-height: 6.4rem" not in css
    form = css[css.index(".lyrics-form {"):]
    form_block = form[: form.index("}")]
    assert "flex: 1 1 auto" in form_block

    source = APP_JS.read_text(encoding="utf-8")
    split = _js_code(source, "moveLyricsSplit")
    assert "setLyricsBarsHeight" in split
    assert "audio" not in split and "api." not in split
    height = _js_code(source, "setLyricsBarsHeight")
    assert "lyricsBars.style.height" in height
    assert "audio" not in height and "api." not in height
    assert "barsHeight" in _js_function(source, "saveLyricsPanelPosition")
    assert "setLyricsBarsHeight" in _js_function(source, "showLyricsPanel")
    assert (
        'lyricsSplitter.addEventListener("pointerdown", startLyricsSplit)' in source
    )


def test_bar_click_selects_the_matching_lyric_line():
    """v2.16: « sits before PLAY and a bar click highlights its lyric line.

    Pressing bar 95 seeks (v2.12) and then selects the words of the
    "95 | …" line, so a line can be checked or rewritten without scrolling
    the field by hand. The lookup is pure string work and the selection is
    DOM only, so rule 07's playback chain is not touched.
    """
    html = INDEX_HTML.read_text(encoding="utf-8")
    controls = html[html.index('class="lyrics-controls"'):]
    controls = controls[: controls.index("</div>")]
    assert controls.index('id="lyrics-start"') < controls.index('id="lyrics-play"')

    source = APP_JS.read_text(encoding="utf-8")
    # The click goes through the v2.17 dispatcher, which falls back to the
    # line selection when nothing is selected.
    assert 'chip.addEventListener("click", () => handleLyricsBarClick(bar))' in source
    assert "focusLyricsBarLine" in _js_code(source, "handleLyricsBarClick")

    focus = _js_code(source, "focusLyricsBarLine")
    assert "lyricsBarLineRange" in focus
    assert "setSelectionRange" in focus
    assert "lyricsInput.scrollTop" in focus
    for marker in (
        "syncTimeMs",
        "bpmDrift",
        "barDurationMs",
        "playbackRate",
        "audio",
        "api.",
        "60000",
        "960",
    ):
        assert marker not in focus, f"focusLyricsBarLine must stay DOM only: {marker}"

    line_range = _js_code(source, "lyricsBarLineRange")
    # Same reading rule as parseLyricsText(): explicit number or continuation.
    assert "nextBar" in line_range
    assert "trimStart" in line_range
    for marker in ("querySelector", "getElementById", "api.", "audio"):
        assert marker not in line_range


def test_selected_words_move_into_the_pressed_bar():
    """v2.17: select words, press a bar -> that bar's line is written.

    A pasted block is consumed phrase by phrase: the selected words leave the
    field and come back as "N | …", so the number comes from the press instead
    of being typed by hand. Ctrl+Enter does the same for the anchor bar and
    steps one bar ahead, which numbers consecutive lines quickly. The helpers
    are string/DOM work only - rule 07's playback chain is not involved.
    """
    source = APP_JS.read_text(encoding="utf-8")
    assert 'lyricsInput.addEventListener("keydown", handleLyricsAssignKey)' in source

    handler = _js_code(source, "handleLyricsBarClick")
    assert "assignLyricsSelectionToBar" in handler
    assert "focusLyricsBarLine" in handler
    assert "lyricsAnchorBar = bar + 1" in handler

    assign = _js_code(source, "assignLyricsSelectionToBar")
    for marker in ("selectionStart", "selectionEnd", "setSelectionRange"):
        assert marker in assign
    assert "lyricsBarLineRange" in assign
    assert "lyricsLineSelection" in assign
    for marker in (
        "syncTimeMs",
        "bpmDrift",
        "barDurationMs",
        "playbackRate",
        "audio",
        "api.",
        "60000",
        "960",
    ):
        assert marker not in assign, f"assignLyricsSelectionToBar must stay DOM only: {marker}"

    key = _js_code(source, "handleLyricsAssignKey")
    assert '"Enter"' in key and "ctrlKey" in key
    for marker in ("audio", "api."):
        assert marker not in key

    # An old number on the picked line must not be copied into the new one.
    chunk = _js_code(source, "normalizeLyricChunk")
    assert "replace" in chunk and "[|:=\\t]" in chunk
    for marker in ("audio", "api."):
        assert marker not in chunk


def test_lyrics_lock_blocks_saves_until_it_is_opened(
    client: TestClient, data_dir: Path
) -> None:
    """v2.18: a finished lyric can be locked from the SANAT editor.

    The flag lives in the sidecar, so the tab files and the playback settings
    stay untouched. A locked lyric still reads normally but refuses a save
    with 409; clearing the box keeps the lines and makes them writable again.
    """
    tab_dir = _make_tab(data_dir, "lyrics-lyric-lock")
    gp5_before = (tab_dir / "tab.gp5").read_bytes()
    assert (
        client.put(
            "/api/tabs/lyrics-lyric-lock/lyrics", json={"measures": {"1": "eka"}}
        ).status_code
        == 200
    )

    locked = client.put(
        "/api/tabs/lyrics-lyric-lock/lyrics/lock", json={"locked": True}
    )
    assert locked.status_code == 200, locked.text
    payload = locked.json()
    assert payload["locked"] is True
    assert payload["measures"] == {"1": "eka"}

    blocked = client.put(
        "/api/tabs/lyrics-lyric-lock/lyrics", json={"measures": {"2": "toka"}}
    )
    assert blocked.status_code == 409, blocked.text
    read_back = client.get("/api/tabs/lyrics-lyric-lock/lyrics").json()
    assert read_back["locked"] is True
    assert read_back["measures"] == {"1": "eka"}

    stored = json.loads(
        (data_dir / "lyrics" / "lyrics-lyric-lock.json").read_text(encoding="utf-8")
    )
    assert stored["locked"] is True

    opened = client.put(
        "/api/tabs/lyrics-lyric-lock/lyrics/lock", json={"locked": False}
    )
    assert opened.status_code == 200
    assert opened.json()["measures"] == {"1": "eka"}
    assert (
        client.put(
            "/api/tabs/lyrics-lyric-lock/lyrics", json={"measures": {"2": "toka"}}
        ).status_code
        == 200
    )
    assert client.get("/api/tabs/lyrics-lyric-lock/lyrics").json()["measures"] == {
        "2": "toka"
    }
    # Locking never rewrites the tab itself.
    assert (tab_dir / "tab.gp5").read_bytes() == gp5_before


def test_lyrics_lock_route_validates_its_payload(
    client: TestClient, data_dir: Path
) -> None:
    _make_tab(data_dir, "lyrics-lock-invalid")
    assert (
        client.put(
            "/api/tabs/lyrics-lock-invalid/lyrics/lock", json={"locked": "yes"}
        ).status_code
        == 422
    )
    assert (
        client.put("/api/tabs/missing-tab/lyrics/lock", json={"locked": True}).status_code
        == 404
    )


def test_lyrics_gap_counts_down_and_finished_lyrics_can_be_locked():
    """v2.18: an empty bar counts down to the next line; a lock keeps it safe.

    The old overlay held the previous line over a gap, so the words of bar 76
    stayed on screen until 80. Now an empty bar is cleared: if a later line
    exists the strip shows 4, 3, 2, 1 as the singer's cue, and after the last
    line it hides. A finished lyric can be locked in the SANAT editor, which
    only writes the sidecar flag.
    """
    html = INDEX_HTML.read_text(encoding="utf-8")
    assert 'id="lyrics-lock"' in html
    assert "Lukittu" in html

    css = (INDEX_HTML.parent / "style.css").read_text(encoding="utf-8")
    assert ".lyrics-current.is-cue" in css

    source = APP_JS.read_text(encoding="utf-8")
    cue = _js_code(source, "lyricForBar")
    assert "nextLyricBar" in cue
    assert "String(next - start)" in cue
    assert "for (let index = start; index >= 1; index -= 1)" not in cue

    nxt = _js_code(source, "nextLyricBar")
    assert "lyricsMeasures" in nxt
    for marker in ("audio", "api."):
        assert marker not in nxt

    strip = _js_code(source, "renderLyricsStrip")
    assert "is-cue" in strip
    for marker in ("audio", "api."):
        assert marker not in strip

    lock = _js_code(source, "applyLyricsLock")
    assert "readOnly" in lock
    assert "lyricsSave" in lock
    for marker in ("audio", "api."):
        assert marker not in lock

    assign = _js_code(source, "assignLyricsSelectionToBar")
    assert "lyricsLocked" in assign

    toggle = _js_code(source, "toggleLyricsLock")
    assert "/lyrics/lock" in toggle
    assert "saveLyricsField" in toggle
    for marker in ("audio", "syncTimeMs", "barDurationMs", "playbackRate"):
        assert marker not in toggle

    assert 'lyricsLockInput.addEventListener("change", toggleLyricsLock)' in source


def test_sneak_peek_shows_the_next_line_one_bar_early():
    """v2.19: the next lyric line is previewed one bar early, 50 % smaller.

    The peek is a second band inside the same fixed overlay, under the main
    line, so the frozen layout and the playback chain stay untouched. The
    Settings switch (lyrics.sneak, default on) turns it off.
    """
    defaults = {field.key: field.default for field in settings.FIELDS}
    assert defaults["lyrics.sneak"] is True
    assert defaults["lyrics.sneak_position"] == "below"
    sneak = next(item for item in settings.FIELDS if item.key == "lyrics.sneak")
    assert sneak.kind == "bool" and sneak.group == "lyrics"
    position = next(
        item for item in settings.FIELDS if item.key == "lyrics.sneak_position"
    )
    assert position.kind == "choice" and position.group == "lyrics"
    assert [value for value, _label in position.options] == ["below", "above"]

    html = INDEX_HTML.read_text(encoding="utf-8")
    assert 'id="lyrics-next"' in html
    strip = html[html.index('id="lyrics-strip"'):]
    strip = strip[: strip.index("</div>")]
    assert strip.index('id="lyrics-current"') < strip.index('id="lyrics-next"')

    css = (INDEX_HTML.parent / "style.css").read_text(encoding="utf-8")
    container = css[css.index(".lyrics-strip {"):]
    container = container[: container.index("}")]
    # v2.23: below by default; .peek-above flips it when the setting says so.
    assert "flex-direction: column;" in container
    above = css[css.index(".lyrics-strip.peek-above {"):]
    above = above[: above.index("}")]
    assert "flex-direction: column-reverse" in above
    peek = css[css.index(".lyrics-next {"):]
    peek = peek[: peek.index("}")]
    assert "#000" in peek
    assert "* 0.5)" in peek

    source = APP_JS.read_text(encoding="utf-8")
    runtime = _js_function(source, "applyRuntimeSettings")
    assert '"lyrics.sneak"' in runtime
    assert '"lyrics.sneak_position"' in runtime
    peek_fn = _js_code(source, "lyricPeekForBar")
    assert "nextLyricBar" in peek_fn
    assert "next - start !== 1" in peek_fn
    assert "lyricsSneak" in peek_fn
    for marker in ("audio", "api.", "setTimeout"):
        assert marker not in peek_fn
    strip_fn = _js_code(source, "renderLyricsStrip")
    assert "lyricPeekForBar" in strip_fn
    assert "is-empty" in strip_fn
    for marker in ("audio", "api."):
        assert marker not in strip_fn
    sneak_fn = _js_code(source, "applyLyricsSneak")
    assert "has-peek" in sneak_fn and "lyricsSneak" in sneak_fn
    assert "peek-above" in sneak_fn and "lyricsSneakPosition" in sneak_fn
    # The band keeps its space while the setting is on (no jumping main line).
    assert "has-peek" in html
    assert ".lyrics-strip:not(.has-peek) .lyrics-next" in css


def test_lyrics_notes_are_saved_with_the_sidecar(
    client: TestClient, data_dir: Path
) -> None:
    """v2.20: a free-text memo keeps the source and the open questions.

    Notes ride in the same sidecar as the lines, so a half-finished lyric can
    say where it came from and what still needs fixing. The tab files stay
    untouched, an absent notes field keeps the stored note, and a locked
    sidecar refuses both with 409.
    """
    tab_dir = _make_tab(data_dir, "lyrics-notes")
    gp5_before = (tab_dir / "tab.gp5").read_bytes()
    memo = "Lähde: Songsterr 25.10.\nTahdit 41–44 kesken."
    saved = client.put(
        "/api/tabs/lyrics-notes/lyrics",
        json={"measures": {"1": "eka"}, "notes": memo},
    )
    assert saved.status_code == 200, saved.text
    payload = saved.json()
    assert payload["notes"] == memo
    assert payload["measures"] == {"1": "eka"}

    # A save that only sends measures keeps the stored note.
    again = client.put(
        "/api/tabs/lyrics-notes/lyrics", json={"measures": {"2": "toka"}}
    )
    assert again.status_code == 200
    assert again.json()["notes"] == memo

    stored = json.loads(
        (data_dir / "lyrics" / "lyrics-notes.json").read_text(encoding="utf-8")
    )
    assert stored["notes"] == memo

    # Locking keeps the note and blocks both the lines and the memo.
    assert (
        client.put(
            "/api/tabs/lyrics-notes/lyrics/lock", json={"locked": True}
        ).status_code
        == 200
    )
    blocked = client.put(
        "/api/tabs/lyrics-notes/lyrics",
        json={"measures": {"3": "kolmas"}, "notes": "uusi"},
    )
    assert blocked.status_code == 409
    read_back = client.get("/api/tabs/lyrics-notes/lyrics").json()
    assert read_back["notes"] == memo
    assert read_back["measures"] == {"2": "toka"}
    assert (tab_dir / "tab.gp5").read_bytes() == gp5_before


def test_lyrics_notes_are_validated(client: TestClient, data_dir: Path) -> None:
    _make_tab(data_dir, "lyrics-notes-bad")
    assert (
        client.put(
            "/api/tabs/lyrics-notes-bad/lyrics",
            json={"measures": {}, "notes": 42},
        ).status_code
        == 422
    )
    assert (
        client.put(
            "/api/tabs/lyrics-notes-bad/lyrics",
            json={"measures": {}, "notes": "x" * 4001},
        ).status_code
        == 422
    )
    # A whitespace-only note is stored as empty text.
    saved = client.put(
        "/api/tabs/lyrics-notes-bad/lyrics",
        json={"measures": {}, "notes": "  \n "},
    )
    assert saved.status_code == 200
    assert saved.json()["notes"] == ""


def test_lyrics_editor_has_a_notes_field():
    """v2.20: the memo is a plain textarea saved with TALLENNA.

    It lives in the same form, follows the lyric lock (read-only) and is
    loaded with the sidecar, so an unfinished job can be picked up later.
    """
    html = INDEX_HTML.read_text(encoding="utf-8")
    assert 'id="lyrics-notes"' in html
    assert "Muistiinpanot" in html

    source = APP_JS.read_text(encoding="utf-8")
    save_fn = _js_code(source, "saveLyricsField")
    assert "lyricsNotesInput" in save_fn
    assert "notes:" in save_fn
    assert "lyricsNotes" in _js_code(source, "fillLyricsDialog")
    assert "lyricsNotes" in _js_code(source, "loadLyrics")
    assert "lyricsNotesInput.readOnly" in _js_code(source, "applyLyricsLock")
    assert 'lyricsNotesInput.addEventListener("input"' in source

    css = (INDEX_HTML.parent / "style.css").read_text(encoding="utf-8")
    assert ".lyrics-notes {" in css
    assert ".lyrics-notes[readonly]" in css
    # The memo must not steal height from the lyric textarea.
    assert ".lyrics-form .lyrics-notes-field" in css
    assert 'class="field lyrics-notes-field"' in html


def test_bulk_fill_numbers_a_pasted_block():
    """v2.22: JAA RIVIT turns a pasted block into one line per bar.

    Select the remaining lyrics (or paste them), press the starting bar and
    hit the button / Ctrl+Shift+Enter: every non-empty line becomes
    "N | text" with consecutive numbers, the source lines are consumed and an
    existing line for a target bar is replaced. Pure DOM/string work, so rule
    07's playback chain is untouched.
    """
    html = INDEX_HTML.read_text(encoding="utf-8")
    assert 'id="lyrics-fill"' in html
    assert "JAA RIVIT" in html

    source = APP_JS.read_text(encoding="utf-8")
    assert (
        'lyricsFillButton.addEventListener("click", fillLyricsFromSelection)'
        in source
    )
    key = _js_code(source, "handleLyricsAssignKey")
    assert "event.shiftKey" in key and "fillLyricsFromSelection" in key

    fill = _js_code(source, "fillLyricsFromSelection")
    assert "assignLyricsBlockToBars" in fill
    for marker in ("audio", "api.", "syncTimeMs", "barDurationMs", "playbackRate"):
        assert marker not in fill

    bulk = _js_code(source, "assignLyricsBlockToBars")
    for marker in (
        "selectionStart",
        "selectionEnd",
        "lyricsLineRecords",
        "wholeLineRange",
        "removeTextRanges",
        "lyricsLocked",
    ):
        assert marker in bulk
    for marker in (
        "audio",
        "api.",
        "syncTimeMs",
        "bpmDrift",
        "barDurationMs",
        "playbackRate",
        "60000",
        "960",
    ):
        assert marker not in bulk, f"the bulk fill must stay DOM only: {marker}"

    records = _js_code(source, "lyricsLineRecords")
    assert "numbered" in records
    for marker in ("audio", "api."):
        assert marker not in records


def test_bar_seek_uses_the_tempo_aware_tick_path():
    """v2.14: a tempo automation must not shift the bar seek.

    Seek & Destroy changes tempo at bar 113 (208 BPM). The first bar jump
    computed the score time from a single tempo, so every bar after ~116
    landed later and later (bar 220 showed bar 235). alphaTab's tickPosition
    setter converts the tick with the score's tempo map, maps it onto the
    backing track and calls the frozen mediaHandler.seekTo() inverse - the
    same path a click on the score already uses.
    """
    jump = _js_code(APP_JS.read_text(encoding="utf-8"), "jumpToBar")
    assert "api.tickPosition = startTick" in jump
    assert "mediaHandler.seekTo" not in jump
    assert "notatedTempo" not in jump
    assert "60000" not in jump
    assert "960" not in jump


def test_corrupt_sidecar_reads_as_no_lyrics(
    client: TestClient, data_dir: Path
) -> None:
    _make_tab(data_dir, "lyrics-corrupt")
    target = data_dir / "lyrics" / "lyrics-corrupt.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("{ this is not json", encoding="utf-8")
    payload = client.get("/api/tabs/lyrics-corrupt/lyrics").json()
    assert payload["measures"] == {}
