"""Nearest-neighbour lists, precomputed for the website.

Pairwise comparisons are cheap enough to do on demand, but "the 25 languages
closest to X" needs a pass over every pair, so we do that offline.
"""

from __future__ import annotations

import numpy as np
from rapidfuzz.distance import Levenshtein
from rapidfuzz.process import cdist

from .asjp import Wordlist
from .distances import MIN_SHARED, ldnd
from .geo import EARTH_RADIUS_KM
from .languages import Language


def lexical(
    wordlists: dict[str, Wordlist], k: int = 25, candidates: int = 100
) -> dict[str, list[tuple[str, float]]]:
    """Top-k neighbours by LDND for every language with a word list.

    Exact LDND for all ~15M pairs is too slow, so we first rank every pair by
    LDN (same-meaning distances only; one form per concept, computed as one
    big matrix per concept), keep the best ``candidates`` per language, and
    compute exact LDND only for those. LDN and LDND rankings agree closely
    among near neighbours, so this rarely changes the top k.
    """
    codes = sorted(wordlists)
    n = len(codes)
    concepts = sorted({c for wl in wordlists.values() for c in wl.words})
    total = np.zeros((n, n), dtype=np.float32)
    count = np.zeros((n, n), dtype=np.uint8)
    for c in concepts:
        idx = np.array([i for i, gc in enumerate(codes) if c in wordlists[gc].words])
        words = [wordlists[codes[i]].words[c][0] for i in idx]
        m = cdist(words, words, scorer=Levenshtein.normalized_distance, dtype=np.float32, workers=-1)
        ix = np.ix_(idx, idx)
        total[ix] += m
        count[ix] += 1
    with np.errstate(divide="ignore", invalid="ignore"):
        ldn = total / count
    del total
    ldn[count < MIN_SHARED] = np.inf
    np.fill_diagonal(ldn, np.inf)
    del count

    cand = np.argpartition(ldn, candidates, axis=1)[:, :candidates]
    cache: dict[tuple[int, int], float] = {}
    out: dict[str, list[tuple[str, float]]] = {}
    for i in range(n):
        scored = []
        for j in cand[i]:
            if not np.isfinite(ldn[i, j]):
                continue
            if wordlists[codes[i]].doculect == wordlists[codes[j]].doculect:
                continue  # two codes that fall back to the same ASJP list
            key = (min(i, int(j)), max(i, int(j)))
            if key not in cache:
                r = ldnd(wordlists[codes[key[0]]], wordlists[codes[key[1]]])
                cache[key] = r.ldnd if r else np.inf
            scored.append((codes[j], cache[key]))
        scored.sort(key=lambda t: t[1])
        out[codes[i]] = [(gc, round(d, 4)) for gc, d in scored[:k] if np.isfinite(d)]
    return out


def geographic(languages: dict[str, Language], k: int = 25) -> dict[str, list[tuple[str, float]]]:
    """Top-k nearest languages by great-circle distance (km) between origin points."""
    codes = sorted(c for c, l in languages.items() if l.origin and not l.is_macrolanguage)
    lat = np.radians([languages[c].origin.lat for c in codes])
    lon = np.radians([languages[c].origin.lon for c in codes])
    out = {}
    for start in range(0, len(codes), 1000):
        sl = slice(start, start + 1000)
        dlat = lat[None, :] - lat[sl, None]
        dlon = lon[None, :] - lon[sl, None]
        h = np.sin(dlat / 2) ** 2 + np.cos(lat[sl, None]) * np.cos(lat[None, :]) * np.sin(dlon / 2) ** 2
        d = 2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(np.clip(h, 0, 1)))
        for r in range(d.shape[0]):
            d[r, start + r] = np.inf
        top = np.argpartition(d, k, axis=1)[:, :k]
        for r, row in enumerate(top):
            row = row[np.argsort(d[r, row])]
            out[codes[start + r]] = [(codes[j], round(float(d[r, j]), 1)) for j in row]
    return out
