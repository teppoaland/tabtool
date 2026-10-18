"""Tempo normalization tests."""

from __future__ import annotations

from app.pipeline.tempo import normalize_bpm


def test_half_time_is_doubled() -> None:
    assert normalize_bpm(68.0) == 136.0


def test_fast_tempo_is_halved() -> None:
    assert normalize_bpm(240.0) == 120.0


def test_normal_range_is_unchanged() -> None:
    assert normalize_bpm(136.0) == 136.0


def test_invalid_tempo_is_returned() -> None:
    assert normalize_bpm(0.0) == 0.0
