# 📊 Projektin edistyminen – AI TABTOOL

## v1.68 – Viritys näkyviin (21.10.2026)

- GP5:n avoimet kielet → `app/tuning.py`: Standard E / Drop D / Eb
  Standard / D Standard / Open G / Custom + kirjaimet. Metaan
  `tuning_label` (`D Standard · DGCFAD`) ja `tuning_notes`;
  `tabs.tuning` saa oikean avaimen (ennen `custom`).
- Näkyy soittokortin metassa, kirjastorivillä (ei-standardit) ja
  NIMEÄ-lomakkeen Viritys-kentässä (`tuning_override`, `tuning_clear`).
- `scripts/backfill_tuning.py` päivitti 6 tabia: WASP
  `Eb Standard · EbAbDbGbBbEb`, Dr. Feelgood `D Standard · DGCFAD`,
  muut Standard E. `smoke-youtube*`-tabien GP5 on rikki (testijäänteitä).
- 114 pytest-testiä.

## v1.67 – YouTube-kanava tabille (21.10.2026)

- `fetch_youtube_details()` lukee `%(channel)s` (fallback uploader);
  `AudioSource.channel` → `meta.youtube_channel` sekä AI-tabeille että
  GP5+YT-liitoksille. Näkyy `YT: <kanava>` kirjastossa, vihjeessä ja
  soittokortissa; `scripts/backfill_youtube_channel.py`. 108 testiä.

## v1.66 – Oma tuontikirjasto ja bulk-export (21.10.2026)

- `app/bulk.py`: `import_folder()` (SHA-256-manifesti estää tuplat) ja
  `export_tabs()` (GP5/MusicXML/MIDI + `manifest.json` + ZIP).
  Skriptit `import_folder.py`, `export_tabs.py`, `adb_pull_gp.ps1`
  (puhelimen Download, ei appien yksityistä dataa). `.gitignore`:
  `library/`. 101 pytest-testiä.

## v1.65 – POISTA punaiseksi ×:ksi (21.10.2026)

- Kirjastorivin poisto on ikonimainen punainen `×` (`aria-label`/`title`
  "Poista … kirjastosta"); lukitulla rivillä harmaa ja pois käytöstä.
- 101 pytest-testiä; `node --check` OK.

## v1.64 – KIRJASTO modaalin vasemmaksi (21.10.2026)

- Sarakkeet vaihdettu DOMissa: KIRJASTO vasen (1.15fr), generaattori
  oikea; erotinviiva generaattorin sarakkeessa. HTML-jäsennin: ei
  sulkemattomia tageja.

## v1.63 – Kirjaston nimet, lukitus ja arkisto (21.10.2026)

- Skeema: `tabs.title_override`, `locked`, `archived` + `ALTER TABLE`
  -migraatio `init_db`ssä (vanha data säilyy).
- `POST /api/tabs/{id}/library` (Form `title`/`locked`/`archived`);
  `_tab_summary` palauttaa `title_override`/`original_title`/`locked`/
  `archived`. Lukittu tabi → `DELETE` 409. Lista aakkosissa
  (SQL artist/nimi + `localeCompare("fi")` UI:ssa).
- UI: rivin `NIMEÄ`-lomake (nimi + Lukitse + Arkistoi + TALLENNA/
  PERUUTA), `ARKISTO (n)` -linkki listan lopussa (rastin poisto
  palauttaa pääkirjastoon).
- 101 pytest-testiä (5 uutta: nimeäminen, lukitus, arkisto, järjestys,
  migraatio).

## v1.57–v1.62 – Tabin marginaalit ja korttiasettelu (21.10.2026)

- Tabin marginaali tulee alphaTabin `display.padding`ista: v1.57
  15 px, v1.58 `[30, 15]` jotta scrollbar saa oman kaistan. `.alphatab`
  paddingiton/reunukseton (reunus inset-varjolla). Mitattu 15/15 ja
  30/30 px eikä ylivuotoa (1600/1366/1200/1024/800 px).
- v1.59–v1.62: hero pois, LIBRARY PLAY-korttiin, työkalurivi omalle
  riville, modaali avautuu LIBRARY-napin korkeudelle, EXPORT tabikentän
  alle, FULLSCREEN kortin oikeaan kulmaan, `.transport` omaksi kortiksi,
  LIBRARY piiloon fullscreenissä.
- Ei muutoksia soittoketjuun (`mediaHandler`/`seekTo`/`syncTimeMs`).

## v1.56 – Count-in toimii, 1:1 säilyy (20.10.2026)

- Count-in 5 → 0 validoitu käyttäjän kuuntelutestillä: laskenta näkyy
  soittonäkymässä, ääni alkaa vasta 0:n jälkeen, kohdistus pysyy 1:1.
- Korjaus: `shouldRunCountIn` ei enää lue `audio.currentTime`ia.
  alphaTab siirtää audion ensimmäiselle iskulle jo latauksessa
  (`mediaHandler.seekTo` → 0,8455 s SIIRTO −0,75:llä), joten v1.55:n
  `currentTime > 0.05` -ehto ohitti laskennan aina. Nyt ohitus perustuu
  käyttäjän omaan seekiin (`countInSkipped`, nollataan `loadTab`issa).
- Vartiotesti `tests/test_playback_guard.py`: count-in-funktioissa ei saa
  olla `audio`-/`api.`-viittauksia eikä soittoketjussa count-in-koodia.
- Headless-Edge (CDP): 5→4→3→2→1→0 ≈ 5,07 s, toisto 5,33 s; laskennan
  aikana `currentTime` 0,846 ja tahti 1 muuttumattomia, layout 800/800;
  2. PLAY peruu, seuraava aloittaa vitosesta; A/B audio 11,0 s → tahti 6
  molemmilla. Ei poikkeuksia konsolissa.
- 96 pytest-testiä.

## v1.55 – Count-in portinvartijana (20.10.2026)

- `handlePlayButton` + `#play-countdown` (fixed-lapsi `#viewer-section`issä,
  ei wrapperia `#alphaTab`in ympärille); `togglePlayback` pysyi
  muuttumattomana (diffissä 2 poistettua riviä).
- Ensimmäinen versio ei käynnistänyt laskentaa lainkaan (ks. v1.56).
- 96 pytest-testiä.

## v1.54 – Palvelimen hallinta käyttäjälle (20.10.2026)

- `stop.bat` + `scripts/stop_server.ps1`: pysäyttää portin 8000
  kuuntelijan ja sen python/uvicorn-emoprosessin, tulostaa PID:t ja
  varmistaa, että portti vapautui.
- `status.bat` + `scripts/server_status.ps1`: portin tila + `/api/version`.
- `start.bat`: porttitarkistus estää toisen instanssin käynnistämisen.
- Testattu: stop.bat pysäytti taustalle jääneen uvicornin (7596/17624),
  start.bat kieltäytyi varatusta portista (exit 1, ei selainta),
  toistettu stop.bat ilmoitti "not in use", status.bat näytti tilan.
- Ei muutoksia soittoon, sync-asetuksiin, tablatuuriin tai GP5-dataan.
- 93 pytest-testiä; palvelin jätetty pysäytetyksi käyttäjän
  käynnistettäväksi.

## v1.53 – Count-in poistettu, soitto 1:1 (20.10.2026)

- Countdown poistettu kokonaan: `#play-countdown`-overlay,
  `.viewer-stage`-kääre, countdown-CSS/JS ja count-in-tilat.
  `togglePlayback` palautettu v1.48:n muotoon (fullscreen +
  `api.playPause()` heti).
- SIIRTO-inversio säilyi v1.52:n mukaisena kaikille `time > 0` -seekeille.
- Mitattu: lataus t = 1,268 s (SIIRTO −0,75), PLAY aloittaa heti,
  10 s toiston jälkeen tahti 7 = odotettu, ei countdown-elementtejä,
  layout 1600/1600 px.
- Countdown tehdään myöhemmin eri tavalla, irrallaan soittoketjusta.
- 93 pytest-testiä; live-palvelin v1.53.

## v1.51–v1.52 – Count-in-yritys ja synkan palautus (19.10.2026)

- v1.51 rajasi SIIRTO-inversion osoitinklikkauksiin → alphaTabin omat
  seekit jäivät kääntämättä ja soitonaloitus siirtyi 1,268 s → 0.
- v1.52 palautti inversion kaikille `time > 0` -seekeille; count-in
  poistettiin v1.53:ssa. 93 pytest-testiä.

## v1.50 – Tabinäkymän leveyskorjaus (19.10.2026)

- `.viewer-stage` ja `.alphatab` saivat `min-width: 0` ja
  `width/max-width: 100 %`; canvas ei enää kasvattanut sivua ~7000 px.
- Mitattu 1366/1600/2560 px, ei sivuttaisvieritystä. 93 testiä.

## v1.49 – Tumma tabinäkymä, LIBRARY-nimet ja 5 s count-in (19.10.2026)

- Tabi tummalle taustalle (`display.resources`-värit, `.alphatab`
  `#0d1117`); SEARCH-napit → LIBRARY, modaalin h2-otsikko pois.
- `#play-countdown` `.viewer-stage`-ankkurissa, 5 → 0, toinen PLAY peruu.
- Headless-CDP validoitu; ei backend-muutoksia; 93 testiä.

## v1.43–v1.48 – Kursorin synkka ja klikkaus-seek (18.–19.10.2026)

- `backingTrackDuration` = partituurin kesto (`scoreEndTimeMs` master
  bar -tikeistä), joten alphaTabin venytys poistui ja kello on 1:1.
- KOHDISTA-klikkaus ja live-offset-näyttö; animoitu beat-kursori pois.
- Klikkaus-seek kääntää SIIRTO/SYNC/BPM-korjauksen. 93 testiä.

## v1.42 – Testiyhteenveto ja sessioalustus (18.10.2026)

- `pytest.ini`:stä pois `addopts = -q`, joten `pytest -q` tulostaa
  yhteenvedon; memory bankin komennot putkitetaan `Out-String -Width 200`.
- Ei toiminnallisia muutoksia; 93 testiä.

## v1.41 – GP3/GP4-tuonti ja audiopolun korjaus (18.10.2026)

- `import`/`import-url` hyväksyvät `.gp3`/`.gp4`; vanha versio
  kirjoitetaan aidoksi GP5:ksi. GP4 → GP5: notet/tahdit/tempo säilyivät.
- `db.import_tabs_from_disk` resolvoi `meta.audio_path`in `DATA_DIR`:stä.
- 93 testiä.

## v1.40 – GP5-tiedosto + YT-linkki yhdellä toiminnolla (18.10.2026)

- SEARCH-modaaliin tuli `GP5-linkki`-kentän rinnalle `tai GP5-tiedosto`.
  `POST /api/tabs/import` hyväksyy nyt `youtube_url` + `options`: ilman
  linkkiä vastaus on tab-yhteenveto, linkin kanssa audio-job, joka
  liittää audion tuotuun tabiin. Sama `_queue_audio_job` kuin
  GP5-linkilla; erillinen `IMPORT TAB` poistettiin.
- GP5 + oma audiotiedosto estetty; audion lähde on YouTube-linkki.
- 91 pytest-testiä; headless: tiedosto + YT → tabi, audio ja viewer.

## v1.39 – SEARCH-modaalin pino (18.10.2026)

- alphaTabin `.at-cursors` käyttää `z-index: 1000`, joten cursor piirtyi
  modaalin päälle. Modaali `2000`, dialogi `2100`,
  `.viewer-section { isolation: isolate }` ja cursor piiloon
  `body.modal-open`-tilassa; paneeli täysin peittäväksi.
- 89 testiä; selainkuvalla varmistettu, ei läpikuultoa.

## v1.38 – SEARCH-modaali, GP5-linkki ja poisto (18.10.2026)

- Haku, GP5-tuonti, kirjasto ja kappaleen valinta siirrettiin
  SEARCH-modaaliin; TV-näkymä jäi soittoon.
- `app/tab_download.py`: GP5/MusicXML-linkin palvelinlataus (vain
  julkinen http(s), max 20 MB, redirectit validoitu, gprotab.net
  HTML → `?download`-retry).
- `app/library.py` + `DELETE /api/tabs/{id}`: tab, hakemisto, stemmit ja
  job/track-rivit pois; jaettu audio säilyy; MP3 jää arkistoon.
- `options.archive_mp3` (oletus true) ja audio-only-job
  (`audio_only`/`attach_tab_id`, ei cachea) GP5 + YT -yhdistelmälle.
- 89 testiä; headless: modaali, valinta, poisto, GP5-render.

## v1.23–v1.37 – Katselu, tuonti ja synkki (18.10.2026)

- Katselu: tab-only, Näkymä, raitavalinnat, FULLSCREEN, cursor.
- Tuonti/pätkä/audio: GP5/MusicXML, `TEE TAB TÄSTÄ`,
  `LIITÄ AUDIO`, TAB BPM (v1.34 desimaali), Nopeus.
- Synkki: SYNC ±10 % (v1.30), SIIRTO tahdein 0,25 askel (v1.35–36),
  playback range -nollaus ja pause-palautus (v1.37).
- MP3-kuunteluversiot (v1.33) ja ulkoinen arkisto `D:\tabtool_files`
  (v1.32); tuotenimi AI TabTool (v1.22); käynnistyksen automaatio
  (v1.21); web-UI/job-jono/alphaTab (v1.20).
- **Ei pushia julkiseen GitHubiin** – vain lokaalit commitit.
  Memory bank -protokolla: `lue membank` (`.clinerules/00`).
- Yksityiskohdat: `CHANGELOG.md`.

## Testitilanne

- `pytest -q` → **114 passed**
- `compileall` → OK
- `node --check app.js` / `remote.js` → OK
- Headless-Edge/Chrome: alphaTab-render, cursor, fullscreen, GP5/MusicXML-
  tuonti (linkki + tiedosto), audio attach, BPM/desimaalitempo, SIIRTO,
  SYNC-tallennus, playback range -nollaus, SEARCH-modaali, kappaleen
  valinta ja poisto, **count-in 5→0** (v1.56: laskennan aikana audio ja
  tahti muuttumattomia, A/B sama tahti samassa audiokohdassa),
  **tabin marginaalit 30/30 px ja scrollbar-kaista** (v1.57–v1.62),
  **modaalin avautuminen ja kirjaston nimeämislomake** (v1.60, v1.63),
  **kanava ja viritys kirjastorivillä** (v1.67–v1.68, pytest + smoke).

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
- GP5 + oma audiotiedosto ei yhdisty yhdellä toiminnolla (audion lähde
  on YouTube-linkki); GP5-linkin lataus vaatii julkisen http(s)-osoitteen
  eikä tue kirjautumista/evästeitä vaativia sivustoja.
- **Ikärajoitettu YouTube-video ei lataudu ilman evästeitä.** yt-dlp
  vaatii `--cookies-from-browser`in, mutta Chrome/Edge lukitsevat
  cookie-DB:n ollessaan auki. Kierto: käytä ei-ikärajoitettua
  studioversiota (esim. virallinen kanava) tai sulje selain / anna
  cookie-tiedosto.
- Poisto ei poista MP3-kuunteluversiota eikä toisen tabin jakamaa audiota.
- Koodi v1.23–v1.56 on committoitu ja pushattu `origin/main`iin
  (käyttäjän pyynnöstä 20.10.2026). **v1.57–v1.68 on työpuussa
  commitoimatta** (21.10.2026); docs-commitit ovat HEADina. Lokaalit
  commitit toimivat edelleen palautuspisteinä.
  `data/` ja `docs/` eivät ole gitissä, joten ne tarvitsevat erillisen
  varmuuskopion.

## Seuraavaksi

0. **Settings-näkymä**: count-inin kesto ja muut toiston asetukset
   säädettäviksi (nyt `COUNT_IN_FROM` / `COUNT_IN_STEP_MS` /
   `COUNT_IN_ZERO_MS` `app.js`:ssä).
1. Päättää soittotapa/refinger: asemaprofiilit, playability-score,
   turhien nuottien karsinta, per-tahti/fraasiasema.
2. Vasta sitten Phase 3 / Spotify: PKCE, haku/metadata, SDK/Connect,
   tokenit `oauth_tokens`-tauluun ja mockatut API-testit.
3. Phase 4: remote-kaukosäädin.

GP5-datan korjaus ei ole prioriteetti: ohjelma todettu 1:1 ainakin
149 tahtiin (Seek & Destroy), ja tabi on syötettä, ei tuotetta.
