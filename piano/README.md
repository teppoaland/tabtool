# 🎹 PianoCapture v0.1

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
   ensimmäiset 75 s ja ehdottaa ikkunan:
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

## Mitattu esimerkki

Testikappale: Diablo – *The Well of Grief*
(<https://www.youtube.com/watch?v=StJwVS0IyO8>), jossa piano alkaa 11 s ja
muut soittimet tulevat mukaan 26 s.

- Ehdotus: **11,0 s → 26,0 s**, varmuus **97 %**.
- Transkriptio 15 s pätkästä: **85 nuottia**, sävelalue MIDI 31–81.
- 74 % nuottien aloituksista osui 60 ms sisään havaittuun onsetiin – suuntaa
  antava laadunmitta, ei todiste oikeellisuudesta. **Korvalla tarkistus on
  ainoa hyväksyntä.**

## Data ja tiedostot

```
data_piano/
  sources/<hash>.wav        # ladattu ja normalisoitu mono 44.1 kHz
  sources/<hash>.json       # url, title, artist, duration
  pieces/<id>/piece.json    # ikkuna + nuotit
  pieces/<id>/audio.wav     # pätkän ääni
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

## Tunnetut rajat (v0.1)

- Ei pedaalin tunnistusta; pitkät nuotit ≈ pedaali.
- Ei kvantisointia tahtiviivoille (tarkoituksella: soitin on piano, ei tabi).
- Käsijako on MIDI-raja (oletus C4), ei oikea käden tunnistus.
- Basic Pitch tuottaa joskus ylimääräisiä harmonisia; onset/frame-kynnyksiä
  voi säätää `piano/transcribe.py`:ssä.
- Analyysi olettaa, että bändin sisääntulo kuuluu äänenvoimakkuuden ja
  perkussiivisuuden hyppynä. Jos intro vaihtuu suoraan soolosoittimeen ilman
  dynamiikkamuutosta, ehdotus menee pieleen → käytä käsin asetettua ikkunaa.

## Seuraavaksi (ehdotus)

1. Pedaalin ja käsien parantaminen (splitin automaatti voice leading -logiikalla).
2. A/B-loop dragauksella ja "toista tämä tahti" -harjoittelu.
3. Tahdeiksi kvantisointi ja MusicXML, jos joskus haluaa nuotit MuseScoreen.
4. Taso 2 analyysiin: Demucs 6s vain alusta, jos heuristiikka ei riitä.
