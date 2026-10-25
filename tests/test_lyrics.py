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
    """v2.08: the floating editor is resizable and remembers its size."""
    html = INDEX_HTML.read_text(encoding="utf-8")
    assert 'id="lyrics-resize"' in html

    source = APP_JS.read_text(encoding="utf-8")
    for name in ("startLyricsResize", "moveLyricsResize", "sizeLyricsPanel"):
        body = _js_code(source, name)
        assert "audio" not in body, f"{name} must not touch the audio element"
        assert "api." not in body, f"{name} must not call the alphaTab API"

    assert 'lyricsResizer.addEventListener("pointerdown", startLyricsResize)' in source
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


def test_corrupt_sidecar_reads_as_no_lyrics(
    client: TestClient, data_dir: Path
) -> None:
    _make_tab(data_dir, "lyrics-corrupt")
    target = data_dir / "lyrics" / "lyrics-corrupt.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("{ this is not json", encoding="utf-8")
    payload = client.get("/api/tabs/lyrics-corrupt/lyrics").json()
    assert payload["measures"] == {}
