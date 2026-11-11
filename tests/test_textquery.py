"""Chapter 19: a language model writes the SPARQL. Every model answer comes
from llm-cache/, so these tests call no model and cost nothing."""

import pytest

from tarnwick import textquery as tq
from tarnwick.build import build

ROOT = tq.ROOT
FIRST_MAP = (ROOT / "stages" / "ch19" / "first-map.txt").read_text(encoding="utf-8").rstrip("\n")


@pytest.fixture(autouse=True)
def no_spending(monkeypatch):
    monkeypatch.setenv("TARNWICK_LLM_BUDGET", "0")


def test_the_map_lists_every_property_with_its_ends():
    m = tq.ontology_map()
    assert "tw:partOf (tw:Place -> tw:Place) [transitive]" in m
    assert "tw:complaintAbout (tw:SupportTicket -> tw:Product) [also implies tw:mentions]" in m
    assert "Customers, orders, order lines" in m and "Every thing has" not in m


def test_the_checks():
    ok = "SELECT ?r WHERE { place:BEND tw:partOf ?r }"
    assert tq.check(ok) == []
    assert tq.check("SELECT ?t WHERE { ?t a tw:Tent }") == [
        "tw:Tent is not a term in the ontology."]
    assert tq.check("SELECT ?r WHERE { place:NOWHERE tw:partOf ?r }") == [
        "place:NOWHERE is not a thing in the graph."]
    assert tq.check("SELECT ?x WHERE { ?x")[0].startswith("It does not parse")
    assert tq.check("DELETE WHERE { ?s ?p ?o }")[0].startswith("It does not parse")


def test_answers_match_by_code_or_name():
    ds = build()[0]
    assert tq.same_answer([("TW-S202", "Recall Policy")],
                          [("Insulated Air Mat", "Recall Policy")], ds)
    assert not tq.same_answer([("TW-S202",)], [("TW-S202",), ("TW-S101",)], ds)


def test_a_slow_query_is_stopped():
    slow = """SELECT (COUNT(*) AS ?n) WHERE { ?a ?p ?b . ?c ?q ?d . ?e ?r ?f }"""
    with pytest.raises(tq.TooSlow):
        tq.run(slow, seconds=1)


def test_the_false_map_line_costs_the_customers():
    q = tq.BENCH[11]
    *_, final, left = tq.attempt(q, map_text=FIRST_MAP)
    assert not left and "rdfs:label ?customerLabel" in final
    assert tq.run(final)[1] == []


def test_the_bench_score():
    assert tq.bench().splitlines()[-1] == "22 of 28 right, 5 wrong, 1 too slow, 0 not run."
