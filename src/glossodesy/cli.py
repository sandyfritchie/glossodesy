"""Command line: fetch data, build the website's data files, compare languages."""

from __future__ import annotations

import argparse
import json
import time
from functools import cached_property
from pathlib import Path

import numpy as np

from . import asjp, calibrate, distances, glottolog, neighbours
from .sources import DEFAULT_RAW_DIR, SOURCES, fetch, source_dir

DEFAULT_BUILD_DIR = Path("data/build")


class Data:
    def __init__(self, raw_dir: Path = DEFAULT_RAW_DIR):
        self.raw_dir = raw_dir

    @cached_property
    def glottolog(self) -> glottolog.Glottolog:
        return glottolog.load(source_dir("glottolog", self.raw_dir))

    @cached_property
    def wordlists(self) -> dict[str, asjp.Wordlist]:
        return asjp.load(source_dir("asjp", self.raw_dir), self.glottolog)

    @cached_property
    def null(self) -> np.ndarray:
        return calibrate.unrelated_ldnd(self.wordlists, self.glottolog, n=self.null_size)

    null_size = 50_000

    def compare(self, a: glottolog.Language, b: glottolog.Language) -> dict:
        gen = distances.genealogical(a, b)
        wa, wb = self.wordlists.get(a.glottocode), self.wordlists.get(b.glottocode)
        lex = distances.ldnd(wa, wb) if wa and wb else None
        return {
            "a": a.glottocode,
            "b": b.glottocode,
            "genealogical": None if gen is None else {
                "distance": round(gen.distance, 4),
                "common_ancestor": gen.common_ancestor,
                "common_ancestor_name": self.glottolog.names.get(gen.common_ancestor),
            },
            "geographic_km": distances.geographic_km(a, b),
            "lexical": None if lex is None else {
                "ldnd": round(lex.ldnd, 4),
                "ldn": round(lex.ldn, 4),
                "n_shared": lex.n_shared,
                "doculects": [wa.doculect, wb.doculect],
                "chance_rate": calibrate.chance_rate(self.null, lex.ldnd),
            },
        }


def _fmt(x, spec):
    return "—" if x is None else format(x, spec)


def cmd_compare(args) -> None:
    d = Data(args.raw)
    g = d.glottolog
    pairs = [p.split(",") for p in args.pairs]
    print(f"{'A':22} {'B':22} {'gen':>5}  {'common ancestor':24} {'km':>6} {'LDND':>6} {'n':>3} {'chance':>7}")
    for a, b in pairs:
        try:
            A, B = g.resolve(a), g.resolve(b)
        except KeyError as e:
            print(f"{a}–{b}: {e.args[0]}")
            continue
        r = d.compare(A, B)
        gen, lex = r["genealogical"], r["lexical"]
        print(
            f"{A.name[:22]:22} {B.name[:22]:22} "
            f"{_fmt(gen and gen['distance'], '5.2f')}  "
            f"{(gen and gen['common_ancestor_name'] or '—')[:24]:24} "
            f"{_fmt(r['geographic_km'], '6.0f')} "
            f"{_fmt(lex and lex['ldnd'], '6.3f')} {_fmt(lex and lex['n_shared'], '3d')} "
            f"{_fmt(lex and lex['chance_rate'], '7.2%')}"
        )


def cmd_neighbours(args) -> None:
    d = Data(args.raw)
    g, wls = d.glottolog, d.wordlists
    for q in args.languages:
        L = g.resolve(q)
        print(f"\n{L.name} ({L.glottocode})")
        if args.dimension == "lexical":
            if L.glottocode not in wls:
                print("  no ASJP word list")
                continue
            me = wls[L.glottocode]
            scored = []
            for gc, wl in wls.items():
                if gc == L.glottocode:
                    continue
                r = distances.ldnd(me, wl)
                if r:
                    scored.append((r.ldnd, gc))
            scored.sort()
            for dist, gc in scored[: args.k]:
                print(f"  {dist:6.3f}  {g.languages[gc].name}")
        else:
            others = [
                (distances.geographic_km(L, o), o)
                for o in g.languages.values()
                if o is not L and o.lat is not None
            ]
            others.sort(key=lambda t: t[0])
            for km, o in others[: args.k]:
                print(f"  {km:6.0f} km  {o.name}")


def cmd_build(args) -> None:
    d = Data(args.raw)
    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    g, wls = d.glottolog, d.wordlists

    def dump(name, obj):
        path = out / name
        path.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        print(f"  wrote {path} ({path.stat().st_size / 1e6:.1f} MB)")

    t = time.time()
    dump("languages.json", {
        gc: {
            "name": l.name, "iso": l.iso, "category": l.category, "macroarea": l.macroarea,
            "lat": l.lat, "lon": l.lon, "family": l.family_id, "path": list(l.path),
            "asjp": wls[gc].doculect if gc in wls else None,
        }
        for gc, l in g.languages.items()
    })
    used = {a for l in g.languages.values() for a in l.path}
    dump("ancestors.json", {gc: g.names[gc] for gc in sorted(used)})
    dump("wordlists.json", {gc: wl.words for gc, wl in wls.items()})
    print("geographic neighbours…")
    dump("neighbours_geographic.json", neighbours.geographic(g.languages, k=args.k))
    print("chance baseline for LDND…")
    d.null_size = args.null_size
    probs = np.unique(np.concatenate([np.geomspace(1e-5, 0.01, 60), np.linspace(0.01, 1, 100)]))
    dump("ldnd_null.json", {
        "description": "LDND quantiles for random pairs of languages with no common Glottolog ancestor",
        "n_pairs": int(len(d.null)),
        "p": [round(float(p), 6) for p in probs],
        "ldnd": [round(float(v), 4) for v in np.quantile(d.null, probs)],
    })
    print("lexical neighbours (the slow one)…")
    dump("neighbours_lexical.json", neighbours.lexical(wls, k=args.k))
    dump("meta.json", {
        "sources": {k: {"repo": s.repo, "tag": s.tag, "licence": s.licence, "citation": s.citation}
                    for k, s in SOURCES.items()},
        "built": time.strftime("%Y-%m-%d"),
    })
    print(f"done in {time.time() - t:.0f}s")


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="glossodesy")
    p.add_argument("--raw", type=Path, default=DEFAULT_RAW_DIR, help="where upstream data lives")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("fetch", help="download the pinned upstream datasets").set_defaults(
        func=lambda a: fetch(a.raw))

    c = sub.add_parser("compare", help="compare language pairs, e.g. nld,deu spa,por")
    c.add_argument("pairs", nargs="+")
    c.set_defaults(func=cmd_compare)

    n = sub.add_parser("neighbours", help="nearest languages to each one given")
    n.add_argument("languages", nargs="+")
    n.add_argument("-d", "--dimension", choices=["lexical", "geographic"], default="lexical")
    n.add_argument("-k", type=int, default=10)
    n.set_defaults(func=cmd_neighbours)

    b = sub.add_parser("build", help="write the JSON files the website reads")
    b.add_argument("--out", type=Path, default=DEFAULT_BUILD_DIR)
    b.add_argument("-k", type=int, default=25)
    b.add_argument("--null-size", type=int, default=200_000, help="unrelated pairs to sample")
    b.set_defaults(func=cmd_build)

    args = p.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
