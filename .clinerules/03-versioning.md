# 📋 Versionhallinta

## Versiosarja

- **AI TabTool = `1.x`**. Aloitus `v1.00`.
- Älä käytä GameHubin `10.x`- tai AI CHAOS STREETin `11.x`-numeroita.

## Nykyinen versio

`v2.30` – `app/__init__.py`:n `__version__`, `app/static/index.html`:n
`#version-tag` ja kaikki `?v=`-leimat. **Palautuspiste: tagi `v2.23`**
(25.10.2026, “hyvä paketti”), vanhempi tagi `v1.99` (23.10.2026).
`v1.23–v2.30` on **pushattu** `origin/main`iin 14.11.2026 (`77ee79f`);
työpuu clean. `v2.29` (SANAT fullscreen) ja `v2.30` (ESIKATSELU) on
kuitattu PC:llä; Android/puhelinpuoli pianosta on vielä testaamatta.

**PianoCapture** (`piano/`) on erillinen app samassa repossa ja käyttää
**omaa `1.x`-versiosarjaa**: ensimmäinen release **`1.00`** (15.11.2026).
Se ei vaikuta TabToolin versionumeroon eikä soittoketjuun. Jatkossa
**+0.01 jokaisesta muutoksesta** (1.01, 1.02…), kuten muissakin omissa
ohjelmissa. Avoin temposkartta-/loppuvartijakorjaus on siirretty versioon
**v2.31** (`memory-bank/progress.md`, "Seuraavaksi").

## Milloin +0.01

Nosta versiota **aina kun ajettava koodi muuttuu**:

- `app/*.py`, `app/pipeline/*.py`
- `app/static/*.html`, `*.css`, `*.js`
- `piano/*.py`, `piano/static/*.html`, `*.css`, `*.js` (PianoCapture:
  sama +0.01-periaate, myös UI-tekstistä)
- `requirements*.txt`, `pytest.ini`, `*.bat`
- rakenteellinen refaktorointi, vaikka toiminta pysyisi samana

## Milloin ei

- vain README, CHANGELOG, LICENSE, THIRD_PARTY_NOTICES
- `docs/`, `data/`, testidata
- pelkkä tekstin tai parametrin säätö ilman koodimuutosta

## Työnkulku

1. Tee muutokset ja jätä ne työpuuhun.
2. Jos koodi muuttui: päivitä `__version__`, `#version-tag` ja kaikki
   `?v=`-leimat samaan numeroon.
3. **Commit = paikallinen tallennus**:
   `git add -A && git commit -m "vNN.NN: …"`.
4. **Push = julkaisu.** Projektia ei vielä julkaista: **älä pushaa**
   `origin`iin ilman käyttäjän erillistä pyyntöä. Lokaalit commitit
   riittävät palautuspisteiksi (`git revert`, `git reset`).
5. **Palvelin.** Uvicorn ei käytä `--reload`ia, joten koodimuutoksen
   jälkeen palvelin pitää käynnistää uudelleen. `start.bat` tekee sen
   yhdellä ajolla: se pysäyttää vanhan instanssin (vain
   Python/uvicorn-prosessin) ja käynnistää uuden. **Agentti saa ajaa oman
   instanssin** (päivitetty 1.11.2026): oma portti (esim. 8011),
   hallittu taustatyö, ei koskaan käyttäjän instanssia portilla 8000 eikä
   `stop.bat`ia. Oma instanssi suljetaan, kun mittaus on tehty, ja
   kerrotaan mitä porttia käytettiin. Jos portilla 8000 on vieras prosessi,
   se ei ole agentin ongelma.
6. **Kuuntelu-/tabsynkkitesti on käyttäjän.** Agentti voi ajaa palvelimen
   ja mitata itse (lokit, API, debug-lukemat), mutta synkan hyväksyy
   edelleen käyttäjä kuuntelemalla.
   Cline ei julista synkkaa toimivaksi ilman kuittausta; portti ja
   testiohje: `.clinerules/07-playback-frozen.md`.
6. Raportoi lyhyesti: mitä muuttui + versionumero.

## Testit ennen committia

```
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m compileall -q app piano
node --check app\static\app.js
node --check app\static\remote.js
node --check piano\static\piano.js
```
