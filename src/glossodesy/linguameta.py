"""LinguaMeta: the source of language identity — codes, names, speaker numbers,
endangerment and coordinates.

Coordinates are per locale (a language spoken in several countries can have a
point in each), and were checked against the locales a language is actually
spoken in, which fixes Glottolog points that fall outside the right country.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Point:
    lat: float
    lon: float
    locale: str  # ISO 3166 code (or UN M49 region)
    source: str  # GLOTTOLOG or GOOGLE_RESEARCH


@dataclass
class Record:
    code: str  # BCP-47
    name: str
    endonym: str | None
    iso: str | None  # ISO 639-3
    glottocode: str | None
    scope: str  # LANGUAGE or MACROLANGUAGE
    speakers: int | None
    endangerment: str | None
    macrolanguage: str | None = None
    members: tuple[str, ...] = ()
    points: tuple[Point, ...] = field(default=())


def load(linguameta_dir: Path) -> dict[str, Record]:
    table = {
        r["bcp_47_code"]: r
        for r in csv.DictReader(open(linguameta_dir / "linguameta.tsv", encoding="utf-8"), delimiter="\t")
    }
    out = {}
    for code, row in table.items():
        path = linguameta_dir / "data" / f"{code}.json"
        detail = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        scope = (detail.get("language_scope") or {}).get("scope")
        if scope not in ("LANGUAGE", "MACROLANGUAGE"):
            continue
        points = []
        for e in detail.get("language_script_locale", []):
            geo = e.get("geolocation")
            if not geo:
                continue
            p = Point(geo["latitude"], geo["longitude"], e["locale"]["iso_3166_code"], geo.get("source", ""))
            if all((p.lat, p.lon) != (q.lat, q.lon) for q in points):  # repeated once per script
                points.append(p)
        out[code] = Record(
            code=code,
            name=row["english_name"],
            endonym=row["endonym"] or None,
            iso=row["iso_639_3_code"] or None,
            glottocode=row["glottocode"] or None,
            scope=scope,
            speakers=int(row["estimated_number_of_speakers"]) if row["estimated_number_of_speakers"] else None,
            endangerment=row["endangerment_status"] or None,
            macrolanguage=row["macrolanguage_bcp_47_code"] or None,
            members=tuple(detail.get("individual_language_bcp_47_codes", ())),
            points=tuple(points),
        )
    return out
