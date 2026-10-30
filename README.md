# glossodesy

How close are two languages? It depends what you mean. glossodesy measures
language similarity along separate dimensions, each with a stated method and
an honest note on coverage, rather than collapsing everything into one number.

## Dimensions (so far)

| Dimension | Source | Measure | Coverage |
|---|---|---|---|
| Genealogical | Glottolog 5.3 | Tree distance: `1 − shared lineage / longer lineage`, plus the lowest common ancestor | ~8,200 languages (not pidgins, mixed, artificial or unclassified languages) |
| Lexical | ASJP 21.1 | LDND (Wichmann et al. 2010) on the 40-item ASJP list, with a chance baseline | ~5,450 languages |
| Geographic | Glottolog 5.3 | Great-circle distance between Glottolog's representative points | ~8,200 languages |

Planned: grammatical (Grambank), phonological (PHOIBLE, needing more thought
than inventory overlap).

### Reading the numbers

- **Genealogical distance** is structural, not a date. Glottolog subgroups some
  families much more finely than others, so 0.3 in Romance and 0.3 in Bantu
  don't mean the same time depth. The common ancestor is often the more
  useful thing to show.
- **LDND** is ~0 for identical word lists and ~1.0 for unrelated languages.
  The `chance` figure is the share of randomly sampled *unrelated* pairs
  (no common Glottolog ancestor) that are at least as similar. Anything above
  roughly 1% is indistinguishable from coincidence. LDND detects shallow
  relationships well and deep ones poorly: English–Hindi only just clears
  chance.
- **Nearest lexical neighbours** of isolates and distant outliers are just the
  luckiest unrelated lists (Basque's are scattered Austronesian and Papuan
  languages at ~0.91). The website should say so rather than present them.

### Known caveats

- ASJP often has several lists per language from different transcribers, and
  results can move noticeably depending on which is used (Hindi–Urdu is 0.26
  with one Hindi list and 0.38 with another). We pick one per language: the
  list whose name marks the standard variety, if near-complete, otherwise the
  fullest. Averaging over lists is a likely improvement.
- Geographic points are single coordinates, so colonial and diaspora languages
  look far apart (Afrikaans–Dutch: ~9,400 km).

## Usage

```bash
pip install -e '.[dev]'
glossodesy fetch                       # clone the pinned datasets into data/raw/
glossodesy compare nld,deu spa,por jpn,kor
glossodesy neighbours nld eus -k 10    # nearest by LDND
glossodesy neighbours eus -d geographic
glossodesy build                       # JSON for the website, into data/build/
```

Languages can be given as Glottocodes, ISO 639-3 codes or exact Glottolog names.

## Data and licences

Upstream data is pinned in `src/glossodesy/sources.py`. Both sources are
CC-BY 4.0; please cite them:

- Hammarström, Harald, Robert Forkel, Martin Haspelmath & Sebastian Bank.
  *Glottolog 5.3*. Leipzig: Max Planck Institute for Evolutionary Anthropology.
- Wichmann, Søren, Eric W. Holman & Cecil H. Brown (eds.). *The ASJP Database*
  (version 21.1).

Method reference: Wichmann, S., Holman, E. W., Bakker, D. & Brown, C. H. (2010).
Evaluating linguistic distance measures. *Physica A* 389: 3632–3639.
