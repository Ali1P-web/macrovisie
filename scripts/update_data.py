#!/usr/bin/env python3
"""MacroVisie v10.1 updater.

Bronnen:
- ECB Data Portal: beleidsrente, eurozone-curves, M3, Eurosysteembalans.
- Eurostat Statistics API: HICP, kern-HICP, werkloosheid, BBP en lonen.
- Deutsche Bundesbank SDMX API: actuele Duitse federale effecten (Schatz/Bobl/Bund).

PMI, OIS en 5y5y-inflatieswap blijven expliciet handmatig. De Euro HY OAS wordt
dagelijks gecontroleerd via FRED (ICE BofA-reeks BAMLHE00EHYIOAS). De webapp bevat hiervoor een
invulhulp. Bij een bronfout blijft de laatst geldige reeks behouden.
"""
from __future__ import annotations

import csv
import io
import json
import math
import os
import urllib.parse
import urllib.request
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "dashboard.json"
SAMPLE = ROOT / "data" / "sample.json"
MANUAL = ROOT / "data" / "manual.csv"
USER_AGENT = "MacroVisie/10.1 (educational dashboard; GitHub Pages)"

ECB = {
    "depositRate": ("FM", "D.U2.EUR.4F.KR.DFR.LEV"),
    # Eurozone spotcurve, alle ratings/emittenten.
    "yield2y": ("YC", "B.U2.EUR.4F.G_N_C.SV_C_YM.SR_2Y"),
    "yield5y": ("YC", "B.U2.EUR.4F.G_N_C.SV_C_YM.SR_5Y"),
    "yield10y": ("YC", "B.U2.EUR.4F.G_N_C.SV_C_YM.SR_10Y"),
    "yield30y": ("YC", "B.U2.EUR.4F.G_N_C.SV_C_YM.SR_30Y"),
    # AAA-spotcurve (niet uitsluitend Duitsland; alle AAA-eurozone-emittenten).
    "aaaYield2y": ("YC", "B.U2.EUR.4F.G_N_A.SV_C_YM.SR_2Y"),
    "aaaYield5y": ("YC", "B.U2.EUR.4F.G_N_A.SV_C_YM.SR_5Y"),
    "aaaYield10y": ("YC", "B.U2.EUR.4F.G_N_A.SV_C_YM.SR_10Y"),
    "aaaYield30y": ("YC", "B.U2.EUR.4F.G_N_A.SV_C_YM.SR_30Y"),
    # ECB-reeks: Real Euro area 10-year Government Benchmark bond yield.
    "realYield": ("FM", "M.U2.EUR.4F.BB.R_U2_10Y.YLDA"),
    "m3": ("BSI", "M.U2.N.V.M30.X.I.U2.2300.Z01.A"),
    "ecbBalance": ("ILM", "W.U2.C.T000000.Z5.Z01"),
}

# Rendement van het meest recente Duitse federale effect per oorspronkelijke looptijd.
BUNDESBANK = {
    "bund2y": "BBSSY.D.REN.EUR.A610.000000WT0202.A",
    "bund5y": "BBSSY.D.REN.EUR.A620.000000WT0505.A",
    "bund10y": "BBSSY.D.REN.EUR.A630.000000WT1010.A",
    "bund30y": "BBSSY.D.REN.EUR.A640.000000WT3030.A",
}

EUROSTAT = {
    "unemployment": [
        ("une_rt_m", {"freq":"M","s_adj":"SA","age":"Y15-74","sex":"T","unit":"PC_ACT","geo":"EA20"}),
        ("une_rt_m", {"freq":"M","s_adj":"SA","age":"Y15-74","sex":"T","unit":"PC_ACT","geo":"EA19"}),
    ],
    "gdp": [
        ("namq_10_gdp", {"freq":"Q","unit":"CLV_PCH_PRE","s_adj":"SCA","na_item":"B1GQ","geo":"EA20"}),
        ("namq_10_gdp", {"freq":"Q","unit":"CLV_PCH_PRE","s_adj":"SCA","na_item":"B1GQ","geo":"EA19"}),
    ],
    # HICP volgens ECOICOP versie 2. De dimensie heet `coicop18`.
    # `TOTAL` is de totale HICP; `TOT_X_NRG_FOOD` is de gebruikelijke
    # kernmaat exclusief energie, voeding, alcohol en tabak.
    "cpi": [
        ("prc_hicp_minr", {"freq":"M","unit":"RCH_A","coicop18":"TOTAL","geo":"EA21"}),
        ("prc_hicp_minr", {"freq":"M","unit":"RCH_A","coicop18":"TOTAL","geo":"EA20"}),
    ],
    "coreCpi": [
        ("prc_hicp_minr", {"freq":"M","unit":"RCH_A","coicop18":"TOT_X_NRG_FOOD","geo":"EA21"}),
        ("prc_hicp_minr", {"freq":"M","unit":"RCH_A","coicop18":"TOT_X_NRG_FOOD","geo":"EA20"}),
    ],
    "wages": [
        ("lc_lci_r2_q", {"freq":"Q","unit":"PCH_SM","s_adj":"CA","nace_r2":"B-S","lcstruct":"WAG","geo":"EA20"}),
        ("lc_lci_r2_q", {"freq":"Q","unit":"PCH_SM","s_adj":"NSA","nace_r2":"B-S","lcstruct":"WAG","geo":"EA20"}),
    ],
}

LABELS = {
    "aaaYield2y": ("AAA-eurozone spotrate 2 jaar", "%"),
    "aaaYield5y": ("AAA-eurozone spotrate 5 jaar", "%"),
    "aaaYield10y": ("AAA-eurozone spotrate 10 jaar", "%"),
    "aaaYield30y": ("AAA-eurozone spotrate 30 jaar", "%"),
    "bund2y": ("Duitse Schatz 2 jaar", "%"),
    "bund5y": ("Duitse Bobl 5 jaar", "%"),
    "bund10y": ("Duitse Bund 10 jaar", "%"),
    "bund30y": ("Duitse Bund 30 jaar", "%"),
    "marketInflation5y5y": ("5Y5Y-inflatieswap", "%"),
    "oisCuts3m": ("OIS 3 maanden", "stappen"),
    "oisCuts6m": ("OIS 6 maanden", "stappen"),
    "oisCuts12m": ("OIS 12 maanden", "stappen"),
    "creditSpread": ("Euro High Yield OAS", "%"),
    "inflationProxy": ("Afgeleide inflatiecompensatie", "%"),
}


def get(url: str, accept: str = "*/*") -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": accept})
    with urllib.request.urlopen(req, timeout=60) as response:
        return response.read()



def fetch_fred_hy_oas() -> list[dict]:
    """ICE BofA Euro High Yield OAS via de openbare FRED CSV-export."""
    raw = get("https://fred.stlouisfed.org/graph/fredgraph.csv?id=BAMLHE00EHYIOAS", "text/csv").decode("utf-8-sig")
    rows = csv.DictReader(io.StringIO(raw))
    values = []
    for row in rows:
        obs = row.get("BAMLHE00EHYIOAS")
        if not obs or obs == ".":
            continue
        try:
            values.append({"date": monthify((row.get("observation_date") or row.get("DATE"))), "value": float(obs)})
        except (ValueError, KeyError):
            continue
    # Dagdata worden voor het compacte dashboard per maand teruggebracht tot de laatste close.
    monthly = {v["date"]: v["value"] for v in values}
    return [{"date": d, "value": monthly[d]} for d in sorted(monthly)]

def monthify(period: str) -> str:
    p = str(period).strip()
    if "Q" in p and len(p) >= 6:
        year, quarter = p.replace("-", "").split("Q")[:2]
        return f"{int(year):04d}-{1 + (int(quarter)-1)*3:02d}-01"
    if len(p) >= 10 and p[4] == "-":
        return p[:7] + "-01"
    if len(p) == 7 and p[4] == "-":
        return p + "-01"
    if len(p) == 4 and p.isdigit():
        return p + "-01-01"
    return p[:10]


def monthly_last(items: list[dict]) -> list[dict]:
    result: dict[str, float] = {}
    for item in sorted(items, key=lambda x: x["date"]):
        result[item["date"][:7] + "-01"] = item["value"]
    return [{"date": d, "value": v} for d, v in sorted(result.items())]


def fetch_ecb(flow: str, key: str) -> list[dict]:
    query = urllib.parse.urlencode({"format":"csvdata", "startPeriod":"2000-01-01", "detail":"dataonly"})
    url = f"https://data-api.ecb.europa.eu/service/data/{flow}/{key}?{query}"
    rows = csv.DictReader(io.StringIO(get(url).decode("utf-8-sig")))
    output = []
    for row in rows:
        period = row.get("TIME_PERIOD") or row.get("TIME PERIOD") or row.get("time_period")
        value = row.get("OBS_VALUE") or row.get("OBS VALUE") or row.get("obs_value")
        if not period or value in (None, "", "NaN"):
            continue
        try:
            number = float(value)
            if math.isfinite(number):
                output.append({"date": str(period)[:10], "value": round(number, 6)})
        except ValueError:
            continue
    return monthly_last(output)


def fetch_bundesbank(series_key: str) -> list[dict]:
    params = urllib.parse.urlencode({"format":"sdmx_csv", "startPeriod":"2000-01-01", "detail":"dataonly"})
    url = f"https://api.statistiken.bundesbank.de/rest/data/BBSSY/{series_key.split('.', 1)[1]}?{params}"
    text = get(url, "text/csv").decode("utf-8-sig")
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;")
    except csv.Error:
        dialect = csv.excel
    rows = csv.DictReader(io.StringIO(text), dialect=dialect)
    output = []
    for row in rows:
        period = row.get("TIME_PERIOD") or row.get("TIME PERIOD")
        value = row.get("OBS_VALUE") or row.get("OBS VALUE")
        if not period or value in (None, "", "NaN"):
            continue
        try:
            output.append({"date": period[:10], "value": round(float(value), 6)})
        except ValueError:
            pass
    return monthly_last(output)


def jsonstat_values(obj: dict) -> list[dict]:
    ids = obj.get("id", [])
    sizes = obj.get("size", [])
    if "time" not in ids or not sizes:
        return []
    time_axis = ids.index("time")
    index = obj["dimension"]["time"]["category"]["index"]
    time_codes = index if isinstance(index, list) else [k for k, _ in sorted(index.items(), key=lambda kv: kv[1])]
    values = obj.get("value", {})
    strides = []
    for axis in range(len(sizes)):
        strides.append(math.prod(sizes[axis + 1:]) if axis + 1 < len(sizes) else 1)
    output = []
    for time_pos, period in enumerate(time_codes):
        flat_index = time_pos * strides[time_axis]  # overige gefilterde dimensies: positie nul
        value = values.get(str(flat_index)) if isinstance(values, dict) else (values[flat_index] if flat_index < len(values) else None)
        if value is None:
            continue
        try:
            output.append({"date": monthify(period), "value": round(float(value), 6)})
        except (TypeError, ValueError):
            pass
    return output


def validate_eurostat_response(obj: dict, filters: dict) -> None:
    """Voorkom dat Eurostat een onbekend filter stilzwijgend negeert.

    De oude parser nam aan dat iedere niet-tijddimensie één categorie bevatte.
    Als bijvoorbeeld `coicop` niet werd herkend, bevatte het antwoord honderden
    categorieën en werd per ongeluk de eerste categorie als CPI getoond.
    """
    ids = obj.get("id", [])
    sizes = obj.get("size", [])
    if not ids or len(ids) != len(sizes):
        raise RuntimeError("ongeldige JSON-stat structuur")

    for dimension, size in zip(ids, sizes):
        if dimension != "time" and int(size) != 1:
            raise RuntimeError(
                f"filter niet eenduidig toegepast: dimensie {dimension} bevat {size} categorieën"
            )

    dimensions = obj.get("dimension", {})
    for key, requested in filters.items():
        # freq is soms een vaste datasetdimensie; alle andere filters moeten
        # als dimensie terugkomen wanneer Eurostat ze heeft geaccepteerd.
        if key not in dimensions:
            raise RuntimeError(f"Eurostat negeerde onbekend filter: {key}")
        category_index = dimensions[key].get("category", {}).get("index", {})
        categories = category_index if isinstance(category_index, list) else list(category_index.keys())
        if categories and str(requested) not in {str(value) for value in categories}:
            raise RuntimeError(f"filter {key}={requested} niet teruggevonden in antwoord")


def fetch_eurostat(dataset: str, filters: dict) -> list[dict]:
    params = {"lang":"EN", "sinceTimePeriod":"2000"}
    params.update(filters)
    url = f"https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/{dataset}?{urllib.parse.urlencode(params)}"
    obj = json.loads(get(url, "application/json").decode("utf-8"))
    if obj.get("error"):
        raise RuntimeError(str(obj["error"]))
    validate_eurostat_response(obj, filters)
    return jsonstat_values(obj)


def merge_values(existing: list[dict], incoming: list[dict]) -> list[dict]:
    """Leg nieuwe observaties over bestaande historie heen."""
    merged = {item["date"]: item["value"] for item in existing}
    merged.update({item["date"]: item["value"] for item in incoming})
    return [{"date": d, "value": v} for d, v in sorted(merged.items())]


def load_base() -> dict:
    for path in (OUT, SAMPLE):
        try:
            if path.exists():
                return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"meta": {}, "series": {}}


def ensure_meta(data: dict, key: str) -> dict:
    series = data.setdefault("series", {}).setdefault(key, {})
    if key in LABELS:
        series.setdefault("label", LABELS[key][0])
        series.setdefault("unit", LABELS[key][1])
    return series


def set_values(data: dict, key: str, values: list[dict], source: str, source_name: str = "") -> None:
    if not values:
        return
    series = ensure_meta(data, key)
    series["values"] = sorted(values, key=lambda x: x["date"])
    series["source"] = source
    if source_name:
        series["source_name"] = source_name


def mark_unavailable(data: dict, key: str, reason: str) -> None:
    """Verwijder onbetrouwbare waarden zodat de site geen oud cijfer als LIVE toont."""
    series = ensure_meta(data, key)
    series["values"] = []
    series["source"] = "niet beschikbaar"
    series["source_name"] = reason
    series["freshness"] = "fout"
    series["data_quality"] = False


def merge_manual(data: dict) -> list[str]:
    if not MANUAL.exists():
        return []
    rows = list(csv.DictReader(MANUAL.open(encoding="utf-8-sig")))
    keys = [
        "pmiManufacturing", "pmiServices", "pmiComposite", "oisCuts3m", "oisCuts6m", "oisCuts12m",
        "marketInflation5y5y", "consensusPmi",
        "consensusCoreCpi", "consensusEcbBp"
    ]
    updated = []
    for key in keys:
        additions = []
        for row in rows:
            raw = row.get(key)
            if raw not in (None, ""):
                try:
                    additions.append({"date": monthify(row["date"]), "value": float(raw.replace(",", "."))})
                except (ValueError, AttributeError):
                    pass
        if additions:
            old = {v["date"]: v["value"] for v in data.get("series", {}).get(key, {}).get("values", [])}
            old.update({v["date"]: v["value"] for v in additions})
            set_values(data, key, [{"date": d, "value": v} for d, v in old.items()], "handmatig", "data/manual.csv")
            updated.append(key)
    return updated


def align_subtract(data: dict, a: str, b: str) -> list[dict]:
    left = {v["date"]: v["value"] for v in data.get("series", {}).get(a, {}).get("values", [])}
    right = {v["date"]: v["value"] for v in data.get("series", {}).get(b, {}).get("values", [])}
    return [{"date": d, "value": round(left[d] - right[d], 6)} for d in sorted(set(left) & set(right))]


def calculate(data: dict) -> None:
    set_values(data, "yieldCurve", align_subtract(data, "yield10y", "yield2y"), "berekend", "10Y min 2Y")
    set_values(data, "aaaYieldCurve", align_subtract(data, "aaaYield10y", "aaaYield2y"), "berekend", "AAA 10Y min AAA 2Y")
    # Dit is inflatiecompensatie/proxy; geen zuivere verhandelbare break-even.
    proxy = align_subtract(data, "yield10y", "realYield")
    set_values(data, "inflationProxy", proxy, "berekend", "ECB nominale benchmark min ECB reële benchmark")
    # Backwards compatibility, maar label en bron worden expliciet gemaakt.
    set_values(data, "breakeven", proxy, "proxy", "Niet-verhandelbare afleiding")
    if "breakeven" in data.get("series", {}):
        data["series"]["breakeven"]["label"] = "Inflatiecompensatie (proxy)"


def validate(data: dict) -> list[str]:
    warnings = []
    today = date.today()
    for key, series in data.get("series", {}).items():
        values = series.get("values", [])
        if not values:
            continue
        if any(not math.isfinite(float(v["value"])) for v in values):
            warnings.append(f"{key}: niet-eindige waarde")
        try:
            age_months = (today.year - int(values[-1]["date"][:4])) * 12 + today.month - int(values[-1]["date"][5:7])
            series["age_months"] = age_months
            series["freshness"] = "actueel" if age_months <= 2 else "verouderd"
        except Exception:
            pass
    return warnings


def main() -> int:
    data = load_base()
    success, errors = [], []

    for key, (flow, series_key) in ECB.items():
        try:
            values = fetch_ecb(flow, series_key)
            if not values:
                raise RuntimeError("lege reeks")
            # ILM publiceert de balans soms in miljoenen euro. Het dashboard toont miljarden.
            if key == "ecbBalance" and values[-1]["value"] > 100_000:
                values = [{"date": v["date"], "value": round(v["value"] / 1000, 3)} for v in values]
                ensure_meta(data, key)["unit"] = "€ mld"
            set_values(data, key, values, "live", "ECB Data Portal")
            success.append(key)
        except Exception as exc:
            errors.append(f"ECB {key}: {exc}")

    for key, series_key in BUNDESBANK.items():
        try:
            values = fetch_bundesbank(series_key)
            if not values:
                raise RuntimeError("lege reeks")
            set_values(data, key, values, "live", "Deutsche Bundesbank")
            success.append(key)
        except Exception as exc:
            errors.append(f"Bundesbank {key}: {exc}")

    for key, alternatives in EUROSTAT.items():
        last_error: Exception | str = "geen query"
        for dataset, filters in alternatives:
            try:
                values = fetch_eurostat(dataset, filters)
                if not values:
                    raise RuntimeError("lege reeks")
                # EA21-reeksen kunnen pas in 2026 beginnen. Bewaar daarom de
                # oudere, reeds gevalideerde historie en vervang alleen overlap.
                if key in {"cpi", "coreCpi"}:
                    latest_value = values[-1]["value"]
                    latest_year = int(values[-1]["date"][:4])
                    if not (-5.0 <= latest_value <= 15.0):
                        raise RuntimeError(f"onplausibele laatste inflatiewaarde: {latest_value}")
                    if latest_year < 2026:
                        raise RuntimeError("HICP-reeks bevat geen observatie vanaf 2026")
                set_values(data, key, values, "live", f"Eurostat · {dataset} · {filters.get('geo')} · {filters.get('coicop18','')}")
                ensure_meta(data, key)["data_quality"] = True
                success.append(key)
                break
            except Exception as exc:
                last_error = exc
        else:
            errors.append(f"Eurostat {key}: {last_error}")
            if key in {"cpi", "coreCpi"}:
                mark_unavailable(data, key, f"Eurostat-update mislukt: {last_error}")

    success.extend(merge_manual(data))
    try:
        values = fetch_fred_hy_oas()
        if not values:
            raise RuntimeError("lege reeks")
        set_values(data, "creditSpread", values, "live", "FRED · ICE BofA Euro High Yield OAS · BAMLHE00EHYIOAS")
        ensure_meta(data, "creditSpread")["data_quality"] = True
        success.append("creditSpread")
    except Exception as exc:
        errors.append(f"FRED creditSpread: {exc}")
    calculate(data)
    errors.extend(validate(data))
    data.setdefault("meta", {}).update({
        "name": "MacroVisie",
        "version": "10.1.0",
        "updated_at": date.today().isoformat(),
        "mode": "web",
        "successful_updates": sorted(set(success)),
        "warnings": errors,
        "methodology": "v10.1: geverifieerde HICP, OIS 3/6/12 maanden, Euro High Yield OAS en Nederlandse notatie",
    })
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"MacroVisie v10.1: {len(set(success))} reeksen bijgewerkt; {len(errors)} waarschuwingen")
    for error in errors:
        print("-", error)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
