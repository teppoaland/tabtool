# 📍 Aktiivinen konteksti – AI TABTOOL

> **Versio:** `v2.18` (25.10.2026) · **Testit:** 275 passed
> **Git:** v1.23–v2.18 **pushattu** `origin/main`iin 25.10.2026 käyttäjän
> pyynnöstä. Vanha palautuspiste: **tagi `v1.99`**
> (`git reset --hard v1.99`, 23.10.2026). Älä pinnaa HEAD-hashia pysyvästi.
> **Push:** vain erillisestä pyynnöstä (20.10., 23.10. ja 25.10.2026).
> **Repo:** https://github.com/teppoaland/tabtool
> **Palvelin:** käyttäjän hallinnassa (`start.bat` / `stop.bat`); Cline ei
> käynnistä sitä taustalle eikä pysäytä ilman pyyntöä.

## Nyt

- 🔒 **ISO LUKKO (23.10.2026) – SOITTO ON VALMIS JA JÄÄDYTETTY.** Käyttäjä
  kuittasi: soitto toimii **99 %** tarkkuudella, mikä riittää. Soittoketjuun
  (kello, `seekTo`-inversio, `mediaHandler`, `syncPosition`, audio-eventit,
  transportin DOM-id:t, `.alphatab`-mitat, `/sync|tempo|section`) ei kosketa
  ilman lupaa; riskimuutos validoidaan käyttäjän kuuntelutestillä
  (Seek & Destroy, SIIRTO −0,75 / BPM 142). Katso
  `.clinerules/07-playback-frozen.md`.
- **Sanoituskokonaisuus valmis (v2.06–v2.18) – käyttäjän UI-/kuuntelutesti
  vielä kesken:**
  - Sanat ovat **sidecarissa** `data/lyrics/<tab_id>.json`
    (`{"tab_id","updated_at","locked","measures":{"10":"…"}}`), eivät GP5:ssä
    eikä tabin metassa. API `GET/PUT /api/tabs/{id}/lyrics` ja
    `PUT /api/tabs/{id}/lyrics/lock` (`{"locked": true|false}`);
    `app/lyrics.py` validoi ja kirjoittaa temp + `os.replace`. Lukittu
    sidecar vastaa tallennukseen **409**; lukitus ei koske tabia, sen
    toistoasetuksia eikä GP5/MusicXML/MIDI-tiedostoja. Tabin poisto poistaa
    sidecarin; lukittu tabi saa silti sanat.
  - Editori (`SANAT`): kelluva, ei modaali (soitto toimii takana),
    raahattava otsikosta, koko kahdesta nurkasta (nw/se), jakokahva
    (`barsHeight`). Soitto: `«` **ennen PLAYtä** (v2.16), PLAY/PAUSE,
    −5 s, +5 s. Tahtinumeron klikkaus hyppää ja **valitsee saman rivin**
    (v2.16); **maalatut sanat siirretään tahtiin** klikkauksella (v2.17) ja
    `Ctrl+Enter` tekee saman ankkuritahtiin ja siirtää ankkurin +1.
    `Lukittu`-rasti (v2.18) tallentaa nykyiset rivit ja lukitsee kerralla;
    lukittuna kenttä on read-only, TALLENNA pois, eikä tahtiklikkaus
    kirjoita rivejä.
  - Overlay `#lyrics-strip`: musta `#000`, sivupadding 3ch, pystypadding
    0.55em, fullscreenissa `96vw` ja nosto (`lyrics.offset_px`, oletus
    100 px). Koko `lyrics.scale` (oletus 200 %) → `--lyrics-scale`.
    **Edellistä riviä ei enää pidetä tyhjän tahdin yli** (v2.18): jos
    myöhempi rivi on olemassa, tahdissa näkyy lähtölaskenta seuraavaan
    riviin (9, 8, … 1) korostusvärillä (`is-cue`); viimeisen rivin jälkeen
    strip piiloutuu. Tyhjiä rivejä (`41 |`) ei tarvitse kirjoittaa – niitä
    ei tallenneta.
  - Sidecarit: Reino Nordin -tabi (97 riviä, tahdit 1–99) päätabille
    `668d62…` ja lukitulle kopiolle `33cbc8bf…`; W.A.S.P. *Animal*
    sanoitettu (lukitus on käyttäjän UI-toiminto). Sanoitukset ovat vain
    `data/`ssa – **eivät gitissä eivätkä tässä tiedostossa**
    (tekijänoikeus).
- **v2.14:n läksy – tahtihyppy:** älä laske tahdin aikaa vakiotempolla
  (`ticks × 60000 / (tempo × 960)`). Käytä `api.tickPosition`-tick-seekiä:
  alphaTab muuntaa tickin **tempokartalla** (Seek & Destroy: tahti 113 →
  208 BPM, 165 → 140 BPM), kuvaa sen backing track -ajaksi ja kutsuu itse
  `mediaHandler.seekTo`-inversiota. Vartiotesti
  `test_bar_seek_uses_the_tempo_aware_tick_path` estää paluun.

## Avoimet / myöhemmin

- **Käyttäjän validointi (sääntö #1):** v2.05–v2.18 UI- ja kuuntelutesti.
  Erityisesti: sanojen siirto klikkauksella ja `Ctrl+Enter`, `Lukittu`-rasti
  (tallennus + 409 + avaus), lähtölaskenta (1–9, 41–44, 76–79) ja tyhjennys
  viimeisen rivin jälkeen, overlay fullscreenissa, tahtihyppy Seek &
  Destroylla (116, 220) sekä referenssisynkka (10 s → tahti 7).
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
