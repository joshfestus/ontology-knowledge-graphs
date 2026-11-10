"""Every competency question, checked two independent ways.

Each test runs the question's SPARQL query against the built graph and
compares the answer with one computed directly from the CSV files in plain
Python, with no RDF involved. If the ontology, the loader or the query is
wrong, the two disagree and the test says where.
"""

import csv
from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal
from itertools import combinations
from pathlib import Path

import pytest

from tarnwick.build import build, run_query

DATA = Path(__file__).resolve().parents[1] / "data"
TODAY = date(2026, 9, 30)


def table(name):
    with open(DATA / name, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


@pytest.fixture(scope="session")
def ds():
    return build()[0]


def answer(ds, q):
    return run_query(q, ds)[1]


# ------------------------------------------------ plain Python helpers

def parents():
    return {r["code"]: r["parent"] for r in table("categories.csv")}


def ancestors(code):
    up, out = parents(), []
    while code:
        out.append(code)
        code = up[code]
    return out


def categories_of():
    out = defaultdict(set)
    for r in table("product_categories.csv"):
        out[r["sku"]].add(r["category"])
    return out


def products():
    return {r["sku"]: r for r in table("products.csv")}


def in_tree(sku, root):
    return any(root in ancestors(c) for c in categories_of()[sku])


def supplier_of():
    """Typed names resolved by hand, as a person reading the file would."""
    by_word = {"brisgate": "SUP-01", "corran": "SUP-02", "mirefield": "SUP-03",
               "wrenmoor": "SUP-04", "quillan": "SUP-05", "tallowmere": "SUP-06"}
    return {sku: by_word[p["supplier"].split()[0].lower()] for sku, p in products().items()}


def suppliers():
    return {r["supplier_id"]: r for r in table("suppliers.csv")}


def orders():
    return {r["order_id"]: r for r in table("orders.csv")}


def lines_by_order():
    out = defaultdict(list)
    for r in table("order_lines.csv"):
        out[r["order_id"]].append(r)
    return out


# ------------------------------------------------------------ the tests

def test_q01_tents_whatever_the_website_calls_them(ds):
    expected = sorted(s for s in products() if in_tree(s, "TENT"))
    got = [r[0] for r in answer(ds, "q01")]
    assert got == expected
    assert "Shelters" in {r[2] for r in answer(ds, "q01")}


def test_q02_more_than_one_category(ds):
    expected = sorted((s, len(c)) for s, c in categories_of().items() if len(c) > 1)
    assert answer(ds, "q02") == expected


def test_q03_supplier_of_each_product(ds):
    sup = suppliers()
    expected = sorted((s, sup[i]["name"]) for s, i in supplier_of().items())
    assert answer(ds, "q03") == expected


def test_q04_current_suppliers(ds):
    expected = sorted(r["name"] for r in suppliers().values() if not r["last_supplied"])
    assert [r[0] for r in answer(ds, "q04")] == expected


def test_q05_on_sale_from_a_dropped_supplier(ds):
    sup, sof = suppliers(), supplier_of()
    expected = sorted(s for s, p in products().items()
                      if p["status"] == "active" and sup[sof[s]]["last_supplied"])
    assert [r[0] for r in answer(ds, "q05")] == expected
    assert expected  # the question must have an answer to teach with


def test_q06_recalled_products_and_buyers(ds):
    recalled = {r["sku"] for r in table("recalls.csv")}
    o = orders()
    expected = sorted({(l["sku"], o[l["order_id"]]["customer_id"])
                       for l in table("order_lines.csv") if l["sku"] in recalled})
    assert answer(ds, "q06") == expected


def test_q07_stock_of_one_product(ds):
    names = {r["store_id"]: r["name"] for r in table("stores.csv")}
    expected = sorted(((names[r["store_id"]], int(r["quantity"]))
                       for r in table("stock.csv")
                       if r["sku"] == "TW-T102" and int(r["quantity"]) > 0),
                      key=lambda t: (-t[1], t[0]))
    assert answer(ds, "q07") == expected


def test_q08_everything_in_camping(ds):
    expected = sorted(s for s in products() if in_tree(s, "CAMP"))
    assert [r[0] for r in answer(ds, "q08")] == expected


def test_q09_every_name_for_packs(ds):
    got = answer(ds, "q09")
    assert got[0] == ("Packs", "preferred")
    assert {r[0] for r in got[1:]} == {"Rucksacks", "Backpacks"}


def test_q10_light_three_season_tents(ds):
    expected = sorted(((s, int(p["weight_g"])) for s, p in products().items()
                       if in_tree(s, "TENT") and int(p["weight_g"]) < 2000
                       and int(p["season_rating"]) >= 3), key=lambda t: t[1])
    assert [(r[0], r[2]) for r in answer(ds, "q10")] == expected


def marketing_active():
    return {o["customer_id"] for o in orders().values()
            if date(2025, 9, 30) < date.fromisoformat(o["order_date"]) <= TODAY}


def finance_active():
    ordered = {o["customer_id"] for o in orders().values()}
    return {c["customer_id"] for c in table("customers.csv")
            if not c["account_closed"] and c["customer_id"] in ordered}


def test_q11_marketing_active(ds):
    assert [r[0] for r in answer(ds, "q11")] == sorted(marketing_active())


def test_q12_finance_and_marketing_differ(ds):
    m, f = marketing_active(), finance_active()
    expected = sorted((c, c in f, c in m) for c in m ^ f)
    assert answer(ds, "q12") == expected
    assert expected


def test_q13_revenue_by_region_last_quarter(ds):
    places = {r["place_id"]: r for r in table("places.csv")}

    def region(town):
        while town and places[town]["kind"] != "region":
            town = places[town]["part_of"]
        return places[town]["name"] if town else "Online"

    store_town = {r["store_id"]: r["town"] for r in table("stores.csv")}
    totals = Counter()
    o = orders()
    for line in table("order_lines.csv"):
        order = o[line["order_id"]]
        if date(2026, 7, 1) <= date.fromisoformat(order["order_date"]) <= TODAY:
            totals[region(store_town[order["store_id"]])] += (
                int(line["quantity"]) * Decimal(line["unit_price_usd"]))
    got = {r[0]: r[1] for r in answer(ds, "q13")}
    assert got == dict(totals)


def test_q14_what_fits_what(ds):
    p = products()
    expected = sorted(((p[r["accessory_sku"]]["name"], p[r["fits_sku"]]["name"])
                       for r in table("fits.csv")), key=lambda t: t[1])
    assert answer(ds, "q14") == expected


def test_q15_down_and_where_it_comes_from(ds):
    sup, sof = suppliers(), supplier_of()
    expected = sorted((s, p["material"], sup[sof[s]]["country"])
                      for s, p in products().items() if "down" in p["material"])
    assert answer(ds, "q15") == expected


def test_q16_one_company_many_spellings(ds):
    sup, typed = suppliers(), defaultdict(set)
    for s, p in products().items():
        typed[sup[supplier_of()[s]]["name"]].add(p["supplier"])
    expected = {k: v for k, v in typed.items() if len(v) > 1}
    got = defaultdict(set)
    for supplier, name in answer(ds, "q16"):
        got[supplier].add(name)
    assert got == expected


def test_q19_policy_for_a_recalled_product(ds):
    assert answer(ds, "q19") == [
        ("TW-S202", "Tarnwick Supply Product Recall Policy", date(2026, 1, 1))]


def test_q20_region_of_a_town(ds):
    assert answer(ds, "q20") == [("Pacific Northwest",)]


def test_q21_same_parent_company(ds):
    sup = suppliers()
    by_parent = defaultdict(set)
    for r in sup.values():
        if r["parent_org"]:
            by_parent[r["parent_org"]].add(r["name"])
    got = answer(ds, "q21")
    assert len(got) == len(by_parent) == 1
    assert set(got[0][1].split(", ")) == by_parent["ORG-01"]


def test_q22_replacements(ds):
    p = products()
    expected = sorted((r["name"], p[r["replaced_by"]]["name"])
                      for r in p.values() if r["status"] == "discontinued")
    assert answer(ds, "q22") == expected


def test_q23_return_window(ds):
    recalled = {r["sku"] for r in table("recalls.csv")}
    rules = {"CAMP": 30, "HIKE": 30, "CLOTH": 30, "CLIMB": 30, "FOOT": 60, "SLEEP": 30}

    def window(sku):
        if sku in recalled:
            return "no limit"
        best = min((ancestors(c).index(r), days)
                    for c in categories_of()[sku]
                    for r, days in rules.items() if r in ancestors(c))
        return str(best[1])

    got = {r[0]: r[1] for r in answer(ds, "q23")}
    assert got == {s: window(s) for s in products()}
    assert len(answer(ds, "q23")) == len(products())


def test_q24_tent_and_its_footprint(ds):
    o, fits = orders(), {r["accessory_sku"]: r["fits_sku"] for r in table("fits.csv")}
    bought = defaultdict(set)
    for line in table("order_lines.csv"):
        bought[o[line["order_id"]]["customer_id"]].add(line["sku"])
    expected = sorted((c, tent) for c, skus in bought.items()
                      for acc, tent in fits.items() if acc in skus and tent in skus)
    assert answer(ds, "q24") == expected


def test_q25_empty_categories(ds):
    used = {a for cats in categories_of().values() for c in cats for a in ancestors(c)}
    labels = {r["code"]: r["label"] for r in table("categories.csv")}
    expected = sorted(labels[c] for c in labels if c not in used)
    assert [r[0] for r in answer(ds, "q25")] == expected


def test_q26_and_q28_validation_finds_the_planted_errors(ds):
    from tarnwick.validate import validate
    conforms, problems = validate(ds)
    assert not conforms
    assert [(p.focus, p.path) for p in problems if p.path] == [("TW-A107", "weightGrams")]
    early = [p for p in problems if "release date" in p.message]
    o, p = orders(), products()
    expected = sorted(l["order_id"] for l in table("order_lines.csv")
                      if o[l["order_id"]]["order_date"] < p[l["sku"]]["release_date"])
    assert [e.focus for e in early] == expected and len(expected) == 1
    assert len(problems) == 2


def test_q27_every_fact_has_a_source(ds):
    got = answer(ds, "q27")
    sources = {r[2] for r in got}
    assert "data/products.csv" in sources
    assert "supplier name matching" in sources
    assert ("suppliedBy", "sup:SUP-01",
            "supplier name matching") in got


def test_q29_store_most_reliant_on_one_supplier(ds):
    sof, sup = supplier_of(), suppliers()
    names = {r["store_id"]: r["name"] for r in table("stores.csv")}
    units, totals = Counter(), Counter()
    for r in table("stock.csv"):
        units[(r["store_id"], sof[r["sku"]])] += int(r["quantity"])
        totals[r["store_id"]] += int(r["quantity"])
    best = max(units, key=lambda k: units[k] / totals[k[0]])
    top = answer(ds, "q29")[0]
    assert (top[0], top[1]) == (names[best[0]], sup[best[1]]["name"])
    assert top[3] == round(100 * units[best] / totals[best[0]])


def test_q30_bought_together(ds):
    pairs = Counter()
    for lines in lines_by_order().values():
        for a, b in combinations(sorted({l["sku"] for l in lines}), 2):
            pairs[(a, b)] += 1
    expected = sorted(pairs.items(), key=lambda kv: (-kv[1], kv[0]))[:10]
    assert [((r[0], r[1]), r[2]) for r in answer(ds, "q30")] == expected


def test_ch05_active_customer_counts():
    from tarnwick.build import run_query
    path = Path(__file__).resolve().parents[1] / "stages" / "ch05" / "active-customers.rq"
    got = run_query(path, build()[0])[1][0]
    m, f = marketing_active(), finance_active()
    assert got == (len(m), len(f), len(m & f), len(m - f), len(f - m)) == (96, 120, 96, 0, 24)
