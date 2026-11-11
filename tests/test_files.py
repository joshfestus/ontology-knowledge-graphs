"""Checks on the source files themselves, before any question is asked."""

import csv
import re
from pathlib import Path

from rdflib import Graph
from rdflib.namespace import OWL, RDF, RDFS, SKOS

from tarnwick.build import build
from tarnwick.namespaces import TW

ROOT = Path(__file__).resolve().parents[1]
DASHES = re.compile("[‒–—―]")
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿]")


def test_every_ontology_term_has_a_label_and_a_definition():
    g = Graph().parse(ROOT / "ontology" / "tarnwick.ttl")
    kinds = (OWL.Class, OWL.ObjectProperty, OWL.DatatypeProperty)
    terms = {s for k in kinds for s in g.subjects(RDF.type, k)}
    assert len(terms) > 40
    missing = sorted(str(t) for t in terms
                     if (t, RDFS.label, None) not in g or (t, SKOS.definition, None) not in g)
    assert missing == []


def test_every_term_used_in_the_data_is_defined():
    ds = build()[0]
    onto = Graph().parse(ROOT / "ontology" / "tarnwick.ttl")
    triples = list(ds.triples((None, None, None)))
    used = {p for _, p, _ in triples if str(p).startswith(str(TW))}
    used |= {o for _, p, o in triples if p == RDF.type and str(o).startswith(str(TW))}
    undefined = sorted(str(t) for t in used if (t, RDFS.label, None) not in onto)
    assert undefined == []


def test_taxonomy_agrees_with_the_category_file():
    g = Graph().parse(ROOT / "ontology" / "taxonomy.ttl")
    with open(ROOT / "data" / "categories.csv", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    by_code = {str(code): s for s, code in g.subject_objects(SKOS.notation)}
    for r in rows:
        concept = by_code[r["code"]]
        assert str(g.value(concept, SKOS.prefLabel)) == r["label"]
        parent = g.value(concept, SKOS.broader)
        assert (str(g.value(parent, SKOS.notation)) if parent else "") == r["parent"]
        assert g.value(concept, SKOS.definition) is not None


def test_no_dashes_or_emoji_in_anything_a_reader_sees():
    files = [p for d in ("data", "ontology", "queries") for p in (ROOT / d).rglob("*")
             if p.is_file()]
    bad = [f"{p.relative_to(ROOT)}:{n}" for p in files
           for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1)
           if DASHES.search(line) or EMOJI.search(line)]
    assert bad == []


def test_every_typed_supplier_name_was_matched():
    assert build()[1] == []


def test_ticket_answer_key_uses_real_products_and_problem_types():
    g = Graph().parse(ROOT / "ontology" / "taxonomy.ttl")
    problems = {str(s).rsplit("/", 1)[-1] for s in g.subjects(SKOS.inScheme, None)
                if "/problem/" in str(s)}
    with open(ROOT / "data" / "products.csv", encoding="utf-8") as fh:
        skus = {r["sku"] for r in csv.DictReader(fh)}
    with open(ROOT / "tests" / "tickets_key.csv", encoding="utf-8") as fh:
        key = list(csv.DictReader(fh))
    assert len(key) == 28
    for r in key:
        assert r["sku"] in skus
        assert r["also_mentions"] in skus | {""}
        assert r["problem"] in problems
