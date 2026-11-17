# 🎹 PianoCapture v1.16

PianoCapture on **erillinen, kevyt app** AI TabToolin rinnalla samassa repossa.
Se ottaa YouTube-linkin (tai äänitiedoston), etsii pianon alun ja bändin
sisääntulon, transkriboi pätkän nuoteiksi ja näyttää ne **88-skaalaisella
pianokoskettimistolla** laskevina nuotteina ilman nuottiviivastoa.

Sovellus on tarkoitettu pianon alkuosille ja lyhyille pätkille, ei kokonaisille
kappaleille.

## Rajaus (tärkeä)

- **Soittimia ei erotella.** Oletus on, että pätkässä soitin on piano. Jos
  pätkä sisältää rumpuja, kitaraa tai orkesteria, transkriptio on sotkuinen –
  se on käyttäjän valinta, ei bugi.
- **Aikaikkuna on ainoa portti.** Alku ja loppu valitaan joko automaattisen
  ehdotuksen pohjalta tai käsin. Ehdotus ei ole totuus: se näytetään aina
  muokattavana.
- **Ei kitaran mallia.** Ei viritystä, ei otelautaa, ei GP5:tä. Nuotti on
  `pitch / start / end / velocity`, ja soitin on 88 koskettimen piano (A0–C8).

## Käynnistys

```bat
start-piano.bat
```

- Työpöydän **PianoCapture**-kuvake tekee saman (käynnistää `start-piano.bat`in
  ja avaa selaimen). Kuvake käyttää `piano/static/piano.ico`-ikonia, jotta se
  erottuu TabTool-kuvakkeesta.
- Yksi kaksoisklikkaus riittää myös uudelleenkäynnistykseen: vanha 8020:n
  instanssi pysäytetään ensin. Sulje konsoli-ikkuna (tai Ctrl+C) lopettaaksesi.
- `PIANO_NO_BROWSER=1` estää selaimen automaattisen avauksen (esim. testaus).
- UI: <http://127.0.0.1:8020>
- API-dokumentaatio: <http://127.0.0.1:8020/docs>
- Oma data: `data_piano/` (gitignoroitu). TabToolin `data/` ja portti 8000
  eivät ole käytössä.
- Sama venv kuin TabToolilla: Torch/Demucs/Basic Pitch -asennuksia ei
  tarvitse tehdä uudelleen.

## Työnkulku

1. **EHDOTA RAJAT (valinnainen apu)** – lataa äänen kerran
   (`data_piano/sources/`), ottaa ensimmäiset 180 s ja ehdottaa ikkunan:
   - **piano alkaa** = ensimmäinen kestävä harmoninen alkusoitto
     (HPSS: harmoninen vs. perkussiivinen energia; vesi/taustakohina on
     pääosin perkussiivista, piano harmonista),
   - **bändi tulee mukaan** = ensimmäinen kestävä (~0,5 s) hyppy sekä
     perkussiivisuudessa että kokonaisäänenvoimakkuudessa; matala kaista ja
     onset-tiheys ovat lisätodisteita.
   Tämä ei ole pakollinen: voit kirjoittaa aloitus- ja lopetussekunnit itse.
2. **Tarkista rajat** – alku ja loppu annetaan muodossa **min:sek**
   (esim. `1:42`) tai pelkkinä sekunteina. Kenttien vieressä näkyy sama väli
   kokonaisina sekunteina, esim. `0:00–1:42 · 102 s`.
3. **LUO SOITTO-OHJE** – ainoa pääpainike. Se avaa vahvistusdialogin, joka
   kertoo mitä tapahtuu (ääni ladataan, pätkä leikataan, piano transkriboidaan,
   ohje tallentuu). **PERUUTA** lopettaa ennen työtä, **JATKA** käynnistää
   taustatyön. Valmis pätkä tallentuu `data_piano/pieces/<id>/`.
4. **Soita** – 88 koskettinta, laskevat nuotit, soittopää, vasen/oikea käsi
   eri väreillä, nopeus 50–100 %, loop ja ORG/MID/mute-toistolähde.
   Käyttöohjeet ovat soittimen **(i)**-painikkeen takana, ja painikkeiden
   hover-vihjeet kertovat loput.

Pikanäppäimet: `Space` = PLAY/PAUSE, `←`/`→` = ±5 s, `Home` = alkuun.

## Kirjasto – nimeä ja poista

YouTube antaa usein sotkuisen otsikon (esim. *For Us: Metal Instrumentals —
THE GATHERING - Shrink [Instrumental]*). Listan oikeassa ylänurkassa on
**MUOKKAA**:

- **NIMEÄ** avaa dialogin, jossa artisti ja kappale voi kirjoittaa siistiksi.
  Nimi päivittyy heti listaan ja soittimen otsikkoon. Ensimmäinen automaattinen
  otsikko säilyy `piece.json`issa (`original_title` / `original_artist`),
  joten alkuperäinen YouTube-nimi ei häviä.
- **POISTA** kysyy vahvistuksen ja poistaa ohjeen äänineen ja nuotteineen
  pysyvästi (`DELETE /api/piano/pieces/<id>`).
- **VALMIS** palaa normaalitilaan, jossa rivi avaa ohjeen soittimeen.
- **Lähde** näkyy rivin tooltipissa ja NIMEÄ-dialogissa; `piece.json` säilyttää
  alkuperäisen URLin (`source.url`), joten lähde on aina tarkistettavissa.

Nimeäminen ei muuta nuotteja, ääntä eikä kiertoa – vain sen, miltä ohje
näyttää listassa.

## KIERTO – opettele yksi kuvio

Pianon alku on usein lyhyt kuvio, joka toistuu 2–4 kertaa. Koko intron
opetteleminen sellaisenaan on turhaa työtä: yksi kierto riittää, ja loput ovat
sama asia bändin kanssa.

- **KIERTO**-valinta näyttää ja loopittaa vain yhden kierron: nuotit rajataan
  kierron loppuun ja ääni hyppää takaisin alkuun.
- **Kierron pituus** ehdotetaan automaattisesti: onset-voimakkuuden
  autokorrelaatiosta etsitään vahvin jakso välillä 1,5–12 s (vähintään kaksi
  toistoa). Ehdotus näkyy muodossa `3,8 s × 3,9`.
- **÷2 / ×2** vaihtavat tahtitasoa: jos ajattelet kuvion olevan 2 tahtia mutta
  työkalu löysi 1 tahdin (tai päinvastoin), yhdellä painalluksella saa oikean.
- Numeroa voi myös kirjoittaa suoraan, joten korvalla tehty korjaus on aina
  mahdollista. Automaatti on ehdotus, ei totuus.
- Jos toistoa ei löydy varmasti (onset-autokorrelaation huippu alle 0,15),
  **KIERTO on pois päältä** ja näytetään koko pätkä. Näin kautta sävelletylle
  introlle ei tarjota väkisin kiertoa – sen voi silti asettaa käsin.
- **KIERTO on oletuksena pois:** koko pätkä näytetään ja **Loop** toistaa
  sen. KIERTO valitaan käsin, jolloin näytetään ja loopitetaan yksi kuvio;
  kierron pituus ja ÷2/×2 ilmestyvät vasta silloin.

Kun kierto on opeteltu, ota **KIERTO** pois päältä: soitto jatkuu koko pätkän
(yhteensä bändin kanssa), ja nuotit näytetään alkuperäisessä pituudessaan.

## Kuuntele ohje – onko transkriptio oikein?

Aloittelija ei ehdi soittaa kuviota niin nopeasti, että voisi verrata sitä
levyyn. Siksi ohjeen voi **kuunnella sellaisenaan**:

- **ORG / MID PLAY-painikkeen vieressä:** **ORG** soittaa alkuperäisen
  äänitteen, **MID** soittaa transkription pianomaisella synteesillä
  (harmoninen sarja + vaimeneva envelope). Kun klikkaat valittua painiketta
  uudelleen, kumpikaan lähde ei ole päällä: ääni on mykistetty ja nuotit
  liikkuvat – soitat itse mukana omalla pianolla. Vaihto kesken toiston
  vaihtaa lähteen samasta kohdasta, joten A/B-vertailu on välitön.
- **LATAA OHJE (MP3)** – koko transkriptio audiotiedostona (serveri renderöi
  sen `guide.wav` → `guide.mp3`, cache pätkän kansiossa). Voit kuunnella sen
  puhelimessa tai hidastaa sitä missä tahansa soittimessa.
- **LATAA MIDI** – sama sisältö MIDInä DAWiin/MuseScoreen.

Synteesi on tarkoituksella yksinkertainen eikä se ole pianon sample: se riittää
kertomaan, *mitkä nuotit* ohjeessa on ja *milloin* ne alkavat. Vertaa aina
alkuperäiseen – se on ainoa totuus.

**v0.5.2:** korjattu bugi, jossa MID-ääni katosi kokonaan, jos sitä ennen oli
soittanut pidempää pätkää (esim. Gathering 2:07 → Diablo 0:15). Syy oli
ääniaikaan sidottu "voices"-throttle, joka jäi päälle pitkästä pätkästä; nyt
se on poistettu ja äänimäärä nollataan pätkän vaihtuessa.

## Käsien rajaus myös latauksiin (v0.6)

Kun **Vasen** tai **Oikea** otetaan pois päältä, myös **LATAA OHJE (MP3)** ja
**LATAA MIDI** rajaavat pois piilotetun käden – esimerkiksi Diablon vasemman
käden haamunuotit. Rajana on **Käsiraja** (oletus C4 = MIDI 60), ja serveri
renderöi rajatun version omaan cacheensa (`guide-right-60.wav` yms.).
Kun molemmat kädet ovat näkyvissä, lataus sisältää kaikki nuotit.

**v0.6.1:** käsivalinta muistetaan **pätkäkohtaisesti** (localStorage), joten
Diablo avautuu suoraan oikea käsi -tilassa ja TG molemmilla käsillä. Itse
`piece.json`ia ei muuteta – alkuperäiset nuotit pysyvät tallessa ja
rajaus tehdään näkymään, synteesiin ja latauksiin.

**v0.6.2:** sekä **Taustaääni** että **Ohjeääni** muistetaan selaimessa, joten
ORG/MID-valinta säilyy reloadin yli. Jos molemmat olisivat pois päältä,
sovellus palauttaa automaattisesti ORGin – PLAY ei jää mykäksi eikä
ORG/MID-valinta tyhjäksi. Mix-tilassa (molemmat päällä) molemmat vaihtoehdot
näkyvät valittuina.

**v0.7.0:** ORG/MID on nyt **kolmitilainen**: ORG, MID tai ei kumpaakaan
(= mykistetty). Erilliset **Taustaääni**- ja **Ohjeääni**-valinnat poistettiin,
koska sama asia valitaan ORG/MID-painikkeilla. Mute ei ole pysyvä asetus:
reload palaa viimeksi valittuun äänilähteeseen, joten sivu ei avaudu mykkänä.
Kaikki käyttöohjeet siirtyivät PLAY-rivin alta **(i)**-painikkeen taakse ja
painikkeiden hover-vihjeet kertovat loput. Samalla korjattiin ÷2-vihjeen
kirjoitusvirhe ("Puoleta" → "Puolita").

**v0.8.0:** työnkulussa on **yksi pääpainike**: **LUO SOITTO-OHJE** avaa
vahvistusdialogin, joka kertoo mitä tapahtuu (ääni, leikkaus, transkriptio,
tallennus), ja vasta **JATKA** käynnistää työn. **EHDOTA RAJAT** on nyt
valinnainen, hillitty apuri – kaksi samanarvoista nappia ei enää kilpaile.
Lista on **Kirjasto**, jossa **MUOKKAA** avaa **NIMEÄ**- ja
**POISTA**-toiminnot sotkuisten YouTube-otsikoiden siistimiseen.

**v0.8.1:** QR-koodi pois tuontikortista – tuonti tehdään PC:llä. Soittokortin
pätkä-QR siirrettiin kortin **oikeaan alakulmaan** latausrivin perään;
**Vasen/Oikea**-käsien selite ja **(i)** jäivät otsikkorivin oikeaan reunaan.

**v0.8.2:** tuontikortti siivottiin: **Puhelin/tabletti**-rivi ja sen
LAN-osoite poistettiin (pätkä-QR riittää) eikä kirjastosta avattu ohje
kirjoita enää "Valmis: N nuottia." -statusta tuontikorttiin. Lähdekentän
ohje on nyt kokonainen lause: *Valitse YouTube-linkki tai äänitiedosto,
josta haluat generoida soitto-ohjeen*. Listan nimi on **Kirjasto**.

**v0.8.3:** QR-koodin alla lukee nyt **Puhelin (i)**. `(i)`-vihje kertoo
hoverilla lyhyesti: *Voit avata soitto-ohjeen puhelimeen lukemalla QR-koodin
kameralla. PC ja puhelin täytyy olla samassa wifi-verkossa, jotta linkitys
toimii.*

**v0.9.0:** pitkä tuonti ei enää avaudu 5 sekunnin kiertona: automaattinen
KIERTO rajattiin enintään 30 s pätkille. Tuontikortti näyttää ikkunan myös
muodossa `0:00–2:22`, joten sekunnit eivät sekoitu aikaan 1:42. Kirjaston
rivi näyttää lähde-URLin tooltipissa, muokkaustilassa **Lähde**-linkkinä ja
NIMEÄ-dialogissa; `GET /api/piano/pieces` palauttaa nyt `url`-kentän.

**v0.10.0:** **Alku** ja **Loppu** syötetään muodossa **min:sek** (esim.
`1:42`) tai sekunteina; kentät, esikatselu ja vahvistusdialogi käyttävät
kokonaisia sekunteja. Myös analyysin ehdotusteksti pyöristyy muotoon `1:02`,
joten YouTube-UI:n `1:42` ei enää muutu vahingossa 142 sekunniksi.

**v1.00 – ensimmäinen release (15.11.2026).** UI ja tuontiputki on hiottu
release-kuntoon: yksi pääpainike ja vahvistusdialogi, Kirjasto
(nimeä/poista/lähde-URL), min:sek-rajat kokonaisina sekunteina, KIERTO
automaattisesti vain lyhyille pätkille, QR-vihje ja siisti mobiiliasettelu.
Tästä eteenpäin versio nousee **+0.01** jokaisesta muutoksesta (1.01, 1.02…).

**v1.01 – mobiilisoitin (15.11.2026).** Puhelimessa ja matalassa
vaakaruudussa pelaamisen ajaksi piilotetaan yläpalkki ja kappaleen alla oleva
ylimääräinen metarivi; soittokortti täyttää näytön ja koskettimisto skaalautuu
jäljelle jäävään tilaan. Soittorivi pysyy koskettimiston alla ja vierittyy
tarvittaessa vaakaan, joten PLAY/ORG/MID eivät katoa ruudun ulkopuolelle.
Latausrivi piilotetaan mobiilissa; käsien värit kerrotaan (i)-ohjeessa.

**v1.02 – vaakatason esitystila (15.11.2026).** Lyhyessä vaakanäkymässä
kappaleen otsikko piilotetaan ja (i) jää kelluvaksi ylänurkkaan. Soittorivi
on yksi kompakti rivi koskettimiston alla, joten tulevat nuotit ja
koskettimisto saavat lähes koko näytön. Pystyssä otsikko ja riveitty
soittorivi säilyvät.

**v1.03 – kappaleen vaihto puhelimessa (15.11.2026).** Soittimen otsikkoon
tuli **KIRJASTO**-painike: se vie kirjastoon, josta voi valita toisen
soitto-ohjeen. Lisäksi koskettimiston päältä voi nyt pyyhkäistä
pystysuunnassa (aiempi `touch-action: none` esti vierityksen), joten
kirjastoon pääsee myös eleellä.

**v1.04 – osoiterivi seuraa kappaletta (15.11.2026).** Kirjastosta
vaihtaminen päivittää `?piece=<id>`-osoitteen, joten reload tai kopioitu
linkki avaa juuri sen ohjeen, joka on ruudulla – ei edellistä. (Diablon
landscape-näkymän "kasaan meneminen" ei johdu datasta: Diablossa on
KIERTO päällä eli 3,8 s kierto ja lyhyet staccato-nuotit, kun taas
Shrinkissä KIERTO on pois ja pitkät nuotit täyttävät kankaan.)

**v1.05 – perussoiton oletukset (15.11.2026).** **Loop on oletuksena päällä
ja KIERTO pois**, joten koko kappale näkyy ja toistuu (myös Diablo 15 s).
KIERTO on nyt aina opt-in; sen pituus- ja ÷2/×2-säädöt piilotetaan, kun
KIERTO ei ole päällä. Nopeus 100 %, ORG ja molemmat kädet ovat oletukset.

**v1.06 – isompi puhelin-QR (15.11.2026).** PC-näkymän QR-koodi kasvoi
84 px:stä **112 px:iin** ja sai hieman lisää valkoista reunaa, jotta
puhelimen kamera (esim. Galaxy S10 Lite) lukee sen helpommin ruudulta.

**v1.07 – PC-ikkuna venyy (16.11.2026).** PC-selaimessa soittokortti täyttää
setupin ja kirjaston alle jäävän vapaan korkeuden. Nuottanäkymä skaalautuu
korkeuden mukaan: isompi ikkuna näyttää enemmän tulevia nuotteja samalla
nuottien pituudella (2,8 s → enintään 8 s), ei venytä nuotteja eikä pakota
koko kappaletta kerralla. Puhelin pysyy 2,8 s:ssä.

**v1.08 – nuoteista pyyhkäisy (16.11.2026).** Nuottialueelta voi pyyhkäistä
vasemmalle = eteenpäin ja oikealle = taaksepäin; täysi leveys ≈ 8 s. Toimii
hiirellä ja kosketuksella, myös puhelimessa. Pystypyyhkäisy vierittää sivua
edelleen, ja aikajana toimii ennallaan.

**v1.09 – pystysuuntainen haku (16.11.2026).** Nuoteista voi pyyhkäistä nyt
myös pystysuunnassa: alas = eteenpäin, ylös = taaksepäin (nuotien
kulkusuunta). Vaakasuunta toimii edelleen. Nuottiala varaa molemmat akselit,
joten sivun vieritys tapahtuu KIRJASTO-painikkeella tai nuottialueen
ulkopuolelta; aikajana toimii ennallaan.

**v1.10 – visuaalinen lataus (16.11.2026).** **LATAA VIDEO (MP4)** tallentaa
soittimen koskettimiston ja nuottialueen + äänen videoksi. Tallennus kestää
kappaleen pituuden; palvelin muuntaa WebM:n ffmpegillä MP4:ksi ja video
ladataan. Videon alueella ei ole kontrolleja.

**v1.11 – latausrivin turha teksti pois (16.11.2026).** Latausnappien edestä
poistettiin “Taustaksi:”/“Lataa:”-teksti; pelkät napit.

**v1.12 – videonauhauksen parillinen koko (16.11.2026).** Canvasin
taustapuskuri pakotetaan parilliseen leveyteen/korkeuteen, koska
MediaRecorder/VP9 pudotti parittomat videokehykset (audio tallentui, video jäi
0 kehykseen). Palvelin skaalaa videon myös parilliseksi ja raportoi
tarkemman ffmpeg-virheen.

**v1.13 – latausrivin järjestys (16.11.2026).** **LATAA VIDEO (MP4)** on
ensimmäisenä ja korostettu pysyvällä paksulla harmaalla reunuksella;
**LATAA AUDIO (MP3)** on viimeisenä. Ohje on transkriptio soitettuna pianolla
(MP3), MIDI on nuottidata DAWiin ilman ääntä; video sisältää jo ohjeäänen.

**v1.14 – ohje-MP3 pois (16.11.2026).** LATAA OHJE (MP3) -nappi poistettu;
jäljellä **VIDEO, MIDI ja AUDIO**. VIDEO pysyy korostettuna paksulla
harmaalla reunuksella ja saa keltaisen hoverin kuten muutkin.

**v1.15 – päivitysilmoitus Windows-versioon (17.11.2026).** Käynnistin
tarkistaa GitHubista uusimman PianoCapture-julkaisun ja ilmoittaa
ilmaisinalueella, jos uudempi versio on saatavilla; klikkaus avaa
lataussivun. Asennus ei ole automaattinen (pakettia ei ole allekirjoitettu).
Asentajan nimi on jatkossa ilman versionumeroa (`PianoCapture-Setup.exe`).

**v1.16 – päivitysilmoitus myös web-UI:hin (17.11.2026).** Sivu kysyy
`/api/piano/update` ja näyttää yläpalkissa **Päivitys saatavilla: V1.x**
-linkin, kun GitHubissa on uudempi julkaisu. Ilmoitus näkyy myös
ilmaisinalueella (Windows-launcher). Ei automaattiasennusta – linkki avaa
julkaisusivun.

## Toisto ja lataukset

- **Toistolähde ORG / MID / ei kumpaakaan:** ORG soittaa pätkän nuottien alla,
  MID soittaa transkription ja mykistää alkuperäisen, ja ei kumpikaan valittuna
  tarkoittaa mykistystä – kello ja nuotit jatkavat, joten voit soittaa omalla
  pianolla mukana. ORG/MID muistetaan selaimessa.
- **LATAA AUDIO (MP3)** – pätkä MP3:nä puhelimeen, DAW:iin tai
  taustanauhakäyttöön. Ensimmäinen lataus koodaa tiedoston ffmpegillä, sen
  jälkeen se tulee cachesta pätkän kansiosta.
- **LATAA OHJE (MP3)** – transkriptio audiona (ks. edellinen luku).
- **LATAA MIDI** – transkriptio MIDI-tiedostona (MuseScore, DAW, synteesi).
  Sama tiedosto kirjoitetaan jo käsittelyvaiheessa (`notes.mid`).

## Puhelin ja tabletti

Pianon edessä ei ole tilaa PC:lle, joten koko näkymä toimii puhelimessa tai
tabletissa samassa Wi-Fi-verkossa:

- `start-piano.bat` sitoo palvelimen `0.0.0.0`:aan. Soittokortin
  **oikeassa alakulmassa** on pieni QR, joka avaa juuri sen pätkän suoraan
  (`/?piece=<id>`). QR:n alla on **Puhelin (i)** -vihje: kamera lukee koodin
  ja PC:n sekä puhelimen pitää olla samassa wifi-verkossa. Erillistä
  osoiteriviä ei enää näytetä; tuonti (linkki ja rajat) tehdään PC:llä.
- Kapealla näytöllä klaviatuuri **rajautuu kappaleen käyttämään sävelalueeseen**
  (vähintään 2 oktaavia), jotta koskettimet pysyvät luettavina. Leveällä
  näytöllä näkyvät kaikki 88.
- Puhelin toistaa äänen itse (tai ORG/MID pois = mykistetty), joten PC:tä ei
  tarvita pianon viereen – se voi olla toisessa huoneessa palvelimena.
- Jos puhelin ei yhdistä, salli portti **8020** Windows Defenderin
  palomuurissa yksityisille verkoille.
- PianoCapturella ei ole PIN-porttia (toisin kuin TabToolin kaukosäätimessä):
  käytä sitä vain luotetussa kotiverkossa.

## Transkriptio

Basic Pitch, mutta **pianon parametreilla** (TabToolin kitara-asetukset eivät
kelpaa):

| Parametri | TabTool (kitara) | PianoCapture |
|---|---|---|
| `minimum_frequency` | 80 Hz | **27,5 Hz** (A0) |
| `maximum_frequency` | 1200 Hz | **4186 Hz** (C8) |
| `melodia_trick` | True | **False** (soinnut ja molemmat kädet säilyvät) |
| `minimum_note_length` | 58 ms | 80 ms |

Nuotit tallennetaan JSONiin ja lisäksi `notes.mid` (tarkistus MuseScorella).

## Mitatut esimerkit

**Diablo – *The Well of Grief*** (<https://www.youtube.com/watch?v=StJwVS0IyO8>):
piano alkaa 11 s, muut soittimet 26 s.

- Ehdotus: **11,0 s → 26,0 s**, varmuus **97 %**.
- Kierto: **3,84 s × 3,9** (varmuus 0,94) – eli 2 tahdin kuvio ~123 BPM:ssä.
- Transkriptio 15 s pätkästä: **85 nuottia**, sävelalue MIDI 31–81.
  **Paikallinen versio on siivottu 58 nuottiin** (vasemman käden haamut pois,
  pitch < 60), ja myös promosample on tästä siivotusta versiosta.
- 74 % nuottien aloituksista osui 60 ms sisään havaittuun onsetiin – suuntaa
  antava laadunmitta, ei todiste oikeellisuudesta. **Korvalla tarkistus on
  ainoa hyväksyntä.**

**The Gathering – *Black Light District*** (<https://www.youtube.com/watch?v=FpGGVkt1M3M>):
yhtenäinen, ei-toistuva piano-intro 0 – 2:09.

- Ehdotus: **0,8 s → 128,3 s** (2:08,3), varmuus **100 %**.
- Kierto: **ei kiertoa** (onset-autokorrelaation huippu 0,06 < 0,15) –
  KIERTO on pois päältä ja koko 2:08 näytetään sellaisenaan.
- Transkriptio 127,5 s pätkästä: **178 nuottia**.

## Promosamplet

Repon `samples/`-kansiossa on kaksi PianoCapturen ohjerenderiä:

- `samples/diablo-the-well-of-grief-guide.wav` – 15 s, vain oikea käsi
  (siivottu haamunuoteista)
- `samples/the-gathering-black-light-district-guide-30s.wav` – 30 s ote
  2:07-introsta (koko kappale ~16 min); molemmat kädet. Koko intro säilyy
  paikallisesti videota varten, ei repossa.

Ne ovat **synteettisiä pianoesityksiä automaattisesti transkriboiduista
nuoteista**, eivät alkuperäisiä äänitteitä. Kappaleet ja kaikki niihin
kuuluvat oikeudet kuuluvat tekijöilleen ja julkaisijoilleen; samplet ovat
mukana bändien promoamiseksi ja Pianon toiminnan esittelemiseksi, ei
virallisina julkaisuina. Tarkempi maininta: `THIRD_PARTY_NOTICES.md` ja
`samples/README.md`. Oikeudenhaltijan pyynnöstä tiedostot poistetaan.

## Data ja tiedostot

```
data_piano/
  sources/<hash>.wav        # ladattu ja normalisoitu mono 44.1 kHz
  sources/<hash>.json       # url, title, artist, duration
  pieces/<id>/piece.json    # ikkuna + nuotit + kierto
  pieces/<id>/audio.wav     # pätkän ääni
  pieces/<id>/audio.mp3     # ladattava tausta (koodataan ensimmäisellä latauksella)
  pieces/<id>/guide.wav     # transkriptio audiona (renderöidään tarvittaessa)
  pieces/<id>/guide.mp3     # ohjeen MP3-lataus
  pieces/<id>/notes.mid     # MIDI-tarkistus
  tmp/                      # analyysin väliaikainen otos
```

Koodi:

```
piano/
  main.py         # FastAPI-reitit + staattinen sivu
  pipeline.py     # analyze_source / process_window
  analyze.py      # intron ja bändin sisääntulon heuristiikka
  transcribe.py   # Basic Pitch, pianon parametrit
  audio.py        # yt-dlp/ffmpeg (lainaa app.pipeline.audio_source)
  store.py        # pätkien tallennus
  jobs.py         # kevyt taustatyörekisteri
  static/         # UI (canvas, ei riippuvuuksia)
```

## Testit

```bat
.venv\Scripts\python.exe -m pytest tests\test_piano.py -q
```

Testit käyttävät synteettistä audiota ja monkeypatchattua transkriptiota:
ei verkkoa, ei TensorFlow'ta, ei mallilatauksia. 16 testiä kattaa mm.
nimeämisen ja poiston (`PATCH`/`DELETE`) sekä UI-sopimuksen.

## Tunnetut rajat (v0.2)

- Kiertoehdotus olettaa, että kuvio alkaa pätkän alusta ja että sen rytmi
  toistuu samana. Jos kuvio alkaa vasta sekunnin päästä tai rytmi vaihtelee,
  ehdotus osuu väärään kohtaan → aseta pituus itse (÷2/×2 tai numero).
- Ei pedaalin tunnistusta; pitkät nuotit ≈ pedaali.
- Ei kvantisointia tahtiviivoille (tarkoituksella: soitin on piano, ei tabi).
- Käsijako on MIDI-raja (oletus C4), ei oikea käden tunnistus.
- Basic Pitch tuottaa joskus ylimääräisiä harmonisia; onset/frame-kynnyksiä
  voi säätää `piano/transcribe.py`:ssä. Tarkoitus on antaa **suunta ja
  esimerkki**, ei virheetön transkriptio.
- Analyysi olettaa, että bändin sisääntulo kuuluu äänenvoimakkuuden ja
  perkussiivisuuden hyppynä. Jos intro vaihtuu suoraan soolosoittimeen ilman
  dynamiikkamuutosta, ehdotus menee pieleen → käytä käsin asetettua ikkunaa.

## Seuraavaksi (ehdotus)

1. Kierron automaattinen aloituskohta (nyt oletus: pätkän alku).
2. Pedaalin ja käsien parantaminen (splitin automaatti voice leading -logiikalla).
3. A/B-loop dragauksella ja "toista tämä tahti" -harjoittelu.
4. Tahdeiksi kvantisointi ja MusicXML, jos joskus haluaa nuotit MuseScoreen.
5. Taso 2 analyysiin: Demucs 6s vain alusta, jos heuristiikka ei riitä.
