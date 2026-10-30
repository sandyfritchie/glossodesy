"""Command line: fetch data, build the website's data files, compare languages."""

from __future__ import annotations

import argparse
import json
import time
from functools import cached_property
from pathlib import Path

import numpy as np

from . import asjp, calibrate, distances, glottolog, languages, linguameta, neighbours, northeuralex
from .sources import DEFAULT_RAW_DIR, SOURCES, fetch, source_dir

DEFAULT_BUILD_DIR = Path("data/build")


class Data:
    null_size = 50_000

    def __init__(self, raw_dir: Path = DEFAULT_RAW_DIR):
        self.raw_dir = raw_dir

    @cached_property
    def glottolog(self) -> glottolog.Glottolog:
        return glottolog.load(source_dir("glottolog", self.raw_dir))

    @cached_property
    def languages(self) -> languages.Languages:
        records = linguameta.load(source_dir("linguameta", self.raw_dir))
        return languages.build(records, self.glottolog)

    @cached_property
    def wordlists(self) -> dict[str, asjp.Wordlist]:
        """One ASJP list per BCP-47 code, where ASJP has one."""
        index = asjp.ASJP(source_dir("asjp", self.raw_dir), self.glottolog)
        out = {}
        for code, lang in self.languages.items():
            if lang.is_macrolanguage:
                continue
            wl = index.select(lang.glottocode, names=(lang.name,))
            if wl:
                out[code] = wl
        return out

    @cached_property
    def native(self) -> dict[str, dict[str, str]]:
        """Spelling in the language's own writing system, per ASJP concept, where
        NorthEuraLex has the same word as the ASJP list."""
        import csv
        params = source_dir("asjp", self.raw_dir) / "cldf" / "parameters.csv"
        concepticon = {r["ID"]: r["Concepticon_ID"] for r in csv.DictReader(open(params, encoding="utf-8"))
                       if r["Name"].startswith("*")}
        words = northeuralex.load(source_dir("northeuralex", self.raw_dir), concepticon)
        out = {}
        for code, wl in self.wordlists.items():
            rec = self.languages[code].record
            cand = words.get(rec.iso or "") or words.get(rec.glottocode or "")
            if cand:
                matched = northeuralex.match(wl, cand)
                if matched:
                    out[code] = matched
        return out

    @cached_property
    def null(self) -> np.ndarray:
        return calibrate.unrelated_ldnd(self.wordlists, self.languages, n=self.null_size)

    def compare(self, a: languages.Language, b: languages.Language) -> dict:
        gen = distances.genealogical(a, b)
        geo = distances.geographic(a, b)
        wa, wb = self.wordlists.get(a.code), self.wordlists.get(b.code)
        lex = distances.ldnd(wa, wb) if wa and wb else None
        return {
            "a": a.code,
            "b": b.code,
            "genealogical": None if gen is None else {
                "distance": round(gen.distance, 4),
                "common_ancestor": gen.common_ancestor,
                "common_ancestor_name": self.glottolog.names.get(gen.common_ancestor),
            },
            "geographic": None if geo is None else {
                "km": round(geo.km, 1),
                "origins": [geo.points[0].locale, geo.points[1].locale],
            },
            "lexical": None if lex is None else {
                "ldnd": round(lex.ldnd, 4),
                "ldn": round(lex.ldn, 4),
                "n_shared": lex.n_shared,
                "doculects": [wa.doculect, wb.doculect],
                "same_list": wa.doculect == wb.doculect,
                "chance_rate": calibrate.chance_rate(self.null, lex.ldnd),
            },
        }


def _fmt(x, spec):
    return "—" if x is None else format(x, spec)


def cmd_compare(args) -> None:
    d = Data(args.raw)
    langs = d.languages
    print(f"{'A':22} {'B':22} {'gen':>5}  {'common ancestor':24} {'km':>6} {'LDND':>6} {'n':>3} {'chance':>7}")
    for pair in args.pairs:
        a, b = pair.split(",")
        try:
            A, B = langs.resolve(a), langs.resolve(b)
        except KeyError as e:
            print(f"{a}–{b}: {e.args[0]}")
            continue
        r = d.compare(A, B)
        gen, geo, lex = r["genealogical"], r["geographic"], r["lexical"]
        print(
            f"{A.name[:22]:22} {B.name[:22]:22} "
            f"{_fmt(gen and gen['distance'], '5.2f')}  "
            f"{(gen and gen['common_ancestor_name'] or '—')[:24]:24} "
            f"{_fmt(geo and geo['km'], '6.0f')} "
            f"{_fmt(lex and lex['ldnd'], '6.3f')} {_fmt(lex and lex['n_shared'], '3d')} "
            f"{_fmt(lex and lex['chance_rate'], '7.2%')}"
            + ("  (same ASJP list)" if lex and lex["same_list"] else "")
        )


def cmd_neighbours(args) -> None:
    d = Data(args.raw)
    langs, wls = d.languages, d.wordlists
    for q in args.languages:
        try:
            L = langs.resolve(q)
        except KeyError as e:
            print(e.args[0])
            continue
        print(f"\n{L.name} ({L.code})")
        if args.dimension == "lexical":
            if L.code not in wls:
                print("  no ASJP word list")
                continue
            me = wls[L.code]
            scored = []
            for code, wl in wls.items():
                if code == L.code or wl.doculect == me.doculect:
                    continue
                r = distances.ldnd(me, wl)
                if r:
                    scored.append((r.ldnd, code))
            scored.sort()
            for dist, code in scored[: args.k]:
                print(f"  {dist:6.3f}  {langs[code].name} ({code})")
        else:
            if not L.origin:
                print("  no location")
                continue
            others = sorted(
                ((g.km, o) for o in langs.values()
                 if o is not L and (g := distances.geographic(L, o)) is not None),
                key=lambda t: t[0],
            )
            for km, o in others[: args.k]:
                print(f"  {km:6.0f} km  {o.name} ({o.code})")


def cmd_build(args) -> None:
    d = Data(args.raw)
    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    langs, wls = d.languages, d.wordlists

    def dump(name, obj):
        path = out / name
        path.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        print(f"  wrote {path} ({path.stat().st_size / 1e6:.1f} MB)")

    t = time.time()
    dump("languages.json", {
        code: {
            "name": l.name,
            "endonym": l.record.endonym,
            "iso": l.record.iso,
            "glottocode": l.glottocode,
            "scope": l.record.scope.lower(),
            "macrolanguage": l.record.macrolanguage,
            "members": list(l.record.members) or None,
            "aliases": list(l.record.aliases) or None,
            "scripts": list(l.record.scripts) or None,
            "countries": [c for c in l.record.locales if c.isalpha()] or None,
            "official": list(l.record.official) or None,
            "speakers": l.record.speakers,
            "endangerment": l.record.endangerment,
            "origin": [l.origin.lat, l.origin.lon, l.origin.locale] if l.origin else None,
            "points": [[p.lat, p.lon, p.locale, p.source] for p in l.points],
            "lineage": list(l.lineage) if l.lineage else None,
            "asjp": wls[code].doculect if code in wls else None,
        }
        for code, l in langs.items()
    })
    used = {gc for l in langs.values() if l.lineage for gc in l.lineage}
    dump("ancestors.json", {gc: d.glottolog.names[gc] for gc in sorted(used)})
    dump("wordlists.json", {code: wl.words for code, wl in wls.items()})
    dump("concepts.json", asjp.load_concepts(source_dir("asjp", d.raw_dir)))
    dump("native.json", d.native)
    dump("scripts.json", linguameta.script_names(source_dir("linguameta", d.raw_dir)))
    print("geographic neighbours…")
    dump("neighbours_geographic.json", neighbours.geographic(langs, k=args.k))
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
        "sources": {k: {"repo": s.repo, "version": s.tag, "licence": s.licence, "citation": s.citation}
                    for k, s in SOURCES.items()},
        "licence": "CC-BY-SA-4.0 (derived from LinguaMeta)",
        "built": time.strftime("%Y-%m-%d"),
    })
    print(f"done in {time.time() - t:.0f}s")


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="glossodesy")
    p.add_argument("--raw", type=Path, default=DEFAULT_RAW_DIR, help="where upstream data lives")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("fetch", help="download the pinned upstream datasets").set_defaults(
        func=lambda a: fetch(a.raw))

    c = sub.add_parser("compare", help="compare language pairs, e.g. nl,de es,pt")
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
