# 📜 CHANGELOG – TABTOOL

> TabTool käyttää `1.x`-versiosarjaa. Aloitus `v1.00`.

## v1.00 – 18.10.2026

Projektin runko ja säännöt.

- `git init`, `origin` = `teppoaland/tabtool`.
- `.gitignore`: `docs/`, `data/`, `.venv`, audio/tab-tiedostot, tokenit,
  mallit ja välimuistit pois julkisesta gitistä.
- `.clinerules/`: arkkitehtuuri, putken ydinsäännöt, versionhallinta,
  data/yksityisyys/lisenssit, kevyt polku ja ei ylimääräisiä dialogeja.
- FastAPI-runko: `/api/health`, `/api/version`, `/`, `/remote`, `/display`.
- Tyhjä tumma TV- ja remote-näkymä.
- `requirements.txt`, `requirements-ml.txt`, `requirements-dev.txt`.
- `setup.bat`, `install-ml.bat`, `start.bat`, `test.bat`.
- Ensimmäinen pytest-testi ja versiotarkistus.
- Lisenssi: All rights reserved. Kolmannen osapuolen lisenssit erillisessä
  `THIRD_PARTY_NOTICES.md`-tiedostossa.
