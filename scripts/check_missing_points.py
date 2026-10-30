# Usage: python scripts/check_missing_points.py LINGUAMETA_DIR GLOTTOLOG_4_8 GLOTTOLOG_5_0 GLOTTOLOG_5_3 OUT.csv
"""Why do ~1,000 LinguaMeta languages have no coordinates?

Compares LinguaMeta's points with Glottolog v4.8, v5.0 and v5.3, and checks
whether each Glottolog point falls in a country LinguaMeta says the language
is spoken in (nearest-populated-place country via reverse_geocoder).
"""
import csv
import json
import sys
from collections import Counter
from pathlib import Path

import reverse_geocoder as rg

LM = Path(sys.argv[1])  # .../url-nlp/linguameta
GLOTTO = {v: Path(p) for v, p in zip(["4.8", "5.0", "5.3"], sys.argv[2:5])}


def coords(path):
    out = {}
    for r in csv.DictReader(open(path / "cldf" / "languages.csv", encoding="utf-8")):
        if r["Latitude"]:
            out[r["ID"]] = (round(float(r["Latitude"]), 4), round(float(r["Longitude"]), 4))
    return out


glotto = {v: coords(p) for v, p in GLOTTO.items()}
names = {r["ID"]: r["Name"] for r in csv.DictReader(open(GLOTTO["5.3"] / "cldf" / "languages.csv"))}

rows = []
for f in sorted((LM / "data").glob("*.json")):
    d = json.loads(f.read_text())
    if (d.get("language_scope") or {}).get("scope") != "LANGUAGE":
        continue
    lsl = d.get("language_script_locale", [])
    locales = {e["locale"]["iso_3166_code"].upper() for e in lsl if "locale" in e}
    locales = {l for l in locales if l.isalpha()}  # drop UN M49 regions like 419
    pts = [(e["geolocation"]["latitude"], e["geolocation"]["longitude"], e["geolocation"]["source"])
           for e in lsl if "geolocation" in e]
    gc = d.get("glottocode")
    rows.append(dict(code=d["bcp_47_code"], gc=gc, locales=locales, pts=pts,
                     g={v: glotto[v].get(gc) for v in glotto}))

need = [r["g"]["5.3"] for r in rows if r["g"]["5.3"]]
cc = iter(x["cc"] for x in rg.search(need, mode=1, verbose=False))
for r in rows:
    r["cc"] = next(cc) if r["g"]["5.3"] else None

with_pt = [r for r in rows if any(s == "GLOTTOLOG" for *_, s in r["pts"]) and r["g"]["5.3"] and r["locales"]]
missing = [r for r in rows if not r["pts"] and r["g"]["5.3"]]
missing_loc = [r for r in missing if r["locales"]]


def inside(r):
    return r["cc"] in r["locales"]


print(f"LinguaMeta languages: {len(rows)}; no point: {sum(not r['pts'] for r in rows)}; "
      f"of those, Glottolog 5.3 has one: {len(missing)}")
print()
print("Baseline: LinguaMeta kept a Glottolog point")
print(f"  {len(with_pt)} languages; Glottolog 5.3 point inside a listed country: "
      f"{sum(map(inside, with_pt)) / len(with_pt):.0%}")
same = Counter()
for r in with_pt:
    lm = {(round(a, 2), round(b, 2)) for a, b, s in r["pts"] if s == "GLOTTOLOG"}
    for v in GLOTTO:
        g = r["g"][v]
        same[v] += bool(g) and (round(g[0], 2), round(g[1], 2)) in lm
print("  LinguaMeta's point identical to Glottolog " +
      ", ".join(f"{v}: {same[v] / len(with_pt):.0%}" for v in GLOTTO))
print()
print("Languages with no LinguaMeta point")
print(f"  {len(missing_loc)} with countries listed; Glottolog 5.3 point inside one: "
      f"{sum(map(inside, missing_loc)) / len(missing_loc):.0%}")
had = Counter(v for r in missing for v in GLOTTO if r["g"][v])
print("  had a Glottolog point in " + ", ".join(f"v{v}: {had[v]}" for v in GLOTTO))
moved = sum(1 for r in missing if r["g"]["4.8"] and r["g"]["4.8"] != r["g"]["5.3"])
print(f"  point moved between v4.8 and v5.3: {moved}")

out = Path(sys.argv[5])
with open(out, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["bcp47", "glottocode", "name", "lat", "lon", "geocoded_country", "linguameta_countries",
                "inside", "in_glottolog_4_8"])
    for r in missing:
        w.writerow([r["code"], r["gc"], names.get(r["gc"], ""), *r["g"]["5.3"], r["cc"],
                    " ".join(sorted(r["locales"])), inside(r), bool(r["g"]["4.8"])])
print(f"\nwrote {out}")
