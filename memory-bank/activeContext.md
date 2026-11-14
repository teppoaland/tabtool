# 📍 Aktiivinen konteksti – AI TABTOOL

> **Versio:** `v2.30` (14.11.2026) + PianoCapture `0.5.0` · **Testit:** 325 passed
> **Git:** kaikki **pushattu** `origin/main`iin 14.11.2026 (`77ee79f`);
> intro-sivu repo `52f2de9`; työpuu clean.
> **Palautuspisteet:** tagi `v2.23` (25.10.2026, “hyvä paketti”) ja vanhempi
> tagi `v1.99` (`git reset --hard v1.99`). Älä pinnaa HEAD-hashia pysyvästi.
> **Push:** vain erillisestä pyynnöstä (20.10., 23.10., 25.10. ja 14.11.2026).
> **Repo:** https://github.com/teppoaland/tabtool
> **Palvelin:** käyttäjän instanssi on hänen CMD-ikkunassaan (portti 8000);
> **agentti saa ajaa oman instanssin toisella portilla** (päivitetty 1.11.2026).
> PianoCapture: oma instanssi portilla 8020 (`start-piano.bat`).

## Nyt

- **v2.29–v2.30 – SANAT koko näytössä ja esikatselu (14.11.2026).**
  Natiivi fullscreen piirtää vain elementin alipuun, joten editori siirretään
  `#viewer-section`in lapseksi (`adoptLyricsDialog`) ja takaisin.
  **ESIKATSELU** = pelkät sanat: koko sanoitus listana, nykyinen rivi
  korostettuna ja keskellä, rivi seuraa `#bar-readout`ia. Ei uusia
  kytkentöjä soittoketjuun. Testit 312.
- **PianoCapture 0.1–0.5.0 (14.11.2026).** Erillinen app `piano/`
  (portti 8020, `data_piano/`): YouTube-pätkä → piano-intro ja bändin
  sisääntulo → Basic Pitch piano-parametreilla → 88 koskettimen canvas.
  KIERTO (onset-autokorrelaatio), MP3/MIDI, Taustaääni, LAN-QR,
  `/?piece=<id>`, työpöydän kuvake. **v0.5:** ohjeen voi kuunnella
  (`render.py` → `guide.wav/mp3`, OHJE/ALKUPERÄINEN-painikkeet,
  parannettu piano-synteesi). 13 piano-testiä; yhteensä **325**.
  Käyttäjä testasi PC:llä: toimii; Android-testi pianolla vielä edessä.
  Ks. `techContext.md` ja `piano/README.md`.
- **Intro-sivu (14.11.2026).** PianoCapture-kortti, 3 kuvaa, laskurit
  02 → 03, ticker, rekrytoijatiivistelmä ja boot-rivi; audit 0 virhettä.
  Kuvista siivottiin LAN-IP ennen julkaisua. `52f2de9` pushattu.
- **v2.28 – metadata on referenssi (1.11.2026).** Katselimen metadatarivi
  (`#tab-meta`) ja Tiedot näyttävät tabin **lähtö-BPM:n**
  (`meta.original_bpm`, kirjoitetaan kerran generoinnissa ja tuonnissa) eivätkä
  peilaa työnopeutta; kun TAB BPM on säädetty, rivi näyttää molemmat
  (`160 BPM (nyt 166)`). `/tempo` ei enää korvaa referenssiä, vain
  `meta.bpm`in; ennen v2.28 luodut tabit saavat lähtöarvon ensimmäisellä
  tallennuksella. `Nopeus` ei kirjoita metaan. Testit **310**
  (`tests/test_tab_bpm_reference.py`).
- **Whiplash (1.11.2026) – oikea tempo 160, ei 175.** Audio mitattiin
  librosalla: **161,5 BPM** (koko raita ja 30–200 s erikseen). 175 oli tabin
  tahdin 1 arvio, ei kappaleen tempo; tabin oma tempoautomatiikka sanoo
  rungoksi 160. Käyttäjä ajaa tabia **166 BPM:llä** (sanoitukset ehtii nähdä
  juuri ennen laulua) – se on työnopeus, ei referenssi: `meta.bpm = 166`,
  `meta.original_bpm = 160`, tempoautomatiikka **päällä**, SIIRTO **0,5**.
  Sanoitussidecar on lukittu eikä muuttunut.
- **AVOIN – kellon loppuvartija ja tempoautomatiikka (1.11.2026).**
  `scoreEndTimeMs()` laskee partituurin lopun **vakiotemolla**, joten
  temposkarttaa käyttävä tabi leikkautuu ennen loppua: Whiplash pysähtyi
  175 BPM:llä tahtiin **150** (20,6 s puuttui) ja 166 BPM:llä tahtiin **158**.
  Korjaus (v2.31, vaatii luvan): loppuaika temposkartasta **vain**
  `syncTimeMs()`in rajaan, jotta `scoreEndTimeMs()`/`backingTrackDuration` ja
  1:1-kartoitus pysyvät ennallaan; S&D:n raja siirtyisi 414,8 → 410,4 s, joten
  käyttäjän kuuntelutesti tarvitaan.
- **v2.27 – tempoautomatiikka (1.11.2026).** Whiplashin (3f74d906…) TAB BPM
  ei vaikuttanut mihinkään: GP5:ssä on **tempoautomatiikka** (tahti 1: 200,
  tahti 6: 160, lineaarinen), jota alphaTab noudattaa perustempon sijaan.
  Mitattu: BPM 100 vs 200 siirsi kursoria 3 tahtia 75:n sijaan; tehollinen
  suhde 0,8 = 160/200. **Korjaus:** Tiedot-dialogissa rasti
  **Tempoautomatiikka** (per tab, oletus päällä) → kun se otetaan pois,
  partituuri parsitaan `ScoreLoader`illa, automatiikka pudotetaan ja
  `renderScore` ajetaan; tahti
  1:n alkutempo säilytetään (muuten alphaTab putoaa 120 BPM:iin). **Oletuspolku
  on `instance.load(bytes)`** — koko tabin strippaus rikkoi Seek & Destroyn
  (sen temponvaihdot tahteissa 113 ja 165 ovat oikeita). Tiedot näyttää
  automatiikan määrän ja viimeisen tahdin; BPM-rivillä kerrotaan, ohjaako
  automatiikka toistoa.
- **S&D kuitattu (1.11.2026).** Käyttäjä testasi: soitto toimii ja soi
  loppuun asti; lopussa ~4 nuottia heittoa on **lähdedataa** (tabi ei ole
  täydellinen), ei kelloa. Aiempi alun horjunta (bar 5–25) ei enää
  ilmennyt; jos se palaa, mittaus tehdään jäljittimellä (20 näytettä/s:
  `audio.currentTime`, `api.tickPosition`, syötetty aika) käyttäjän
  selaimessa, koska headlessissä audio ei etene.
- 🔒 **ISO LUKKO (23.10.2026) – SOITTO ON VALMIS JA JÄÄDYTETTY.** Käyttäjä
  kuittasi: soitto toimii **99 %** tarkkuudella, mikä riittää. Soittoketjuun
  (kello, `seekTo`-inversio, `mediaHandler`, `syncPosition`, audio-eventit,
  transportin DOM-id:t, `.alphatab`-mitat, `/sync|tempo|section`) ei kosketa
  ilman lupaa; riskimuutos validoidaan käyttäjän kuuntelutestillä
  (Seek & Destroy, SIIRTO −0,75 / BPM 142). Katso
  `.clinerules/07-playback-frozen.md`.
- **Toistomerkit (31.10.2026):** Slayer – Dead Skin Mask pysähtyi tahtiin 68
  (96 kirjoitettua tahtia, 8 toistolohkoa = 143 soitettua). Kello laskee vain
  kirjoitetut tahdit, joten korjaus tehtiin datana:
  `scripts/expand_repeats.py --tab <id>` → 143 tahtia, validointi soitettua
  järjestystä vasten. Soittoketjuun ei koskettu. Jos tabin loppu ja audio
  eroavat (~13 s tässä), se on lähdedataa eikä kelloa.
- **v2.25 – oma audio GP-tabiin + valinnan nollaus (31.10.2026).** Kaksi
  korjausta samasta oivalluksesta: (1) *Oma audio* -kentän perässä on **×**,
  joka tyhjentää valinnan (selain säilyttää file-valinnan modaalin
  sulkemisen jälkeen); (2) GP3/GP4/GP5/MusicXML-tabiin voi liittää **oman
  MP3/WAV-tiedoston** – GP-lähde ei enää vaadi YouTube-linkkiä.
  `POST /api/tabs/import` ottaa valinnaisen `audio_file`in ja
  `POST /api/jobs` hyväksyy ladatun audion `gp5_url`in kanssa;
  `_queue_upload_audio_job` (main.py) tekee saman audio-only-jobin
  (`audio_only` + `attach_tab_id`) kuin YouTube-polku, ja
  `jobs.run_audio_job` ratkaisee ladatun tiedoston `data/`-juuresta.
  Väärä tiedostotyyppi → **415** ennen tuontia, audio + YouTube yhtä aikaa
  → **422**, `meta.audio_source_type = "upload"`, `meta.mp3_created` vain
  YouTube-lataukselle. Soittoketjuun (kello, `seekTo`-inversio,
  `mediaHandler`, transportin id:t, `.alphatab`) ei koskettu; uusi CSS on
  `.file-pick`/`.file-clear`. Testit **292**
  (`tests/test_import_own_audio.py`).
- **v2.24 – `«` katselimen PLAYn edessä (käyttäjä kuitannut 25.10.2026).**
  `#seek-start` (`«`) hyppää kappaleen alkuun samalla `seekTo(0)`lla kuin
  sanoituseditorin `#lyrics-start` ja remoten `seek 0`. `«` ja PLAY ovat
  samassa `.viewer-start`-flex-solussa, joten `.viewer-bar`in grid
  (`auto minmax(0, 1fr) auto`), otsikkosarake ja lukitut id:t pysyivät
  ennallaan; count-in jää tarkoituksella päälle. Vartiotesti
  `tests/test_viewer_seek_start.py`. Soittoketjuun ei koskettu.
- **Sanoituskokonaisuus valmis (v2.06–v2.23) – tarkistuslista referenssinä,
  jos sanoja muokataan:**
  - Sanat ovat **sidecarissa** `data/lyrics/<tab_id>.json`
    (`{"tab_id","updated_at","locked","notes","measures":{"10":"…"}}`), eivät
    GP5:ssä eikä tabin metassa. API `GET/PUT /api/tabs/{id}/lyrics` ja
    `PUT /api/tabs/{id}/lyrics/lock`; `app/lyrics.py` validoi ja kirjoittaa
    temp + `os.replace`. Lukittu sidecar vastaa tallennukseen **409**;
    lukitus ei koske tabia, sen toistoasetuksia eikä GP5/MusicXML/MIDIä.
    Tabin poisto poistaa sidecarin; lukittu tabi saa silti sanat.
  - Editori (`SANAT`): kelluva, ei modaali (soitto toimii takana),
    raahattava, koko kahdesta nurkasta (nw/se), jakokahva (`barsHeight`).
    Soitto: `«` ennen PLAYtä (v2.16), PLAY/PAUSE, −5 s, +5 s. Tahtiklikkaus
    hyppää ja valitsee saman rivin (v2.16); maalatut sanat siirretään
    tahtiin (v2.17) ja `Ctrl+Enter` siirtää ankkuria +1. **`JAA RIVIT`
    (v2.22) numeroi koko liitetyn lohkon** yhdellä kertaa (valinta tai
    kaikki numeroimattomat rivit) alkaen ankkuritahdista. **Muistiinpanot
    (v2.20)** ovat vapaa teksti samassa sidecarissa (`notes`, max 4000
    merkkiä) – lähde ja avoimet korjaukset. `Lukittu`-rasti (v2.18)
    tallentaa ja lukitsee kerralla (kentät read-only, TALLENNA pois).
  - Overlay `#lyrics-strip`: musta `#000`, sivupadding 3ch, pystypadding
    0.55em, fullscreenissa `96vw` ja nosto (`lyrics.offset_px`, oletus
    100 px). Koko `lyrics.scale` (oletus 200 %) → `--lyrics-scale`.
    Tyhjää riviä ei pidetä (v2.18): seuraavaan riviin näytetään
    lähtölaskenta (9…1, `is-cue` = väri) ja viimeisen rivin jälkeen strip
    piiloutuu. **Sneak peek (v2.19)**: seuraava rivi 50 % pienempänä yhtä
    tahtia etukäteen; sijainti Settingsistä (`lyrics.sneak_position`,
    oletus `below`, vaihtoehto `above`; v2.23).
  - Sidecarit: Reino Nordin -tabi (97 riviä, tahdit 1–99) päätabille
    `668d62…` ja lukitulle kopiolle `33cbc8bf…`; W.A.S.P. *Animal*
    sanoitettu; **Dr. Feelgood kesken** (135 tahtia, 5 riviä tahdeilla
    24/26–29, muistiinpanoissa 86 riviä lähdetekstiä – jatka `JAA RIVIT`
    -toiminnolla tahdista 30). Sanoitukset ovat vain `data/`ssa – **eivät
    gitissä eivätkä tässä tiedostossa** (tekijänoikeus).
- **v2.14:n läksy – tahtihyppy:** älä laske tahdin aikaa vakiotempolla
  (`ticks × 60000 / (tempo × 960)`). Käytä `api.tickPosition`-tick-seekiä:
  alphaTab muuntaa tickin **tempokartalla** (Seek & Destroy: tahti 113 →
  208 BPM, 165 → 140 BPM), kuvaa sen backing track -ajaksi ja kutsuu itse
  `mediaHandler.seekTo`-inversiota. Vartiotesti
  `test_bar_seek_uses_the_tempo_aware_tick_path` estää paluun.

## Avoimet / myöhemmin

- **PianoCapture – seuraavat (omat 0.x-versiot):**
  - käyttäjän Android-testi pianon ääressä (PC:llä kuitattu toimivaksi)
  - haamunuotit: "siivoa haamut" -suodatin tai pianospesifi malli
  - A–B-loop raahauksella; FI/EN kielituki vasta kun TabTool on valmis
  - tunnettu raja: Basic Pitch keksii harmonisia; ohje on suunta, ei
    virheetön transkriptio (käyttäjän hyväksymä).
- **Käyttäjän validointi (sääntö #1):** v2.24 (`«` alkuun) kuitattu
  25.10.2026 (”Kaikki toimii”). Sanoitusosion lista pysyy referenssinä, jos
  sanoja muokataan: sanojen siirto klikkauksella ja `Ctrl+Enter`, `JAA RIVIT`
  (tahdista 30 Dr. Feelgoodilla), muistiinpanot, `Lukittu`-rasti (tallennus
  + 409 + avaus), lähtölaskenta (1–9, 41–44, 76–79), sneak peek molemmissa
  asennoissa (`lyrics.sneak_position`), overlay fullscreenissa, tahtihyppy
  Seek & Destroylla (116, 220) sekä referenssisynkka (10 s → tahti 7).
- **Pickup-varotin soittokelloon (vaatii luvan):** `barDurationMs()` ja
  `ticksPerBar()` ottavat tahdin pituuden kahdesta ensimmäisestä tahdista;
  anacrusis-tabissa SIIRTO/KOHDISTA 8×/16× liian voimakkaita. Data korjataan
  `scripts/trim_bars.py --bars 1`llä; koodikorjaus vaatii luvan + koko
  regressiochecklistin + kuuntelutestin.
- **W.A.S.P.:** kirjastossa `8e8dfa0f…` *Animal (Fuck Like A Beast)*
  (`Eb Standard`); Songsterr näyttää D standardia → ero on tab-datassa, ei
  synkassa. Uusi tuonti vain jos viritys/rakenne kaipaa korjausta.
- **Dr. Feelgood – valmis (v1.76–v1.78):** toisto kirjoitettu tahdeiksi,
  ylimääräiset tahdit ja 1/16-pickup poistettu.
- **Refinger/playability:** asemaprofiilit, helpoin arvio, turhien nuottien
  karsinta – ei koodia vielä.
- **AI-transkriptio (Basic Pitch)** on luonnos; referenssitabit + TuxGuitar
  apuna, ei Guitar Pro -pakkoa.
- **Referenssitabi vs. audio:** Seek & Destroy 258 tahtia, BPM 143,5
  (GP5 144), AI-tabi 249 tahtia → rakenne-ero vaatii GP5-korjauksen tai
  SIIRTOn. Layout 1600/1600 px (ei sivuttaisvieritystä).
- **Spotify Phase 3**, retention, bass/laulu, rummut (ADTOF/Omnizart),
  manuaalinen editori.
- **LAN-kaukosäädin (v1.82–v1.90)** odottaa käyttäjän puhelintestiä.
- **Seek & Destroy referenssi:** toisto 1:1 vähintään tahtiin 149
  (SIIRTO −0,75 / BPM 142). GP5-dataa ei korjata: tabi on syötettä.
  `SIIRTO alkaen tahdista X` (breakpoint-offset) myöhemmin.

## Uuden session aloitus

**Sano Cline:lle: `lue membank`.** Protokolla on
`.clinerules/00-memory-bank.md`:ssä: lue tämä kansio + säännöt, tarkista
git/pytest ja jatka seuraavasta vaiheesta.
`docs/` ja `data/` ovat yksityisiä eivätkä kuulu gitiin.
