# MacroVisie v10.1.0

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

PMI, OIS per 3/6/12 maanden, Euro High Yield OAS en de 5Y5Y-inflatieswap zijn commercieel gelicentieerde marktdata of hebben geen stabiele, vrij herpubliceerbare API. Vul deze in via **Handmatige data** in de app. Het bestand is `data/manual.csv`.

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


## Handmatige waarden juli 2026

- PMI: manufacturing 52.0, services 51.6, composite 51.9; Reuters-consensus composite 50.3.
- OIS: indicatieve marktpricing per 31 juli 2026: -0.9 stap (3m), -1.6 stap (6m), -2.0 stappen (12m). Negatief betekent renteverhogingen. Dit zijn afgeronde marktinschattingen, geen officiële fixing.
- Euro High Yield OAS: 2.50% op 23 juli 2026, ICE BofA Euro High Yield Index OAS via FRED.
- 5Y5Y-inflatieswap: 2.10% als afgeronde handmatige marktinschatting; controleer deze bij een professionele marktbron voordat je hem als exact dagcijfer gebruikt.
- Consensus kerninflatie: 2.4% voor 2026 uit de ECB Survey of Professional Forecasters van juli 2026.
- ECB-verrassing: 0 bp voor de vergadering van 23 juli 2026, omdat de depositorente conform verwachting ongewijzigd bleef.


## v10.1
Recessiemodel, confidence badges, Valuation LAB, uitgebreide Scenario- en Portfolio LAB, Dalio-correlatiescore, historische regimes vanaf 1929 en herstelde Bundesbank-SDMX-query.
