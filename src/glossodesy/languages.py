"""The language index: LinguaMeta records joined to Glottolog by glottocode."""

from __future__ import annotations

from dataclasses import dataclass

from .glottolog import Glottolog
from .linguameta import Point, Record


@dataclass
class Language:
    code: str  # BCP-47, the project's primary key
    record: Record
    lineage: tuple[str, ...] | None  # Glottolog root-to-languoid path, if classifiable

    @property
    def name(self) -> str:
        return self.record.name

    @property
    def glottocode(self) -> str | None:
        return self.record.glottocode

    @property
    def points(self) -> tuple[Point, ...]:
        return self.record.points

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


def build(records: dict[str, Record], glottolog: Glottolog) -> Languages:
    out = Languages()
    for code, rec in sorted(records.items()):
        lineage = None
        if rec.glottocode and glottolog.is_genealogical(rec.glottocode):
            lineage = glottolog.lineage(rec.glottocode)
        out[code] = Language(code=code, record=rec, lineage=lineage)
    return out
