# 10 – Git-hygienia: gittiin vain tuotekoodi

## Mitä gittiin ei laiteta

- **Ei keskusteluja.** Kysymys devaamisen yhteydessä ("miten X on tehty",
  "miksi tämä toimii näin") on keskustelu, ei commit.
- **Ei tutkinta- tai analyysiskriptejä** (esim. `.tmp-*`, MCP-/selain-
  tutkinnat, kertakäyttöiset `.mjs`/`.ps1`-pätkät).
- **Ei väliaikaistiedostoja, lokitulosteita eikä agentin työmuistiinpanoja.**
- **Ei memory bankia** (paikallinen, `.gitignore`ssa).

## Miten toimitaan

- Väliaikaistiedostot tehdään **repon ulkopuolelle**:
  `D:\AI\AI_temp\<aihe>\`. Ei repon juureen, ei `.clinerules`-kansioon.
- Keskustelun tulos jää chattiin. Jos se on pysyvästi arvokasta, siitä
  kirjoitetaan **lyhyt tiivistelmä** `memory-bank/`-tiedostoon (paikallinen,
  ei committia) – ei koskaan raakaa skriptiä tai keskustelulokia.
- Ennen mitään committia `git status` tarkistetaan: ylimääräiset `??`-rivit
  siivotaan ensin. `git add -A` ja `git commit -a` ovat kiellettyjä.
- Jos jokin ei-sovellukseen kuuluva tiedosto on vahingossa trackattu,
  poistetaan se `git rm --cached`illa ja lisätään `.gitignore`en.

## Lokaali git ja GitHub

- Sääntö-, doc- ja konfiguraatiomuutokset saa committaa **lokaalisti**
  (`docs(...)`-prefix).
- Devaustyö menee aina myös GitHubiin, joten **kaikki mikä on `main`issa voi
  päätyä julkiseksi**. Siksi työpuu siivotaan ennen committia ja pushia:
  lokaaliin committiin ei jätetä mitään, mitä ei haluta GitHubiin.
- Push vain erillisestä pyynnöstä; committikaan ei ole lupa pushata.

## Sääntö lyhyesti

> Jos tiedosto ei ole sovelluksen lähdekoodia, testi, dokumentaatio tai
> määritelty konfiguraatio, se ei mene gittiin.
