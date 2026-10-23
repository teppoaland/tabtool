# 🏗️ AI TABTOOL – arkkitehtuuri

## Projektin luonne

AI TabTool on **lokaali, yhden käyttäjän web-palvelu** (versiosarja `1.x`).
Se hakee kappaleita Spotifysta, generoi kitaratablatuurin paikallisesta
audiosta tai YouTube-lähteestä sekä näyttää tabin alphaTabilla. Palvelin
pyörii käyttäjän omalla koneella; ei pilveä, ei monikäyttäjätilejä.

## Suojatut tiedostot

> ⚠️ Älä muuta ilman erillistä pyyntöä.

- `app/main.py` – FastAPI-sovellus, reitit, staattiset tiedostot
- `app/config.py` – polut, ympäristömuuttujat, asetukset
- `app/db.py` – SQLite-skeema ja kyselyt
- `app/spotify.py` – OAuth PKCE, token refresh, Spotify Web API
- `app/jobs.py` – job-jono, worker, SSE-eventit
- `app/tab_import.py` – GP5/MusicXML-tuonti
- `app/tab_download.py` – GP5/MusicXML-linkin palvelinlataus
- `app/library.py` – kappaleen poisto (MP3 jää)
- `app/pipeline/*` – äänilähde, Demucs, Basic Pitch, tempo, fretboard, export
- `app/static/app.js` – TV-näkymän logiikka
- `app/static/vendor/alphaTab/*` – kolmannen osapuolen alphaTab (MPL-2.0)

> 🔒 **Sääntö #1:** soitto ja tablatuurin kohdistus ovat koskemattomia.
> `app.js`n synkka-/seek-/`mediaHandler`-ketju, transportin DOM-id:t,
> `.alphatab`-mitat ja `/sync|tempo|section`-reitit eivät muutu ilman
> erillistä lupaa. Katso `.clinerules/07-playback-frozen.md`.

## Kerrosrajat

1. Reitit eivät kutsu Demucsia tai Basic Pitchiä suoraan – ne luovat jobin.
2. Putki ei importtaa FastAPIä eikä kirjoita HTTP-vastauksia.
3. Frontend ei käsittele Spotify-client-secretiä. Käytössä on PKCE.
4. Kaikki polut tulevat `app/config.py`:stä; ei absoluuttisia kovakoodauksia.

## Teknologiapino

- Backend: Python 3.11, FastAPI, Uvicorn, SQLite (stdlib), httpx.
- Frontend: vanilla HTML/CSS/JS, alphaTab 1.8.4 vendoroituna.
- Putki: ffmpeg, Demucs `htdemucs_6s`, Basic Pitch, librosa.
- Export: PyGuitarPro (GP5), MusicXML, MIDI.
- **Ei npm-riippuvuuksia eikä build-vaihetta.**

## Käytännöt

1. Kunnioita olemassa olevaa koodia – älä refaktoroi ilman pyyntöä.
2. Pidä muutokset kohdistettuina.
3. `docs/` ja `data/` ovat yksityisiä eivätkä koskaan gitiin.
4. Älä lisää uusia riippuvuuksia ilman perustelua.
5. `origin` = `teppoaland/tabtool` on totuus.
6. Versiot: AI TabTool = `1.x`. Älä käytä GameHubin `10.x`-sarjaa.
7. **Yksi toiminto kerrallaan:** kappaletta joko lisätään, säädetään tai
   soitetaan. Palvelin estää päällekkäisyyden (409) eikä UI tarjoa sitä.
