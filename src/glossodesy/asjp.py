"""Load ASJP word lists and pick one representative list per Glottolog language."""

from __future__ import annotations

import csv
import re
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


def _squash(s: str) -> str:
    return re.sub(r"[^a-z]", "", s.lower())


def _name_match(doculect: str, language_name: str, coded_to_language: bool) -> int:
    """How much a doculect looks like the standard variety of its language.

    ASJP often codes dialect lists (BRABANTIC, JAMTLANDIC) to the language's own
    glottocode, so the glottocode alone can't tell us which list is "Dutch".
    The doculect's name usually can: DUTCH, ENGLISH_2, STANDARD_GERMAN.
    """
    name, base = _squash(language_name), _squash(re.sub(r"_\d+$", "", doculect))
    if base == name:
        return 3 if not re.search(r"_\d+$", doculect) else 2
    if name.startswith("standard") and base == name[len("standard"):]:
        return 2
    return 1 if coded_to_language else 0


@dataclass
class Wordlist:
    doculect: str
    glottocode: str  # language-level glottocode
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


def load(asjp_dir: Path, glottolog: Glottolog) -> dict[str, Wordlist]:
    """Return one word list per language-level glottocode.

    Where ASJP has several doculects for a language (dialects, different
    sources), we keep the one whose name marks it as the standard variety
    (DUTCH over BRABANTIC), provided it is near-complete; failing that, the one
    with the most of the 40 concepts attested.
    """
    concepts = load_concepts(asjp_dir)
    cldf = asjp_dir / "cldf"

    doc_lang: dict[str, str] = {}
    doc_match: dict[str, int] = {}
    with open(cldf / "languages.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            gc = r["Glottocode"]
            if gc and gc in glottolog.language_of:
                lang = glottolog.languages[glottolog.language_of[gc]]
                doc_lang[r["ID"]] = lang.glottocode
                doc_match[r["ID"]] = _name_match(r["ID"], lang.name, coded_to_language=lang.glottocode == gc)

    words: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    with open(cldf / "forms.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["Parameter_ID"] not in concepts or r["Loan"] == "true":
                continue
            if r["Language_ID"] not in doc_lang:
                continue
            w = normalise(r["Form"])
            if w:
                words[r["Language_ID"]][r["Parameter_ID"]].append(w)

    def rank(doc: str) -> tuple:
        # A near-complete list that looks like the standard language beats
        # dialect lists; otherwise take the fullest list.
        match = doc_match[doc] if len(words[doc]) >= GOOD_ENOUGH else 0
        return (-match, -len(words[doc]), doc)

    best: dict[str, Wordlist] = {}
    for doc in sorted(words, key=rank):
        ws = words[doc]
        if len(ws) < MIN_CONCEPTS or doc_lang[doc] in best:
            continue
        best[doc_lang[doc]] = Wordlist(doc, doc_lang[doc], {c: tuple(v) for c, v in ws.items()})
    return best
