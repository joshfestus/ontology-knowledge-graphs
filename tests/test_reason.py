"""The reasoner reports in Chapter 10."""

from pathlib import Path

from rdflib import URIRef

from tarnwick.build import run_query
from tarnwick.namespaces import ID, TW
from tarnwick.reason import load_for, reason_report, run

ROOT = Path(__file__).resolve().parents[1]
CH10 = ROOT / "stages" / "ch10"


def test_full_data_reasons_cleanly():
    new, errors = run(load_for(data=True))
    assert errors == []
    assert sum(1 for t in new if t[1] == TW.partOf) == 23


def test_question_13_needs_the_reasoner():
    _, without = run_query("q13", reason=False)
    _, with_ = run_query("q13")
    assert [r[0] for r in without] == ["Online"]
    assert len(with_) == 5
    assert sum(r[1] for r in without) == sum(r[1] for r in with_)


def test_boulder_chain():
    new, _ = run(load_for([CH10 / "boulder.ttl"]))
    boulder = URIRef(ID["place/BOULDER"])
    ups = {o for s, p, o in new if s == boulder and p == TW.partOf}
    assert ups == {ID["place/MTW"], ID["place/US"]}


def test_and_or_trap():
    _, errors = run(load_for([CH10 / "quantity-both.ttl"], data=True))
    assert len(errors) == 947 + 188
    _, errors = run(load_for([CH10 / "quantity-either.ttl"], data=True))
    assert errors == []


def test_open_world_and_sample():
    assert run(load_for([CH10 / "every-product-supplied.ttl"]))[1] == []
    assert len(run(load_for([CH10 / "supplier-sample.ttl"], data=True))[1]) == 1


def test_reports_fit_the_page():
    for r in (reason_report(data=True),
              reason_report([CH10 / "boulder.ttl"], about="place:BOULDER"),
              reason_report([CH10 / "quantity-both.ttl"], data=True)):
        assert max(len(line) for line in r.splitlines()) <= 74
