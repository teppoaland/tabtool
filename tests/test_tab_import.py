from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.pipeline.build import build_document
from app.pipeline.export_gp5 import export_gp5
from app.pipeline.model import STANDARD_TUNING, TabNote


def _gp5_bytes(tmp_path: Path) -> bytes:
    document = build_document(
        title="Imported Song",
        artist="Imported Band",
        bpm=100,
        time_signature="4/4",
        tuning=STANDARD_TUNING,
        tab_notes=[TabNote(40, 6, 0, 0, 960)],
        measure_count=1,
    )
    path = tmp_path / "import.gp5"
    export_gp5(document, path)
    return path.read_bytes()


def test_import_gp5(client: TestClient, tmp_path: Path) -> None:
    data = _gp5_bytes(tmp_path)
    response = client.post(
        "/api/tabs/import",
        files={"file": ("imported.gp5", data, "application/octet-stream")},
    )
    assert response.status_code == 200, response.text
    summary = response.json()
    assert summary["title"] == "Imported Song"
    assert summary["artist"] == "Imported Band"

    tab = client.get(f"/api/tabs/{summary['id']}").json()
    assert tab["title"] == "Imported Song"
    assert tab["artist"] == "Imported Band"
    assert tab["audio_path"] == ""
    assert tab["meta"]["files"]["gp5"] == "tab.gp5"
    assert tab["meta"]["source_type"] == "import"

    score = client.get(f"/api/tabs/{summary['id']}/score/gp5")
    assert score.status_code == 200
    assert score.content == data


def test_import_rejects_unsupported_extension(client: TestClient) -> None:
    response = client.post(
        "/api/tabs/import",
        files={"file": ("notes.pdf", b"%PDF", "application/pdf")},
    )
    assert response.status_code == 415


def test_import_rejects_invalid_gp5(client: TestClient) -> None:
    response = client.post(
        "/api/tabs/import",
        files={
            "file": (
                "broken.gp5",
                b"not a guitar pro file",
                "application/octet-stream",
            )
        },
    )
    assert response.status_code == 422


def test_import_musicxml(client: TestClient, tmp_path: Path) -> None:
    from music21 import metadata, meter, note, stream, tempo

    score = stream.Score()
    score.metadata = metadata.Metadata()
    score.metadata.title = "XML Song"
    score.metadata.composer = "XML Band"
    part = stream.Part()
    part.append(meter.TimeSignature("4/4"))
    part.append(tempo.MetronomeMark(number=100))
    measure = stream.Measure(number=1)
    measure.append(note.Note("E2", quarterLength=1))
    part.append(measure)
    score.insert(0, part)
    path = tmp_path / "import.musicxml"
    score.write("musicxml", fp=str(path))
    data = path.read_bytes()

    response = client.post(
        "/api/tabs/import",
        files={"file": ("song.musicxml", data, "application/xml")},
    )
    assert response.status_code == 200, response.text
    summary = response.json()
    assert summary["title"] == "XML Song"
    assert summary["artist"] == "XML Band"

    tab = client.get(f"/api/tabs/{summary['id']}").json()
    assert tab["meta"]["files"]["musicxml"] == "tab.musicxml"
    assert tab["measure_count"] >= 1
    assert tab["note_count"] >= 1

    score_response = client.get(f"/api/tabs/{summary['id']}/score/musicxml")
    assert score_response.status_code == 200
    assert score_response.content == data
