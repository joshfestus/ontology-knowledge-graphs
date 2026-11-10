"""The taxonomy commands in Chapter 9."""

import csv
from pathlib import Path

from rdflib import Graph
from rdflib.namespace import SKOS

from tarnwick.namespaces import ID
from tarnwick.search import search
from tarnwick.skos import checks, concepts_in, csv_to_turtle, load, tree_report

ROOT = Path(__file__).resolve().parents[1]
CH09 = ROOT / "stages" / "ch09"
COPIED = (SKOS.prefLabel, SKOS.altLabel, SKOS.notation, SKOS.broader,
          SKOS.inScheme, SKOS.topConceptOf)


def converted(name, tmp_path):
    out = tmp_path / (name + ".ttl")
    out.write_text(csv_to_turtle(CH09 / name), encoding="utf-8")
    return out


def test_stage_spreadsheet_matches_the_product_team_file():
    def rows(p):
        with open(p, encoding="utf-8") as fh:
            return [(r["code"], r["label"], r["parent"]) for r in csv.DictReader(fh)]
    assert rows(CH09 / "categories.csv") == rows(ROOT / "data" / "categories.csv")


def test_conversion_gives_the_finished_taxonomy_less_the_human_work(tmp_path):
    made = Graph().parse(converted("categories.csv", tmp_path))
    full = load([])
    for p in COPIED:
        mine = {t for t in made.triples((None, p, None))}
        keep = concepts_in(full, ID["categories"]) | {ID["categories"]}
        theirs = {t for t in full.triples((None, p, None)) if t[0] in keep}
        assert mine == theirs, p


def test_clean_taxonomy_passes_and_draft_fails_three_ways(tmp_path):
    full = load([])
    assert checks(full, concepts_in(full, ID["categories"])) == []
    draft = load([converted("categories-draft.csv", tmp_path)])
    assert len(checks(draft, concepts_in(draft, ID["categories"]))) == 3


def test_draft_searches_lose_and_mix_products(tmp_path):
    draft = converted("categories-draft.csv", tmp_path)
    assert len(search("sleeping", "taxonomy")[1]) == 8
    assert len(search("sleeping", "taxonomy", draft)[1]) == 5
    assert len(search("insulation", "thesaurus", draft)[1]) == 8


def test_reports_fit_the_page(tmp_path):
    for r in (tree_report(), tree_report([converted("categories-draft.csv", tmp_path)]),
              csv_to_turtle(CH09 / "categories.csv")):
        assert max(len(line) for line in r.splitlines()) <= 74


def test_shipped_conversions_are_what_the_command_writes():
    for csv_name, ttl in (("categories.csv", "categories.ttl"),
                          ("categories-draft.csv", "draft.ttl")):
        shipped = (CH09 / ttl).read_text(encoding="utf-8").rstrip("\n")
        assert shipped == csv_to_turtle(CH09 / csv_name)
