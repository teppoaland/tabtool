# 📋 Versionhallinta

## Versiosarja

- **AI TabTool = `1.x`**. Aloitus `v1.00`.
- Älä käytä GameHubin `10.x`- tai AI CHAOS STREETin `11.x`-numeroita.

## Nykyinen versio

`v1.46` – `app/__init__.py`:n `__version__`, `app/static/index.html`:n
`#version-tag` ja kaikki `?v=`-leimat.

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
5. **Käynnistä palvelin uudelleen koodimuutoksen jälkeen.** Uvicorn ei
   käytä `--reload`ia; muuten selain saa uusista reiteistä
   `404 Not Found` (esim. `/tempo`, `/sync`).
6. Raportoi lyhyesti: mitä muuttui + versionumero.

## Testit ennen committia

```
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m compileall -q app
node --check app\static\app.js
node --check app\static\remote.js
```
