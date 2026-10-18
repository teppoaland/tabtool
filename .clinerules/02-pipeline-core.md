# 🎸 Putken ydinsäännöt

## Putki

```
audio → stemmit → transkriptio → tempo/kvantisointi → otelauta → export → cache
```

## Suojatut moduulit

- `app/pipeline/audio_source.py` – upload, local path, yt-dlp
- `app/pipeline/separate.py` – Demucs `htdemucs_6s`
- `app/pipeline/transcribe.py` – Basic Pitch
- `app/pipeline/tempo.py` – librosa beat/tempo
- `app/pipeline/quantize.py` – grid, tahdit, restit, tie
- `app/pipeline/fretboard.py` – kieli/ote-dynamic programming
- `app/pipeline/export_*.py` – GP5, MusicXML, MIDI

## Invariantit

1. Sama `track_id` + samat asetukset + sama audio → sama tulos.
2. Valmis tab cachetetaan; ei ylikirjoiteta ilman eksplisiittistä
   `regenerate`-pyyntöä.
3. Audio, stemmit ja tabit ovat yksityisiä: ei koskaan `static/`-hakemistoon
   eikä gitiin.
4. Kaikki tiedostopolut validoidaan `data/`-juuren alle (path traversal -suojaus).
5. Kirjoitukset tehdään temp-tiedostoon ja `os.replace`-operaatiolla;
   epäonnistunut job ei jätä puolikasta tabia näkyviin.
6. Jobin metadataan tallennetaan malli, malliversio, parametrit ja varoitukset.
7. Kitara on ensisijainen. Basso, laulu ja rummut lisätään vasta, kun
   kitaralinja toimii.
8. Demucs-oletus on `htdemucs_6s` (guitar/bass/drums/vocals/other/piano).
   4-stem `htdemucs` on fallback.
9. Basic Pitch ei tue rumpuja; rummut vaativat oman mallin (esim. ADTOF).

## Testit

Kun logiikka muuttuu:

```
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m compileall -q app
node --check app\static\app.js
node --check app\static\remote.js
```

## Laatutavoite

v1.0 tuottaa **soitettavan ensimmäisen luonnoksen**, ei täydellistä
transkriptiota. Korjaus tapahtuu viemällä GP5 Guitar Prohon tai TuxGuitariin.
