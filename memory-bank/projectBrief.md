# 🎯 Projektin lyhyt kuvaus – AI TABTOOL

> **Versio:** `v1.29` (18.10.2026)
> **Repo:** https://github.com/teppoaland/tabtool
> **Paikallinen:** `D:\AI\tabtool`

## Tavoite

Lokaali web-palvelu, jossa voi:

1. hakea kappaleita Spotifysta (haku/metadata),
2. generoida kitaratablatuuri omasta MP3:sta tai YouTube-audiosta,
3. tuoda valmiita GP5/MusicXML-tabeja ja liittää niihin audio,
4. katsoa tablatuuria alphaTabilla TV:stä/tietokoneelta (aikajana,
   cursor, fullscreen, raitavalinnat, BPM/Nopeus),
5. käyttää puhelinta kaukosäätimenä,
6. viedä tabin GP5/MusicXML/MIDI-muodossa.

## Lukitut päätökset

- **Local-first audio:** tab-generointi ja taustatoisto tehdään samasta
  paikallisesta audiosta. Spotify ei anna raakaa audiota (DRM).
- **Spotify** = haku, metadata ja valinnainen toisto. Spotify-integraatio
  tulee vasta Phase 3:ssa.
- **YouTube** ladataan yt-dlp:llä audiostreamina; mainokset eivät tule
  mukaan. Käyttäjä vastaa ToS/tekijänoikeuksista.
- **Kitara ensin.** Basso, laulu ja rummut myöhemmin; rummut vaativat
  oman transkriptiomallin.
- **Täydet kappaleet ovat oletus.** Pätkägenerointi on poikkeus.
- **Valmiin tabin tuonti** GP5/MusicXML; samannimisen AI-tabin audio
  voidaan liittää tuotuun tabiin. Tabin BPM korjattavissa desimaalilla
  (GP5 tallentaa kokonaisluvun; desimaali on toiston korjaus), `Nopeus`
  50–150 % harjoitteluun, `SYNC` ±10 % hienosäätöön ja `SIIRTO`
  −64…+64 tahtia rakenne-eroon; kaikki tallentuvat tabille.
- **Ei pakollista Guitar Prota.** TuxGuitar on ilmainen apuväline
  tarvittaessa; appi tuo GP5/MusicXML:n.
- **All rights reserved** (GameHubin käytäntö). Kolmannen osapuolen
  lisenssit `THIRD_PARTY_NOTICES.md`:ssä.
- **Versiosarja `1.x`**, aloitus `v1.00`; nyt `v1.29`.
- **Ei julkista julkaisua:** koodi pidetään lokaalina. Commitit tehdään
  paikalliseen repoon palautuspisteiksi (revert); push GitHubiin vain
  erillisestä pyynnöstä.
- **Ulkoinen sisältö arkistoidaan** `D:\tabtool_files\`
  (`TABTOOL_EXTERNAL_DIR`): YouTube-audiot ja tuodut GP5/MusicXML
  luettavalla nimellä. `data/` on totuuden lähde; hard link samalla
  levyllä, joten tiedostot löytyvät myös muuhun käyttöön ilman
  tuplalevytilaa. YouTube-latauksista tehdään lisäksi MP3
  `audio/mp3/<Artisti>/`-kansioon omaan kuunteluun.
- **Tuotenimi `AI TabTool`** (v1.22–v1.29). Repo/hakemisto `tabtool`,
  `TABTOOL_*`-ympäristömuuttujat ja `data/tabtool.sqlite3` ovat teknisiä
  nimiä. Ei sidoksissa tabtool GmbH:hen eikä SEYDEL TabTooliin.
- UI-tekstit ovat toistaiseksi suomeksi; pelaajalle näkyvät ydintekstit
  ovat englanniksi (SEARCH, GENERATE TAB, PLAY, PAUSE, EXPORT, REMOTE).

## Ei kuulu tähän projektiin

- ei pilvipalvelua eikä monikäyttäjätilejä
- ei Spotifyn DRM-audion tallennusta tai purkamista
- ei pelien fysiikkaa, kukkaro-/jukebox-logiikkaa tai GameHubin
  `10.x`-versiointia
- ei npm-riippuvuuksia eikä build-vaihetta frontendiin

## Session aloitus

Sano Cline:lle **`lue membank`**. Sääntö on
`.clinerules/00-memory-bank.md`:ssä.

## Tärkeät tiedostot

- `README.md` – käyttöohje ja tila
- `CHANGELOG.md` – versiohistoria
- `.clinerules/` – 7 projektisääntöä
- `app/pipeline/` – audio-to-tab-putki
- `app/tab_import.py` – GP5/MusicXML-tuonti
- `scripts/pipeline_smoke.py` – CLI-proof
- `tests/` – 64 pytest-testiä
- `data/` – GITIGNORED: audio, stemmit, tabit, tokenit
- `docs/` – GITIGNORED: henkilökohtainen suunnitelma
