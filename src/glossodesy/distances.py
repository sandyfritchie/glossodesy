"""Distance measures. Each returns None when the data can't support a comparison."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from rapidfuzz.distance import Levenshtein
from rapidfuzz.process import cdist

from .asjp import Wordlist
from .glottolog import Language

# --- Genealogical ---------------------------------------------------------


@dataclass
class Genealogical:
    distance: float  # 0 = same language, 1 = no common ancestor in Glottolog
    common_ancestor: str | None  # glottocode of the lowest shared node


def genealogical(a: Language, b: Language) -> Genealogical | None:
    """Tree distance: 1 - shared lineage / longer lineage.

    Lineages are root-to-language paths in the Glottolog tree. Because Glottolog
    subgroups some families far more finely than others, the same number can
    mean different time depths in different families; it is a structural
    measure, not a dating.
    """
    if not (a.is_genealogical and b.is_genealogical):
        return None
    la, lb = a.lineage, b.lineage
    shared = 0
    for x, y in zip(la, lb):
        if x != y:
            break
        shared += 1
    if shared == 0:
        return Genealogical(1.0, None)
    return Genealogical(1 - shared / max(len(la), len(lb)), la[shared - 1])


# --- Geographic -----------------------------------------------------------

EARTH_RADIUS_KM = 6371.0


def geographic_km(a: Language, b: Language) -> float | None:
    """Great-circle distance between Glottolog's representative points."""
    if None in (a.lat, a.lon, b.lat, b.lon):
        return None
    p1, p2 = math.radians(a.lat), math.radians(b.lat)
    dp, dl = p2 - p1, math.radians(b.lon - a.lon)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(h))


# --- Lexical (LDND) -------------------------------------------------------

MIN_SHARED = 20


@dataclass
class Lexical:
    ldnd: float  # ~0 = identical lists; ~1 = no more similar than chance
    ldn: float  # mean normalised Levenshtein over same-meaning pairs
    n_shared: int  # concepts attested in both lists


def ldnd(a: Wordlist, b: Wordlist, min_shared: int = MIN_SHARED) -> Lexical | None:
    """Levenshtein Distance Normalised Divided (Wichmann et al. 2010).

    LDN is the mean length-normalised edit distance between words for the same
    concept. Dividing by the mean over *different* concepts corrects for chance
    resemblance from similar phoneme inventories and word shapes. Where a
    concept has synonyms, the closest pair is used.
    """
    shared = sorted(set(a.words) & set(b.words))
    if len(shared) < min_shared:
        return None
    wa = [w for c in shared for w in a.words[c]]
    wb = [w for c in shared for w in b.words[c]]
    m = cdist(wa, wb, scorer=Levenshtein.normalized_distance, dtype=np.float32)

    n = len(shared)
    if len(wa) == n and len(wb) == n:  # no synonyms: the common case
        best = m
    else:  # concept x concept, min over synonym pairs
        ia = np.array([i for i, c in enumerate(shared) for _ in a.words[c]])
        ib = np.array([i for i, c in enumerate(shared) for _ in b.words[c]])
        best = np.ones((n, n), dtype=np.float32)
        np.minimum.at(best, (ia[:, None], ib[None, :]), m)
    same = float(np.trace(best)) / n
    diff = (float(best.sum()) - same * n) / (n * (n - 1))
    return Lexical(ldnd=same / diff if diff else float("nan"), ldn=same, n_shared=n)
