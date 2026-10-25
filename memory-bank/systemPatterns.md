# 🧩 Järjestelmän arkkitehtuuri – AI TABTOOL

## Kerrokset

```
FastAPI (app/main.py)
  ├─ /api/health, /api/version, /api/config
  ├─ /api/jobs, /api/jobs/{id}, /api/jobs/{id}/events (SSE)
  ├─ /api/tabs, /api/tabs/{id} (GET/DELETE)
  ├─ /api/tabs/import, /api/tabs/import-url
  ├─ /api/tabs/{id}/section, /attach-audio, /tempo, /sync, /library,
  │  /lyrics, /lyrics/lock
  ├─ /api/remote/command|state|commands, /api/lan/info|qr.svg
  ├─ score/export/audio
  ├─ /lan (PIN-kirjautuminen)
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
  samalla formaatilla. Ennen GP5-kirjoitusta `_sanitize_for_gp5` korjaa
  legacy-arvot, jotka GP5 tallentaa etumerkittöminä (v1.99: GP3:n
  grace-fret −1 → `isDead`, fret 0). Testi: GP3 −1-grace → aito GP5.
- `app/tab_download.py` hakee GP5/MusicXML-linkin palvelimella: vain
  julkinen http(s) (ei localhost/yksityisverkko), max 20 MB, redirectit
  validoitu. gprotab.netin HTML-sivu → automaattinen `?download`-retry.
- **Sanat sidecarina** (v2.06–v2.07): `app/lyrics.py` pitää sanoitukset
  tiedostossa `data/lyrics/<tab_id>.json` (`{"tab_id", "updated_at",
  "measures": {"10": "…"}}`), joten GP5/MusicXML/MIDI ja tabin meta pysyvät
  tavu-tasolla ennallaan. `GET/PUT /api/tabs/{tab_id}/lyrics`; lukittu tabi
  saa silti sanat. Katselimen `SANAT` avaa **kelluvan, raahattavan** paneelin
  (`#lyrics-dialog.lyrics-float`, z-index 2200, ei `body.modal-open`ia), ja
  `#lyrics-strip` lukee kuluvan tahdin `#bar-readout`-tekstistä
  (`MutationObserver`) – ei kelloa, ei `api`-kutsuja, ei audio-kirjoituksia.
  Otsikon `#lyrics-bar-badge` ja tahtilistan `is-current` auttavat
  asettamaan rivit kuuntelemalla. Paneeli on myös **kooltaan säädettävä**
  kahdesta nurkasta (`#lyrics-resize` = vasen yläkulma `nw`,
  `#lyrics-resize-se` = oikea alakulma `se`; koko talletetaan) ja
  sanoitusrivin koko tulee Settingsistä (`lyrics.scale`, 100–400 %, oletus
  200 % → CSS-muuttuja `--lyrics-scale`) ja koko näytön nosto
  (`lyrics.offset_px`, oletus 100 px → `--lyrics-offset`, vain
  fullscreenissa). Fullscreenissa rivi on 96vw leveä, joten se pysyy yhdellä
  rivillä. Tausta on musta (`#000`) ja sivupadding 3ch. Editorissa on
  PLAY/PAUSE, «, −5 s ja +5 s, ja **tahtinumeron klikkaus hyppää siihen
  tahtiin** `api.tickPosition`-tick-seekillä – alphaTab muuntaa tickin
  tempokartalla (myös tempo-automaatiot), kuvaa sen backing track -ajaksi ja
  kutsuu itse `mediaHandler.seekTo`-inversiota. **Älä laske tahdin aikaa
  itse** (`ticks * 60000 / (tempo * 960)`): Seek & Destroy vaihtaa tempon
  tahdissa 113 (208 BPM), jolloin vakiotempo heittää tahti tahdilta
  (v2.14-bugi: 220 → 235). Tabin poisto poistaa sidecarin.
  **Editorin työnkulku (v2.16–v2.18):** `«` on PLAYn vasemmalla puolella;
  tahtiklikki valitsee saman rivin ja maalatut sanat **siirretään tahtiin**
  (`assignLyricsSelectionToBar`: vanha `N |` siivotaan, rivinvaihdot
  litistetään; `Ctrl+Enter` = ankkuritahti +1). `Lukittu`-rasti tallentaa ja
  lukitsee sidecarin (`PUT /api/tabs/{id}/lyrics/lock`); lukittu sidecar
  vastaa tallennukseen **409** ja kenttä on read-only. Overlay **ei enää
  pidä edellistä riviä**: tyhjä tahti näyttää lähtölaskennan seuraavaan
  riviin (`nextLyricBar`, 9…1, `is-cue` = vain väri) ja viimeisen rivin
  jälkeen strip piiloutuu. Vartiotestit:
  `test_bar_click_selects_the_matching_lyric_line`,
  `test_selected_words_move_into_the_pressed_bar`,
  `test_lyrics_gap_counts_down_and_finished_lyrics_can_be_locked`,
  `test_lyrics_lock_blocks_saves_until_it_is_opened`.
- `app/library.py` hoitaa poiston: tab-hakemisto, stemmit sekä job/track-
  rivit. Jaettu audio säilyy, jos toinen tabi käyttää sitä; MP3 jää
  `EXTERNAL_DIR`iin. Poisto ei koske `data/`-juuren ulkopuolisiin polkuihin.
- **Kirjaston metadata** (v1.63, v2.03): `tabs.title_override` (näkyvä nimi),
  `tabs.artist_override` (näkyvä esittäjä; `original_artist` säilyy),
  `tabs.locked`, `tabs.archived`. `db._tab_row` palauttaa ylikirjoitetut
  `title`/`artist` ja alkuperäiset `original_title`/`original_artist`ina;
  `db._migrate_tab_columns` lisää sarakkeet vanhaan kantaan
  `init_db`ssä. Muutokset: `POST /api/tabs/{id}/library`
  (Form `artist`/`title`/`locked`/`archived`/`tuning`; `tuning_clear`
  poistaa ylikirjoituksen; tyhjä `artist` palauttaa generaattorin arvon).
  Lukittu tabi ei poistu (`DELETE` → 409) eikä muutu ennen avausta.
  `db.list_tabs` järjestää ylikirjoitetun artistin ja nimen mukaan; UI
  lajittelee lisäksi `localeCompare("fi")`lla.
- **Lähdemeta** (v2.03): `meta.audio_source_url` (YouTube-linkki, josta
  audio ladattiin; `_process_audio_job` ja AI-putki) sekä
  `meta.tab_source_url` / `meta.tab_source_file` (GP3/GP4/GP5/MusicXML-
  tuonnin linkki ja alkuperäinen tiedostonimi,
  `tab_import.import_tab_bytes(source_url=…, source_file=…)`).
  `_tab_summary` palauttaa `source_url`/`tab_source_url`/`tab_source_file`
  vain http(s)-linkkeinä; `audio_source_url` puuttuessa käytetään vanhaa
  `meta.source`-kenttää. Kirjaston **Tiedot**-modaali näyttää ne
  (`app.js`: `openDetailDialog`).
- **Kanava ja viritys metaan** (v1.67–v1.68): `meta.youtube_channel`
  (yt-dlp `%(channel)s`, fallback uploader) ja `meta.tuning_label` /
  `tuning_notes` (`app/tuning.py` lukee GP5:n kielet; presets
  standard/drop_d/eb_standard/d_standard/open_g, muut `Custom` +
  kirjaimet). `_tab_summary` palauttaa `channel`, `tuning`,
  `tuning_override`, `tuning_label`. Viritys-valinta vaikuttaa vain
  AI-generointiin, ei GP5-tuontiin. **v1.79:** `app.tuning.open_strings()`
  valitsee kitararaidan (6 kieltä, eniten nuotteja; rummut ohitetaan),
  koska moniraitaisen GP5:n raita 0 on usein laulu – ennen tätä Drop D
  -kitara näkyi `Standard E`nä. **v1.80:** `retune_tracks()` vaihtaa
  virityksen ja siirtää nauhat kielikohtaisesti, joten soivat sävelet
  pysyvät samoina.
- `app/tab_edit.py` hoitaa tab-datan muokkauksen ilman HTTP- tai
  ML-riippuvuutta: `read_song` (UTF-8 → cp1252 -fallback), `backup_file`
  (`data/backups/<id>-<aika>/`), `save_song` (temp + `os.replace`,
  validointi lukemalla takaisin), `expand_repeat` (toisto tahdeiksi),
  `remove_bars` (tahdin poisto, säilyttää absoluuttisen ajoituksen),
  `retune_tracks` (viritys + nauhojen siirto, sävelet ennallaan) ja
  `resolve_tab_gp5`. Kutsujat: `scripts/expand_repeat.py`,
  `scripts/trim_bars.py`, `scripts/retune_tab.py`.
- **LAN-kaukosäädin** (v1.82–v1.90): `app/remote.py` omistaa komentojonon
  (`RemoteHub`, 50 komentoa, TTL 60 s), TV:n tilan, QR-koodin
  (`segno`, aina sen hetkisestä IP:stä) ja valinnaisen PIN-portinvartijan.
  `app/main.py` kutsuu vain `remote.install(app)`. Selainpuolella
  `remote-bridge.js` pollaa komennot 0,5 s välein ja klikkaa olemassa
  olevia kontrolleja (`#play-button`, `#seek-slider`, `#rate-slider`,
  kirjaston rivi) – `app.js` ja soittoketju pysyvät koskemattomina.
  `/remote` pollaa tilan 1 s välein ja näyttää 150 px QR-koodin.
  Kolme tilaa (SOITA / LISÄÄ / SÄÄDÄ) pitävät yhden toiminnon kerrallaan:
  `jobs_running()` + TV:n `playing` estävät päällekkäisyyden 409:llä.
  Sivun auetessa silta lukitsee sekvenssin (`primeSequence`) eikä toista
  aiempia komentoja (v1.90). **v1.93–v1.98:** `/remote`-otsikko on
  yhdellä rivillä ja yksi tila-indikaattori (`Online` / `Offline` /
  `Offline-TV`); `«` lähettää `seek 0`, `+5 s` on poistettu; nopeus 1 %
  askelet + 95–105 % → 100 %. `refresh` käsittelee API- ja TV-tilan
  erikseen, joten lyhyt API-katkos ei väitä TV-näkymän olevan kiinni.
- **Bulk-tuonti/vienti** (v1.66): `app/bulk.py` – `import_folder()`
  (SHA-256-manifesti `.tabtool-imported.json`) ja `export_tabs()`
  (GP5/MusicXML/MIDI + `manifest.json` + ZIP). Skriptit
  `import_folder.py`, `export_tabs.py`, `adb_pull_gp.ps1`
  (puhelimen `/sdcard/Download`, ei appien yksityistä dataa).
- **Toistot ja teksti-huomautukset:** GP5 tallentaa toiston tahtiin
  (`isRepeatOpen`, `repeatClose`; PyGuitarPro lukee raa'an arvon ja
  vähentää 1:n, joten `repeatClose = soitokerrat − 1`). alphaTab
  noudattaa vain näitä. `Beat.text` (esim. "Should be played 17 times")
  on vain visuaalinen huomautus eikä ohjaa toistoa – esim. Dr. Feelgood
  m2 on tiedostossa ×2 ja audio toistaa enemmän, joten ero on tab-datassa.
  **v1.76 ratkaisu:** toisto kirjoitetaan tahdeiksi
  (`scripts/expand_repeat.py`) eikä toistomerkiksi, koska katselimen kello
  laskee partituurin keston kirjoitetuista tahdeista – toistomerkki
  jättäisi partituurin lyhyemmäksi ja score-end-guard katkaisisi toiston.
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
- **Sormitusversiot (v1.72, varmistus + varmuuskopio v2.04):** `fretboard.py`
  tuottaa kolme profiilia
  (`V1 · Avoimet kielet`, `V2 · Boksi`, `V3 · Vähän liikettä`),
  `playability.py` laskee 0–10-score; versiot kirjoitetaan raitoina samaan
  GP5:hen ja valitaan `VALITSE TÄMÄ`lla (`POST /api/tabs/{id}/variant`,
  `variant_store.py` JSON-snapshotit). **v2.04:** valinta kysytään
  `#variant-dialog`issa, ja ennen kirjoitusta finalisoimaton tila
  kopioidaan `data/backups/variant-<tab_id>/`iin (`manifest.json` +
  `variants/` + tab-tiedostot); `meta.variant_backup` kertoo sijainnin.
  `POST /api/tabs/{id}/variant/restore` kopioi varmuuskopion takaisin ja
  palauttaa `variants`/`default_variant`/`note_count`/`variant_finalized`
  → `PALAUTA VERSIOT` -nappi. **Sanat eivät säily versiovalinnassa**
  (GP5 kirjoitetaan JSON-snapshotista), joten sanoitus pidetään erillisellä
  `Vocals`-raidalla ja lukitussa kopiotabissa (`… (sanat)`).
  Jäljellä: parhaan version
  automaattinen valinta, score näkyviin ja turhien nuottien karsinta
  per tahti/fraasi.

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

- `/` ja `/display` = TV-näkymä, `/remote` = puhelinohjain + 150 px QR
  (v1.83). Puhelin ei toista audiota: TV omistaa audion.
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
  vierittyy oikealle (v1.50). Scoren marginaali tulee alphaTabin omasta
  `display.padding: [30, 15]` -asetuksesta (v1.58): `.alphatab` on
  paddingiton ja reunukseton (reunus inset-varjolla), koska alphaTab
  mitoittaa `.at-surface`n `offsetWidth`ista ja sijoittaa sen
  sisältölaatikkoon. Oikean reunan 30 px jättää 15 px scrollbarille
  oman kaistan.
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
- Kirjastorivi: `NIMEÄ` avaa rivin sisäisen lomakkeen (nimi +
  `[ ] Lukitse` + `[ ] Arkistoi` + TALLENNA/PERUUTA); poisto on punainen
  `×`, joka avaa varoitusdialogin. Poisto päivittää listan ja piilottaa
  viewerin, jos poistettu tabi oli auki; MP3 jää arkistoon. Lukittu rivi:
  `×` pois käytöstä, metassa "lukittu". Arkistoidut rivit näkyvät
  `ARKISTO (n)` -linkin takana; rastin poisto palauttaa ne päälistaan.
  Modaalissa KIRJASTO on vasen (leveämpi) sarake ja generaattori oikea
  (v1.64).
- **Soittokortti (v1.59–v1.62):** `.viewer-bar` on grid
  `auto auto 1fr auto` (LIBRARY, PLAY, otsikko, FULLSCREEN oikeassa
  reunassa); NÄKYMÄ/raitavalinnat omalla rivillään vasemmasta reunasta.
  `.transport` on oma taustakortti. EXPORT-rivi on tabikentän alla.
  Fullscreenissä LIBRARY piilotetaan ja grid kavennetaan kolmeen
  sarakkeeseen. **v1.81:** FULLSCREEN-nappi ja COUNT-IN-kytkin ovat
  samassa `.viewer-corner`-lohkossa (flex-sarake), joten ruudukkoon ei
  tullut uutta saraketta eikä tabialueen mitat muutu.
- **Modaali avautuu LIBRARY-napin korkeudelle** (v1.60):
  `openSearch()` mittaa napin `getBoundingClientRect().top`in ja asettaa
  `--modal-top`in; `#search-modal` käyttää sitä yläpaddingina ja
  paneelin `max-height` lasketaan samasta. Poiston dialogi pysyy
  keskitettynä.
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
- **Tunnettu rajoite (avaa lupaa vaativa korjaus):** `barDurationMs()` ja
  `ticksPerBar()` laskevat tahdin pituuden **kahdesta ensimmäisestä
  tahdista** (`bars[1].start − bars[0].start`). Jos tabi alkaa
  anacrusiksella (1/16 tai 1/8), SIIRTO ja KOHDISTA ovat 8×/16× liian
  voimakkaita. Toistaiseksi korjaus tehdään datasta
  (`scripts/trim_bars.py --bars 1`), kuten Dr. Feelgoodissa v1.78;
  koodikorjaus on sääntö #1:n ydintä ja vaatii erillisen luvan sekä koko
  regressiochecklistin.
- **Kursorin pieni edestakainen heitto (23.10.2026) – korjattu v1.91.**
  alphaTab asettaa syötetyn ajan kursoriksi ilman tarkistusta, joten
  selaimen ~250 ms paloina tuleva `audio.currentTime` (voi toistua tai
  mennä hetken taakse) käänsi kursorin. `syncPosition()` pitää syötön nyt
  monotonisena toiston aikana; kello (`syncTimeMs`), inversio
- **Kursorin nopeus = TAB BPM (23.10.2026).** `bpmDrift() = bpm /
  notatedTempo() − 1`, syöttö = `audioTime * (1 + drift)`, ja alphaTab
  muuntaa ajan tikeiksi GP5:n tempolla → **tehollinen nopeus on täsmälleen
  `tabs.bpm`**. Siksi BPM-kentän arvo on ainoa nopeussäädin: 142 vs audion
  ~143,5 = 18 ms/tahti (0,7 s / 40 tahtia, 2,7 s / 148 tahtia). Tämä on
  hyvä mittatikku, kun epäillään "kasvavaa heittoa".
- **SIIRTO-askel on 0,25 tahtia = 1 isku** (`setSyncOffsetBars` pyöristää
  neljännesosiksi, `syncOffsetBars * barDurationMs()`). Puolen iskun
  (~0,2 s) heittoa **ei voi säätää pois** nykyisellä UI:lla. Hienompi askel
  (esim. 1/16 tahtia) on sääntö #1:n ydintä → vaatii luvan.
- **Seek & Destroy -tabin tempo-automaatiot (erillinen riski – EI selitä
  tahteja 1–41):** `357dca53…` sisältää vain kaksi tempo-automaatiota –
  **tahti 113 → 208 BPM** ja **tahti 165 → 140 BPM**. Ne vaikuttavat
  **aikaisintaan tahdista 113 alkaen**, joten niillä ei voi olla osaa
  tahdeissa 1–80 näkyvään heittoon. Ne ovat oma, myöhemmin tarkistettava
  asiansa (jos alphaTab noudattaa niitä, kursori karkaa tahdista 113).
  Älä käytä niitä 1–41-ongelman selityksenä.
- **`api.score.tempo` kumoutuu – kursorin nopeus = BPM-kenttä.**
  `notatedTempo()` palauttaa saman `api.score.tempo`n, joten syöttö on
  `audio × bpm / tempo` ja alphaTabin score-time→tick käyttää samaa
  tempoa → **tehollinen nopeus = `tabs.bpm` täsmälleen**. Sekä tempo-
  automaatiot että `score.tempo` ovat siksi vain sanity check lokissa;
  ne eivät aiheuta nopeusvirhettä.
- **Onset-pohjainen tab↔audio-sovitus on monitulkintainen (23.10.2026).**
  Riffi toistaa saman 8-osakuvion, joten sekä 0 ms että ±0,3 s tuottavat
  lähes yhtä pienen virheen (`cost` 5–10 ms). **Älä yritä mitata intron
  vaihetta onseteilla** – käytä sovelluksen omaa `Osoitin`-lukemaa
  (`#sync-offset-readout`), joka mittaa suoraan kursorin ja audion eron.
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
- **Nopeus ≠ kohdistus (v1.96–v1.97):** `playbackRate` on
  harjoittelunopeus; `syncTimeMs` lukee `audio.currentTime`ia eikä
  `playbackRate` esiinny kellotuksessa, `bpmDrift`issä eikä
  `seekTo`-inversiossa. Vartiotesti:
  `test_playback_rate_never_enters_the_alignment_math`.
- Ei committoituja modeleita/audioita `static/`-hakemistoon.
