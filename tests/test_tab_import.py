from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app import config
from app.pipeline.build import build_document
from app.pipeline.export_gp5 import export_gp5
from app.pipeline.model import D_STANDARD_TUNING, STANDARD_TUNING, TabNote


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


def _gp4_bytes(tmp_path: Path) -> bytes:
    """A GP4 copy of the same song (legacy tabs are often only GP4)."""
    import guitarpro

    source = tmp_path / "source.gp5"
    source.write_bytes(_gp5_bytes(tmp_path))
    song = guitarpro.parse(str(source))
    path = tmp_path / "import.gp4"
    guitarpro.write(song, str(path), version=(4, 0, 6))
    return path.read_bytes()


def _gp3_bytes(tmp_path: Path) -> bytes:
    """A GP3 copy with a dead grace note (fret -1, a real-world GP3 value)."""
    import guitarpro

    source = tmp_path / "source.gp5"
    source.write_bytes(_gp5_bytes(tmp_path))
    song = guitarpro.parse(str(source))
    note = song.tracks[0].measures[0].voices[0].beats[0].notes[0]
    note.effect.grace = guitarpro.models.GraceEffect(fret=-1)
    path = tmp_path / "import.gp3"
    guitarpro.write(song, str(path), version=(3, 0, 0))
    return path.read_bytes()


def test_import_keeps_non_standard_tuning(
    client: TestClient, tmp_path: Path
) -> None:
    document = build_document(
        title="D Standard Song",
        artist="Test Band",
        bpm=100,
        time_signature="4/4",
        tuning=D_STANDARD_TUNING,
        tab_notes=[TabNote(38, 6, 0, 0, 960)],
        measure_count=1,
    )
    path = tmp_path / "dstandard.gp5"
    export_gp5(document, path)

    response = client.post(
        "/api/tabs/import",
        files={
            "file": (
                "dstandard.gp5",
                path.read_bytes(),
                "application/octet-stream",
            )
        },
    )
    assert response.status_code == 200, response.text
    summary = response.json()
    tab = client.get(f"/api/tabs/{summary['id']}").json()

    assert tab["tuning"] == "d_standard"
    assert tab["meta"]["tuning_label"] == "D Standard · DGCFAD"
    assert tab["meta"]["tuning_notes"] == ["D2", "G2", "C3", "F3", "A3", "D4"]
    assert summary["tuning_label"] == "D Standard · DGCFAD"


def test_import_gp4_is_converted_to_gp5(
    client: TestClient, tmp_path: Path
) -> None:
    data = _gp4_bytes(tmp_path)
    assert b"FICHIER GUITAR PRO v4" in data[:32]

    response = client.post(
        "/api/tabs/import",
        files={"file": ("legacy.gp4", data, "application/octet-stream")},
    )
    assert response.status_code == 200, response.text
    summary = response.json()
    assert summary["title"] == "Imported Song"
    assert summary["artist"] == "Imported Band"
    assert summary["measure_count"] == 1
    assert summary["note_count"] == 1

    tab = client.get(f"/api/tabs/{summary['id']}").json()
    assert tab["meta"]["files"]["gp5"] == "tab.gp5"

    score = client.get(f"/api/tabs/{summary['id']}/score/gp5")
    assert score.status_code == 200
    assert b"FICHIER GUITAR PRO v5" in score.content[:32]

    archived = config.EXTERNAL_DIR / "tabs" / "Imported Band - Imported Song.gp5"
    assert archived.is_file()
    assert b"FICHIER GUITAR PRO v5" in archived.read_bytes()[:32]


def test_import_gp3_is_converted_to_gp5(client: TestClient, tmp_path: Path) -> None:
    """v1.99: a GP3 grace note with fret -1 must not fail the conversion."""
    data = _gp3_bytes(tmp_path)
    assert b"FICHIER GUITAR PRO v3" in data[:32]

    response = client.post(
        "/api/tabs/import",
        files={"file": ("legacy.gp3", data, "application/octet-stream")},
    )
    assert response.status_code == 200, response.text
    summary = response.json()
    assert summary["title"] == "Imported Song"
    assert summary["artist"] == "Imported Band"

    tab = client.get(f"/api/tabs/{summary['id']}").json()
    assert tab["meta"]["files"]["gp5"] == "tab.gp5"

    score = client.get(f"/api/tabs/{summary['id']}/score/gp5")
    assert score.status_code == 200
    assert b"FICHIER GUITAR PRO v5" in score.content[:32]

    import guitarpro

    written = tmp_path / "written.gp5"
    written.write_bytes(score.content)
    song = guitarpro.parse(str(written))
    grace = song.tracks[0].measures[0].voices[0].beats[0].notes[0].effect.grace
    assert grace is not None
    assert grace.fret == 0
    assert grace.isDead is True


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

    archived = config.EXTERNAL_DIR / "tabs" / "Imported Band - Imported Song.gp5"
    assert archived.is_file()
    assert archived.read_bytes() == data


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
