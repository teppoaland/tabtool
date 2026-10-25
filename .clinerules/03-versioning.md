# 📋 Versionhallinta

## Versiosarja

- **AI TabTool = `1.x`**. Aloitus `v1.00`.
- Älä käytä GameHubin `10.x`- tai AI CHAOS STREETin `11.x`-numeroita.

## Nykyinen versio

`v2.21` – `app/__init__.py`:n `__version__`, `app/static/index.html`:n
`#version-tag` ja kaikki `?v=`-leimat. Tagi `v1.99` = vanhempi toimiva
palautuspiste (23.10.2026); v1.23–v2.14 on pushattu `origin/main`iin
25.10.2026.

## Milloin +0.01

Nosta versiota **aina kun ajettava koodi muuttuu**:

- `app/*.py`, `app/pipeline/*.py`
- `app/static/*.html`, `*.css`, `*.js`
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
5. **Palvelin on käyttäjän hallinnassa.** Uvicorn ei käytä `--reload`ia,
   joten koodimuutoksen jälkeen palvelin pitää käynnistää uudelleen.
   `start.bat` tekee sen yhdellä ajolla: se pysäyttää vanhan instanssin
   (vain Python/uvicorn-prosessin) ja käynnistää uuden. Älä käynnistä
   palvelinta taustalle äläkä pysäytä sitä ilman pyyntöä; kerro
   käyttäjälle, että uudelleenkäynnistys tarvitaan. Vierasta prosessia
   portilla 8000 `start.bat` ei tapa – se kertoo siitä ja lopettaa.
6. **Kuuntelu-/tabsynkkitesti on käyttäjän.** Käyttäjä ajaa `start.bat`in
   omassa CMD-ikkunassaan (se sammuttaa ja käynnistää palvelimen) ja
   tarkistaa soiton UI:ssa.
   Cline ei julista synkkaa toimivaksi ilman kuittausta; portti ja
   testiohje: `.clinerules/07-playback-frozen.md`.
6. Raportoi lyhyesti: mitä muuttui + versionumero.

## Testit ennen committia

```
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m compileall -q app
node --check app\static\app.js
node --check app\static\remote.js
```
