# 🔒 SÄÄNTÖ #1 – Soitto ja tablatuurin kohdistus ovat koskemattomia

> Tämä on projektin tärkein sääntö. Se on tarkoituksella eksplisiittinen,
> koska rikkomus näkyy vasta minuuttien kuluttua: kursori ja ääni erkanevat
> hiljalleen eikä syy löydy enää siitä muutoksesta, joka sen aiheutti.

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
- `pytest -q` (93 passed), `compileall`, `node --check app.js` ja
  `remote.js` OK

## Ihmisvalidointi – kuuntelutesti on ainoa hyväksyntä

Automaatio ei kuule synkkaa. `pytest`, `compileall`, `node --check` ja
headless-ajo todentavat vain, että koodi latautuu ja arvot tallentuvat –
ne eivät todista, että kursori osuu musiikkiin. Siksi:

1. **Käyttäjä tekee kuuntelu-/tabsynkkitestin itse.** Cline ei koskaan
   sano synkkaa korjatuksi, valmiiksi eikä "pitäisi toimia" ilman
   käyttäjän kuittausta.
2. **Palvelin on käyttäjän CMD-ikkunassa.** Käyttäjä ajaa `stop.bat` /
   `start.bat`in ja tarkistaa UI:n. Cline ei käynnistä palvelinta
   taustalle, ei pysäytä sitä eikä kierrä tätä omalla instanssilla
   toisella portilla.
3. **Portti ennen seuraavaa työtä:** riskialttiin muutoksen jälkeen Cline
   pysähtyy, kertoo mitä muuttui ja antaa testiohjeen. Seuraavaa
   ominaisuutta ei aloiteta ennen kuin käyttäjä on kuitannut testin.
4. **Epäselvässä tilassa ei arvata:** jos vaikutusta ei voi todentaa,
   vastaus on "vaatii ihmisvalidoinnin", ei "pitäisi toimia".

### Testiohje käyttäjälle (Seek & Destroy -kalibrointi)

1. `stop.bat` → `start.bat` (uusi koodi latautuu; selaimessa Ctrl+F5).
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
