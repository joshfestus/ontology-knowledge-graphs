"""Chapter 21: the semantic layer. Model answers come from llm-cache/, so
these tests call no model and cost nothing."""

from datetime import date

import pytest

from tarnwick import metrics as mt
from tarnwick.build import run_query

CH21 = mt.ROOT / "stages" / "ch21"


@pytest.fixture(autouse=True)
def no_spending(monkeypatch):
    monkeypatch.setenv("TARNWICK_LLM_BUDGET", "0")


def test_every_metric_and_dimension_checks_out():
    ok, text = mt.check()
    assert ok, text
    assert "Requests tried: 8" in text


def test_the_two_definitions_agree_with_questions_11_and_12():
    marketing = mt.compute("active-customers-marketing")[0][1]
    finance = mt.compute("active-customers-finance")[0][1]
    assert (marketing, finance) == (96, 120)
    assert len(run_query("q11")[1]) == marketing
    differ = run_query("q12")[1]
    assert len(differ) == finance - marketing
    assert all(r[1] is True and r[2] is False for r in differ)


def test_revenue_by_region_is_question_13():
    rows = mt.compute("revenue", by="region", period="2026-Q3")
    assert [(g, float(v)) for g, v in rows] == [
        (r, float(v)) for r, v in run_query("q13")[1]]


def test_counts_by_home_region_cover_every_active_customer():
    rows = mt.compute("active-customers-marketing", by="home-region")
    assert sum(v for _, v in rows) == 96


def test_a_term_with_two_definitions_must_be_named():
    with pytest.raises(mt.MetricError, match="has 2 definitions"):
        mt.resolve("active customers")
    assert mt.resolve("sales") == "revenue"
    assert mt.resolve("active customers (finance)") == "active-customers-finance"


def test_requests_the_layer_refuses():
    with pytest.raises(mt.MetricError, match="needs a period"):
        mt.compute("revenue")
    with pytest.raises(mt.MetricError, match="cannot be split by store"):
        mt.compute("active-customers-finance", by="store")
    with pytest.raises(mt.MetricError, match="not a period"):
        mt.period_dates("Q3 2026")


def test_periods():
    assert mt.period_dates("2026-Q3") == (date(2026, 7, 1), date(2026, 9, 30))
    assert mt.period_dates("2026-02") == (date(2026, 2, 1), date(2026, 2, 28))
    assert mt.period_dates("2026") == (date(2026, 1, 1), date(2026, 12, 31))


def test_copies_of_one_definition_disagree():
    rows = dict(run_query(CH21 / "copies.rq")[1])
    assert rows == {"board pack": 95, "campaigns": 96, "stores": 99}


def test_the_model_chooses_and_the_layer_computes():
    assert "unclear" in mt.ask("How many active customers does Tarnwick have?")
    by_region = mt.ask("What was the revenue in each region last quarter?")
    assert "revenue by region, period 2026-Q3" in by_region
    assert "15,532.00" in by_region
    assert "none" in mt.ask("What is our average order value?")


def test_the_answer_to_task_21_3(tmp_path, monkeypatch):
    both = tmp_path / "metrics.ttl"
    both.write_text(mt.METRICS.read_text() + (CH21 / "answers" / "orders.ttl").read_text())
    monkeypatch.setattr(mt, "METRICS", both)
    ok, text = mt.check()
    assert ok and "Requests tried: 10" in text
    orders = mt.compute("orders", period="2026-Q3")[0][1]
    revenue = mt.compute("revenue", period="2026-Q3")[0][1]
    assert orders == 53 and round(float(revenue) / orders, 2) == 293.06


def test_the_answer_to_task_21_4():
    from tarnwick.load import new_dataset
    ds = new_dataset()
    ds.graph().parse(mt.METRICS)
    rows = run_query(CH21 / "answers" / "terms.rq", ds)[1]
    assert rows == [("active customer", 2), ("revenue", 1)]


def test_an_earlier_reporting_date():
    assert mt.compute("active-customers-marketing", as_of="2026-06-30")[0][1] == 98
    assert mt.compute("active-customers-finance", as_of="2026-06-30")[0][1] == 118


def test_the_chapter_21_copy_of_the_definitions_is_current():
    """stages/ch21/metrics.ttl lets Task 21.4 run inside the stage folder; it
    must stay the same as ontology/metrics.ttl."""
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    assert ((root / "stages" / "ch21" / "metrics.ttl").read_bytes()
            == (root / "ontology" / "metrics.ttl").read_bytes())
