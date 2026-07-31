#!/usr/bin/env python3
"""Werk MacroVisie-data bij via officiële ECB- en Eurostat-API's.

Geen externe Python-pakketten nodig. Bij een mislukte bron blijft de bestaande
reeks in data/dashboard.json staan. Handmatige reeksen worden uit data/manual.csv
gelezen. Het script is bedoeld voor GitHub Actions, maar kan ook lokaal draaien.
"""
from __future__ import annotations
import csv, io, json, os, sys, urllib.parse, urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "dashboard.json"
SAMPLE = ROOT / "data" / "sample.json"
MANUAL = ROOT / "data" / "manual.csv"
USER_AGENT = "MacroVisie/0.3 (+GitHub Pages educational dashboard)"

# ECB series keys. De updater bewaart de bestaande reeks als een sleutel tijdelijk
# niet beschikbaar is of door de ECB wordt gewijzigd.
ECB = {
    "depositRate": ("FM", "D.U2.EUR.4F.KR.DFR.LEV"),
    "yield2y": ("YC", "B.U2.EUR.4F.G_N_C.SV_C_YM.SR_2Y"),
    "yield5y": ("YC", "B.U2.EUR.4F.G_N_C.SV_C_YM.SR_5Y"),
    "yield10y": ("YC", "B.U2.EUR.4F.G_N_C.SV_C_YM.SR_10Y"),
    "yield30y": ("YC", "B.U2.EUR.4F.G_N_C.SV_C_YM.SR_30Y"),
    # Reële benchmarkyield; wanneer de ECB-reeks wijzigt blijft cache actief.
    "realYield": ("IRS", "M.U2.EUR.L.RE.BB.I10Y"),
    # M3 annual growth rate.
    "m3": ("BSI", "M.U2.N.V.M30.X.I.U2.2300.Z01.A"),
    # Total assets / liabilities Eurosystem; configured as best-effort series.
    "ecbBalance": ("ILM", "W.U2.C.T000000.Z5.Z01"),
}

# Eurostat query-definities. De Statistics API accepteert dimensies als URL-filters.
EUROSTAT = {
    "unemployment": [
        ("une_rt_m", {"freq":"M","s_adj":"SA","age":"Y15-74","sex":"T","unit":"PC_ACT","geo":"EA20"}),
        ("une_rt_m", {"freq":"M","s_adj":"SA","age":"Y15-74","sex":"T","unit":"PC_ACT","geo":"EA19"}),
    ],
    "gdp": [
        ("namq_10_gdp", {"freq":"Q","unit":"CLV_PCH_PRE","s_adj":"SCA","na_item":"B1GQ","geo":"EA20"}),
        ("namq_10_gdp", {"freq":"Q","unit":"CLV_PCH_PRE","s_adj":"SCA","na_item":"B1GQ","geo":"EA19"}),
    ],
    # HICP annual rate. Multiple dataset/code variants are tried to survive classification changes.
    "cpi": [
        ("prc_hicp_manr", {"freq":"M","unit":"RCH_A","coicop":"CP00","geo":"EA20"}),
        ("prc_hicp_manr", {"freq":"M","unit":"RCH_A","coicop":"CP00","geo":"EA19"}),
        ("prc_hicp_minr", {"freq":"M","unit":"RCH_A","coicop":"CP00","geo":"EA20"}),
    ],
    "coreCpi": [
        ("prc_hicp_manr", {"freq":"M","unit":"RCH_A","coicop":"TOT_X_NRG_FOOD","geo":"EA20"}),
        ("prc_hicp_manr", {"freq":"M","unit":"RCH_A","coicop":"CP00_X_0451_0452","geo":"EA20"}),
    ],
    # Labour cost index / wages: tried as a quarterly wage-cost growth series.
    "wages": [
        ("lc_lci_r2_q", {"freq":"Q","unit":"PCH_SM","s_adj":"CA","nace_r2":"B-S","lcstruct":"WAG","geo":"EA20"}),
        ("lc_lci_r2_q", {"freq":"Q","unit":"PCH_SM","s_adj":"CA","nace_r2":"B-S","lcstruct":"D1","geo":"EA20"}),
    ],
}

def get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept":"*/*"})
    with urllib.request.urlopen(req, timeout=45) as r:
        return r.read()

def monthify(period: str) -> str:
    p = period.strip()
    if "Q" in p:
        y, q = p.split("Q")
        month = 1 + (int(q)-1)*3
        return f"{int(y):04d}-{month:02d}-01"
    if len(p) == 7 and p[4] == "-": return p + "-01"
    if len(p) == 4 and p.isdigit(): return p + "-01-01"
    try: return datetime.fromisoformat(p.replace("Z","+00:00")).date().isoformat()
    except Exception: return p[:10]

def fetch_ecb(flow: str, key: str) -> list[dict]:
    params = urllib.parse.urlencode({"format":"csvdata","startPeriod":"2000-01-01","detail":"dataonly"})
    url = f"https://data-api.ecb.europa.eu/service/data/{flow}/{key}?{params}"
    text = get(url).decode("utf-8-sig")
    rows = list(csv.DictReader(io.StringIO(text)))
    out = []
    for row in rows:
        t = row.get("TIME_PERIOD") or row.get("TIME PERIOD") or row.get("time_period")
        v = row.get("OBS_VALUE") or row.get("OBS VALUE") or row.get("obs_value")
        if not t or v in (None, "", "NaN"): continue
        try: out.append({"date": monthify(t), "value": round(float(v), 4)})
        except ValueError: pass
    # Daily/weekly ECB series are reduced to the last observation per month.
    by_month = {}
    for item in sorted(out, key=lambda x:x["date"]): by_month[item["date"][:7]+"-01"] = item["value"]
    return [{"date":k,"value":v} for k,v in sorted(by_month.items())]

def jsonstat_values(obj: dict) -> list[dict]:
    ids = obj.get("id", [])
    sizes = obj.get("size", [])
    if "time" not in ids: return []
    time_dim = obj["dimension"]["time"]["category"]["index"]
    if isinstance(time_dim, list): time_codes = time_dim
    else: time_codes = [k for k,_ in sorted(time_dim.items(), key=lambda kv:kv[1])]
    values = obj.get("value", [])
    # Queries filter all non-time dimensions to one position, so values map directly to time.
    out=[]
    if isinstance(values, dict):
        for i,t in enumerate(time_codes):
            v=values.get(str(i))
            if v is not None: out.append({"date":monthify(t),"value":round(float(v),4)})
    else:
        for t,v in zip(time_codes,values):
            if v is not None: out.append({"date":monthify(t),"value":round(float(v),4)})
    return out

def fetch_eurostat(dataset: str, filters: dict) -> list[dict]:
    params={"lang":"EN","sinceTimePeriod":"2000"};params.update(filters)
    url=f"https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/{dataset}?{urllib.parse.urlencode(params)}"
    obj=json.loads(get(url).decode("utf-8"))
    if "error" in obj or "warning" in obj: raise RuntimeError(str(obj.get("error") or obj.get("warning")))
    return jsonstat_values(obj)

def load_base() -> dict:
    for p in (OUT,SAMPLE):
        if p.exists():
            try: return json.loads(p.read_text(encoding="utf-8"))
            except Exception: pass
    return {"meta":{},"series":{}}

def set_values(data,key,values,source="live"):
    if values:
        data["series"].setdefault(key,{})["values"] = values
        data["series"][key]["source"] = source

def merge_manual(data):
    if not MANUAL.exists(): return
    rows=list(csv.DictReader(MANUAL.open(encoding="utf-8")))
    for key in ("pmiManufacturing","pmiServices","pmiComposite","oisCuts","creditSpread"):
        vals=[]
        for r in rows:
            if r.get(key) not in (None,""):
                try: vals.append({"date":monthify(r["date"]),"value":float(r[key])})
                except ValueError: pass
        if vals:
            old={v["date"]:v["value"] for v in data["series"].get(key,{}).get("values",[])}
            old.update({v["date"]:v["value"] for v in vals})
            set_values(data,key,[{"date":d,"value":v} for d,v in sorted(old.items())],"handmatig")

def calculate(data):
    def mapvals(key): return {v["date"]:v["value"] for v in data["series"].get(key,{}).get("values",[])}
    y2,y10,real=mapvals("yield2y"),mapvals("yield10y"),mapvals("realYield")
    curve=[{"date":d,"value":round(y10[d]-y2[d],4)} for d in sorted(set(y2)&set(y10))]
    bre=[{"date":d,"value":round(y10[d]-real[d],4)} for d in sorted(set(y10)&set(real))]
    set_values(data,"yieldCurve",curve,"berekend");set_values(data,"breakeven",bre,"berekend")

def main():
    data=load_base();errors=[];success=[]
    for key,(flow,series_key) in ECB.items():
        try:
            vals=fetch_ecb(flow,series_key)
            if not vals: raise RuntimeError("lege reeks")
            set_values(data,key,vals);success.append(key)
        except Exception as e: errors.append(f"ECB {key}: {e}")
    for key,queries in EUROSTAT.items():
        ok=False
        for dataset,filters in queries:
            try:
                vals=fetch_eurostat(dataset,filters)
                if not vals: raise RuntimeError("lege reeks")
                set_values(data,key,vals);success.append(key);ok=True;break
            except Exception as e: last=e
        if not ok: errors.append(f"Eurostat {key}: {last}")
    merge_manual(data);calculate(data)
    data.setdefault("meta",{})
    data["meta"].update({"name":"MacroVisie","version":"0.3.0","updated_at":date.today().isoformat(),"mode":"web","successful_updates":success,"warnings":errors})
    OUT.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
    print(f"Bijgewerkt: {len(success)} reeksen; waarschuwingen: {len(errors)}")
    for e in errors: print("-",e,file=sys.stderr)
    # Do not fail the action when one public source changes; cached data remains visible.
    return 0
if __name__=="__main__": raise SystemExit(main())
