# 🎯 Projektin lyhyt kuvaus – AI TABTOOL

> **Versio:** `v2.14` (25.10.2026)
> **Repo:** https://github.com/teppoaland/tabtool
> **Paikallinen:** `D:\AI\tabtool`

## Tavoite

Lokaali web-palvelu, jossa voi:

1. hakea kappaleita Spotifysta (haku/metadata),
2. generoida kitaratablatuuri omasta MP3:sta tai YouTube-audiosta,
3. tuoda GP5/MusicXML-tabeja **linkistä tai koneelta** ja liittää niihin
   YouTube-audio yhdellä toiminnolla,
4. katsoa tablatuuria alphaTabilla TV:stä/tietokoneelta (aikajana,
   cursor, fullscreen, raitavalinnat, BPM/Nopeus),
5. valita ja poistaa kappaleita LIBRARY-modaalin kirjastosta,
6. käyttää puhelinta kaukosäätimenä sisäverkossa (QR-pariutus,
   valinnainen LAN-PIN),
7. viedä tabin GP5/MusicXML/MIDI-muodossa.

## Lukitut päätökset

- **Local-first audio:** tab-generointi ja taustatoisto tehdään samasta
  paikallisesta audiosta. Spotify ei anna raakaa audiota (DRM).
- **Spotify** = haku, metadata ja valinnainen toisto. Spotify-integraatio
  tulee vasta Phase 3:ssa.
- **YouTube** ladataan yt-dlp:llä audiostreamina; mainokset eivät tule
  mukaan. Käyttäjä vastaa ToS/tekijänoikeuksista.
- **Kitara ensin.** Basso, laulu ja rummut myöhemmin; rummut vaativat
  oman transkriptiomallin.
- **Täydet kappaleet ovat oletus.** Pätkägenerointi on poikkeus.
- **Valmiin tabin tuonti** GP3/GP4/GP5/MusicXML joko linkistä (palvelin
  lataa tiedoston) tai koneelta. GP3/GP4 muunnetaan GP5:ksi (v1.99:
  GP3:n −1-grace-fret sanitoidaan ennen kirjoitusta). GP5-lähde
  ohittaa AI-generoinnin; YouTube-
  linkin kanssa audio liitetään samalla kertaa yhdellä jobilla. Ilman
  GP5-lähdettä tabi generoidaan AI:lla. Samannimisen AI-tabin audio
  voidaan myös liittää tuotuun tabiin. Tabin BPM korjattavissa
  desimaalilla (GP5 tallentaa kokonaisluvun; desimaali on toiston
  korjaus), `Nopeus` 50–150 % harjoitteluun, `SYNC` ±10 % hienosäätöön
  ja `SIIRTO` tahdeittain (±999, 0,25 tahdin askel = 1 isku) rakenne-eroon
  tai vakiosiirtoon; kaikki tallentuvat tabille.
- **Ei pakollista Guitar Prota.** TuxGuitar on ilmainen apuväline
  tarvittaessa; appi tuo GP5/MusicXML:n.
- **Sääntö #1 – soitto on koskematon.** Soitto ja tablatuurin osoittimen
  kohdistus on ainoa 1:1-validoitu toiminto (Seek & Destroy, SIIRTO −0,75 /
  BPM 142). Ydintä ei muuteta ilman erillistä lupaa; uudet ominaisuudet
  lisätään sen ulkopuolelle ja jokainen ydinmuutos validoidaan
  regressiochecklistillä. **Hyväksyntä on käyttäjän kuuntelu-/tabsynkkitesti**
  – automaatio ei kuule heittoa, joten Cline ei julista synkkaa korjatuksi
  ilman kuittausta. Palvelimen käynnistää ja pysäyttää käyttäjä omassa
  CMD-ikkunassaan. Katso `.clinerules/07-playback-frozen.md`.
- **Nopeus on harjoittelunopeus, ei kohdistus (v1.96–v1.97).** `Nopeus`
  50–150 % skaalaa audion ja kursorin yhdessä; `playbackRate` ei kuulu
  kello- eikä seek-matematiikkaan. 1 % askelet ja 95–105 % → 100 % snap;
  kaksoisnapautus palauttaa 100 %. Vartiotesti
  `test_playback_rate_never_enters_the_alignment_math`.
- **Remote (v1.93–v1.98):** puhelimen otsikko yhdellä rivillä (AI TABTOOL,
  versio ja yksi tila-indikaattori `Online` / `Offline` / `Offline-TV`).
  Soittopalkissa `«` (alkuun, `seek 0`) ja PLAY/PAUSE; `+5 s` poistettu.
  QR-lohko on sivun alaosassa (piilossa puhelimessa). Nopeus 1 % askelet +
  10 %:n ikkuna. `start.bat` pysäyttää vanhan Python/uvicorn-instanssin ja
  käynnistää uuden yhdellä ajolla (v1.94); vierasta prosessia ei tapeta.
- **Settings (v2.02):** `/settings` (SETTINGS yläpalkissa REMOTE- ja
  API-linkkien jälkeen) säätää count-inin askelmat/kestot, Näkymän
  oletuksen ja jokaisen päänäkymän toiminnon näkyvyyden (oletus: näkyvissä)
  sekä puhelimen LISÄÄ/SÄÄDÄ/Nopeus/soitinvalinnan. Oletukset ovat
  `app/settings.py`:ssä, arvot `settings`-taulussa (`GET/POST
  /api/settings`). Asetukset eivät vaikuta soittoketjuun. Puhelimessa
  SOITA/LISÄÄ/SÄÄDÄ ovat sivun alaosassa ja niiden paikalla ovat tabin
  soittimet: napautus näyttää/piilottaa raidan TV:n tablatuurista.
- **Kirjastot aakkosissa bändin nimellä (v2.00–v2.01).** TV:n LIBRARY ja
  puhelimen SOITA/SÄÄDÄ järjestetään `artist` → `title`
  (`localeCompare("fi", {numeric:true, sensitivity:"base"})`).
  Remote-kirjastossa ei ole sisäistä scroll-ikkunaa: lista kasvaa sivun
  mukana (yksi scrollbar).
- **All rights reserved** (GameHubin käytäntö). Kolmannen osapuolen
  lisenssit `THIRD_PARTY_NOTICES.md`:ssä.
- **Kappaleen poisto** (v1.38): poistaa tabin, hakemiston, stemmit sekä
  job/track-rivit. Jaettu audio säilyy, jos toinen tabi käyttää samaa
  tiedostoa. MP3-kuunteluversio jää tarkoituksella arkistoon.
- **LIBRARY-modaali** (v1.38, entinen SEARCH v1.49): haku, GP5-linkki/-tiedosto,
  MP3-valinta, kirjasto ja kappaleen valinta samassa ikkunassa; TV-näkymä
  on soittoa varten. Poistolla on oma varoitusdialogi. Tabi on oletuksena
  tummassa teemassa. Count-in **5 → 0** on toteutettu v1.56:ssa
  soittoketjun ulkopuolelle (overlay + portinvartija
  `handlePlayButton`); ks. `.clinerules/07-playback-frozen.md`.
  KIRJASTO on modaalissa vasemmalla ja generaattori oikealla (v1.64);
  rivin poisto on punainen × (v1.65). Count-in on kytkettävissä
  **ON/OFF** (v1.81): kytkin on FULLSCREEN-napin alla sekä normaalissa
  että koko näytön näkymässä, oletus ON, valinta muistetaan selaimessa.
- **LAN-kaukosäädin (v1.82–v1.90):** `start.bat` sitoo palvelimen
  sisäverkkoon ja tulostaa LAN-osoitteet. **`/remote`-sivu näyttää
  150 × 150 px QR-koodin** ja osoitteen; QR generoidaan **pyydettäessä sen
  hetkisestä IP-osoitteesta** (ei kiinteää IP:tä; DHCP saa vaihtua).
  Puhelin avaa `/remote`-näkymän: PLAY/PAUSE, ±5 s, toistokohta, Nopeus ja
  kirjaston valinta. **Yksi toiminto kerrallaan:** SOITA / LISÄÄ / SÄÄDÄ;
  lisäys estetty soiton aikana ja soitto jobin aikana (409). Toisto
  tapahtuu aina tietokoneen omasta
  audiotiedostosta. Valinnainen `TABTOOL_LAN_PIN` vaatii PINin localhostin
  ulkopuolelta; QR-pariutus kirjaa puhelimen sisään istuntotokenilla.
  Kaukosäätö ei muuta soittoketjua: TV:n silta klikkaa olemassa olevia
  kontrolleja.
- **Sormitusversiot (v1.72, v2.04):** AI-tabi generoidaan kolmella
  otelautaprofiililla (V1 · Avoimet kielet / V2 · Boksi / V3 · Vähän
  liikettä) samoin sävelin. `VALITSE TÄMÄ` kysyy varmistuksen ja
  varmuuskopioi muut versiot `data/backups/variant-<tab_id>/`iin ennen
  poistoa; `PALAUTA VERSIOT` peruu valinnan. Tuntematonta kappaletta voi
  siis kokeilla korvakuulolta ilman pelkoa pysyvästä valinnasta.
- **Kirjaston metadata on käyttäjän dataa** (v1.63, v2.03): oma nimi
  (`title_override`, generaattorin nimi säilyy `original_title`ina) ja oma
  esittäjä (`artist_override`, alkuperäinen `original_artist`ina; tyhjä
  palauttaa generaattorin arvon), lukitus (estää poiston ja muutokset) ja
  arkistointi (piiloon päälistalta, `ARKISTO (n)` -linkki listan lopussa).
  Lista on aakkosjärjestyksessä ylikirjoitetun esittäjän mukaan.
- **Tiedot-modaali (v2.03):** kirjastorivin **Tiedot** avaa modaalin, jossa
  esittäjä, nimi, viritys, lukitus ja arkistointi ovat muokattavissa ja
  absoluuttiset tiedot (BPM, tahtia, nuotteja, kanava, lisäysaika, ID)
  näkyvät vain luku -tietoina. Samassa ikkunassa ovat **Audiolähde**- ja
  **Tablähde**-linkit: `meta.audio_source_url` (YouTube-linkki, josta audio
  ladattiin) ja `meta.tab_source_url` + `meta.tab_source_file` (GP-linkki /
  tiedostonimi). Vanhat AI-tabit saavat audiolinkin `meta.source`-kentästä;
  `scripts/backfill_source_url.py` täydentää puuttuvan job-riveistä.
- **Oma tuontikirjasto (v1.66):** valmiit GP3/GP4/GP5- ja MusicXML-tabit
  tuodaan kansiosta kerralla (`scripts/import_folder.py`) ja viedään ulos
  (`scripts/export_tabs.py`: GP5/MusicXML/MIDI + `manifest.json` + ZIP).
  Tuodut tiedostot ovat `data/`ssa ja `D:\tabtool_files`issa (gitignored)
  – ne eivät koskaan mene julkiseen gitiin.
- **YouTube-lähde näkyviin (v1.67):** tabille tallentuu `youtube_channel`
  ja se näytetään (`YT: <kanava>`), koska GP5 sopii yleensä vain yhteen
  saman kappaleen uploadiin.
- **Viritys näkyviin (v1.68):** GP5:n avoimet kielet → `tuning_label`
  (esim. `D Standard · DGCFAD`) + `tuning_notes`; manuaalinen ylikirjoitus
  kirjaston NIMEÄ-lomakkeessa. Tuonti ei muuta tabitiedostoa eikä
  Viritys-valinta vaikuta siihen (se on vain AI-generointia varten).
  Viritys luetaan **kitararaidasta** (v1.79: eniten nuotteja, 6 kieltä;
  ei raidasta 0, joka on usein laulu). `scripts/retune_tab.py` (v1.80)
  vaihtaa virityksen säilyttäen soivat sävelet (nauhat siirtyvät
  kielikohtaisesti) – silloin GP5 on oikeasti uudessa virityksessä.
- **Tab-datan työkalut (v1.76–v1.80):** `app/tab_edit.py` + skriptit
  `expand_repeat.py` (toisto kirjoitetaan tahdeiksi, koska katselimen kello
  seuraa kirjoitettua aikajanaa), `trim_bars.py` (ylimääräiset tahdit pois)
  ja `retune_tab.py` (virityksen vaihto). Kaikki varmuuskopioivat GP5:n
  `data/backups/`iin, validoivat tuloksen lukemalla tiedoston takaisin ja
  palauttavat varmuuskopion, jos jokin ei täsmää.
- **Sanat sidecarina (v2.06):** laulun sanat eivät mene GP5/MusicXML/MIDIin
  eivätkä tabin metadataan, vaan omaan tiedostoon
  `data/lyrics/<tab_id>.json` (`{"tab_id", "updated_at", "measures":
  {"10": "…"}}`). `app/lyrics.py` validoi ja kirjoittaa atomaarisesti;
  `GET/PUT /api/tabs/{id}/lyrics`. Katselimen SANAT-editori kirjoittaa vain
  tämän tiedoston, ja overlay näyttää kuluvan tahdin rivin lukemalla
  `#bar-readout`-tekstiä (`MutationObserver`) – ei kelloa, ei
  alphaTab-kutsuja, ei audion kirjoituksia. Editori on **kelluva, raahattava
  ja kooltaan säädettävä paneeli** (ei modaalia, ei `body.modal-open`ia),
  joten soitto toimii sen takaa; otsikko näyttää kuluvan tahdin. Soiton
  aikana näkyvän rivin koko tulee Settingsistä (`lyrics.scale`, oletus
  200 % = tuplat, CSS-muuttuja `--lyrics-scale`) ja koko näytön nosto
  alareunasta (`lyrics.offset_px`, oletus 100 px, `--lyrics-offset`);
  fullscreenissa rivi on 96vw leveä → yksi rivi isommallakin koolla.
  Rivin tausta on **täysin musta** (`#000`) ja sivupadding 3ch, joten
  liikkuva tabi ei häiritse lukemista. Editorissa on kaukosäätimen
  perussoitto (PLAY/PAUSE, «, −5 s, +5 s) ja **tahtinumeron klikkaus hyppää
  siihen tahtiin** `api.tickPosition`-tick-seekillä (alphaTabin tempokartta,
  myös tempo-automaatiot; ei omaa aikamatematiikkaa). Tahtilista on
  oletuksena 14rem ja sen ja sanoituskentän välissä on jakokahva
  (`#lyrics-split`): listan kasvaessa tekstikenttä pienenee, ja jako
  muistetaan. Tabin poisto poistaa sidecarin; lukittu tabi saa silti sanat.
- **Songsterr / Ultimate Guitar:** ei scrapea eikä kiertämistä.
  Songsterr-appin cache sisältää vain SVG-renderin, beat-ajastuksen ja
  audion (ei string/fret-dataa), ja GP/MIDI/MP3-lataus on Plus-ominaisuus
  (`songsterr.com/ai.txt`). Käyttäjän Android-osto on **kertamaksu**
  (vain Android, ei web). GP5:t haetaan laillisesta lähteestä käsin.
- **Versiosarja `1.x`**, aloitus `v1.00`; nyt `v2.14`.
- **Ei julkista julkaisua:** koodi pidetään lokaalina. Commitit tehdään
  paikalliseen repoon palautuspisteiksi (revert); push GitHubiin vain
  erillisestä pyynnöstä.
- **Ulkoinen sisältö arkistoidaan** `D:\tabtool_files\`
  (`TABTOOL_EXTERNAL_DIR`): YouTube-audiot ja tuodut GP5/MusicXML
  luettavalla nimellä. `data/` on totuuden lähde; hard link samalla
  levyllä, joten tiedostot löytyvät myös muuhun käyttöön ilman
  tuplalevytilaa. YouTube-latauksista tehdään lisäksi MP3
  `audio/mp3/<Artisti>/`-kansioon omaan kuunteluun; MP3-valinta on
  oletuksena päällä, ja kappaleen poisto jättää MP3:n hakemistoon.
- **Tuotenimi `AI TabTool`** (v1.22–v1.40). Repo/hakemisto `tabtool`,
  `TABTOOL_*`-ympäristömuuttujat ja `data/tabtool.sqlite3` ovat teknisiä
  nimiä. Ei sidoksissa tabtool GmbH:hen eikä SEYDEL TabTooliin.
- UI-tekstit ovat toistaiseksi suomeksi; pelaajalle näkyvät ydintekstit
  ovat englanniksi (SEARCH, GENERATE TAB, PLAY, PAUSE, EXPORT, REMOTE).

## Ei kuulu tähän projektiin

- ei pilvipalvelua eikä monikäyttäjätilejä
- ei Spotifyn DRM-audion tallennusta tai purkamista
- ei pelien fysiikkaa, kukkaro-/jukebox-logiikkaa tai GameHubin
  `10.x`-versiointia
- ei npm-riippuvuuksia eikä build-vaihetta frontendiin

## Session aloitus

Sano Cline:lle **`lue membank`**. Sääntö on
`.clinerules/00-memory-bank.md`:ssä.

## Tärkeät tiedostot

- `README.md` – käyttöohje ja tila
- `CHANGELOG.md` – versiohistoria
- `.clinerules/` – 8 projektisääntöä (sääntö #1 = koskematon soitto)
- `app/pipeline/` – audio-to-tab-putki
- `app/tab_import.py` – GP3/GP4/GP5/MusicXML-tuonti (+ GP5-sanitointi)
- `app/tab_download.py` – GP5/MusicXML-linkin palvelinlataus
- `app/library.py` – kappaleen poisto (tab/audio/stemmit, MP3 jää)
- `app/tab_edit.py` – tab-datan muokkaus (toisto, tahdin poisto, viritys)
- `app/lyrics.py` – sanojen sidecar (`data/lyrics/<tab_id>.json`)
- `scripts/pipeline_smoke.py` – CLI-proof
- `stop.bat` / `status.bat` – palvelimen pysäytys ja tilan tarkistus
- `tests/` – 270 pytest-testiä
- `data/` – GITIGNORED: audio, stemmit, tabit, tokenit
- `docs/` – GITIGNORED: henkilökohtainen suunnitelma
