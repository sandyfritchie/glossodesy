"""Build site/assets/map-extra.json: what the website's map needs beyond the
world-atlas country shapes (site/assets/countries-50m.json).

- iso: ISO 3166 alpha-2 -> numeric, to match LinguaMeta's country codes to
  world-atlas shapes, which are keyed by numeric code.
- disputed: Natural Earth's 1:50m breakaway and disputed areas, drawn hatched
  on the map so it doesn't assign them to either claimant.

Usage:
    pip install pycountry
    git clone --depth 1 --filter=blob:none --sparse https://github.com/nvkelso/natural-earth-vector
    git -C natural-earth-vector sparse-checkout set --no-cone \
        /geojson/ne_50m_admin_0_breakaway_disputed_areas.geojson
    python scripts/make_map_assets.py natural-earth-vector site/assets/map-extra.json

Built from natural-earth-vector commit ca96624 (Natural Earth 5.1.x).
"""
import json
import sys
from pathlib import Path

import pycountry


def rounded(coords, places=3):
    if isinstance(coords[0], (int, float)):
        return [round(c, places) for c in coords]
    return [rounded(c, places) for c in coords]


def main(ne_dir: str, out: str) -> None:
    iso = {c.alpha_2.lower(): c.numeric for c in pycountry.countries}
    src = Path(ne_dir) / "geojson" / "ne_50m_admin_0_breakaway_disputed_areas.geojson"
    features = []
    for f in json.loads(src.read_text(encoding="utf-8"))["features"]:
        p = f["properties"]
        note = p.get("NOTE_BRK") or p.get("BRK_NAME") or ""
        geom = f["geometry"]
        features.append({
            "type": "Feature",
            "properties": {"name": p.get("BRK_NAME") or p.get("NAME"), "note": note},
            "geometry": {"type": geom["type"], "coordinates": rounded(geom["coordinates"])},
        })
    Path(out).write_text(json.dumps(
        {"iso": iso, "disputed": {"type": "FeatureCollection", "features": features}},
        ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"wrote {out}: {len(iso)} country codes, {len(features)} disputed areas")


if __name__ == "__main__":
    main(*sys.argv[1:3])
