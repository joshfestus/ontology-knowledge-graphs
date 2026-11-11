"""The property graph, GQL subset and algorithms of Chapter 17."""

import csv
from decimal import Decimal
from pathlib import Path

import pytest

from tarnwick.build import run_query
from tarnwick.gql import GQLError, run
from tarnwick.pgraph import property_graph, shortest_path, similar_report

ROOT = Path(__file__).resolve().parents[1]
CH17 = ROOT / "stages" / "ch17"


@pytest.fixture(scope="module")
def pg():
    return property_graph()


def gql(pg, name):
    return run(pg, (CH17 / name).read_text(encoding="utf-8"))[1]


def test_edges_carry_the_order_lines_and_stock(pg):
    with open(ROOT / "data" / "order_lines.csv", encoding="utf-8") as fh:
        lines = sum(1 for _ in fh) - 1
    assert sum(e.type == "CONTAINS" for e in pg.edges) == lines
    assert sum(e.type == "STOCKS" for e in pg.edges) == 188


def test_stock_matches_question_7(pg):
    _, sparql = run_query("q07")
    assert [tuple(r) for r in gql(pg, "stock.gql")] == [tuple(r) for r in sparql]


def test_pairs_match_question_30(pg):
    _, sparql = run_query("q30")
    assert [tuple(r) for r in gql(pg, "pairs.gql")] == [tuple(r) for r in sparql[:5]]


def test_revenue_adds_up_every_line(pg):
    total = Decimal(0)
    with open(ROOT / "data" / "order_lines.csv", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            total += int(r["quantity"]) * Decimal(r["unit_price_usd"])
    assert sum(r[1] for r in gql(pg, "revenue.gql")) == total


def test_reach_counts_distinct_customers(pg):
    rows = dict(gql(pg, "reach.gql"))
    assert rows["Brisgate Textiles Ltd"] == 117 and max(rows.values()) <= 160


def test_path_and_similarity(pg):
    path = shortest_path(pg, "ST-BTV", "ORG-01")
    assert [e.type for _, e, _ in path] == ["STOCKS", "SUPPLIED_BY", "OWNED_BY"]
    assert "TW-A101" in similar_report("TW-T102").splitlines()[4]


def test_unsupported_query_is_reported(pg):
    with pytest.raises(GQLError):
        run(pg, "MATCH (s:Store RETURN s.name")
