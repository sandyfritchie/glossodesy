"""NorthEuraLex: the same core words in each language's own writing system.

ASJP stores words only in its 41-symbol transcription. NorthEuraLex (107
languages, mostly northern Eurasia) has the orthographic form of each word
alongside an IPA transcription, linked to ASJP's concepts through Concepticon.
We show the spelling next to the ASJP form, so it has to be the same word:
where a concept has several words (Hindi आँख and चक्षु for "eye"), we pick
the one whose IPA, roughly converted to ASJP symbols, is closest to the ASJP
form, and show nothing if none is close.
"""

from __future__ import annotations

import csv
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

from rapidfuzz.distance import Levenshtein

from .asjp import Wordlist

# Words are compared as broad sound classes (voicing, vowel quality and place
# details ignored), since the two sources transcribe differently. Above this
# normalised distance the NorthEuraLex word is probably a different word.
MAX_DISTANCE = 0.4
_CLASSES = str.maketrans({
    **dict.fromkeys("pbfv8", "P"), **dict.fromkeys("td", "T"), **dict.fromkeys("kgqGxX", "K"),
    **dict.fromkeys("szSZcCj", "S"), **dict.fromkeys("nN5", "N"), "m": "M",
    **dict.fromkeys("rlL4", "R"), "w": "W", "y": "Y", **dict.fromkeys("h7", "H"),
    **dict.fromkeys("aeiouE3", "V"),
})


def sound_classes(asjp_form: str) -> str:
    """Collapse to broad classes, merging repeated symbols (long vowels, geminates)."""
    s = asjp_form.translate(_CLASSES)
    return re.sub(r"(.)\1+", r"\1", s)


def similarity_distance(a: str, b: str) -> float:
    """0 = same word, 1 = unrelated. A stem match counts as the same word, so
    a citation form with a suffix (Turkish gelmek, ASJP gel) still matches."""
    ca, cb = sound_classes(a), sound_classes(b)
    if not ca or not cb:
        return 1.0
    short, long_ = sorted((ca, cb), key=len)
    if len(short.replace("V", "")) >= 1 and len(short) >= 2 and long_.startswith(short):
        return 0.0
    return Levenshtein.normalized_distance(ca, cb)

# Rough IPA -> ASJP symbols. Multi-character sequences first, and the IPA
# vowels y/ʏ before j, since j becomes ASJP y.
_IPA_TO_ASJP = [
    ("y", "i"), ("ʏ", "i"),
    ("t͡ʃ", "C"), ("tʃ", "C"), ("d͡ʒ", "j"), ("dʒ", "j"), ("t͡s", "c"), ("ts", "c"),
    ("d͡z", "z"), ("dz", "z"), ("t͡ɕ", "C"), ("tɕ", "C"), ("d͡ʑ", "j"), ("dʑ", "j"),
    ("ʃ", "S"), ("ʂ", "S"), ("ɕ", "S"), ("ʒ", "Z"), ("ʐ", "Z"), ("ʑ", "Z"),
    ("ŋ", "N"), ("ɲ", "5"), ("ɳ", "n"), ("ʔ", "7"), ("θ", "8"), ("ð", "8"),
    ("χ", "X"), ("ʁ", "X"), ("ħ", "h"), ("ʕ", "7"), ("ɦ", "h"), ("ç", "x"), ("ɣ", "x"),
    ("ɟ", "y"), ("j", "y"), ("ʎ", "L"), ("ɫ", "l"), ("ɭ", "l"), ("ɾ", "r"), ("ɹ", "r"),
    ("ɻ", "r"), ("ʀ", "r"), ("ʋ", "v"), ("β", "v"), ("ɸ", "f"), ("ɡ", "g"), ("ɢ", "G"),
    ("ʈ", "t"), ("ɖ", "d"), ("ɕ", "S"),
    ("ə", "3"), ("ɐ", "3"), ("ɜ", "3"), ("ɘ", "3"), ("ɛ", "E"), ("æ", "E"), ("œ", "E"),
    ("ø", "e"), ("ɔ", "o"), ("ɒ", "o"), ("ɑ", "a"), ("ʌ", "a"), ("ɪ", "i"), ("ɨ", "i"),
    ("ʊ", "u"), ("ɯ", "u"), ("ɤ", "o"),
]


def ipa_to_asjp(ipa: str) -> str:
    s = ipa.replace(" ", "")
    for a, b in _IPA_TO_ASJP:
        s = s.replace(a, b)
    # Drop length, stress, tone, aspiration and other diacritics.
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return re.sub(r"[^A-Za-z0-9]", "", s)


def load(nel_dir: Path, asjp_concepticon: dict[str, str]) -> dict[str, dict[str, list[tuple[str, str]]]]:
    """Language (ISO 639-3 and glottocode keys) -> ASJP concept id -> [(spelling, ipa)]."""
    cldf = nel_dir / "cldf"
    to_asjp = {}
    with open(cldf / "parameters.csv", encoding="utf-8") as f:
        by_concepticon = {cid: aid for aid, cid in asjp_concepticon.items()}
        for r in csv.DictReader(f):
            if r["Concepticon_ID"] in by_concepticon:
                to_asjp[r["ID"]] = by_concepticon[r["Concepticon_ID"]]
    langs = {}
    with open(cldf / "languages.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            langs[r["ID"]] = [k for k in (r["ISO639P3code"], r["Glottocode"]) if k]
    words: dict[str, dict[str, list[tuple[str, str]]]] = defaultdict(lambda: defaultdict(list))
    with open(cldf / "forms.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            concept = to_asjp.get(r["Parameter_ID"])
            if concept and r["Value"]:
                for key in langs.get(r["Language_ID"], []):
                    words[key][concept].append((r["Value"], r["Form"]))
    return words


def match(wordlist: Wordlist, candidates: dict[str, list[tuple[str, str]]]) -> dict[str, str]:
    """For each concept, the spelling of the word that matches the ASJP form."""
    out = {}
    for concept, forms in wordlist.words.items():
        best, best_d = None, MAX_DISTANCE
        for spelling, ipa in candidates.get(concept, []):
            approx = ipa_to_asjp(ipa)
            for f in forms:
                d = similarity_distance(approx, f)
                if d <= best_d:
                    best, best_d = spelling, d
        if best:
            out[concept] = best
    return out
