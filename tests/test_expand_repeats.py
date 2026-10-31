"""Guards for scripts/expand_repeats.py (v2.25).

The viewer's clock only counts written bars, so a GP tab with repeat marks
ends early (Slayer – Dead Skin Mask stopped at bar 68 of 96). The tool writes
every repeat block out as real bars; these tests pin the block detection and
the played order that the validation compares against.
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.expand_repeats import find_blocks, played_order  # noqa: E402


def _header(is_open: bool = False, close: int = -1, ending: int = 0):
    return SimpleNamespace(
        isRepeatOpen=is_open, repeatClose=close, repeatAlternative=ending
    )


def test_blocks_follow_the_tab_marks():
    # bars 2-3 x2, bar 4 once, bars 5-6 x4 (GP: repeatClose = extra passes)
    headers = [
        _header(),
        _header(is_open=True),
        _header(),
        _header(close=1),
        _header(),
        _header(is_open=True),
        _header(),
        _header(close=3),
    ]
    song = SimpleNamespace(measureHeaders=headers)
    blocks = find_blocks(song)
    assert [(b["start"], b["close"], b["plays"]) for b in blocks] == [
        (1, 3, 2),
        (5, 7, 4),
    ]


def test_zero_and_negative_close_mean_no_repeat():
    """A rewritten GP5 stores 0 for "no repeat"; that is not a block."""
    song = SimpleNamespace(
        measureHeaders=[
            _header(is_open=True),
            _header(close=0),
            _header(close=-1),
        ]
    )
    assert find_blocks(song) == []


def test_played_order_expands_the_repeats():
    song = SimpleNamespace(
        measureHeaders=[
            _header(),
            _header(is_open=True),
            _header(),
            _header(close=1),
            _header(),
        ]
    )
    blocks = find_blocks(song)
    # bar 1, then bars 2-4 twice, then bar 5
    assert played_order(5, blocks) == [0, 1, 2, 3, 1, 2, 3, 4]


def test_alternate_ending_is_left_out_of_the_last_pass():
    headers = [
        _header(is_open=True),
        _header(),
        _header(close=1, ending=1),
    ]
    blocks = find_blocks(SimpleNamespace(measureHeaders=headers))
    assert blocks[0]["endings"] == {2: 1}
    # pass 1 plays bars 1-3, pass 2 skips the 1st ending (bar 3)
    assert played_order(3, blocks) == [0, 1, 2, 0, 1]
