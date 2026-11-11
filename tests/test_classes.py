"""The class report in Chapter 7."""

import csv
from pathlib import Path

from rdflib import Graph

from tarnwick.classes import analyse, load, report

ROOT = Path(__file__).resolve().parents[1]
CH07 = ROOT / "stages" / "ch07"


def counts(paths):
    _, _, direct, member, problems = analyse(load(paths))
    g = load(paths)
    name = g.namespace_manager.normalizeUri
    return ({name(c): len(m) for c, m in member.items()},
            {name(c): len(d) for c, d in direct.items()}, problems)


def test_full_tarnwick_counts_match_the_files():
    total, direct, problems = counts([])
    with open(ROOT / "data" / "suppliers.csv", encoding="utf-8") as fh:
        suppliers = len(list(csv.DictReader(fh)))
    with open(ROOT / "data" / "places.csv", encoding="utf-8") as fh:
        places = len(list(csv.DictReader(fh)))
    assert total["tw:Supplier"] == suppliers == 6
    assert total["tw:Organization"] == suppliers + 1
    assert total["tw:Place"] == places and direct.get("tw:Place", 0) == 0
    assert problems == []


def test_walls_catch_the_sample_and_their_absence_does_not():
    _, _, problems = counts([CH07 / "classes.ttl", CH07 / "things.ttl",
                             CH07 / "supplier-sample.ttl"])
    assert len(problems) == 1
    _, _, problems = counts([CH07 / "classes-no-walls.ttl", CH07 / "things.ttl",
                             CH07 / "supplier-sample.ttl"])
    assert problems == []


def test_stage_classes_agree_with_the_ontology():
    onto = Graph().parse(ROOT / "ontology" / "tarnwick.ttl")
    from rdflib.namespace import RDFS
    for s, o in Graph().parse(CH07 / "classes.ttl").subject_objects(RDFS.subClassOf):
        assert (s, RDFS.subClassOf, o) in onto


def test_reports_fit_the_page():
    for files in ([], [CH07 / "classes.ttl", CH07 / "things.ttl"],
                  [CH07 / "tents-as-classes.ttl"]):
        assert max(len(line) for line in report(files).splitlines()) <= 74
