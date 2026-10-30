"""Load language-level languoids and their classification from Glottolog CLDF."""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

# Glottolog "category" values for language-level languoids whose position in a
# pseudo-family says nothing about genealogy. Sign languages are kept: Glottolog
# groups them in a pseudo-family but classifies them genealogically inside it.
NON_GENEALOGICAL = {
    "Pidgin",
    "Mixed_Language",
    "Artificial_Language",
    "Speech_Register",
    "Unclassifiable",
    "Unattested",
}
EXCLUDED = {"Bookkeeping"}


@dataclass
class Language:
    glottocode: str
    name: str
    iso: str | None
    category: str
    macroarea: str | None
    lat: float | None
    lon: float | None
    family_id: str | None
    path: tuple[str, ...] = field(default=())  # ancestors, root first, excluding self

    @property
    def is_genealogical(self) -> bool:
        return self.category not in NON_GENEALOGICAL

    @property
    def lineage(self) -> tuple[str, ...]:
        """Ancestors plus the language itself."""
        return self.path + (self.glottocode,)


@dataclass
class Glottolog:
    languages: dict[str, Language]
    names: dict[str, str]  # every languoid (incl. families, dialects) -> name
    language_of: dict[str, str]  # every languoid at or below language level -> language

    def resolve(self, query: str) -> Language:
        """Find a language by glottocode, ISO 639-3 code or exact name (case-insensitive)."""
        q = query.strip()
        if q in self.language_of:
            return self.languages[self.language_of[q]]
        ql = q.lower()
        for lang in self.languages.values():
            if lang.iso == ql:
                return lang
        matches = [l for l in self.languages.values() if l.name.lower() == ql]
        if len(matches) == 1:
            return matches[0]
        if matches:
            raise KeyError(f"{query!r} is ambiguous: {[m.glottocode for m in matches]}")
        raise KeyError(f"No language matches {query!r}")


def _float(s: str) -> float | None:
    return float(s) if s else None


def load(glottolog_dir: Path) -> Glottolog:
    cldf = glottolog_dir / "cldf"
    rows = list(csv.DictReader(open(cldf / "languages.csv", encoding="utf-8")))
    names = {r["ID"]: r["Name"] for r in rows}

    category: dict[str, str] = {}
    classification: dict[str, tuple[str, ...]] = {}
    with open(cldf / "values.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            pid = r["Parameter_ID"]
            if pid == "category":
                category[r["Language_ID"]] = r["Value"]
            elif pid == "classification" and r["Value"]:
                classification[r["Language_ID"]] = tuple(r["Value"].split("/"))

    languages: dict[str, Language] = {}
    language_of: dict[str, str] = {}
    for r in rows:
        gc = r["ID"]
        if r["Level"] == "language":
            cat = category.get(gc, "")
            if cat in EXCLUDED:
                continue
            languages[gc] = Language(
                glottocode=gc,
                name=r["Name"],
                iso=r["ISO639P3code"] or None,
                category=cat,
                macroarea=r["Macroarea"] or None,
                lat=_float(r["Latitude"]),
                lon=_float(r["Longitude"]),
                family_id=r["Family_ID"] or None,
                path=classification.get(gc, ()),
            )
            language_of[gc] = gc
    for r in rows:
        if r["Level"] == "dialect" and r["Language_ID"] in languages:
            language_of[r["ID"]] = r["Language_ID"]
    return Glottolog(languages=languages, names=names, language_of=language_of)
