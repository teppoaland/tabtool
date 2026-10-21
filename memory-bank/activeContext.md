# 📍 Aktiivinen konteksti – AI TABTOOL

> **Versio:** `v1.65` (21.10.2026)
> **Git:** HEAD `196ff62` (docs, ahead 1). **v1.57–v1.65 koodi on
> työpuussa commitoimatta** (`CHANGELOG`, `app/*`, `app/static/*`,
> `tests/test_tab_library.py`). Docs-commit siirtää HEADia, joten älä
> pinnaa hashia pysyvästi.
> **Push:** vain erillisestä pyynnöstä (käyttäjä pyysi 20.10.2026).
> **Repo:** https://github.com/teppoaland/tabtool
> **Palvelin:** käyttäjän hallinnassa (`start.bat` / `stop.bat`); Cline ei
> käynnistä sitä taustalle eikä pysäytä ilman pyyntöä. 21.10.2026 se on
> sammutettu.

## Nyt

- **v1.63–v1.65 – kirjaston hallinta.** `POST /api/tabs/{id}/library`
  (`title`/`locked`/`archived`), rivin `NIMEÄ`-lomake (nimi + Lukitse +
  Arkistoi + TALLENNA/PERUUTA), `ARKISTO (n)` -linkki listan lopussa,
  aakkosjärjestys ja punainen `×`-poisto. `locked` estää poiston (409);
  `archived` piilottaa päälistalta ja rastin poisto palauttaa sen.
  Sarakkeet: `title_override`, `locked`, `archived` (+ migraatio).
- **v1.57–v1.62 – ulkoasu.** Tabin marginaalit 30/30 px (alphaTabin
  `display.padding: [30, 15]`, jotta 15 px scrollbar ei mene tabin
  päälle), `.alphatab` paddingitta (reunus inset-varjolla), yläosa
  tiiviimmäksi, LIBRARY PLAY-korttiin, NÄKYMÄ/raitavalinnat omalle
  riville, FULLSCREEN kortin oikeaan yläkulmaan, `.transport` omaksi
  kortiksi, EXPORT tabikentän alle, modaali avautuu LIBRARY-napin
  korkeudelle, LIBRARY piiloon fullscreenissä, KIRJASTO modaalin
  vasemmaksi sarakkeeksi.
- **v1.56 – count-in 5 → 0 soittoketjun ulkopuolella (validoitu
  käyttäjän kuuntelutestillä).** `handlePlayButton` on portinvartija.
- **v1.54**: palvelimen hallinta käyttäjälle (`stop.bat`, `status.bat`,
  `start.bat`in porttitarkistus); ei muutoksia soittoon.
- **v1.49**: tabi tummassa teemassa; SEARCH-napit → LIBRARY.
- **Kursorin synkka (v1.43–v1.48)**: `backingTrackDuration` = partituurin
  kesto master bar -tikeistä (`scoreEndTimeMs`), ei ääniraidan kesto;
  `enableAnimatedBeatCursor = false`; klikkaus-seek kääntää
  SIIRTO/SYNC/BPM-korjauksen (`time > 0`). KOHDISTA-nappi ja
  live-offset-näyttö (v1.46) auttavat kohdistamaan.
- **v1.42**: `pytest.ini`:n `addopts = -q` poistettu, joten `pytest -q`
  tulostaa yhteenvedon (`101 passed`).
- Phase 0/1/2 valmiit; v1.23–v1.37 katselu, aikajana, tuonti/audio,
  BPM/Nopeus, SYNC/SIIRTO ja ulkoinen arkisto. v1.38–v1.40 toivat
  **SEARCH-modaalin**, GP5-linkin/-tiedoston + YT-audion yhdellä
  toiminnolla ja kappaleen poiston. **v1.41** lisäsi GP3/GP4-tuonnin
  (konversio aidoksi GP5:ksi) ja korjasi audiopolun katoamisen
  levyrekisteröinnissä.
- **SEARCH-modaali** (v1.38; v1.49 käyttöliittymässä **LIBRARY**): YouTube-
  linkki, GP5-linkki tai GP5-tiedosto, MP3-valinta, GENERATE TAB sekä
  kirjasto, josta kappale valitaan soittoon. TV-näkymä on soittoa varten.
  Modaalin iso `SEARCH`-otsikko poistettu v1.49:ssä; `aria-label` säilyttää
  nimeämisen.
- **GP5 + YT yhdellä toiminnolla** (v1.40): `GP5-linkki` tai
  `GP5-tiedosto` ohittaa AI-generoinnin. YouTube-linkin kanssa tabi
  tuodaan ja audio liitetään samalla jobilla; ilman GP5-lähdettä tabi
  generoidaan AI:lla. GP5 + oma audiotiedosto on estetty.
- **Poisto** (v1.38, × v1.65): kirjastorivin punainen `×` avaa
  varoitusdialogin. Tab, hakemisto, stemmit ja job/track-rivit
  poistetaan; jaettu audio säilyy ja MP3-kuunteluversio jää arkistoon.
  Lukittua tabia ei voi poistaa (409).
- **Kirjaston metadata** (v1.63): `NIMEÄ` avaa rivin lomakkeen
  (nimi + `[ ] Lukitse` + `[ ] Arkistoi`); `title_override` on käyttäjän
  nimi, `original_title` generaattorin nimi. Lista on aakkosjärjestyksessä
  ja arkistoidut löytyvät listan lopun `ARKISTO (n)` -linkistä; rastin
  poisto palauttaa ne pääkirjastoon.
- **MP3-valinta** (v1.38): `MP3-kuunteluversio` on oletuksena päällä;
  valinta ei vaikuta tabin cache-avaimeen.
- **Modaalin pino** (v1.39): alphaTabin cursor (`z-index: 1000`) ei enää
  näy modaalin päällä; modaali `2000`, dialogi `2100`, viewer
  `isolation: isolate`, cursor piiloon `body.modal-open`-tilassa.
- Katselu: **tab-only oletus**, Näkymä (`Tab`/`Auto`/`Tab+nuotit`/`Nuotit`),
  raitavalinnat ja tabikohtainen muisti, FULLSCREEN + automaattinen
  fullscreen PLAYssa (fullscreenissä LIBRARY piilotetaan, v1.62),
  cursor + edellinen rivi näkyvissä, dynamiikat piilossa,
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
- **Kirjasto tyhjänä?** Tarkista `TABTOOL_DATA_DIR` ja
  `TABTOOL_EXTERNAL_DIR`. Jos IDE:n perimä ympäristö osoittaa
  testihakemistoon (esim. vanha `tabtool_ui5` Tempissä), UI näyttää
  väärän kirjaston. Käynnistä palvelin ilman näitä muuttujia
  (`Remove-Item Env:TABTOOL_DATA_DIR`) → oletukset `data/` ja
  `D:\tabtool_files`. v1.41 korjasi myös sen, että levyltä luettu
  relatiivinen `meta.audio_path` säilyy tabilla.
- **MP3-kuunteluversiot** (v1.33): YouTube-latauksista syntyy
  `D:\tabtool_files\audio\mp3\<Artisti>\Artist - Title.mp3`
  (ffmpeg VBR ~190 kbps; vain jos WAV on uudempi). Pätkäklipit ja
  omat uploadit ohitetaan.
- **Seek-synkki** tutkittu: siirto sliderilla ei riko aikasynkkiä
  (tahtilukema osui 30→10→50→20→55→5 s kaikissa). `audio.seeking`
  estää välipositiot ja slider vapautetaan `pointerup`/`blur`illa.
- **Playback range -ansa** (v1.37): hiirellä raahaus loi alphaTabin
  loop-alueen (vihreä kehys), joka clampaa `mainSeek`in → tab näyttää
  väärää kohtaa ja Pause hyppää. Range nollataan nyt
  `playbackRangeChanged`issa, `scoreLoaded`issa ja ennen seekiä.
  Pause palauttaa sijainnin audion aikaan (60/150 ms).
- **Desimaali-TAB BPM** (v1.34): kenttä hyväksyy 0,1 askeleen
  (`143,55`). GP5 tallentaa kokonaisluvun (`int(bpm+0,5)`), desimaali
  toteutuu toiston korjauksena `bpm/score.tempo - 1`, joka summataan
  SYNC-arvoon. Ratkaisee "143 jää jälkeen / 144 edistää" -ongelman.
  Seek & Destroy -audion mitattu tempo **143,555 BPM** (librosa).
- **SIIRTO (tahtia)** (v1.35–v1.36): siirtää tabia tahdeilla
  (−64…+64, 0,25 tahdin askel = 1 isku), tallentuu
  `meta.sync_offset_bars`. Vakiosiirtoon (esim. 6 iskua = 1,5 tahtia)
  ja rakenne-eroon. Ei korvaa SYNCiä (prosentti) eikä BPM:ää.
- Referenssitabi: 258 tahtia, BPM 143,5 (GP5 144); AI-tabi 249
  tahtia, BPM 143,5547. BPM/SYNC/SIIRTO eivät pakota 144:ään.
- Täydet kappaleet ovat oletus; pätkägenerointi (`TEE TAB TÄSTÄ`) on
  poikkeus.
- Soittotapa/refinger (asemaprofiilit, helpoin-arvio, turhien nuottien
  karsinta, per-tahti-asema) on suunniteltu mutta **ei toteutettu**;
  jäissä. Koodi on committoitu (v1.41); vain lokaalit commitit,
  ei pushia.
- Spotify ei ole vielä mukana (Phase 3).

## Seuraava vaihe

1. Päätä soittotapa/refinger-toteutus: asemaprofiilit, playability-score,
   turhien nuottien karsinta, per-tahti/fraasiasema.
2. Vasta sitten Phase 3 / Spotify: PKCE, haku/metadata, SDK/Connect,
   tokenit `oauth_tokens`-tauluun ja mockatut API-testit.
3. Phase 4: remote-kaukosäädin.


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

- `pytest -q` → **101 passed**; `compileall` ja `node --check` OK.
- v1.57–v1.62 headless (käyttäjän palvelin): tabin marginaalit
  30/30 px ja tabin reuna → scrollbar 15 px (1600/1366/1200/1024/800 px,
  ei sivuttaisvieritystä); LIBRARY/PLAY-kortti + FULLSCREEN oikeassa
  reunassa; modaalin yläreuna = LIBRARY-napin top (118 px); fullscreen
  piilottaa LIBRARYn; EXPORT 16 px tabikentän alapuolella.
- v1.63–v1.65: backend **101 passed** (nimeäminen, lukitus/poistoesto,
  arkisto, järjestys, migraatio); UI-smoke: lista aakkosissa (myös
  samannimiset), NIMEÄ-lomake (Lukitse/Arkistoi/TALLENNA/PERUUTA) ja
  PERUUTUS toimivat. Tallennuspolkua ei testattu selaimessa.
- v1.56 headless-Edge (CDP, käyttäjän palvelin): countdown 5→4→3→2→1→0
  ≈ 5,07 s, toisto 5,33 s; laskennan aikana `audio.currentTime` 0,846,
  `paused`, tahti 1 – kaikki muuttumattomia; layout 800/800; 2. PLAY
  peruu, seuraava aloittaa vitosesta; A/B audio 11,0 s → tahti 6
  molemmilla. Käyttäjän kuuntelutesti: **OK**.
- v1.31–v1.41 headless: TALLENNA/dirty-tila, backfill + hard link, seek
  30/10/50/20/55/5 s → 16/6/26/11/28/3, SYNC `+3.50 %` → `0.035`,
  desimaali-BPM, SIIRTO, GP3/GP4 → GP5 (0 nuottieroa), SEARCH-mod +
  poisto, GP5+YT. Tempot 143,55 / 161,5 / 143,55 / 112,35 / 136,0 BPM.
  Yksityiskohdat `CHANGELOG.md`:ssä.
- Palvelin on käyttäjän CMD-ikkunassa; v1.56 mitattiin käyttäjän
  käynnissä olevaa palvelinta vasten headless-CDP:llä.
- v1.49–v1.53 headless: tumma render, LIBRARY ilman otsikkoa, count-in
  4→0 (v1.49–v1.52) ja sen poisto (v1.53); lataus t = 1,268 s, 10 s →
  tahti 7 (SIIRTO −0,75), layout 1600/1600 px.
- Referenssitabi: 258 tahtia, BPM 143,5 (GP5 144); AI-tabi 249 tahtia,
  BPM 143,5547. Audio 414,72 s, PLAY + aikajana + cursor; 5 raitaa.
- GP5/MusicXML-tuonti ja `LIITÄ AUDIO` validoitu headless-selaimessa.
- Seek & Destroy -audion mitattu tempo 143,555 BPM; desimaali-BPM ja
  SIIRTO käytössä. Referenssitabissa ~9 tahtia enemmän kuin
  levytyksessä → rakenne-ero vaatii GP5-korjauksen tai SIIRTOn.

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
- **Seek & Destroy todistettu (19.10.):** toisto osuu 1:1 ainakin tahtiin
  149 asti asetuksilla **SIIRTO −0,75 / BPM 142**. GP5-datan korjaus ei
  ole prioriteetti: tabi on ohjelman lukemaa syötettä ja dataa korjataan
  vasta kun ohjelma on valmis. `SIIRTO alkaen tahdista X`
  (breakpoint-offset) jää myöhemmäksi.

## Uuden session aloitus

**Sano Cline:lle: `lue membank`.** Protokolla on `.clinerules/00-memory-bank.md`:ssä:
lue tämä kansio + säännöt, tarkista git/pytest ja jatka seuraavasta vaiheesta.
`docs/` ja `data/` ovat yksityisiä eivätkä kuulu gitiin.
