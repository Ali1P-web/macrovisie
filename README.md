# MacroVisie v8.0

MacroVisie is een Nederlandstalig, statisch macro-dashboard voor de eurozone. Versie 8.0 voegt een **duidelijk afgescheiden scenario-simulatie** toe en slaat versie 7 bewust over.

## Nieuw in v8.0

- Afzonderlijke pagina **Scenario-simulatie** onder het navigatieblok `Experiment`.
- De simulatie verandert nooit de actuele dashboarddata.
- Vijf instelbare verrassingen: groei/PMI, kerninflatie, ECB, liquiditeit en credit spreads.
- Mechanische richting voor langlopende staatsobligaties, aandelen, euro, goud, Investment Grade en High Yield.
- Vier voorbeeldscenario's en een neutrale reset.
- Automatisch opgebouwde redeneerketen.
- Expliciete waarschuwingen dat uitkomsten educatief zijn en geen prognose of advies.

## Lokaal openen

Open `index.html`. Voor volledige PWA-functionaliteit kun je een lokale webserver gebruiken:

```bash
python -m http.server 8000
```

Open daarna `http://localhost:8000`.

## GitHub Pages

1. Maak een nieuwe GitHub-repository.
2. Upload de **inhoud** van deze map naar de root van de repository.
3. Open `Settings → Pages`.
4. Kies bij Source voor **GitHub Actions**.
5. Open `Actions` en voer `Update data and deploy` één keer handmatig uit.

De workflow werkt daarna dagelijks de databestanden bij en publiceert de website.

## Belangrijk over de simulatie

Het model is bewust eenvoudig en transparant. Het vertaalt macroverrassingen naar richting, niet naar voorspelde rendementen. Tegenstrijdige effecten worden bij elkaar opgeteld. De echte marktreactie hangt altijd af van positionering, waardering en wat al is ingeprijsd.

## Bestanden

- `index.html` — interface en pagina's
- `css/style.css` — vormgeving, inclusief aparte simulatiestijl
- `js/app.js` — dashboard- en simulatielogica
- `data/` — huidige en voorbeelddata
- `scripts/update_data.py` — updater
- `.github/workflows/update-and-deploy.yml` — dagelijkse update en GitHub Pages-deploy
