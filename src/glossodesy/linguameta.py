"""LinguaMeta: the source of language identity — codes, names, speaker numbers,
endangerment and coordinates.

Coordinates are per locale (a language spoken in several countries can have a
point in each), and were checked against the locales a language is actually
spoken in, which fixes Glottolog points that fall outside the right country.
"""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Point:
    lat: float
    lon: float
    locale: str  # ISO 3166 code (or UN M49 region such as 419)
    source: str  # GLOTTOLOG or GOOGLE_RESEARCH (or GLOTTOLOG_FALLBACK, added by us)
    speakers: int | None = None  # in that locale


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
    locales: tuple[str, ...] = ()  # every country LinguaMeta lists, with or without a point
    aliases: tuple[str, ...] = ()  # other English names (Cantonese for Yue Chinese)


def english_aliases(detail: dict, canonical: str) -> tuple[str, ...]:
    """Other English names LinguaMeta records (from ISO 639, CLDR, Wikidata…),
    without code-like entries such as "Nld", "Zh-Yue" or "Bhs"."""
    out, seen = [], {canonical.lower()}
    for n in detail.get("name_data", []):
        name = (n.get("name") or "").strip()
        if n.get("bcp_47_code") != "en" or len(name) <= 3 or any(ch.isdigit() for ch in name):
            continue
        if re.match(r"^[A-Za-z]{2,3}-", name):  # Zh-Yue, Zh-Min-Nan
            continue
        if name.lower() not in seen:
            seen.add(name.lower())
            out.append(name)
    return tuple(out)


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
            p = Point(geo["latitude"], geo["longitude"], e["locale"]["iso_3166_code"], geo.get("source", ""),
                      (e.get("speaker_data") or {}).get("number_of_speakers"))
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
            locales=tuple(sorted({e["locale"]["iso_3166_code"] for e in detail.get("language_script_locale", [])
                                  if "locale" in e})),
            aliases=english_aliases(detail, row["english_name"]),
        )
    return out
