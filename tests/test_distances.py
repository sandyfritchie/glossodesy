from glossodesy.asjp import Wordlist, _name_match, normalise
from glossodesy.distances import genealogical, geographic, ldnd
from glossodesy.languages import Language, Languages, MacrolanguageError, choose_origin
from glossodesy.linguameta import Point, Record


def lang(code, lineage=None, points=(), scope="LANGUAGE", members=(), name=None):
    rec = Record(code, name or code, None, None, None, scope, None, None, members=members, points=points)
    return Language(code, rec, tuple(lineage) if lineage else None, points, points[0] if points else None)


def test_genealogical_siblings_and_strangers():
    a = lang("a", ["fam", "sub", "a"])
    b = lang("b", ["fam", "sub", "b"])
    c = lang("c", ["other", "c"])
    assert genealogical(a, a).distance == 0
    sib = genealogical(a, b)
    assert sib.common_ancestor == "sub" and 0 < sib.distance < 1
    stranger = genealogical(a, c)
    assert stranger.distance == 1 and stranger.common_ancestor is None


def test_genealogical_not_applicable_without_lineage():
    assert genealogical(lang("a", ["fam", "a"]), lang("p")) is None


def test_origin_follows_glottolog_country_then_nearest_then_speakers():
    gb = Point(52.0, -1.0, "gb", "", 60_000_000)
    us = Point(39.0, -98.0, "us", "", 300_000_000)
    hk = Point(22.3, 114.2, "hk", "", 1_000_000)
    region = Point(-10.0, -60.0, "419", "", 400_000_000)
    pts = (gb, us, hk, region)
    assert choose_origin(pts, (53.0, -2.0), "GB") is gb
    assert choose_origin(pts, (53.0, -2.0), None) is gb  # nearest to Glottolog
    assert choose_origin(pts, None, None) is us  # most speakers, ignoring regions
    assert choose_origin((region,), None, None) is region
    assert choose_origin((), None, None) is None


def test_geographic_uses_origin_points():
    a = lang("a", points=(Point(0, 0, "x", ""),))
    b = lang("b", points=(Point(0, 1, "y", ""),))
    assert 100 < geographic(a, b).km < 120
    assert geographic(a, lang("nowhere")) is None


def test_fallback_point_only_inside_listed_country(monkeypatch):
    from glossodesy import glottolog as gl
    from glossodesy.languages import build

    g = gl.Glottolog(names={}, level={"good1234": "language", "bad1234": "language"}, path={},
                     language_of={"good1234": "good1234", "bad1234": "bad1234"}, category={},
                     coords={"good1234": (1.0, 1.0), "bad1234": (2.0, 2.0)})
    recs = {
        "good": Record("good", "Good", None, None, "good1234", "LANGUAGE", None, None, locales=("aa",)),
        "bad": Record("bad", "Bad", None, None, "bad1234", "LANGUAGE", None, None, locales=("aa",)),
    }
    langs = build(recs, g, geocode=lambda pts: ["AA" if pt == (1.0, 1.0) else "BB" for pt in pts])
    assert langs["good"].origin.source == "GLOTTOLOG_FALLBACK"
    assert langs["bad"].origin is None


def test_resolve_macrolanguage_lists_members():
    langs = Languages(
        sw=lang("sw", scope="MACROLANGUAGE", members=("swh",), name="Swahili"),
        swh=lang("swh", name="Swahili"),
    )
    assert langs.resolve("Swahili").code == "swh"  # name prefers the individual language
    try:
        langs.resolve("sw")
        raise AssertionError("expected MacrolanguageError")
    except MacrolanguageError as e:
        assert "swh" in str(e)


WORDS = {str(i): (w,) for i, w in enumerate(
    "mano pe kabesa ojo nariz boka dente lingua oreja piel sangre weso kwerno arbol oja "
    "pesko perro piojo persona uno dos yo tu nosotros rodilla agua fwego piedra sol "
    "estreya noche monte kamino nombre ver oir morir venir lengua senyo".split())}


def test_ldnd_identical_lists_is_zero():
    w = Wordlist("x", "x", WORDS)
    assert ldnd(w, w).ldnd == 0


def test_ldnd_needs_enough_shared_concepts():
    a = Wordlist("a", "a", dict(list(WORDS.items())[:10]))
    assert ldnd(a, a) is None


def test_ldnd_synonyms_take_closest():
    a = Wordlist("a", "a", {**WORDS, "0": ("xyz", "mano")})
    b = Wordlist("b", "b", WORDS)
    assert ldnd(a, b).ldnd == 0


def test_normalise_strips_asjp_modifiers():
    assert normalise('t"a* k~ ') == "tak"


def test_name_match_prefers_standard_variety():
    assert _name_match("DUTCH", "Dutch", True) > _name_match("BRABANTIC", "Dutch", True)
    assert _name_match("STANDARD_GERMAN", "Standard German", True) == 4
    assert _name_match("ENGLISH", "English", True) > _name_match("ENGLISH_2", "English", True)
    assert _name_match("MANDARIN", "Mandarin Chinese", True) > _name_match("KUNMING_MANDARIN", "Mandarin Chinese", True)
    assert _name_match("NORWEGIAN_NYNORSK_TOTEN", "Norwegian Nynorsk", False) > 0


def test_english_aliases_drop_codes_and_canonical():
    from glossodesy.linguameta import english_aliases
    detail = {"name_data": [
        {"name": "Yue Chinese", "bcp_47_code": "en"}, {"name": "Cantonese", "bcp_47_code": "en"},
        {"name": "Zh-Yue", "bcp_47_code": "en"}, {"name": "Nld", "bcp_47_code": "en"},
        {"name": "cantonais", "bcp_47_code": "fr"}, {"name": "cantonese", "bcp_47_code": "en"},
    ]}
    assert english_aliases(detail, "Yue Chinese") == ("Cantonese",)


def test_resolve_by_alias():
    langs = Languages(yue=lang("yue", name="Yue Chinese"))
    langs["yue"].record.aliases = ("Cantonese",)
    assert langs.resolve("cantonese").code == "yue"


def test_canonical_scripts_skip_romanisations():
    from glossodesy.linguameta import canonical_scripts
    hindi = {"language_script_locale": [
        {"script": {"iso_15924_code": "deva", "is_canonical": True}},
        {"script": {"iso_15924_code": "latn"}},
    ]}
    assert canonical_scripts(hindi) == ("deva",)
    unmarked = {"language_script_locale": [{"script": {"iso_15924_code": "latn"}}]}
    assert canonical_scripts(unmarked) == ("latn",)
