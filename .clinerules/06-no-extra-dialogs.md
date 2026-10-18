# 🚫 Ei ylimääräisiä dialogeja

Älä lisää uutta käyttäjälle näkyvää dialogia, popupia, modaalia tai
toast-ilmoitusta ilman käyttäjän erillistä pyyntöä.

## Kielletty ilman lupaa

- uudet modaalit ja confirm-dialogit
- uudet popupit ja varoitusikkunat
- uudet toast-/snackbar-viestit

## Sallittua

- olemassa olevan viestin tekstin tai keston korjaus
- jobin pakolliset tilaviestit olemassa olevalla status-rivillä
- testi- ja debug-tekstit

## Hyväksytyt UI-tekstit

Kun UI on päätetty, sen tekstit lukitaan tähän. Toistaiseksi hyväksytyt
ydintekstit:

- `TABTOOL`
- `SEARCH`
- `GENERATE TAB`
- `PLAY` / `PAUSE`
- `EXPORT`
- `REMOTE`
- `Queued` / `Downloading audio…` / `Separating stems…` /
  `Transcribing guitar…` / `Building tab…` / `Ready` / `Failed`
- `CONNECT SPOTIFY` / `Spotify Premium required` / `Spotify not configured`

Näitä saa korjata, mutta uusia viestejä ei lisätä kysymättä.
