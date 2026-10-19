# 📊 Projektin edistyminen – AI TABTOOL

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

- v1.51 rajasi SIIRTO-inversion osoitinklikkauksiin (600 ms ikkuna).
  Silloin alphaTabin omat lataus-/play-/pause-seekit jäivät kääntämättä:
  soitonaloitus siirtyi 1,268 s → 0 ja koko biisi oli 0,75 tahtia eri
  kohdassa (SIIRTO −0,75 / BPM 142 -kalibrointi).
- v1.52 palautti inversion kaikille `time > 0` -seekeille. Count-in ei
  koskenut PLAY-nappiin, audioon eikä kursoriin, mutta se poistettiin
  kokonaan v1.53:ssa.
- 93 pytest-testiä.

## v1.50 – Tabinäkymän leveyskorjaus (19.10.2026)

- v1.49:n `.viewer-stage`-kääre otti leveytensä alphaTabin canvasin
  sisältöleveydestä: grid-rata kasvoi ~7000 px:iin ja sivu vierittyi
  oikealle. Korjaus: `.viewer-stage` ja `.alphatab` saivat
  `min-width: 0` sekä `width/max-width: 100 %`.
- Mitattu 1366/1600/2560 px: `document.scrollWidth == clientWidth`,
  `#alphaTab` 1084 px (`.shell`-raja). Ei muita muutoksia;
  93 pytest-testiä.

## v1.49 – Tumma tabinäkymä, LIBRARY-nimet ja 5 s count-in (19.10.2026)

- Tabi renderöityy oletuksena tummalle taustalle: `display.resources`
  (`mainGlyphColor`, `secondaryGlyphColor`, `staffLineColor`,
  `barSeparatorColor`, `barNumberColor`, `scoreInfoColor`) ja
  `.alphatab`-tausta `#0d1117`; highlight-kursori `var(--ok)`.
- SEARCH-napit → **LIBRARY** (yläpalkki ja etusivu), lede ja README
  päivitetty; modaalista poistettu `SEARCH`-h2 ja tilalla
  `aria-label="Library ja generaattori"`.
- `#play-countdown`-overlay `.viewer-stage`-ankkurissa: PLAY käynnistää
  **5 → 0** -laskennan, audio alkaa vasta 0:n jälkeen; toinen PLAY peruu.
  Kesto `COUNTDOWN_SECONDS` (`app/static/app.js`).
- Validoitu headless-Edgellä (CDP, trusted click, ei autoplay-poikkeusta):
  tumma render, modaali ilman otsikkoa, countdown 5→0, peruutus ja toisto.
- Ei backend-muutoksia; 93 pytest-testiä; live-palvelin v1.49.

## v1.43–v1.48 – Kursorin synkka ja klikkaus-seek (18.–19.10.2026)

- v1.43–v1.45: `backingTrackDuration` palauttaa partituurin keston
  (`scoreEndTimeMs` master bar -tikeistä), joten alphaTabin
  backing track -venytys poistui ja kello on 1:1. `api.endTime` oli
  live-arvo (0 ennen toistoa), siksi master bar -laskenta.
- v1.46–v1.47: KOHDISTA-klikkaus ja live-offset-näyttö; animoitu
  beat-kursori pois päältä, jotta kursori ei ekstrapoloi ääntä edelle.
- v1.48: klikkaus-seek kääntää SIIRTO/SYNC/BPM-korjauksen, jotta klikattu
  nuotti osuu kohdalleen. (v1.51 rajaa inversion vain käyttäjän
  osoitinklikkaukseen; alphaTabin lataus-seek ~0,44 ms menee läpi.)
- Ei backend-muutoksia; 93 pytest-testiä.

## v1.42 – Testiyhteenveto ja sessioalustuksen tulosteet (18.10.2026)

- `pytest.ini`:stä poistettiin `addopts = -q`. Memory bankin ohje
  `pytest -q` oli siten `-qq`, mikä piilotti yhteenvedon kokonaan
  (vain pisteet). Nyt `pytest -q` tulostaa `93 passed`.
- `lue membank` -protokollan komennot putkitetaan
  `Out-String -Width 200`:lla; agentin kuori on 12×16 merkkiä ja
  shell integration saattoi pudottaa tulosteen.
- Ei toiminnallisia muutoksia; 93 testiä.

## v1.41 – GP3/GP4-tuonti ja audiopolun rescan-korjaus (18.10.2026)

- `POST /api/tabs/import` ja `import-url` hyväksyvät `.gp3`/`.gp4`;
  PyGuitarPro lukee ja vanha versio kirjoitetaan aidoksi GP5:ksi
  (`tab.gp5`). Testattu GP4 → GP5: notet, tahdit ja tempo säilyivät.
- `db.import_tabs_from_disk` resolvoi nyt relatiivisen
  `meta.audio_path`-arvon `DATA_DIR`-juuresta; aiemmin levyrekisteröinti
  pudotti `audio/…wav`-polun ja tabi menetti audion (404).
- UI: tiedostovalitsin `.gp3/.gp4/.gp5`, GP-tekstit ja vihje
  "GP4 muunnetaan GP5:ksi".
- Kirjastoon tuotu 5 kappaletta YT-audiolla; ks. `activeContext.md`.
- 93 pytest-testiä.

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

- `pytest -q` → **93 passed**
- `compileall` → OK
- `node --check app.js` / `remote.js` → OK
- Headless-Edge/Chrome: alphaTab-render, cursor, fullscreen, GP5/MusicXML-
  tuonti (linkki + tiedosto), audio attach, BPM/desimaalitempo, SIIRTO,
  SYNC-tallennus, playback range -nollaus, SEARCH-modaali, kappaleen
  valinta ja poisto.

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
- Koodi v1.23–v1.41 on committoitu (v1.41 = GP3/GP4-tuonti); tagi
  `v1.29` = `bb704e8`. Repoa ei pushatta julkiseen GitHubiin:
  lokaalit commitit toimivat palautuspisteinä.
  `data/` ja `docs/` eivät ole gitissä, joten ne tarvitsevat erillisen
  varmuuskopion.

## Seuraavaksi

0. **Settings-näkymä**: countdownin kesto (nyt 5 s kovakoodattu
   `COUNTDOWN_SECONDS`) ja muut toiston asetukset säädettäviksi.
1. Päättää soittotapa/refinger: asemaprofiilit, playability-score,
   turhien nuottien karsinta, per-tahti/fraasiasema.
2. Vasta sitten Phase 3 / Spotify: PKCE, haku/metadata, SDK/Connect,
   tokenit `oauth_tokens`-tauluun ja mockatut API-testit.
3. Phase 4: remote-kaukosäädin.

GP5-datan korjaus ei ole prioriteetti: ohjelma todettu 1:1 ainakin
149 tahtiin (Seek & Destroy), ja tabi on syötettä, ei tuotetta.
