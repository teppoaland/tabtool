# 🎸 TABTOOL

Lokaali web-palvelu kitaratablatuurien hakuun, generointiin ja katseluun.
Hae kappale Spotifysta tai käytä omaa MP3/YouTube-audioita, anna tekoälyn
tehdä ensimmäinen tablatuuriluonnos ja katsele sitä alphaTabilla TV:stä
tai tietokoneelta. Puhelin toimii kaukosäätimenä.

**Versio:** `v1.00` (Phase 0 – runko)

---

## Mikä tämä on

TabTool yhdistää:

- **Spotify** – haku, metadata ja valinnainen toisto
- **oma MP3 / YouTube** – tab-generoinnin ja taustatoiston audiolähde
- **Demucs** – stemmien erottelu (`htdemucs_6s`)
- **Basic Pitch** – audio-to-MIDI -transkriptio
- **alphaTab** – interaktiivinen tablatuurinäkymä selaimessa
- **FastAPI + SQLite** – lokaali backend, jobit ja cache

### Tärkeä periaate: local-first audio

Spotify ei anna raakaa audiota (DRM), joten tab-generointi tehdään aina
paikallisesta tiedostosta tai yt-dlp:llä ladatusta audiosta. **Toisto
tapahtuu samasta tiedostosta**, jolloin tabi ja tausta ovat täsmälleen
samassa tahdissa. Spotify-toistoa voidaan käyttää vain, jos kyseessä on
sama äänite; muuten käytetään paikallista audiota.

YouTube-mainokset eivät tule mukaan, koska yt-dlp lataa audiostreamin
eikä YouTube-soitinta käytetä.

---

## Vaatimukset

- Windows 10/11
- Python 3.11
- ffmpeg (PATH:ssa)
- Node.js (vain `node --check`-tarkistuksiin)
- Spotify Premium + Developer Client ID vain Spotify-toistoa varten
- GPU ei ole pakollinen; CPU-only on hidas mutta toimii

---

## Pika-aloitus

```bat
setup.bat
start.bat
```

Avaa selaimessa:

- TV/näkymä: <http://127.0.0.1:8000>
- Kaukosäädin: <http://127.0.0.1:8000/remote>
- API-dokumentaatio: <http://127.0.0.1:8000/docs>

### Manuaalinen asennus

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-dev.txt
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### ML-putken riippuvuudet (Phase 1)

```bat
install-ml.bat
```

Tämä asentaa Demucsin, Basic Pitchin, librosan, music21:n, PyGuitarPron ja
yt-dlp:n. Asennus on useita gigatavuja ja voi kestää kauan.

---

## Testit

```bat
test.bat
```

tai:

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m compileall -q app
node --check app\static\app.js
node --check app\static\remote.js
```

---

## Testikappaleet (Phase 1)

1. **YouTube:** KISS – *I’m A Legend Tonight*
   <https://www.youtube.com/watch?v=lHvfqaDp0zA>
2. **Paikallinen fallback:**
   `C:\Music_mp3\Diablo\Diablo - Mimic47-2006\05 - Mimic 47.mp3`

YouTube-lataus on käyttäjän vastuulla. Jos YouTube estää latauksen,
käytetään paikallista MP3:aa.

---

## Spotify-asetukset (Phase 3)

1. Luo Spotify Developer Dashboardissa app nimeltä `TabTool`.
2. Lisää redirect URI **täsmälleen** muodossa:
   `http://127.0.0.1:8000/auth/callback`
   (`localhost` ei kelpaa; käytä loopback-IP:tä.)
3. Kopioi Client ID `.env`-tiedostoon:

```env
SPOTIFY_CLIENT_ID=your_client_id_here
SPOTIFY_REDIRECT_URI=http://127.0.0.1:8000/auth/callback
```

4. Varmista, että tililläsi on Spotify Premium.
5. Development mode sallii 1 client ID:n ja 5 käyttäjää; oma käyttö on
   sallittua, kaupallinen käyttö ei.

Scopes: `streaming`, `user-read-email`, `user-read-private`,
`user-read-playback-state`, `user-modify-playback-state`,
`user-read-currently-playing`.

---

## Data ja yksityisyys

Nämä hakemistot eivät mene julkiseen gitiin:

- `docs/` – henkilökohtaiset suunnitelmat
- `data/` – audio, stemmit, tabit, SQLite, Spotify-tokenit, lokit
- `.env` – salaisuudet

`data/` on palvelimen yksityinen juuri. Sitä ei koskaan tarjoilla
staattisena hakemistona; tiedostot avataan vain validoitujen API-reittien
kautta.

---

## Rakenne

```
app/
├─ main.py          FastAPI, reitit, static
├─ config.py        polut ja ympäristömuuttujat
├─ static/          TV- ja remote-näkymät
├─ pipeline/        Demucs → Basic Pitch → tab (Phase 1)
└─ ...
tests/              pytest
scripts/            CLI-työkalut
data/               GITIGNORED
docs/               GITIGNORED
.clinerules/        projektin säännöt
```

---

## Tiekartta

- **v1.00** – repo, säännöt, FastAPI-runko, testit
- **v1.10** – putki: Demucs + Basic Pitch + fretboard + GP5/MusicXML
- **v1.20** – web-UI + alphaTab + paikallinen toisto
- **v1.30** – Spotify-haku, OAuth, SDK/Connect-synkka
- **v1.40** – remote-kaukosäädin
- **1.x** – basso, laulu, rummut, kirjasto/import, bending

---

## Rajoitukset

- AI-transkriptio on luonnos: akordit, särö, päällekkäiset kitarat ja
  nopeat soolot tuottavat virheitä.
- CPU-only: kappaleen käsittely voi kestää useita minuutteja.
- Rummut vaativat oman transkriptiomallin (ei v1.0:ssa).
- Tempo- tai tahtilajimuutokset voivat vaatia manuaalista BPM/offset-
  säätöä.
- Spotify-toisto ei ole synkronin oletuslähde; käytä paikallista audiota.

---

## Lisenssi ja kiitokset

Projekti: **All rights reserved** – ks. [LICENSE](LICENSE).

Tämä projekti hyödyntää avoimen lähdekoodin malleja ja kirjastoja:

- Meta / Alexandre Défossez – **Demucs** (stem separation, MIT)
- Spotify – **Basic Pitch** (audio-to-MIDI, Apache-2.0)
- Daniel Kuschny – **alphaTab** (tab rendering, MPL-2.0)
- **PyGuitarPro** (GP3–GP5, LGPL-3.0)
- **FastAPI**, **music21**, **librosa**, **yt-dlp**, **FFmpeg**

Täydellinen luettelo: [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

Generoidut transkriptiot ovat henkilökohtaiseen käyttöön. Älä julkaise
tekijänoikeudella suojattuja tablatuureja ilman lupaa.
