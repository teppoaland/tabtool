# 🧠 Memory bank -protokolla

## Trigger

Kun käyttäjä sanoo **`lue membank`**, **`lue memory bank`**, **`alusta sessio`**
tai **`aloita uusi sessio`**, tee alla oleva järjestyksessä. Älä kysy
lisäkysymyksiä, ellei jokin tiedosto puutu.

## 1. Lue

1. `memory-bank/projectBrief.md`
2. `memory-bank/systemPatterns.md`
3. `memory-bank/techContext.md`
4. `memory-bank/activeContext.md`
5. `memory-bank/progress.md`
6. `.clinerules/*.md` (kaikki)

## 2. Tarkista tila

```powershell
git --no-pager status -sb 2>&1 | Out-String -Width 200
git --no-pager log -1 --oneline 2>&1 | Out-String -Width 200
.venv\Scripts\python.exe -m pytest -q 2>&1 |
  Select-Object -Last 3 | Out-String -Width 200
```

Agentin kuori voi olla hyvin kapea (esim. 12 merkkiä) ja VS Code
shell integration voi pudottaa raa'an tulosteen. Siksi tuloste
putkitetaan `Out-String -Width 200`:lla. `pytest.ini`:ssä ei ole
`addopts = -q`, joten `pytest -q` tulostaa yhteenvedon
(esim. `93 passed`); älä anna pytestille kahta `-q`:ta. Jos tuloste
katoaa, aja komento uudelleen tai ohjaa se tiedostoon
(`> tulos.txt 2>&1`).

Älä aja Demucsia, Basic Pitchiä, yt-dlp:tä tai mallien latausta session
alustuksessa. Älä lue koko repoa tai vanhaa keskusteluhistoriaa.

## 3. Vastaa lyhyesti

Kerro 3–6 rivillä:

- versio + commit
- git-tila (clean / ahead)
- testien tulos
- seuraava vaihe `activeContext.md`:stä
- mahdolliset ristiriidat memory bankin ja koodin välillä

Jos käyttäjän viestissä on jo tehtävä, jatka siitä. Muuten ehdota
`activeContext.md`:n seuraavaa vaihetta.

## 4. Päivitä memory bank

- **Milestone / merkittävä muutos:** päivitä `activeContext.md` ja
  `progress.md`.
- **Arkkitehtuuri, stack tai päätökset:** päivitä `projectBrief.md`,
  `systemPatterns.md` ja `techContext.md` vain kun ne oikeasti muuttuvat.
- Älä kopioi koko keskustelua, lokia tai koodia. Linkitä tiedostoon tai
  committiin.
- Pidä tiedostot tiiviinä: tavoite < 200 riviä / tiedosto. Jos paisuu,
  siirrä yksityiskohdat README:hen/koodiin ja tiivistä.
- Memory bank on julkinen (committed): ei salaisuuksia, tokeneita,
  henkilötietoja eikä audio-/tab-sisältöä.
- Memory bank -muutokset commitoidaan `docs:`-prefixillä; ei
  versiobumppia.
- `docs/` ja `data/` pysyvät gitignorattuina.

## 5. Totuusjärjestys

1. Koodi ja git = toteutuksen totuus.
2. `memory-bank/` = päätösten ja tilan totuus.
3. MCP-graafi = nopea haku, ei ensisijainen lähde.

Jos memory bank ja koodi ovat ristiriidassa, raportoi se ja korjaa
memory bank.

## 6. Älä

- Älä laita memory bankiin pitkiä rimpsuja tai koko sessiohistoriaa.
- Älä käynnistä raskaita ML-ajoja `lue membank` -komennolla.
- Älä muuta `docs/`- tai `data/`-sisältöä.
- Älä unohda `.clinerules`-sääntöjä.
