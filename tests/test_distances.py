from glossodesy.asjp import Wordlist, _name_match, normalise
from glossodesy.distances import genealogical, ldnd
from glossodesy.glottolog import Language


def lang(gc, path, category="Spoken_L1_Language"):
    return Language(gc, gc, None, category, None, None, None, path[0] if path else None, tuple(path))


def test_genealogical_siblings_and_strangers():
    a = lang("a", ["fam", "sub"])
    b = lang("b", ["fam", "sub"])
    c = lang("c", ["other"])
    assert genealogical(a, a).distance == 0
    sib = genealogical(a, b)
    assert sib.common_ancestor == "sub" and 0 < sib.distance < 1
    stranger = genealogical(a, c)
    assert stranger.distance == 1 and stranger.common_ancestor is None


def test_genealogical_not_applicable_for_pidgins():
    assert genealogical(lang("a", ["fam"]), lang("p", ["pidg"], category="Pidgin")) is None


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
    assert _name_match("STANDARD_GERMAN", "Standard German", True) == 3
    assert _name_match("ENGLISH", "English", True) > _name_match("ENGLISH_2", "English", True)
