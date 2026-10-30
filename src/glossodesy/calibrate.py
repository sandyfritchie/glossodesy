"""What does an LDND score look like between languages that aren't related?

LDND is already chance-corrected on average, but the spread matters: an isolate's
"nearest" lexical neighbours are just the luckiest unrelated lists (Basque's top
hits are scattered Austronesian and Papuan languages at ~0.91). Sampling pairs
with no common ancestor in Glottolog gives an empirical null distribution, so we
can say how often unrelated languages look at least this similar.
"""

from __future__ import annotations

import random

import numpy as np

from .asjp import Wordlist
from .distances import ldnd
from .languages import Language


def unrelated_ldnd(
    wordlists: dict[str, Wordlist], languages: dict[str, Language], n: int = 50_000, seed: int = 0
) -> np.ndarray:
    """Sorted LDND values for ``n`` random pairs from different top-level families."""
    codes = [c for c in sorted(wordlists) if languages[c].lineage]
    rng = random.Random(seed)
    out = []
    while len(out) < n:
        a, b = rng.sample(codes, 2)
        if languages[a].lineage[0] == languages[b].lineage[0]:
            continue
        r = ldnd(wordlists[a], wordlists[b])
        if r:
            out.append(r.ldnd)
    return np.sort(np.array(out, dtype=np.float32))


def chance_rate(null: np.ndarray, value: float) -> float:
    """Share of unrelated pairs with LDND at or below ``value``."""
    return float(np.searchsorted(null, value, side="right")) / len(null)
