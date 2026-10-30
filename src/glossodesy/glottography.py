"""Glottography: language areas as polygons, linked to Glottolog.

We use the dataset digitised from Asher & Moseley's *Atlas of the World's
Languages* (2007), which covers the whole world, in its "traditional" version:
areas at the time of contact for the Americas and Australia, and the atlas's
contemporary areas elsewhere. That matches how the site describes geography,
as where a language is traditionally spoken.

The polygons are simplified for the web (to about 2 km) and written in small
files by the first letter of the language code, so a comparison fetches two
of them rather than the whole world.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from shapely import set_precision
from shapely.geometry import MultiPolygon, Polygon, mapping, shape
from shapely.geometry.base import BaseGeometry
from shapely.geometry.polygon import orient

TOLERANCE_DEG = 0.02  # simplification, roughly 2 km
PRECISION_DEG = 0.001  # coordinate grid, roughly 100 m


def load(version_dir: Path) -> dict[str, BaseGeometry]:
    """Glottocode (language level) -> area, from one version's CLDF folder
    (e.g. cldf/traditional)."""
    path = version_dir / "languages.geojson"
    data = json.loads(path.read_text(encoding="utf-8"))
    out = {}
    for f in data["features"]:
        gc = f["properties"].get("cldf:languageReference")
        if gc and f.get("geometry"):
            out[gc] = shape(f["geometry"])
    return out


def simplify(geom: BaseGeometry) -> BaseGeometry:
    g = set_precision(geom.simplify(TOLERANCE_DEG, preserve_topology=True), PRECISION_DEG)
    # d3 (and spherical geometry generally) reads a ring's winding as which side
    # is inside: exterior rings must run clockwise, or the polygon becomes the
    # whole globe minus the area. GeoJSON's RFC 7946 says the opposite, so set it.
    if isinstance(g, Polygon):
        return orient(g, sign=-1.0)
    if isinstance(g, MultiPolygon):
        return MultiPolygon([orient(p, sign=-1.0) for p in g.geoms])
    return g


def shards(areas_by_code: dict[str, BaseGeometry]) -> dict[str, dict[str, dict]]:
    """First letter of the language code -> {code: GeoJSON geometry}."""
    out: dict[str, dict[str, dict]] = defaultdict(dict)
    for code, geom in sorted(areas_by_code.items()):
        g = simplify(geom)
        if not g.is_empty:
            out[code[0]][code] = mapping(g)
    return out
