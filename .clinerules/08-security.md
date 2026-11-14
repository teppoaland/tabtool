# 🔐 Tietoturva – sisäverkko, ei julkista palvelua

## Käyttökonteksti (hyväksytty riski)

Kaikki käyttö on **omaa sisäverkkoa (LAN)**. Palveluita ei julkaista
internetiin, ei tunneloida, ei deployata pilveen eikä pushata julkisille
alustoille. Tässä kontekstissa seuraavat ovat tietoisesti hyväksyttyjä:

- palvelin sitoo `0.0.0.0`:aan ja koko UI, pätkät ja äänet ovat saman verkon
  laitteiden saatavilla
- **ei autentikaatiota, ei PIN-porttia** PianoCapturessa (TabToolin remote voi
  halutessaan vaatia PINin)
- API hyväksyy pyynnöstä YouTube-URLin (yt-dlp) ja paikallisen tiedostopolun
  (äänen tuonti). Tämä on sisäverkossa ok, mutta olisi vakava ongelma
  julkisessa palvelussa (SSRF / mielivaltainen tiedoston luku).

**Älä lisää autentikaatiota, HTTPS:ää, rate-limitejä tai muita kovennuksia
ilman erillistä pyyntöä.** Sisäverkon oletus riittää.

## Silti: pysähdy, kerro ja kysy ennen jatkamista, jos näet

1. **Salaisuuksia gitissä tai pushissa**: API-avaimet, tokenit, salasanat,
   yksityiset avaimet, `.env`-tiedosto, tai data jota ei ole gitignoressa.
2. **Julkinen altistus**: palvelin sidotaan julkiseen osoitteeseen,
   tunnelointi (ngrok, Cloudflare Tunnel), pilvideploy, tai palomuuri avataan
   julkisiin verkkoihin.
3. **Etäkoodin suoritus tai tiedostopääsy**, joka olisi julkisesti
   saavutettavissa: uusi reitti, joka lukee pyynnön polun, ajaa komennon tai
   hakee mielivaltaisen URLin ilman rajausta.
4. **Riippuvuus, joka lataa ja ajaa koodia verkosta** ilman tarkistusta
   (postinstall-skriptit, tuntematon malli- tai binäärilähde).
5. **Yksityisen datan päätyminen julkiseen repoon**: audio, tabit, sanat,
   henkilötiedot, lokit.

Näissä tapauksissa: **pysäytä työ, kerro mikä riski on ja kysy lupaa.**
Muuten: älä jankuta tietoturvasta, vaan keskity ominaisuuksiin.

## Muistilista pushin yhteyteen

- Push vain erillisestä pyynnöstä (`.clinerules/03-versioning.md`).
- Ennen pushia: `git status`, `git ls-files` (ei `data/`, `data_piano/`,
  `.env`), eikä commiteissa salaisuuksia.
- `data/`, `data_piano/`, `.env*` ja audioformaattien pääteet ovat
  gitignoressa – tarkista, ettei uusi polku ohita sitä.
