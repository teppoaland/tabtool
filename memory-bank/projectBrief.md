# 🎯 Projektin lyhyt kuvaus – TABTOOL

> **Versio:** `v1.11` (18.10.2026)
> **Repo:** https://github.com/teppoaland/tabtool
> **Paikallinen:** `D:\AI\tabtool`

## Tavoite

Lokaali web-palvelu, jossa voi:

1. hakea kappaleita Spotifysta (haku/metadata),
2. generoida kitaratablatuurin omasta MP3:sta tai YouTube-audiosta,
3. katsoa tablatuuria alphaTabilla TV:stä/tietokoneelta,
4. käyttää puhelinta kaukosäätimenä,
5. viedä tabin GP5/MusicXML/MIDI-muodossa.

## Lukitut päätökset

- **Local-first audio:** tab-generointi ja taustatoisto tehdään samasta
  paikallisesta audiosta. Spotify ei anna raakaa audiota (DRM).
- **Spotify** = haku, metadata ja valinnainen toisto. Spotify-integraatio
  tulee vasta Phase 3:ssa.
- **YouTube** ladataan yt-dlp:llä audiostreamina; mainokset eivät tule
  mukaan. Käyttäjä vastaa ToS/tekijänoikeuksista.
- **Kitara ensin.** Basso, laulu ja rummut myöhemmin; rummut vaativat
  oman transkriptiomallin.
- **All rights reserved** (GameHubin käytäntö). Kolmannen osapuolen
  lisenssit `THIRD_PARTY_NOTICES.md`:ssä.
- **Versiosarja `1.x`**, aloitus `v1.00`; nyt `v1.11`.
- UI-tekstit ovat toistaiseksi suomeksi; pelaajalle näkyvät ydintekstit
  ovat englanniksi (SEARCH, GENERATE TAB, PLAY, PAUSE, EXPORT, REMOTE).

## Ei kuulu tähän projektiin

- ei pilvipalvelua eikä monikäyttäjätilejä
- ei Spotifyn DRM-audion tallennusta tai purkamista
- ei pelien fysiikkaa, kukkaro-/jukebox-logiikkaa tai GameHubin
  `10.x`-versiointia
- ei npm-riippuvuuksia eikä build-vaihetta frontendiin

## Tärkeät tiedostot

- `README.md` – käyttöohje ja tila
- `CHANGELOG.md` – versiohistoria
- `.clinerules/` – 6 projektisääntöä
- `app/pipeline/` – audio-to-tab-putki
- `scripts/pipeline_smoke.py` – CLI-proof
- `data/` – GITIGNORED: audio, stemmit, tabit, tokenit
- `docs/` – GITIGNORED: henkilökohtainen suunnitelma
