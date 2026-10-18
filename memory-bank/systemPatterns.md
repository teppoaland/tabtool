# 🧩 Järjestelmän arkkitehtuuri – TABTOOL

## Kerrokset

```
FastAPI (app/main.py)
  ├─ /api/health, /api/version, /api/config
  ├─ /, /display, /remote  → app/static/
  └─ (Phase 2+) /api/jobs, /api/tabs, /ws
        │
        ▼
Job-kerros (Phase 2: app/jobs.py)
        │
        ▼
Putki (app/pipeline/)
  audio_source → separate → transcribe → tempo → quantize
  → fretboard → build → export_gp5/musicxml/midi
```

- Reitit eivät kutsu Demucsia/Basic Pitchiä suoraan; ne luovat jobin.
- Putki ei importtaa FastAPIä eikä kirjoita HTTP-vastauksia.
- Frontend ei käsittele Spotify-client-secretiä (PKCE).
- Kaikki polut `app/config.py`:stä. `data/` on yksityinen juuri.

## Putken data

- `NoteEvent` – pitch, start/end sekunteina, velocity.
- `QuantizedNote` – tick-grid, `tie` = jatkuu edellisestä tahdista.
- `TabNote` – pitch, string, fret, start_tick, duration_ticks, tie.
- `TabMeasure` / `TabDocument` – tahdit, viritys, BPM, varoitukset.
- **Ticks:** 960 per quarter; 1/16 = 240 ticks; 4/4 tahti = 3840.
- Kvantisointi jakaa nuotit tahtirajoilla ja merkitsee jatkot tie:ksi.

## Fretboard

- Viterbi/DP: kustannus = käsiaseman liike, fret-span, korkeat frets,
  open-string-bonus.
- Kielikohtainen monofonia: jos kieli on varattu, nuotti siirretään
  vapaalle kielelle tai edellistä nuottia lyhennetään.
- Viritykset: standard, drop D, Eb, D, open G, bass 4-string.
- Standard E -alueen ulkopuoliset nuotit pudotetaan varoituksella.

## Export

- **GP5 ensisijainen** (PyGuitarPro). Validointi lukee tiedoston takaisin:
  tahtikestot täsmäävät, ei duplicate string -nuotteja.
- **MusicXML** tab-clef + `<technical><string><fret>`.
- **MIDI** pretty_midi, tempo = BPM, program 25.
- Tie-tila on nuottikohtainen (v1.11).

## Cache / DB (Phase 2)

Suunniteltu SQLite:

- `tracks` – Spotify/local/YouTube-metadata
- `jobs` – status, stage, progress, options, error
- `tabs` – `cache_key = sha256(track_id + pipeline_version + options)`
- `oauth_tokens` – Spotify PKCE -tokenit
- `settings`

Invariantit:

1. Sama audio + asetukset → sama tulos.
2. Valmis tab cachetetaan; ei ylikirjoitusta ilman regeneratea.
3. Atomiset kirjoitukset: temp + `os.replace`.
4. Path traversal -suojaus; `data/` ei koskaan static-mounttiin.
5. Jobin metadataan malli, versio, parametrit ja varoitukset.

## UI (Phase 2)

- `/` ja `/display` = TV-näkymä, `/remote` = puhelin.
- alphaTab 1.8.4 vendoroituna `app/static/vendor/alphaTab/`.
- `PlayerMode.EnabledExternalMedia` + `IExternalMediaHandler`.
- Paikallinen audio: `<audio>` + Range; positio 50 ms välein
  `api.player.output.updatePosition(pos + offset)`.
- Spotify (Phase 3): Web Playback SDK tai Spotify Connect -laite.
- Ei uusia modaaleja/toasteja; status inline.
