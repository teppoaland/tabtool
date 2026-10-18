# 📍 Aktiivinen konteksti – AI TABTOOL

> **Versio:** `v1.33` (18.10.2026)
> **Git:** koodi `d07c7de`, tagi `v1.29` = `bb704e8`, `origin/main` = `69c2e39`
> **Push:** ei pushata julkiseen GitHubiin — vain lokaalit commitit
> **Repo:** https://github.com/teppoaland/tabtool

## Nyt

- Phase 0/1/2 valmiit; Phase 2:n päälle on tehty v1.23–v1.29:
  katselu, aikajana, tuonti/audio, BPM/Nopeus ja pätkägenerointi.
- Katselu: **tab-only oletus**, Näkymä (`Tab`/`Auto`/`Tab+nuotit`/`Nuotit`),
  raitavalinnat ja tabikohtainen muisti, FULLSCREEN + automaattinen
  fullscreen PLAYssa, cursor + edellinen rivi näkyvissä, dynamiikat piilossa,
  vaakascrollbar pois.
- Aikajana: aika/kesto, **tahtilukema**, ±5 s, Space/nuolet, seek
  vierittää tabin cursorin kohdalle.
- YouTube-metadata: title/artist yt-dlp:stä, `(Remastered)`-siivous;
  `YouTube audio` vain fallback. `audio_path` myös web-tabin metassa.
- Valmiin tabin tuonti: **GP5/MusicXML**, metat PyGuitarPro/music21,
  kirjastoon; tuodut tabit merkitään `Lähde: tuotu tabi`.
- **LIITÄ AUDIO**: samannimisen AI-tabin audio liitetään tuotuun tabiin;
  PLAY/aikajana/cursor tulevat käyttöön. Moniraitaisesta tuonnista
  oletuksena Guitar 1 + Guitar 2.
- **TAB BPM/Nopeus**: GP5-tempo korjattavissa, audio 100 %; Nopeus
  50–150 % harjoitteluun. AI-BPM on arvio, ei totuus.
- **SYNC** (v1.30): tabin kohdistus ±10 %/0,05 %, `+` eteen ja `-`
  taakse; tallentuu tabin `meta.json`iin (`sync_drift`) ja palautuu
  aina tabia avattaessa. GP5/audio eivät muutu. Syy: pitkässä
  GP5-tabissa heitto kertyy (esim. Seek & Destroy ~60–70 tahti).
- **TALLENNA** (v1.31, entinen ASETA): TAB BPM tallentuu vain napista;
  tallentamaton arvo värjää kentän, syötteen ja napin punaiseksi.
  Virheet (BPM 20–400, tallennusvirhe) punaisella; SYNC-virheet samoin.
- **"Not found" -muistutus:** uvicorn ei käytä `--reload`ia. Jos UI on
  uudempi kuin käynnissä oleva prosessi, `/tempo` ja `/sync` palauttavat
  404 → käynnistä palvelin uudelleen (`start.bat`).
- **Ulkoinen arkisto** (v1.32): YouTube-audio ja tuodut GP5/MusicXML
  mirroroidaan hakemistoon `D:\tabtool_files\audio` ja `\tabs`
  (`TABTOOL_EXTERNAL_DIR`), nimi `Artist - Title.ext`. Samalla levyllä
  hard link (ei tuplalevytilaa), muuten kopio. `data/` on edelleen
  totuuden lähde; pätkäklipit jätetään arkistoimatta.
- **Kirjasto tyhjänä?** Tarkista `TABTOOL_DATA_DIR`. Jos ympäristömuuttuja
  osoittaa testihakemistoon (esim. aiemman `Start-Process`in perintö),
  UI näyttää tyhjän kirjaston vaikka `D:\AI\tabtool\data` olisi ehjä.
  Käynnistä palvelin eksplisiittisellä `TABTOOL_DATA_DIR`illa.
- **MP3-kuunteluversiot** (v1.33): YouTube-latauksista syntyy
  `D:\tabtool_files\audio\mp3\<Artisti>\Artist - Title.mp3`
  (ffmpeg VBR ~190 kbps; vain jos WAV on uudempi). Pätkäklipit ja
  omat uploadit ohitetaan.
- **Seek-synkki** tutkittu: siirto sliderilla ei riko aikasynkkiä
  (tahtilukema osui 30→10→50→20→55→5 s kaikissa). `audio.seeking`
  estää välipositiot ja slider vapautetaan `pointerup`/`blur`illa.
- Referenssitabi palautettu **140 BPM**; audio liitetty; AI-tabi 144.
  BPM/Nopeus-kontrollit jäävät, mutta eivät pakota 144:ään.
- Täydet kappaleet ovat oletus; pätkägenerointi (`TEE TAB TÄSTÄ`) on
  poikkeus.
- Soittotapa/refinger (asemaprofiilit, helpoin-arvio, turhien nuottien
  karsinta, per-tahti-asema) on suunniteltu mutta **ei toteutettu**;
  jäissä. Koodi on committoitu (`d07c7de`); tagi `v1.29` = `bb704e8`;
  vain lokaalit commitit, ei pushia.
- Spotify ei ole vielä mukana (Phase 3).

## Seuraava vaihe

1. Seek & Destroy -GP5:n hienosäätö: aja kohtaan ~60–70 tahti, säädä
   SYNC kohdalleen (tallentuu tabille); jos heitto kasvaa edelleen,
   tarkista GP5:n BPM/tahtirakenne TAB BPM:llä ja Guitar Prolla.
2. Päätä soittotapa/refinger-toteutus: asemaprofiilit, playability-score,
   turhien nuottien karsinta, per-tahti/fraasiasema.
3. Vasta sitten Phase 3 / Spotify: PKCE, haku/metadata, SDK/Connect,
   tokenit `oauth_tokens`-tauluun ja mockatut API-testit.


## Tärkeät komennot

```powershell
cd D:\AI\tabtool
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m compileall -q app scripts tests
node --check app\static\app.js
node --check app\static\remote.js
start.bat
```

Putki:

```powershell
.venv\Scripts\python.exe scripts\pipeline_smoke.py "C:\Music\song.mp3" --title "Song" --artist "Artist"
```

## Tuoreimmat validointitulokset

- `pytest -q` → **64 passed**; `compileall` ja `node --check` OK.
- Headless-Chrome: SYNC `+3.50 %` → `sync_drift 0.035` kantaan ja
  `meta.json`iin; reload palautti arvon; Nopeus 50–150 %.
- v1.31 headless: TALLENNA-nappi, punainen dirty-tila
  (`rgb(255,123,123)`), BPM 146 → GP5-tempo 146 ja tila tyhjeni;
  SYNC `+2.50 %` → `0.025`, ei virheitä.
- v1.32: 69 pytest-testiä; backfill arkistoi 5 tiedostoa
  (`D:\tabtool_files`), `fsutil hardlink list` vahvisti hard linkin
  (`yt-62c1293b02.wav` ↔ `Metallica - Seek & Destroy.wav`).
- Live-palvelin 8000: **v1.33**, 8 tabia `D:\AI\tabtool\data`:sta.
- v1.33: seek-testi 30/10/50/20/55/5 s → tahdit 16/6/26/11/28/3
  (odotetut); MP3 `Metallica` 414,7 s / 9,8 MB, `KISS` 20,0 s
  (alkuperäinen audio on 20 s klippi); 72 testiä.
- Referenssitabi **140 BPM**, audio 414,72 s, PLAY + aikajana + cursor;
  5 raitaa, oletus Guitar 1 + Guitar 2.
- AI-tabi 144 BPM / 249 tahtia; referenssi 140 BPM / 258 tahtia.
- GP5/MusicXML-tuonti ja `LIITÄ AUDIO` validoitu headless-selaimessa.
- 144 BPM -kokeilu peruutettu; referenssi palautettu 140:een käyttäjän
  toiveesta. BPM/Nopeus-kontrollit jäivät paikoilleen.

## Avoimet / myöhemmin

- Soittotapa/refinger: asemaprofiilit, helpoin-arvio, turhien nuottien
  karsinta, per-tahti/fraasiasema; **ei koodia vielä**. Tarkoitus on
  käyttää samaa nuottidataa ja tehdä eri sormitusvaihtoehdot.
- AI-transkription tarkkuus (Basic Pitch); referenssitabit ja ilmainen
  TuxGuitar apuna, ei Guitar Pro -pakkoa.
- KISSin kaltaiset kappaleet ilman valmista tabia: AI-tabi + korjaus.
- Referenssitabin rakenne vs. audio (258 vs. 249 tahtia). SYNC korjaa
  vain lineaarisen heiton; ylimääräinen/puuttuva tahti vaatii GP5-korjauksen.
- Spotify Phase 3, remote Phase 4, LAN-PIN, retention, bass/laulu,
  rummut (ADTOF/Omnizart), manuaalinen editori.

## Uuden session aloitus

**Sano Cline:lle: `lue membank`.**

Se tekee automaattisesti:

1. Lukee `memory-bank/projectBrief.md`, `systemPatterns.md`,
   `techContext.md`, `activeContext.md` ja `progress.md`.
2. Lukee `.clinerules/*.md`.
3. Ajaa `git --no-pager status -sb`, `git --no-pager log -1 --oneline`
   ja `pytest -q`.
4. Jatkaa tämän tiedoston seuraavasta vaiheesta; ei riko
   `.clinerules/`-sääntöjä.
5. `docs/` ja `data/` ovat yksityisiä eivätkä kuulu gitiin.
