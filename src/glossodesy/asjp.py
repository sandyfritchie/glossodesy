"""ASJP word lists, and picking the right one for a language."""

from __future__ import annotations

import csv
import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from .glottolog import Glottolog

# ASJP code modifiers: * nasalised, " glottalised, ~ and $ merge the preceding
# 2 or 3 symbols into one segment, ! marks clicks. Like the standard LDND
# implementations, we drop them and compare the base symbols.
_MODIFIERS = re.compile(r'[*"~$!\s]')

# Lists shorter than this are too sparse for a stable LDND (ASJP convention).
MIN_CONCEPTS = 28
# A list that looks like the standard variety is preferred over dialect lists
# once it has at least this many concepts.
GOOD_ENOUGH = 35


def normalise(form: str) -> str:
    return _MODIFIERS.sub("", form)


def _tokens(s: str) -> tuple[str, ...]:
    folded = unicodedata.normalize("NFKD", s.lower()).encode("ascii", "ignore").decode()
    return tuple(re.findall(r"[a-z]+", folded))


def _name_match(doculect: str, language_name: str, coded_to_target: bool) -> float:
    """How much a doculect looks like the named variety.

    ASJP often codes dialect lists (BRABANTIC, KUNMING_MANDARIN) to the
    language's own glottocode, so the glottocode alone can't tell us which list
    is "Dutch" or "Mandarin Chinese". The doculect's name usually can.
    """
    numbered = re.search(r"_\d+$", doculect) is not None
    doc = _tokens(re.sub(r"_\d+$", "", doculect))
    name = _tokens(language_name)
    if doc == name:  # DUTCH for Dutch; ENGLISH_2 scores a little lower
        return 4 if not numbered else 3
    if name[:1] == ("standard",) and doc == name[1:]:  # GERMAN for Standard German
        return 3
    if set(doc) <= set(name):  # MANDARIN for Mandarin Chinese
        return 3 if not numbered else 2
    if set(name) <= set(doc):  # NORWEGIAN_NYNORSK_TOTEN for Norwegian Nynorsk
        return 1
    return 0.5 if coded_to_target else 0


@dataclass
class Wordlist:
    doculect: str
    glottocode: str  # as coded in ASJP
    words: dict[str, tuple[str, ...]]  # concept id -> forms (synonyms)

    def __len__(self) -> int:
        return len(self.words)


def load_concepts(asjp_dir: Path) -> dict[str, str]:
    """The 40-item ASJP list (concepts starred in parameters.csv): id -> gloss."""
    out = {}
    with open(asjp_dir / "cldf" / "parameters.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["Name"].startswith("*"):
                out[r["ID"]] = r["Name"].lstrip("*")
    return out


class ASJP:
    """All usable ASJP lists, indexed by Glottolog languoid."""

    def __init__(self, asjp_dir: Path, glottolog: Glottolog):
        self.glottolog = glottolog
        concepts = load_concepts(asjp_dir)
        cldf = asjp_dir / "cldf"
        coded: dict[str, str] = {}
        with open(cldf / "languages.csv", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r["Glottocode"] in glottolog.language_of:
                    coded[r["ID"]] = r["Glottocode"]

        words: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
        with open(cldf / "forms.csv", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r["Parameter_ID"] in concepts and r["Loan"] != "true" and r["Language_ID"] in coded:
                    w = normalise(r["Form"])
                    if w:
                        words[r["Language_ID"]][r["Parameter_ID"]].append(w)

        self.by_glottocode: dict[str, list[Wordlist]] = defaultdict(list)
        self.by_language: dict[str, list[Wordlist]] = defaultdict(list)
        for doc, ws in words.items():
            if len(ws) < MIN_CONCEPTS:
                continue
            wl = Wordlist(doc, coded[doc], {c: tuple(v) for c, v in ws.items()})
            self.by_glottocode[wl.glottocode].append(wl)
            self.by_language[glottolog.language_of[wl.glottocode]].append(wl)

    def select(self, glottocode: str | None, names: tuple[str, ...] = ()) -> Wordlist | None:
        """The best list for a languoid.

        For a dialect-level glottocode (LinguaMeta codes Norwegian Bokmål as a
        dialect of Norwegian, for instance) we use a list coded to exactly that
        dialect when there is one. Otherwise we choose among all lists for the
        language: the one whose name marks it as the standard variety, provided
        it is near-complete, failing that the fullest.
        """
        g = self.glottolog
        if not glottocode or glottocode not in g.language_of:
            return None
        lang = g.language_of[glottocode]
        specific = names + (g.names[glottocode],)  # the variety asked for
        general = (g.names[lang],)  # the language it belongs to
        if glottocode != lang and self.by_glottocode.get(glottocode):
            pool, target = self.by_glottocode[glottocode], glottocode
        else:
            pool, target = self.by_language.get(lang, []), lang

        def rank(wl: Wordlist) -> tuple:
            if len(wl) < GOOD_ENOUGH:
                return (0, 0, -len(wl), wl.doculect)
            coded = wl.glottocode == target
            return (
                -max(_name_match(wl.doculect, n, coded) for n in specific),
                -max(_name_match(wl.doculect, n, coded) for n in general),
                -len(wl),
                wl.doculect,
            )

        return min(pool, key=rank) if pool else None
