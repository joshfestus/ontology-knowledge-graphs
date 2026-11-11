"""The queries written for Chapter 14."""

from pathlib import Path

from tarnwick.build import run_query

CH14 = Path(__file__).resolve().parents[1] / "stages" / "ch14"


def test_discontinued_and_parents():
    _, rows = run_query(CH14 / "discontinued.rq")
    assert len(rows) == 3
    _, rows = run_query(CH14 / "parents.rq")
    assert len(rows) == 6 and sum(1 for r in rows if r[1]) == 2


def test_camping_count_matches_the_tree():
    _, rows = run_query(CH14 / "camping-count.rq")
    assert rows == [(31,)]


def test_path_needs_no_reasoner_but_q20_does():
    _, rows = run_query(CH14 / "region-path.rq", reason=False)
    assert rows == [("Pacific Northwest",)]
    _, rows = run_query("q20", reason=False)
    assert rows == []
