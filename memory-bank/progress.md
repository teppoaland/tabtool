# 📊 Projektin edistyminen – AI TABTOOL

> **Versio:** `v2.18` (25.10.2026) · **Testit:** 275 passed ·
> **Git:** v1.23–v2.18 pushattu `origin/main`iin 25.10.2026.
> Yksityiskohtainen historia: `CHANGELOG.md`. Tässä tiedostossa on tila,
> päätökset ja seuraavat askeleet – ei lokia.

## 🔒 ISO LUKKO – soitto valmis ja jäädytetty (23.10.2026)

- Käyttäjä kuittasi: **kaikki soittoviat korjattu**, soitto toimii **99 %**
  tarkkuudella ja se riittää. Tila on lopullinen.
- **Soittoketjuun ei kosketa**: `notatedTempo`/`bpmDrift`/`barDurationMs`/
  `syncTimeMs`/`scoreEndTimeMs`, `mediaHandler.seekTo`-inversio,
  `syncPosition`, `seekTo`, `clearPlaybackRange`, `togglePlayback`,
  audio-eventit, transportin DOM-id:t, `.alphatab`-mitat ja
  `/sync|tempo|section`-reitit. Riskimuutos = lupa + regressiochecklist +
  käyttäjän kuuntelutesti (Seek & Destroy, SIIRTO −0,75 / BPM 142).
- Katso `.clinerules/07-playback-frozen.md`.

## Nyt – sanoitus (v2.06–v2.18)

- **Sidecar:** sanat `data/lyrics/<tab_id>.json`
  (`{"tab_id","updated_at","locked","measures":{"10":"…"}}`). Tabi pysyy
  lukusyötteenä: GP5/MusicXML/MIDI ja meta eivät muutu (testi vertaa tavut).
  API `GET/PUT /api/tabs/{id}/lyrics` + `PUT /api/tabs/{id}/lyrics/lock`;
  `app/lyrics.py` validoi (tahti 1–10000, rivi ≤ 300 merkkiä, ≤ 2000 riviä)
  ja kirjoittaa atomaarisesti. **Lukittu sidecar → tallennus 409**; lukitus
  ei koske tabia eikä toistoasetuksia. Tabin poisto poistaa sidecarin;
  lukittu tabi saa silti sanat.
- **Editori (`SANAT`)**: kelluva paneeli (ei modaalia → soitto toimii
  takana), raahaus otsikosta, koko kahdesta nurkasta (nw/se), jakokahva
  (`barsHeight`), tahtilista 14rem ja paneeli 46rem oletuksena. Soitto:
  `«` **ennen PLAYtä** (v2.16), PLAY/PAUSE, −5 s, +5 s. Tahtinumeron
  klikkaus = hyppy + saman rivin valinta; **maalatut sanat siirretään
  tahtiin** (v2.17) ja `Ctrl+Enter` tekee saman ankkuritahtiin (ankkuri +1
  per siirto). Kaksoisklikkaus lisää rivin `tahti | `.
- **Lukitus (v2.18):** `Lukittu`-rasti tallentaa rivit ja lukitsee sidecarin;
  lukittuna kenttä read-only, TALLENNA pois, tahtiklikkaus ei kirjoita.
  Rastin poisto avaa lukituksen.
- **Overlay**: `#lyrics-strip` fixed, `pointer-events: none`, musta `#000`,
  sivupadding 3ch, pystypadding 0.55em; fullscreenissa 96vw ja nosto
  `--lyrics-offset`. Koko `--lyrics-scale` (Settings `lyrics.scale`, oletus
  200 %). Tahdin numero luetaan `#bar-readout`-tekstistä
  (`MutationObserver`). **Tyhjää riviä ei pidetä** (v2.18): lähtölaskenta
  seuraavaan riviin (9…1, `is-cue` = vain väri) ja viimeisen rivin jälkeen
  strip piiloutuu. Tyhjiä rivejä (`41 |`) ei tallenneta.
- **Tahtihyppy**: `api.tickPosition = startTick` → alphaTab käyttää
  tempokarttaa (myös tempo-automaatiot) ja kutsuu itse
  `mediaHandler.seekTo`-inversiota. **Vakiotempo-laskenta kielletty**
  (v2.14-bugi: Seek & Destroy 116 → 117, 220 → 235).
- **Data:** Reino Nordin -tabin 97 riviä (tahdit 1–99, tauot 82–83)
  sidecarissa sekä päätabille `668d62…` että lukitulle kopiolle
  `33cbc8bf…`; W.A.S.P. *Animal* sanoitettu (lukitus UI:ssa). Sanoitukset
  **eivät ole gitissä eivätkä memory bankissa**.
- **Vartiotestit:** `test_lyrics_stay_outside_the_playback_chain`,
  `test_bar_seek_uses_the_tempo_aware_tick_path`,
  `test_bar_click_selects_the_matching_lyric_line`,
  `test_selected_words_move_into_the_pressed_bar`,
  `test_lyrics_gap_counts_down_and_finished_lyrics_can_be_locked`,
  `test_lyrics_lock_blocks_saves_until_it_is_opened`.
- **Avoin:** käyttäjän UI-/kuuntelutesti koko sanoituskokonaisuudelle
  (sääntö #1). Cline ei julista sitä valmiiksi ilman kuittausta.

## Versiohistoria (tiivis – detaljit `CHANGELOG.md`)

- **v1.55–v1.56** count-in; **v1.63** kirjaston metadata; **v1.67–v1.68**
  kanava + viritys; **v1.69** score-end guard; **v1.72** sormitusversiot.
- **v1.76–v1.80** `tab_edit` + `expand_repeat`/`trim_bars`/`retune_tab`.
- **v1.82–v1.90** LAN-kaukosäädin (`/remote`, QR, PIN, kolme tilaa).
- **v1.91** monotoninen syöttö; **v1.92** count-in palauttaa audiopaikan
  (ISO LUKKO); **v1.93–v1.98** remote-UI, nopeus 1 % + 10 % snap,
  `start.bat`; **v1.99** GP3-grace + tagi = vanha palautuspiste.
- **v2.00–v2.01** kirjastot bändin nimellä, yksi scrollbar.
- **v2.02** Settings (`/settings`, count-inin kestot, UI-kytkimet).
- **v2.03** kirjaston Tiedot + lähdemeta (`artist_override`, URLit).
- **v2.04** versiovalinnan varmistus + varmuuskopio/palautus.
- **v2.05** LIBRARY yläpalkkiin (oranssi), PLAY = pelkkä toisto.
- **v2.06** sanat sidecariin; **v2.07** kelluva editori; **v2.08** koko
  säädettävä + tekstin koko Settingsiin; **v2.09** fullscreen-nosto;
  **v2.10** musta tausta; **v2.11** kaksi resize-kulmaa; **v2.12**
  soittonapit + tahtiklikki; **v2.13** tahtilista + jakokahva; **v2.14**
  tick-pohjainen tahtihyppy (tempo-automaatiot); **v2.15** neutraali
  sanoitusesimerkki (sanoitukset pois julkisesta reposta); **v2.16** `«`
  ennen PLAYtä + tahtiklikki valitsee rivin; **v2.17** maalatut sanat
  siirretään tahtiin + `Ctrl+Enter`; **v2.18** sanojen lukitus + taukojen
  lähtölaskenta ja tyhjennys.

## Tunnetut rajoitukset

- AI-transkriptio on luonnos: särö, akordit ja nopeat soolot virheellisiä;
  Basic Pitch ei ole kitarakohtainen → otteet voivat poiketa opitusta.
- Standard E -alueen ulkopuoliset nuotit pudotetaan varoituksella.
- Tempo voi olla half/double-time; AI-BPM on arvio (TAB BPM/Nopeus korjaa).
- SIIRTO-askel on 0,25 tahtia (= 1 isku); hienompi säätö on sääntö #1:n
  ydintä. Pickup-tabissa SIIRTO/KOHDISTA voimistuvat 8×/16×.
- Rummut vaativat oman mallin; Spotify on Phase 3.
- GP5 + oma audiotiedosto ei yhdisty yhdellä toiminnolla (audiolähde on
  YouTube-linkki); GP-linkki vaatii julkisen http(s)-osoitteen.
- Ikärajoitettu YouTube vaatii evästeet (`--cookies-from-browser`).
- Kappaleen poisto jättää MP3-kuunteluversion ja toisen tabin audion.
- `VALITSE TÄMÄ` kirjoittaa GP5:n versio-JSON:sta → Vocals-raita katoaa
  siitä tabista (siksi erillinen lukittu sanakopio).
- Referenssitabissa 258 tahtia vs. AI-tabi 249 → rakenne-ero vaatii
  GP5-korjauksen tai SIIRTOn (SYNC korjaa vain lineaarisen heiton).
- Sanojen lähtölaskenta näyttää koko tauon pituuden (esim. 20 → 1); ylärajaa
  ei ole. Sanojen siirto/liittäminen tehdään ohjelmallisesti, joten selaimen
  Ctrl+Z ei välttämättä palauta edellistä tilaa. Sanojen lukitus on
  sidecar-kohtainen (`locked`), ei tabin lukitus.

## Seuraavaksi

1. **Käyttäjän validointi** sanoituskokonaisuudelle (rule 07) ja sen
   jälkeen mahdolliset hienosäädöt (esim. tahtilistan oletuskorkeus).
2. **Pickup-varotin** (`barDurationMs`/`ticksPerBar`): vaatii luvan,
   regressiochecklistin ja kuuntelutestin; sitä ennen data-kierto
   `scripts/trim_bars.py --bars 1`.
3. **Tuonnin laatuapurit:** duplikaatit (SHA-256 / sama artisti+biisi),
   tabin pituus vs. audion kesto, pickup-varoitus.
4. **Refinger/playability loppuun:** automaattinen paras versio ja turhien
   nuottien karsinta per tahti/fraasi.
5. **Remote-puhelintesti** (v1.82–v1.90) – käyttäjän kuittaus.
6. Vasta sitten **Spotify Phase 3** (PKCE, haku/metadata, SDK/Connect).

## Data ja git

- `data/` (audio, stemmit, tabit, `lyrics/*.json`, SQLite, tokenit) ja
  `docs/` ovat gitignoroituja; ne tarvitsevat erillisen varmuuskopion.
- `scripts/build_kiss_legend.py` on gitignoroitu (koko kappaleen nuottidata).
- Ulkoinen arkisto `D:\tabtool_files\` (`TABTOOL_EXTERNAL_DIR`) sisältää
  YouTube-audiot, MP3-kuunteluversiot ja tuodut GP5/MusicXML:t.

