# 🔒 Data, yksityisyys ja lisenssit

## Yksityiset tiedostot

Nämä eivät koskaan mene julkiseen gitiin:

- `docs/` – henkilökohtaiset suunnitelmat ja muistiinpanot
- `data/` – audio, stemmit, tabit, SQLite, Spotify-tokenit, lokit
- `.env` ja kaikki `.env.*` (paitsi `.env.example`)
- `*.wav`, `*.mp3`, `*.flac`, `*.gp5`, `*.musicxml`, `*.mid` jne.

## Spotify

- Käytetään **Authorization Code with PKCE** -virtaa; ei client secretiä.
- Tokenit tallennetaan vain `data/`-hakemistoon (gitignored).
- Access token annetaan selaimelle vain Web Playback SDK:ta varten.
- `/api/spotify/token` ja muut herkät Spotify-reitit vain localhostille,
  ellei LAN-PIN ole käytössä.
- Spotifyä käytetään hakuun, metadataan ja valinnaiseen toistoon.
  **Spotifyn DRM-audiota ei tallenneta eikä pureta.**

## Äänilähteet

- Ensisijainen: käyttäjän oma MP3/WAV tai yt-dlp:llä ladattu audio.
- Tabi sidotaan siihen audiotiedostoon, josta se tehtiin.
- YouTube-lataus on käyttäjän vastuulla (YouTube ToS, tekijänoikeudet).
- Generoidut transkriptiot ovat henkilökohtaiseen käyttöön; niitä ei
  julkaista eikä levitetä.

## Lisenssit

- Projektin lisenssi: **All rights reserved** (GameHubin käytäntö).
- Kolmannen osapuolen komponentit pysyvät omilla lisensseillään:
  Demucs (MIT), Basic Pitch (Apache-2.0), alphaTab (MPL-2.0),
  PyGuitarPro (LGPL-3.0), yt-dlp (Unlicense), FastAPI (MIT),
  music21 (BSD-3), librosa (ISC).
- Luettelo ylläpidetään `THIRD_PARTY_NOTICES.md`:ssä.
- Älä kopioi kolmannen osapuolen lähdekoodia omaan koodiin.

## Palvelimen verkko

- Oletus: `127.0.0.1:8000`.
- `--lan` / `TABTOOL_HOST=0.0.0.0` vain luotetussa lähiverkossa.
- Suositus: valinnainen `TABTOOL_LAN_PIN`.
- Ei CORSia eikä julkista `data/`-static-mounttia.
