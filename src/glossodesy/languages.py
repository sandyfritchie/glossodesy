"""The language index: LinguaMeta records joined to Glottolog by glottocode."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from .geo import country_of, great_circle_km
from .glottolog import Glottolog
from .linguameta import Point, Record

FALLBACK_SOURCE = "GLOTTOLOG_FALLBACK"


@dataclass
class Language:
    code: str  # BCP-47, the project's primary key
    record: Record
    lineage: tuple[str, ...] | None  # Glottolog root-to-languoid path, if classifiable
    points: tuple[Point, ...] = field(default=())  # every location (LinguaMeta, or our fallback)
    origin: Point | None = None  # the one location that stands for the language

    @property
    def name(self) -> str:
        return self.record.name

    @property
    def glottocode(self) -> str | None:
        return self.record.glottocode

    @property
    def is_macrolanguage(self) -> bool:
        return self.record.scope == "MACROLANGUAGE"


class MacrolanguageError(KeyError):
    pass


class Languages(dict[str, Language]):
    def resolve(self, query: str) -> Language:
        """Find a language by BCP-47, ISO 639-3, glottocode or English name.

        A macrolanguage can't be compared directly (it covers several distinct
        languages), so resolving one raises MacrolanguageError listing them —
        unless the name also matches exactly one individual language, as with
        Swahili (sw) and Swahili (swh).
        """
        q = query.strip()
        ql = q.lower()
        hit = self.get(q) or self.get(ql)
        if hit is None:
            hit = next((l for l in self.values() if l.record.iso == ql), None)
        if hit is None:
            hit = next((l for l in self.values() if l.glottocode == ql), None)
        if hit is None:
            named = [l for l in self.values() if l.name.lower() == ql]
            individual = [l for l in named if not l.is_macrolanguage]
            if len(individual) == 1:
                hit = individual[0]
            elif len(individual) > 1:
                raise KeyError(f"{query!r} is ambiguous: {', '.join(l.code for l in individual)}")
            elif named:
                hit = named[0]
        if hit is None:
            raise KeyError(f"No language matches {query!r}")
        if hit.is_macrolanguage:
            members = [f"{self[m].name} ({m})" for m in hit.record.members if m in self]
            shown = ", ".join(members[:8]) + (f" and {len(members) - 8} more" if len(members) > 8 else "")
            raise MacrolanguageError(f"{hit.name} ({hit.code}) is a macrolanguage; pick one of: {shown}")
        return hit


def choose_origin(
    points: tuple[Point, ...],
    glottolog_point: tuple[float, float] | None,
    glottolog_country: str | None = None,
) -> Point | None:
    """The location most people would think of as where the language is from.

    LinguaMeta has a point for each country a language is spoken in. Most
    languages have one. For the rest, Glottolog's coordinate marks the
    traditional area, so we take the LinguaMeta point in the country that
    coordinate falls in (English in England, Spanish in Spain, Portuguese in
    Portugal), or failing that the nearest one, or with no Glottolog point at
    all the country with the most speakers. Regional points such as "Latin
    America" are only used if there is nothing else.
    """
    candidates = [p for p in points if p.locale.isalpha()] or list(points)
    if len(candidates) <= 1:
        return candidates[0] if candidates else None
    if glottolog_country:
        same = [p for p in candidates if p.locale.upper() == glottolog_country.upper()]
        if same:
            return same[0]
    if glottolog_point:
        return min(candidates, key=lambda p: great_circle_km(p.lat, p.lon, *glottolog_point))
    return max(candidates, key=lambda p: p.speakers or 0)


def build(
    records: dict[str, Record],
    glottolog: Glottolog,
    geocode: Callable[[list[tuple[float, float]]], list[str]] = country_of,
) -> Languages:
    """Join LinguaMeta to Glottolog.

    LinguaMeta has no coordinates for ~1,000 languages. Glottolog has a point
    for most of them, but these are on average less reliable (in a sample, a
    fifth fell outside every country LinguaMeta lists for the language, and
    several of those were plainly misplaced). So we fall back to Glottolog's
    point only when it lands in one of the language's LinguaMeta countries.
    """

    def glottolog_point(rec: Record) -> tuple[float, float] | None:
        gc = rec.glottocode
        if not gc:
            return None
        return glottolog.coords.get(gc) or glottolog.coords.get(glottolog.language_of.get(gc, ""))

    # Which country is each relevant Glottolog point in? Needed for languages
    # with no LinguaMeta point (fallback) or with several (choosing an origin).
    to_geocode = [
        code for code, rec in records.items()
        if glottolog_point(rec) and ((not rec.points and rec.locales) or len(rec.points) > 1)
    ]
    glottolog_country = dict(zip(to_geocode, geocode([glottolog_point(records[c]) for c in to_geocode])))

    fallback = {}
    for code, cc in glottolog_country.items():
        rec = records[code]
        if rec.scope == "LANGUAGE" and not rec.points and cc.lower() in rec.locales:
            fallback[code] = Point(*glottolog_point(rec), cc.lower(), FALLBACK_SOURCE)

    out = Languages()
    for code, rec in sorted(records.items()):
        lineage = None
        if rec.glottocode and glottolog.is_genealogical(rec.glottocode):
            lineage = glottolog.lineage(rec.glottocode)
        points = rec.points or ((fallback[code],) if code in fallback else ())
        out[code] = Language(
            code=code,
            record=rec,
            lineage=lineage,
            points=points,
            origin=choose_origin(points, glottolog_point(rec), glottolog_country.get(code)),
        )
    return out
