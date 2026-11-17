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
  (`docs(...)`-prefix). Push vain erillisestä pyynnöstä.
- **GitHubiin viedään vain arvokas data:** koodi, dokumentaatio,
  konfiguraatio ja julkaisut – jotta projekti säilyy, jos kone hajoaa, ja
  jotta sitä voi tutkia. Roska estetään jo ennen committia, ei siivota
  jälkikäteen.
- **Historiaa ei siivota eikä uudelleenkirjoiteta** – ei `filter-repo`ia,
  ei force-pushia. Vanhat commitit saavat jäädä; niissä ei ole salaisuuksia.
- Memory bank on henkilökohtainen työmuisti: **paikallinen, ei GitHubiin.**

## Sääntö lyhyesti

> Jos tiedosto ei ole sovelluksen lähdekoodia, testi, dokumentaatio tai
> määritelty konfiguraatio, se ei mene gittiin.
