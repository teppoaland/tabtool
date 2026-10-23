# 📊 Projektin edistyminen – AI TABTOOL

## 🔒 ISO LUKKO – soitto valmis ja jäädytetty (23.10.2026)

- Käyttäjä kuitannut: **kaikki soittoviat on korjattu** ja soitto toimii
  **99 % tarkkuudella** oikein, mikä **riittää**. Tila on hyväksytty
  lopulliseksi.
- **Soittoon vaikuttaviin koodeihin EI KOSKETA.** Mikä tahansa koodi, jolla
  on pienikin mahdollisuus sotkea soittoa, tehdään **varoen** ja käyttäjää
  **pyydetään testaamaan soitto referenssikappaleella** (Seek & Destroy,
  SIIRTO −0,75 / BPM 142) ennen ja jälkeen.
- Katso `.clinerules/07-playback-frozen.md`.

## v1.93–v2.01 – Remote-UI, nopeus, GP3 ja kirjastot (23.10.2026)

- **Remote (v1.93–v1.98):** otsikko yhdelle riville (AT-merkki,
  DISPLAY/API-nav ja REMOTE-kicker pois); QR sivun alaosaan; `«` =
  `seek 0`, `+5 s` pois; nopeus 1 % askelet + 95–105 % → 100 %; yksi
  tila-indikaattori `Online` / `Offline` / `Offline-TV` (lyhyt
  API-katkos ei enää väitä TV:n olevan kiinni); seek-sliderin
  strict-mode `ReferenceError` korjattu (`forwardButton`-jäänne) +
  regressiotesti.
- **Päänäkymä (v1.96–v1.97):** `#rate-slider` step 0,01 + 10 %:n snap;
  ei muutoksia `setPlaybackRate`iin; vartiotesti estää `playbackRate`n
  päätymisen kohdistusmatematiikkaan.
- **`start.bat` (v1.94):** yksi ajo pysäyttää vanhan Python/uvicorn-
  instanssin ja käynnistää uuden; vierasta prosessia ei tapeta.
- **GP3 → GP5 (v1.99):** `_sanitize_for_gp5` korjaa grace-fretin −1
  (`isDead`, fret 0) ennen kirjoitusta; White Wedding (gprotab) toimii.
  Testi: GP3 −1-grace → aito GP5.
- **Kirjastot (v2.00–v2.01):** TV:n LIBRARY ja puhelimen SOITA/SÄÄDÄ
  järjestetään bändin nimellä (`artist` → `title`,
  `localeCompare("fi")`); remote-kirjaston sisäinen `max-height`/
  `overflow` poistettu → yksi sivun scrollbar.
- Testit **195**; tagi `v1.99` = viimeisin pushattu palautuspiste
  (v2.00–v2.01 paikallisia).

## v1.92 – Count-in ei siirrä alkukohdistusta (23.10.2026)

- **Juurisyy (bisect):** count-inin 5→0-portinvartija (v1.55–v1.56) viivästytti
  `togglePlayback()` → `api.playPause()` ~5,25 s; fullscreen-resize siirsi
  audion pois aloituspaikalta → intro heitti 1–40, runko 41+ 1:1. v1.48/v1.53
  (ei count-in) 1:1, v1.68 (count-in) rikki; v1.48→v1.53 nettoero = 0.
- **Korjaus:** `handlePlayButton` tallentaa audion paikan (`countInAudioTime`)
  ja `finishCountIn` palauttaa sen ennen `togglePlayback()`ia. Synkka-ketju
  koskematon. Sääntö 07 dokumentoitu (v1.92 palautus = no-op paluu).
- Käyttäjän kuuntelutesti: Seek & Destroy / Mötley / Whiplash 1:1 alusta
  (99 %). Tagi `v1.92`. 189 testiä.

## v1.91 – Kursorin edestakainen heitto (23.10.2026)
- Syy: alphaTab asettaa jokaisen syötetyn ajan kursoriksi ilman
  tarkistusta (`output.updatePosition` → `updateTimePosition`), ja selain
  ilmoittaa `audio.currentTime`n ~250 ms paloina, jotka voivat toistua tai
  mennä hetken taaksepäin → kursori hyppäsi iskun eteen ja palasi.
- Korjaus: `syncPosition()` pitää syötön monotonisena toiston aikana
  (`lastFedScoreMs`, `lastFedAudioS`, `FEED_JITTER_S = 0,3 s`). Pidetty
  arvo on aina oikean lukeman tuottama, joten kello ei mene audion edelle.
  `force` (seek/pause/lataus/SIIRTO/SYNC), pysäytetty audio ja yli 0,3 s
  taaksepäin menevä aito seek nollaavat vertailun → kelaus toimii.
- Ei muutoksia `syncTimeMs`iin, `mediaHandler`iin, `togglePlayback`iin,
  audio-eventteihin, DOM-id:ihin eikä CSS:ään. 1 uusi vartiotesti →
  **189 testiä**. `syncPosition` ajettu Node-harnessilla (monotonisuus,
  forced-seek, aito taaksepäin-seek, pause-palautus, `audio.seeking`-esto).
- **Odottaa käyttäjän kuuntelu-/tabsynkkitestiä.**
- **HUOM (23.10.2026): tämä ei ratkaissut käyttäjän raportoimaa
  ongelmaa** (heitto kasvaa tahdeissa 1–41 ja "katoaa" tahdissa 41).
  v1.91 ei voi muuttaa kellon nopeutta, joten syy on muualla — katso
  `activeContext.md`:n avoin ongelma. A/B: `git revert 1807688`.

## ✅ Ratkaistu v1.92 – heitto tahdeissa 1–41 (count-in)

- Syy: count-inin portinvartija, ei audio eikä synkka-koodi (katso v1.92 yllä).
- Hypoteesit H0/H1/H2 kumottu: heitto ei ollut tallenteen tempo eikä
  naamiointi, vaan viivästetyn lähdön siirto fullscreen-resizen vuoksi.

## v1.90 – Vanhojen remote-komentojen toisto (23.10.2026)
- TV-silta aloitti jonon alusta → vanhat komennot laukesivat sivun
  auetessa (eri aloituskohta eri startilla; restart korjasi). Nyt
  `primeSequence` lukitsee sekvenssin eikä suorita aiempia. 2 uutta
  testiä → **188 testiä**. Tabidata tarkistettu: lukitut sync-arvot tallessa.

## v1.89 – Remote kolmessa tilassa (23.10.2026)
- SOITA / LISÄÄ / SÄÄDÄ, vain yksi paneeli kerrallaan. Lisäys estetty
  soiton aikana ja soitto jobin aikana (palvelin 409 + UI).
- LISÄÄ: YT + valinn. GP5-linkki/-tiedosto → olemassa olevat reitit;
  job-seuranta 1,5 s; kirjasto päivittyy. SÄÄDÄ: nimi/viritys/lukitus/
  arkistointi. 6 uutta testiä → **186 testiä**.

## v1.88 – Varoitus, kun TV-näkymä puuttuu (23.10.2026)
- `/remote`: `#tv-hint` kertoo `TV-näkymä ei ole auki. Avaa
  http://127.0.0.1:8000 tietokoneella.`, kun `tv_online: false`.
- `start.bat` muistuttaa pitämään `/`-välilehden auki ja avaamaan
  `/remote` toiseen välilehteen. 1 uusi testi → **180 testiä**.

## v1.87 – PAUSE-tila punaisella (23.10.2026)
- `remote.js` togglaa `.is-playing`-luokan; CSS `#remote-play.is-playing`
  = `--error`-tausta + tumma teksti. 1 uusi testi → **179 testiä**.

## v1.86 – PLAY ei himmene offline-tilassa (23.10.2026)
- `remote.js`: `playButton.disabled` pois; komento jonoutuu ja toteutuu
  kun TV-sivu on näkyvissä. Tilateksti `TV: Offline · avaa TV-näkymä`.
- `TV_ONLINE_S` 10 → 30 s, koska selain hidastaa taustavälilehden
  ajastimia. 2 uutta testiä → **178 testiä**.

## v1.85 – QR-palstan URL-rivi (23.10.2026)
- `.remote-pair` 150 px levyiseksi ja `.remote-url` rivittymään samaan
  leveyteen (`word-break`); oikea reuna linjassa QR:n kanssa. Vain CSS.
  176 testiä.

## v1.84 – QR-SVG:n xmlns-korjaus (23.10.2026)
- `/api/lan/qr.svg` käytti `svg_inline`iä, joka jättää `xmlns`:n pois →
  selain näytti rikkinäisen kuvan. Nyt `segno.save(kind="svg")` →
  `<svg xmlns="http://www.w3.org/2000/svg" …>`. Testi valvoo määrettä.
  176 testiä.

## v1.83 – Yksi käynnistin + QR `/remote`ssa (23.10.2026)
- `start-lan.bat` **poistettu** (turha): `start.bat` sitoo aina
  `0.0.0.0:8000`:aan, tulostaa LAN-osoitteet ja avaa TV-näkymän.
- **150 × 150 px QR `/remote`-sivun oikeassa reunassa** + osoite
  `http://<LAN-IP>:8000/remote`; piilotettu alle 720 px näytöillä.
  QR encodaa LAN-IP:n, ei 127.0.0.1; päivittyy 30 s välein (istuntotoken).
- `/connect`-sivu poistettu (`connect.html/js`); `GET /connect` → 404.
- `scripts/lan_addresses.ps1` tulostaa vain `LAN: http://…/remote`.
- `app.js` ei muuttunut; `index.html` vain `?v=1.83`-leimat. 176 testiä.

## v1.82 – LAN-kaukosäädin (23.10.2026)
- `start-lan.bat` (= `start.bat lan`): `0.0.0.0:8000`, LAN-osoitteet
  (`scripts/lan_addresses.ps1`), selain `/connect`-sivulle. `status.bat`
  näyttää LAN-osoitteen, kun palvelin kuuntelee kaikkia rajapintoja.
- `app/remote.py`: `RemoteHub` (komentojono 50, TTL 60 s, `seq`/`reset`),
  `/api/remote/command|state|commands`, `/api/lan/info|qr.svg`, `/connect`,
  valinnainen LAN-PIN (`/lan`, HttpOnly-eväste, SHA-256, 10 yritystä/60 s).
  QR-pariutus käyttää istuntotokenia – PIN ei koskaan URLiin.
- `app/static/remote-bridge.js`: pollaa komennot 0,5 s ja klikkaa olemassa
  olevia transport-nappeja (PLAY, seek-slider, rate-slider, kirjaston rivi).
  **`app.js` ei muuttunut** → sääntö #1 säilyy.
- `/remote` = puhelinnäkymä (PLAY/PAUSE, ±5 s, seek, Nopeus, kirjasto, TV:n
  tila). `connect.html/js` = QR-sivu.
- `segno==1.6.6` (BSD-3-Clause, puhdas Python). 23 uutta testiä →
  **175 pytest-testiä**. Vaatii käyttäjän puhelin-/kuuntelutestin.
  (v1.83 yhdisti käynnistyksen ja siirsi QR:n `/remote`en.)

## v1.81 – COUNT-IN ON/OFF (22.10.2026)
- FULLSCREEN-napin alle `.viewer-corner`-lohkoon liukukytkin
  (`#countin-toggle`, `#countin-state`, ON/OFF), oletus ON, valinta
  localStorageen (`tabtool:countIn`). Luetaan **vain**
  `shouldRunCountIn`issa → soittoketju koskematon. 2 guard-testiä.

## v1.80 – Virityksen vaihto sävelet säilyttäen (22.10.2026)
- `app.tab_edit.retune_tracks` + `scripts/retune_tab.py`: raidat, joiden
  avoimet kielet täsmäävät `--from`iin, viritetään uudelleen ja nauhat
  siirretään kielikohtaisesti (`nauha = sävel − uusi avoin`). Validointi
  vertaa jokaisen nuotin soivan sävelen; varmuuskopio + palautus.
- Volbeat `116a1fa3…` Drop D → **D Standard** (2529 nuottia, max nauha 13,
  BAR 7 `0/2`, BAR 9–10 `4/2 5/3 6/4`). 2 uutta testiä.

## v1.79 – Viritys kitararaidasta (22.10.2026)
- `app.tuning.open_strings()`: 6-kielinen raita, jossa eniten nuotteja
  (rummut ohitetaan) → Volbeat-tabit `Standard E` → `Drop D · DADGBE`.
- `backfill_tuning.py --force` (ohittaa manuaaliset overridet, lukee
  UTF-8 → cp1252). 2 uutta testiä.

## v1.78 – Pickup-tahdin poisto (22.10.2026)
- `remove_bars` pitää ensimmäisen jäljelle jäävän tahdin absoluuttisen
  alun. Dr. Feelgoodin 1/16-anacrusis pois → 135 tahtia, `ticksPerBar`
  240 → 3840 (SIIRTO oli 16× liian voimakas). 1 uusi testi.

## v1.77 – Ylimääräiset tahdit pois (22.10.2026)
- `remove_bars` + `scripts/trim_bars.py` (`--bars "137,138"`, `--reset-sync`).
  Dr. Feelgood 138 → 136 tahtia: audion musiikki päättyy 287,74 s, tabi
  jatkui 291,6 s. 3 uutta testiä.

## v1.76 – Toisto kirjoitetaan tahdeiksi (22.10.2026)
- `app/tab_edit.py` (`read_song`, `backup_file`, `save_song`,
  `expand_repeat`, `count_notes`) + `scripts/expand_repeat.py`.
  Dr. Feelgood bar 2 ×2 → 17 tahtia (122 → 138, 2615 nuottia).
  6 uutta testiä.

## v1.75 – TEMPO cp1252 + SIIRTO ±999 (22.10.2026)
- `_gp5_song()` lukee GP5:n UTF-8 → cp1252 -fallbackilla ja kirjoittaa
  UTF-8:na (Dr. Feelgood `Mötley Crüe`, 0xf6). `SYNC_OFFSET_LIMIT = 999`
  (backend + `#shift-input` + `app.js`n clampit). 2 uutta testiä.


## v1.74 – GP5 UTF-8 (21.10.2026)
- GP5 merkkijonot kirjoitetaan/luetaan UTF-8:na (alphaTab luki cp1252:n
  väärin → `·`/`ä` = `�`); `backfill_gp5_utf8.py` korjasi 2 AI-tabia.

## v1.73 – Haamunuottien siivo (21.10.2026)
- `app/pipeline/prune.py`: oktaavihaamut pois + polyfonia max 4/isku;
  `PIPELINE_VERSION=3`, meta `pruned_notes`. 5 uutta testiä.

## v1.72 – Sormitusprofiilit + versiot (21.10.2026)
- `fretboard.py`: 3 profiilia (V1·Avoimet/V2·Boksi/V3·Vähän liikettä) +
  uusi kustannusfunktio. `playability.py` 0–10 score. Versiot raitoina
  yhdessä GP5:ssä; `VALITSE TÄMÄ` (`POST /api/tabs/{id}/variant`),
  `variant_store.py`, `PIPELINE_VERSION=2`. Uudet testit:
  fretboard_profiles, playability, tab_variant.

## v1.71 – Lukkoikoni (21.10.2026)
- 🔒 lukitun kappaleen kirjastoriville (rivin oma elementti).

## v1.70 – Lukitus kaikkiin asetuksiin (21.10.2026)
- `locked` = read-only: nimi/viritys/arkistointi/TAB BPM/SYNC/SIIRTO/
  audion liityntä + poisto (409). UI disabloi; avaus NIMEÄstä. 2 testiä.

## v1.69 – Kappale soi loppuun (21.10.2026)
- `syncTimeMs` clamp `scoreEnd−50ms` + `handlePlayButton`-nollaus →
  tabin päätyttyä audio soi loppuun, kursori jää viimeiselle iskulle.
  1 testi (score-end-guard).

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

## v1.20–v1.40 – Perusta, tuonti ja modaali (18.10.2026)

- Katselu (tab-only, Näkymä, raitavalinnat, FULLSCREEN, cursor), pätkä- ja
  audiojobi, SYNC ±10 %, SIIRTO, playback range -nollaus, MP3-kuunteluversiot,
  `D:\tabtool_files`-arkisto, web-UI/job-jono/alphaTab, käynnistyksen
  automaatio, tuotenimi AI TabTool.
- SEARCH-modaali (haku, GP5-linkki + `app/tab_download.py`, GP5-tiedosto +
  YT-linkki samalla jobilla), kappaleen poisto (`app/library.py`),
  GP3/GP4-tuonti (muunnos aidoksi GP5:ksi, 0 nuottoeroa).
- Modaalin pino (`z-index` 2000/2100, cursor piiloon) ja
  `db.import_tabs_from_disk`.
- Yksityiskohdat `CHANGELOG.md`:ssä, ankkurit `techContext.md`:ssä.

## Testitilanne

- `pytest -q` → **188 passed**
- `compileall` → OK
- `node --check app.js` / `remote.js` / `remote-bridge.js` → OK
- Headless-Edge/Chrome: alphaTab-render, cursor, fullscreen, GP5/MusicXML-
  tuonti (linkki + tiedosto), audio attach, BPM/desimaalitempo, SIIRTO,
  SYNC-tallennus, playback range -nollaus, SEARCH-modaali, kappaleen
  valinta ja poisto, **count-in 5→0** (v1.56: laskennan aikana audio ja
  tahti muuttumattomia, A/B sama tahti samassa audiokohdassa),
  **tabin marginaalit 30/30 px ja scrollbar-kaista** (v1.57–v1.62),
  **modaalin avautuminen ja kirjaston nimeämislomake** (v1.60, v1.63),
  **kanava ja viritys kirjastorivillä** (v1.67–v1.68, pytest + smoke).

## Tunnetut rajoitukset

- **Kursorin pieni edestakainen heitto (käyttäjän havainto 23.10.2026) –
  korjattu v1.91, odottaa kuuntelutestiä.** alphaTab asettaa jokaisen
  syötetyn ajan kursoriksi ilman tarkistusta, joten selaimen ~250 ms
  paloina tuleva `audio.currentTime` käänsi kursorin hetkeksi takaisin.
  `syncPosition()` pitää syötön nyt monotonisena toiston aikana; kello,
  `mediaHandler.seekTo`-inversio ja audio-eventit eivät muuttuneet.
  Jos heitto näkyy yhä, mittaa ennen uutta arvausta (ks. `activeContext.md`).

- AI-transkriptio on luonnos; särö/akordit/nopeat soolot virheellisiä.
- Basic Pitch ei ole kitarakohtainen; otteet/asemat voivat poiketa
  opitusta tabista. Referenssitabi + TuxGuitar auttavat.
- Standard E -alueen ulkopuoliset nuotit pudotetaan varoituksella.
- Tempo voi olla half/double-time; AI-BPM on arvio; TAB BPM/Nopeus
  korjaa.
- Soittotapa/refinger (asemaprofiilit, nuottien karsinta) puuttuu.
- Referenssitabilla on 258 tahtia vs. AI 249; rakenne voi poiketa.
- Rummut vaativat oman mallin; Spotify Phase 3; remote valmis v1.82
  (vaatii käyttäjän puhelintestin).
- GP5 + oma audiotiedosto ei yhdisty yhdellä toiminnolla (audion lähde
  on YouTube-linkki); GP5-linkin lataus vaatii julkisen http(s)-osoitteen
  eikä tue kirjautumista/evästeitä vaativia sivustoja.
- **Ikärajoitettu YouTube-video ei lataudu ilman evästeitä.** yt-dlp
  vaatii `--cookies-from-browser`in, mutta Chrome/Edge lukitsevat
  cookie-DB:n ollessaan auki. Kierto: käytä ei-ikärajoitettua
  studioversiota (esim. virallinen kanava) tai sulje selain / anna
  cookie-tiedosto.
- Poisto ei poista MP3-kuunteluversiota eikä toisen tabin jakamaa audiota.
- **Koko historia v1.23–v1.99 on pushattu `origin/main`iin** (käyttäjän
  pyynnöistä 20.10. ja 23.10.2026); **tagi `v1.99` = viimeisin pushattu
  palautuspiste**; v2.00–v2.01 ovat paikallisia (ei pushattu).
  `scripts/build_kiss_legend.py` on gitignorattu (koko kappaleen
  nuottidata, tekijänoikeus). `data/` ja `docs/` eivät ole gitissä,
  joten ne tarvitsevat erillisen varmuuskopion.

## Seuraavaksi

0. ~~Kursorin heitto (sääntö #1)~~ ✅ **RATKAISTU v1.92 – ISO LUKKO.**
   Soitto kuitattu valmiiksi (99 %, riittää). Soittoon vaikuttaviin
   koodeihin ei kosketa; riskimuutokset varoen + referenssitesti
   (Seek & Destroy, SIIRTO −0,75 / BPM 142).
1. **Pickup-varotin soittokelloon** (`barDurationMs`/`ticksPerBar`):
   anacrusis-tabissa SIIRTO/KOHDISTA 8×/16× liian voimakas. Vaatii luvan
   (sääntö #1) + regressiochecklist + kuuntelutesti. Sitä ennen data-kierto
   `scripts/trim_bars.py --bars 1`.
2. **Tuonnin laatuapurit:** duplikaattien tunnistus (sama GP5 SHA-256 tai
   sama artisti+biisi eri audio), tabin pituus vs. audion kesto,
   pickup-varoitus.
3. **Settings-näkymä**: count-inin kesto ja muut toisto-oletukset
   säädettäviksi (nyt `COUNT_IN_FROM` / `COUNT_IN_STEP_MS` /
   `COUNT_IN_ZERO_MS` `app.js`:ssä; ON/OFF-kytkin on jo v1.81).
4. **Refinger/playability loppuun:** paras versio automaattisesti, score
   näkyviin, turhien nuottien karsinta per tahti/fraasi.
5. Vasta sitten Phase 3 / Spotify: PKCE, haku/metadata, SDK/Connect,
   tokenit `oauth_tokens`-tauluun ja mockatut API-testit.
6. Remote-kaukosäädin valmis (v1.82–v1.90) – odottaa käyttäjän
   puhelintestiä.

GP5-datan korjaus ei ole prioriteetti: ohjelma todettu 1:1 ainakin
149 tahtiin (Seek & Destroy), ja tabi on syötettä, ei tuotetta.
