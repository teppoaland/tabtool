# 🛠️ Tekninen ympäristö – TABTOOL

## Kone

- Windows 10/11, `D:\AI\tabtool`
- Python 3.11.9, `.venv` projektissa
- ffmpeg 7.1 (PATH)
- Node.js 22.22.2 (vain `node --check`)
- **Ei GPU:ta** (`nvidia-smi` tyhjä) → CPU-only
- D: levytilaa ~147 GB vapaana

## Python-paketit (v1.11)

Core:

- fastapi 0.143.3
- uvicorn 0.54.0
- httpx 0.28.1
- python-multipart 0.0.32
- python-dotenv 1.2.4
- pytest 9.1.1
- httpx2 2.13.1 (Starlette 1.8+ TestClient)

ML / audio:

- demucs 4.1.0
- basic-pitch 0.4.0
- tensorflow 2.15.0 (CPU)
- torch 2.14.1+cpu
- librosa 0.11.0
- soundfile 0.14.0
- music21 10.5.0
- PyGuitarPro 0.11
- yt-dlp 2026.8.19
- numpy 1.26.4
- **setuptools<81** (Basic Pitchin resampy käyttää `pkg_resources`)

## Asennus

```bat
setup.bat          :: core + dev
install-ml.bat     :: Demucs + Basic Pitch + export/audio
start.bat          :: uvicorn 127.0.0.1:8000
test.bat           :: pytest + compileall + node --check
```

Manuaalinen:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-dev.txt
.venv\Scripts\python.exe -m pip install -r requirements-ml.txt
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## Testit

```powershell
.venv\Scripts\python.exe -m pytest -q          # 30 passed
.venv\Scripts\python.exe -m compileall -q app scripts tests
node --check app\static\app.js
node --check app\static\remote.js
```

## Pipeline CLI

```powershell
.venv\Scripts\python.exe scripts\pipeline_smoke.py "C:\Music\song.mp3" --title "Song" --artist "Artist"
.venv\Scripts\python.exe scripts\pipeline_smoke.py "https://youtu.be/..." --clip-seconds 30
.venv\Scripts\python.exe scripts\pipeline_smoke.py song.mp3 --no-separation --clip-seconds 20
```

Hyödylliset valinnat: `--model htdemucs_6s`, `--stem guitar`, `--tuning`,
`--bpm`, `--start-seconds`, `--clip-seconds`, `--no-separation`,
`--max-fret`, `--max-span`, `--grid`, `--debug`.

## Git

- `origin` = `https://github.com/teppoaland/tabtool.git`
- `main` = `origin/main` = **6bd647c** (v1.11)
- Commit author: `Azure Notepad Pipeline <azure-pipeline@notepad-automation.com>`
- `.gitattributes`: `*.bat eol=crlf`
- `.gitignore`: `docs/`, `data/`, `.venv`, audio/tabit, tokenit, mallit
