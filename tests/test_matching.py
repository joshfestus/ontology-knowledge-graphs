"""Supplier name matching in Chapter 15."""

from pathlib import Path

from tarnwick.resolve import THRESHOLD, match_report, similarity

CH15 = Path(__file__).resolve().parents[1] / "stages" / "ch15"


def test_close_scores_on_both_sides_of_any_line():
    a = similarity("Wrenmoor Insul.", "Wrenmoor Insulation")
    b = similarity("Brisgate Tents", "Brisgate Textiles Ltd")
    assert b < a < THRESHOLD and a - b < 0.02


def test_worked_example_score():
    assert round(similarity("Brisgate Textile Ltd", "Brisgate Textiles Ltd"), 3) == 0.968


def test_decisions_are_applied():
    r = match_report(decisions=CH15 / "decisions.csv")
    assert "decided by purchasing" in r and "none" in r


def test_reports_fit_the_page():
    for r in (match_report(), match_report(["Wrenmoor Insul.", "BTL"]),
              match_report(decisions=CH15 / "decisions.csv")):
        assert max(len(line) for line in r.splitlines()) <= 74
