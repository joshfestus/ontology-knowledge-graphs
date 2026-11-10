"""The property reports in Chapter 8."""

from pathlib import Path

from tarnwick.implied import conclusions, implied_report, load, properties_report

ROOT = Path(__file__).resolve().parents[1]
CH08 = ROOT / "stages" / "ch08"


def run(*names, data=False):
    return conclusions(load([CH08 / n for n in names], data=data))


def test_full_data_has_no_contradictions_and_every_class_written():
    facts, types, clashes, wrong, one_value = conclusions(load(data=True))
    assert types == {} and clashes == [] and wrong == [] and one_value == []
    with open(ROOT / "data" / "order_lines.csv", encoding="utf-8") as fh:
        lines = sum(1 for _ in fh) - 1
    with open(ROOT / "data" / "products.csv", encoding="utf-8") as fh:
        products = sum(1 for _ in fh) - 1
    assert len(facts) == lines + products + 3


def test_range_concludes_rather_than_rejects():
    _, types, clashes, _, _ = run("home-town.ttl")
    assert len(types) == 2 and clashes == []
    _, types, clashes, _, _ = run("home-state.ttl")
    assert len(clashes) == 1


def test_quantity_domain_turns_every_stock_level_into_a_contradiction():
    with open(ROOT / "data" / "stock.csv", encoding="utf-8") as fh:
        stock = sum(1 for _ in fh) - 1
    _, _, clashes, _, _ = run("quantity-domain.ttl", data=True)
    assert len(clashes) == stock == 188


def test_one_value_and_different_from():
    *_, one_value = run("two-statuses.ttl")
    declared = {str(s).rsplit("/", 1)[-1]: d for s, _, _, d in one_value}
    assert declared == {"TW-T105": True, "TW-T102": False}


def test_wrong_value_type_and_inverse():
    assert len(run("weight-as-text.ttl")[3]) == 1
    assert len(run("supplied.ttl")[0]) == 2


def test_reports_fit_the_page():
    reports = [properties_report(), properties_report("Order"),
               implied_report(data=True)]
    reports += [implied_report([CH08 / n]) for n in
                ("home-town.ttl", "home-state.ttl", "two-statuses.ttl",
                 "weight-as-text.ttl", "supplied.ttl")]
    for r in reports:
        assert max(len(line) for line in r.splitlines()) <= 74
