# Third-Party Notices

AI TabTool uses the following open-source libraries, models and tools as
separate dependencies. They remain under their respective licenses.
AI TabTool does not claim ownership of them.

## Runtime

| Component | Purpose | License | Home |
|---|---|---|---|
| FastAPI | Web API framework | MIT | https://fastapi.tiangolo.com/ |
| Uvicorn | ASGI server | BSD-3-Clause | https://www.uvicorn.org/ |
| HTTPX | HTTP client | BSD-3-Clause | https://www.python-httpx.org/ |
| python-multipart | Form uploads | Apache-2.0 | https://github.com/Kludex/python-multipart |
| python-dotenv | `.env` loading | BSD-3-Clause | https://github.com/theskumar/python-dotenv |
| Segno | QR code for phone pairing | BSD-3-Clause | https://github.com/heuer/segno/ |
| SQLite | Local database | Public domain | https://www.sqlite.org/ |

## Audio / ML pipeline

| Component | Purpose | License | Home |
|---|---|---|---|
| Demucs | Stem separation | MIT | https://github.com/adefossez/demucs |
| Basic Pitch | Audio-to-MIDI | Apache-2.0 | https://github.com/spotify/basic-pitch |
| Librosa | Tempo/beat analysis | ISC | https://librosa.org/ |
| SoundFile | Audio I/O | BSD-3-Clause | https://github.com/bastibe/python-soundfile |
| music21 | MusicXML export | BSD-3-Clause | https://web.mit.edu/music21/ |
| PyGuitarPro | GP3/GP4/GP5 read/write | LGPL-3.0-only | https://github.com/Perlence/PyGuitarPro |
| yt-dlp | YouTube audio download | Unlicense | https://github.com/yt-dlp/yt-dlp |
| FFmpeg | Audio conversion | LGPL/GPL (build-dependent) | https://ffmpeg.org/ |

FFmpeg is used as an external program and is not distributed with this
repository.

## Frontend

| Component | Purpose | License | Home |
|---|---|---|---|
| alphaTab | Tab rendering and playback | MPL-2.0 | https://www.alphatab.net/ |

alphaTab 1.8.4 is vendored unmodified under `app/static/vendor/alphaTab/`
(`alphaTab.min.js`, the Bravura font and the upstream `LICENSE`). The
Bravura music font is licensed under the SIL Open Font License 1.1; its
license text is kept next to the font files.

## External services

| Service | Purpose | Terms |
|---|---|---|
| Spotify Web API / Web Playback SDK | Search, metadata, optional playback | Spotify Developer Terms |
| YouTube | Audio source (via yt-dlp) | YouTube Terms of Service |

Spotify and YouTube are not affiliated with AI TabTool. The user is
responsible for complying with their terms and with copyright law.

## Models

Demucs pretrained models and Basic Pitch models are downloaded by their
respective libraries and remain under their respective licenses. Model
files are stored under the private `data/` directory and are not
committed to this repository.
