"""Chapter 22: measuring the model with and without the graph. Every model
answer comes from llm-cache/, so these tests call no model and cost nothing."""

import pytest

from tarnwick import llm, measure
from tarnwick import textquery as tq
from tarnwick.build import build


@pytest.fixture(autouse=True)
def no_spending(monkeypatch):
    monkeypatch.setenv("TARNWICK_LLM_BUDGET", "0")


@pytest.fixture(scope="module")
def ds():
    return build()[0]


def test_a_sku_counts_for_a_name(ds):
    expected = [("Footprint for Backpacking Tent 2P", "Backpacking Tent 2P")]
    assert tq.same_answer(expected, [("TW-A101", "TW-T102")], ds)
    assert tq.same_answer(expected, [("prod:TW-A101", "prod:TW-T102")], ds)
    assert not tq.same_answer(expected, [("TW-A101", "TW-T103")], ds)


def test_a_header_row_is_not_an_answer(ds):
    assert tq.header(("customer_id", "tent_sku"))
    assert not tq.header(("C-0001", "TW-T201"))
    assert not tq.header(("Packs",))
    assert tq.same_answer([("C-0001",)], [("customer_id",), ("C-0001",)], ds)


def test_a_name_inside_a_longer_cell(ds):
    expected = [("sup:SUP-02",)]
    assert tq.same_answer(expected, [("SUP-02 Corran Alloy Works",)], ds)
    # numbers must be whole cells: 3 is not found inside TW-T103
    assert not tq.found({"3"}, {"TW-T103"}, "TW-T103")


def test_numbers_are_written_one_way():
    assert tq.norm("15532.00") == tq.norm(15532) == tq.norm("15532")


def pair_counts():
    """{(sku, sku): orders containing both}, from the CSV file."""
    import csv
    import itertools
    from collections import Counter, defaultdict
    lines = defaultdict(set)
    with open(tq.ROOT / "data" / "order_lines.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            lines[r["order_id"]].add(r["sku"])
    return Counter(p for skus in lines.values()
                   for p in itertools.combinations(sorted(skus), 2))


def test_question_30_accepts_any_tied_pair(ds):
    rows = tq.reference(30, ds)
    assert tq.right(30, rows, ds)
    # swap the last pair kept for a pair below the cut with the same count
    counts = pair_counts()
    below = sorted(p for p, c in counts.items() if c == 3 and p not in rows)
    assert len(below) == 6
    assert tq.right(30, rows[:-1] + [below[0]], ds)
    # a pair bought together only twice is wrong in any place
    assert not tq.right(30, rows[:-1] + [("TW-T101", "TW-T102")], ds)


def test_a_repeat_run_has_its_own_cache_key():
    a = llm.key_for("m", "i", "t", None, 10)
    assert a == llm.key_for("m", "i", "t", None, 10, run=1)
    assert a != llm.key_for("m", "i", "t", None, 10, run=2)


def test_rows_drop_whole_cells_to_fit():
    line = measure.fit(["prod:TW-T105", "Backpacking Tent 3P", "prod:TW-T106",
                        "Backpacking Tent 3P Mk II"], width=60)
    assert line == "prod:TW-T105 | Backpacking Tent 3P | prod:TW-T106 | ..."


def test_question_22_from_the_saved_answers(ds):
    files = [measure.trial(22, "files", r, ds)["right"] for r in (1, 2, 3)]
    graph = [measure.trial(22, "graph", r, ds)["right"] for r in (1, 2, 3)]
    assert files == [True, True, True]
    assert graph == [False, True, True]
