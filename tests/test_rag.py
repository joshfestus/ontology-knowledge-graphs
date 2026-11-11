"""Chapter 18: retrieval before answering. Every model answer comes from
llm-cache/, so these tests call no model and cost nothing."""

import pytest

from tarnwick import rag

AIR_MAT = ("I bought an Insulated Air Mat four months ago and it keeps going "
           "flat. Can I return it?")
REFUND = ("I mailed my Leather Hiking Boot Women's back for a refund. How long "
          "does the refund take?")


@pytest.fixture(autouse=True)
def no_spending(monkeypatch):
    monkeypatch.setenv("TARNWICK_LLM_BUDGET", "0")


def test_text_retrieval_misses_the_refund_paragraph_until_four():
    top3 = [t for t, _ in rag.text_retrieve(REFUND, 3)]
    top4 = [t for t, _ in rag.text_retrieve(REFUND, 4)]
    assert not any(t.startswith("Refunds are made") for t in top3)
    assert top4[3].startswith("Refunds are made")


def test_graph_facts_for_the_air_mat_carry_their_sources():
    facts = dict(rag.graph_facts(["TW-S202"]))
    rule = next(t for t in facts if t.startswith("The return rule"))
    assert "30 days" in rule and facts[rule] == ["ontology/policies.ttl"]
    recall = next(t for t in facts if "was recalled on 2026-05-12" in t)
    assert facts[recall] == ["data/recalls.csv", "ontology/policies.ttl"]


def test_footwear_gets_the_footwear_rule():
    rule = next(t for t, _ in rag.graph_facts(["TW-F102"]) if t.startswith("The return rule"))
    assert "footwear return window" in rule and "60 days" in rule


def test_the_check_finds_uncited_sentences_and_unknown_numbers():
    problems, cited = rag.check("Yes. It was recalled [2]. Keep it somewhere dry. See [9].", 4)
    assert cited == [2, 9]
    assert problems == ['no citation: "Keep it somewhere dry."', "cites [9], which was never given"]
    assert rag.check("I cannot tell from the information I have.", 3) == ([], [])


def test_the_three_ways_on_the_air_mat():
    text = rag.report(AIR_MAT, "text")
    assert "I cannot tell" in text
    assert "recalled" in rag.report(AIR_MAT, "graph", show=False)
    both = rag.report(AIR_MAT, "both", show=False)
    assert "any time" in both and "every sentence cites a fact" in both


def test_reports_fit_the_page():
    for r in (rag.report(AIR_MAT, u) for u in ("text", "graph", "both")):
        assert max(len(line) for line in r.splitlines()) <= 76
