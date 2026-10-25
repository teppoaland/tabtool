"""v2.24: the viewer bar has a « button left of PLAY that jumps to the start.

The button only calls the existing seekTo(0) - the same call the lyrics editor
and the remote already make - so rule #1's playback chain is untouched. These
tests guard the placement, the layout wrapper and that single call.
"""

from pathlib import Path

STATIC = Path(__file__).resolve().parents[1] / "app" / "static"
APP_JS = STATIC / "app.js"
INDEX_HTML = STATIC / "index.html"
STYLE_CSS = STATIC / "style.css"


def _html() -> str:
    return INDEX_HTML.read_text(encoding="utf-8")


def _source() -> str:
    return APP_JS.read_text(encoding="utf-8")


def test_viewer_bar_has_start_button_before_play():
    html = _html()
    bar = html[html.index('class="viewer-bar"'):]
    bar = bar[: bar.index('<div class="transport"')]
    assert 'id="seek-start"' in bar
    assert bar.index('id="seek-start"') < bar.index('id="play-button"')


def test_start_button_shares_the_play_grid_cell():
    """« and PLAY sit in one flex cell, so .viewer-bar keeps its columns."""
    html = _html()
    assert '<div class="viewer-start">' in html
    css = STYLE_CSS.read_text(encoding="utf-8")
    block = css[css.index(".viewer-start {"):]
    block = block[: block.index("}")]
    assert "display: flex" in block
    bar = css[css.index(".viewer-bar {"):]
    bar = bar[: bar.index("}")]
    assert "grid-template-columns: auto minmax(0, 1fr) auto;" in bar


def test_start_button_seeks_to_the_beginning():
    source = _source()
    assert 'document.getElementById("seek-start")' in source
    assert 'seekStart.addEventListener("click", () => seekTo(0));' in source


def test_start_button_does_not_touch_the_playback_chain():
    source = _source()
    start = source.index('seekStart.addEventListener("click"')
    snippet = source[start : source.index(");", start)]
    for forbidden in ("audio.", "api.", "playbackRate", "countInSkipped"):
        assert forbidden not in snippet
