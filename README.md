# glossodesy

How close are two languages? It depends what you mean. glossodesy measures
language similarity along separate dimensions, each with a stated method and
an honest note on coverage, rather than collapsing everything into one number.

## Languages

Language identity comes from [LinguaMeta](https://github.com/google-research/url-nlp/tree/main/linguameta):
BCP-47 codes (the project's primary key), ISO 639-3 codes, English names and
endonyms, speaker numbers, endangerment status and coordinates. Glottolog and
ASJP are joined to it by glottocode. That gives 7,449 individual languages
plus 62 macrolanguages, which can't be compared directly (Arabic, Chinese,
Swahili…) and instead point to their member languages.

## Dimensions (so far)

| Dimension | Source | Measure | Coverage |
|---|---|---|---|
| Genealogical | Glottolog 5.3 | Tree distance: `1 − shared lineage / longer lineage`, plus the lowest common ancestor | ~7,150 languages (not pidgins, mixed, artificial or unclassified languages) |
| Lexical | ASJP 21.1 | LDND (Wichmann et al. 2010) on the 40-item ASJP list, with a chance baseline | ~5,500 languages |
| Geographic | LinguaMeta | Great-circle distance between LinguaMeta's points (one per country a language is spoken in), using the closest pair | ~6,480 languages |

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
  with one Hindi list and 0.38 with another). We pick one per language: a
  list coded to the exact variety where LinguaMeta points at a dialect-level
  glottocode (Norwegian Nynorsk), otherwise the list whose name best matches
  the language (MANDARIN, not KUNMING_MANDARIN), otherwise the fullest.
  Averaging over lists is a likely improvement.
- Where ASJP has no list for a variety, it falls back to its language's list,
  so two codes can share one (flagged as "same ASJP list"; they're left out of
  each other's neighbour lists).
- Using the closest pair of points means widely spoken languages are "near"
  almost everything: English has points in Hong Kong, India, Singapore and
  more. Which point should represent a language is an open question.

## Usage

```bash
pip install -e '.[dev]'
glossodesy fetch                       # clone the pinned datasets into data/raw/
glossodesy compare nl,de es,pt ja,ko
glossodesy neighbours nl eu -k 10      # nearest by LDND
glossodesy neighbours eu -d geographic
glossodesy build                       # JSON for the website, into data/build/
```

Languages can be given as BCP-47 codes, ISO 639-3 codes, glottocodes or exact English names.

## Data and licences

Upstream data is pinned in `src/glossodesy/sources.py`. LinguaMeta is
CC BY-SA 4.0, so the files written by `glossodesy build` are too. Glottolog
and ASJP are CC BY 4.0. Please cite them:

- Ritchie, Sandy, Daan van Esch, Uche Okonkwo, Shikhar Vashishth & Emily
  Drummond. 2024. LinguaMeta: Unified metadata for thousands of languages.
  *Proceedings of LREC-COLING 2024*, 10530–10538.
- Hammarström, Harald, Robert Forkel, Martin Haspelmath & Sebastian Bank.
  *Glottolog 5.3*. Leipzig: Max Planck Institute for Evolutionary Anthropology.
- Wichmann, Søren, Eric W. Holman & Cecil H. Brown (eds.). *The ASJP Database*
  (version 21.1).

Method reference: Wichmann, S., Holman, E. W., Bakker, D. & Brown, C. H. (2010).
Evaluating linguistic distance measures. *Physica A* 389: 3632–3639.
