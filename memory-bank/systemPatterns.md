# 🧩 Järjestelmän arkkitehtuuri – AI TABTOOL

## Kerrokset

```
FastAPI (app/main.py)
  ├─ /api/health, /api/version, /api/config
  ├─ /api/jobs, /api/jobs/{id}, /api/jobs/{id}/events (SSE)
  ├─ /api/tabs, /api/tabs/{id} (GET/DELETE)
  ├─ /api/tabs/import, /api/tabs/import-url
  ├─ /api/tabs/{id}/section, /attach-audio, /tempo, /sync
  ├─ score/export/audio
  └─ /, /display, /remote  → app/static/
        │
        ▼
Job-kerros (app/jobs.py: jono + worker + cache + eventit)
        │
        ▼
SQLite (app/db.py: tracks, jobs, tabs, oauth_tokens, settings)
        │
        ▼
Putki (app/pipeline/)
  audio_source → separate → transcribe → tempo → quantize
  → fretboard → build → export_gp5/musicxml/midi
```

- Reitit eivät kutsu Demucsia/Basic Pitchiä suoraan; ne luovat jobin.
- Putki ei importtaa FastAPIä eikä kirjoita HTTP-vastauksia.
- Job-kerros importtaa putken vasta ajon aikana (kevyt käynnistys).
- Frontend ei käsittele Spotify-client-secretiä (PKCE).
- Kaikki polut `app/config.py`:stä. `data/` on yksityinen juuri.
- `app/tab_import.py` hoitaa GP3/GP4/GP5- ja MusicXML-tuonnin sekä
  metatiedot (PyGuitarPro/music21) ilman ML-putkea. GP3/GP4 kirjoitetaan
  tuonnissa aidoksi GP5:ksi, jotta alphaTab ja GP5-export toimivat
  samalla formaatilla.
- `app/tab_download.py` hakee GP5/MusicXML-linkin palvelimella: vain
  julkinen http(s) (ei localhost/yksityisverkko), max 20 MB, redirectit
  validoitu. gprotab.netin HTML-sivu → automaattinen `?download`-retry.
- `app/library.py` hoitaa poiston: tab-hakemisto, stemmit sekä job/track-
  rivit. Jaettu audio säilyy, jos toinen tabi käyttää sitä; MP3 jää
  `EXTERNAL_DIR`iin. Poisto ei koske `data/`-juuren ulkopuolisiin polkuihin.
- GP5 + YouTube -yhdistelmä: `jobs.submit_job` luo audio-only-jobin
  (`options.audio_only`, `attach_tab_id`), joka lataa audion ja liittää
  sen valmiiksi tuotuun tabiin ilman transkriptiota. Sama polku
  GP5-linkille ja paikalliselle GP5-tiedostolle.
- YouTube-metadata haetaan `audio_source.fetch_youtube_metadata`illa;
  `jobs.effective_track_metadata` valitsee oikean nimen/artistin.
- Pätkäjobi luodaan tabin omasta audiopolusta (`/section`); BPM-korjaus
  kirjoittaa GP5:n `song.tempo`-arvon (`/tempo`).

## Putken data

- `NoteEvent` – pitch, start/end sekunteina, velocity.
- `QuantizedNote` – tick-grid, `tie` = jatkuu edellisestä tahdista.
- `TabNote` – pitch, string, fret, start_tick, duration_ticks, tie.
- `TabMeasure` / `TabDocument` – tahdit, viritys, BPM, varoitukset.
- **Ticks:** 960 per quarter; 1/16 = 240 ticks; 4/4 tahti = 3840.
- Kvantisointi jakaa nuotit tahtirajoilla ja merkitsee jatkot tie:ksi.

## Fretboard

- Viterbi/DP: kustannus = käsiaseman liike, fret-span, korkeat frets,
  open-string-bonus.
- Kielikohtainen monofonia: jos kieli on varattu, nuotti siirretään
  vapaalle kielelle tai edellistä nuottia lyhennetään.
- Viritykset: standard, drop D, Eb, D, open G, bass 4-string.
- Standard E -alueen ulkopuoliset nuotit pudotetaan varoituksella.
- **Soittotapa/refinger ei ole vielä toteutettu.** Suunniteltu:
  asemaprofiilit (1./5./7. asema, avoimet/matalat kielet, ei venytyksiä),
  playability-score ja turhien/harmonisten nuottien karsinta. Nykyinen
  DP tuottaa yhden sormituksen, joten sama nuottidata voi näyttää
  erilaiselta kuin opittu tabi.

## Export

- **GP5 ensisijainen** (PyGuitarPro). Validointi lukee tiedoston takaisin:
  tahtikestot täsmäävät, ei duplicate string -nuotteja.
- **MusicXML** tab-clef + `<technical><string><fret>`.
- **MIDI** pretty_midi, tempo = BPM, program 25.
- Tie-tila on nuottikohtainen (v1.11).

## Cache / DB

Toteutettu SQLite (`app/db.py`, WAL, `data/tabtool.sqlite3`):

- `tracks` – title, artist, source_type, source_ref, fingerprint, audio
- `jobs` – status, stage, progress, options, warnings, error, tab_id
- `tabs` – `cache_key`, directory, metadata, `meta_json`, `audio_path`
- `oauth_tokens` – Spotify PKCE -tokenit (Phase 3)
- `settings`

Tuodut tabit: `source_type = import`; `meta.files` kertoo GP5- tai
MusicXML-tiedoston. `db.update_tab_audio` liittää audion ja
`db.update_tab_tempo` päivittää BPM:n sekä `meta.json`in. Audiota ei
kopioida; tuotu tabi voi jakaa AI-tabin audiopolun. Täydet kappaleet
oletus; pätkäjobi käyttää samaa audio-/options-lähdettä.

`cache_key = sha256(fingerprint + PIPELINE_VERSION + options)`.
Fingerprint: uploadin sisältöhash, YouTube-URL tai local path + koko +
mtime. Polut tallennetaan suhteessa `DATA_DIR`:iin.

Reititys- ja arkistovalinnat (`audio_only`, `attach_tab_id`,
`archive_mp3`) eivät kuulu cache-avaimeen (`JobOptions.as_cache_dict`),
joten MP3-valinnan vaihtaminen ei invalidoi aiempia tabeja. `audio_only`
ohittaa aina cache-haun.

Invariantit:

1. Sama audio + asetukset → sama tulos.
2. Valmis tab cachetetaan; `regenerate` korvaa vanhan tabin ja
   hakemiston vasta onnistuneen viennin jälkeen.
3. Atomiset kirjoitukset: temp-hakemisto + `os.replace`.
4. Path traversal -suojaus; `data/` ei koskaan static-mounttiin.
5. Jobin metadataan malli, versio, parametrit ja varoitukset.
6. Poisto poistaa tabin datan, mutta ei MP3-kuunteluversiota eikä
   toisen tabin jakamaa audiota.

`external_store.archive_external` mirroroi YouTube-audion ja tuodut
GP5/MusicXML-tabit `EXTERNAL_DIR`iin (oletus `D:\tabtool_files`,
`Artist - Title.ext`). Samalla levyllä käytetään hard linkiä; virhe ei
kaada jobia. `archive_mp3` koodaa YouTube-WAV:t
`audio/mp3/<Artisti>/`-kansioon (ffmpeg, VBR ~190 kbps).

Levyltä luettaessa (`import_tabs_from_disk`) suhteellinen
`meta.audio_path` resolvoidaan `DATA_DIR`-juuresta (v1.41); aiemmin se
resolvoitui työhakemistosta ja tabi menetti audionsa.

## UI

- `/` ja `/display` = TV-näkymä, `/remote` = puhelin (Phase 4).
- alphaTab 1.8.4 vendoroituna `app/static/vendor/alphaTab/`
  (Bravura-fontti `font/`, `core.useWorkers = false`).
- `PlayerMode.EnabledExternalMedia` + `IExternalMediaHandler`;
  positio 50 ms välein `api.player.output.updatePosition(ms)`.
  `backingTrackDuration` = partituurin kesto (v1.45), jotta alphaTabin
  backing track -venytys ei siirrä kursoria.
- Paikallinen audio: `<audio>` + Range (`FileResponse` 206).
- Oletus: **tab-only** (StaveProfile.Tab), Näkymä-valinta, raitavalinnat
  (tabikohtainen muisti), FULLSCREEN/autofullscreen, cursor + edellinen
  rivi, dynamiikat piilossa, vaakascrollbar pois. Tabi renderöityy
  **tummalle** taustalle (`display.resources`-värit, `.alphatab`
  `#0d1117`; v1.49). `.alphatab` tarvitsee `min-width: 0`:n, muuten
  alphaTabin canvas voi kasvattaa grid-radan (~7000 px) ja sivu
  vierittyy oikealle (v1.50).
- Aikajana: aika/kesto, tahtilukema, ±5 s, Space/nuolet, seek vierittää
  cursorin kohdalle; `TEE TAB TÄSTÄ` tekee pätkäjobin.
- **Count-in (v1.56):** 5 → 0 toteutetaan soittoketjun ulkopuolella.
  `handlePlayButton` kutsuu muuttumatonta `togglePlayback`ia joko heti
  (pause, seek ennen ensimmäistä PLAYta) tai laskennan jälkeen.
  `#play-countdown` on `#viewer-section`in fixed-lapsi eikä grid/flex-
  item, joten mitat eivät muutu. Toinen PLAY/Esc peruu; `loadTab` nollaa
  lipun. AlphaTab siirtää audion ensimmäiselle iskulle jo latauksessa
  (0,8455 s SIIRTO −0,75:llä), joten ohitus ei voi perustua
  `audio.currentTime`iin.
- **LIBRARY-modaali** (v1.38, entinen SEARCH v1.49): YouTube-linkki,
  GP5-linkki tai GP5-tiedosto, MP3-valinta, GENERATE TAB, kirjasto ja
  kappaleen valinta/poisto samassa ikkunassa. TV-näkymä jää soittoa varten.
  GP5-lähde ohittaa AI-generoinnin; YT-audio liitetään samalla jobilla.
  Score-format valitaan `meta.files`:stä (gp5/musicxml). Tuotu tabi ilman
  audiota: PLAY ja aikajana piilotetaan, `LIITÄ AUDIO` hakee samannimisen
  AI-tabin audion. Modaalin iso otsikko on poistettu (v1.49).
- Kirjastorivi: `POISTA` avaa varoitusdialogin; poisto päivittää listan ja
  piilottaa viewerin, jos poistettu tabi oli auki. MP3 jää arkistoon.
- `TAB BPM` kirjoittaa GP5-tempon **TALLENNA**-napista; desimaalit
  sallitaan (0,1 askel) ja desimaaliosa toteutuu toiston korjauksena.
  Tallentamaton arvo näkyy punaisena. `Nopeus` (50–150 %, 0,1 %) on
  harjoittelusäädin. `SYNC` (±10 %, 0,05 %) siirtää tabin aikajanaa
  audioon nähden ja `SIIRTO` (0,25 tahdin askel = 1 isku) korjaa
  vakiosiirron tai rakenne-eron; molemmat tallentuvat metaan
  (`sync_drift`, `sync_offset_bars`,
  `POST /api/tabs/{id}/sync`); AI-BPM on arvio.
- LIBRARY-modaali ja poiston varoitusdialogi ovat hyväksytyt; muita
  modaaleja/toasteja ei lisätä ilman pyyntöä.
- Modaalin pino: alphaTabin `.at-cursors` käyttää `z-index: 1000`, joten
  modaali on `2000`, dialogi `2100`, `.viewer-section` on `isolation:
  isolate` ja cursor piilotetaan `body.modal-open`-tilassa.
- **Seek-invariantti (v1.52):** `mediaHandler.seekTo` kääntää
  SIIRTO/SYNC/BPM-korjauksen **kaikille** `time > 0` -seekeille, myös
  alphaTabin omille lataus-/play-/pause-seekeille. Inversion rajaaminen
  pelkkiin osoitinklikkauksiin (v1.51) siirsi soitonaloituksen
  1,268 s → 0 ja rikkoi synkan; `time === 0` jätetään ennalleen.
- Aluevalinta: alphaTabin raahaus ei jää loopiksi – `playbackRange`
  nollataan heti. Pause palauttaa cursorin audion aikaan.
- **Sääntö #1 – koskematon ydin** (`.clinerules/07-playback-frozen.md`):
  soitto- ja kohdistusketju (`notatedTempo`/`bpmDrift`, `barDurationMs`/
  `syncTimeMs`/`scoreEndTimeMs`, `mediaHandler.seekTo`-inversio,
  `syncPosition`, `seekTo`, `clearPlaybackRange`, `togglePlayback`,
  `output.handler`-kytkennät, audio-eventit) sekä transportin DOM-id:t,
  `.alphatab`-mitat ja `/sync|tempo|section`-reitit ovat koskemattomia
  ilman lupaa. Regressiochecklist on samassa säännössä: SIIRTO −0,75 /
  BPM 142 → lataus 1,268 s ja 10 s → tahti 7. **Hyväksyntä tehdään
  käyttäjän kuuntelu-/tabsynkkitestillä** (ei automatisoitavissa), ja
  palvelin on käyttäjän CMD-ikkunassa (`stop.bat`/`start.bat`).
- Ei committoituja modeleita/audioita `static/`-hakemistoon.
