# 📜 CHANGELOG – AI TABTOOL

> AI TabTool käyttää `1.x`-versiosarjaa. Aloitus `v1.00`.

## v1.83 – 23.10.2026

- **Yksi käynnistin.** `start-lan.bat` poistettu – se oli turha. `start.bat`
  sitoo aina `0.0.0.0:8000`:aan, tulostaa koneen LAN-osoitteet ja avaa
  TV-näkymän. Ei lippuja eikä toista skriptiä.
- **QR suoraan `/remote`-sivulle.** 150 × 150 px QR ja sen alla osoite
  `http://<LAN-IP>:8000/remote`; piilotettu kapeilla (puhelin) näytöillä,
  jotta ohjaimet pysyvät selkeinä. QR encodaa aina sen hetkisen LAN-IP:n,
  ei `127.0.0.1`:tä, joten DHCP-osoitteen vaihtuminen ei haittaa.
- **`/connect`-sivu poistettu** (`connect.html`/`connect.js`): iso QR oli
  ylimääräinen mutka. `GET /connect` → 404.
- `scripts/lan_addresses.ps1` tulostaa vain `LAN: http://…/remote`.
- `app.js` ei muuttunut; `index.html` sai vain `?v=1.83`-leimat.
  `remote.html`, `remote.js` ja `style.css` (uudet `.remote-qr`-luokat)
  muuttuivat → vaatii käyttäjän kuuntelu-/tabsynkkitestin (sääntö #1).
- 1 uusi testi (remote-sivun QR-palsta), `/connect`-testi vaihdettu
  404-testiksi → **176 pytest-testiä**.

## v1.82 – 23.10.2026

- **LAN-kaukosäädin ja QR-pariutus.** `start-lan.bat` (`start.bat lan`)
  sitoo palvelimen `0.0.0.0`:aan, tulostaa koneen LAN-osoitteet ja avaa
  QR-sivun. QR generoidaan pyydettäessä sen hetkisestä osoitteesta
  (`segno`), joten DHCP-osoitteen vaihtuminen ei riko pariutusta; QR
  osoittaa `/remote`iin tai PINin kanssa `/lan?t=<istuntotoken>`iin.
- **Kaukosäätö ilman ydinmuutoksia.** `app/remote.py` pitää komentojonon
  (`play`/`pause`/`toggle`, `seek`, `seek_rel`, `rate`, `select_tab`) ja
  TV:n raportoiman tilan. `app/static/remote-bridge.js` pollaa komennot ja
  klikkaa olemassa olevia transport-nappeja; `app.js`, `mediaHandler`,
  `seekTo` ja `syncTimeMs` pysyvät koskemattomina (sääntö #1). Komento
  vanhenee 60 s:ssa eikä jono toista vanhaa PLAYta.
- **Puhelin-näkymä** (`/remote`): PLAY/PAUSE, ±5 s, toistokohta, Nopeus,
  kirjaston kappalevalinta ja TV:n tila. Puhelin ei toista audiota.
- **Valinnainen LAN-PIN** (`TABTOOL_LAN_PIN`): localhost ohittaa, muut
  vaativat HttpOnly-evästeen (SHA-256-tiiviste, ei PINiä evästeeseen),
  10 yritystä / 60 s. Ilman PINiä LAN sallitaan konsolivaroituksella.
- `requirements.txt` + `THIRD_PARTY_NOTICES.md`: `segno==1.6.6`
  (BSD-3-Clause, puhdas Python, ei npm/build-vaihetta).
- 23 uutta testiä → **175 pytest-testiä**. `index.html` sai yhden
  `remote-bridge.js`-script-rivin; transportin DOM-id:t, `.alphatab`-mitat
  ja `style.css`n olemassa olevat säännöt pysyivät ennallaan. Vaatii
  käyttäjän kuuntelu-/tabsynkkitestin (sääntö #1).

## v1.81 – 22.10.2026

- **COUNT-IN-kytkin (ON/OFF).** FULLSCREEN-napin alle tuli pieni liukukytkin
  (`#countin-toggle` + `#countin-state`), joka näkyy sekä normaalissa että
  koko näytön näkymässä. Oletus **ON**, valinta tallentuu selaimeen
  (`tabtool:countIn`). Kytkin luetaan **vain** `shouldRunCountIn()`issa, joten
  `togglePlayback`, `mediaHandler`, `seekTo`, `syncTimeMs` ja itse
  laskenta-animaatio pysyvät koskemattomina; kesken laskennan pois
  kytkeminen peruu laskennan (`cancelCountIn`).
- `index.html`: FULLSCREEN-nappi ja kytkin ovat samassa `.viewer-corner`
  -lohkossa – ruudukkoon ei tullut uutta saraketta, joten TAB-alueen mitat
  eivät muutu.
- 2 uutta guard-testiä (`countInEnabled` vain `shouldRunCountIn`issa;
  kytkin on FULLSCREEN-napin alla ja oletuksena päällä) → **152
  pytest-testiä**. Vaatii käyttäjän kuuntelu-/tabsynkkitestin (sääntö #1).

## v1.80 – 22.10.2026

- **Virityksen vaihto säilyttäen musiikki** (`app.tab_edit.retune_tracks`,
  `scripts/retune_tab.py`): vaihtaa raidat, joiden avoimet kielet vastaavat
  lähtöviritystä, uuteen viritykseen ja siirtää **jokaisen nauhan saman
  verran kuin sen kieli** (`fret_new = sävel − uusi avoin kieli`), joten
  soivat sävelet pysyvät identtisinä. Muut raidat (laulu, basso, rummut)
  jätetään koskematta. Skripti tulostaa `--dry-run`illa raitamäärän,
  siirrettyjen nuottien määrän ja suurimman nauhan, varmuuskopioi GP5:n,
  päivittää virityslabelin ja validoi tuloksen vertaamalla jokaisen nuotin
  soivan sävelen ennen/jälkeen.
- **Volbeat `I Only Wanna Be With You` (uusin tabi, 116a1fa3…) kirjoitettu
  D Standardiin:** kitararaidat `DADGBE` → `DGCFAD`, **2529 nuottia siirretty**
  (5. kieli 0 → 2 jne.), suurin nauha 13, sävelet ennallaan. BAR 7 alkaa nyt
  `0/2` (6. kieli 0, 5. kieli 2) ja BAR 9–10 `0/2 … 4/2 5/3 6/4`.
  `tuning_label` = `D Standard · DGCFAD` (manuaalinen override poistettu,
  koska data on nyt oikeasti D standard).
- 2 uutta testiä (`retune_tracks`) → **150 pytest-testiä**.

## v1.79 – 22.10.2026

- **Korjaus: viritys luetaan kitararaidasta, ei raidasta 0.**
  Moniraitaisessa GP5:ssä ensimmäinen raita on usein laulu tai koskettimet, ja
  `tuning_label` tuli siitä (esim. kitara Drop D:ssä näkyi `Standard E`).
  Uusi `app.tuning.open_strings()` valitsee 6-kielisen raidan, jossa on eniten
  nuotteja (rummut ohitetaan, koska niiden kielet ovat 0). Käytössä tuonnissa
  (`app/tab_import.py`) ja backfillissä.
- `scripts/backfill_tuning.py`: `--force` laskee labelit uudelleen, lukee
  GP5:n UTF-8 → cp1252 -fallbackilla ja **ohittaa tabit, joilla on manuaalinen
  `tuning_override`**.
- **Volbeat-data:** molemmat `I Only Wanna Be With You` -tabit näyttivät
  `Standard E`, vaikka kitara on Drop D. Nyt label on `Drop D · DADGBE`
  (kumpikin). Uusin tabi (22.10., kanava "Austrian Stuff") sai manuaalisen
  virityksen **`D Standard · DGCFAD`** – GP5:n kielet ovat edelleen DADGBE,
  eli ylikirjoitus on tabin viritystieto (näkyy kirjastossa ja
  AI-generoinnissa), ei soivaa dataa.
- 2 uutta testiä (`open_strings`) → **148 pytest-testiä**.

## v1.78 – 22.10.2026

- **Korjaus: pickup-tahdin poisto ei siirrä kappaletta ajassa.**
  `remove_bars` pitää nyt ensimmäisen jäljelle jäävän tahdin absoluuttisen
  alun (`header.start`), jotta anacrusis-tahdin poisto ei nytkäytä koko
  biisiä. 1 uusi testi.
- **Dr. Feelgood: 1/16-anacrusis (BAR 1) pois.** Tahdissa 1 oli yksi avoin
  D-kieli (tick 960) ja raita 2 tyhjä, joten se näkyi pelkkänä suikaleena.
  Tärkeämpää: `barDurationMs()` ja `ticksPerBar()` laskevat tahdin pituuden
  kahdesta ensimmäisestä tahdista, joten 1/16-alkutahdin takia **SIIRTO oli
  tässä tabissa 16× liian voimakas** (240 tickiä = 133 ms "tahti").
  39 "tahtia" oli siis ~2,4 oikeaa tahtia. Nyt tabi on 135 tahtia, tahdin
  pituus 3840 tickiä (oikea 4/4) ja SIIRTO toimii oikeina tahteina.
  1. nuotti = riffin alku, SYNC/SIIRTO = 0.
- Huom: GP5:n ensimmäinen tahti alkaa aina tickistä 960, joten anacrusiksen
  poisto siirtää sisältöä 240 tickiä (0,13 s) aikaisemmaksi. Jos sen kuulee,
  SYNC +0,05 % kompensoi; vaihtoehtoisesti koko anacrusis palautetaan
  varmuuskopiosta ja korjataan `barDurationMs`/`ticksPerBar` (koskematon
  soittoketju – vaatii erillisen luvan).
- 1 uusi testi → **146 pytest-testiä**.

## v1.77 – 22.10.2026

- **Ylimääräisten tahtien poisto** (`app/tab_edit.remove_bars`,
  `scripts/trim_bars.py`): katselimen kello seuraa kirjoitettua aikajanaa,
  joten tabin häntä audion yli piti saada pois. `--bars "137,138"` (tai
  `"136-138"`) poistaa tahdit kaikilta raidoilta, numeroi loput uudelleen ja
  laskee tahtien alut; GP5 validoidaan lukemalla takaisin ja alkuperäinen
  varmuuskopioidaan `data/backups/`. `--reset-sync` nollaa SYNC/SIIRTO-arvot.
- **Dr. Feelgood siistitty:** 138 → **136 tahtia** (2551 nuottia). Audion
  musiikki päättyy 287,74 s, mutta tabi jatkui 291,6 s asti eli kaksi
  viimeistä tahtia (137–138) osuivat kokonaan audion hiljaiseen häntään.
  Nyt tabi päättyy **287,39 s**, SIIRTO/SYNC = 0. (Mitattu audion tempo on
  112,35 BPM; GP5:ssä 113 – ero on alle 1 % ja korjattavissa TAB BPM:llä.)
- `scripts/expand_repeat.py` käyttää samoja `app/tab_edit`-apureita
  (`read_song`, `backup_file`, `resolve_tab_gp5`) eikä omaa kopiota.
- 3 uutta testiä (`remove_bars`) → **145 pytest-testiä**. Vaatii käyttäjän
  kuuntelu-/tabsynkkitestin (sääntö #1).

## v1.76 – 22.10.2026

- **Toiston kirjoittaminen auki** (`app/tab_edit.py`, `scripts/expand_repeat.py`):
  katselimen kello laskee partituurin keston kirjoitetuista tahdeista
  (`scoreEndTimeMs`), ja alphaTab laajentaa toistot vasta toistossa. GP5:n
  `bar 2 ×17` jätti siksi partituurin 15 tahtia lyhyemmäksi eikä SIIRTO
  korjannut sitä. Skripti kirjoittaa toistetun tahdin tahdeiksi, poistaa
  toistomerkit ja numeroi tahdit uudelleen; tulos validoidaan lukemalla GP5
  takaisin ja alkuperäinen varmuuskopioidaan `data/backups/`.
- **Dr. Feelgood (Mötley Crüe) korjattu datasta:** bar 2 ×2 → **17
  kirjoitettua tahtia** (122 → 138 tahtia, 2471 → 2615 nuottia, `×17`-teksti
  vain ensimmäisessä tahdissa), toistomerkit poistettu ja SYNC/SIIRTO
  nollattu. Partituurin loppu 291,6 s vs. audio 290,0 s → score-end-guard
  pitää toiston audion mitassa. GP5 kirjoitettiin UTF-8:na, joten
  `Mötley Crüe` näkyy oikein.
- 6 uutta testiä (`tests/test_tab_edit.py`) → **142 pytest-testiä**.
  Vaatii käyttäjän kuuntelu-/tabsynkkitestin (sääntö #1).

## v1.75 – 22.10.2026

- **Korjaus: TEMPO-tallennus kaatui cp1252-koodattuun GP5:een.** Valmiina
  tuodut GP5:t (esim. Dr. Feelgood) säilyttävät alkuperäisen koodauksensa,
  ja `POST /api/tabs/{id}/tempo` luki ne vain UTF-8:nä →
  `'utf-8' codec can't decode byte 0xf6 in position 1` (M**ö**tley).
  Nyt luenta kokeilee UTF-8:aa ja fallbackaa cp1252:een (`_gp5_song`,
  sama kaava kuin tuonnissa) ja kirjoittaa tabin takaisin UTF-8:na, joten
  myös GP5:n otsikot korjautuvat alphaTabissa.
- **SIIRTO-raja ±64 → ±999 tahtia** (`SYNC_OFFSET_LIMIT`): rakenne-ero voi
  vaatia kymmeniä tahteja (tabin toistot vs. levytys). Kellotus ei muutu –
  `syncTimeMs` rajaa position edelleen partituurin loppuun.
  `#shift-input`in `min`/`max` ja `app.js`n kaksi clampia käyttävät samaa
  rajaa.
- Testit: 136 (`test_set_tab_tempo_handles_cp1252_gp5`,
  `test_set_tab_sync_accepts_long_bar_shift`; hylkytesti siirretty arvoon
  5000). Vaatii käyttäjän kuuntelu-/tabsynkkitestin (sääntö #1).

## v1.74 – 21.10.2026

- **Korjaus: GP5-merkkijonot UTF-8:ksi.** PyGuitarPro kirjoitti GP5:n
  oletuksena `cp1252`:na, mutta alphaTab lukee ne UTF-8:na, joten
  varianttien nimet `V1 · Avoimet kielet` / `V2 · Boksi` /
  `V3 · Vähän liikettä` näkyivät `�`-merkkeinä. Nyt `export_gp5`,
  `export_gp5_variants`, `tab_tempo` ja tuonnin GP3/GP4-muunto kirjoittavat
  UTF-8:na; omat GP5:t luetaan UTF-8:na ja tuonnissa kokeillaan UTF-8 ensin
  (fallback cp1252 vanhoille Guitar Pro -tiedostoille).
- `scripts/backfill_gp5_utf8.py` korjasi 2 olemassa olevaa AI-tabia
  (uudelleenexport variantti-JSONeista UTF-8:na).
- 134 pytest-testiä ennallaan; `test_export_gp5_variants` lukee nyt
  UTF-8:na. Vaatii käyttäjän silmämääräisen tarkistuksen (raidannimet).

## v1.73 – 21.10.2026

- **Haamunuottien siivo** (`app/pipeline/prune.py`): transkription jälkeen,
  ennen kvantisointia, pudotetaan selvästi hiljaisemmat oktaavi-/kvintti-
  duplikaatit samasta onsetista ja rajataan soinnun polyfonia max 4 nuottiin
  per isku (pidetään voimakkaimmat). Suodatin vain poistaa – se ei siirrä
  eikä muuta säilytettyjä nuotteja.
- `PIPELINE_VERSION = "3"` → vanhat AI-tabit eivät tule cachesta; uusi
  generointi käyttää siivottua nuottilistaa. Metaan tallentuu `pruned_notes`
  (poistettujen määrä) ja `detected_notes` pysyy raakana määränä.
- 134 pytest-testiä (5 uutta `tests/test_prune.py`: oktaavihaamu pois,
  samanvahvuinen oktaavituplaus säilyy, polyfoniakatto, onset-ikkuna,
  determinismi). Vaatii käyttäjän kuuntelutestin.

## v1.72 – 21.10.2026

- **Useampi sormitusversio per generointi.** Putki luo samasta
  kvantisoidusta MIDI-datasta kolme soitettavaa otelautaversiota
  (`app/pipeline/fretboard.py`): `V1 · Avoimet kielet`, `V2 · Boksi`,
  `V3 · Vähän liikettä`. Uusi kustannusfunktio rankaisee käden siirroista,
  kielten ylityksistä, leveistä otteista ja korkeista nauhoista – ja
  palkitsee profiilin mukaisesti avoimista kielistä/matalasta
  rekisteristä.
- **Soitettavuusmittari** (`app/pipeline/playability.py`): jokainen versio
  saa deterministisen 0–10-pisteen arvon (siirrot/tahti, otteen leveys,
  kielihypyt, pudonneet nuotit). Paras score valitsee oletusversion.
- **Versiot näkyvät raitoina:** katselun GP5 sisältää yhden raidan per
  versio, joten versioiden vaihto käyttää olemassa olevia raitachipejä
  (ei audion uudelleenlatausta eikä kosketusta synkkaan). Oletuksena
  näkyy paras versio; käyttäjän valinta palautuu localStoragesta.
- **`VALITSE TÄMÄ`** (`POST /api/tabs/{id}/variant`): valittu versio
  kirjoitetaan 1-raitaiseksi `tab.gp5`/`musicxml`/`mid`, muiden versioiden
  JSON-snapshotit poistetaan ja `meta.selected_variant`/
  `variant_finalized` asetetaan. Kirjaston lukitus estää valinnan (409).
  Lopullinen tiedosto generoidaan tabin **nykyisellä BPM:llä**, joten
  TAB BPM:n säätö ennen valintaa ei katoa.
- **Uudet tiedostot:** `app/pipeline/playability.py`,
  `app/pipeline/variant_store.py` (TabDocument ↔ JSON).
  `PIPELINE_VERSION = "2"` → vanhat AI-tabit eivät tule cachesta.
  `JobOptions.variants` (oletus päällä) on mukana cache-avaimessa.
- **Ei muutoksia soittoketjuun:** `syncTimeMs`, `mediaHandler`,
  transport ja `#alphaTab`-mitat pysyvät ennallaan. Katselijan pintaan
  tuli vain `restoreTrackSelection`-oletus ja `VALITSE TÄMÄ` -nappi
  `.viewer-tools`-riville.
- Uudet testit: `test_fretboard_profiles.py`, `test_playability.py`,
  `test_tab_variant.py` + `export_gp5_variants` `test_export.py`:ssä.
  Vaatii käyttäjän kuuntelu-/tabsynkkitestin (sääntö #1).

## v1.71 – 21.10.2026

- **Lukon kuvake kirjastolistaan.** Lukitun kappaleen rivillä on nyt
  lukko (🔒) kappaleen nimen jälkeen, ennen `NIMEÄ`/`×`-nappeja;
  vihje kertoo mitä lukitus estää. Kuvake on rivin oma elementti, joten
  pitkä nimi ei leikkaa sitä pois (`.library-title` ellipsi säilyy).
  Muualle UI:hin lukkoa ei lisätty.
- Kirjastorivin metasta poistui päällekkäinen teksti `lukittu`
  (kuvake kertoo saman); työkaluvihje ja `#library`-rivi muuten
  ennallaan.
- Ei muutoksia soittoketjuun eikä backend-reitteihin.
- 117 pytest-testiä ennallaan; `node --check` ja `compileall` OK.

## v1.70 – 21.10.2026

- **Lukitus koskee nyt kaikkia asetuksia.** Aiemmin `locked` esti vain
  poiston. Nyt lukittu tabi on **vain luku**: nimi, viritys,
  arkistointi, TAB BPM, SYNC, SIIRTO ja audion liittäminen on estetty
  sekä palvelimessa (`409` `POST /library|/tempo|/sync|/attach-audio`,
  `DELETE`) että käyttöliittymässä (napit ja kentät pois käytöstä,
  vihje "Tabi on lukittu. Avaa lukitus kirjastossa (NIMEÄ).").
- **Lukituksen avaus:** kirjaston `NIMEÄ`-lomakkeessa poistetaan rasti
  `Lukitse`-kohdasta ja tallennetaan. Yhdellä tallennuksella voi avata
  lukituksen ja muuttaa nimeä/viritystä/arkistointia
  (`locked=false` + muut kentät).
- **Ei muutoksia soittoketjuun:** `app.js`:n soitto-/synkkafunktiot,
  `mediaHandler` ja transportin DOM-id:t pysyivät ennallaan. Ainoa
  kosketus on uusi `applyLockState()` (kytkee `disabled`-tilat) sekä
  `lockTitle`-vihjeiden vaihto.
- `style.css`: pois käytöstä olevat asetuskentät himmennetään
  (`opacity`), mitat ja scroll eivät muutu.
- 117 pytest-testiä (2 uutta: lukitun tabin asetukset 409, avaus +
  muokkaus samalla tallennuksella). Vaatii käyttäjän silmämääräisen
  tarkistuksen (disabled-tilat ja lukituksen avaus).

## v1.69 – 21.10.2026

- **Kappale soi loppuun, vaikka tab loppuu aiemmin.** alphaTab lopettaa
  soiton heti, kun syötetty positio saavuttaa partituurin viimeisen tahdin:
  `stop()` → `output.pause()` (= `audio.pause()`) ja `tickPosition = 0`
  (josta `audio.currentTime = 0`). Siksi biisi katkesi kuin seinään, jos
  tab loppui ennen tallennetta (esim. WASP: kitarat loppuvat, rummut
  soivat vielä). Nyt `syncTimeMs()` pitää syötön 50 ms ennen partituurin
  loppua (`SCORE_END_GUARD_MS`), joten alphaTab pysyy soittotilassa ja
  audio soi omaan loppuunsa; kursori jää viimeiselle iskulle ja
  `Tahti`-lukema viimeiselle tahdille.
- **1:1-kellotus ennallaan:** `bpmDrift`, `barDurationMs`,
  `syncOffsetBars`, SYNC/SIIRTO ja `mediaHandler.seekTo`-inversio eivät
  muuttuneet. Clamp koskee vain partituurin viimeistä ~0,05 tahtia, joten
  kalibrointiarvot (lataus 1,268 s, 10 s → tahti 7, seekit
  16/6/26/11/28/3) pysyvät.
- **PLAY biisin loputtua:** portinvartija `handlePlayButton` tekee kerran
  `api.stop()`in, kun audio on jo päättynyt, joten PLAY aloittaa alusta
  eikä "pauseta" päättynyttä konetta. `togglePlayback`, `mediaHandler` ja
  `syncPosition` eivät muuttuneet.
- Tunnettu kosmeettinen sivuvaikutus: outron aikana `SIIRTO`-livenäyttö
  näyttää kasvavaa "Osoitin x,xx tahtia jäljessä" -lukemaa, koska kursori
  ei voi seurata tabin ulkopuolelle.
- 115 pytest-testiä (1 uusi: score-end-guard pysyy kellossa). Vaatii
  käyttäjän kuuntelu-/tabsynkkitestin (sääntö #1).

## v1.68 – 21.10.2026

- **Viritys näkyviin ja talteen.** GP5-tuonti lukee nyt avoimet kielet
  (`app/tuning.py`): tunnistetaan Standard E, Drop D, Eb Standard,
  D Standard, Open G ja bass 4-string; muut → `Custom` + kirjaimet.
  Tabin metaan tallentuu `tuning_label` (esim. `D Standard · DGCFAD`) ja
  `tuning_notes` (`["D2","G2",…]`), ja `tabs.tuning` saa oikean avaimen
  (aiemmin kaikki ei-standardit olivat `custom`).
- **Näkyvyys:** soittokortin meta alkaa virityksellä
  (`D Standard · DGCFAD · 142 BPM · …`), kirjastorivi näyttää virityksen
  kun se ei ole standardi, ja työkaluvihje kertoo kanavan.
- **Manuaalinen ylikirjoitus:** kirjaston `NIMEÄ`-lomakkeessa on uusi
  Viritys-kenttä (`meta.tuning_override`); tyhjä kenttä palauttaa
  tiedostosta luetun virityksen (`tuning_clear`).
- **Vanhojen tabien viritykset:** `scripts/backfill_tuning.py` lukee
  tallennetut GP5-tiedostot ja täyttää puuttuvat tiedot (`--dry-run`
  ensin). Itse tabitiedostoja ei muuteta.
- AI-tabit saavat virityksen valitusta asetuksesta; GP5-tuonti ei välitä
  Viritys-valinnasta (se vaikuttaa vain generointiin).
- 114 pytest-testiä (6 uutta: viritysten tunnistus, D-standard-tuonti,
  ylikirjoitus). Ei muutoksia soittoketjuun.

## v1.67 – 21.10.2026

- **YouTube-kanava näkyviin jokaiselle tabille.** `fetch_youtube_details()`
  lukee nyt kanavan (`%(channel)s`, fallback `%(uploader)s`) ja
  `AudioSource.channel` kuljettaa sen putkeen. Kanava tallentuu tabin
  metaan (`youtube_channel`) sekä AI-tabeille että GP5 + YouTube
  -liitoksille (`_process_audio_job`).
- **Näkyvyys:** kirjastorivi `… · YT: James Sly`, työkaluvihje
  `YouTube: …` ja soittokortin meta `… · YT: …`. Näin saman kappaleen eri
  uploadit erottuvat ja oikea GP5/audio-pari pysyy tiedossa.
- `fetch_youtube_metadata()` säilyy yhteensopivana `(title, artist)`.
- **Vanhojen tabien kanavat:** `scripts/backfill_youtube_channel.py`
  hakee kanavan olemassa oleville YouTube-tabeille (`--dry-run` ensin).
- 108 pytest-testiä (2 uutta: kanavan parsinta, `channel`-kenttä
  `/api/tabs`-vastauksessa). Ei muutoksia soittoketjuun.

## v1.66 – 21.10.2026

- **Oma tuontikirjasto + bulk-export (ei julkiseen gitiin).** Uusi
  `app/bulk.py`: `import_folder()` tuo kansiosta (myös alikansiot)
  GP3/GP4/GP5- ja MusicXML-tabit kirjastoon ja `export_tabs()` kopioi
  tabit GP5/MusicXML/MIDI-muodossa `manifest.json`in kanssa (valinnainen
  ZIP). Tuodut tiedostot sijaitsevat `data/`- ja `EXTERNAL_DIR`-juurissa,
  jotka ovat jo gitignoroituja; `.gitignore` sai lisäksi `library/`.
- **Tuplien esto:** lähdekansioon kirjoitetaan
  `.tabtool-imported.json` (SHA-256 → tab_id); `--force` ohittaa.
- **Komennot:** `scripts/import_folder.py`, `scripts/export_tabs.py` ja
  `scripts/adb_pull_gp.ps1`, joka hakee puhelimen `/sdcard/Download`ista
  **itse ladatut** GP/MusicXML-tiedostot tuontikansioon. Skripti ei koske
  appien yksityiseen dataan eikä hae mitään verkosta.
- 106 pytest-testiä (5 uutta: `tests/test_bulk.py`).
- Ei muutoksia soittoketjuun eikä API-reitteihin.

## v1.65 – 21.10.2026

- **Kirjastorivin POISTA on nyt pelkkä punainen ×.** Nappi on
  ikonimainen ja kapea (ei reunusta normaalitilassa), joten rivi vie
  vähemmän tilaa. Toiminto on ennallaan: klikkaus avaa saman
  poiston varoitusdialogin. `title` ja uusi `aria-label` kertovat
  edelleen "Poista … kirjastosta"; lukitulla rivillä nappi on harmaa
  ja pois käytöstä.
- Varoitusdialogin POISTA-nappi on edelleen tekstillinen.
- 101 pytest-testiä; `node --check` OK.

## v1.64 – 21.10.2026

- **LIBRARY-modaalin sarakkeet vaihdettu:** KIRJASTO on nyt vasemmalla
  (leveämpi, 1.15fr) ja generaattori (Oma audio / YouTube / GP5) oikealla.
  Yleensä modaalista vain valitaan soitettava kappale, joten lista on
  ensisijainen. DOM-järjestys vaihdettiin samaan järjestykseen, joten
  myös näppäimistö/Tab-järjestys seuraa näkymää.
- Erotinviiva siirtyi generaattorin sarakkeeseen
  (`.modal-body > .modal-column:last-child`); ≤900 px -näkymässä viiva on
  generaattorin yläpuolella. Ei muutoksia toimintaan eikä id:ihin.
- 101 pytest-testiä; `node --check` OK.

## v1.63 – 21.10.2026

- **Kappaleiden uudelleennimeäminen.** Uusi `tabs.title_override`
  (näkyvä nimi) ja `tabs.original_title` (generoitu nimi säilyy).
  Tyhjä nimi palauttaa alkuperäisen. Nimi tallentuu uudella reitillä
  `POST /api/tabs/{id}/library`. Näkymä ja kirjasto käyttävät aina
  käyttäjän nimeä, joten samannimiset versiot pysyvät erillään.
- **Lukitse.** `tabs.locked` estää poiston: `DELETE /api/tabs/{id}`
  palauttaa 409 ja kirjastorivin `POISTA` on pois käytöstä, kunnes
  lukitus avataan nimeämislomakkeesta. Lukittu rivi näyttää metassa
  "lukittu".
- **Arkistoi + Arkisto-lista.** `tabs.archived` piilottaa kappaleen
  päälistalta. Listan lopussa on pieni `ARKISTO (n)` -linkki, joka
  näyttää arkistoidut; arkistorastin poisto palauttaa kappaleen
  pääkirjastoon. Kirjasto avautuu aina päälistaan.
- **Aakkosjärjestys.** Rivit järjestetään `artist — title` -nimikkeen
  mukaan (`localeCompare("fi", {numeric:true})`); myös `db.list_tabs`
  palauttaa rivit artistin ja nimen mukaan.
- **Rivin sisäinen nimeämislomake** (ei uutta modaalia): nimi-kenttä,
  `[ ] Lukitse`, `[ ] Arkistoi`, TALLENNA ja PERUUTA. Virheet näkyvät
  kirjaston status-rivillä.
- **Skeemamigraatio:** `init_db` lisää `title_override`/`locked`/
  `archived` -sarakkeet vanhaan kantaan (`ALTER TABLE`), olemassa oleva
  data säilyy.
- 101 pytest-testiä (`tests/test_tab_library.py`: nimeäminen, lukitus,
  arkisto, järjestys, migraatio).

## v1.62 – 21.10.2026

- **LIBRARY piilotetaan fullscreenissä.** `#open-search` ei näy koko
  näytön soittotilassa (`:fullscreen` ja `.is-fullscreen`), jotta ruutu
  jää soitolle; Esc / FULLSCREEN palauttaa sen. Samalla `.viewer-bar`in
  grid kaventuu kolmeen sarakkeeseen (`auto 1fr auto`), joten FULLSCREEN
  pysyy kortin oikeassa reunassa ja PLAY siirtyy vasempaan laitaan.
- Vain CSS; ei muutoksia DOMiin, soittoketjuun eikä reitteihin.
- 96 pytest-testiä; `node --check` OK.

## v1.61 – 21.10.2026

- **EXPORT-rivi tabikentän alle.** `.viewer-foot` siirrettiin `#alphaTab`in
  jälkeen: GP5 / MusicXML / MIDI -linkit ovat nyt tablatuurin alapuolella
  eivätkä vie tilaa soittopalkkien välistä. Fullscreenissä rivi piilotetaan
  edelleen.
- **FULLSCREEN kortin oikeaan yläkulmaan.** `#fullscreen-button` siirrettiin
  `.viewer-tools`ista samalle riville LIBRARYn, PLAYn ja otsikon kanssa;
  `.viewer-bar`-grid sai neljännen sarakkeen (`auto auto 1fr auto`), joten
  nappi asettuu kortin oikeaan reunaan.
- **Transportille oma taustakortti.** `.transport` sai saman pinnan kuin
  LIBRARY/PLAY-kortti: `var(--panel)`-tausta, reunus, pyöristys, varjo ja
  `0.9rem 1.2rem` padding (`0 0.35rem` → kortti).
- Ei muutoksia soittoketjuun: transportin DOM-id:t ja käsittelijät,
  `#alphaTab`, `mediaHandler`/`seekTo`/`syncTimeMs` ennallaan.
- 96 pytest-testiä; `compileall`, `node --check` OK.

## v1.60 – 21.10.2026

- **LIBRARY-modaali avautuu LIBRARY-napin korkeudelle** eikä hyppää
  ruudun keskelle. `openSearch()` mittaa napin `getBoundingClientRect()`
  -arvon ja kirjoittaa sen `--modal-top`-muuttujaan; `#search-modal`
  käyttää sitä yläpaddingina (`align-items: flex-start`) ja paneelin
  `max-height` lasketaan samasta arvosta, jotta paneeli mahtuu ruudulle.
- Ankkuri: kortin LIBRARY-nappi; jos tabia ei ole auki (viewer piilossa),
  käytetään topbarin LIBRARY-nappia. Arvo rajataan vähintään 8 px:iin.
- Poiston varoitusdialogi pysyy keskitettynä (sääntö kohdistuu vain
  `#search-modal`iin). Ei muutoksia soittoketjuun.
- 96 pytest-testiä; `compileall`, `node --check` OK.

## v1.59 – 21.10.2026

- **Yläosa tiiviimmäksi.** Hero-osio (kicker + irrallinen LIBRARY-nappi)
  poistettu; `.shell`-ylämarginaali ja `.viewer-section`in ylämarginaali
  pienenivät, joten tablatuuri alkaa heti topbarin alta.
- **LIBRARY samaan korttiin PLAYn kanssa.** `#open-search` siirrettiin
  `#viewer-section`in `.viewer-bar`-korttiin PLAY-napin vasemmalle
  puolelle (id ja käsittelijä ennallaan; topbarin `#open-search-top`
  avaa kirjaston edelleen, kun tabia ei ole auki).
- **Työkalurivi vasempaan reunaan.** `.viewer-bar` on nyt grid
  (`auto auto 1fr`), joten NÄKYMÄ, raitavalinnat, FULLSCREEN ja
  LIITÄ AUDIO alkavat omalta riviltään kortin vasemmasta reunasta
  LIBRARY-napin alta. ≤720 px: kaksi saraketta + meta omalle rivilleen.
- Ei muutoksia soittoketjuun: transportin DOM-id:t, `#alphaTab`,
  `.transport` ja reitit ennallaan.
- 96 pytest-testiä; `compileall`, `node --check` OK.

## v1.58 – 21.10.2026

- **Scrollbar omalle kaistalleen, marginaalit 30 px.** v1.57:n 15 px
  sisämarginaali jätti pystyvierityspalkin (15 px gutter) tablatuurin
  oikean reunan päälle. Nyt `display.padding: [30, 15]`: tablatuurin
  oikea reuna on 30 px päässä reunasta, joten scrollbar (15 px) saa oman
  kaistan eikä mene tabin päälle; vasen marginaali 15 → 30 px.
- Ei muutoksia soittoketjuun: vain scoren sisämarginaali. Score-alueen
  leveys ja cursor-säiliö seuraavat edelleen samaa `offsetWidth`-mittaa.
- 96 pytest-testiä; `compileall`, `node --check` OK.

## v1.57 – 21.10.2026

- **Tabinäkymän marginaali 15 px molemmille puolille.** Vasen marginaali
  oli ~26 px ja oikea ~3 px, koska alphaTab mitoittaa `.at-surface`-
  kerroksen `.alphatab`-laatikon `offsetWidth`ista (koko reunuslaatikko)
  mutta sijoittaa sen sisältölaatikon alkuun. Silloin `padding: 0.6rem`,
  1 px reunus ja 15 px scrollbar-gutter työnsivät tablatuuria oikealle ja
  oikea reuna leikkautui (`overflow-x: hidden`).
- Korjaus: `.alphatab` ilman paddingia ja reunusta (reunus piirretään
  `inset`-varjolla, ei vie tilaa) ja marginaali alphaTabin omalla
  `display.padding: [15, 15]` -asetuksella. Mitat `min-height`,
  `max-height`, `overflow`, `min-width`, `width`, `max-width` pysyivät
  ennallaan.
- Mitattu headless-Edgellä 1600/1366/1200/1024/800 px: vasen ja oikea
  marginaali 15 px, ylivuoto 0 px, `document.scrollWidth ===
  clientWidth` (ei sivuttaisvieritystä).
- 96 pytest-testiä; `compileall`, `node --check app.js`/`remote.js` OK.

## v1.56 – 20.10.2026

- **Korjaus: count-in ei käynnistynyt lainkaan.** v1.55 päätteli
  "käyttäjä on seekannut" ehdosta `audio.currentTime > 0.05`, mutta
  alphaTab siirtää audion ensimmäiselle iskulle jo **latauksessa**
  (`mediaHandler.seekTo` → `currentTime ≈ 0,8455 s` SIIRTO −0,75:llä).
  Ehto oli siis aina tosi ja laskenta ohitettiin.
- Nyt ohitus perustuu **käyttäjän omaan seekiin**: liukusäädin, ±5 s
  -napit ja nuolinäppäimet asettavat `countInSkipped`-lipun, joka
  nollataan `loadTab`issa. Count-in-funktiot eivät enää lue audiota
  lainkaan.
- Vartiotesti tiukennettu: count-in-funktioissa ei saa esiintyä `audio`-
  eikä `api.`-viittauksia.
- 96 pytest-testiä.

## v1.55 – 20.10.2026

- **Count-in 5 → 0 ilman kosketusta soittoketjuun.** Overlay
  (`#play-countdown`) on `#viewer-section`in fixed-lapsi: se ei ole grid-
  eikä flex-item, joten tabin leveys, scroll-alue ja `.alphatab`-mitat
  pysyvät ennallaan. Laskenta tekee vain DOM-muutoksia.
- **Portinvartija:** PLAY-nappi ja Space kutsuvat `handlePlayButton`ia,
  joka joko kutsuu **muuttumatonta** `togglePlayback`ia tai näyttää
  count-inin ja kutsuu samaa funktiota vasta 0:n jälkeen. Fullscreen
  pyydetään heti PLAYsta (käyttäjän ele), ei laskennan lopussa.
- Count-in vain tabin ensimmäisellä PLAYlla; `loadTab` nollaa lipun ja
  peruu keskeneräisen laskennan. Toinen PLAY tai Esc peruu; seek ennen
  ensimmäistä PLAYta ohittaa laskennan. Ei audiota → ei laskentaa.
- Uusi vartiotesti `tests/test_playback_guard.py`: count-in ei saa
  sisältää `api.`/`audio.play`/`audio.pause`-kutsuja eikä
  `togglePlayback`/`mediaHandler`/`syncTimeMs`-ketju count-in-koodia.
- 96 pytest-testiä.

## v1.54 – 20.10.2026

- **Palvelimen hallinta käyttäjälle.** `stop.bat` pysäyttää portin 8000
  kuuntelijan (uvicornin käynnistin + lapsiprosessi) ja tulostaa PID:t;
  `status.bat` näyttää portin tilan ja `/api/version`-vastauksen.
- **`start.bat` ei käynnistä toista instanssia**, jos portti 8000 on jo
  varattu: se tulostaa PID:n ja neuvoo ajamaan `stop.bat`in.
- Ei muutoksia soittoon, sync-asetuksiin, tablatuuriin tai GP5-dataan.
- 93 pytest-testiä.

## v1.53 – 20.10.2026

- **Count-in poistettu toistaiseksi kokonaan.** `#play-countdown`-overlay,
  `.viewer-stage`-kääre, countdown-CSS ja countdown-JS poistettu.
  `togglePlayback` palautettu v1.48:n muotoon: PLAY avaa fullscreenin ja
  käynnistää toiston heti (`api.playPause()`).
- Soitto ja tablatuuri ovat jälleen **1:1** alusta asti: lataus
  t = 1,268 s (SIIRTO −0,75), 10 s toiston jälkeen tahti 7 = odotettu.
- Countdown tehdään myöhemmin eri tavalla, irrallaan soittoketjusta.
- 93 pytest-testiä.

## v1.52 – 19.10.2026

- **Korjaus: soitto ja tablatuuri pysyvät taas synkissä.** v1.51 rajoitti
  SIIRTO-inversion pelkkiin osoitinklikkauksiin, jolloin alphaTabin omat
  seekit (lataus, play, pause) jäivät kääntämättä. Soiton aloituskohta
  siirtyi 1,268 s → 0 ja koko biisi oli 0,75 tahtia eri kohdassa.
  Palautettu v1.50:n käytös: `time > 0` -seekeissä inversio tehdään aina,
  myös alphaTabin omille seekeille.
- Count-in-parannukset säilyvät: vain ensimmäisellä aloituksella eikä
  koske PLAY-nappiin, audioon tai kursoriin.
- Validoitu headless-Edgellä: lataus t = 1,268 s (SIIRTO −0,75),
  count-in ei muuta sitä, 10 s toiston jälkeen tahti 7 = odotettu,
  tauon jälkeen resume ilman laskentaa.
- 93 pytest-testiä.

## v1.51 – 19.10.2026

- **Count-in vain kerran kappaleen alussa.** `countInDone` asetetaan
  ensimmäisen toiston `play`-tapahtumassa ja nollataan `loadTab`issa.
  Tauon jälkeen jatkaminen alkaa heti ilman laskentaa.
- **Count-in on nyt täysin erillinen soitosta.** Se ei enää muuta
  PLAY/PAUSE-napin tilaa eikä kutsu alphaTabia tai audiota ennen kuin
  laskenta päättyy; `audio.currentTime` ja kursori pysyvät paikallaan
  (t = 0, Tahti 1). Toinen PLAY-painallus peruu laskennan.
- **Korjaus: SIIRTO ei enää siirrä audiota latauksessa.** alphaTab kutsuu
  latauksessa `seekTo(~0,44 ms)`, ja vanha `time > 0` -ehto käänsi sen
  SIIRTO-arvolla 1,268 sekunniksi. Nyt inversio tehdään vain oikealle
  osoitinklikkaukselle (600 ms ikkuna `pointerdown`/`mousedown`ista),
  joten engine-seekit menevät läpi sellaisenaan ja toisto alkaa 0:sta.
- Validoitu headless-Edgellä: t = 0 latauksessa ja koko count-inin ajan,
  tauon jälkeen resume ilman laskentaa, klikkaus-seek osuu tahtiin 3.
- 93 pytest-testiä.

> Huom: v1.51:n SIIRTO-latausseek-muutos kumottiin v1.52:ssa, koska se
> siirsi soitonaloituksen 1,268 s → 0 ja rikkoi soiton/tabin synkan.

## v1.50 – 19.10.2026

- **Korjaus: tabinäkymä levisi oikealle aloitusnäkymässä.** v1.49:n
  `.viewer-stage`-kääre (count-in-overlayn ankkuri) otti leveytensä
  alphaTabin canvasin sisältöleveydestä, joten grid-rata kasvoi noin
  7000 px:iin ja koko sivu vierittyi oikealle. `min-width: 0` kääreelle
  ja `.alphatab`ille sekä `width/max-width: 100 %` rajaavat näkymän.
  Testattu 1366/1600/2560 px: `scrollWidth == clientWidth`.
- Ei muita muutoksia; 93 pytest-testiä.

## v1.49 – 19.10.2026

- **Tumma tabinäkymä oletuksena.** alphaTabin värit asetettiin
  `display.resources`-asetuksilla vaaleiksi (`mainGlyphColor`,
  `secondaryGlyphColor`, `staffLineColor`, `barSeparatorColor`,
  `barNumberColor`, `scoreInfoColor`) ja `.alphatab`-tausta tummaksi
  (`#0d1117`). Suurella näytöllä tabi ei enää väläytä valkoisena.
- **SEARCH-napit → LIBRARY.** Yläpalkin ja etusivun nappi avaavat saman
  ikkunan; modaalista poistettiin iso `SEARCH`-otsikko (jäljellä
  `LIBRARY · GENERAATTORI`) ja `aria-label` korvaa poistetun otsikon.
- **Count-in 5 → 0.** PLAY näyttää viiden sekunnin laskennan tabin päällä
  ennen kuin toisto alkaa; toinen PLAY-painallus peruu laskennan.
  Kesto on `COUNTDOWN_SECONDS` (`app/static/app.js`), kunnes
  Settings-näkymä tehdään.
- Ei backend-muutoksia; 93 pytest-testiä.

## v1.48 – 19.10.2026

- **Korjaus: klikkaus-seek kohdistaa nyt oikein.** `mediaHandler.seekTo`
  käänsi aiemmin SIIRTO/SYNC/BPM-korjauksen vain osittain, joten klikatun
  tahdin sijaan valittiin edellinen (esim. klikkaa 183 → valitsee 182).
  Nyt `syncTimeMs()` käännetään klikkaus-seekeissä (`time > 0`), mutta
  nollaus/pysäytys (`time === 0`) jätetään ennalleen, joten toisto ei
  muuttunut. Ei backend-muutoksia; 93 pytest-testiä.

## v1.47 – 18.10.2026

- **Korjaus: osoitin "juoksi" edellä toiston aikana (renderöinti).** alphaTabin
  `enableAnimatedBeatCursor` ekstrapoloi kursorin CSS-siirtymällä seuraavan
  iskun yli (`ToNextBext` → kerroin 2), joten toiston aikana näkymä eteni
  ääntä edellä ja pysäytyksessä palasi tarkkaan paikkaan. Animoitu kursori
  otettiin pois käytöstä: nyt kursori hyppää suoraan oikeaan
  `tickPosition`iin joka 50 ms -päivityksellä.
- Ei backend-muutoksia; 93 pytest-testiä.

## v1.46 – 18.10.2026

- **Kohdistusavustin (pyynnöstä):**
  - **Live-offset-näyttö** kuljetuspalkissa näyttää osoittimen eron
    ääneen (`Osoitin +0,50 tahtia edellä` / `−0,50 tahtia jäljessä` /
    `Kohdallaan`), laskettuna `api.tickPosition` vs.
    `audio.currentTime × BPM × 960 / 60000`.
  - **KOHDISTA-nappi**: pysäytä toisto ja klikkaa tabista sitä nuottia,
    jonka pitäisi soida nyt. Appi laskee eron `beat.absolutePlaybackStart`
    vs. nykyinen `tickPosition` ja tallentaa sen SIIRTO-arvoksi
    (`/api/tabs/{id}/sync`). Klikkauksen aikana alphaTabin oma
    click-to-seek on väliaikaisesti pois päältä.
- Ei backend-muutoksia; 93 pytest-testiä.

## v1.45 – 18.10.2026

- **Korjaus: partituurin kesto lasketaan master bar -tikeistä.** Aiempi
  korjaus käytti `api.endTime`ä, joka on alphaTabin *live* `currentPosition`
  ja on 0 ennen ensimmäistä toistotikkia — siksi `backingTrackDuration`
  putosi takaisin ääniraidan kestoon ja alphaTabin venytys jäi voimaan.
  Nyt kesto = `(viimeisen tahdin start + kesto) × 60000 / (tempo × 960)`,
  joka on oikea heti ensimmäisestä kursoritikistä. Seek & Destroy
  (258 tahtia, tempo 144) → 430 000 ms.
- Ei backend-muutoksia; 93 pytest-testiä.

## v1.44 – 18.10.2026

- `scoreEndTimeMs()` käyttää suoraan `api.endTime`ä (sekvensserin
  `currentEndTime`, sama arvo kuin alphaTabin backing track -kaavassa).
  Aiempi `api.tickCache.endTime`-haara poistettiin, koska tick lookup
  -objektilla ei ole `endTime`-kenttää. Toiminta ei muuttunut; korjaus
  on täysin selainpuolinen, joten se aktivoituu kovalla uudelleenlatauksella
  (Ctrl+F5) myös ilman palvelimen uudelleenkäynnistystä.

## v1.43 – 18.10.2026

- **Korjaus: osoitin kulki ääntä edellä (kursorin synkka).** alphaTabin
  ulkoisen median kello venyttää backing trackin ajan koko partituurin
  pituuteen suhteella `partituurin kesto / backingTrackDuration`.
  `backingTrackDuration` palautti ääniraidan keston, joten kun tabi on
  pidempi kuin audio (esim. Seek & Destroy -referenssi: 258 tahtia vs.
  ~249 tahtia), jokainen `audio.currentTime`-syöte skaalattiin ylöspäin ja
  kursori meni musiikin edelle. Nyt `backingTrackDuration` palauttaa
  partituurin keston (`api.tickCache.endTime`), jolloin kellotus on 1:1 ja
  vain TAB BPM / SYNC / SIIRTO -korjaukset vaikuttavat. Tab BPM 143,5
  (GP5 144) kohdistaa tahdin 41 viimeisen nuotin oikein.
- Ei muutoksia backendiin; 93 pytest-testiä.

## v1.42 – 18.10.2026

- **Testiajon yhteenveto näkyviin:** `pytest.ini`:stä poistettiin
  `addopts = -q`. Ohjeen `pytest -q` oli aiemmin käytännössä `-qq`,
  joten pytest tulosti vain pisteet eikä lainkaan riviä `93 passed`.
  Nyt `pytest -q` (ja `test.bat`) näyttää aina testien määrän.
- **Sessioalustuksen tulosteet kapeaan konsoliin:** memory bank
  -protokollan tarkistuskomennot putkitetaan `Out-String -Width 200`
  -muotoon. PowerShell muotoilee monirivisen tulosteen konsolin
  leveyden mukaan; kapeassa kuoressa rivit hajosivat ja VS Code
  shell integration saattoi pudottaa tulosteen kokonaan.
- Ei muutoksia sovelluksen toimintaan; 93 pytest-testiä.

## v1.41 – 18.10.2026

- **GP3/GP4-tuki tuonnille:** `POST /api/tabs/import` ja
  `POST /api/tabs/import-url` hyväksyvät nyt `.gp3`, `.gp4` ja `.gp5`.
  PyGuitarPro lukee tiedoston ja vanha versio kirjoitetaan aidoksi
  GP5:ksi (`tab.gp5`), jotta alphaTab ja GP5-export toimivat
  yhdenmukaisesti. Konversio ei muuta nuotteja (testattu GP4 → GP5:
  samat tahdit, notet ja tempo).
- **Korjaus: levyltä uudelleenrekisteröity tabi menetti audionsa.**
  `db.import_tabs_from_disk` resolvoi `meta.audio_path`-arvon
  työhakemistosta, vaikka jobit tallentavat sen suhteessa `data/`-juureen.
  Nyt relatiivinen polku resolvoidaan `DATA_DIR`-juuresta, joten
  `audio/…wav` säilyy tabilla myös kannan uudelleenluennassa.
- SEARCH-modaalin tiedostovalitsin hyväksyy `.gp3/.gp4/.gp5` ja
  virhetekstit puhuvat GP-tiedostosta; GP5-säilyy tallennusformaattina.
- 93 pytest-testiä (uudet: GP4-tuonti konvertoituu GP5:ksi,
  relatiivinen audio_path säilyy rescanissa).

## v1.40 – 18.10.2026

- **Yksi toiminto kaikille GP5-lähteille:** SEARCH-modaalissa on nyt
  `GP5-linkki (valinnainen)` ja `tai GP5-tiedosto`. Molemmat käyttävät
  samaa GENERATE TAB -toimintoa, joten paikallinen GP5/MusicXML-tiedosto
  + YouTube-linkki onnistuu yhdellä painalluksella.
- `POST /api/tabs/import` hyväksyy nyt `youtube_url`- ja
  `options`-kentät: ilman YouTube-linkkiä vastaus on tab-yhteenveto,
  linkin kanssa vastaus on audio-job, joka liittää audion tuotuun
  tabiin valmistuttuaan. Sama `_queue_audio_job`-polku kuin
  GP5-linkilla.
- Erillinen `IMPORT TAB` -rivi poistettu modaalista; GP5/MusicXML-tuonti
  tapahtuu samasta lomakkeesta. GP5-linkki ja GP5-tiedosto ovat
  vaihtoehtoisia (ei molempia), eikä GP5-lähteen kanssa voi käyttää
  omaa audiotiedostoa – audio tulee YouTube-linkistä.
- 91 pytest-testiä (uudet: GP5-tiedosto + YT liittää audion,
  ei-YouTube-URL hylätään). Headless-selaimessa validoitu koko
  kombinaatio: tiedosto + YT → tabi tuotu, audio liitetty, modaali
  sulkeutui, viewer avautui.

## v1.39 – 18.10.2026

- **Korjaus: alphaTabin cursor näkyi SEARCH-modaalin päällä.** alphaTab
  antaa cursor-kontilleen `z-index: 1000`, joten vihreä
  valinta-/cursor-kehys piirtyi modaalin yli (modaali oli `60`).
  Modaalin pino nostettiin (`2000`, varoitusdialogi `2100`),
  `.viewer-section` eristettiin omaksi pinoksi (`isolation: isolate`)
  ja cursor-elementit piilotetaan modaalin ollessa auki
  (`body.modal-open .at-cursors`).
- Modaalin tausta muutettiin täysin peittäväksi, jotta taustan sisältö
  ei näy läpi.
- Ei toiminnallisia backend-muutoksia; 89 testiä ennallaan.

## v1.38 – 18.10.2026

- **SEARCH-modaali:** kappaleen haku, GP5-tuonti, kirjasto ja kappaleen
  valinta ovat nyt omassa tilavassa ikkunassaan. TV-näkymä jää soittoa
  varten; `SEARCH` avaa modaalin yläpalkista ja etusivulta, `SULJE`/Esc
  sulkee sen.
- **YouTube + GP5-linkki:** jos GP5-linkki annetaan, tablatuuria ei
  generoida AI:lla. Palvelin hakee GP5/MusicXML-tiedoston suoraan
  linkistä (`app/tab_download.py`), importtaa sen ja liittää
  YouTube-audiosta ladatun audion tabiin. Ilman GP5-linkkiä toiminta on
  ennallaan (AI-generointi).
- **gprotab.net:** tavallinen tabisivu palauttaa HTML:n; lataus osaa
  retryttää `?download`-parametrilla. Vain julkiset http(s)-osoitteet
  sallitaan (ei localhost/yksityisverkko), koko enintään 20 MB.
- **MP3-valinta:** `MP3-kuunteluversio` on oletuksena päällä ja
  tallentaa YouTube-audiosta MP3:n `D:\tabtool_files\audio\mp3\`-
  hakemistoon. Valinta ei vaikuta tabin cache-avaimeen.
- **Kappaleen poisto:** kirjastoriviltä `POISTA` avaa
  varoitusdialogin. Poisto siirtää tabin, sen audion, stemmit sekä
  niihin liittyvät job/track-rivit pois; MP3-kuunteluversio jää
  hakemistoon. Jaettu audio säilyy, jos toinen tabi käyttää samaa
  tiedostoa.
- **Uudet reitit:** `POST /api/tabs/import-url`, `DELETE /api/tabs/{id}`;
  `POST /api/jobs` hyväksyy `gp5_url`-kentän. Audio-only-job (malli
  tallentuu `options`-kenttään) liittää audion tuotuun tabiin ilman
  transkriptiota.
- 89 pytest-testiä (uudet: download, delete, GP5+YT-job, optioiden
  erottelu). Headless-selaimessa validoitu modaalin avaus, kappaleen
  valinta, poistodialogi ja GP5-linkin tuonti (W.A.S.P. — Animal
  (Fuck Like A Beast), 111 tahtia, 3471 nuottia).

## v1.37 – 18.10.2026

- **Korjaus: vahingossa syntyvä playback range (loop).** alphaTab luo
  hiirellä raahaamalla `playbackRange`-alueen (vihreä kehys), joka
  rajaa `mainSeek`in. Silloin tab jämähtää/clampautuu väärään kohtaan
  (esim. "tab bar 85, soitto bar 84") ja Pause hyppää beat-alun
  mukaan. Range nollataan nyt heti: `playbackRangeChanged`-tapahtumassa,
  `scoreLoaded`issa ja ennen jokaista seekiä. Klikkaus siirtää edelleen,
  mutta raahaus ei jätä looppia.
- **Pause-palautus:** kun alphaTab pysäyttää ja snapsauttaa cursorin
  beat-alun mukaan, sijainti palautetaan audion aikaan
  (`playerStateChanged` 60 ms + audion `pause` 150 ms).
- Validoitu headless-selaimessa: raahaus → `.at-selection` 0×0,
  seek 10 s → tahti 6 (ei clampattu); pause → tahtilukema säilyy.
- 75 pytest-testiä (ei backend-muutoksia).

## v1.36 – 18.10.2026

- **SIIRTO neljännes tahdin tarkkuudella:** 0,25 tahdin askel = 1 isku
  4/4:ssä, joten 6–7 iskun vakiosiirto korjataan suoraan
  (esim. −1,5 tai −1,75). Arvo pyöristetään lähimpään 0,25:een ja
  tallentuu `meta.sync_offset_bars`iin.
- Rajaus ±64 tahtia; backend hyväksyy edelleen desimaalit.
- Testit: siirto tallentuu desimaalina (−1.5); 75 pytest-testiä.

## v1.35 – 18.10.2026

- **SIIRTO (tahtia)** -kenttä: siirtää tabia kokonaisilla tahdeilla
  (−64…+64, tallentuu `meta.sync_offset_bars`). Tarkoitettu
  rakenne-eroon, jota prosenttisäätö ei korjaa: esim. referenssitabissa
  on 258 tahtia mutta levytyksessä ~249, jolloin tabi voi olla
  8 tahtia edellä (≈13 s @ 143,5 BPM).
- Siirto lasketaan tabin omasta tahtipituudesta
  (`masterBars[1].start − masterBars[0].start` tickeinä) ja lisätään
  SYNC/BPM-korjauksen päälle; arvo tallentuu ja palautuu tabia
  avattaessa.
- `POST /api/tabs/{id}/sync` hyväksyy nyt `offset_bars`-kentän
  (validointi ±64).
- Testit: siirron tallennus ja raja; 75 pytest-testiä.

## v1.34 – 18.10.2026

- **Desimaali-TAB BPM:** kenttä hyväksyy 0,1 askelen (esim. `143,55`).
  GP5 tallentaa edelleen kokonaisluvun (`int(bpm+0,5)`), mutta
  desimaaliosa toteutetaan toiston korjauksena
  (`bpmDrift = bpm / nuottitempo - 1`), joka summataan SYNC-arvoon.
  Näin 143 → tab jää jälkeen / 144 → edistää -ongelma poistuu ilman
  GP5:n muokkaamista käsin.
- `meta.gp5_tempo` tallentaa kirjoitetun kokonaisluvun; frontend lukee
  ensisijaisesti alphaTabin `score.tempo`n.
- BPM näytetään kirjastossa ja otsikossa yhdellä desimaalilla, kun arvo
  ei ole kokonaisluku.
- Mitattu Seek & Destroy -audion tempo: **143,555 BPM**
  (librosa, mediaanibeat 0,41796 s; 420 beatia). Suositus: `143,55`.
- Headless-Chrome: 119,5 BPM → GP5 120, 58 s kohdalla tahti 29
  (ilman korjausta 30); 73 pytest-testiä.

## v1.33 – 18.10.2026

- **MP3-kuunteluversiot:** YouTube-latauksista tehdään WAV:n rinnalle
  MP3 `D:\tabtool_files\audio\mp3\<Artisti>\Artist - Title.mp3`
  (ffmpeg, libmp3lame VBR ~190 kbps). Artistikansiot syntyvät
  automaattisesti; tuntematon artisti → `Unknown Artist`.
  MP3 uudelleen­koodataan vain, jos WAV on uudempi. Pätkäklipit ja omat
  uploadit ohitetaan.
- `scripts/backfill_external.py` tekee myös MP3:t olemassa oleville
  YouTube-audioille (sama audio koodataan vain kerran).
- **Seek-synkki:** tutkittu headless-selaimessa (30 tahtia, 120 BPM,
  sliderilla 30→10→50→20→55→5 s). Tahtilukema osui joka kerta
  odotettuun tahtiin, joten siirto ei riko aikasynkkiä. Vakaunnukset:
  seekin aikana positiota ei syötetä alphaTabille (`audio.seeking`),
  `seekTo`/`seeked` pakottavat synkan, slider vapautetaan myös
  dokumentin `pointerup`/ikkunan `blur`-tapahtumissa.

## v1.32 – 18.10.2026

- **Ulkoinen arkisto:** YouTube-lataukset ja tuodut GP5/MusicXML-tabit
  mirroroidaan luettavalla nimellä (`Artist - Title.ext`) hakemistoon
  `D:\tabtool_files\audio` ja `D:\tabtool_files\tabs`
  (`TABTOOL_EXTERNAL_DIR`). Samalla levyasemalla käytetään hard linkiä,
  joten levytilaa ei kulu ylimääräistä; muuten tehdään kopio.
  Arkistointivirhe ei kaada jobia. Pätkäklipit jätetään arkistoimatta.
- `scripts/backfill_external.py` arkistoi olemassa olevan kirjaston
  kertaalleen.
- `tests/test_external_store.py` ja tuontitestin arkistovarmistus;
  testit käyttävät temp-hakemistoa, eivät `D:\tabtool_files`ia.
- Muistutus: `TABTOOL_DATA_DIR`-ympäristömuuttuja periytyy
  `Start-Process`ille. Jos se osoittaa testihakemistoon, UI näyttää
  tyhjän kirjaston vaikka `data/` olisi ehjä – käynnistä palvelin
  oikealla data-juurella.

## v1.31 – 18.10.2026

- **TALLENNA** (entinen `ASETA`): TAB BPM tallentuu vain napista.
  Kun kenttään kirjoittaa eri arvon kuin tabissa on, kenttä, syöte ja
  nappi muuttuvat punaisiksi, kunnes arvo on tallennettu; virheet
  (`BPM 20–400`, tallennusvirhe) näytetään punaisella.
- SYNC-tallennuksen virheet näytetään punaisella; onnistunut
  tallennus kuittaa tilan.
- `Not found` -virhe johtui vanhasta käynnissä olleesta
  palvelinprosessista (v1.22), jonka reiteissä ei ollut `/tempo`- eikä
  `/sync`-päätepistettä. Korjaus: käynnistä palvelin uudelleen
  (`start.bat`) koodimuutosten jälkeen.

## v1.30 – 18.10.2026

- **SYNC**-säädin: tabin kohdistus audion aikajanalle ±10 % (askel
  0,05 %). `+` siirtää tabia eteenpäin, `-` taaksepäin, joten pitkän
  kappaleen loppupään kertynyt heitto korjataan yhdellä säädöllä.
  Korjaus tallennetaan tabin `meta.json`iin (`sync_drift`) ja
  tietokantaan (`POST /api/tabs/{id}/sync`), joten se on automaattisesti
  mukana, kun tabi avataan uudelleen. GP5- ja audiotiedostoja ei muuteta.
- **Nopeus**-säätimen alue laajennettu 50–150 %:iin (aiempi 95–105 %).
  Nopeus on harjoittelusäädin: tabi seuraa audiota samassa suhteessa,
  joten kohdistus tehdään SYNC-säätimellä.
- Uudet testit: `tests/test_tab_sync.py` (tallennus, rajat, virheellinen
  arvo, tuntematon tabi).

## v1.29 – 18.10.2026

- **TAB BPM** -korjaus: katselimen transportissa voi asettaa GP5-tabin
  todellisen tempon. Backend päivittää GP5:n `song.tempo`-arvon,
  tietokannan ja `meta.json`in (`POST /api/tabs/{id}/tempo`).
  Näin tabi saadaan kappaleen nopeuteen: esim. Seek & Destroy
  -referenssitabi 140 → 144 BPM, audio 100 %:ssa. Tahti 62 osuu tällöin
  kohtaan 1:42 (101.7 s).
- **Nopeus**-säädin tarkentui: 95–105 %, askel 0,1 % ja yhden
  desimaalin näyttö. Sillä hienosäädetään esim. 143,55 BPM audio
  vastaamaan 144 BPM tabia.
- AI-BPM on jatkossa merkitty arvioksi (`AI-arvio`), ei absoluuttiseksi
  totuudeksi; kappaleen tempo ratkaisee.

## v1.28 – 18.10.2026

- Tuodun referenssitabin audio: `LIITÄ AUDIO` etsii samannimisen tabin,
  jolla on audio (esim. AI-tabi), ja liittää sen audiopolun tuotuun
  tabiin (`POST /api/tabs/{id}/attach-audio`). Tämän jälkeen myös tuotu
  tabi soi, vierittyy ja toimii fullscreenissä koko kappaleen ajan.
- Katselimeen lisätty **Nopeus**-säädin (85–115 %). Sillä voi hienosäätää
  audion nopeuden tabin tempoon, esim. 140 BPM tabi + 144 BPM audio.
  `preservesPitch` pitää sävelkorkeuden normaalina.
- `LIITÄ AUDIO` näkyy vain tabilla, jolla ei ole audiota; liittämisen
  jälkeen PLAY, aikajana, cursor ja Nopeus tulevat näkyviin. Tuodun tabin
  `meta.json` päivitetään samalla, jotta audiolinkitys säilyy.
- Täydet kappaleet ovat oletus; pätkägenerointi on edelleen poikkeus.

## v1.27 – 18.10.2026

- Pätkägenerointi: katselimessa voi siirtyä kohtaan, valita 30/60/120 s ja
  painaa `TEE TAB TÄSTÄ`. Backend luo uuden jobin nykyisen tabin audiosta
  ja asetuksista (`POST /api/tabs/{id}/section`), leikkaa audiosta pätkän
  ja tekee tabin vain siitä. Uusi tabi avautuu automaattisesti ja sen
  nimessä on aikaväli, esim. `Seek & Destroy [0:28 +60s]`.
- Tuodut tabit merkitään kirjaston tooltipissa (`Lähde: tuotu tabi`).
  Moniraitaisesta GP5/MusicXML-tabista näytetään oletuksena kaksi
  ensimmäistä kitaraa (Guitar 1 + Guitar 2); loput raidat saa valittua
  raitanapeista.
- Pätkägenerointi käyttää samaa audiota ja samoja asetuksia kuin
  lähtötabi, joten se toimii myös YouTube-lähteille ilman uutta latausta.

## v1.26 – 18.10.2026

- Valmiin tabin tuonti: GP5 ja MusicXML (`POST /api/tabs/import`).
  Tuotu tabi tallennetaan `data/tabs/`-hakemistoon ja rekisteröidään
  kirjastoon; metatiedot (nimi, artisti, BPM, tahtimäärä) luetaan
  tiedostosta (PyGuitarPro / music21).
- UI: `Tuo valmis tabi (GP5 / MusicXML)` -tiedostovalinta ja
  `IMPORT TAB` -nappi. Tuotu tabi avautuu suoraan katselimeen.
- Tuodulla tabilla ei ole audiota, joten PLAY ja aikajana piilotetaan;
  tabi, raitavalinnat, näkymävalinta ja export toimivat. Export-linkit
  näytetään vain niille formaateille, jotka tabissa on.
- Tämä on suositeltu polku, kun halutaan juuri opeteltu standarditabi
  (esim. Songsterr/Guitar Pro) AI-luonnoksen sijaan.

## v1.25 – 18.10.2026

- YouTube-jobien nimi ja artisti haetaan nyt yt-dlp:n metadatasta ja
  puhdistetaan (esim. `(Remastered)` pois). `YouTube audio` jää vain
  fallbackiksi, jos metadata ei ole saatavilla.
- `meta.json` sisältää nyt `audio_path`-kentän myös web-jobille, joten
  tabi voidaan tuoda uudelleen ilman audion katoamista.
- Katseluun lisätty aikajana: nykyinen aika, kokonaiskesto, tahtilukema,
  −5 s/+5 s -siirtymät sekä Space- ja nuolinäppäimet. Tahtilukema auttaa
  hyppäämään intron jälkeen alkavaan riffiin.
- Olemassa oleva Seek & Destroy -tabi nimettiin uudelleen
  (`Metallica — Seek & Destroy`) tietokantaan, `meta.json`iin, GP5:een ja
  MusicXML:ään.

## v1.24 – 18.10.2026

Soittonäkymän seurattavuus ja siisteys.

- Cursor ei enää karkaa ruudun yläosaan rivinvaihdossa. Käytössä on
  alphaTabin `Smooth`-scroll ja negatiivinen `scrollOffsetY`, joka
  skaalautuu näkymän korkeuden mukaan. Edellinen järjestelmä jää näkyviin
  nykyisen yläpuolelle, joten etenemistä ja jo soitettua kohtaa on helppo
  seurata.
- Dynamiikkamerkinnät (`p`, `mp`, `mf`, `f`, …) piilotettu. Ne syntyivät
  Basic Pitchin velocity-arvoista eivätkä tuo tablatuuriin lisäarvoa.
  Piilotus tehdään `NotationElement.EffectDynamics` -asetuksella, joten
  se koskee myös vanhoja tabeja ilman uudelleengenerointia.

## v1.23 – 18.10.2026

Katselunäkymän parannukset Phase 2:n päälle.

- Oletusnäkymä on pelkkä tablatuuri. `Näkymä`-valinnalla voi vaihtaa
  tab + nuotit, nuotit tai Auto (kitarat tablatuurina, muut nuotteina);
  valinta muistetaan selaimessa.
- Raitavalitsin: tabin raidat voi näyttää ja piilottaa. Valinta
  muistetaan tabikohtaisesti. Nykyiset generoidut tabit sisältävät
  yhden `Guitar`-raidan.
- `FULLSCREEN` ja automaattinen koko näyttö PLAY:ta painettaessa; Esc
  palauttaa. Koko näytössä tabit skaalautuvat ruudun mukaan.
- Soittocursor: vihreä tahtikorostus ja beat-viiva seuraavat paikallista
  audiota. alphaTabin cursor-CSS lisätty, koska vendor-bundlessa ei ole
  tyylejä.
- Vaakascrollbar poistettu tablatuurin alta; pitkä tabi vierittyy
  pystysuunnassa.
- Kirjaston napeissa tooltip (tahtimäärä, nuotit, BPM, luontiaika ja ID),
  joten samannimiset versiot erottuvat. Myös lomakkeen valikoissa tooltipit.
- `EXPORT` siirretty pois pääkontrolliriviltä; tilalla näkymä- ja
  raitavalinnat.

## v1.22 – 18.10.2026

Tuotenimi vaihdettu: **AI TabTool**.

- `APP_NAME` = "AI TabTool"; HTML-otsikot, wordmark `AI TABTOOL` ja
  brand-mark `AT` (aiempi `TT` muistutti TabToolia).
- `start.bat` ja `scripts/open_browser.ps1` käyttävät uutta nimeä.
- Sisäiset tunnisteet ennallaan: `TABTOOL_*`-ympäristömuuttujat,
  `data/tabtool.sqlite3` ja repo `teppoaland/tabtool`.
- Testit päivitetty uuteen nimeen; ei toiminnallisia muutoksia.
- README: nimi- ja tavaramerkkihuomautus.

## v1.21 – 18.10.2026

- `start.bat` avaa oletusselaimen automaattisesti vasta kun palvelin
  vastaa `/api/health` (uusi `scripts/open_browser.ps1`, 30 s timeout).
- `TABTOOL_NO_BROWSER=1` ohittaa automaattiavauksen (automaatio/testit).
- Ei muita toiminnallisia muutoksia.

## v1.20 – 18.10.2026

Phase 2 – web-käyttöliittymä, job-jono, cache, alphaTab ja paikallinen toisto.

### Muutokset

- `app/db.py`: SQLite-skeema (`tracks`, `jobs`, `tabs`, `oauth_tokens`,
  `settings`), cache-avain, `data/`-juureen sidotut polkuapurit ja
  CLI-tabien tuonti (`data/tabs/<nimi>/meta.json`).
- `app/jobs.py`: yhden workerin job-jono, vaihekohtainen progress
  (queued → downloading → separating → transcribing → building → ready),
  SSE-tilaukset, cache-osuma ilman uutta ajoa, `regenerate`-tuki.
- `app/main.py`: `POST /api/jobs` (upload / YouTube / local path),
  `GET /api/jobs`, `GET /api/jobs/{id}`, `GET /api/jobs/{id}/events`,
  `GET /api/tabs`, `GET /api/tabs/{id}`, inline `score/{fmt}`,
  attachment `export/{fmt}` ja Range-tuettu `audio`.
- UI: upload/YouTube-lomake, viritys/grid/nopea tila, status-rivi,
  kirjasto, alphaTab-katselin, `PLAY`/`PAUSE` ja `EXPORT`.
- alphaTab 1.8.4 vendoroituna (`app/static/vendor/alphaTab/`,
  MPL-2.0 + Bravura OFL), ulkoinen media `IExternalMediaHandler`illa ja
  50 ms positiosynkka.
- Tabit kirjoitetaan temp-hakemistoon ja `os.replace`lla; cache-avain =
  audion sormenjälki + pipeline-versio + asetukset.
- 45 pytest-testiä; API-, cache-, validointi- ja polkuturvatestit
  mockatulla putkella.

### Validointi

- Oikea putki nopeassa tilassa 20 s klipillä: 12 tahtia, 58 nuottia,
  GP5 luettu takaisin (78 nuottimerkintää), MusicXML jäsentyy.
- 137 tahdin KISS-tabi renderöityy alphaTabilla headless-Chromessa
  (30 254 px korkea sivu, nuottimerkinnät piirtyvät).
- 46 MB WAV striimautuu Range-pyynnöllä (206, `bytes 0-99/...`).
- Korjaukset browser-validoinnissa: fonttipolun trailing slash,
  `PlayerState`-enumin puuttuminen UMD-globalista, `useWorkers: false`.

## v1.11 – 18.10.2026

Tie-korjaus ja validointi.

- GP5- ja MusicXML-viennissä tie-tila on nyt nuottikohtainen. Aiemmin
  saman segmentin uudet ja edellisestä tahdista jatkuvat nuotit saivat
  saman tie-tilan (255 sekasegmenttiä KISS-testissä).
- Uusi testi `test_tie_state_is_per_note`.
- 30 pytest-testiä.
- Koko YouTube-testikohde (KISS – I’m A Legend Tonight, 4:00) ajettu
  läpi: 137 tahtia, 1410 tab-nuottia, GP5 validi, ei rikkinäisiä
  tahtikestoja eikä päällekkäisiä kieliä.

## v1.10 – 18.10.2026

Phase 1 – audio-to-tab -putki.

- Lisätty `app/pipeline/`: `audio_source`, `separate`, `transcribe`,
  `tempo`, `quantize`, `fretboard`, `segments`, `build`,
  `export_gp5`, `export_musicxml`, `export_midi`.
- `scripts/pipeline_smoke.py`: local/YouTube → ffmpeg → Demucs 6s →
  Basic Pitch → tempo → quantize → fretboard → GP5/MusicXML/MIDI +
  `meta.json`.
- Demucs `htdemucs_6s`, 4-stem fallback ja `--no-separation`-pikatila.
- Tempo normalisoidaan 70–180 BPM -alueelle (esim. 68 → 136).
- Kielikohtainen monofonia: päällekkäinen nuotti siirretään vapaalle
  kielelle tai edellistä nuottia lyhennetään.
- Fretboard-Viterbi ja virityspresetit: standard, drop D, Eb, D, open G,
  bass 4-string.
- GP5/MusicXML/MIDI-export. GP5 validointi: 108 tahtia, 884 tab-nuottia,
  ei rikkinäisiä tahtikestoja eikä päällekkäisiä kieliä.
- 29 pytest-testiä.
- ML-riippuvuudet: Demucs 4.1.0, Basic Pitch 0.4.0, TensorFlow 2.15,
  Torch 2.14 CPU. `setuptools<81`, koska Basic Pitchin resampy käyttää
  `pkg_resources`-APIa.
- Validointi: 3:10 MP3 ~67 s CPU:lla; YouTube 20 s klipit toimivat.

## v1.00 – 18.10.2026

Projektin runko ja säännöt.

- `git init`, `origin` = `teppoaland/tabtool`.
- `.gitignore`: `docs/`, `data/`, `.venv`, audio/tab-tiedostot, tokenit,
  mallit ja välimuistit pois julkisesta gitistä.
- `.clinerules/`: arkkitehtuuri, putken ydinsäännöt, versionhallinta,
  data/yksityisyys/lisenssit, kevyt polku ja ei ylimääräisiä dialogeja.
- FastAPI-runko: `/api/health`, `/api/version`, `/`, `/remote`, `/display`.
- Tyhjä tumma TV- ja remote-näkymä.
- `requirements.txt`, `requirements-ml.txt`, `requirements-dev.txt`.
- `setup.bat`, `install-ml.bat`, `start.bat`, `test.bat`.
- Ensimmäinen pytest-testi ja versiotarkistus.
- Lisenssi: All rights reserved. Kolmannen osapuolen lisenssit erillisessä
  `THIRD_PARTY_NOTICES.md`-tiedostossa.
