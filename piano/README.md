# 🎹 PianoCapture v0.3

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

## Tausta ja lataukset

- **Taustaääni** (oletuksena päällä): pätkä soi nuottien alla. Kun sen ottaa
  pois, ääni vaikenee mutta kello ja nuotit jatkavat – voit soittaa omalla
  pianolla mukana. Valinta muistetaan selaimessa.
- **LATAA AUDIO (MP3)** – pätkä MP3:nä puhelimeen, DAW:iin tai
  taustanauhakäyttöön. Ensimmäinen lataus koodaa tiedoston ffmpegillä, sen
  jälkeen se tulee cachesta pätkän kansiosta.
- **LATAA MIDI** – transkriptio MIDI-tiedostona (MuseScore, DAW, synteesi).
  Sama tiedosto kirjoitetaan jo käsittelyvaiheessa (`notes.mid`).

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
