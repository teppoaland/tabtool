# 🔒 SÄÄNTÖ #1 – Soitto ja tablatuurin kohdistus ovat koskemattomia

> Tämä on projektin tärkein sääntö. Se on tarkoituksella eksplisiittinen,
> koska rikkomus näkyy vasta minuuttien kuluttua: kursori ja ääni erkanevat
> hiljalleen eikä syy löydy enää siitä muutoksesta, joka sen aiheutti.

## 🔒 ISO LUKKO – soitto on valmis ja jäädytetty (23.10.2026)

- Käyttäjä on kuitannut: **kaikki soittoviat on korjattu** ja soitto toimii
  **99 % tarkkuudella** oikein, mikä **riittää** käyttäjälle. Tila on
  hyväksytty lopulliseksi, ei enää "odottaa kuuntelutestiä".
- **Soittoon vaikuttaviin koodeihin EI KOSKETA.** Tämä koskee kaikkea,
  mikä voi vaikuttaa äänen ja kursorin kohdistukseen, kellotukseen,
  seekiin, count-iniin, alphaTab-kytkentöihin tai transportin DOM-rakenteeseen.
- **Jos jokin koodi, jolla on pienikin mahdollisuus sotkea soittoa, on
  pakko muuttaa:** se tehdään **varoen**, pienimmällä mahdollisella diffillä,
  ja käyttäjää **pyydetään testaamaan soitto referenssikappaleella**
  (Seek & Destroy, SIIRTO −0,75 / BPM 142) ennen ja jälkeen. Muutos
  hyväksytään vasta käyttäjän kuuntelutestillä.
- **Nopeus ≠ kohdistus:** `setPlaybackRate` / `audio.playbackRate` on
  harjoittelunopeus. Se skaalaa äänen ja kursorin yhdessä, koska
  `syncTimeMs()` lukee `audio.currentTime`ia; `playbackRate` ei esiinny
  kellotuksessa, `bpmDrift`issä eikä `seekTo`-inversiossa. Nopeuden
  muutos (50–150 %) ei siis siirrä tabia audion suhteen. Silti se on
  lukittu pinta, koska se kirjoittaa audio-elementtiin.
  `tests/test_playback_guard.py` valvoo, ettei `playbackRate` päädy
  kohdistusmatematiikkaan.

## Miksi tämä on sääntö #1

Soitto ja tablatuurin osoittimen kohdistus (paikallinen audio ↔ alphaTabin
cursor) on **ainoa toiminto, joka on validoitu 1:1 oikeaa levyä vasten**:
Seek & Destroy asetuksilla **SIIRTO −0,75 / BPM 142**, toisto osuu tahtiin
149 asti. Kirjasto, tuonti, UI ja putki voidaan rikkoa ja korjata; tämän
rikkoutuminen tekee koko työkalusta hyödyttömän ja on vaikein diagnosoida.

Tabi on ohjelman lukemaa syötettä; **kohdistusmekaniikka on tuote**.

## Koskematon pinta – ei muutoksia ilman erillistä lupaa

### 1. `app/static/app.js` – soittoketju

Nämä funktiot ja kytkennät ovat lukittuja. Niiden kaavoja, ehtoja,
kutsujärjestystä ja sivuvaikutuksia ei muuteta:

- kellotus ja korjaukset: `notatedTempo`, `bpmDrift`, `barDurationMs`,
  `syncTimeMs`, `scoreEndTimeMs`, `ticksPerBar`, `SYNC_LIMIT`,
  `normalizeSyncDrift`, `setSyncDrift`, `setSyncOffsetBars`
- mittaus: `currentOffsetBars`, `updateOffsetReadout`
- media-adapteri: `mediaHandler` kokonaan – `backingTrackDuration`,
  `playbackRate` (getter/setter), `masterVolume`, `seekTo` (**inversio**),
  `play`, `pause`
- syöttö ja seek: `syncPosition`, `syncPositionSoon`,
  `clearPlaybackRange`, `seekTo`, `seekBy`, `setPlaybackRate`,
  `scrollScoreToCursor`, `applyScrollOffset`
- alphaTab-kytkennät `getAlphaTab`issa: `api.playerStateChanged`,
  `api.playbackRangeChanged`, `api.scoreLoaded` (mukaan lukien
  `output.handler = mediaHandler` ja `syncPositionSoon`),
  `display.enableAnimatedBeatCursor`, `display.enableCursor`,
  `scrollMode`, `scrollOffsetY`, `display.resources`-värit
- valmius: `togglePlayback`, `handleAlignClick`/`armAlign`/`disarmAlign`
- audion tapahtumat: `audio.addEventListener("play" | "pause" | "seeked" |
  "ended")` sekä `updateTransport`
- lataus: `loadTab`in audio- ja synkkaosat (`setAudioAvailable`,
  `audio.src`, `audio.load`, `setPlaybackRate(1)`, tallennettujen
  `meta.sync_drift` / `meta.sync_offset_bars` palautus)

### 2. `app/static/index.html` – transportin rakenne

Näiden elementtien olemassaolo, `id`, `type`, `min/max/step` ja
tapahtumakytkennät ovat lukittuja: `#play-button`, `#seek-back`,
`#seek-forward`, `#seek-slider`, `#time-current`, `#time-total`,
`#bar-readout`, `#sync-offset-readout`, `#section-button`,
`#rate-slider`, `#rate-readout`, `#sync-slider`, `#sync-readout`,
`#shift-input`, `#bpm-input`, `#bpm-button`, `#alphaTab`,
`#audio`. Myös `#viewer-section`-rakennetta ja `.transport`-palkkia
koskee sama raja.

- **v1.96 (käyttäjän pyyntö):** `#rate-slider` on `min="0.5" max="1.5"
  step="0.01"` ja sen `input`-käsittelijä snapittaa 95–105 % → 100 %
  (10 %:n ikkuna). Sama ikkuna on `/remote`-sivun nopeussäätimessä.
  Muut lukitut `min/max/step`-arvot ja kytkennät ovat ennallaan;
  `setPlaybackRate` itse ei muuttunut.

### 3. `app/static/style.css` – mitat ja pino

- `.alphatab` ja `.viewer-stage`: `min-width: 0`, `width/max-width: 100 %`
  (v1.50: ilman tätä canvas kasvattaa sivun ~7000 px:iin)
- `.viewer-section` `isolation: isolate`, `.at-cursors` `z-index: 1000`,
  modaalin `2000` / dialogin `2100`, cursor piiloon `body.modal-open`
- `.transport`-, `.seek-slider`-, `.sync-offset-readout`-mitoitus ja
  `#alphaTab`-korkeus/scroll-alue

Sallittua: väri, fontti ja varjostus, **jos** ne eivät muuta näiden
konttien mittoja, `overflow`- tai `scroll`-käyttäytymistä.

### 4. Backend ja data

- reitit: `POST /api/tabs/{id}/sync`, `/tempo`, `/section`,
  `/attach-audio`; `GET /api/tabs/{id}/audio` (Range → 206)
- tallennus: `db.update_tab_sync`, `meta.sync_drift`,
  `meta.sync_offset_bars`, `meta.gp5_tempo`, `meta.tempo_override`
- testit: `tests/test_tab_sync.py`, `test_tab_tempo.py`,
  `test_tab_section.py`, `test_tab_audio.py`, `test_tab_import.py`
  (GP5-tempo). Testejä saa **lisätä**, ei heikentää eikä poistaa.

## Sallittua ilman lupaa

- uusi ominaisuus, joka lisätään ytimen **ulkopuolelle**: uusi paneeli,
  reitti, moduuli tai tiedosto, joka ei muuta yllä lueteltuja rivejä,
  niiden syötteitä, DOM-id:itä eikä CSS-mittoja
- tekstin ja värin muutos, joka ei vaikuta mittoihin
- bugikorjaus, joka ei kosketa koskematonta pintaa
- dokumentaatio, sääntöteksti ja uudet testit
- uuden vaiheen suunnittelu (Phase 3 Spotify, Phase 4 remote), kunhan
  soittoketjuun ei kosketa

## Menettely, jos ytimeen on pakko koskea

1. **Kysy lupa** ja kerro, miksi muutos ei onnistu ytimen ulkopuolella.
2. **Yksi muutos kerrallaan**: ei refaktorointia, uudelleennimeämistä eikä
   "selkeyttämistä" samalla kertaa.
3. Aja testit **ja** alla oleva regressiochecklist. Jos jokin arvo poikkeaa,
   palauta muutos ennen kuin jatkat.
4. Raportoi ennen/jälkeen -mittaukset ja versionumero.

## Regressiochecklist (pakollinen jokaisesta ydinmuutoksesta)

Lukitut vertailuarvot (Seek & Destroy -kalibrointi, v1.52–v1.54):

- lataus: `audio.currentTime ≈ 1,268 s` (ei 0) kun SIIRTO −0,75 / BPM 142
- 10 s toiston jälkeen tahti **7** = odotettu
- seek 30 / 10 / 50 / 20 / 55 / 5 s → tahdit **16 / 6 / 26 / 11 / 28 / 3**
- `time === 0` ei koskaan käänny inversiolla (rewind/stop jää ennalleen)
- PLAY alkaa heti (ei countdownia); PAUSE palauttaa cursorin audion aikaan
- raahaus ei jätä `playbackRange`ia päälle (ei looppia eikä clampia)
- `document.scrollWidth === document.clientWidth` (1600 px), ei
  sivuttaisvieritystä
- SYNC ±10 % / 0,05 %, SIIRTO 0,25 tahdin askel, desimaali-TAB BPM
  tallentuvat ja palautuvat tabia avattaessa
- `pytest -q` (v2.18: 275 passed), `compileall`, `node --check app.js` ja
  `remote.js` OK

## Ihmisvalidointi – kuuntelutesti on ainoa hyväksyntä

Automaatio ei kuule synkkaa. `pytest`, `compileall`, `node --check` ja
headless-ajo todentavat vain, että koodi latautuu ja arvot tallentuvat –
ne eivät todista, että kursori osuu musiikkiin. Siksi:

1. **Käyttäjä tekee kuuntelu-/tabsynkkitestin itse.** Cline ei koskaan
   sano synkkaa korjatuksi, valmiiksi eikä "pitäisi toimia" ilman
   käyttäjän kuittausta.
2. **Palvelin on käyttäjän CMD-ikkunassa.** Käyttäjä ajaa `start.bat`in
   (se pysäyttää vanhan instanssin ja käynnistää uuden) ja tarkistaa
   UI:n. Cline ei käynnistä palvelinta taustalle, ei pysäytä sitä eikä
   kierrä tätä omalla instanssilla toisella portilla.
3. **Portti ennen seuraavaa työtä:** riskialttiin muutoksen jälkeen Cline
   pysähtyy, kertoo mitä muuttui ja antaa testiohjeen. Seuraavaa
   ominaisuutta ei aloiteta ennen kuin käyttäjä on kuitannut testin.
4. **Epäselvässä tilassa ei arvata:** jos vaikutusta ei voi todentaa,
   vastaus on "vaatii ihmisvalidoinnin", ei "pitäisi toimia".

### Testiohje käyttäjälle (Seek & Destroy -kalibrointi)

1. `start.bat` (pysäyttää ja käynnistää palvelimen; selaimessa Ctrl+F5).
2. Avaa kalibrointitabi; aseta **SIIRTO −0,75** ja **BPM 142**.
3. PLAY: ääni alkaa heti ja kursori osuu tahtiin; 10 s kohdalla tahti **7**.
4. Seek 30 / 10 / 50 / 20 / 55 / 5 s → tahdit 16 / 6 / 26 / 11 / 28 / 3.
5. PAUSE: kursori jää audion kohtaan (ei hyppää iskun alkuun).
6. Raahaa hiiri tabin yli: vihreää loop-aluetta ei jää päälle.
7. Kuittaa Cline:lle "OK" tai missä kohtaa heitto alkaa (tahti + suunta).

### Mikä laukaisee ihmisvalidoinnin (myös ytimen ulkopuolella)

- mikä tahansa muutos `app/static/app.js`, `index.html` tai `style.css`
  (myös väri, fontti ja layout)
- `loadTab`, score-formaatin valinta (`meta.files`), GP5/MusicXML-tuonti
  ja tempon luku
- `GET /api/tabs/{id}/audio` (Range → 206), `attach-audio`,
  `audio_only`-jobit ja tabin poisto
- alphaTab-vendorin päivitys, `?v=`-leimat ja välimuistiin vaikuttavat
  muutokset
- `db.update_tab_sync`, `meta.sync_*`, `meta.gp5_tempo`

## Työtapa, joka estää synkan hajoamisen uudelleen

1. **Yksi riskimuutos kerrallaan**: oma commit ja oma validointi. Ei
   kahta soittoon vaikuttavaa muutosta samaan committiin.
2. **Pienin mahdollinen diff.** Ei siivousta, uudelleennimeämistä eikä
   refaktorointia samalla kierroksella.
3. **Jos synkka hajoaa: palauta ensin, korjaa sitten.** `git revert`
   viimeisin koodicommit ja varmista toiminta ennen uutta yritystä – älä
   korjaa arvaamalla rikkinäisen päälle.
4. **Visuaaliset työt erikseen** omiin committeihin, jotta soittoketjun
   regressio ei peity CSS-muutoksen alle.
5. Ydintä koskeva muutos on oma tehtävänsä ja oma lupansa – ei "samaan
   hintaan" muun työn kanssa.

## Count-in (v1.55) – sallittu vain tässä muodossa

Count-in on sallittu, koska se ei kosketa soittoketjua:

- overlay (`#play-countdown`) on `position: fixed` -lapsi
  `#viewer-section`issä; **ei wrapperia** `#alphaTab`in ympärille eikä
  muutoksia `.viewer-section`in grid/flex-mittoihin
- laskenta tekee vain DOM-muutoksia: ei `api.*`-kutsuja, ei
  `audio.play`/`audio.pause`, ei muita `audio.currentTime`-kirjoituksia kuin
  **v1.92:n palautus**: `handlePlayButton` tallentaa audion paikan lähdön
  hetkellä (`countInAudioTime`) ja `finishCountIn` palauttaa sen ennen
  `togglePlayback()`ia, koska fullscreen-resize voi siirtää audion pois
  aloituspaikalta laskennan aikana. Tämä on paluu jo luettuun arvoon
  (no-op, jos audio ei liikkunut) – ei kellotuksen muutos.
- toisto käynnistetään lopussa **muuttumattomalla** `togglePlayback()`illa
  täsmälleen kerran
- fullscreen pyydetään PLAY-käsittelijässä heti (käyttäjän ele), ei
  laskennan lopussa
- `togglePlayback`, `mediaHandler`, `seekTo` ja `syncTimeMs`-ketju eivät
  saa sisältää count-in-koodia; `tests/test_playback_guard.py` valvoo
- ON/OFF-kytkin (v1.81) on sallittu: `#countin-toggle` luetaan **vain**
  `shouldRunCountIn()`issa. Se ei muuta askelmäärää, kestoa eikä ääntä,
  eikä kytkentä saa näkyä soitofunktioissa (guard-testi valvoo)
- askelmäärän, keston tai äänen muutos vaatii luvan ja koko
  regressiochecklistin

## Kielletyt ilman lupaa

- kellotuksen, offsetin tai count-inin uudelleensuunnittelu
- `backingTrackDuration` → ääniraidan kesto (v1.43–v1.45-regressio)
- seek-inversion rajaaminen pelkkiin osoitinklikkauksiin
  (v1.51-regressio: aloitus 1,268 s → 0)
- `playbackRange`in salliminen tai `clearPlaybackRange`in poisto
- kursoria koskevan CSS:n tai layoutin muutos osana visuaalista työtä
- soittoketjun refaktorointi "osana muuta työtä"

## Linnake (arkkitehtuurilinjaus)

Nykyinen raja on **looginen** (tämä sääntö + regressiochecklist), ei
fyysinen. Mahdollinen tuleva eriytys, **vain erillisellä luvalla**:

- siirrä **puhdas matematiikka** (`bpmDrift`, `barDurationMs`,
  `scoreEndTimeMs`, `syncTimeMs` ja sen inversio) omaan
  `app/static/playback-core.js`:ään ja lukitse kaavat Node 22:n
  `node --test` -golden-testeillä (ei npm-riippuvuuksia)
- **kytkennät jäävät** `app.js`:ään: `output.handler`, `seekTo`-inversio,
  `playerStateChanged`/`playbackRangeChanged`/`scoreLoaded`, audio-eventit.
  Ne ovat historiallisesti rikkoneet synkan, eivät kaavat.
- eriytys vaatii aina koko regressiochecklistin ja versionumeron noston;
  sitä ei tehdä osana muuta työtä.
