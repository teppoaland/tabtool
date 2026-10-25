# 🛠️ Tekninen ympäristö – AI TABTOOL

## Kone

- Windows 10/11, `D:\AI\tabtool`
- Python 3.11.9, `.venv` projektissa
- ffmpeg 7.1 (PATH)
- Node.js 22.22.2 (vain `node --check`)
- **Ei GPU:ta** (`nvidia-smi` tyhjä) → CPU-only
- D: levytilaa ~147 GB vapaana

## Python-paketit (v2.04)

Core:

- fastapi 0.143.3
- uvicorn 0.54.0
- httpx 0.28.1
- python-multipart 0.0.32
- python-dotenv 1.2.4
- segno 1.6.6 (QR-pariutus, puhdas Python)
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
start.bat          :: stop+start: uvicorn 0.0.0.0:8000 (vanha Python-instanssi alas)
stop.bat           :: pysäyttää portin 8000 palvelimen
status.bat         :: portin tila + /api/version
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
.venv\Scripts\python.exe -m pytest -q          # 244 passed
.venv\Scripts\python.exe -m compileall -q app scripts tests
node --check app\static\app.js
node --check app\static\remote.js
node --check app\static\remote-bridge.js
node --check app\static\settings.js
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
- **Push vain erillisestä pyynnöstä.** Projektia ei julkaista; commitit
  ovat ensisijaisesti paikallisia palautuspisteitä (`git revert`).
- Ankkurit: v1.38 `c74ccdd`, v1.39 `8237876`, v1.40 `30e2c0e`,
  v1.41 = GP3/GP4-tuonti; tagi `v1.29` = `bb704e8`; tagi `v1.99` =
  toimiva palautuspiste (23.10.2026).
- Koodi v1.23–v1.99 on **pushattu** `origin/main`iin käyttäjän pyynnöstä
  23.10.2026 (aiempi push 20.10.2026). **Tagi `v1.99` = viimeisin
  pushattu palautuspiste** (`git reset --hard v1.99`); v2.00–v2.01 ovat
  paikallisia (ei pushattu). Push vain erillisestä pyynnöstä; `data/` ja
  `docs/` eivät ole gitissä.
- `scripts/build_kiss_legend.py` on `.gitignore`ssa: se sisältää koko
  kappaleen nuottidatan (tekijänoikeus), joten sitä ei viedä julkiseen
  gitiin.
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
  aikajana/tahtilukema, **LIBRARY-modaali** (YouTube + GP5-linkki/-tiedosto,
  MP3-valinta, kirjasto ja poisto), LIITÄ AUDIO, TAB BPM ja Nopeus.
- **Tumma tabi** (v1.49): `display.resources`-värit vaaleiksi ja
  `.alphatab`-tausta `#0d1117`. `mediaHandler.seekTo` kääntää
  SIIRTO/SYNC/BPM-korjauksen kaikille `time > 0` -seekeille (v1.52);
  rajaaminen klikkauksiin rikkoi synkan (aloitus siirtyi 1,268 s → 0).
  **Count-in (v1.56):** `handlePlayButton` on portinvartija, joka kutsuu
  muuttumatonta `togglePlayback`ia joko heti tai 5 → 0 -laskennan jälkeen
  (`#play-countdown`, fixed-lapsi viewerissä; ei `api.`/`audio`-kutsuja).
  Ohitus perustuu käyttäjän omaan seekiin (`countInSkipped`), ei
  `currentTime`iin: alphaTab siirtää audion ensimmäiselle iskulle jo
  latauksessa (0,8455 s SIIRTO −0,75:llä). **v1.81:** ON/OFF-kytkin
  (`#countin-toggle`, `#countin-state`, `.viewer-corner` FULLSCREEN-napin
  alla, localStorage `tabtool:countIn`, oletus ON) luetaan **vain**
  `shouldRunCountIn`issa. Vartio: `tests/test_playback_guard.py`.
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
  UI pyöristää 0,25 tahdin askeleeseen (1 isku 4/4:ssä). Rajana
  **±999 tahtia** (`app/main.py` `SYNC_OFFSET_LIMIT`, v1.75).
  **Tunnettu rajoite:** `barDurationMs()`/`ticksPerBar()` ottavat
  tahdin pituuden **kahdesta ensimmäisestä tahdista** – jos tabi alkaa
  anacrusiksella, SIIRTO on 8×/16× liian voimakas (Dr. Feelgood ennen
  v1.78:aa). Data korjataan `trim_bars.py --bars 1`llä;
  koodikorjaus on sääntö #1:n ydintä ja vaatii erillisen luvan.
- Playback range: alphaTab luo raahauksella `playbackRange`in; se
  nollataan (`clearPlaybackRange`) ennen seekiä, latauksessa ja
  `playbackRangeChanged`issa. Pause → `syncPosition(true)`.
- `TALLENNA` (v1.31): BPM tallentuu vain napista; tallentamaton arvo
  värjää `.bpm-field`-kentän punaiseksi. Status-tekstit
  (`bpm-status`, `sync-status`) saavat `.is-error`-luokan virheestä.
- Uvicorn ajetaan ilman `--reload`ia: koodimuutoksen jälkeen palvelin
  on käynnistettävä uudelleen. **Palvelin on käyttäjän hallinnassa:**
  `start.bat` pysäyttää vanhan Python/uvicorn-instanssin ja käynnistää
  uuden yhdellä ajolla; `stop.bat` pysäyttää ja `status.bat` näyttää
  tilan ja version. Vierasta prosessia portilla 8000 ei tapeta.
  Cline ei käynnistä palvelinta taustalle eikä pysäytä ilman pyyntöä.
  **Soiton/tabin synkka hyväksytään vain käyttäjän kuuntelutestillä**
  (`.clinerules/07-playback-frozen.md`): pytest, `node --check` ja
  headless eivät todista kohdistusta.
  Staattisten tiedostojen `?v=1.99`-leimat pakottavat tuoreen CSS/JS:n;
  selaimessa voi silti tarvita Ctrl+F5:n.
- **LAN ja puhelin (v1.82–v1.90):** `start.bat` sitoo aina `0.0.0.0`:aan
  (yksi käynnistin, ei `start-lan.batia`); `TABTOOL_LAN_PIN` aktivoi
  portinvartijan (HttpOnly eväste, SHA-256-tiiviste, 10 yritystä/60 s),
  `TABTOOL_LAN_IP` kiinnittää QR-koodin osoitteen. **150 px QR on
  `/remote`-sivulla** (`/api/lan/qr.svg`, `segno`, aina sen hetkinen
  LAN-IP); DHCP-osoitteen vaihtuminen ei riko pariutusta. TV:n
  `remote-bridge.js` pollaa `/api/remote/commands` 0,5 s välein ja
  klikkaa olemassa olevia nappeja; `app.js` pysyy koskemattomana
  (sääntö #1). Sivun auetessa silta lukitsee nykyisen sekvenssin
  (`primeSequence`), joten ennen sitä jonoon jääneet komennot eivät
  laukea (v1.90).
- Modaalin pino: alphaTabin `.at-cursors` on `z-index: 1000`; modaali
  `2000`, dialogi `2100`, viewer `isolation: isolate`, cursor piiloon
  `body.modal-open`-tilassa. Modaalin tausta on peittävä.
- **Kirjasto ja työkalut (v1.63–v2.03):** `POST /api/tabs/{id}/library`
  (`artist`/`title`/`locked`/`archived`/`tuning`, tyhjä viritys
  `tuning_clear`), `title_override`/`artist_override` +
  `original_title`/`original_artist`, `locked` estää poiston (409) ja
  muutokset, `archived` piilottaa päälistalta (`ARKISTO (n)`),
  aakkosjärjestys `localeCompare("fi")`, **Tiedot**-modaali (esittäjä,
  nimi, viritys, Lukitse, Arkistoi + vain luku -metadata ja lähdelinkit)
  ja punainen `×`-poisto. Modaalissa KIRJASTO vasemmalla.
  Kanava `meta.youtube_channel`, viritys `meta.tuning_label` +
  `tuning_notes` (GP5:n kielet, `app/tuning.py`).
- **Skriptit:** `import_folder.py`, `export_tabs.py`,
  `adb_pull_gp.ps1` (puhelimen Download), `backfill_youtube_channel.py`,
  `backfill_source_url.py` (v2.03: audiolinkki job-riveistä),
  `backfill_tuning.py` (`--force`), `backfill_external.py`,
  `backfill_gp5_utf8.py`, `pipeline_smoke.py` ja tab-datan työkalut
  `expand_repeat.py` (toisto tahdeiksi), `trim_bars.py` (tahdin poisto),
  `retune_tab.py` (virityksen vaihto sävelet säilyttäen). Kaikki
  varmuuskopioivat `data/backups/`iin.
- Headless-Edge/Chrome-validoinnit: alphaTab-render, cursor, fullscreen,
  GP5/MusicXML-tuonti (linkki + tiedosto), audio attach, BPM 140/144,
  aikajana, SEARCH-modaali, poisto, playback range -nollaus.
  v1.57–v1.62: tabin marginaali 30/30 px + 15 px scrollbar-kaista
  (mitattu 1600/1366/1200/1024/800 px), korttien asettelu, modaalin
  avautuminen LIBRARY-napin korkeudelle, LIBRARY piiloon fullscreenissä.
  v1.63–v1.68: kirjaston nimeäminen/lukitus/arkisto, kanava ja viritys
  renderöityivät oikein; tallennuspolut testattu pytestillä
  (TestClient), ei selaimessa.

## v1.93–v2.01 (23.10.2026)

- **Remote:** otsikko yhdellä rivillä (AT-merkki, DISPLAY/API-nav ja
  REMOTE-kicker pois); yksi tila-indikaattori `Online` / `Offline` /
  `Offline-TV`; `«` = `seek 0` ja `+5 s` pois; QR sivun alaosaan;
  nopeus 1 % askelet + 95–105 % → 100 %; seek-sliderin strict-mode
  `ReferenceError` korjattu (v1.98, `forwardButton`-jäänne).
- **Päänäkymä:** `#rate-slider` step 0,01 + 10 %:n snap (v1.96).
  `playbackRate` on harjoittelunopeus, ei kohdistus; vartiotesti
  `test_playback_rate_never_enters_the_alignment_math` (v1.97).
- **`start.bat`:** stop+start yhdellä ajolla (v1.94); vierasta prosessia
  portilla 8000 ei tapeta.
- **GP3-tuonti:** `_sanitize_for_gp5` (grace fret −1 → `isDead`, fret 0)
  ennen GP5-kirjoitusta (v1.99); White Wedding (gprotab) toimii.
- **Kirjastot (v2.00–v2.01):** TV:n LIBRARY ja puhelimen SOITA/SÄÄDÄ
  järjestetään `artist` → `title` (`localeCompare("fi")`); remote-kirjaston
  sisäinen `max-height`/`overflow` poistettu → yksi sivun scrollbar.
- Testit **195**; tagi `v1.99` = viimeisin pushattu palautuspiste.

## v2.02 (24.10.2026)

- **Settings-näkymä:** `/settings` + `GET/POST /api/settings`
  (`app/settings.py`, 25 kenttää: count-in, Näkymän oletus, 16 päänäkymän
  toimintoa, 4 puhelimen toimintoa). Arvot `settings`-taulussa JSONina;
  lukukelvoton tai rajan ulkopuolinen arvo palautuu oletukseen.
- **`app.js`:** `SETTINGS_URL`, `UI_FEATURES`, `applyRuntimeSettings`,
  `applyUiVisibility` (body-luokat `hide-ui-*`), `loadRuntimeSettings`
  käynnistyksen alussa. Count-in lukee `countInSteps` / `countInStepMs` /
  `countInZeroMs`; oletukset ennallaan (5 / 1000 / 250). Sanoitusrivin koko
  luetaan kentästä `lyrics.scale` → `applyLyricsScale()` →
  `--lyrics-scale` (v2.08).
- **Puhelin:** `remote.html` (soittimet ylhäällä, mode-napit alhaalla),
  `remote.js` (`renderTracks`, `send("track")`, `features`),
  `remote-bridge.js` (`readTracks`, `tracks`-kenttä, `action === "track"`),
  `remote.py` (`track`-komento 0–31, `clean_state` → `tracks`).
- Testit **229**; `tests/test_settings.py` + raidat `tests/test_remote.py`.

## v2.03 (24.10.2026)

- **Kirjaston Tiedot:** `NIMEÄ` → `Tiedot` (`#detail-dialog`,
  `app.js`: `openDetailDialog`/`saveDetail`/`renderDetailMeta`). Muokattavat:
  esittäjä, nimi, viritys, lukitus, arkistointi; vain luku: BPM, tahtia,
  nuotteja, kanava, lisäysaika, `Audiolähde`, `Tablähde`, ID. Lukittu tabi
  aukeaa vain luku -tilaan (Lukitse-rasti avaa lukituksen).
- **Skeema:** `tabs.artist_override` (+ migraatio), `_tab_row` vaihtaa
  `artist`in ja palauttaa `original_artist`in; `list_tabs` järjestää
  ylikirjoitetun artistin mukaan. `POST /api/tabs/{id}/library` hyväksyy
  `artist`-kentän (tyhjä = palauta).
- **Lähdemeta:** `meta.audio_source_url` / `audio_source_type`
  (`jobs._process_audio_job`, AI-putki), `meta.tab_source_url` /
  `tab_source_file` (`tab_import.import_tab_bytes(source_url, source_file)`,
  `_download_tab`). `_tab_summary` → `source_url`, `tab_source_url`,
  `tab_source_file` (vain http(s)); `scripts/backfill_source_url.py`
  täydentää vanhat audiolinkit job-riveistä.
- **Puhelin:** SÄÄDÄ-lomakkeessa `#adjust-artist`; `remote.js` lähettää
  artistin samalla "tyhjä = alkuperäinen" -logiikalla.
- Testit **239**.

## v2.04 (24.10.2026)

- **Versiovalinnan varmistus ja palautus:** `#variant-dialog` kysyy
  valinnan ennen `POST /api/tabs/{id}/variant`ia. Palvelin kopioi
  finalisoimattoman tilan `data/backups/variant-<tab_id>/`iin
  (`tab.gp5/musicxml/mid`, `variants/*.json`, `manifest.json`) ja
  tallentaa polun `meta.variant_backup`iin (`_variant_backup`).
  `POST /api/tabs/{id}/variant/restore` palauttaa tiedostot ja metan
  (`variants`, `default_variant`, `note_count`, `variant_finalized=false`).
- **UI:** `#variant-restore-button` (PALAUTA VERSIOT) näkyy vain
  finalisoidulla tabilla; `openVariantDialog`/`restoreVariants` app.js:ssä;
  Tiedot-dialogi näyttää "Versioiden varmuuskopio" -rivin.
- Testit **244**.

## Sanat GP5:ssä – työtapa (24.10.2026)

- **`beat.text` on paras paikka sanoille:** alphaTab piirtää sen tahtirivin
  yläpuolelle. GP:n omat lyriikat (`song.lyrics`, sana per isku) renderöityvät
  raidan alle, mutta menevät päällekkäin tiheissä 16-osakohdissa.
- **Tarkistus ilman selainta:** `node` + vendoroitu alphaTab
  (`alphaTab.importer.ScoreLoader.loadScoreFromBytes(bytes, new Settings())`)
  lukee `beat.text` / `beat.lyrics` ja raitojen nimet; visuaalinen tarkistus
  headless Edgellä (`msedge --headless=new --screenshot`) temp-HTML:stä,
  johon alphaTab ja GP5 upotetaan base64:nä (fontDirectory `file:///…/font/`).
- **Tyhjä raita toimii:** kopioi raita, tyhjennä nuotit
  (`beat.notes=[]`, `beat.status=BeatStatus.rest`) ja kirjoita tekstit.
  0 kielellä alphaTab ei osaa renderöidä raitaa (pidä kitaran kielet).
- **Sanoitukset eivät ole gitissä eivätkä memory bankissa** (tekijänoikeus);
  ne elävät vain `data/`ssa ja arkistossa.
