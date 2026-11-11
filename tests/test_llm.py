"""The budget guard and cache in llm.py, tested without calling any model."""

import json

import pytest

from tarnwick import llm


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    monkeypatch.setattr(llm, "CACHE", tmp_path)
    monkeypatch.setattr(llm, "LEDGER", tmp_path / "spend.json")
    monkeypatch.setenv("TARNWICK_LLM_MODEL", "gpt-5.6-luna")
    return tmp_path


def test_a_saved_answer_is_returned_without_a_call(sandbox, monkeypatch):
    monkeypatch.setenv("TARNWICK_LLM_BUDGET", "0")
    key = llm.key_for("gpt-5.6-luna", "Be brief.", "Hello", None, 100)
    (sandbox / f"{key}.json").write_text(json.dumps({"answer": "Hi"}))
    assert llm.ask("Be brief.", "Hello", max_output_tokens=100) == "Hi"


def test_a_call_that_could_pass_the_budget_is_refused(sandbox, monkeypatch):
    monkeypatch.setenv("TARNWICK_LLM_BUDGET", "1.00")
    (sandbox / "spend.json").write_text(json.dumps({"total_usd": 0.9999}))
    with pytest.raises(llm.BudgetExceeded):
        llm.ask("Be brief.", "A new question", max_output_tokens=1000)


def test_costs_follow_the_price_table():
    assert llm.cost_of("gpt-5.6-luna", 1_000_000, 0, 0) == pytest.approx(0.20)
    assert llm.cost_of("gpt-5.6-luna", 0, 0, 1_000_000) == pytest.approx(1.20)
    assert llm.cost_of("a-local-model", 10**6, 0, 10**6) == 0.0
