# 📍 Aktiivinen konteksti – TABTOOL

> **Versio:** `v1.11` (18.10.2026)
> **Git:** `main` = `origin/main` = `6bd647c`
> **Repo:** https://github.com/teppoaland/tabtool

## Nyt

- **Phase 0 valmis:** repo, säännöt, `.gitignore`, FastAPI-runko,
  TV/remote-shell, testit, CI-tyyppiset tarkistukset.
- **Phase 1 valmis:** koko audio-to-tab-putki toimii CLI:stä:
  oma MP3 / YouTube → ffmpeg → Demucs `htdemucs_6s` → Basic Pitch →
  tempo → kvantisointi → fretboard → GP5/MusicXML/MIDI + `meta.json`.
- **v1.11:** tie-tila nuottikohtainen GP5/MusicXML-viennissä.
- **Web-UI on yhä Phase 0 -shell.** alphaTab-katselin, job-jono, cache,
  upload-API ja remote-toiminnot tulevat Phase 2:ssa.
- **Spotify ei ole vielä mukana.** Haku/OAuth/SDK/Connect tulevat
  Phase 3:ssa. Client ID ja Premium eivät ole vielä tarpeen.

## Seuraava vaihe: Phase 2 / v1.20

1. SQLite: `tracks`, `jobs`, `tabs`, `oauth_tokens`, `settings`.
2. Job-jono + worker + WebSocket/SSE-progress.
3. Upload / local path / YouTube source + cache.
4. alphaTab 1.8.4 vendoroituna; GP5-viewer.
5. Paikallinen audiotoisto (`<audio>` + Range) ja
   `IExternalMediaHandler`-synkka 50 ms välein.
6. API-testit mockatulla putkella.
7. Tarvittaessa `data/tabs`-kirjasto/import.

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

- **Diablo – Mimic 47** (3:10 MP3): 108 tahtia, 884 tab-nuottia,
  GP5 validi, ~67 s CPU:lla.
- **KISS – I’m A Legend Tonight** (4:00 YouTube): 137 tahtia,
  1413 tab-nuottia, GP5 validi (3050 GP5-nuottimerkintää mm. tie- ja
  sointunuoteista), ei rikkinäisiä tahtikestoja eikä duplicate string
  -nuotteja.
- YouTube-lataus toimii ilman mainoksia (yt-dlp audiostream).

## Avoimet / myöhemmin

- Spotify Client ID + Premium (Phase 3).
- Playback: Web Playback SDK vs. Spotify Connect -laite.
- LAN-PIN ja `--lan`-tila.
- Audion/stemmojen säilytysaika (`TABTOOL_AUDIO_RETENTION_DAYS`).
- Basso/laulu; rummut vaativat ADTOF/Omnizart-tyyppisen mallin.
- Manuaalinen tab-editori vai pelkkä import/export + Guitar Pro?
- alphaTab + MusicXML -tab-staffin validointi Phase 2:ssa.

## Uuden session aloitus

**Sano Cline:lle: `lue membank`.**

Se tekee automaattisesti:

1. Lukee `memory-bank/projectBrief.md`, `systemPatterns.md`,
   `techContext.md`, `activeContext.md` ja `progress.md`.
2. Lukee `.clinerules/*.md`.
3. Ajaa `git --no-pager status -sb`, `git --no-pager log -1 --oneline`
   ja `pytest -q`.
4. Jatkaa `Phase 2` -listasta; ei riko `.clinerules/`-sääntöjä.
5. `docs/` ja `data/` ovat yksityisiä eivätkä kuulu gitiin.
