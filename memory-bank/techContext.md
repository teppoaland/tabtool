# 🛠️ Tekninen ympäristö – AI TABTOOL

## Kone

- Windows 10/11, `D:\AI\tabtool`
- Python 3.11.9, `.venv` projektissa
- ffmpeg 7.1 (PATH)
- Node.js 22.22.2 (vain `node --check`)
- **Ei GPU:ta** (`nvidia-smi` tyhjä) → CPU-only
- D: levytilaa ~147 GB vapaana

## Python-paketit (v1.48)

Core:

- fastapi 0.143.3
- uvicorn 0.54.0
- httpx 0.28.1
- python-multipart 0.0.32
- python-dotenv 1.2.4
- pytest 9.1.1
- httpx2 2.13.1 (Starlette 1.8+ TestClient)

ML / audio:

- demucs 4.1.0
- basic-pitch 0.4.0
- tensorflow 2.15.0 (CPU)
- torch 2.14.1+cpu
- librosa 0.11.0
- soundfile 0.14.0
- music21 10.5.0
- PyGuitarPro 0.11
- yt-dlp 2026.8.19
- numpy 1.26.4
- **setuptools<81** (Basic Pitchin resampy käyttää `pkg_resources`)

## Asennus

```bat
setup.bat          :: core + dev
install-ml.bat     :: Demucs + Basic Pitch + export/audio
start.bat          :: uvicorn 127.0.0.1:8000
test.bat           :: pytest + compileall + node --check
```

Manuaalinen:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-dev.txt
.venv\Scripts\python.exe -m pip install -r requirements-ml.txt
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## Testit

```powershell
.venv\Scripts\python.exe -m pytest -q          # 93 passed
.venv\Scripts\python.exe -m compileall -q app scripts tests
node --check app\static\app.js
node --check app\static\remote.js
```

Konsoli voi olla hyvin kapea (agentin kuori ~12 merkkiä, CP437) ja
VS Code shell integration voi pudottaa raa'an tulosteen. Putkita
tuloste `Out-String -Width 200`:lla tai ohjaa se tiedostoon.
`pytest.ini`:ssä ei ole `addopts = -q`, joten yksi `-q` riittää ja
yhteenvetorivi näkyy (v1.42).

## Pipeline CLI

```powershell
.venv\Scripts\python.exe scripts\pipeline_smoke.py "C:\Music\song.mp3" --title "Song" --artist "Artist"
.venv\Scripts\python.exe scripts\pipeline_smoke.py "https://youtu.be/..." --clip-seconds 30
.venv\Scripts\python.exe scripts\pipeline_smoke.py song.mp3 --no-separation --clip-seconds 20
```

Hyödylliset valinnat: `--model htdemucs_6s`, `--stem guitar`, `--tuning`,
`--bpm`, `--start-seconds`, `--clip-seconds`, `--no-separation`,
`--max-fret`, `--max-span`, `--grid`, `--debug`.

## Git

- `origin` = `https://github.com/teppoaland/tabtool.git`
- **Vain lokaalit commitit.** Projektia ei julkaista eikä pushatta
  julkiseen GitHubiin toistaiseksi. Commitit ovat palautuspisteitä
  (revert), jos koodi hajoaa. Push vaatii aina erillisen pyynnön.
- Ankkurit: v1.38 `c74ccdd`, v1.39 `8237876`, v1.40 `30e2c0e`,
  v1.41 = GP3/GP4-tuonti; tagi `v1.29` = `bb704e8`,
  `origin/main` = `69c2e39`.
- Paikallinen `main` on `origin/main`:ia edellä (v1.23–v1.40 koodi +
  memory bank -docs); **ei pushattu**. `git status -sb` näyttää määrän.
- Älä kirjaa tähän HEAD-hashia: docs-commit siirtää HEADin joka kerta.
- Työpuu clean committien jälkeen.
- Git ei versioi `data/`- eikä `docs/`-hakemistoa; tag/commit palauttaa
  vain koodin, ei audioita/tabeja/tokeneita.
- Commit author: `Azure Notepad Pipeline <azure-pipeline@notepad-automation.com>`
- `.gitattributes`: `*.bat eol=crlf`, `app/static/vendor/** -text`
- `.gitignore`: `docs/`, `data/`, `.venv`, audio/tabit, tokenit, mallit

## Data

- `data/tabtool.sqlite3` (WAL) – tracks/jobs/tabs/oauth_tokens/settings
- `data/audio/` – uploadit, YouTube-normalisoinnit ja pätkäklipit
- `data/stems/` – Demucs-stemmat
- `data/tabs/<id>/` – `tab.gp5`, `tab.musicxml`, `tab.mid`, `meta.json`
  (mm. `files`, `audio_path`, `bpm`, `gp5_tempo`, `sync_drift`,
  `sync_offset_bars`)
- `D:\tabtool_files\` (gitin ulkopuolella) – ulkoisen sisällön arkisto:
  `audio/Artist - Title.wav`, `audio/mp3/<Artisti>/Artist - Title.mp3`,
  `tabs/Artist - Title.gp5|.musicxml`.
  Polku `TABTOOL_EXTERNAL_DIR`; WAV hard link samalla levyllä.
  MP3 syntyy vain kun `archive_mp3` on päällä (oletus); tabin poisto
  jättää MP3:n ja jakamaansa audiota ei poisteta.
- Tuodut tabit: GP5/MusicXML + `meta.json`; `source_type=import`
- Audio attach: tuotu tabi voi osoittaa samannimisen AI-tabin audioon;
  audioita ei kopioida. Pätkäjobi käyttää tabin audiota ja optionsia.
- `notes.json` / refinger **ei vielä** ole käytössä.

Sisäiset nimet säilyttävät `tabtool`-etuliitteen (repo, `TABTOOL_*`,
DB-tiedosto); vain tuotenimi on `AI TabTool`.

## Frontend

- alphaTab 1.8.4 vendoroituna `app/static/vendor/alphaTab/`
  (`alphaTab.min.js`, `font/Bravura.woff2`, `LICENSE`).
- Ei npm-riippuvuuksia eikä buildia; `core.useWorkers = false` pitää
  renderöinnin deterministisenä.
- Oletus tab-only; Näkymä, raitavalinnat, FULLSCREEN, cursor/scroll,
  aikajana/tahtilukema, **SEARCH-modaali** (YouTube + GP5-linkki/-tiedosto,
  MP3-valinta, kirjasto ja poisto), LIITÄ AUDIO, TAB BPM ja Nopeus.
- Score-format valitaan `meta.files`:stä (gp5 ensin, muuten musicxml);
  tuotu tabi ilman audiota piilottaa PLAYn ja transportin.
- `mediaHandler.playbackRate` seuraa `audio.playbackRate`-arvoa
  (`Nopeus` 50–150 %); `preservesPitch = true`. BPM-korjaus kirjoittaa
  GP5:n ja lataa tabin.
- `mediaHandler.backingTrackDuration` palauttaa **partituurin keston**
  (laskettu master bar -tikeistä, v1.45), ei ääniraidan kestoa. alphaTabin
  ulkoisen median kello skaalaa backing trackin ajan suhteella
  `scoreEnd / backingTrackDuration`; ääniraidan kestolla pidempi tabi
  venytti kursorin ääntä edelle. Nyt kellotus on 1:1 ja vain BPM/SYNC/
  SIIRTO vaikuttavat.
- `SYNC` (±10 %, 0,05 %) kertoo tabin aikajanan siirrosta:
  `syncPosition()` antaa alphaTabille `audio.currentTime * (1 + drift)`
  (clamped audion kestoon). Arvo tallentuu `meta.sync_drift`iin ja
  palautuu `loadTab`issa; GP5/audio eivät muutu.
- Seek: `audio.seeking` estää välipositiot; `seekTo()`/`seeked`
  pakottavat synkan (`force`). Seek-slider vapautetaan `change`-,
  `pointerup`-, dokumentin `pointerup`- ja `blur`-tapahtumissa.
- Desimaali-TAB BPM: `bpmDrift = bpm / score.tempo - 1` summataan
  `syncDrift`iin; GP5 säilyttää kokonaislukutempon.
- SIIRTO: `sync_offset_bars` lisätään positioon
  `bars × tahtipituus_ms`; tahtipituus lasketaan `masterBars`-tickeistä
  ja nuottitemposta. Tallentuu `meta.sync_offset_bars`iin.
  UI pyöristää 0,25 tahdin askeleeseen (1 isku 4/4:ssä).
- Playback range: alphaTab luo raahauksella `playbackRange`in; se
  nollataan (`clearPlaybackRange`) ennen seekiä, latauksessa ja
  `playbackRangeChanged`issa. Pause → `syncPosition(true)`.
- `TALLENNA` (v1.31): BPM tallentuu vain napista; tallentamaton arvo
  värjää `.bpm-field`-kentän punaiseksi. Status-tekstit
  (`bpm-status`, `sync-status`) saavat `.is-error`-luokan virheestä.
- Uvicorn ajetaan ilman `--reload`ia: koodimuutoksen jälkeen palvelin
  on käynnistettävä uudelleen, muuten uudet reitit palauttavat 404.
  Staattisten tiedostojen `?v=1.48`-leimat pakottavat tuoreen CSS/JS:n;
  selaimessa voi silti tarvita Ctrl+F5:n.
- Modaalin pino: alphaTabin `.at-cursors` on `z-index: 1000`; modaali
  `2000`, dialogi `2100`, viewer `isolation: isolate`, cursor piiloon
  `body.modal-open`-tilassa. Modaalin tausta on peittävä.
- Headless-Edge/Chrome-validoinnit: alphaTab-render, cursor, fullscreen,
  GP5/MusicXML-tuonti (linkki + tiedosto), audio attach, BPM 140/144,
  aikajana, SEARCH-modaali, poisto, playback range -nollaus.
