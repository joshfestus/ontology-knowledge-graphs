"""The Chapter 2 searches, checked against counts made straight from the files."""

import csv
from pathlib import Path

from rdflib import Graph
from rdflib.compare import graph_diff, to_isomorphic

from tarnwick.search import search

ROOT = Path(__file__).resolve().parents[1]


def table(name):
    with open(ROOT / "data" / name, encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def under(root):
    """Category codes at or below root, from categories.csv."""
    parent = {r["code"]: r["parent"] for r in table("categories.csv")}

    def ok(c):
        while c:
            if c == root:
                return True
            c = parent[c]
        return False
    return {c for c in parent if ok(c)}


def products_in(codes):
    return {r["sku"] for r in table("product_categories.csv") if r["category"] in codes}


def count(term, level, tax=None):
    return len(search(term, level, tax)[1])


def test_website_finds_only_its_own_word():
    web = [r for r in table("web_catalogue.csv") if r["web_category"] == "Tents"]
    assert count("tents", "website") == len(web) == 7
    assert count("shelters", "website") == 3


def test_vocabulary_without_a_tree_finds_only_the_exact_category():
    assert count("tents", "vocabulary") == len(products_in({"TENT"})) == 1


def test_taxonomy_finds_everything_beneath():
    assert count("tents", "taxonomy") == len(products_in(under("TENT"))) == 10
    assert count("camping", "taxonomy") == len(products_in(under("CAMP")))
    assert count("shelters", "taxonomy") == 0


def test_thesaurus_knows_the_other_words():
    assert count("shelters", "thesaurus") == len(products_in({"TENT-FAM"})) == 3
    assert count("rucksacks", "thesaurus") == len(products_in(under("PACK"))) == 5
    assert count("rain jackets", "thesaurus") == 3
    assert count("rain jackets", "website") == 0


def test_the_wrong_tree_differs_by_one_fact_and_counts_accessories_as_tents():
    good = Graph().parse(ROOT / "ontology" / "taxonomy.ttl")
    bad_path = ROOT / "stages" / "ch02" / "wrong-tree.ttl"
    _, only_good, only_bad = graph_diff(to_isomorphic(good), to_isomorphic(Graph().parse(bad_path)))
    assert len(only_good) == len(only_bad) == 1
    expected = len(products_in(under("TENT") | under("TENT-ACC")))
    assert count("tents", "taxonomy", bad_path) == expected == 16


def test_no_product_is_listed_twice():
    found = search("camping", "taxonomy")[1]
    assert len(found) == len({sku for sku, _, _ in found})
