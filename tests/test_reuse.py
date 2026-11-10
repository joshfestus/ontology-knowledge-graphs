"""Reuse in Chapter 11."""

from pathlib import Path

from rdflib.namespace import DCTERMS

from tarnwick.build import build, run_query
from tarnwick.reason import load_for, run

ROOT = Path(__file__).resolve().parents[1]
CH11 = ROOT / "stages" / "ch11"
SCHEMA = "https://schema.org/"


def test_mappings_add_schema_terms():
    new, errors = run(load_for([CH11 / "mappings.ttl"], data=True), (SCHEMA,))
    assert errors == []
    assert sum(1 for t in new if str(t[1]) == SCHEMA + "sku") == 49


def test_same_as_merges_and_exact_match_does_not():
    assert len(run(load_for([CH11 / "same-as.ttl"], data=True))[1]) == 3
    assert run(load_for([CH11 / "exact-match.ttl"], data=True))[1] == []


def test_sources_are_things_not_text():
    ds = build()[0]
    sources = list(ds.objects(None, DCTERMS.source))
    assert sources and all(not hasattr(o, "language") for o in sources)
    _, rows = run_query(CH11 / "sources.rq")
    assert len(rows) == len({r[0] for r in rows}) == 19


def test_schema_org_is_always_https():
    for folder in ("ontology", "stages", "queries"):
        for path in (ROOT / folder).rglob("*"):
            if path.suffix in (".ttl", ".rq"):
                assert "http://schema.org" not in path.read_text(encoding="utf-8"), path
