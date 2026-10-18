# 📊 Projektin edistyminen – AI TABTOOL

## Memory bank -protokolla (18.10.2026)

- `.clinerules/00-memory-bank.md` lisätty.
- Trigger: **`lue membank`** / `lue memory bank` / `alusta sessio` /
  `aloita uusi sessio`.
- Lukee 5 memory-bank-tiedostoa + `.clinerules/*`, ajaa git-tilan ja
  `pytest -q`, raportoi 3–6 riviä ja jatkaa `activeContext.md`:n
  seuraavasta vaiheesta.
- Memory bank -muutokset `docs:`-commitilla, ei versiobumppia.

## v1.29 – TAB BPM ja Nopeus (18.10.2026)

- `TAB BPM` -kontrolli ja `POST /api/tabs/{id}/tempo`: GP5:n
  `song.tempo`, `tabs.bpm` ja `meta.json` päivittyvät; audio 100 %.
- `Nopeus` 95–105 %, askel 0,1 %, yhden desimaalin näyttö;
  `mediaHandler.playbackRate` seuraa audio-ratea.
- Referenssitabi 140 → 144 → **takaisin 140** käyttäjän toiveesta;
  audio pysyi liitettynä, AI-tabi 144. BPM/Nopeus-kontrollit jäivät.
- Soittotapa/refinger (asemaprofiilit, helpoin-arvio, turhien nuottien
  karsinta) suunniteltu, **ei toteutettu**; jäissä.
- 60 pytest-testiä.

## v1.28 – Referenssitabin audio (18.10.2026)

- `LIITÄ AUDIO` + `POST /api/tabs/{id}/attach-audio`: samannimisen
  AI-tabin audio liitetään tuotuun tabiin; PLAY/aikajana/cursor.
- Moniraitaisen tuonnin oletus Guitar 1 + Guitar 2.
- `Nopeus`-säädin; `meta.json` päivittyy audiolinkityksellä.
- 58 pytest-testiä.

## v1.27 – Pätkägenerointi (18.10.2026)

- `TEE TAB TÄSTÄ`, 30/60/120 s, `POST /api/tabs/{id}/section`.
- Uusi tabi nimellä `[start +kesto]`; audio/options lähtötabista.
- Tuodut tabit merkitään `Lähde: tuotu tabi`; oletus Guitar 1/2.
- 56 pytest-testiä.

## v1.26 – GP5/MusicXML-tuonti (18.10.2026)

- `app/tab_import.py`, `POST /api/tabs/import`; PyGuitarPro/music21
  metat, GP5/MusicXML-tiedostot, kirjastoon.
- Tuotu tabi ilman audiota: PLAY/transport piilotettu; export-linkit
  vain olemassa oleville formaateille.
- 53 pytest-testiä.

## v1.25 – Metatiedot ja aikajana (18.10.2026)

- YouTube title/artist yt-dlp:stä, suffix-siivous, `audio_path` metaan.
- Aikajana: aika/kesto, tahtilukema, ±5 s, Space/nuolet,
  scroll-to-cursor.
- Vanha referenssitabi nimettiin oikein (DB/meta/GP5/MusicXML).
- 49 pytest-testiä.

## v1.24 – Scroll ja dynamiikat (18.10.2026)

- Smooth + negatiivinen `scrollOffsetY`: edellinen rivi näkyviin,
  cursor ei karkaa yläreunaan.
- Dynamiikkamerkinnät piilotettu (`EffectDynamics`); 45 testiä.

## v1.23 – Katselu (18.10.2026)

- Tab-only oletus, Näkymä-valinta, raitavalinnat, FULLSCREEN +
  autofullscreen, cursor/tahtikorostus, vaakascrollbar pois,
  kirjaston tooltipit.
- 45 pytest-testiä.

## v1.22 – Tuotenimi AI TabTool (18.10.2026)

- `APP_NAME` = "AI TabTool"; wordmark `AI TABTOOL`, brand-mark `AT`.
- HTML-otsikot, footer, `start.bat` ja `open_browser.ps1` päivitetty.
- Sisäiset tunnisteet ennallaan: repo `tabtool`, `TABTOOL_*`,
  `data/tabtool.sqlite3`.
- Testit päivitetty uuteen nimeen; 45 passed.

## v1.21 – Käynnistyksen automaatio (18.10.2026)

- `start.bat` avaa oletusselaimen, kun `/api/health` vastaa.
- `scripts/open_browser.ps1`: 30 s timeout, 500 ms pollaus,
  `TABTOOL_NO_BROWSER=1` ohittaa avauksen.
- Validoitu: timeout-tapaus 2,8 s, valmis palvelin 0,2 s,
  `start.bat` → health 200 (v1.21) ja siisti sammutus.

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

- `pytest -q` → **60 passed**
- `compileall` → OK
- `node --check app.js` / `remote.js` → OK
- Headless-Chrome: alphaTab-render, cursor, fullscreen, GP5/MusicXML-
  tuonti, audio attach, BPM 140/144, aikajana

## Tunnetut rajoitukset

- AI-transkriptio on luonnos; särö/akordit/nopeat soolot virheellisiä.
- Basic Pitch ei ole kitarakohtainen; otteet/asemat voivat poiketa
  opitusta tabista. Referenssitabi + TuxGuitar auttavat.
- Standard E -alueen ulkopuoliset nuotit pudotetaan varoituksella.
- Tempo voi olla half/double-time; AI-BPM on arvio; TAB BPM/Nopeus
  korjaa.
- Soittotapa/refinger (asemaprofiilit, nuottien karsinta) puuttuu.
- Referenssitabilla on 258 tahtia vs. AI 249; rakenne voi poiketa.
- Rummut vaativat oman mallin; Spotify Phase 3; remote Phase 4.
- Koodi v1.23–v1.29 on työpuussa, ei committoitu.

## Seuraavaksi

1. Committaa v1.23–v1.29 koodi + testit (työpuu) ja varmistaa 60 testiä.
2. Päättää soittotapa/refinger: asemaprofiilit, playability-score,
   turhien nuottien karsinta, per-tahti/fraasiasema.
3. Vasta sitten Phase 3 / Spotify: PKCE, haku/metadata, SDK/Connect,
   tokenit `oauth_tokens`-tauluun ja mockatut API-testit.
4. Phase 4: remote-kaukosäädin.
