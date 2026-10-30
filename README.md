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
| Geographic | Glottography (Asher & Moseley 2007 atlas); LinguaMeta, Glottolog | Gap between the areas where each language is traditionally spoken, at their closest (or overlapping / adjacent); a single approximate place where the atlas has no area | ~4,400 languages with areas, ~7,150 in all |

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
- **Where a language is traditionally spoken.** LinguaMeta has a point for
  each country a language is spoken in. Each language is represented by one:
  where it is traditionally spoken (not where it originated, which for English
  would be northern Germany). The website rounds these distances and
  highlights an approximate area rather than a dot. Most languages have only one point; for the ~50 with several,
  we take the one in the country Glottolog's coordinate falls in (English in
  Great Britain, Spanish in Spain, Portuguese in Portugal), else the nearest
  to it, else the country with most speakers. Diaspora and colonial languages
  still look far apart (Afrikaans–Dutch: ~9,500 km).
- **Language areas** come from Glottography's digitisation of Asher & Moseley's
  *Atlas of the World's Languages* (2007), "traditional" version: areas at the
  time of contact for the Americas and Australia, the atlas's contemporary
  areas elsewhere. They cover ~4,400 of LinguaMeta's languages; some major
  national languages (Indonesian, Punjabi, Filipino) have no area and fall back
  to a single place. The atlas sometimes includes minority communities (Korean
  pockets in Japan), so areas reflect its editors' choices. Simplified to ~2 km
  for the web; two areas count as overlapping only where one reaches more than
  10 km inside the other, and as adjacent within 25 km.
- **Missing points.** LinguaMeta has no point for ~1,000 languages. All of them
  had Glottolog points when LinguaMeta was built, and those points are less
  reliable than the ones LinguaMeta kept: about 23% fall outside every country
  LinguaMeta lists for the language, against 4% for the kept ones. So we use
  Glottolog's point only when it lands in one of the language's LinguaMeta
  countries, which recovers ~700 languages. Countries are judged by nearest
  populated place, which can misjudge points near borders and on small islands.

## Usage

```bash
pip install -e '.[dev]'
glossodesy fetch                       # clone the pinned datasets into data/raw/
glossodesy compare nl,de es,pt ja,ko
glossodesy neighbours nl eu -k 10      # nearest by LDND
glossodesy neighbours eu -d geographic
glossodesy build                       # JSON for the website, into data/build/
```

Languages can be given as BCP-47 codes, ISO 639-3 codes, glottocodes, exact English names, or
other English names LinguaMeta records (Cantonese, Sorani, Flemish); the website searches these too.

The website shows each ASJP word with its spelling in the language's own
writing system where NorthEuraLex (107 languages, mostly northern Eurasia) has
the same word. NorthEuraLex's IPA is converted roughly to ASJP symbols and
compared by broad sound classes, accepting a stem match for citation forms
(Turkish *gelmek* for ASJP *gel*); about 91% of words match, and unmatched
ones are left without a spelling rather than risk showing a different word.

## Website

`site/index.html` is a static page that reads the JSON from `glossodesy build`.
Compare two languages at `#nl-de`, or see one language's nearest neighbours at
`#nl`. Pairwise numbers are computed in the browser (and match the Python
package); nearest-neighbour lists are precomputed.

To run it locally:

```bash
glossodesy build --out site/data
python -m http.server -d site 8000      # then open http://localhost:8000
```

Above the scales, a sentence gives context from LinguaMeta: speaker numbers,
then only what the pair shares. That covers the scripts both are usually
written in (or, for closely related languages, the scripts that divide them,
as with Hindi and Urdu), and the countries both are spoken in and official
in. These are facts about the pair, not distances, so they aren't scored.

The map highlights the other countries where each language is spoken today,
zooming out to include them all, and hatches
Natural Earth's disputed areas (Kashmir, Aksai Chin, Crimea…) rather than
assigning them to a claimant. `scripts/make_map_assets.py` builds the
country-code table and disputed-areas layer in `site/assets/map-extra.json`.

`.github/workflows/pages.yml` builds the data and deploys the site to GitHub
Pages on every push to `main`.

## Data and licences

Upstream data is pinned in `src/glossodesy/sources.py`. LinguaMeta is
CC BY-SA 4.0, so the files written by `glossodesy build` are too. Glottolog,
ASJP and NorthEuraLex are CC BY 4.0. Please cite them:

- Ritchie, Sandy, Daan van Esch, Uche Okonkwo, Shikhar Vashishth & Emily
  Drummond. 2024. LinguaMeta: Unified metadata for thousands of languages.
  *Proceedings of LREC-COLING 2024*, 10530–10538.
- Asher, R. E. & Christopher J. Moseley (eds.). 2007. *Atlas of the World's
  Languages*. 2nd edn. Routledge. Digitised by Glottography
  (https://doi.org/10.5281/zenodo.15287257), CC BY 4.0.
- Hammarström, Harald, Robert Forkel, Martin Haspelmath & Sebastian Bank.
  *Glottolog 5.3*. Leipzig: Max Planck Institute for Evolutionary Anthropology.
- Wichmann, Søren, Eric W. Holman & Cecil H. Brown (eds.). *The ASJP Database*
  (version 21.1).
- Dellert, Johannes, Thora Daneyko, Alla Münch et al. 2020. NorthEuraLex
  (version 0.9). *Language Resources and Evaluation*.
  https://doi.org/10.1007/s10579-019-09480-6

Method reference: Wichmann, S., Holman, E. W., Bakker, D. & Brown, C. H. (2010).
Evaluating linguistic distance measures. *Physica A* 389: 3632–3639.
