# 📜 CHANGELOG – TABTOOL

> TabTool käyttää `1.x`-versiosarjaa. Aloitus `v1.00`.

## v1.20 – 18.10.2026

Phase 2 – web-käyttöliittymä, job-jono, cache, alphaTab ja paikallinen toisto.

### Muutokset

- `app/db.py`: SQLite-skeema (`tracks`, `jobs`, `tabs`, `oauth_tokens`,
  `settings`), cache-avain, `data/`-juureen sidotut polkuapurit ja
  CLI-tabien tuonti (`data/tabs/<nimi>/meta.json`).
- `app/jobs.py`: yhden workerin job-jono, vaihekohtainen progress
  (queued → downloading → separating → transcribing → building → ready),
  SSE-tilaukset, cache-osuma ilman uutta ajoa, `regenerate`-tuki.
- `app/main.py`: `POST /api/jobs` (upload / YouTube / local path),
  `GET /api/jobs`, `GET /api/jobs/{id}`, `GET /api/jobs/{id}/events`,
  `GET /api/tabs`, `GET /api/tabs/{id}`, inline `score/{fmt}`,
  attachment `export/{fmt}` ja Range-tuettu `audio`.
- UI: upload/YouTube-lomake, viritys/grid/nopea tila, status-rivi,
  kirjasto, alphaTab-katselin, `PLAY`/`PAUSE` ja `EXPORT`.
- alphaTab 1.8.4 vendoroituna (`app/static/vendor/alphaTab/`,
  MPL-2.0 + Bravura OFL), ulkoinen media `IExternalMediaHandler`illa ja
  50 ms positiosynkka.
- Tabit kirjoitetaan temp-hakemistoon ja `os.replace`lla; cache-avain =
  audion sormenjälki + pipeline-versio + asetukset.
- 45 pytest-testiä; API-, cache-, validointi- ja polkuturvatestit
  mockatulla putkella.

### Validointi

- Oikea putki nopeassa tilassa 20 s klipillä: 12 tahtia, 58 nuottia,
  GP5 luettu takaisin (78 nuottimerkintää), MusicXML jäsentyy.
- 137 tahdin KISS-tabi renderöityy alphaTabilla headless-Chromessa
  (30 254 px korkea sivu, nuottimerkinnät piirtyvät).
- 46 MB WAV striimautuu Range-pyynnöllä (206, `bytes 0-99/...`).
- Korjaukset browser-validoinnissa: fonttipolun trailing slash,
  `PlayerState`-enumin puuttuminen UMD-globalista, `useWorkers: false`.

## v1.11 – 18.10.2026

Tie-korjaus ja validointi.

- GP5- ja MusicXML-viennissä tie-tila on nyt nuottikohtainen. Aiemmin
  saman segmentin uudet ja edellisestä tahdista jatkuvat nuotit saivat
  saman tie-tilan (255 sekasegmenttiä KISS-testissä).
- Uusi testi `test_tie_state_is_per_note`.
- 30 pytest-testiä.
- Koko YouTube-testikohde (KISS – I’m A Legend Tonight, 4:00) ajettu
  läpi: 137 tahtia, 1410 tab-nuottia, GP5 validi, ei rikkinäisiä
  tahtikestoja eikä päällekkäisiä kieliä.

## v1.10 – 18.10.2026

Phase 1 – audio-to-tab -putki.

- Lisätty `app/pipeline/`: `audio_source`, `separate`, `transcribe`,
  `tempo`, `quantize`, `fretboard`, `segments`, `build`,
  `export_gp5`, `export_musicxml`, `export_midi`.
- `scripts/pipeline_smoke.py`: local/YouTube → ffmpeg → Demucs 6s →
  Basic Pitch → tempo → quantize → fretboard → GP5/MusicXML/MIDI +
  `meta.json`.
- Demucs `htdemucs_6s`, 4-stem fallback ja `--no-separation`-pikatila.
- Tempo normalisoidaan 70–180 BPM -alueelle (esim. 68 → 136).
- Kielikohtainen monofonia: päällekkäinen nuotti siirretään vapaalle
  kielelle tai edellistä nuottia lyhennetään.
- Fretboard-Viterbi ja virityspresetit: standard, drop D, Eb, D, open G,
  bass 4-string.
- GP5/MusicXML/MIDI-export. GP5 validointi: 108 tahtia, 884 tab-nuottia,
  ei rikkinäisiä tahtikestoja eikä päällekkäisiä kieliä.
- 29 pytest-testiä.
- ML-riippuvuudet: Demucs 4.1.0, Basic Pitch 0.4.0, TensorFlow 2.15,
  Torch 2.14 CPU. `setuptools<81`, koska Basic Pitchin resampy käyttää
  `pkg_resources`-APIa.
- Validointi: 3:10 MP3 ~67 s CPU:lla; YouTube 20 s klipit toimivat.

## v1.00 – 18.10.2026

Projektin runko ja säännöt.

- `git init`, `origin` = `teppoaland/tabtool`.
- `.gitignore`: `docs/`, `data/`, `.venv`, audio/tab-tiedostot, tokenit,
  mallit ja välimuistit pois julkisesta gitistä.
- `.clinerules/`: arkkitehtuuri, putken ydinsäännöt, versionhallinta,
  data/yksityisyys/lisenssit, kevyt polku ja ei ylimääräisiä dialogeja.
- FastAPI-runko: `/api/health`, `/api/version`, `/`, `/remote`, `/display`.
- Tyhjä tumma TV- ja remote-näkymä.
- `requirements.txt`, `requirements-ml.txt`, `requirements-dev.txt`.
- `setup.bat`, `install-ml.bat`, `start.bat`, `test.bat`.
- Ensimmäinen pytest-testi ja versiotarkistus.
- Lisenssi: All rights reserved. Kolmannen osapuolen lisenssit erillisessä
  `THIRD_PARTY_NOTICES.md`-tiedostossa.
