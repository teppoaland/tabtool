# 🧩 Järjestelmän arkkitehtuuri – TABTOOL

## Kerrokset

```
FastAPI (app/main.py)
  ├─ /api/health, /api/version, /api/config
  ├─ /api/jobs, /api/jobs/{id}, /api/jobs/{id}/events (SSE)
  ├─ /api/tabs, /api/tabs/{id}, score/export/audio
  └─ /, /display, /remote  → app/static/
        │
        ▼
Job-kerros (app/jobs.py: jono + worker + cache + eventit)
        │
        ▼
SQLite (app/db.py: tracks, jobs, tabs, oauth_tokens, settings)
        │
        ▼
Putki (app/pipeline/)
  audio_source → separate → transcribe → tempo → quantize
  → fretboard → build → export_gp5/musicxml/midi
```

- Reitit eivät kutsu Demucsia/Basic Pitchiä suoraan; ne luovat jobin.
- Putki ei importtaa FastAPIä eikä kirjoita HTTP-vastauksia.
- Job-kerros importtaa putken vasta ajon aikana (kevyt käynnistys).
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

## Cache / DB

Toteutettu SQLite (`app/db.py`, WAL, `data/tabtool.sqlite3`):

- `tracks` – title, artist, source_type, source_ref, fingerprint, audio
- `jobs` – status, stage, progress, options, warnings, error, tab_id
- `tabs` – `cache_key`, directory, metadata, `meta_json`
- `oauth_tokens` – Spotify PKCE -tokenit (Phase 3)
- `settings`

`cache_key = sha256(fingerprint + PIPELINE_VERSION + options)`.
Fingerprint: uploadin sisältöhash, YouTube-URL tai local path + koko +
mtime. Polut tallennetaan suhteessa `DATA_DIR`:iin.

Invariantit:

1. Sama audio + asetukset → sama tulos.
2. Valmis tab cachetetaan; `regenerate` korvaa vanhan tabin ja
   hakemiston vasta onnistuneen viennin jälkeen.
3. Atomiset kirjoitukset: temp-hakemisto + `os.replace`.
4. Path traversal -suojaus; `data/` ei koskaan static-mounttiin.
5. Jobin metadataan malli, versio, parametrit ja varoitukset.

## UI

- `/` ja `/display` = TV-näkymä, `/remote` = puhelin (Phase 4).
- alphaTab 1.8.4 vendoroituna `app/static/vendor/alphaTab/`
  (Bravura-fontti `font/`, `core.useWorkers = false`).
- `PlayerMode.EnabledExternalMedia` + `IExternalMediaHandler`;
  positio 50 ms välein `api.player.output.updatePosition(ms)`.
- Paikallinen audio: `<audio>` + Range (`FileResponse` 206).
- UI: upload/YouTube-lomake, status-rivi + progress, kirjasto,
  EXPORT-linkit, `?tab=<id>`-syvälinkki.
- Ei uusia modaaleja/toasteja; status inline.
