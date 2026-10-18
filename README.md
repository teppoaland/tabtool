# 🎸 TABTOOL

Lokaali web-palvelu kitaratablatuurien hakuun, generointiin ja katseluun.
Hae kappale Spotifysta tai käytä omaa MP3/YouTube-audioita, anna tekoälyn
tehdä ensimmäinen tablatuuriluonnos ja katsele sitä alphaTabilla TV:stä
tai tietokoneelta. Puhelin toimii kaukosäätimenä.

**Versio:** `v1.20` (Phase 2 – web-UI, alphaTab ja paikallinen toisto)

## Session aloitus

Sano Cline:lle **`lue membank`**. Se lukee `memory-bank/*.md`- ja
`.clinerules/*`-tiedostot, tarkistaa git-tilan ja ajaa testit. Sen
jälkeen voit antaa tehtävän suoraan.

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

## Putki CLI (Phase 1)

```powershell
# Paikallinen tiedosto
.venv\Scripts\python.exe scripts\pipeline_smoke.py "C:\Music\song.mp3" --title "Song" --artist "Artist"

# YouTube (lataa audiostreamin, ei mainoksia)
.venv\Scripts\python.exe scripts\pipeline_smoke.py "https://youtu.be/..." --clip-seconds 30

# Nopea savutesti ilman stem-erottelua
.venv\Scripts\python.exe scripts\pipeline_smoke.py song.mp3 --no-separation --clip-seconds 20
```

Tulosteet: `data/tabs/<nimi>/tab.gp5`, `tab.musicxml`, `tab.mid` ja
`meta.json`. Hyödylliset valinnat: `--model htdemucs_6s`, `--stem guitar`,
`--tuning standard`, `--bpm 136`, `--start-seconds 60`, `--clip-seconds 30`,
`--no-separation`.

**Phase 1 -validointi (18.10.2026):**
- Paikallinen 3:10 MP3: Demucs 6s + Basic Pitch + fretboard + export
  ~67 sekunnissa CPU:lla.
- 108 tahtia, 884 tab-nuottia; GP5 luettiin uudelleen ilman virheitä.
- YouTube 20 s klipit toimivat; mainokset eivät tule mukaan.

---

## Testikappaleet

1. **YouTube:** KISS – *I’m A Legend Tonight*
   <https://www.youtube.com/watch?v=lHvfqaDp0zA>
2. **Paikallinen fallback:**
   `C:\Music_mp3\Diablo\Diablo - Mimic47-2006\05 - Mimic 47.mp3`

Molemmat on validoitu Phase 1:ssä. YouTube-lataus on käyttäjän vastuulla.
Jos YouTube estää latauksen, käytetään paikallista MP3:aa.

```powershell
.venv\Scripts\python.exe scripts\pipeline_smoke.py "C:\Music_mp3\Diablo\Diablo - Mimic47-2006\05 - Mimic 47.mp3" --title "Mimic 47" --artist "Diablo"
```

---

## Web-käyttö (Phase 2)

1. Käynnistä `start.bat` ja avaa <http://127.0.0.1:8000>.
2. Valitse oma MP3/WAV tai liitä YouTube-linkki.
3. Valitse viritys ja grid. **Nopea tila** ohittaa Demucsin (nopea,
   heikompi laatu). **Generoi uudelleen** ohittaa cachetuloksen.
4. Status-rivi näyttää vaiheet: `Queued` → `Downloading audio…` →
   `Separating stems…` → `Transcribing guitar…` → `Building tab…` →
   `Ready` (tai `Failed` + virhe).
5. Valmis tabi renderöityy alphaTabilla. `PLAY`/`PAUSE` soittaa samaa
   paikallista audiota ja kursori seuraa tahtia 50 ms synkalla.
6. `EXPORT` lataa GP5-, MusicXML- ja MIDI-tiedostot.
7. Kirjasto listaa aiemmat tabit; myös CLI:llä tehdyt
   `data/tabs/<nimi>/`-tabit (joissa on `meta.json`) rekisteröityvät
   automaattisesti. Suora linkki: `/?tab=<tab_id>`.

Jobit, cache ja tabimetadata ovat SQLitessä (`data/tabtool.sqlite3`).
Sama audio + samat asetukset palauttaa cachesta saman tabin; vain
`regenerate`-pyyntö kirjoittaa uuden.

### API

| Reitti | Kuvaus |
|---|---|
| `POST /api/jobs` | multipart: `file` tai `youtube_url` (+ `options` JSON) |
| `GET /api/jobs`, `GET /api/jobs/{id}` | job-lista ja tila |
| `GET /api/jobs/{id}/events` | SSE-progress |
| `GET /api/tabs`, `GET /api/tabs/{id}` | kirjasto ja tab-metadata |
| `GET /api/tabs/{id}/score/{gp5\|musicxml\|midi}` | inline score alphaTabille |
| `GET /api/tabs/{id}/export/{gp5\|musicxml\|midi}` | lataus (attachment) |
| `GET /api/tabs/{id}/audio` | WAV-stream Range-tuella |

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
├─ db.py            SQLite: tracks, jobs, tabs, settings
├─ jobs.py          job-jono, worker, cache, SSE-eventit
├─ static/          TV- ja remote-näkymät
│  └─ vendor/alphaTab/   alphaTab 1.8.4 + Bravura (MPL-2.0 / OFL)
├─ pipeline/        audio_source, separate, transcribe, tempo,
│                   quantize, fretboard, export_gp5/musicxml/midi
└─ ...
tests/              pytest
scripts/            CLI-työkalut
data/               GITIGNORED
docs/               GITIGNORED
.clinerules/        projektin säännöt
```

---

## Tiekartta

- **v1.00** ✅ – repo, säännöt, FastAPI-runko, testit
- **v1.10** ✅ – putki: Demucs + Basic Pitch + fretboard + GP5/MusicXML/MIDI
- **v1.20** ✅ – web-UI: upload/YouTube → job → alphaTab + paikallinen toisto
- **v1.30** – Spotify-haku, OAuth, SDK/Connect-synkka
- **v1.40** – remote-kaukosäädin
- **1.x** – basso, laulu, rummut, bending

---

## Rajoitukset

- AI-transkriptio on luonnos: akordit, särö, päällekkäiset kitarat ja
  nopeat soolot tuottavat virheitä.
- CPU-only: kappaleen käsittely voi kestää useita minuutteja.
- Rummut vaativat oman transkriptiomallin (ei vielä).
- Tempo- tai tahtilajimuutokset voivat vaatia manuaalista BPM/offset-
  säätöä. Beat trackerin half/double-time tulkinta normalisoidaan
  70–180 BPM -alueelle.
- Kielikohtainen monofonia varmistetaan: päällekkäinen nuotti siirretään
  vapaalle kielelle tai edellistä nuottia lyhennetään.
- Standard E -viritykseen kuulumattomat nuotit pudotetaan varoituksella.
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
