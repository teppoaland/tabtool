# 📊 Projektin edistyminen – TABTOOL

## Memory bank -protokolla (18.10.2026)

- `.clinerules/00-memory-bank.md` lisätty.
- Trigger: **`lue membank`** / `lue memory bank` / `alusta sessio` /
  `aloita uusi sessio`.
- Lukee 5 memory-bank-tiedostoa + `.clinerules/*`, ajaa git-tilan ja
  `pytest -q`, raportoi 3–6 riviä ja jatkaa `activeContext.md`:n
  seuraavasta vaiheesta.
- Memory bank -muutokset `docs:`-commitilla, ei versiobumppia.

## v1.20 – Phase 2: web-UI, job-jono ja alphaTab (18.10.2026)

### Muutokset

- `app/db.py`: SQLite (`tracks`, `jobs`, `tabs`, `oauth_tokens`,
  `settings`), `data/`-juureen sidotut polkuapurit, CLI-tabien import.
- `app/jobs.py`: yksi worker, stage-progress, SSE-tilaukset, cache ja
  `regenerate`; tabit kirjoitetaan temp-hakemistoon ja `os.replace`lla.
- `app/main.py`: `POST /api/jobs` (upload / YouTube / local path),
  job- ja tab-reitit, inline score, attachment-export, Range-audio.
- UI: lomake, status-rivi, kirjasto, alphaTab-katselin, `PLAY`/`PAUSE`,
  `EXPORT`, `?tab=<id>`-syvälinkki.
- alphaTab 1.8.4 vendoroituna (`app/static/vendor/alphaTab/`), Bravura
  fontti, `IExternalMediaHandler` + 50 ms positiosynkka.
- 45 pytest-testiä (API, cache, validoinnit, polkuturva, import).

### Validointi

- Oikea putki nopeassa tilassa: 12 tahtia, 58 nuottia; GP5 takaisinluettu
  (78 merkintää); MusicXML jäsentyy; Range-audio 206.
- 137 tahdin tabi renderöityi headless-Chromessa (30 254 px, ink OK).
- Browser-validoinnissa korjattiin: fonttipolun trailing slash,
  `PlayerState`-enumin puuttuminen UMD-globalista, `useWorkers: false`.

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

- `pytest -q` → **45 passed**
- `compileall` → OK
- `node --check app.js` / `remote.js` → OK
- `test.bat` → exit 0

## Tunnetut rajoitukset

- AI-transkriptio on luonnos; särö/akordit/nopeat soolot virheellisiä.
- Standard E -alueen ulkopuoliset nuotit pudotetaan varoituksella.
- Tempo voi olla half/double-time; normalisoidaan 70–180 BPM.
- Ei manuaalista editoria; GP5 korjataan Guitar Prossa/TuxGuitarissa.
- Toisto on testattu handler-tasolla; käyttäjän kuuntelutesti puuttuu.
- Rummut vaativat oman mallin.
- Spotify-integraatio puuttuu; Phase 3.
- Remote-näkymä on yhä pelkkä shell; Phase 4.

## Seuraavaksi

Phase 3 / v1.30: Spotify PKCE + haku/metadata, Web Playback SDK tai
Connect-laite, tokenit `oauth_tokens`-tauluun ja mockatut API-testit.
Tämän jälkeen Phase 4: remote-kaukosäädin.
