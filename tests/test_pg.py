"""The property graph view in Chapter 4."""

from pathlib import Path

from tarnwick.pg import convert, report

CH04 = Path(__file__).resolve().parents[1] / "stages" / "ch04"


def test_files_that_share_an_iri_merge_into_one_node():
    nodes, edges = convert([CH04 / "products.ttl", CH04 / "suppliers.ttl"])
    assert [label for _, label, _ in nodes] == ["Product", "Product", "Supplier"]
    supplier = nodes[2]
    assert ("country", '"United Kingdom"') in supplier[2]
    assert sorted(e[1] for e in edges) == ["FITS", "SUPPLIED_BY", "SUPPLIED_BY"]


def test_an_order_line_is_a_node_of_its_own():
    nodes = convert([CH04 / "purchase.ttl"])[0]
    lines = [n for n in nodes if n[1] == "OrderLine"]
    assert len(lines) == 2
    assert ("quantity", "2") in lines[1][2]


def test_a_second_name_for_the_same_company_splits_it():
    nodes = convert([CH04 / "products.ttl", CH04 / "vendors.ttl"])[0]
    labels = [label for _, label, _ in nodes]
    assert labels.count("Supplier") == 1 and labels.count("Vendor") == 1
    supplier = next(n for n in nodes if n[1] == "Supplier")
    assert supplier[2] == [("iri", "sup:SUP-01")]


def test_reports_fit_the_page():
    for files in ([CH04 / "products.ttl", CH04 / "suppliers.ttl"], [CH04 / "purchase.ttl"],
                  [CH04 / "products.ttl", CH04 / "vendors.ttl"]):
        assert max(len(line) for line in report(files).splitlines()) <= 74
