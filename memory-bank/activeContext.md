# 📍 Aktiivinen konteksti – AI TABTOOL

> **Versio:** `v1.22` (18.10.2026)
> **Git:** viimeisin koodicommit `2d4fe02` (v1.22), ei pushattu
> **Repo:** https://github.com/teppoaland/tabtool

## Nyt

- **Phase 0 valmis:** repo, säännöt, `.gitignore`, FastAPI-runko,
  TV/remote-shell, testit, CI-tyyppiset tarkistukset.
- **Phase 1 valmis:** koko audio-to-tab-putki toimii CLI:stä:
  oma MP3 / YouTube → ffmpeg → Demucs `htdemucs_6s` → Basic Pitch →
  tempo → kvantisointi → fretboard → GP5/MusicXML/MIDI + `meta.json`.
- **Phase 2 valmis (v1.20):** SQLite (`tracks`, `jobs`, `tabs`,
  `oauth_tokens`, `settings`), job-jono + yksi worker + SSE-progress,
  upload / YouTube / local-path, cache + `regenerate`, alphaTab 1.8.4
  vendoroituna, paikallinen WAV-toisto Range-tuella ja 50 ms
  `IExternalMediaHandler`-synkka, kirjasto + CLI-tabien import ja
  `?tab=<id>`-syvälinkki.
- **v1.21:** `start.bat` avaa oletusselaimen automaattisesti, kun
  `/api/health` vastaa (`scripts/open_browser.ps1`); `TABTOOL_NO_BROWSER=1`
  ohittaa avauksen.
- **v1.22:** tuotenimi **AI TabTool** (wordmark `AI TABTOOL`, markki `AT`).
  Repo, `TABTOOL_*`-muuttujat ja `data/tabtool.sqlite3` säilyvät
  teknisinä niminä. Ei toiminnallisia muutoksia.
- **Spotify ei ole vielä mukana.** Haku/OAuth/SDK/Connect tulevat
  Phase 3:ssa. Client ID ja Premium eivät ole vielä tarpeen.

## Seuraava vaihe: Phase 3 / v1.30

1. `app/spotify.py`: Authorization Code + PKCE, token refresh ja
   `/api/spotify/*` (vain localhost, LAN-PIN huomioiden).
2. Haku + metadata `tracks`-tauluun ja tuloslista UI:hin.
3. Web Playback SDK tai Spotify Connect -laite; tabin audio pysyy
   paikallisena (local-first).
4. Tokenit `oauth_tokens`-tauluun `data/`-hakemistoon; ei gitiin.
5. API-testit mockatulla Spotifyllä.


## Tärkeät komennot

```powershell
cd D:\AI\tabtool
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m compileall -q app scripts tests
node --check app\static\app.js
node --check app\static\remote.js
start.bat
```

Putki:

```powershell
.venv\Scripts\python.exe scripts\pipeline_smoke.py "C:\Music\song.mp3" --title "Song" --artist "Artist"
```

## Tuoreimmat validointitulokset

- **v1.20 web-smoke** (20 s klippi, nopea tila): 12 tahtia, 58 nuottia;
  GP5 luettu takaisin (78 merkintää), MusicXML jäsentyy; audio 206
  Range-pyynnöllä (46 MB WAV).
- **alphaTab 1.8.4** renderöi 137 tahdin KISS-tabin headless-Chromessa
  (30 254 px korkea sivu, nuotti-ink havaittu screenshotista).
- **Kirjasto/import:** 6 CLI-tabia (`data/tabs/*/meta.json`)
  rekisteröityi automaattisesti; `?tab=<id>` avaa suoraan.
- **Diablo – Mimic 47** (3:10 MP3): 108 tahtia, 884 tab-nuottia,
  GP5 validi, ~67 s CPU:lla.
- **KISS – I’m A Legend Tonight** (4:00 YouTube): 137 tahtia,
  1413 tab-nuottia, GP5 validi (3050 GP5-nuottimerkintää mm. tie- ja
  sointunuoteista), ei rikkinäisiä tahtikestoja eikä duplicate string
  -nuotteja.

## Avoimet / myöhemmin

- Spotify Client ID + Premium sekä haku/OAuth (Phase 3).
- Playback: Web Playback SDK vs. Spotify Connect -laite.
- Remote-kaukosäädin (Phase 4).
- LAN-PIN ja `--lan`-tila.
- Audion/stemmojen säilytysaika (`TABTOOL_AUDIO_RETENTION_DAYS`).
- Basso/laulu; rummut vaativat ADTOF/Omnizart-tyyppisen mallin.
- Manuaalinen tab-editori vai pelkkä import/export + Guitar Pro?

## Uuden session aloitus

**Sano Cline:lle: `lue membank`.**

Se tekee automaattisesti:

1. Lukee `memory-bank/projectBrief.md`, `systemPatterns.md`,
   `techContext.md`, `activeContext.md` ja `progress.md`.
2. Lukee `.clinerules/*.md`.
3. Ajaa `git --no-pager status -sb`, `git --no-pager log -1 --oneline`
   ja `pytest -q`.
4. Jatkaa `Phase 3` -listasta; ei riko `.clinerules/`-sääntöjä.
5. `docs/` ja `data/` ovat yksityisiä eivätkä kuulu gitiin.
