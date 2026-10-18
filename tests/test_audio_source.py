import subprocess

from app import jobs
from app.pipeline import audio_source


def test_clean_youtube_title() -> None:
    assert (
        audio_source.clean_youtube_title("Seek & Destroy (Remastered)")
        == "Seek & Destroy"
    )
    assert audio_source.clean_youtube_title("Song [Official Music Video]") == "Song"
    assert (
        audio_source.clean_youtube_title("Song (Official Audio) (Remastered)")
        == "Song"
    )
    assert audio_source.clean_youtube_title("Plain Title") == "Plain Title"
    assert audio_source.clean_youtube_title("") == ""


def test_fetch_youtube_metadata_parses_ytdlp_output(monkeypatch) -> None:
    def fake_run(command: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            command,
            0,
            stdout="Seek & Destroy (Remastered)\nMetallica\nMetallica\n",
            stderr="",
        )

    monkeypatch.setattr(audio_source, "_run", fake_run)
    assert audio_source.fetch_youtube_metadata("https://youtu.be/example") == (
        "Seek & Destroy",
        "Metallica",
    )


def test_fetch_youtube_metadata_falls_back_to_uploader(monkeypatch) -> None:
    def fake_run(command: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            command,
            0,
            stdout="Some Song\nNA\nSome Channel\n",
            stderr="",
        )

    monkeypatch.setattr(audio_source, "_run", fake_run)
    assert audio_source.fetch_youtube_metadata("https://youtu.be/example") == (
        "Some Song",
        "Some Channel",
    )


def test_effective_track_metadata_prefers_real_metadata() -> None:
    assert jobs.effective_track_metadata(
        "YouTube audio", "", "Seek & Destroy", "Metallica"
    ) == ("Seek & Destroy", "Metallica")
    assert jobs.effective_track_metadata("My Song", "Band", "Other", "") == (
        "My Song",
        "Band",
    )
    assert jobs.effective_track_metadata("", "", "", "") == ("Untitled", "")
