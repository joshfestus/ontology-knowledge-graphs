"""Chapter 16: reading tickets with a language model, and the checks that
decide which readings enter the graph. Every answer comes from llm-cache/,
so these tests call no model and cost nothing."""

import pytest
from rdflib import Graph

from tarnwick import extract
from tarnwick.validate import validate_report

ROOT = extract.ROOT


@pytest.fixture(autouse=True)
def no_spending(monkeypatch):
    monkeypatch.setenv("TARNWICK_LLM_BUDGET", "0")


def test_a_shortened_quote_still_counts_as_the_ticket_words():
    text = extract.plain("Main zip on my jacket separates from the bottom.")
    assert extract.quoted_from("zip ... separates from the bottom", text)
    assert extract.quoted_from("Main zip; the bottom", text)
    assert not extract.quoted_from("zip separates", text)
    assert not extract.quoted_from("the bottom ... Main zip", text)


def test_the_checks_hold_back_three_tickets():
    answers, on_order = extract.everything(), extract.ordered()
    held = {t: extract.checks(t, a, on_order.get(t, set())) for t, a in answers.items()}
    assert {t: f for t, f in held.items() if f} == {
        "T-008": ["words not in ticket"],
        "T-020": ["no product named"],
        "T-027": ["not on the order"]}


def test_every_reading_that_passes_agrees_with_the_key():
    answers, on_order, key = extract.everything(), extract.ordered(), extract.key()
    for t, a in answers.items():
        if not extract.checks(t, a, on_order.get(t, set())):
            assert a["complaint_about"]["sku"] == key[t]["sku"]
            assert a["problem"] == key[t]["problem"]


def test_the_saved_turtle_is_what_extract_writes_now():
    saved = (ROOT / "extracted" / "tickets.ttl").read_text(encoding="utf-8")
    assert saved.strip() == extract.turtle().strip()
    Graph().parse(data=saved, format="turtle")


def test_the_ticket_shape_catches_the_wrong_bag():
    report = validate_report([ROOT / "stages" / "ch16" / "wrong-bag.ttl"], with_data=True)
    assert "is about." in report and "ticket:T-027 tw:complaintAbout: too many" in report


def test_reports_fit_the_page():
    for text in (extract.table(), extract.score(), extract.one("T-027"),
                 extract.one("T-002", free=True), extract.policy("returns.md")):
        assert max(len(line) for line in text.splitlines()) <= 76
