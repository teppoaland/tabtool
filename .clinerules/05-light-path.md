# 🪶 Kevyt polku

## Staattinen muutos → ei testejä

Kun muutos koskee vain yhtä näkymää tai staattista asiaa (väri, teksti,
koko, sijainti, fontti), riittää:

1. lue vain se tiedosto, jota muutos koskee
2. tee muutos
3. raportoi 1–3 riviä

Käyttäjä testaa itse silmällä.

## UI-muutokset – käyttäjä validoi

Pienet UI-muutokset (teksti, sijainti, tooltip, väri, tyhjä tila, QR) saa
tehdä suoraan: **ei pytestia, ei selainautomaatiota, ei kuvakaappauksia**.
Käyttäjä tarkistaa UI:n itse joka tapauksessa.

Sama koskee PianoCapturen `piano/static/` -tiedostoja. Testiajo ja
selainvalidointi varataan muutoksiin, jotka voivat rikkoa logiikan, API:n,
tallennuksen tai soittoketjun.

Raportti: mitä muuttui + versionumero, 1–3 riviä.

## Toiminnallisuus muuttuu → testaa

Testit ajetaan, kun muuttuu logiikka, putki, API, DB, OAuth, kvantisointi,
fretboard, export, reitit, tallennus tai turvallisuus.

Komennot:

```
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m compileall -q app
node --check app\static\app.js
node --check app\static\remote.js
```

## Muistipankki ja dokumentit

- Memory-bankia ei päivitetä, ellei käyttäjä pyydä.
- Uusia memoja ei tehdä ilman pyyntöä.
- Versiorivi nostetaan koodimuutoksesta (sääntö 03).
