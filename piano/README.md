# 🎹 PianoCapture v0.6.2

PianoCapture on **erillinen, kevyt app** AI TabToolin rinnalla samassa repossa.
Se ottaa YouTube-linkin (tai äänitiedoston), etsii pianon alun ja bändin
sisääntulon, transkriboi pätkän nuoteiksi ja näyttää ne **88-skaalaisella
pianokoskettimistolla** laskevina nuotteina ilman nuottiviivastoa.

Sovellus on tarkoitettu pianon alkuosille ja lyhyille pätkille, ei kokonaisille
kappaleille.

## Rajaus (tärkeä)

- **Soittimia ei erotella.** Oletus on, että pätkässä soitin on piano. Jos
  pätkä sisältää rumpuja, kitaraa tai orkesteria, transkriptio on sotkuinen –
  se on käyttäjän valinta, ei bugi.
- **Aikaikkuna on ainoa portti.** Alku ja loppu valitaan joko automaattisen
  ehdotuksen pohjalta tai käsin. Ehdotus ei ole totuus: se näytetään aina
  muokattavana.
- **Ei kitaran mallia.** Ei viritystä, ei otelautaa, ei GP5:tä. Nuotti on
  `pitch / start / end / velocity`, ja soitin on 88 koskettimen piano (A0–C8).

## Käynnistys

```bat
start-piano.bat
```

- Työpöydän **PianoCapture**-kuvake tekee saman (käynnistää `start-piano.bat`in
  ja avaa selaimen). Kuvake käyttää `piano/static/piano.ico`-ikonia, jotta se
  erottuu TabTool-kuvakkeesta.
- Yksi kaksoisklikkaus riittää myös uudelleenkäynnistykseen: vanha 8020:n
  instanssi pysäytetään ensin. Sulje konsoli-ikkuna (tai Ctrl+C) lopettaaksesi.
- `PIANO_NO_BROWSER=1` estää selaimen automaattisen avauksen (esim. testaus).
- UI: <http://127.0.0.1:8020>
- API-dokumentaatio: <http://127.0.0.1:8020/docs>
- Oma data: `data_piano/` (gitignoroitu). TabToolin `data/` ja portti 8000
  eivät ole käytössä.
- Sama venv kuin TabToolilla: Torch/Demucs/Basic Pitch -asennuksia ei
  tarvitse tehdä uudelleen.

## Työnkulku

1. **ANALYSOI ALKU** – lataa äänen kerran (`data_piano/sources/`), ottaa
   ensimmäiset 180 s ja ehdottaa ikkunan:
   - **piano alkaa** = ensimmäinen kestävä harmoninen alkusoitto
     (HPSS: harmoninen vs. perkussiivinen energia; vesi/taustakohina on
     pääosin perkussiivista, piano harmonista),
   - **bändi tulee mukaan** = ensimmäinen kestävä (~0,5 s) hyppy sekä
     perkussiivisuudessa että kokonaisäänenvoimakkuudessa; matala kaista ja
     onset-tiheys ovat lisätodisteita.
2. **KÄYTÄ EHDOTUSTA / säädä** – alku ja loppu sekunteina.
3. **KÄSITTELE PÄTKÄ** – leikkaa pätkä, transkriboi Basic Pitchillä ja tallentaa
   pätkän (`data_piano/pieces/<id>/`).
4. **Soita** – 88 koskettinta, laskevat nuotit, soittopää, vasen/oikea käsi
   eri väreillä, nopeus 50–100 %, loop, valinnainen synteettinen näppäinääni.

Pikanäppäimet: `Space` = PLAY/PAUSE, `←`/`→` = ±5 s, `Home` = alkuun.

## KIERTO – opettele yksi kuvio

Pianon alku on usein lyhyt kuvio, joka toistuu 2–4 kertaa. Koko intron
opetteleminen sellaisenaan on turhaa työtä: yksi kierto riittää, ja loput ovat
sama asia bändin kanssa.

- **KIERTO**-valinta näyttää ja loopittaa vain yhden kierron: nuotit rajataan
  kierron loppuun ja ääni hyppää takaisin alkuun.
- **Kierron pituus** ehdotetaan automaattisesti: onset-voimakkuuden
  autokorrelaatiosta etsitään vahvin jakso välillä 1,5–12 s (vähintään kaksi
  toistoa). Ehdotus näkyy muodossa `3,8 s × 3,9`.
- **÷2 / ×2** vaihtavat tahtitasoa: jos ajattelet kuvion olevan 2 tahtia mutta
  työkalu löysi 1 tahdin (tai päinvastoin), yhdellä painalluksella saa oikean.
- Numeroa voi myös kirjoittaa suoraan, joten korvalla tehty korjaus on aina
  mahdollista. Automaatti on ehdotus, ei totuus.
- Jos toistoa ei löydy varmasti (onset-autokorrelaation huippu alle 0,15),
  **KIERTO on pois päältä** ja näytetään koko pätkä. Näin kautta sävelletylle
  introlle ei tarjota väkisin kiertoa – sen voi silti asettaa käsin.

Kun kierto on opeteltu, ota **KIERTO** pois päältä: soitto jatkuu koko pätkän
(yhteensä bändin kanssa), ja nuotit näytetään alkuperäisessä pituudessaan.

## Kuuntele ohje – onko transkriptio oikein?

Aloittelija ei ehdi soittaa kuviota niin nopeasti, että voisi verrata sitä
levyyn. Siksi ohjeen voi **kuunnella sellaisenaan**:

- **ORG / MID PLAY-painikkeen vieressä:** **ORG** soittaa alkuperäisen
  äänitteen, **MID** soittaa transkription pianomaisella synteesillä
  (harmoninen sarja + vaimeneva envelope). Vaihto kesken toiston vaihtaa
  lähteen samasta kohdasta, joten A/B-vertailu on välitön.
- **Ohjeääni + Taustaääni** yhdessä = kuulet molemmat päällekkäin ja huomaat
  heti, jos nuotti on väärä.
- **LATAA OHJE (MP3)** – koko transkriptio audiotiedostona (serveri renderöi
  sen `guide.wav` → `guide.mp3`, cache pätkän kansiossa). Voit kuunnella sen
  puhelimessa tai hidastaa sitä missä tahansa soittimessa.
- **LATAA MIDI** – sama sisältö MIDInä DAWiin/MuseScoreen.

Synteesi on tarkoituksella yksinkertainen eikä se ole pianon sample: se riittää
kertomaan, *mitkä nuotit* ohjeessa on ja *milloin* ne alkavat. Vertaa aina
alkuperäiseen – se on ainoa totuus.

**v0.5.2:** korjattu bugi, jossa MID-ääni katosi kokonaan, jos sitä ennen oli
soittanut pidempää pätkää (esim. Gathering 2:07 → Diablo 0:15). Syy oli
ääniaikaan sidottu "voices"-throttle, joka jäi päälle pitkästä pätkästä; nyt
se on poistettu ja äänimäärä nollataan pätkän vaihtuessa.

## Käsien rajaus myös latauksiin (v0.6)

Kun **Vasen** tai **Oikea** otetaan pois päältä, myös **LATAA OHJE (MP3)** ja
**LATAA MIDI** rajaavat pois piilotetun käden – esimerkiksi Diablon vasemman
käden haamunuotit. Rajana on **Käsiraja** (oletus C4 = MIDI 60), ja serveri
renderöi rajatun version omaan cacheensa (`guide-right-60.wav` yms.).
Kun molemmat kädet ovat näkyvissä, lataus sisältää kaikki nuotit.

**v0.6.1:** käsivalinta muistetaan **pätkäkohtaisesti** (localStorage), joten
Diablo avautuu suoraan oikea käsi -tilassa ja TG molemmilla käsillä. Itse
`piece.json`ia ei muuteta – alkuperäiset nuotit pysyvät tallessa ja
rajaus tehdään näkymään, synteesiin ja latauksiin.

**v0.6.2:** sekä **Taustaääni** että **Ohjeääni** muistetaan selaimessa, joten
ORG/MID-valinta säilyy reloadin yli. Jos molemmat olisivat pois päältä,
sovellus palauttaa automaattisesti ORGin – PLAY ei jää mykäksi eikä
ORG/MID-valinta tyhjäksi. Mix-tilassa (molemmat päällä) molemmat vaihtoehdot
näkyvät valittuina.

## Tausta ja lataukset

- **Taustaääni** (oletuksena päällä): pätkä soi nuottien alla. Kun sen ottaa
  pois, ääni vaikenee mutta kello ja nuotit jatkavat – voit soittaa omalla
  pianolla mukana, tai kuunnella pelkän ohjeen. Valinta muistetaan selaimessa.
- **LATAA AUDIO (MP3)** – pätkä MP3:nä puhelimeen, DAW:iin tai
  taustanauhakäyttöön. Ensimmäinen lataus koodaa tiedoston ffmpegillä, sen
  jälkeen se tulee cachesta pätkän kansiosta.
- **LATAA OHJE (MP3)** – transkriptio audiona (ks. edellinen luku).
- **LATAA MIDI** – transkriptio MIDI-tiedostona (MuseScore, DAW, synteesi).
  Sama tiedosto kirjoitetaan jo käsittelyvaiheessa (`notes.mid`).

## Puhelin ja tabletti

Pianon edessä ei ole tilaa PC:lle, joten koko näkymä toimii puhelimessa tai
tabletissa samassa Wi-Fi-verkossa:

- `start-piano.bat` sitoo palvelimen `0.0.0.0`:aan. Asetusnäytön
  **Puhelin/tabletti**-rivillä on LAN-osoite ja QR-koodi, jolla puhelin avaa
  saman sivun. Soittimen otsikossa on **pieni QR**, joka avaa juuri sen pätkän
  suoraan (`/?piece=<id>`).
- Kapealla näytöllä klaviatuuri **rajautuu kappaleen käyttämään sävelalueeseen**
  (vähintään 2 oktaavia), jotta koskettimet pysyvät luettavina. Leveällä
  näytöllä näkyvät kaikki 88.
- Puhelin toistaa taustaäänen itse (tai Taustaääni pois), joten PC:tä ei
  tarvita pianon viereen – se voi olla toisessa huoneessa palvelimena.
- Jos puhelin ei yhdistä, salli portti **8020** Windows Defenderin
  palomuurissa yksityisille verkoille.
- PianoCapturella ei ole PIN-porttia (toisin kuin TabToolin kaukosäätimessä):
  käytä sitä vain luotetussa kotiverkossa.

## Transkriptio

Basic Pitch, mutta **pianon parametreilla** (TabToolin kitara-asetukset eivät
kelpaa):

| Parametri | TabTool (kitara) | PianoCapture |
|---|---|---|
| `minimum_frequency` | 80 Hz | **27,5 Hz** (A0) |
| `maximum_frequency` | 1200 Hz | **4186 Hz** (C8) |
| `melodia_trick` | True | **False** (soinnut ja molemmat kädet säilyvät) |
| `minimum_note_length` | 58 ms | 80 ms |

Nuotit tallennetaan JSONiin ja lisäksi `notes.mid` (tarkistus MuseScorella).

## Mitatut esimerkit

**Diablo – *The Well of Grief*** (<https://www.youtube.com/watch?v=StJwVS0IyO8>):
piano alkaa 11 s, muut soittimet 26 s.

- Ehdotus: **11,0 s → 26,0 s**, varmuus **97 %**.
- Kierto: **3,84 s × 3,9** (varmuus 0,94) – eli 2 tahdin kuvio ~123 BPM:ssä.
- Transkriptio 15 s pätkästä: **85 nuottia**, sävelalue MIDI 31–81.
- 74 % nuottien aloituksista osui 60 ms sisään havaittuun onsetiin – suuntaa
  antava laadunmitta, ei todiste oikeellisuudesta. **Korvalla tarkistus on
  ainoa hyväksyntä.**

**The Gathering – *Black Light District*** (<https://www.youtube.com/watch?v=FpGGVkt1M3M>):
yhtenäinen, ei-toistuva piano-intro 0 – 2:09.

- Ehdotus: **0,8 s → 128,3 s** (2:08,3), varmuus **100 %**.
- Kierto: **ei kiertoa** (onset-autokorrelaation huippu 0,06 < 0,15) –
  KIERTO on pois päältä ja koko 2:08 näytetään sellaisenaan.
- Transkriptio 127,5 s pätkästä: **178 nuottia**.

## Data ja tiedostot

```
data_piano/
  sources/<hash>.wav        # ladattu ja normalisoitu mono 44.1 kHz
  sources/<hash>.json       # url, title, artist, duration
  pieces/<id>/piece.json    # ikkuna + nuotit + kierto
  pieces/<id>/audio.wav     # pätkän ääni
  pieces/<id>/audio.mp3     # ladattava tausta (koodataan ensimmäisellä latauksella)
  pieces/<id>/guide.wav     # transkriptio audiona (renderöidään tarvittaessa)
  pieces/<id>/guide.mp3     # ohjeen MP3-lataus
  pieces/<id>/notes.mid     # MIDI-tarkistus
  tmp/                      # analyysin väliaikainen otos
```

Koodi:

```
piano/
  main.py         # FastAPI-reitit + staattinen sivu
  pipeline.py     # analyze_source / process_window
  analyze.py      # intron ja bändin sisääntulon heuristiikka
  transcribe.py   # Basic Pitch, pianon parametrit
  audio.py        # yt-dlp/ffmpeg (lainaa app.pipeline.audio_source)
  store.py        # pätkien tallennus
  jobs.py         # kevyt taustatyörekisteri
  static/         # UI (canvas, ei riippuvuuksia)
```

## Testit

```bat
.venv\Scripts\python.exe -m pytest tests\test_piano.py -q
```

Testit käyttävät synteettistä audiota ja monkeypatchattua transkriptiota:
ei verkkoa, ei TensorFlow'ta, ei mallilatauksia.

## Tunnetut rajat (v0.2)

- Kiertoehdotus olettaa, että kuvio alkaa pätkän alusta ja että sen rytmi
  toistuu samana. Jos kuvio alkaa vasta sekunnin päästä tai rytmi vaihtelee,
  ehdotus osuu väärään kohtaan → aseta pituus itse (÷2/×2 tai numero).
- Ei pedaalin tunnistusta; pitkät nuotit ≈ pedaali.
- Ei kvantisointia tahtiviivoille (tarkoituksella: soitin on piano, ei tabi).
- Käsijako on MIDI-raja (oletus C4), ei oikea käden tunnistus.
- Basic Pitch tuottaa joskus ylimääräisiä harmonisia; onset/frame-kynnyksiä
  voi säätää `piano/transcribe.py`:ssä. Tarkoitus on antaa **suunta ja
  esimerkki**, ei virheetön transkriptio.
- Analyysi olettaa, että bändin sisääntulo kuuluu äänenvoimakkuuden ja
  perkussiivisuuden hyppynä. Jos intro vaihtuu suoraan soolosoittimeen ilman
  dynamiikkamuutosta, ehdotus menee pieleen → käytä käsin asetettua ikkunaa.

## Seuraavaksi (ehdotus)

1. Kierron automaattinen aloituskohta (nyt oletus: pätkän alku).
2. Pedaalin ja käsien parantaminen (splitin automaatti voice leading -logiikalla).
3. A/B-loop dragauksella ja "toista tämä tahti" -harjoittelu.
4. Tahdeiksi kvantisointi ja MusicXML, jos joskus haluaa nuotit MuseScoreen.
5. Taso 2 analyysiin: Demucs 6s vain alusta, jos heuristiikka ei riitä.
