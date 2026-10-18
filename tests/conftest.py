"""Make the project root importable when pytest is run from any directory."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import app.config as config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture()
def data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Isolate the private data directory for a single test."""
    root = tmp_path / "data"
    root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(config, "DATA_DIR", root)
    monkeypatch.setattr(config, "EXTERNAL_DIR", root / "external")
    return root


@pytest.fixture()
def client(data_dir: Path) -> TestClient:
    return TestClient(app)

