# 🎸 AI TabTool

AI TabTool on lokaali web-palvelu kitaratablatuurien hakuun, generointiin
ja katseluun. Hae kappale Spotifysta tai käytä omaa MP3/YouTube-audioita,
anna tekoälyn tehdä ensimmäinen tablatuuriluonnos ja katsele sitä
alphaTabilla TV:stä tai tietokoneelta. Puhelin toimii kaukosäätimenä.

**Versio:** `v2.16` (Phase 4 – LAN-kaukosäädin, Settings, kirjaston Tiedot, sormitusversiot ja sanat sidecarina)

## Session aloitus

Sano Cline:lle **`lue membank`**. Se lukee `memory-bank/*.md`- ja
`.clinerules/*`-tiedostot, tarkistaa git-tilan ja ajaa testit. Sen
jälkeen voit antaa tehtävän suoraan.

---

## Mikä tämä on

AI TabTool yhdistää:

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

`start.bat` käynnistää palvelimen ja avaa oletusselaimen automaattisesti,
kun `/api/health` vastaa (ei kiinteää viivettä). Jos palvelin on jo
käynnissä, `start.bat` pysäyttää vanhan instanssin ja käynnistää sen
uudelleen – yksi kaksoisklikkaus riittää koodimuutoksen jälkeen. Sulje
ikkuna tai paina `Ctrl+C` lopettaaksesi. Automaattiavauksen voi ohittaa
asettamalla `TABTOOL_NO_BROWSER=1`.

`stop.bat` pysäyttää portin 8000 palvelimen (myös taustalle jääneen
uvicorn-prosessin) ja `status.bat` näyttää portin tilan sekä
`/api/version`-vastauksen. `start.bat` ei tapa vierasta prosessia: jos
portilla 8000 kuuntelee muu kuin Python/uvicorn, se kertoo siitä eikä
käynnistä toista instanssia.

Avaa tarvittaessa käsin:

- TV/näkymä: <http://127.0.0.1:8000>
- Kaukosäädin + QR: <http://127.0.0.1:8000/remote>
- API-dokumentaatio: <http://127.0.0.1:8000/docs>

### Puhelin kaukosäätimenä (sisäverkko)

`start.bat` on ainoa käynnistin: se sitoo palvelimen `0.0.0.0:8000`:aan,
joten sekä tämä kone että puhelin samassa verkossa voivat yhdistää.
Se tulostaa koneen LAN-osoitteet.

1. Avaa koneella <http://127.0.0.1:8000/remote> → sivun oikeassa
   yläkulmassa on **150 × 150 px QR-koodi** ja sen alla osoite
   `http://192.168.1.44:8000/remote`.
2. Skannaa QR puhelimen kameralla → puhelin avaa saman sivun LAN-osoitteesta.
3. Pidä TV-näkymä auki tietokoneella (<http://127.0.0.1:8000>). **Avaa
   `/remote` erilliseen välilehteen** – jos korvaat TV-välilehden sillä,
   PLAY ei tee mitään, koska mikään sivu ei enää toista audiota.
4. Puhelin ohjaa kolmessa tilassa – **yksi toiminto kerrallaan**:
   - **SOITA:** soitinten valinta, PLAY/PAUSE, « (alkuun), toistokohta,
     Nopeus ja kirjastovalinta.
   - **LISÄÄ:** YouTube-linkki ja valinnainen GP5-linkki tai GP5-tiedosto
     puhelimesta → GENERATE TAB. Työn vaiheet ja edistyminen näkyvät;
     valmis tabi ilmestyy kirjastoon (ei automaattista toistoa).
   - **SÄÄDÄ:** nimi, viritys, lukitus ja arkistointi.
   Lisäys on estetty soiton aikana ja soitto tabin luonnin aikana (myös
   palvelin vastaa 409:llä). Toisto tapahtuu tietokoneen omasta
   audiotiedostosta; puhelin ei toista eikä lataa audiota.
   **v2.02:** SOITA/LISÄÄ/SÄÄDÄ-painikkeet ovat sivun alaosassa ja niiden
   paikalla ovat avoimen tabin **soittimet** (esim. neljä kitaraa ja basso).
   Soittimen napautus näyttää tai piilottaa sen raidan TV:n tablatuurista
   myös kesken toiston; valinta tallentuu kuten TV:ssä.

IP-osoite ei ole kiinteä: QR generoidaan pyydettäessä sen hetkisestä
osoitteesta, joten reitittimen DHCP ei haittaa. `TABTOOL_LAN_IP` voi
kiinnittää QR-koodin osoitteen (VPN / useita verkkokortteja) ja
`scripts\lan_addresses.ps1` listaa ne.

**Valinnainen LAN-PIN:** aseta `.env`iin `TABTOOL_LAN_PIN=1234` ja
käynnistä uudelleen. Silloin muut kuin localhost-yhteydet vaativat PINin,
mutta QR-pariutus kirjaa puhelimen sisään ilman PINin kirjoittamista.
Ilman PINiä kuka tahansa samassa verkossa voi ohjata sovellusta.

Windowsin palomuuri: salli portti 8000 **yksityisessä** verkossa, jos
puhelin ei saa yhteyttä. `stop.bat` pysäyttää palvelimen.

### Settings-näkymä (v2.02)

Yläpalkin **SETTINGS** (REMOTE- ja API-linkkien jälkeen) avaa `/settings`.
Arvot tallennetaan SQLite-kantaan, joten ne ovat yhteisiä kaikille laitteille;
jokaisen kentän alla näkyy oletus ja **OLETUS**-napilla arvon voi palauttaa.
TALLENNA kirjoittaa arvot palvelimelle (rajat ja tyypit validoi
`app/settings.py`).

- **Toisto:** lähtölaskennan askelmat (1–12), askeleen kesto (200–3000 ms) ja
  nollan kesto (0–2000 ms) sekä lähtölaskenta oletuksena päälle/pois.
  Oletukset ovat samat kuin ennen: 5 askelta × 1000 ms + 250 ms.
- **Sanat:** soiton aikana näkyvän sanoitusrivin koko (100–400 %, askel 25 %,
  oletus **200 %** = tuplat aiemmasta) ja **nosto** koko näytön tilassa
  (0–600 px, askel 10, oletus **100 px**). Sama kerroin toimii myös koko
  näytön tilassa; 100 % palauttaa vanhan koon ja nosto 0 px laskee rivin
  takaisin alareunaan.
- **Näkymä:** Näkymän oletus (Tab / Auto / Tab + nuotit / Nuotit) uudelle
  selaimelle; TV-näkymän oma valinta ohittaa sen.
- **Toiminnot näkyvissä:** jokainen päänäkymän toiminto (LIBRARY, REMOTE, API,
  FULLSCREEN, COUNT-IN-kytkin, Näkymä, raidat, VALITSE TÄMÄ, LIITÄ AUDIO,
  TEE TAB TÄSTÄ, Nopeus, SYNC, SIIRTO, KOHDISTA, TAB BPM, EXPORT) voidaan
  piilottaa. Oletus on, että kaikki näkyvät.
- **Puhelin (REMOTE):** LISÄÄ- ja SÄÄDÄ-välilehdet, Nopeussäädin ja
  soitinten valinta.

Asetukset eivät vaikuta soittoketjuun: ne luetaan sivun latauksessa ja
lähtölaskenta lukee kestonsa omassa lohkossaan (`.clinerules/07-playback-frozen.md`).

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
node --check app\static\remote-bridge.js
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
   paikallista audiota ja kursori seuraa tahtia 50 ms synkalla. `PLAY` on
   pelkkä toisto (v2.05): se ei avaa koko näyttöä vaan vaihtuu soiton ajaksi
   `PAUSE`ksi; koko näyttö otetaan `FULLSCREEN`-painikkeesta. Kirjasto
   avataan yläpalkin oranssista `LIBRARY`-painikkeesta.
6. `EXPORT` lataa GP5-, MusicXML- ja MIDI-tiedostot.
7. Kirjasto listaa aiemmat tabit; myös CLI:llä tehdyt
   `data/tabs/<nimi>/`-tabit (joissa on `meta.json`) rekisteröityvät
   automaattisesti. Suora linkki: `/?tab=<tab_id>`.

**Sormitusversiot (V1/V2/V3, v1.72 / v2.04):** AI-tabi generoidaan kolmella
otelautaprofiililla – **V1 · Avoimet kielet**, **V2 · Boksi** ja
**V3 · Vähän liikettä**. Sävelet ja rytmit ovat kaikissa samat, vain
kielten/nauhojen sijoittelu vaihtelee. Raitavalinnalla voi kuunnella ja
vertailla; kun yksi versio tuntuu oikealta, valitse vain se näkyviin ja paina
**VALITSE TÄMÄ**. Valinta kysytään varmistusdialogissa, ja ennen kirjoitusta
kaikki versiot varmuuskopioidaan `data/backups/variant-<tab_id>/`iin.
Virhevalinnan voi perua painikkeella **PALAUTA VERSIOT**, joka tuo V1/V2/V3
takaisin (myös TAB BPM säilyy).

**Kirjaston Tiedot (v2.03):** kirjastorivin **Tiedot** avaa modaalin, jossa
voi korjata **esittäjän**, kappaleen nimen ja virityksen sekä lukita tai
arkistoida tabin. Esittäjän ylikirjoitus (`artist_override`) tarvitaan,
koska YouTube-latauksen esittäjäksi tulee helposti kanava/uploader (esim.
`Knight Rydazz`), ei artisti. Samassa ikkunassa näkyvät vain luku -tietoina
BPM, tahtien ja nuottien määrä, YouTube-kanava, lisäysaika sekä
**Audiolähde**- ja **Tablähde**-rivit: mistä YouTube-linkistä audio
ladattiin ja mistä GP-linkistä tai tiedostosta tabi tuotiin. Tyhjä esittäjä
palauttaa tiedostosta luetun esittäjän; lukittu tabi on vain luku -tilassa,
kunnes lukitus avataan samasta ikkunasta.

Valmis referenssitabi: valitse **LIBRARY**-modaalista **GP5-linkki** tai
**GP-tiedosto** (GP3/GP4/GP5/MusicXML; GP3/GP4 muunnetaan GP5:ksi).
Tabi avautuu suoraan katselimeen. Jos samannimisestä
kappaleesta on AI-tabi, paina **LIITÄ AUDIO**: tabi saa audion, PLAYn,
aikajanan ja cursorin. **TAB BPM** -kenttään asetetaan kappaleen
todellinen tempo ja painetaan **TALLENNA** – pelkkä kirjoitus ei tallennu.
Kenttä, syöte ja nappi muuttuvat punaisiksi, kun arvo on tallentamatta.
TALLENNA päivittää GP5:n tempon ja pitää audion 100 %:ssa.

**Desimaalitempo:** GP5 tallentaa tempon kokonaislukuna, joten kenttä
hyväksyy desimaalit (esim. `143,5`). Desimaaliosa toteutetaan toiston
hienosäätönä, jolloin tabi ei jää jälkeen eikä edistä: esim. Seek &
Destroyn mitattu tempo on ~143,55 BPM, joten arvo `143,55` osuu
kohdalleen, vaikka GP5:ssä lukee 144. **Nopeus**-säätimellä (50–150 %)
hidastetaan tai nopeutetaan toistoa harjoittelua varten; tabi seuraa
mukana.

**SYNC**-säätimellä (±10 %, askel 0,05 %) kohdistetaan tabi kappaleeseen:
`+` siirtää tabia eteenpäin ja `-` taaksepäin. Arvo tallennetaan tabin
`meta.json`iin (`sync_drift`), joten kerran tehty korjaus on mukana aina
tabia avattaessa. SYNC ei muuta GP5-tiedostoa eikä audiota.

**SIIRTO (tahtia)** siirtää tabia tahdeilla (−999…+999, 0,25 tahdin
askel = 1 isku 4/4:ssä). Käytä sitä, kun tabi ja kappale ovat
vakiomäärän iskuja eri kohdassa: esim. `-1,5` = tabi on 6 iskua edellä,
`+1,5` = 6 iskua jäljessä. Iso siirto (kymmeniä tahteja) on tarkoitettu
rakenne-eroon: tabin toistot ja levytys eivät vastaa toisiaan.
Prosenttisäätö ei korjaa tällaista vakiosiirtoa. Arvo tallentuu tabille
(`sync_offset_bars`) ja pysyy mukana.

**Count-in:** tabin ensimmäinen PLAY näyttää **5 → 0** -laskennan
soittonäkymässä ennen kuin ääni alkaa. Laskenta on pelkkä overlay: se ei
kirjoita audiota, ei kutsu alphaTabia eikä muuta kohdistusta. Toinen PLAY
tai Esc peruu laskennan (seuraava PLAY yrittää uudelleen), tauon jälkeen
toisto jatkuu ilman laskentaa, ja jos siirrät kohdistinta ennen
ensimmäistä PLAYta, laskenta ohitetaan. **FULLSCREEN-napin alla on
COUNT-IN-kytkin (ON/OFF, oletus ON)** sekä normaalissa että koko näytön
näkymässä; valinta muistetaan selaimessa. Kytkin luetaan vain
`shouldRunCountIn`issa – se ei koske soittoketjuun.

**Sanat (v2.06–v2.12):** katselimen **SANAT** avaa **kelluvan** editorin, jota
voi raahata otsikkorivista, jonka kokoa voi muuttaa **kummasta nurkasta
tahansa** (vasen yläkulma tai oikea alakulma) ja joka pysyy aina
päällimmäisenä. Sijainti ja koko muistetaan selaimessa. Koska taustalla ei ole
verhoa, soitto, seek ja kursorin seuraaminen toimivat paneelin takaa: sanat voi
asettaa kuuntelemalla. Editorissa on samat perustoiminnot kuin
kaukosäätimessä – **PLAY/PAUSE**, **«**, **−5 s** ja **+5 s** – ja
**tahtinumeron klikkaus hyppää siihen tahtiin** (soitto, tabi ja kursori) –
myös tablatuureissa, joissa on tempo-automaatioita, koska hyppy käyttää
alphaTabin tempokarttaa tick-seekin kautta.
Kaksoisklikkaus tahtinumerossa aloittaa rivin `tahti | `. Tahtilista on
oletuksena korkea, ja sen ja sanoituskentän välissä on **jakokahva**: kun
lista kasvaa, tekstikenttä pienenee – näin 258 tahdin kappale pysyy
hallittavana. Jako muistetaan selaimessa. Otsikossa näkyy kuluvan tahdin numero
ja tahtilista korostaa saman tahdin, joten rivin paikka on helppo tarkistaa.
Jokainen rivi on muotoa `tahti | teksti` (esim. `10 | Ensimmäinen rivi`); tahdin
voi kirjoittaa käsin tai klikata tahtilistasta. Ilman tahtinumeroa oleva rivi
jatkaa edellisestä tahdista. Sanat tallennetaan **erilliseen** tiedostoon
`data/lyrics/<tab_id>.json` – GP5/MusicXML/MIDI ja tabin metadata eivät muutu,
joten tabi pysyy lukusyötteenä eikä soitto- tai synkkaketjuun kosketa.
Soiton aikana näkyvän rivin kokoa säädetään **SETTINGS → Sanat**
(100–400 %, oletus 200 %) ja koko näytön nostoa alareunasta
(0–600 px, oletus 100 px). Koko näytön tilassa rivi käyttää 96 % leveydestä,
joten se pysyy yhdellä rivillä isommallakin koolla. Rivin tausta on **täysin
musta** ja tekstin molemmin puolin on kolme merkin levyinen tyhjä tila, joten
rivi on helppo lukea liikkuvan tabin päältä.

**Vihje:** älä raahaa hiirellä tabin yli – se saattoi aiemmin luoda
alphaTabin loop-alueen. Nykyään alue nollataan automaattisesti, mutta
klikkaaminen riittää siirtämiseen.

Pätkägenerointi: siirry katselimessa kohtaan, valitse **30/60/120 s** ja
paina **TEE TAB TÄSTÄ**. Ohjelma tekee uuden tabin vain siitä pätkästä
samoilla asetuksilla ja avaa sen; nimi sisältää aikavälin.

Jobit, cache ja tabimetadata ovat SQLitessä (`data/tabtool.sqlite3`).
Sama audio + samat asetukset palauttaa cachesta saman tabin; vain
`regenerate`-pyyntö kirjoittaa uuden.

### API

| Reitti | Kuvaus |
|---|---|
| `POST /api/jobs` | multipart: `file` tai `youtube_url` (+ `options` JSON) |
| `GET /api/jobs`, `GET /api/jobs/{id}` | job-lista ja tila |
| `GET /api/jobs/{id}/events` | SSE-progress |
| `POST /api/tabs/import` | GP3/GP4/GP5/MusicXML-tabin tuonti (GP3/GP4 → GP5) |
| `POST /api/tabs/{id}/section` | pätkäjobin luonti tabin audiosta |
| `POST /api/tabs/{id}/attach-audio` | samannimisen tabin audion liitys |
| `POST /api/tabs/{id}/tempo` | GP5-tabin BPM:n korjaus |
| `POST /api/tabs/{id}/sync` | manuaalinen tabin kohdistus (`sync_drift`) |
| `GET /api/tabs`, `GET /api/tabs/{id}` | kirjasto ja tab-metadata |
| `GET /api/tabs/{id}/score/{gp5\|musicxml\|midi}` | inline score alphaTabille |
| `GET /api/tabs/{id}/export/{gp5\|musicxml\|midi}` | lataus (attachment) |
| `GET /api/tabs/{id}/audio` | WAV-stream Range-tuella |

---

## Ulkoinen arkisto (`D:\tabtool_files`)

Ulkoinen sisältö mirroroidaan luettavalla nimellä, jotta samat tiedostot
löytyvät helposti muuhunkin käyttöön:

- `D:\tabtool_files\audio\` – YouTube-lataukset (`Artist - Title.wav`)
- `D:\tabtool_files\audio\mp3\<Artisti>\` – kuunteluversiot
  (`Artist - Title.mp3`, ffmpeg + libmp3lame VBR ~190 kbps)
- `D:\tabtool_files\tabs\` – tuodut tabit (`Artist - Title.gp5`/`.musicxml`)

MP3 tehdään YouTube-latauksista (ei pätkäklipistä eikä omasta uploadista),
joten bändin biisit löytyvät artistikansioista esim. autoon tai
harjoituksiin.

Samalla levyasemalla käytetään **hard linkiä**, joten tiedosto ei vie
ylimääräistä levytilaa ja näkyy molemmissa hakemistoissa. `data/` pysyy
totuuden lähteenä; arkistointi ei koskaan kaada jobia. Pätkägeneroinnin
klipit jätetään arkistoimatta (nimi ei kuvaisi koko kappaletta).

Polun voi vaihtaa `.env`-tiedostossa:

```env
TABTOOL_EXTERNAL_DIR=D:\tabtool_files
```

Olemassa olevan kirjaston voi arkistoida kertaalleen:

```powershell
.venv\Scripts\python.exe scripts\backfill_external.py
```

Vanhojen tabien lähdelinkit voi täydentää jälkikäteen (v2.03):

```powershell
.venv\Scripts\python.exe scripts\backfill_source_url.py --dry-run
.venv\Scripts\python.exe scripts\backfill_source_url.py
```

---

## Oma tuontikirjasto ja bulk-export (v1.66)

Valmiit GP3/GP4/GP5- ja MusicXML-tabit voi tuoda **kansiosta kerralla** ja
viedä ulos samoilla formaateilla. Tiedostot pysyvät yksityisinä:
`data/`, `library/` ja `D:\tabtool_files\` ovat gitignoroituja, joten
tuotu sisältö ei mene julkiseen repoon.

```powershell
# 1) Tuo kaikki tabit kansiosta (myös alikansiot)
.venv\Scripts\python.exe scripts\import_folder.py "D:\tabtool_files\imports"

# uudelleentuonti (ohittaa .tabtool-imported.json -manifestin)
.venv\Scripts\python.exe scripts\import_folder.py "D:\tabtool_files\imports" --force

# 2) Vie koko kirjasto GP5/MusicXML/MIDI-muodossa + manifest.json + ZIP
.venv\Scripts\python.exe scripts\export_tabs.py "D:\tabtool_files\exports" --zip

# vain osa formaateista / tietyt tabit
.venv\Scripts\python.exe scripts\export_tabs.py "D:\tabtool_files\exports" --formats gp5 --ids <tab_id>
```

Tuoja kirjoittaa lähdekansioon `.tabtool-imported.json`-manifestin
(SHA-256 → tab_id), joten samaa tiedostoa ei tuoda kahdesti. Export
nimeää tiedostot muotoon `Artisti - Kappale.gp5` ja kirjoittaa
`manifest.json`iin tunnisteet, BPM:n ja tahtimäärän.

Puhelimesta voi hakea **itse lataamasi** GP/MusicXML-tiedostot
(`/sdcard/Download`) suoraan tuontikansioon – appien yksityiseen dataan
skripti ei koske:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\adb_pull_gp.ps1
.venv\Scripts\python.exe scripts\import_folder.py "D:\tabtool_files\imports"
```

### Toiston kirjoittaminen auki (v1.76)

Katselimen kello laskee partituurin keston **kirjoitetuista** tahdeista
(`scoreEndTimeMs`). alphaTab laajentaa toistot vasta toistossa, joten GP5:n
`×17`-toistomerkintä jätti partituurin 15 tahtia lyhyemmäksi eikä SIIRTO
voinut korjata sitä. `scripts/expand_repeat.py` kirjoittaa toistetun tahdin
tahdeiksi, poistaa toistomerkit ja numeroi loput tahdit uudelleen – tabi ja
audio ovat silloin 1:1.

```powershell
# tarkista ensin (ei kirjoita mitään)
.venv\Scripts\python.exe scripts\expand_repeat.py --tab <tab_id> --bar 2 --times 17 --dry-run

# kirjoita: alkuperäinen varmuuskopioidaan data/backups/<id>-<aika>/
.venv\Scripts\python.exe scripts\expand_repeat.py --tab <tab_id> --bar 2 --times 17 --reset-sync
```

`--reset-sync` nollaa SYNC- ja SIIRTO-arvot, koska tabi vastaa nyt audiota.
Skripti validoi tuloksen lukemalla GP5:n takaisin ja palauttaa
varmuuskopion, jos kirjoitus epäonnistuu.

### Ylimääräisten tahtien poisto (v1.77)

Jos tabin häntä jatkuu audion yli (kursori jatkaa soittamisen jälkeen),
ylimääräiset tahdit voi poistaa. Tahdit annetaan 1-pohjaisina, kaikilta
raidoilta, ja loput numeroidaan uudelleen:

```powershell
# tarkista ensin
.venv\Scripts\python.exe scripts\trim_bars.py --tab <tab_id> --bars 137,138 --dry-run

# poista (varmuuskopio data/backups/<id>-<aika>/)
.venv\Scripts\python.exe scripts\trim_bars.py --tab <tab_id> --bars 137,138 --reset-sync
```

Väli käy muodossa `136-138`. `--reset-sync` nollaa SYNC- ja SIIRTO-arvot.

### Virityksen vaihto niin, että musiikki pysyy samana (v1.80)

Jos tabi on kirjoitettu eri viritykseen kuin oma kitara, skripti vaihtaa
kitararaitojen avoimet kielet ja siirtää nauhat vastaavasti – sävelet pysyvät
identtisinä, soitto-ohje vain siirtyy oikeisiin asemiin:

```powershell
# tarkista ensin: montako raitaa/nuottia ja mikä on suurin nauha
.venv\Scripts\python.exe scripts\retune_tab.py --tab <tab_id> --from drop_d --to d_standard --dry-run

# vaihda (varmuuskopio data/backups/, sävelet validoidaan ennen/jälkeen)
.venv\Scripts\python.exe scripts\retune_tab.py --tab <tab_id> --from drop_d --to d_standard --clear-override
```

Viritysavaimet: `standard`, `drop_d`, `eb_standard`, `d_standard`, `open_g`.
Vain raidat, joiden avoimet kielet täsmäävät `--from`-viritykseen, muutetaan
(laulu-, basso- ja rumpuraidat jäävät ennalleen). `--clear-override` poistaa
manuaalisen viritystiedon, koska data on nyt oikeasti uudessa virityksessä.

---

## Spotify-asetukset (Phase 3)

1. Luo Spotify Developer Dashboardissa app nimeltä `AI TabTool`.
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

## Nimi ja tavaramerkit

**AI TabTool** on tämän projektin tuotenimi. Repo/hakemisto `tabtool` on
vain tekninen nimi, samoin sisäiset tunnisteet: `TABTOOL_*`-ympäristö-
muuttujat ja `data/tabtool.sqlite3`.

Projekti ei ole sidoksissa tabtool GmbH:hen (tabtool.de) eikä SEYDEL
TabTooliin. Nimi on tarkoitettu henkilökohtaiseen, paikalliseen käyttöön;
ennen laajempaa jakelua tai kaupallistamista nimi kannattaa tarkistaa
tavaramerkkirekistereistä (PRH, EUIPO, WIPO, USPTO).

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
├─ settings.py      /api/settings: oletukset, rajat ja tallennus
├─ jobs.py          job-jono, worker, cache, SSE-eventit
├─ external_store.py  YouTube-audion ja tuotujen tabien arkistointi
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
- **v1.22** ✅ – tuotenimi **AI TabTool** (repo pysyy `tabtool`)
- **v1.23** ✅ – katselu: tab-only-oletus, raitavalinnat, fullscreen, cursor
- **v1.24** ✅ – seuranta: edellinen rivi näkyy, dynamiikkamerkinnät pois
- **v1.25** ✅ – metatiedot ja aikajana: oikea nimi, tahti- ja aikasiirtymät
- **v1.26** ✅ – GP5/MusicXML-referenssitabin tuonti UI:sta
- **v1.27** ✅ – pätkägenerointi: TEE TAB TÄSTÄ ja aikaväli tabin nimessä
- **v1.28** ✅ – referenssitabin audio, PLAY ja Nopeus-synkka
- **v1.29** ✅ – TAB BPM -korjaus ja tarkempi Nopeus-hienosäätö
- **v1.30** ✅ – manuaalinen SYNC-kohdistus (tallentuu tabille), Nopeus 50–150 %
- **v1.31** ✅ – TALLENNA-nappi ja punainen muistutus tallentamattomasta BPM:stä
- **v1.32** ✅ – ulkoinen arkisto `D:\tabtool_files` (YouTube-audio + tuodut tabit)
- **v1.33** ✅ – MP3-kuunteluversiot artistikansioihin + seek-synkin vakaunnus
- **v1.34** ✅ – desimaali-TAB BPM (esim. 143,55) GP5:n kokonaislukutemposta huolimatta
- **v1.35** ✅ – SIIRTO (tahtia): rakenne-eron korjaus tabille tallentuen
- **v1.54** ✅ – palvelimen hallinta: stop.bat, status.bat, start.bat ei käynnistä toista instanssia
- **v1.53** ✅ – count-in poistettu; soitto 1:1 (v1.48:n play-polku palautettu)
- **v1.52** ✅ – korjaus: soitto ja tablatuuri synkissä (SIIRTO-inversio myös alphaTabin seekeille)
- **v1.51** ✅ – count-in vain kerran alussa ja erillään soitosta (SIIRTO-seek-muutos kumottu v1.52:ssa)
- **v1.50** ✅ – korjaus: tabinäkymä ei enää leviä oikealle (viewer-stage min-width)
- **v1.49** ✅ – tumma tabinäkymä oletuksena, LIBRARY-napit, 5 s count-in ennen toistoa
- **v1.48** ✅ – klikkaus-seek kohdistaa oikein SIIRTO/SYNC/BPM huomioiden (ei koske toistoa)
- **v1.47** ✅ – osoitin ei enää "juokse" edellä: animoitu beat-kursori pois käytöstä
- **v1.46** ✅ – kohdistusavustin: live-offset-näyttö + KOHDISTA-klikkaus (tallentaa SIIRTO-arvon)
- **v1.45** ✅ – kursorin synkka: partituurin kesto master bar -tikeistä (api.endTime oli 0 ennen toistoa)
- **v1.44** ✅ – kursorin synkka: `api.endTime`-lähde, selainpuolinen korjaus (Ctrl+F5)
- **v1.43** ✅ – kursorin synkka: backing track -venytys pois, osoitin äänen tahdissa
- **v1.42** ✅ – testiyhteenveto näkyviin (`pytest.ini`), sessioalustuksen tulosteet kapeaan konsoliin
- **v1.41** ✅ – GP3/GP4-tuonti (konversio GP5:ksi), audiopolun rescan-korjaus
- **v2.04** ✅ – VALITSE TÄMÄ kysyy varmistuksen, varmuuskopioi versiot ja PALAUTA VERSIOT peruu valinnan
- **v2.03** ✅ – kirjaston Tiedot-modali: esittäjän korjaus, lähdelinkit (YouTube/GP) ja metadata; puhelimen SÄÄDÄ saa esittäjän
- **v2.02** ✅ – Settings-näkymä: count-inin kesto, näkymän oletus, toiminnot näkyviin/piiloon; puhelimen soitinvalinnat ja painikkeet sivun alaosaan
- **v2.01** ✅ – kirjastot bändin nimellä, remote yksi scrollbar
- **v1.83** ✅ – yksi `start.bat` (LAN aina), 150 px QR `/remote`-sivulla
- **v1.82** ✅ – LAN-kaukosäädin: QR-pariutus, valinnainen LAN-PIN
- **v1.36** – Spotify-haku, OAuth, SDK/Connect-synkka
- **1.x** – basso, laulu, rummut, bending

---

## Rajoitukset

- AI-transkriptio on luonnos: akordit, särö, päällekkäiset kitarat ja
  nopeat soolot tuottavat virheitä.
- CPU-only: kappaleen käsittely voi kestää useita minuutteja.
- Rummut vaativat oman transkriptiomallin (ei vielä).
- Tempo- tai tahtilajimuutokset voivat vaatia manuaalista BPM/offset-
  säätöä. Beat trackerin half/double-time tulkinta normalisoidaan
  70–180 BPM -alueelle. SYNC-korjaus vaikuttaa vain katseluun; vietävä
  GP5 säilyttää alkuperäisen tempon.
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
