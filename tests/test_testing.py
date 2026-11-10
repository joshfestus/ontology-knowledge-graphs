"""The testing tools in Chapter 12."""

from pathlib import Path

from tarnwick.coverage import report as coverage_report
from tarnwick.coverage import unused
from tarnwick.pitfalls import check, load, pitfalls_report
from tarnwick.validate import validate_report

ROOT = Path(__file__).resolve().parents[1]
CH12 = ROOT / "stages" / "ch12"


def codes(path=None):
    return {code for code, _, _ in check(load(path))}


def test_sample_products_fail_four_ways():
    r = validate_report([CH12 / "products-sample.ttl"], CH12 / "product-shape.ttl")
    assert "Problems: 4" in r
    for kind in ("missing", "too many values", "not an allowed value", "wrong pattern"):
        assert kind in r


def test_tent_constraint_follows_the_taxonomy():
    r = validate_report([CH12 / "tents-sample.ttl"], CH12 / "tent-shape.ttl")
    assert "Problems: 1" in r and "prod:TW-T201" in r and "TW-A101" not in r


def test_full_data_has_the_two_planted_problems():
    r = validate_report()
    assert "Checked 1,896 things" in r and "Problems: 2" in r
    assert "order:O-00209" in r and "prod:TW-A107" in r


def test_pitfalls_before_and_after():
    assert codes(CH12 / "tarnwick-before.ttl") == {"P11", "P13", "P41"}
    assert codes() == {"P11", "P13"}
    p11 = next(items for code, _, items in check(load()) if code == "P11")
    assert p11 == ["tw:product", "tw:quantity", "tw:text"]


def test_coverage_and_reports_fit_the_page():
    assert len(unused()) == 27
    for r in (coverage_report(True), pitfalls_report(),
              pitfalls_report(CH12 / "tarnwick-before.ttl")):
        assert max(len(line) for line in r.splitlines()) <= 74
