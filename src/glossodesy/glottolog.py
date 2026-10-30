"""Glottolog: the classification tree, used for genealogy and for mapping
dialect-level glottocodes onto languages.

Language identity (codes, names, coordinates) comes from LinguaMeta; Glottolog
is consulted only by glottocode.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

# Glottolog "category" values whose position in a pseudo-family says nothing
# about genealogy. Sign languages are kept: Glottolog groups them in a
# pseudo-family but classifies them genealogically inside it.
NON_GENEALOGICAL = {
    "Bookkeeping",
    "Pidgin",
    "Mixed_Language",
    "Artificial_Language",
    "Speech_Register",
    "Unclassifiable",
    "Unattested",
}


@dataclass
class Glottolog:
    names: dict[str, str]  # every languoid -> name
    level: dict[str, str]  # every languoid -> family | language | dialect
    path: dict[str, tuple[str, ...]]  # every languoid -> ancestors, root first
    language_of: dict[str, str]  # language or dialect -> its language-level languoid
    category: dict[str, str]  # language -> Glottolog category

    def lineage(self, glottocode: str) -> tuple[str, ...] | None:
        """Root-to-languoid path, including the languoid itself."""
        if glottocode not in self.level:
            return None
        return self.path.get(glottocode, ()) + (glottocode,)

    def is_genealogical(self, glottocode: str) -> bool:
        if glottocode not in self.level:
            return False
        lang = self.language_of.get(glottocode)
        if lang is None:  # a family-level code: genealogical by definition
            return self.category.get(glottocode, "Family") == "Family"
        return self.category.get(lang) not in NON_GENEALOGICAL


def load(glottolog_dir: Path) -> Glottolog:
    cldf = glottolog_dir / "cldf"
    names, level, language_of = {}, {}, {}
    with open(cldf / "languages.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            gc = r["ID"]
            names[gc] = r["Name"]
            level[gc] = r["Level"]
            if r["Level"] == "language":
                language_of[gc] = gc
            elif r["Level"] == "dialect" and r["Language_ID"]:
                language_of[gc] = r["Language_ID"]

    category, path = {}, {}
    with open(cldf / "values.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            pid = r["Parameter_ID"]
            if pid == "category":
                category[r["Language_ID"]] = r["Value"]
            elif pid == "classification" and r["Value"]:
                path[r["Language_ID"]] = tuple(r["Value"].split("/"))
    return Glottolog(names=names, level=level, path=path, language_of=language_of, category=category)
