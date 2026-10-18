# 📊 Projektin edistyminen – TABTOOL

## v1.11 – Tie-korjaus ja validointi (18.10.2026)

### Muutokset

- GP5/MusicXML: tie-tila nuottikohtainen; uudet ja jatkuvat nuotit
  samassa segmentissä saavat oikean tilan.
- Uusi testi `test_tie_state_is_per_note`.
- 30 pytest-testiä.

### Validointi

- KISS – I’m A Legend Tonight (YouTube, 4:00): 137 tahtia,
  1413 tab-nuottia, GP5 validi, 0 rikkinäistä tahtikestoa,
  0 duplicate string -beatiä.
- MusicXML: 137 tahtia, 3050 tab-nuottimerkintää.
- MIDI: 1413 nuottia.

## v1.10 – Audio-to-tab-putki (18.10.2026)

### Muutokset

- `app/pipeline/`: audio_source, separate, transcribe, tempo, quantize,
  fretboard, segments, build, export_gp5, export_musicxml, export_midi.
- `scripts/pipeline_smoke.py`.
- Demucs `htdemucs_6s`, 4-stem fallback, `--no-separation`.
- Tempo 70–180 BPM -normalisointi.
- Kielikohtainen monofonia.
- Fretboard-Viterbi ja virityspresetit.
- GP5/MusicXML/MIDI-export.
- 29 pytest-testiä.

### Validointi

- Diablo – Mimic 47 (3:10 MP3): 108 tahtia, 884 tab-nuottia,
  GP5 validi, ~67 s CPU:lla.
- KISS 20 s YouTube-klipit: putki toimii; mainokset eivät tule mukaan.
- Demucs 6s erottaa guitar/bass/drums/vocals/other/piano.

## v1.00 – Runko (18.10.2026)

- git init + origin, `.gitignore`, `.clinerules/` (6 sääntöä),
  README/CHANGELOG/LICENSE/THIRD_PARTY_NOTICES.
- FastAPI: `/`, `/display`, `/remote`, `/api/health`, `/api/version`,
  `/api/config`.
- setup.bat, install-ml.bat, start.bat, test.bat.
- Ensimmäiset testit.

## Testitilanne

- `pytest -q` → **30 passed**
- `compileall` → OK
- `node --check app.js` / `remote.js` → OK
- `test.bat` → exit 0

## Tunnetut rajoitukset

- AI-transkriptio on luonnos; särö/akordit/nopeat soolot virheellisiä.
- Standard E -alueen ulkopuoliset nuotit pudotetaan varoituksella.
- Tempo voi olla half/double-time; normalisoidaan 70–180 BPM.
- Ei manuaalista editoria; GP5 korjataan Guitar Prossa/TuxGuitarissa.
- Web-UI ei vielä näytä tabia; alphaTab tulee Phase 2:ssa.
- Spotify-integraatio puuttuu; Phase 3.
- Rummut vaativat oman mallin.

## Seuraavaksi

Phase 2 / v1.20: SQLite + job-jono + cache + alphaTab + paikallinen
toisto + API-testit. Tämän jälkeen Phase 3: Spotify.
