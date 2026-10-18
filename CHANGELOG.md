# 📜 CHANGELOG – AI TABTOOL

> AI TabTool käyttää `1.x`-versiosarjaa. Aloitus `v1.00`.

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
