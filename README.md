# MacroVisie v9.2.0

Nederlandstalig macro-dashboard voor de eurozone, gebouwd als statische GitHub Pages-app.

## Nieuw in v9

- Broncontrole en verouderingslabel per reeks.
- HICP-query aangepast aan `prc_hicp_minr`.
- ECB 10-jaars reële benchmarkyield gecorrigeerd.
- AAA-eurozone spotcurve (ECB) toegevoegd.
- Duitse Schatz/Bobl/Bund 2Y, 5Y, 10Y en 30Y (Deutsche Bundesbank) toegevoegd.
- Inflatieverwachting opgesplitst in:
  - 5Y5Y-inflatieswap: marktmaat, handmatig zolang geen vrij herpubliceerbare stabiele API beschikbaar is;
  - afgeleide inflatiecompensatie: expliciet als proxy gelabeld.
- Transparante Macro Pulse: elke score is open te klappen.
- Nederlandse getalnotatie en correcte ECB-balansweergave in miljarden euro.
- Apart Portefeuille-LAB met alle besproken activaklassen.
- Scenario-LAB toont de huidige consensus-baselines.
- Pagina **Handmatige data** maakt een complete CSV-regel en linkt direct naar GitHub.

## Automatische bronnen

- ECB Data Portal
- Eurostat Statistics API
- Deutsche Bundesbank SDMX API

## Bewust handmatig

PMI, OIS, credit spreads en de 5Y5Y-inflatieswap zijn commercieel gelicentieerde marktdata of hebben geen stabiele, vrij herpubliceerbare API. Vul deze in via **Handmatige data** in de app. Het bestand is `data/manual.csv`.

## Publiceren

Vervang de bestanden in je repository door de inhoud van deze map. Controleer daarna:

1. **Settings → Pages → GitHub Actions**
2. **Actions → Update data and deploy MacroVisie → Run workflow**
3. Open `data/dashboard.json` en controleer `successful_updates` en `warnings`.

## Belangrijk onderscheid

- `AAA-eurozonecurve`: ECB-modelcurve van alle AAA-emittenten; niet uitsluitend Duitsland.
- `Duitse Bunds`: actuele federale effecten, rechtstreeks van de Bundesbank.
- `5Y5Y-inflatieswap`: marktgebaseerde inflatiecompensatie, inclusief risicopremie.
- `inflationProxy`: nominale benchmark minus reële benchmark; alleen richtinggevend.
