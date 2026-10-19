# 📜 CHANGELOG – AI TABTOOL

> AI TabTool käyttää `1.x`-versiosarjaa. Aloitus `v1.00`.

## v1.51 – 19.10.2026

- **Count-in vain kerran kappaleen alussa.** `countInDone` asetetaan
  ensimmäisen toiston `play`-tapahtumassa ja nollataan `loadTab`issa.
  Tauon jälkeen jatkaminen alkaa heti ilman laskentaa.
- **Count-in on nyt täysin erillinen soitosta.** Se ei enää muuta
  PLAY/PAUSE-napin tilaa eikä kutsu alphaTabia tai audiota ennen kuin
  laskenta päättyy; `audio.currentTime` ja kursori pysyvät paikallaan
  (t = 0, Tahti 1). Toinen PLAY-painallus peruu laskennan.
- **Korjaus: SIIRTO ei enää siirrä audiota latauksessa.** alphaTab kutsuu
  latauksessa `seekTo(~0,44 ms)`, ja vanha `time > 0` -ehto käänsi sen
  SIIRTO-arvolla 1,268 sekunniksi. Nyt inversio tehdään vain oikealle
  osoitinklikkaukselle (600 ms ikkuna `pointerdown`/`mousedown`ista),
  joten engine-seekit menevät läpi sellaisenaan ja toisto alkaa 0:sta.
- Validoitu headless-Edgellä: t = 0 latauksessa ja koko count-inin ajan,
  tauon jälkeen resume ilman laskentaa, klikkaus-seek osuu tahtiin 3.
- 93 pytest-testiä.

## v1.50 – 19.10.2026

- **Korjaus: tabinäkymä levisi oikealle aloitusnäkymässä.** v1.49:n
  `.viewer-stage`-kääre (count-in-overlayn ankkuri) otti leveytensä
  alphaTabin canvasin sisältöleveydestä, joten grid-rata kasvoi noin
  7000 px:iin ja koko sivu vierittyi oikealle. `min-width: 0` kääreelle
  ja `.alphatab`ille sekä `width/max-width: 100 %` rajaavat näkymän.
  Testattu 1366/1600/2560 px: `scrollWidth == clientWidth`.
- Ei muita muutoksia; 93 pytest-testiä.

## v1.49 – 19.10.2026

- **Tumma tabinäkymä oletuksena.** alphaTabin värit asetettiin
  `display.resources`-asetuksilla vaaleiksi (`mainGlyphColor`,
  `secondaryGlyphColor`, `staffLineColor`, `barSeparatorColor`,
  `barNumberColor`, `scoreInfoColor`) ja `.alphatab`-tausta tummaksi
  (`#0d1117`). Suurella näytöllä tabi ei enää väläytä valkoisena.
- **SEARCH-napit → LIBRARY.** Yläpalkin ja etusivun nappi avaavat saman
  ikkunan; modaalista poistettiin iso `SEARCH`-otsikko (jäljellä
  `LIBRARY · GENERAATTORI`) ja `aria-label` korvaa poistetun otsikon.
- **Count-in 5 → 0.** PLAY näyttää viiden sekunnin laskennan tabin päällä
  ennen kuin toisto alkaa; toinen PLAY-painallus peruu laskennan.
  Kesto on `COUNTDOWN_SECONDS` (`app/static/app.js`), kunnes
  Settings-näkymä tehdään.
- Ei backend-muutoksia; 93 pytest-testiä.

## v1.48 – 19.10.2026

- **Korjaus: klikkaus-seek kohdistaa nyt oikein.** `mediaHandler.seekTo`
  käänsi aiemmin SIIRTO/SYNC/BPM-korjauksen vain osittain, joten klikatun
  tahdin sijaan valittiin edellinen (esim. klikkaa 183 → valitsee 182).
  Nyt `syncTimeMs()` käännetään klikkaus-seekeissä (`time > 0`), mutta
  nollaus/pysäytys (`time === 0`) jätetään ennalleen, joten toisto ei
  muuttunut. Ei backend-muutoksia; 93 pytest-testiä.

## v1.47 – 18.10.2026

- **Korjaus: osoitin "juoksi" edellä toiston aikana (renderöinti).** alphaTabin
  `enableAnimatedBeatCursor` ekstrapoloi kursorin CSS-siirtymällä seuraavan
  iskun yli (`ToNextBext` → kerroin 2), joten toiston aikana näkymä eteni
  ääntä edellä ja pysäytyksessä palasi tarkkaan paikkaan. Animoitu kursori
  otettiin pois käytöstä: nyt kursori hyppää suoraan oikeaan
  `tickPosition`iin joka 50 ms -päivityksellä.
- Ei backend-muutoksia; 93 pytest-testiä.

## v1.46 – 18.10.2026

- **Kohdistusavustin (pyynnöstä):**
  - **Live-offset-näyttö** kuljetuspalkissa näyttää osoittimen eron
    ääneen (`Osoitin +0,50 tahtia edellä` / `−0,50 tahtia jäljessä` /
    `Kohdallaan`), laskettuna `api.tickPosition` vs.
    `audio.currentTime × BPM × 960 / 60000`.
  - **KOHDISTA-nappi**: pysäytä toisto ja klikkaa tabista sitä nuottia,
    jonka pitäisi soida nyt. Appi laskee eron `beat.absolutePlaybackStart`
    vs. nykyinen `tickPosition` ja tallentaa sen SIIRTO-arvoksi
    (`/api/tabs/{id}/sync`). Klikkauksen aikana alphaTabin oma
    click-to-seek on väliaikaisesti pois päältä.
- Ei backend-muutoksia; 93 pytest-testiä.

## v1.45 – 18.10.2026

- **Korjaus: partituurin kesto lasketaan master bar -tikeistä.** Aiempi
  korjaus käytti `api.endTime`ä, joka on alphaTabin *live* `currentPosition`
  ja on 0 ennen ensimmäistä toistotikkia — siksi `backingTrackDuration`
  putosi takaisin ääniraidan kestoon ja alphaTabin venytys jäi voimaan.
  Nyt kesto = `(viimeisen tahdin start + kesto) × 60000 / (tempo × 960)`,
  joka on oikea heti ensimmäisestä kursoritikistä. Seek & Destroy
  (258 tahtia, tempo 144) → 430 000 ms.
- Ei backend-muutoksia; 93 pytest-testiä.

## v1.44 – 18.10.2026

- `scoreEndTimeMs()` käyttää suoraan `api.endTime`ä (sekvensserin
  `currentEndTime`, sama arvo kuin alphaTabin backing track -kaavassa).
  Aiempi `api.tickCache.endTime`-haara poistettiin, koska tick lookup
  -objektilla ei ole `endTime`-kenttää. Toiminta ei muuttunut; korjaus
  on täysin selainpuolinen, joten se aktivoituu kovalla uudelleenlatauksella
  (Ctrl+F5) myös ilman palvelimen uudelleenkäynnistystä.

## v1.43 – 18.10.2026

- **Korjaus: osoitin kulki ääntä edellä (kursorin synkka).** alphaTabin
  ulkoisen median kello venyttää backing trackin ajan koko partituurin
  pituuteen suhteella `partituurin kesto / backingTrackDuration`.
  `backingTrackDuration` palautti ääniraidan keston, joten kun tabi on
  pidempi kuin audio (esim. Seek & Destroy -referenssi: 258 tahtia vs.
  ~249 tahtia), jokainen `audio.currentTime`-syöte skaalattiin ylöspäin ja
  kursori meni musiikin edelle. Nyt `backingTrackDuration` palauttaa
  partituurin keston (`api.tickCache.endTime`), jolloin kellotus on 1:1 ja
  vain TAB BPM / SYNC / SIIRTO -korjaukset vaikuttavat. Tab BPM 143,5
  (GP5 144) kohdistaa tahdin 41 viimeisen nuotin oikein.
- Ei muutoksia backendiin; 93 pytest-testiä.

## v1.42 – 18.10.2026

- **Testiajon yhteenveto näkyviin:** `pytest.ini`:stä poistettiin
  `addopts = -q`. Ohjeen `pytest -q` oli aiemmin käytännössä `-qq`,
  joten pytest tulosti vain pisteet eikä lainkaan riviä `93 passed`.
  Nyt `pytest -q` (ja `test.bat`) näyttää aina testien määrän.
- **Sessioalustuksen tulosteet kapeaan konsoliin:** memory bank
  -protokollan tarkistuskomennot putkitetaan `Out-String -Width 200`
  -muotoon. PowerShell muotoilee monirivisen tulosteen konsolin
  leveyden mukaan; kapeassa kuoressa rivit hajosivat ja VS Code
  shell integration saattoi pudottaa tulosteen kokonaan.
- Ei muutoksia sovelluksen toimintaan; 93 pytest-testiä.

## v1.41 – 18.10.2026

- **GP3/GP4-tuki tuonnille:** `POST /api/tabs/import` ja
  `POST /api/tabs/import-url` hyväksyvät nyt `.gp3`, `.gp4` ja `.gp5`.
  PyGuitarPro lukee tiedoston ja vanha versio kirjoitetaan aidoksi
  GP5:ksi (`tab.gp5`), jotta alphaTab ja GP5-export toimivat
  yhdenmukaisesti. Konversio ei muuta nuotteja (testattu GP4 → GP5:
  samat tahdit, notet ja tempo).
- **Korjaus: levyltä uudelleenrekisteröity tabi menetti audionsa.**
  `db.import_tabs_from_disk` resolvoi `meta.audio_path`-arvon
  työhakemistosta, vaikka jobit tallentavat sen suhteessa `data/`-juureen.
  Nyt relatiivinen polku resolvoidaan `DATA_DIR`-juuresta, joten
  `audio/…wav` säilyy tabilla myös kannan uudelleenluennassa.
- SEARCH-modaalin tiedostovalitsin hyväksyy `.gp3/.gp4/.gp5` ja
  virhetekstit puhuvat GP-tiedostosta; GP5-säilyy tallennusformaattina.
- 93 pytest-testiä (uudet: GP4-tuonti konvertoituu GP5:ksi,
  relatiivinen audio_path säilyy rescanissa).

## v1.40 – 18.10.2026

- **Yksi toiminto kaikille GP5-lähteille:** SEARCH-modaalissa on nyt
  `GP5-linkki (valinnainen)` ja `tai GP5-tiedosto`. Molemmat käyttävät
  samaa GENERATE TAB -toimintoa, joten paikallinen GP5/MusicXML-tiedosto
  + YouTube-linkki onnistuu yhdellä painalluksella.
- `POST /api/tabs/import` hyväksyy nyt `youtube_url`- ja
  `options`-kentät: ilman YouTube-linkkiä vastaus on tab-yhteenveto,
  linkin kanssa vastaus on audio-job, joka liittää audion tuotuun
  tabiin valmistuttuaan. Sama `_queue_audio_job`-polku kuin
  GP5-linkilla.
- Erillinen `IMPORT TAB` -rivi poistettu modaalista; GP5/MusicXML-tuonti
  tapahtuu samasta lomakkeesta. GP5-linkki ja GP5-tiedosto ovat
  vaihtoehtoisia (ei molempia), eikä GP5-lähteen kanssa voi käyttää
  omaa audiotiedostoa – audio tulee YouTube-linkistä.
- 91 pytest-testiä (uudet: GP5-tiedosto + YT liittää audion,
  ei-YouTube-URL hylätään). Headless-selaimessa validoitu koko
  kombinaatio: tiedosto + YT → tabi tuotu, audio liitetty, modaali
  sulkeutui, viewer avautui.

## v1.39 – 18.10.2026

- **Korjaus: alphaTabin cursor näkyi SEARCH-modaalin päällä.** alphaTab
  antaa cursor-kontilleen `z-index: 1000`, joten vihreä
  valinta-/cursor-kehys piirtyi modaalin yli (modaali oli `60`).
  Modaalin pino nostettiin (`2000`, varoitusdialogi `2100`),
  `.viewer-section` eristettiin omaksi pinoksi (`isolation: isolate`)
  ja cursor-elementit piilotetaan modaalin ollessa auki
  (`body.modal-open .at-cursors`).
- Modaalin tausta muutettiin täysin peittäväksi, jotta taustan sisältö
  ei näy läpi.
- Ei toiminnallisia backend-muutoksia; 89 testiä ennallaan.

## v1.38 – 18.10.2026

- **SEARCH-modaali:** kappaleen haku, GP5-tuonti, kirjasto ja kappaleen
  valinta ovat nyt omassa tilavassa ikkunassaan. TV-näkymä jää soittoa
  varten; `SEARCH` avaa modaalin yläpalkista ja etusivulta, `SULJE`/Esc
  sulkee sen.
- **YouTube + GP5-linkki:** jos GP5-linkki annetaan, tablatuuria ei
  generoida AI:lla. Palvelin hakee GP5/MusicXML-tiedoston suoraan
  linkistä (`app/tab_download.py`), importtaa sen ja liittää
  YouTube-audiosta ladatun audion tabiin. Ilman GP5-linkkiä toiminta on
  ennallaan (AI-generointi).
- **gprotab.net:** tavallinen tabisivu palauttaa HTML:n; lataus osaa
  retryttää `?download`-parametrilla. Vain julkiset http(s)-osoitteet
  sallitaan (ei localhost/yksityisverkko), koko enintään 20 MB.
- **MP3-valinta:** `MP3-kuunteluversio` on oletuksena päällä ja
  tallentaa YouTube-audiosta MP3:n `D:\tabtool_files\audio\mp3\`-
  hakemistoon. Valinta ei vaikuta tabin cache-avaimeen.
- **Kappaleen poisto:** kirjastoriviltä `POISTA` avaa
  varoitusdialogin. Poisto siirtää tabin, sen audion, stemmit sekä
  niihin liittyvät job/track-rivit pois; MP3-kuunteluversio jää
  hakemistoon. Jaettu audio säilyy, jos toinen tabi käyttää samaa
  tiedostoa.
- **Uudet reitit:** `POST /api/tabs/import-url`, `DELETE /api/tabs/{id}`;
  `POST /api/jobs` hyväksyy `gp5_url`-kentän. Audio-only-job (malli
  tallentuu `options`-kenttään) liittää audion tuotuun tabiin ilman
  transkriptiota.
- 89 pytest-testiä (uudet: download, delete, GP5+YT-job, optioiden
  erottelu). Headless-selaimessa validoitu modaalin avaus, kappaleen
  valinta, poistodialogi ja GP5-linkin tuonti (W.A.S.P. — Animal
  (Fuck Like A Beast), 111 tahtia, 3471 nuottia).

## v1.37 – 18.10.2026

- **Korjaus: vahingossa syntyvä playback range (loop).** alphaTab luo
  hiirellä raahaamalla `playbackRange`-alueen (vihreä kehys), joka
  rajaa `mainSeek`in. Silloin tab jämähtää/clampautuu väärään kohtaan
  (esim. "tab bar 85, soitto bar 84") ja Pause hyppää beat-alun
  mukaan. Range nollataan nyt heti: `playbackRangeChanged`-tapahtumassa,
  `scoreLoaded`issa ja ennen jokaista seekiä. Klikkaus siirtää edelleen,
  mutta raahaus ei jätä looppia.
- **Pause-palautus:** kun alphaTab pysäyttää ja snapsauttaa cursorin
  beat-alun mukaan, sijainti palautetaan audion aikaan
  (`playerStateChanged` 60 ms + audion `pause` 150 ms).
- Validoitu headless-selaimessa: raahaus → `.at-selection` 0×0,
  seek 10 s → tahti 6 (ei clampattu); pause → tahtilukema säilyy.
- 75 pytest-testiä (ei backend-muutoksia).

## v1.36 – 18.10.2026

- **SIIRTO neljännes tahdin tarkkuudella:** 0,25 tahdin askel = 1 isku
  4/4:ssä, joten 6–7 iskun vakiosiirto korjataan suoraan
  (esim. −1,5 tai −1,75). Arvo pyöristetään lähimpään 0,25:een ja
  tallentuu `meta.sync_offset_bars`iin.
- Rajaus ±64 tahtia; backend hyväksyy edelleen desimaalit.
- Testit: siirto tallentuu desimaalina (−1.5); 75 pytest-testiä.

## v1.35 – 18.10.2026

- **SIIRTO (tahtia)** -kenttä: siirtää tabia kokonaisilla tahdeilla
  (−64…+64, tallentuu `meta.sync_offset_bars`). Tarkoitettu
  rakenne-eroon, jota prosenttisäätö ei korjaa: esim. referenssitabissa
  on 258 tahtia mutta levytyksessä ~249, jolloin tabi voi olla
  8 tahtia edellä (≈13 s @ 143,5 BPM).
- Siirto lasketaan tabin omasta tahtipituudesta
  (`masterBars[1].start − masterBars[0].start` tickeinä) ja lisätään
  SYNC/BPM-korjauksen päälle; arvo tallentuu ja palautuu tabia
  avattaessa.
- `POST /api/tabs/{id}/sync` hyväksyy nyt `offset_bars`-kentän
  (validointi ±64).
- Testit: siirron tallennus ja raja; 75 pytest-testiä.

## v1.34 – 18.10.2026

- **Desimaali-TAB BPM:** kenttä hyväksyy 0,1 askelen (esim. `143,55`).
  GP5 tallentaa edelleen kokonaisluvun (`int(bpm+0,5)`), mutta
  desimaaliosa toteutetaan toiston korjauksena
  (`bpmDrift = bpm / nuottitempo - 1`), joka summataan SYNC-arvoon.
  Näin 143 → tab jää jälkeen / 144 → edistää -ongelma poistuu ilman
  GP5:n muokkaamista käsin.
- `meta.gp5_tempo` tallentaa kirjoitetun kokonaisluvun; frontend lukee
  ensisijaisesti alphaTabin `score.tempo`n.
- BPM näytetään kirjastossa ja otsikossa yhdellä desimaalilla, kun arvo
  ei ole kokonaisluku.
- Mitattu Seek & Destroy -audion tempo: **143,555 BPM**
  (librosa, mediaanibeat 0,41796 s; 420 beatia). Suositus: `143,55`.
- Headless-Chrome: 119,5 BPM → GP5 120, 58 s kohdalla tahti 29
  (ilman korjausta 30); 73 pytest-testiä.

## v1.33 – 18.10.2026

- **MP3-kuunteluversiot:** YouTube-latauksista tehdään WAV:n rinnalle
  MP3 `D:\tabtool_files\audio\mp3\<Artisti>\Artist - Title.mp3`
  (ffmpeg, libmp3lame VBR ~190 kbps). Artistikansiot syntyvät
  automaattisesti; tuntematon artisti → `Unknown Artist`.
  MP3 uudelleen­koodataan vain, jos WAV on uudempi. Pätkäklipit ja omat
  uploadit ohitetaan.
- `scripts/backfill_external.py` tekee myös MP3:t olemassa oleville
  YouTube-audioille (sama audio koodataan vain kerran).
- **Seek-synkki:** tutkittu headless-selaimessa (30 tahtia, 120 BPM,
  sliderilla 30→10→50→20→55→5 s). Tahtilukema osui joka kerta
  odotettuun tahtiin, joten siirto ei riko aikasynkkiä. Vakaunnukset:
  seekin aikana positiota ei syötetä alphaTabille (`audio.seeking`),
  `seekTo`/`seeked` pakottavat synkan, slider vapautetaan myös
  dokumentin `pointerup`/ikkunan `blur`-tapahtumissa.

## v1.32 – 18.10.2026

- **Ulkoinen arkisto:** YouTube-lataukset ja tuodut GP5/MusicXML-tabit
  mirroroidaan luettavalla nimellä (`Artist - Title.ext`) hakemistoon
  `D:\tabtool_files\audio` ja `D:\tabtool_files\tabs`
  (`TABTOOL_EXTERNAL_DIR`). Samalla levyasemalla käytetään hard linkiä,
  joten levytilaa ei kulu ylimääräistä; muuten tehdään kopio.
  Arkistointivirhe ei kaada jobia. Pätkäklipit jätetään arkistoimatta.
- `scripts/backfill_external.py` arkistoi olemassa olevan kirjaston
  kertaalleen.
- `tests/test_external_store.py` ja tuontitestin arkistovarmistus;
  testit käyttävät temp-hakemistoa, eivät `D:\tabtool_files`ia.
- Muistutus: `TABTOOL_DATA_DIR`-ympäristömuuttuja periytyy
  `Start-Process`ille. Jos se osoittaa testihakemistoon, UI näyttää
  tyhjän kirjaston vaikka `data/` olisi ehjä – käynnistä palvelin
  oikealla data-juurella.

## v1.31 – 18.10.2026

- **TALLENNA** (entinen `ASETA`): TAB BPM tallentuu vain napista.
  Kun kenttään kirjoittaa eri arvon kuin tabissa on, kenttä, syöte ja
  nappi muuttuvat punaisiksi, kunnes arvo on tallennettu; virheet
  (`BPM 20–400`, tallennusvirhe) näytetään punaisella.
- SYNC-tallennuksen virheet näytetään punaisella; onnistunut
  tallennus kuittaa tilan.
- `Not found` -virhe johtui vanhasta käynnissä olleesta
  palvelinprosessista (v1.22), jonka reiteissä ei ollut `/tempo`- eikä
  `/sync`-päätepistettä. Korjaus: käynnistä palvelin uudelleen
  (`start.bat`) koodimuutosten jälkeen.

## v1.30 – 18.10.2026

- **SYNC**-säädin: tabin kohdistus audion aikajanalle ±10 % (askel
  0,05 %). `+` siirtää tabia eteenpäin, `-` taaksepäin, joten pitkän
  kappaleen loppupään kertynyt heitto korjataan yhdellä säädöllä.
  Korjaus tallennetaan tabin `meta.json`iin (`sync_drift`) ja
  tietokantaan (`POST /api/tabs/{id}/sync`), joten se on automaattisesti
  mukana, kun tabi avataan uudelleen. GP5- ja audiotiedostoja ei muuteta.
- **Nopeus**-säätimen alue laajennettu 50–150 %:iin (aiempi 95–105 %).
  Nopeus on harjoittelusäädin: tabi seuraa audiota samassa suhteessa,
  joten kohdistus tehdään SYNC-säätimellä.
- Uudet testit: `tests/test_tab_sync.py` (tallennus, rajat, virheellinen
  arvo, tuntematon tabi).

## v1.29 – 18.10.2026

- **TAB BPM** -korjaus: katselimen transportissa voi asettaa GP5-tabin
  todellisen tempon. Backend päivittää GP5:n `song.tempo`-arvon,
  tietokannan ja `meta.json`in (`POST /api/tabs/{id}/tempo`).
  Näin tabi saadaan kappaleen nopeuteen: esim. Seek & Destroy
  -referenssitabi 140 → 144 BPM, audio 100 %:ssa. Tahti 62 osuu tällöin
  kohtaan 1:42 (101.7 s).
- **Nopeus**-säädin tarkentui: 95–105 %, askel 0,1 % ja yhden
  desimaalin näyttö. Sillä hienosäädetään esim. 143,55 BPM audio
  vastaamaan 144 BPM tabia.
- AI-BPM on jatkossa merkitty arvioksi (`AI-arvio`), ei absoluuttiseksi
  totuudeksi; kappaleen tempo ratkaisee.

## v1.28 – 18.10.2026

- Tuodun referenssitabin audio: `LIITÄ AUDIO` etsii samannimisen tabin,
  jolla on audio (esim. AI-tabi), ja liittää sen audiopolun tuotuun
  tabiin (`POST /api/tabs/{id}/attach-audio`). Tämän jälkeen myös tuotu
  tabi soi, vierittyy ja toimii fullscreenissä koko kappaleen ajan.
- Katselimeen lisätty **Nopeus**-säädin (85–115 %). Sillä voi hienosäätää
  audion nopeuden tabin tempoon, esim. 140 BPM tabi + 144 BPM audio.
  `preservesPitch` pitää sävelkorkeuden normaalina.
- `LIITÄ AUDIO` näkyy vain tabilla, jolla ei ole audiota; liittämisen
  jälkeen PLAY, aikajana, cursor ja Nopeus tulevat näkyviin. Tuodun tabin
  `meta.json` päivitetään samalla, jotta audiolinkitys säilyy.
- Täydet kappaleet ovat oletus; pätkägenerointi on edelleen poikkeus.

## v1.27 – 18.10.2026

- Pätkägenerointi: katselimessa voi siirtyä kohtaan, valita 30/60/120 s ja
  painaa `TEE TAB TÄSTÄ`. Backend luo uuden jobin nykyisen tabin audiosta
  ja asetuksista (`POST /api/tabs/{id}/section`), leikkaa audiosta pätkän
  ja tekee tabin vain siitä. Uusi tabi avautuu automaattisesti ja sen
  nimessä on aikaväli, esim. `Seek & Destroy [0:28 +60s]`.
- Tuodut tabit merkitään kirjaston tooltipissa (`Lähde: tuotu tabi`).
  Moniraitaisesta GP5/MusicXML-tabista näytetään oletuksena kaksi
  ensimmäistä kitaraa (Guitar 1 + Guitar 2); loput raidat saa valittua
  raitanapeista.
- Pätkägenerointi käyttää samaa audiota ja samoja asetuksia kuin
  lähtötabi, joten se toimii myös YouTube-lähteille ilman uutta latausta.

## v1.26 – 18.10.2026

- Valmiin tabin tuonti: GP5 ja MusicXML (`POST /api/tabs/import`).
  Tuotu tabi tallennetaan `data/tabs/`-hakemistoon ja rekisteröidään
  kirjastoon; metatiedot (nimi, artisti, BPM, tahtimäärä) luetaan
  tiedostosta (PyGuitarPro / music21).
- UI: `Tuo valmis tabi (GP5 / MusicXML)` -tiedostovalinta ja
  `IMPORT TAB` -nappi. Tuotu tabi avautuu suoraan katselimeen.
- Tuodulla tabilla ei ole audiota, joten PLAY ja aikajana piilotetaan;
  tabi, raitavalinnat, näkymävalinta ja export toimivat. Export-linkit
  näytetään vain niille formaateille, jotka tabissa on.
- Tämä on suositeltu polku, kun halutaan juuri opeteltu standarditabi
  (esim. Songsterr/Guitar Pro) AI-luonnoksen sijaan.

## v1.25 – 18.10.2026

- YouTube-jobien nimi ja artisti haetaan nyt yt-dlp:n metadatasta ja
  puhdistetaan (esim. `(Remastered)` pois). `YouTube audio` jää vain
  fallbackiksi, jos metadata ei ole saatavilla.
- `meta.json` sisältää nyt `audio_path`-kentän myös web-jobille, joten
  tabi voidaan tuoda uudelleen ilman audion katoamista.
- Katseluun lisätty aikajana: nykyinen aika, kokonaiskesto, tahtilukema,
  −5 s/+5 s -siirtymät sekä Space- ja nuolinäppäimet. Tahtilukema auttaa
  hyppäämään intron jälkeen alkavaan riffiin.
- Olemassa oleva Seek & Destroy -tabi nimettiin uudelleen
  (`Metallica — Seek & Destroy`) tietokantaan, `meta.json`iin, GP5:een ja
  MusicXML:ään.

## v1.24 – 18.10.2026

Soittonäkymän seurattavuus ja siisteys.

- Cursor ei enää karkaa ruudun yläosaan rivinvaihdossa. Käytössä on
  alphaTabin `Smooth`-scroll ja negatiivinen `scrollOffsetY`, joka
  skaalautuu näkymän korkeuden mukaan. Edellinen järjestelmä jää näkyviin
  nykyisen yläpuolelle, joten etenemistä ja jo soitettua kohtaa on helppo
  seurata.
- Dynamiikkamerkinnät (`p`, `mp`, `mf`, `f`, …) piilotettu. Ne syntyivät
  Basic Pitchin velocity-arvoista eivätkä tuo tablatuuriin lisäarvoa.
  Piilotus tehdään `NotationElement.EffectDynamics` -asetuksella, joten
  se koskee myös vanhoja tabeja ilman uudelleengenerointia.

## v1.23 – 18.10.2026

Katselunäkymän parannukset Phase 2:n päälle.

- Oletusnäkymä on pelkkä tablatuuri. `Näkymä`-valinnalla voi vaihtaa
  tab + nuotit, nuotit tai Auto (kitarat tablatuurina, muut nuotteina);
  valinta muistetaan selaimessa.
- Raitavalitsin: tabin raidat voi näyttää ja piilottaa. Valinta
  muistetaan tabikohtaisesti. Nykyiset generoidut tabit sisältävät
  yhden `Guitar`-raidan.
- `FULLSCREEN` ja automaattinen koko näyttö PLAY:ta painettaessa; Esc
  palauttaa. Koko näytössä tabit skaalautuvat ruudun mukaan.
- Soittocursor: vihreä tahtikorostus ja beat-viiva seuraavat paikallista
  audiota. alphaTabin cursor-CSS lisätty, koska vendor-bundlessa ei ole
  tyylejä.
- Vaakascrollbar poistettu tablatuurin alta; pitkä tabi vierittyy
  pystysuunnassa.
- Kirjaston napeissa tooltip (tahtimäärä, nuotit, BPM, luontiaika ja ID),
  joten samannimiset versiot erottuvat. Myös lomakkeen valikoissa tooltipit.
- `EXPORT` siirretty pois pääkontrolliriviltä; tilalla näkymä- ja
  raitavalinnat.

## v1.22 – 18.10.2026

Tuotenimi vaihdettu: **AI TabTool**.

- `APP_NAME` = "AI TabTool"; HTML-otsikot, wordmark `AI TABTOOL` ja
  brand-mark `AT` (aiempi `TT` muistutti TabToolia).
- `start.bat` ja `scripts/open_browser.ps1` käyttävät uutta nimeä.
- Sisäiset tunnisteet ennallaan: `TABTOOL_*`-ympäristömuuttujat,
  `data/tabtool.sqlite3` ja repo `teppoaland/tabtool`.
- Testit päivitetty uuteen nimeen; ei toiminnallisia muutoksia.
- README: nimi- ja tavaramerkkihuomautus.

## v1.21 – 18.10.2026

- `start.bat` avaa oletusselaimen automaattisesti vasta kun palvelin
  vastaa `/api/health` (uusi `scripts/open_browser.ps1`, 30 s timeout).
- `TABTOOL_NO_BROWSER=1` ohittaa automaattiavauksen (automaatio/testit).
- Ei muita toiminnallisia muutoksia.

## v1.20 – 18.10.2026

Phase 2 – web-käyttöliittymä, job-jono, cache, alphaTab ja paikallinen toisto.

### Muutokset

- `app/db.py`: SQLite-skeema (`tracks`, `jobs`, `tabs`, `oauth_tokens`,
  `settings`), cache-avain, `data/`-juureen sidotut polkuapurit ja
  CLI-tabien tuonti (`data/tabs/<nimi>/meta.json`).
- `app/jobs.py`: yhden workerin job-jono, vaihekohtainen progress
  (queued → downloading → separating → transcribing → building → ready),
  SSE-tilaukset, cache-osuma ilman uutta ajoa, `regenerate`-tuki.
- `app/main.py`: `POST /api/jobs` (upload / YouTube / local path),
  `GET /api/jobs`, `GET /api/jobs/{id}`, `GET /api/jobs/{id}/events`,
  `GET /api/tabs`, `GET /api/tabs/{id}`, inline `score/{fmt}`,
  attachment `export/{fmt}` ja Range-tuettu `audio`.
- UI: upload/YouTube-lomake, viritys/grid/nopea tila, status-rivi,
  kirjasto, alphaTab-katselin, `PLAY`/`PAUSE` ja `EXPORT`.
- alphaTab 1.8.4 vendoroituna (`app/static/vendor/alphaTab/`,
  MPL-2.0 + Bravura OFL), ulkoinen media `IExternalMediaHandler`illa ja
  50 ms positiosynkka.
- Tabit kirjoitetaan temp-hakemistoon ja `os.replace`lla; cache-avain =
  audion sormenjälki + pipeline-versio + asetukset.
- 45 pytest-testiä; API-, cache-, validointi- ja polkuturvatestit
  mockatulla putkella.

### Validointi

- Oikea putki nopeassa tilassa 20 s klipillä: 12 tahtia, 58 nuottia,
  GP5 luettu takaisin (78 nuottimerkintää), MusicXML jäsentyy.
- 137 tahdin KISS-tabi renderöityy alphaTabilla headless-Chromessa
  (30 254 px korkea sivu, nuottimerkinnät piirtyvät).
- 46 MB WAV striimautuu Range-pyynnöllä (206, `bytes 0-99/...`).
- Korjaukset browser-validoinnissa: fonttipolun trailing slash,
  `PlayerState`-enumin puuttuminen UMD-globalista, `useWorkers: false`.

## v1.11 – 18.10.2026

Tie-korjaus ja validointi.

- GP5- ja MusicXML-viennissä tie-tila on nyt nuottikohtainen. Aiemmin
  saman segmentin uudet ja edellisestä tahdista jatkuvat nuotit saivat
  saman tie-tilan (255 sekasegmenttiä KISS-testissä).
- Uusi testi `test_tie_state_is_per_note`.
- 30 pytest-testiä.
- Koko YouTube-testikohde (KISS – I’m A Legend Tonight, 4:00) ajettu
  läpi: 137 tahtia, 1410 tab-nuottia, GP5 validi, ei rikkinäisiä
  tahtikestoja eikä päällekkäisiä kieliä.

## v1.10 – 18.10.2026

Phase 1 – audio-to-tab -putki.

- Lisätty `app/pipeline/`: `audio_source`, `separate`, `transcribe`,
  `tempo`, `quantize`, `fretboard`, `segments`, `build`,
  `export_gp5`, `export_musicxml`, `export_midi`.
- `scripts/pipeline_smoke.py`: local/YouTube → ffmpeg → Demucs 6s →
  Basic Pitch → tempo → quantize → fretboard → GP5/MusicXML/MIDI +
  `meta.json`.
- Demucs `htdemucs_6s`, 4-stem fallback ja `--no-separation`-pikatila.
- Tempo normalisoidaan 70–180 BPM -alueelle (esim. 68 → 136).
- Kielikohtainen monofonia: päällekkäinen nuotti siirretään vapaalle
  kielelle tai edellistä nuottia lyhennetään.
- Fretboard-Viterbi ja virityspresetit: standard, drop D, Eb, D, open G,
  bass 4-string.
- GP5/MusicXML/MIDI-export. GP5 validointi: 108 tahtia, 884 tab-nuottia,
  ei rikkinäisiä tahtikestoja eikä päällekkäisiä kieliä.
- 29 pytest-testiä.
- ML-riippuvuudet: Demucs 4.1.0, Basic Pitch 0.4.0, TensorFlow 2.15,
  Torch 2.14 CPU. `setuptools<81`, koska Basic Pitchin resampy käyttää
  `pkg_resources`-APIa.
- Validointi: 3:10 MP3 ~67 s CPU:lla; YouTube 20 s klipit toimivat.

## v1.00 – 18.10.2026

Projektin runko ja säännöt.

- `git init`, `origin` = `teppoaland/tabtool`.
- `.gitignore`: `docs/`, `data/`, `.venv`, audio/tab-tiedostot, tokenit,
  mallit ja välimuistit pois julkisesta gitistä.
- `.clinerules/`: arkkitehtuuri, putken ydinsäännöt, versionhallinta,
  data/yksityisyys/lisenssit, kevyt polku ja ei ylimääräisiä dialogeja.
- FastAPI-runko: `/api/health`, `/api/version`, `/`, `/remote`, `/display`.
- Tyhjä tumma TV- ja remote-näkymä.
- `requirements.txt`, `requirements-ml.txt`, `requirements-dev.txt`.
- `setup.bat`, `install-ml.bat`, `start.bat`, `test.bat`.
- Ensimmäinen pytest-testi ja versiotarkistus.
- Lisenssi: All rights reserved. Kolmannen osapuolen lisenssit erillisessä
  `THIRD_PARTY_NOTICES.md`-tiedostossa.
