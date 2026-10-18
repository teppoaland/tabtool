# 📊 Projektin edistyminen – AI TABTOOL

## v1.37 – Playback range -korjaus (18.10.2026)

- Hiirellä raahaus loi alphaTabin `playbackRange`-loopin (vihreä
  kehys), joka rajaa `mainSeek`in → tab clampautuu väärään kohtaan ja
  Pause hyppää beat-alun mukaan. Range nollataan nyt
  `playbackRangeChanged`-, `scoreLoaded`- ja seek-yhteyksissä.
- Pause-palautus: `playerStateChanged` (60 ms) ja audion `pause`
  (150 ms) pakottavat synkan audion aikaan.
- Headless: raahaus → `.at-selection` 0×0; seek 10 s → tahti 6;
  pause säilytti tahtilukeman. 75 testiä.

## v1.35–v1.36 – SIIRTO (tahtia) (18.10.2026)

- SIIRTO siirtää tabia tahdeilla (−64…+64) ja tallentuu
  `meta.sync_offset_bars`iin; 0,25 tahdin askel = 1 isku (v1.36).
  Tahtipituus lasketaan `masterBars`-tickeistä.
- Syy: 258 tahtia vs. levytys ~249; vakiosiirto (esim. 6 iskua = 1,5
  tahtia) ei korjaannu prosentilla. Tallennettu tila: bpm 143,5,
  GP5 144, drift −0,35 %.
- Headless: −8 → tahti 13 @ 40 s; −1,5 → tahti 19; 75 testiä.

## v1.34 – Desimaali-TAB BPM (18.10.2026)

- TAB BPM 0,1 askeleen (143,55); GP5 kokonaisluku (`int(bpm+0,5)`),
  `meta.gp5_tempo`. `bpmDrift = bpm / score.tempo - 1` summataan
  SYNCiin. Seek & Destroy -audion tempo **143,555 BPM** (librosa).
- 73 testiä; headless 119,5 → GP5 120, tahti 29 @ 58 s.

## v1.33 – MP3-kuunteluversiot ja seek-synkki (18.10.2026)

- YouTube-latauksista tehdään MP3 `audio/mp3/<Artisti>/`-kansioon
  (ffmpeg libmp3lame VBR ~190 kbps); uudelleenkoodaus vain jos WAV on
  uudempi. Pätkäklipit ja omat uploadit ohitetaan.
- Backfill tekee MP3:t myös vanhoille YouTube-audioille.
- Seek-synkki tutkittu headless-selaimessa (30 tahtia / 120 BPM,
  siirrot 30→10→50→20→55→5 s): tahtilukema osui aina odotettuun,
  joten siirto ei riko aikasynkkiä. Vakaunnus: `audio.seeking`
  estää välipositiot, `seekTo`/`seeked` pakottavat synkan, slider
  vapautuu myös `pointerup`/`blur`illa.
- 72 pytest-testiä.

## v1.32 – Ulkoinen arkisto D:\tabtool_files (18.10.2026)

- `app/external_store.py`: `archive_external()` mirroroi tiedoston
  luettavalla nimellä `Artist - Title.ext`; hard link samalla levyllä,
  muuten kopio; virhe ei kaada jobia.
- Kytkennät: YouTube-audio `jobs.run_pipeline`:ssa (ei pätkäklipille) ja
  tuodut GP5/MusicXML `tab_import.import_tab_bytes`:ssa.
- `TABTOOL_EXTERNAL_DIR` (oletus `D:\tabtool_files`), `.env.example`.
- `scripts/backfill_external.py` arkistoi olemassa olevan kirjaston.
- 69 pytest-testiä (`tests/test_external_store.py` + tuontitesti).
- Kirjasto näytti tyhjältä, koska palvelin peri testin
  `TABTOOL_DATA_DIR`in; data oli ehjä (8 tabia). Palvelin käynnistettiin
  uudelleen oikealla juurella; live v1.32.

## v1.30–v1.31 – SYNC, TALLENNA ja Nopeus (18.10.2026)

- v1.30: SYNC ±10 % (`sync_drift`, `POST /api/tabs/{id}/sync`),
  Nopeus 50–150 %; arvot palautuvat `loadTab`issa, GP5/audio ennallaan.
- v1.31: `ASETA` → **TALLENNA**; tallentamaton BPM punaisena
  (`.bpm-field.is-dirty`), virheet `.is-error`. "Not found" johtui
  v1.22-palvelinprosessista; uudelleenkäynnistys ohjeistettu.
- Headless: SYNC +3.50 % → 0.035; TALLENNA 146 → GP5 146; 64 testiä.

## Session päätökset (18.10.2026)

- HEAD-viittaukset korjattu pysyviin ankkureihin; **ei pushia
  julkiseen GitHubiin** – vain lokaalit commitit (sääntö 03:ssa).

## Memory bank -protokolla (18.10.2026)

- `.clinerules/00-memory-bank.md` lisätty.
- Trigger: **`lue membank`** / `lue memory bank` / `alusta sessio` /
  `aloita uusi sessio`.
- Lukee 5 memory-bank-tiedostoa + `.clinerules/*`, ajaa git-tilan ja
  `pytest -q`, raportoi 3–6 riviä ja jatkaa `activeContext.md`:n
  seuraavasta vaiheesta.
- Memory bank -muutokset `docs:`-commitilla, ei versiobumppia.

## v1.26–v1.29 – Tuonti, pätkä, audio, BPM (18.10.2026)

- v1.26: GP5/MusicXML-tuonti (`app/tab_import.py`, PyGuitarPro/music21).
- v1.27: pätkägenerointi (`TEE TAB TÄSTÄ`, 30/60/120 s).
- v1.28: `LIITÄ AUDIO` ja Nopeus-säädin; `meta.json` päivittyy.
- v1.29: TAB BPM kirjoittaa GP5:n `song.tempo`n; 60 testiä.

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

## Varhaiset versiot (v1.00–v1.11, 18.10.2026)

- v1.00: repo, `.clinerules`, FastAPI-runko, `start.bat`/`test.bat`.
- v1.10: audio-to-tab-putki (Demucs `htdemucs_6s`, Basic Pitch,
  fretboard-Viterbi, GP5/MusicXML/MIDI); KISS 4 min → 137 tahtia.
- v1.11: tie-tila nuottikohtainen; GP5 validointi (ei duplicate
  string -beateja); 30 testiä.

## Testitilanne

- `pytest -q` → **75 passed**
- `compileall` → OK
- `node --check app.js` / `remote.js` → OK
- Headless-Chrome: alphaTab-render, cursor, fullscreen, GP5/MusicXML-
  tuonti, audio attach, BPM/desimaalitempo, SIIRTO, SYNC-tallennus,
  playback range -nollaus

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
- Koodi v1.23–v1.37 on committoitu (`b438e7b`); tagi `v1.29` =
  `bb704e8`. Repoa ei pushatta julkiseen GitHubiin:
  lokaalit commitit toimivat palautuspisteinä.
  `data/` ja `docs/` eivät ole gitissä, joten ne tarvitsevat erillisen
  varmuuskopion.

## Seuraavaksi

1. Päättää soittotapa/refinger: asemaprofiilit, playability-score,
   turhien nuottien karsinta, per-tahti/fraasiasema.
2. Vasta sitten Phase 3 / Spotify: PKCE, haku/metadata, SDK/Connect,
   tokenit `oauth_tokens`-tauluun ja mockatut API-testit.
3. Phase 4: remote-kaukosäädin.
