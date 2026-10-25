# 📍 Aktiivinen konteksti – AI TABTOOL

> **Versio:** `v2.15` (25.10.2026) · **Testit:** 270 passed
> **Git:** v1.23–v2.15 **pushattu** `origin/main`iin 25.10.2026 käyttäjän
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
- **Sanoituskokonaisuus valmis (v2.06–v2.15) – käyttäjän UI-/kuuntelutesti
  vielä kesken:**
  - Sanat ovat **sidecarissa** `data/lyrics/<tab_id>.json`
    (`{"tab_id","updated_at","measures":{"10":"…"}}`), eivät GP5:ssä eikä
    tabin metassa. API `GET/PUT /api/tabs/{id}/lyrics` (`app/lyrics.py`:
    validointi, temp + `os.replace`); tabin poisto poistaa sidecarin;
    lukittu tabi saa silti sanat.
  - Editori (`SANAT`): kelluva, ei modaali (soitto toimii takana),
    raahattava otsikosta, koko **kahdesta nurkasta** (nw/se), jakokahva
    tahtilistan ja tekstikentän välillä (`barsHeight` muistissa), soittonapit
    PLAY/PAUSE, «, ±5 s. Tahtinumeron klikkaus hyppää, kaksoisklikkaus lisää
    rivin `tahti | `.
  - Overlay `#lyrics-strip`: musta `#000`, sivupadding 3ch, pystypadding
    0.55em, fullscreenissa `96vw` ja nosto (`lyrics.offset_px`, oletus
    100 px). Koko `lyrics.scale` (oletus 200 %) → CSS `--lyrics-scale`,
    nosto → `--lyrics-offset`. Kaikki vain DOM/CSS:ää.
  - Reino Nordin -tabi: **97 riviä tahdeille 1–99** (tauot 82–83), viety
    sidecariin sekä päätabille `668d62…` että lukitulle kopiolle
    `33cbc8bf…`. Sanoitukset ovat vain `data/`ssa – **eivät gitissä eivätkä
    tässä tiedostossa** (tekijänoikeus).
- **v2.14:n läksy – tahtihyppy:** älä laske tahdin aikaa vakiotempolla
  (`ticks × 60000 / (tempo × 960)`). Käytä `api.tickPosition`-tick-seekiä:
  alphaTab muuntaa tickin **tempokartalla** (Seek & Destroy: tahti 113 →
  208 BPM, 165 → 140 BPM), kuvaa sen backing track -ajaksi ja kutsuu itse
  `mediaHandler.seekTo`-inversiota. Vartiotesti
  `test_bar_seek_uses_the_tempo_aware_tick_path` estää paluun.

## Avoimet / myöhemmin

- **Käyttäjän validointi (sääntö #1):** v2.05–v2.14 UI- ja kuuntelutesti.
  Erityisesti: tahtihyppy Seek & Destroylla (116, 220), overlay
  fullscreenissa, editorin jako/koko, ja referenssisynkka (10 s → tahti 7).
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
