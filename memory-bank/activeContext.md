# 📍 Aktiivinen konteksti – AI TABTOOL

> **Versio:** `v2.12` (25.10.2026)
> **Git:** v1.23–v1.99 **pushattu** `origin/main`iin 23.10.2026 käyttäjän
> pyynnöstä; **tagi `v1.99` = viimeisin pushattu palautuspiste**
> (`git reset --hard v1.99`); v2.00–v2.12 ovat paikallisia. Älä pinnaa
> HEAD-hashia pysyvästi.
> **Push:** vain erillisestä pyynnöstä (käyttäjä pyysi 20.10. ja 23.10.2026).
> **Repo:** https://github.com/teppoaland/tabtool
> **Palvelin:** käyttäjän hallinnassa (`start.bat` / `stop.bat`); Cline ei
> käynnistä sitä taustalle eikä pysäytä ilman pyyntöä.

## Nyt

- 🔒 **ISO LUKKO (23.10.2026) – SOITTO ON VALMIS JA JÄÄDYTETTY.** Käyttäjä
  on kuitannut: kaikki soittoviat on korjattu ja soitto toimii **99 %
  tarkkuudella** oikein, mikä **riittää**. Tila on hyväksytty lopulliseksi:
  **soittoon vaikuttaviin koodeihin ei kosketa.** Mikä tahansa koodi, jolla
  on pienikin mahdollisuus sotkea soittoa, tehdään **varoen** ja käyttäjää
  **pyydetään testaamaan soitto referenssikappaleella** (Seek & Destroy,
  SIIRTO −0,75 / BPM 142) ennen ja jälkeen. Katso
  `.clinerules/07-playback-frozen.md`.
- **v2.12 (25.10.2026) – Soittoeditori sanoitusikkunaan:**
  - PLAY/PAUSE (`handlePlayButton`), « (`seekTo(0)`), −5 s / +5 s
    (`seekBy`); editorin PLAY peilaa katselimen nappia `MutationObserver`illa
    (ei uusia audio-eventtejä).
  - Tahtinumeron klikkaus → `jumpToBar(bar)`: score-aika
    `masterBars[i].start` + `notatedTempo()` → **mediaHandler.seekTo**
    (jäädytetty inversio) + `syncPosition(true)` + `updateTransport` +
    `scrollScoreToCursor`. Ei omaa drift/offset-matematiikkaa (vartiotesti).
    Kaksoisklikkaus lisää yhä rivin `tahti | `.
  - Testit **268**.
- **v2.11 (25.10.2026) – Koon muutto kummasta nurkasta:**
  - Kaksi kahvaa: `#lyrics-resize` (vasen yläkulma, `data-corner="nw"`) ja
    `#lyrics-resize-se` (oikea alakulma, `se`); sama `startLyricsResize`,
    nurkka elementistä. `nw` pitää vastakkaisen reunan paikallaan
    (`left`/`top` seuraavat pointeria), klampaus 360×280 … ikkuna−16.
  - Otsikkoriville vasen padding, ettei kahva peitä otsikkoa; kahva
    `z-index: 2` eikä käynnistä raahausta.
  - Testit **267** (laajennettu: kaksi kahvaa + nurkkalogiikka).
- **v2.10 (25.10.2026) – Sanoitustausta mustaksi ja väljemmäksi:**
  - `.lyrics-current`: `background: #000` (läpinäkyvä rgba ja tekstin varjo
    pois), sivupadding **3ch**, pystypadding **0.55em** symmetrisesti →
    korkeampi musta palkki, teksti keskellä. `ch`/`em` skaalautuvat
    `lyrics.scale`n mukana (myös 300 % / fullscreen).
  - Testit **267** (1 uusi: läpinäkymätön tausta, 3ch-sivuväli, ei
    rgba-täyttöjä eikä reunaviivaa).
- **v2.09 (25.10.2026) – Fullscreen-sanoitus ylemmäs + nosto-asetus:**
  - Koko näytössä `#lyrics-strip` nostetaan
    `calc(1.1rem + var(--lyrics-offset, 100px))` ja `.lyrics-current` saa
    `max-width: 96vw` → pitkä rivi pysyy yhdellä rivillä 300 %:lla.
    Normaali näkymä ennallaan.
  - Uusi Settings-kenttä `lyrics.offset_px` (ryhmä Sanat): 0–600 px,
    askel 10, **oletus 100 px**. `applyLyricsStyle()` kirjoittaa
    `--lyrics-scale` + `--lyrics-offset` (vain dokumentin tyylit).
  - Testit **266** (laajennetut koon/noston tarkistukset + CSS-säännöt).
- **v2.08 (25.10.2026) – Sanoitusikkuna resizable + tekstin koko Settingsiin:**
  - `#lyrics-resize` (oikea alakulma, pointer events): paneelin koko
    360×280 … ikkuna−16 px; koko tallentuu `tabtool:lyricsPos`-tietueeseen
    (`width`/`height`) ja klampataan resize/fullscreenissa. Tekstikenttä
    kasvaa paneelin mukana (`.lyrics-form .field` flex).
  - Settings: uusi ryhmä **Sanat**, kenttä `lyrics.scale` (100–400 %,
    askel 25, **oletus 200 %** = tuplat). `applyRuntimeSettings` →
    `applyLyricsScale()` → CSS-muuttuja `--lyrics-scale`;
    `.lyrics-current` = `calc(clamp(…) * var(--lyrics-scale, 2))`, joten
    oletus on voimassa jo ennen asetusten latausta ja myös fullscreenissa.
  - Testit **266** (2 uutta + Settings-testin ryhmä/rajat).
- **v2.07 (25.10.2026) – Sanat-editori kelluvaksi:**
  - `#lyrics-dialog` on nyt `position: fixed` paneeli (`z-index: 2200`,
    `#lyrics-handle`-otsikosta raahaus pointer-eventeillä, sijainti
    localStoragessa `tabtool:lyricsPos`). Ei taustaverhoa eikä
    `body.modal-open`ia → PLAY/seek/kursorin seuranta toimivat paneelin
    takaa, joten sanat voi asettaa kuuntelemalla.
  - Otsikossa `#lyrics-bar-badge` (`Tahti N`) ja tahtilistassa
    `.lyrics-bar.is-current`; tieto tulee edelleen vain `#bar-readout`ista.
    Chip-lista vierittyy vain omassa kontissaan (sivu ei hyppää).
  - Data: Reino Nordin -tabin 97 rivin mäppäys (tahdit 1–99) kirjoitettu
    sidecariin sekä päätabille `668d62…` että lukitulle kopiolle
    `33cbc8bf…`; käyttäjän rivit 1–3 voittivat. **Ei gitiin** (data/,
    tekijänoikeus).
  - Testit **263** (1 uusi: kelluva paneeli + drag ei koske audioon/apiin).
- **v2.06 (25.10.2026) – Sanat sidecarina (täysi irtikytkentä):**
  - Sanat eivät mene GP5/MusicXML/MIDIin eivätkä tabin metadataan:
    `data/lyrics/<tab_id>.json` (`{"measures": {"10": "…"}}`),
    `app/lyrics.py` (validointi, temp + `os.replace`).
  - `GET/PUT /api/tabs/{id}/lyrics`; lukittu tabi saa silti sanat;
    tabin poisto poistaa sidecarin (`library.delete_tab_data`).
  - UI: `.viewer-tools`in **SANAT** avaa editorin (tahtilistat + rivi per
    tahti `tahti | teksti`). Overlay `#lyrics-strip` on `position: fixed`
    ja lukee vain `#bar-readout`-tekstiä `MutationObserver`illa – ei
    `api`-kutsuja, ei audio-kirjoituksia, ei kellomuutoksia.
  - Testit **262** (16 uutta + vartiotesti
    `test_lyrics_stay_outside_the_playback_chain`). Vaatii käyttäjän
    UI-/kuuntelutestin (sääntö 07).
- **v2.05 (25.10.2026) – LIBRARY yläpalkkiin, PLAY pelkäksi toistoksi:**
  - Yläpalkin `LIBRARY` (`#open-search-top`) on oranssi päätoiminto
    (`primary nav-library`).
  - Katselimen `#open-search` poistettu (turha toisto PLAYn vieressä);
    `.viewer-bar` 3 saraketta, `openSearch()`/`remote-bridge.js` käyttävät
    yläpalkin painiketta.
  - `PLAY` ei enää avaa koko näyttöä (`enterViewerFullscreen` poistettu
    `togglePlayback`ista ja `handlePlayButton`ista); label vaihtuu
    `PAUSE`ksi kuten ennen. FULLSCREEN on oma painike. Kello, seek-inversio,
    `syncPosition` ja count-in (5→0 + `togglePlayback` kerran) ennallaan;
    v1.92:n audiopaikan palautus jäi (FULLSCREEN kesken laskennan).
  - Testit **246** (2 uutta: PLAY ei koske fullscreeniin, LIBRARY vain
    yläpalkissa). Vaatii käyttäjän kuuntelu-/UI-testin (sääntö 07).
- **Sanat tabiin (24.10.2026, vain dataa – ei koodimuutosta):**
  - Reino Nordin `668d62…` (*Xsuaalisuuteen*): **97 riviä sanoja** GP5:n
    `beat.text`-kenttinä, tahdit 1–99 (tauot 82–83 ja 100–101). Ajoitus
    sovitettiin käyttäjän korvakiintopisteisiin (M 1/1, "Mun sydän palaa"
    tahti 10, kertosäkeet 22/30/59/84) ja Demucs-vokaalistemman
    frasialkuihin. Sanat ovat oikeilla tahdeilla mutta eivät iskuilleen.
  - Sanat siirrettiin **omalle 4. raidalle `Vocals`**: V1/V2/V3 pysyivät
    muuttumattomina (1681 nuottia/raita), joten mitä tahansa niistä voi
    soittaa sanojen kanssa. Vocals on opasraita (taukoja + tekstit).
  - Suojaus: erillinen **lukittu** kirjastotabi `33cbc8bf…`
    *Xsuaalisuuteen (sanat)* (sama audio, ei versio-metadataa) +
    arkistokopio `D:\tabtool_files\tabs\Reino Nordin - Xsuaalisuuteen (sanat).gp5`
    + `data/backups/668d62…-vocals-20261024-155850/`.
  - **Rajoite:** `VALITSE TÄMÄ` kirjoittaa GP5:n versio-JSON:sta, jolloin
    Vocals-raita katoaa siitä tabista. Siksi lukittu kopio; sanat voi
    lisätä takaisin temp-skriptillä (skriptiä ei viedä gitiin).
  - Sanoitukset eivät ole gitissä eivätkä memory bankissa (tekijänoikeus).
- **v2.04 (24.10.2026) – Sormitusversion valinta turvalliseksi (ei
  soittoketjuun):**
  - `VALITSE TÄMÄ` kysyy nyt varmistuksen (`#variant-dialog`) – ennen
    painallus finalisoi suoraan ja poisti muut versiot ilman paluuta.
  - Palvelin kopioi finalisoimattoman tilan
    `data/backups/variant-<tab_id>/`iin (tab.gp5/musicxml/mid,
    `variants/*.json`, `manifest.json`); `meta.variant_backup` kertoo
    sijainnin.
  - `POST /api/tabs/{id}/variant/restore` + `PALAUTA VERSIOT` -nappi
    palauttavat V1/V2/V3:n, `default_variant`in ja `note_count`in.
    TAB BPM säilyy valinnassa ja palautuksessa; lukittu tabi estää
    molemmat (409).
  - Testit **244** (5 uutta `tests/test_tab_variant.py`).
- **v2.03 (24.10.2026) – Kirjaston Tiedot ja lähdemeta (ei soittoketjuun):**
  - `NIMEÄ` → **Tiedot**: modaali (`#detail-dialog`) muokkaa esittäjän
    (`tabs.artist_override` + migraatio, `original_artist` säilyy), nimen,
    virityksen, lukituksen ja arkistoinnin. BPM/tahtia/nuotteja/kanava/
    lisäysaika/ID sekä **Audiolähde**- ja **Tablähde**-linkit näkyvät vain
    luku -tietoina. Lukittu tabi pysyy vain luku -tilassa.
  - Lähdetiedot talteen: `meta.audio_source_url` (YouTube-linkki myös
    GP5 + YouTube- ja LIITÄ AUDIO -tapauksissa) sekä `meta.tab_source_url`
    ja `tab_source_file` (GP-linkki ja alkuperäinen tiedostonimi).
    Vanha `meta.source` toimii fallbackina; `scripts/backfill_source_url.py`
    täydentää vanhat audiolinkit job-riveistä.
  - Puhelimen SÄÄDÄ saa Esittäjä-kentän.
  - Testit **239**.
- **v2.02 (24.10.2026) – Settings-näkymä ja puhelimen soittimet (ei
  soittoketjuun):**
  - `/settings` (SETTINGS yläpalkissa REMOTE- ja API-linkkien jälkeen)
    säätää count-inin askelmat ja kestot (oletus 5 × 1000 ms + 250 ms =
    entinen toiminta), Näkymän oletuksen, 16 päänäkymän toiminnon
    näkyvyyden (oletus: kaikki näkyvät) sekä puhelimen LISÄÄ/SÄÄDÄ-,
    Nopeus- ja soitinvalinnan.
  - Arvot ovat SQLite `settings`-taulussa: `app/settings.py`, `GET/POST
    /api/settings` (tyypit ja rajat validoitu, virhe → 422). `app.js` lukee
    ne latauksessa `applyRuntimeSettings`issa; `beginCountIn()` lukee kestot
    omassa lohkossaan eikä kutsu audiota eikä alphaTabia.
  - Puhelimessa SOITA/LISÄÄ/SÄÄDÄ siirtyivät sivun alaosaan ja niiden
    paikalle tulivat avoimen tabin soittimet: TV raportoi raidat
    (`clean_state` → `tracks`) ja silta klikkaa samaa `.track-chip`iä
    (uusi komento `track`). 2 soitinta = 1 rivi, 5 = 2 riviä.
  - Testit **229**; kuuntelutesti (rule 07) on käyttäjän.
- **v1.93–v2.01 (23.10.2026) – UI/tuonti, ei soittoketjuun:**
  - v1.93–v1.95: remote-otsikko yhdelle riville; `«` = `seek 0`,
    `+5 s` pois; nopeus 1 % askelet + 95–105 % → 100 %; QR sivun alaosaan.
  - v1.96: sama nopeusikkuna päänäkymään. v1.97: `playbackRate` todettu
    harjoittelunopeudeksi + vartiotesti; remote saa yhden
    tila-indikaattorin `Online` / `Offline` / `Offline-TV`.
  - v1.98: puhelimen seek-slider jäi vasempaan laitaan, koska `render()`
    viittasi poistettuun `forwardButton`iin (strict-mode ReferenceError);
    viittaus pois + regressiotesti.
  - v1.99: GP3-tuonti kaatui grace-nuotin fret −1:een; `_sanitize_for_gp5`
    mappaa sen `isDead`-lipuksi ennen GP5-kirjoitusta. White Wedding toimii.
  - v2.00–v2.01: kirjastot aakkosissa **bändin nimellä** (`artist` →
    `title`); remote-kirjastosta pois sisäinen scroll-ikkuna (yksi sivun
    scrollbar).
- ✅ **RATKAISTU (23.10.2026, v1.92) – kursorin heitto tahdeissa 1–41.**
  Syy ei ollut audion tempo eikä synkka-koodi, vaan **count-inin
  portinvartija** (v1.55–v1.56): se viivästytti `togglePlayback()` →
  `api.playPause()` noin 5,25 s, ja fullscreen-resize ehti siirtää audion
  pois aloituspaikalta laskennan aikana → viivästetty soitto alkoi väärästä
  kohdasta. Bisect: v1.48/v1.53 (ei count-in) 1:1, v1.68 (count-in) rikki;
  v1.48→v1.53 nettoero synkka-funktioissa = 0.
  **Korjaus (v1.92):** `handlePlayButton` tallentaa audion paikan lähdön
  hetkellä (`countInAudioTime`) ja `finishCountIn` palauttaa sen ennen
  `togglePlayback()`ia. Synkka-ketju koskematon. Käyttäjän kuuntelutesti:
  Seek & Destroy / Mötley / Whiplash 1:1 alusta (99 %). Tagi `v1.92`.
  v1.91:n monotoninen syöttö pysyy (ei selittänyt tätä, mutta on oikea
  korjaus edestakaiseen heittoon). Tahdin 113 tempo (208 BPM) on edelleen
  erillinen, myöhemmin tarkistettava riski.
- **v1.91 (23.10.2026): kursorin edestakainen heitto – tekninen korjaus
  tehty (ei ratkaissut yllä olevaa ongelmaa).**
  - Syy: alphaTab asettaa jokaisen syötetyn ajan kursoriksi **ilman
    tarkistusta** (`updatePosition` → `updateTimePosition`), ja selain
    ilmoittaa `audio.currentTime`n ~250 ms paloina, jotka voivat toistua tai
    mennä hetken taaksepäin → kursori hyppäsi iskun eteen ja palasi.
  - Korjaus vain `syncPosition`issa: syöttö pidetään monotonisena toiston
    aikana (`lastFedScoreMs`, `lastFedAudioS`, `FEED_JITTER_S = 0,3 s`).
    Pidetty arvo on aina oikean lukeman tuottama → kello ei mene audion
    edelle. `force` (seek/pause/lataus/SIIRTO/SYNC), pysäytetty audio ja
    yli 0,3 s taaksepäin menevä aito seek nollaavat vertailun.
  - Koskematta: `syncTimeMs`, `mediaHandler.seekTo`, `togglePlayback`,
    audio-eventit, DOM-id:t, CSS. 1 uusi vartiotesti → **189 testiä**.
- **v1.90 (23.10.2026): vanhojen remote-komentojen toisto korjattu.**
  - TV-silta aloitti jonon alusta (`since=0`) → edellisen 60 s komennot
    (seek/play/select_tab/rate) laukesivat sivun auetessa. Eri startilla eri
    aloituskohta; restart tyhjensi jonon. Nyt `primeSequence` lukitsee
    nykyisen sekvenssin eikä suorita aiempia.
  - **Diagnoosi:** tabidata ehjä (12 tabia, lukitut SYNC/SIIRTO tallessa,
    ei duplikaatteja, ei jumeja); lukko ei nollaa sync-arvoja.
  - 2 uutta testiä → **188 testiä**.
- **v1.89 (23.10.2026): remote kolmessa tilassa, yksi kerrallaan.**
  - SOITA / LISÄÄ / SÄÄDÄ; vain yksi paneeli näkyvissä.
  - LISÄÄ: YouTube (+ GP5-linkki/-tiedosto) → `/api/jobs` tai
    `/api/tabs/import`; työn seuranta 1,5 s, kirjasto päivittyy.
  - SÄÄDÄ: nimi, viritys, lukitus, arkistointi (`/library`).
  - Ei päällekkäisyyttä: palvelin 409 job-pyyntöihin soiton aikana ja
    PLAY-komentoon jobin aikana; UI näyttää saman.
  - 6 uutta testiä → **186 testiä**.
- **v1.88 (23.10.2026): varoitus, kun TV-näkymä puuttuu.**
  - `/remote` näyttää punaisen rivin `TV-näkymä ei ole auki…`, kun
    `tv_online: false`; PLAY pysyy käytössä mutta syy näkyy.
  - `start.bat` muistuttaa: pidä `/` auki ja avaa `/remote` toiseen
    välilehteen. 1 uusi testi.
- **v1.87 (23.10.2026): PAUSE-tila punaisella.**
  - Sama PLAY/PAUSE-nappi saa `.is-playing`-luokan, kun TV soittaa;
    tausta `--error` (punainen), teksti tumma. Vain `remote.js` + CSS.
- **v1.86 (23.10.2026): PLAY pysyy käytettävissä.**
  - `remote.js` ei disabloi PLAYtä TV:n offline-tilassa; komento jonoutuu
    (TTL 60 s) ja toteutuu kun TV-sivu on näkyvissä. Teksti:
    `TV: Offline · avaa TV-näkymä`.
  - `TV_ONLINE_S` 10 → **30 s** (taustavälilehden ajastinpihtaus).
- **v1.85 (23.10.2026): QR-palstan URL sopii QR:n leveyteen.**
  - `.remote-pair` = 150 px; `.remote-url` rivittyy samaan leveyteen →
    oikea reuna linjassa QR:n kanssa. Vain CSS.
- **v1.84 (23.10.2026): QR-SVG -korjaus.**
  - `/api/lan/qr.svg` kirjoitetaan standalone-SVG:nä (`segno.save(
    kind="svg")`) → `xmlns` mukana; ennen `svg_inline` jätti sen pois ja
    selain näytti rikkinäisen kuvan. Testi valvoo `xmlns`-määrettä.
- **v1.83 (23.10.2026): yksi käynnistin + QR `/remote`ssa.**
  - `start-lan.bat` **poistettu**; `start.bat` sitoo aina `0.0.0.0:8000`:aan
    ja tulostaa LAN-osoitteet (`scripts/lan_addresses.ps1`).
  - **150 × 150 px QR `/remote`-sivun oikeassa reunassa** + osoite
    `http://<LAN-IP>:8000/remote`; piilotettu alle 720 px näytöillä.
    QR encodaa aina LAN-IP:n (ei 127.0.0.1), DHCP saa vaihtua.
  - `/connect`-sivu poistettu (turha mutka); `GET /connect` → 404.
  - `app/remote.py`: komentojono + TV:n tila + valinnainen LAN-PIN
    (`TABTOOL_LAN_PIN`, HttpOnly-eväste, 10 yritystä/60 s); PINillä QR →
    `/lan?t=<istuntotoken>`.
  - `app/static/remote-bridge.js` pollaa komennot ja klikkaa olemassa
    olevia transport-nappeja → **app.js koskematon** (sääntö #1).
  - **188 pytest-testiä**.
- **v1.82 (23.10.2026): LAN-kaukosäädin.** `RemoteHub`, `/api/remote/*`,
  `/api/lan/info|qr.svg`, `/lan`-PIN, `/remote`-puhelinnäkymä, `segno`.
  (v1.83 yhdisti käynnistyksen ja siirsi QR:n `/remote`en.)
- **v1.75–v1.81 (22.10.2026, committoitu lokaalisti; ~14 h sessio):**
  - **v1.75** TEMPO-reitti lukee cp1252-GP5:n (`_gp5_song`, fallback) ja
    kirjoittaa UTF-8:na; SIIRTO-raja ±64 → **±999** (`SYNC_OFFSET_LIMIT`).
    Syy: Dr. Feelgoodin GP5 oli cp1252 (`Mötley Crüe` = 0xf6) → TALLENNA
    kaatui `'utf-8' codec can't decode byte 0xf6`.
  - **v1.76** `app/tab_edit.py` + `scripts/expand_repeat.py`: toisto
    kirjoitetaan tahdeiksi. Dr. Feelgood bar 2 ×2 → **17 tahdia**
    (122 → 138, 2615 nuottia). Toistomerkki ei toimi, koska kello seuraa
    kirjoitettua aikajanaa (score-end-guard katkaisisi).
  - **v1.77** `remove_bars` + `scripts/trim_bars.py`: audion musiikki
    päättyy 287,74 s mutta tabi jatkui 291,6 s → 2 viimeistä tahtia pois.
  - **v1.78** pickup-tahdin poisto säilyttää ajoituksen; Dr. Feelgoodin
    1/16-anacrusis (BAR 1, yksi avoin D) pois → **135 tahtia**, nuotit 2550,
    `ticksPerBar` 3840 (ennen 240 → SIIRTO oli 16× liian voimakas).
  - **v1.79** viritys luetaan kitararaidasta (`app.tuning.open_strings`),
    ei raidasta 0 (laulu); `backfill_tuning.py --force` korjasi
    Volbeat-tabit `Standard E` → **`Drop D · DADGBE`**.
  - **v1.80** `retune_tracks` + `scripts/retune_tab.py`: Drop D →
    **D Standard** sävelet säilyttäen (2529 nuottia, max nauha 13;
    BAR 7 `0/2`, BAR 9–10 `4/2 5/3 6/4`). Uusin Volbeat-tabi 116a1fa3…
    on nyt datassa D standard (override poistettu).
  - **v1.81** COUNT-IN ON/OFF -kytkin FULLSCREEN-napin alle
    (`.viewer-corner`, `#countin-toggle`, localStorage `tabtool:countIn`,
    oletus ON); luetaan vain `shouldRunCountIn`issa, soitoketju koskematon.
  - **188 pytest-testiä** (v1.81:ssä 152).
- **Kirjaston data 22.10.2026:** 12 tabia. Dr. Feelgood 135 tahtia /
  2550 nuottia (17 toistoa, SYNC/SIIRTO 0). Volbeat 2 tabia samasta
  biisistä eri audioilla: `7f30610c…` `Drop D · DADGBE` (SIIRTO −0,25),
  `116a1fa3…` **`D Standard · DGCFAD`**.
- **Aiemmat (v1.69–v1.74, `d76ddaf`):** score-end-guard (v1.69), lukitus
  read-only (v1.70), lukkoikoni (v1.71), sormitusprofiilit + versiot
  (v1.72), haamunuottien siivo (v1.73), GP5 UTF-8 (v1.74).
- **KISS – I Am a Legend Tonight:** AI-tabi (v3) jäi kohinaiseksi (kaksi
  kitaraa samassa stemissä). Löytyi oikea tekstibabi (Emil Ortenmark);
  soitetaan **standard E:ssä ilman capoa**. `scripts/build_kiss_legend.py`
  teki nuottiviite-GP5:n (2 raitaa Rhythm/Lead, 23 tahtia) → tuotu
  kirjastoon + audio liitetty. Täysi versio (tekniikat + osien järjestys)
  jäi TuxGuitarille/exportterin laajennukselle.
- **v1.66–v1.68 – tuonti, kanava ja viritys.** `app/bulk.py` +
  `scripts/import_folder.py` / `export_tabs.py` / `adb_pull_gp.ps1`
  (SHA-256-manifesti estää tuplat; export GP5/MusicXML/MIDI + `manifest.json`
  + ZIP). `meta.youtube_channel` näkyy `YT: <kanava>`; viritys →
  `tuning_label` + `tuning_notes`, manuaalinen ylikirjoitus NIMEÄ-lomakkeessa
  (`tuning_clear`). Backfillit `backfill_youtube_channel.py`,
  `backfill_tuning.py`.
- **v1.38–v1.65 – kirjasto ja ulkoasu.** `POST /api/tabs/{id}/library`
  (`title`/`locked`/`archived`/`tuning`), `NIMEÄ`-lomake, `ARKISTO (n)`,
  aakkosjärjestys, punainen `×`-poisto + varoitusdialogi (lukittu → 409;
  jaettu audio säilyy, MP3 jää arkistoon). Tabin marginaalit 30/30 px,
  `.transport` omaksi kortiksi, EXPORT tabikentän alle, modaali avautuu
  LIBRARY-napin korkeudelle, modaalin pino (cursor `1000`, modaali `2000`,
  dialogi `2100`).
- **v1.43–v1.56 – synkka ja count-in.** `backingTrackDuration` = partituurin
  kesto (`scoreEndTimeMs`), ei ääniraidan; klikkaus-seek kääntää
  SIIRTO/SYNC/BPM-korjauksen (`time > 0`); KOHDISTA + live-offset.
  Count-in 5 → 0 soittoketjun ulkopuolella (`handlePlayButton` portinvartija;
  kytkin ON/OFF v1.81). Palvelin käyttäjän hallintaan (v1.54).
- **Historia (v1.20–v1.42):** katselu, aikajana, tuonti/audio, BPM/Nopeus,
  SYNC/SIIRTO, ulkoinen arkisto, SEARCH-modaali (UI:ssa **LIBRARY**),
  GP5+YT yhdellä jobilla, GP3/GP4-konversio, poisto, pytest-yhteenveto.
  Yksityiskohdat `CHANGELOG.md`:ssä ja `README.md`:ssä.
- Katselu: **tab-only oletus**, Näkymä (`Tab`/`Auto`/`Tab+nuotit`/`Nuotit`),
  raitavalinnat ja tabikohtainen muisti, FULLSCREEN + automaattinen
  fullscreen PLAYssa (fullscreenissä LIBRARY piilotetaan, v1.62),
  cursor + edellinen rivi näkyvissä, dynamiikat piilossa,
  vaakascrollbar pois.
- Aikajana: aika/kesto, **tahtilukema**, ±5 s, Space/nuolet, seek
  vierittää tabin cursorin kohdalle.
- YouTube-metadata: title/artist yt-dlp:stä, `(Remastered)`-siivous;
  `YouTube audio` vain fallback. `audio_path` myös web-tabin metassa.
- Valmiin tabin tuonti: **GP5/MusicXML**, metat PyGuitarPro/music21,
  kirjastoon; tuodut tabit merkitään `Lähde: tuotu tabi`.
- **LIITÄ AUDIO**: samannimisen AI-tabin audio liitetään tuotuun tabiin;
  PLAY/aikajana/cursor tulevat käyttöön. Moniraitaisesta tuonnista
  oletuksena Guitar 1 + Guitar 2.
- **TAB BPM/Nopeus**: GP5-tempo korjattavissa, audio 100 %; Nopeus
  50–150 % harjoitteluun. AI-BPM on arvio, ei totuus.
- **SYNC** (v1.30): tabin kohdistus ±10 %/0,05 %, `+` eteen ja `-`
  taakse; tallentuu tabin `meta.json`iin (`sync_drift`) ja palautuu
  aina tabia avattaessa. GP5/audio eivät muutu. Syy: pitkässä
  GP5-tabissa heitto kertyy (esim. Seek & Destroy ~60–70 tahti).
- **TALLENNA** (v1.31, entinen ASETA): TAB BPM tallentuu vain napista;
  tallentamaton arvo värjää kentän, syötteen ja napin punaiseksi.
  Virheet (BPM 20–400, tallennusvirhe) punaisella; SYNC-virheet samoin.
- **"Not found" -muistutus:** uvicorn ei käytä `--reload`ia. Jos UI on
  uudempi kuin käynnissä oleva prosessi, `/tempo` ja `/sync` palauttavat
  404 → käynnistä palvelin uudelleen (`start.bat`).
- **Ulkoinen arkisto** (v1.32): YouTube-audio ja tuodut GP5/MusicXML
  mirroroidaan hakemistoon `D:\tabtool_files\audio` ja `\tabs`
  (`TABTOOL_EXTERNAL_DIR`), nimi `Artist - Title.ext`. Samalla levyllä
  hard link (ei tuplalevytilaa), muuten kopio. `data/` on edelleen
  totuuden lähde; pätkäklipit jätetään arkistoimatta.
- **Kirjasto tyhjänä?** Tarkista `TABTOOL_DATA_DIR` ja
  `TABTOOL_EXTERNAL_DIR`. Jos IDE:n perimä ympäristö osoittaa
  testihakemistoon (esim. vanha `tabtool_ui5` Tempissä), UI näyttää
  väärän kirjaston. Käynnistä palvelin ilman näitä muuttujia
  (`Remove-Item Env:TABTOOL_DATA_DIR`) → oletukset `data/` ja
  `D:\tabtool_files`. v1.41 korjasi myös sen, että levyltä luettu
  relatiivinen `meta.audio_path` säilyy tabilla.
- **MP3-kuunteluversiot** (v1.33): YouTube-latauksista syntyy
  `D:\tabtool_files\audio\mp3\<Artisti>\Artist - Title.mp3`
  (ffmpeg VBR ~190 kbps; vain jos WAV on uudempi). Pätkäklipit ja
  omat uploadit ohitetaan.
- **Seek-synkki** tutkittu: siirto sliderilla ei riko aikasynkkiä
  (tahtilukema osui 30→10→50→20→55→5 s kaikissa). `audio.seeking`
  estää välipositiot ja slider vapautetaan `pointerup`/`blur`illa.
- **Playback range -ansa** (v1.37): hiirellä raahaus loi alphaTabin
  loop-alueen (vihreä kehys), joka clampaa `mainSeek`in → tab näyttää
  väärää kohtaa ja Pause hyppää. Range nollataan nyt
  `playbackRangeChanged`issa, `scoreLoaded`issa ja ennen seekiä.
  Pause palauttaa sijainnin audion aikaan (60/150 ms).
- **Desimaali-TAB BPM** (v1.34): kenttä hyväksyy 0,1 askeleen
  (`143,55`). GP5 tallentaa kokonaisluvun (`int(bpm+0,5)`), desimaali
  toteutuu toiston korjauksena `bpm/score.tempo - 1`, joka summataan
  SYNC-arvoon. Ratkaisee "143 jää jälkeen / 144 edistää" -ongelman.
  Seek & Destroy -audion mitattu tempo **143,555 BPM** (librosa).
- **SIIRTO (tahtia)** (v1.35–v1.36): siirtää tabia tahdeilla
  (−64…+64, 0,25 tahdin askel = 1 isku), tallentuu
  `meta.sync_offset_bars`. Vakiosiirtoon (esim. 6 iskua = 1,5 tahtia)
  ja rakenne-eroon. Ei korvaa SYNCiä (prosentti) eikä BPM:ää.
- Referenssitabi: 258 tahtia, BPM 143,5 (GP5 144); AI-tabi 249
  tahtia, BPM 143,5547. BPM/SYNC/SIIRTO eivät pakota 144:ään.
- Täydet kappaleet ovat oletus; pätkägenerointi (`TEE TAB TÄSTÄ`) on
  poikkeus.
- Soittotapa/refinger (asemaprofiilit, helpoin-arvio, turhien nuottien
  karsinta, per-tahti-asema) on suunniteltu mutta **ei toteutettu**;
  jäissä. Koodi on committoitu (v1.41); vain lokaalit commitit,
  ei pushia.
- Spotify ei ole vielä mukana (Phase 3).

## Seuraava vaihe

0. **WASP uudelleen** (käyttäjä tekee itse): export GP5 vanhasta tabista,
   tuo se + `https://youtu.be/7COTI8k-rgo`, nimeä ja arkistoi vanha.
   Tarkista riviltä `YT: James Sly` ja viritys.
1. Päätä soittotapa/refinger-toteutus: asemaprofiilit, playability-score,
   turhien nuottien karsinta, per-tahti/fraasiasema.
2. Vasta sitten Phase 3 / Spotify: PKCE, haku/metadata, SDK/Connect,
   tokenit `oauth_tokens`-tauluun ja mockatut API-testit.
3. Remote-kaukosäädin on valmis (v1.82); jäljellä käyttäjän puhelintesti.


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

- `pytest -q` → **152 passed** (v1.81); `compileall` ja `node --check` OK.
- v1.75–v1.81: tässä sessiossa ajettu `pytest` (152), `compileall`,
  `node --check` ja HTML-tagien tasapaino; data-validoinnit tehty
  lukemalla GP5 takaisin (tahtimäärä, nuotit, soivat sävelet, toistot).
  **Soiton/tabin synkka odottaa käyttäjän kuuntelutestiä** (sääntö #1):
  count-in-kytkin ja uusi `.viewer-corner`-asettelu.
- v1.57–v1.62 headless (käyttäjän palvelin): tabin marginaalit
  30/30 px ja tabin reuna → scrollbar 15 px (1600/1366/1200/1024/800 px,
  ei sivuttaisvieritystä); LIBRARY/PLAY-kortti + FULLSCREEN oikeassa
  reunassa; modaalin yläreuna = LIBRARY-napin top (118 px); fullscreen
  piilottaa LIBRARYn; EXPORT 16 px tabikentän alapuolella.
- v1.63–v1.68: backend **114 passed** (nimeäminen, lukitus/poistoesto,
  arkisto, järjestys, migraatio, kanava, viritys, ylikirjoitus, bulk).
  UI-smoke: lista aakkosissa (myös samannimiset), NIMEÄ-lomake ja
  PERUUTUS toimivat; kanava/viritys renderöityivät oikein.
- **Backfillit ajettu (21.10.2026):** viritys 6 tabille (Dr. Feelgood
  `D Standard · DGCFAD`, WASP `Eb Standard · EbAbDbGbBbEb`, muut
  Standard E); kanavaa ei vielä asetettu (vain 2 smoke-tabia olisivat
  tarjonneet URLin). `smoke-youtube*`-tabien GP5 on rikki (testijäänteitä).
- v1.56 headless-Edge (CDP, käyttäjän palvelin): countdown 5→4→3→2→1→0
  ≈ 5,07 s, toisto 5,33 s; laskennan aikana `audio.currentTime` 0,846,
  `paused`, tahti 1 – kaikki muuttumattomia; layout 800/800; 2. PLAY
  peruu, seuraava aloittaa vitosesta; A/B audio 11,0 s → tahti 6
  molemmilla. Käyttäjän kuuntelutesti: **OK**.
- v1.31–v1.41 headless: TALLENNA/dirty-tila, backfill + hard link, seek
  30/10/50/20/55/5 s → 16/6/26/11/28/3, SYNC `+3.50 %` → `0.035`,
  desimaali-BPM, SIIRTO, GP3/GP4 → GP5 (0 nuottieroa), SEARCH-mod +
  poisto, GP5+YT. Tempot 143,55 / 161,5 / 143,55 / 112,35 / 136,0 BPM.
  Yksityiskohdat `CHANGELOG.md`:ssä.
- Palvelin on käyttäjän CMD-ikkunassa; v1.56 mitattiin käyttäjän
  käynnissä olevaa palvelinta vasten headless-CDP:llä.
- v1.49–v1.53 headless: tumma render, LIBRARY ilman otsikkoa, count-in
  4→0 (v1.49–v1.52) ja sen poisto (v1.53); lataus t = 1,268 s, 10 s →
  tahti 7 (SIIRTO −0,75), layout 1600/1600 px.
- Referenssitabi: 258 tahtia, BPM 143,5 (GP5 144); AI-tabi 249 tahtia,
  BPM 143,5547. Audio 414,72 s, PLAY + aikajana + cursor; 5 raitaa.
- GP5/MusicXML-tuonti ja `LIITÄ AUDIO` validoitu headless-selaimessa.
- Seek & Destroy -audion mitattu tempo 143,555 BPM; desimaali-BPM ja
  SIIRTO käytössä. Referenssitabissa ~9 tahtia enemmän kuin
  levytyksessä → rakenne-ero vaatii GP5-korjauksen tai SIIRTOn.

## Avoimet / myöhemmin

- **Pickup-varotin soittokelloon (vaatii luvan, sääntö #1):**
  `barDurationMs()` ja `ticksPerBar()` ottavat tahdin pituuden **kahdesta
  ensimmäisestä tahdista** (`bars[1] − bars[0]`). Anacrusis-tabissa SIIRTO
  ja KOHDISTA ovat 8×/16× liian voimakkaita (Dr. Feelgood ennen v1.78:aa).
  Data korjataan `scripts/trim_bars.py --bars 1`llä; koodikorjaus vaatii
  luvan, koko regressiochecklistin ja käyttäjän kuuntelutestin.
- **W.A.S.P.:** kirjastossa `8e8dfa0f…` *Animal (Fuck Like A Beast)*,
  `Eb Standard · EbAbDbGbBbEb`; vanhaa väärää `bc5a287d…` ei ole enää
  kannassa. Uusi tuonti kanavalta James Sly (`https://youtu.be/7COTI8k-rgo`)
  vain jos viritys/rakenne kaipaa korjausta – Songsterr näyttää samalle
  kappaleelle D standardia, ero on tab-datassa, ei synkassa.
- **Dr. Feelgood – valmis (v1.76–v1.78):** bar 2 soitetaan 17 kertaa
  kirjoitettuina tahteina (135 tahtia), 2 ylimääräistä lopputahtia ja
  1/16-pickup poistettu. Erillistä `set_repeat.py`tä ei tarvita.
- **Session tilanne 24.10.2026:** v1.93–v2.04 valmiit (remote-UI, nopeus,
  seek-slider, `start.bat`, GP3-grace, kirjastot bändin nimellä, Settings,
  puhelimen soitinvalinnat, kirjaston Tiedot + lähdemeta, versiovalinnan
  varmistus + palautus). Lisäksi data-työnä Reino Nordin -tabin sanoitus
  omalla Vocals-raidalla + lukittu sanakopio. 244 testiä vihreänä. **Soitto
  kuitattu valmiiksi (99 %, riittää) → ISO LUKKO; tagi `v1.99` = viimeisin
  pushattu palautuspiste, v2.00–v2.04 paikallisia.**
  Seuraava: käyttäjän UI-/kuuntelutesti (rule 07) / pickup-korjaus.
- Soittotapa/refinger: asemaprofiilit, helpoin-arvio, turhien nuottien
  karsinta, per-tahti/fraasiasema; **ei koodia vielä**.
- AI-transkription tarkkuus (Basic Pitch); referenssitabit ja ilmainen
  TuxGuitar apuna, ei Guitar Pro -pakkoa.
- KISSin kaltaiset kappaleet ilman valmista tabia: AI-tabi + korjaus.
- Referenssitabin rakenne vs. audio (258 vs. 249 tahtia). SYNC korjaa
  vain lineaarisen heiton; ylimääräinen/puuttuva tahti vaatii GP5-korjauksen.
- Spotify Phase 3, retention, bass/laulu,
  rummut (ADTOF/Omnizart), manuaalinen editori.
- **LAN-kaukosäädin (v1.82–v1.90) – käyttäjän testi:** `start.bat`,
  `/remote` (150 px QR), `/lan` PIN, kolme tilaa (SOITA/LISÄÄ/SÄÄDÄ).
  Cline ei julista kaukosäätöä toimivaksi ilman käyttäjän puhelintestiä
  (sääntö #1:n ihmisvalidointi).
- **Tablatuurisynkan hienosäätö – RATKAISTU v1.92, ISO LUKKO.** v1.91:n
  monotoninen syöttö jäi voimaan; varsinainen tahdit 1–41 -heitto oli
  count-inin viivästys, joka korjattiin v1.92:ssa. Soitto on käyttäjän
  kuittaama 99 %; ei enää avoin ongelma.
- **Seek & Destroy todistettu (19.10.):** toisto osuu 1:1 ainakin tahtiin
  149 asti asetuksilla **SIIRTO −0,75 / BPM 142**. GP5-datan korjaus ei
  ole prioriteetti: tabi on ohjelman lukemaa syötettä ja dataa korjataan
  vasta kun ohjelma on valmis. `SIIRTO alkaen tahdista X`
  (breakpoint-offset) jää myöhemmäksi.

## Uuden session aloitus

**Sano Cline:lle: `lue membank`.** Protokolla on `.clinerules/00-memory-bank.md`:ssä:
lue tämä kansio + säännöt, tarkista git/pytest ja jatka seuraavasta vaiheesta.
`docs/` ja `data/` ovat yksityisiä eivätkä kuulu gitiin.
