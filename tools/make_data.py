"""Write the Tarnwick Supply source files into data/.

Everything here is invented for the book. The core tables (categories,
products, suppliers, places, stores, recalls) are written out by hand
because readers see them printed. Customers, orders and stock are generated
from a fixed seed so every build produces identical files.

Deliberate problems planted for the chapters to find:
  * the web catalogue calls family tents "Shelters" (Ch 1, Ch 9)
  * supplier names are typed several ways in products.csv (Ch 15)
  * two products sit in two categories (Ch 7)
  * the Climbing and Harnesses categories have no products (Ch 9)
  * one product record has no weight (Ch 12)
  * one order line is dated before its product's release (Ch 12)
  * marketing and finance define "active customer" differently (Ch 21)
"""

import csv
import random
from datetime import date, timedelta
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
AS_OF = date(2026, 9, 30)  # the book's "today" for every dated question
SEED = 20261107


def write(name, header, rows):
    DATA.mkdir(exist_ok=True)
    with open(DATA / name, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)


# code, label used by the product team, parent code
CATEGORIES = [
    ("CAMP", "Camping", ""),
    ("TENT", "Tents", "CAMP"),
    ("TENT-BP", "Backpacking Tents", "TENT"),
    ("TENT-FAM", "Family Tents", "TENT"),
    ("TENT-ACC", "Tent Accessories", "CAMP"),
    ("SLEEP", "Sleeping", "CAMP"),
    ("SLEEP-BAG", "Sleeping Bags", "SLEEP"),
    ("SLEEP-MAT", "Sleeping Mats", "SLEEP"),
    ("KITCHEN", "Camp Kitchen", "CAMP"),
    ("STOVE", "Stoves", "KITCHEN"),
    ("COOK", "Cookware", "KITCHEN"),
    ("REPAIR", "Repair and Care", "CAMP"),
    ("HIKE", "Hiking", ""),
    ("FOOT", "Footwear", "HIKE"),
    ("BOOT", "Hiking Boots", "FOOT"),
    ("SHOE", "Trail Shoes", "FOOT"),
    ("PACK", "Packs", "HIKE"),
    ("PACK-DAY", "Daypacks", "PACK"),
    ("PACK-BP", "Backpacking Packs", "PACK"),
    ("CLOTH", "Clothing", ""),
    ("JACKET", "Jackets", "CLOTH"),
    ("JACKET-WP", "Waterproof Jackets", "JACKET"),
    ("JACKET-INS", "Insulated Jackets", "JACKET"),
    ("BASE", "Base Layers", "CLOTH"),
    ("CLIMB", "Climbing", ""),
    ("HARNESS", "Harnesses", "CLIMB"),
]

# The web team's own category words. Where they differ from the product
# team's, the search on the website misses products.
WEB_LABELS = {
    "TENT-BP": "Tents",
    "TENT-FAM": "Shelters",
    "TENT": "Tents",
    "TENT-ACC": "Tent Extras",
    "SLEEP-BAG": "Sleep Systems",
    "SLEEP-MAT": "Sleep Systems",
    "STOVE": "Cook Systems",
    "COOK": "Cook Systems",
    "REPAIR": "Tent Extras",
    "BOOT": "Boots",
    "SHOE": "Trail Runners",
    "PACK-DAY": "Rucksacks",
    "PACK-BP": "Rucksacks",
    "JACKET-WP": "Hardshells",
    "JACKET-INS": "Insulation",
    "BASE": "Base Layers",
}

SUPPLIERS = [
    # id, legal name, country, first supplied, last supplied, parent id
    ("SUP-01", "Brisgate Textiles Ltd", "United Kingdom", "2019-02-01", "", ""),
    ("SUP-02", "Corran Alloy Works", "Canada", "2020-06-15", "", "ORG-01"),
    ("SUP-03", "Mirefield Down Company", "Poland", "2018-09-01", "2025-06-30", ""),
    ("SUP-04", "Wrenmoor Insulation", "United States", "2024-01-10", "", ""),
    ("SUP-05", "Quillan Packworks Inc.", "United States", "2019-05-20", "", "ORG-01"),
    ("SUP-06", "Tallowmere Footwear", "Portugal", "2021-03-01", "", ""),
]
PARENTS = [("ORG-01", "Lowmoor Holdings", "United States")]

# How the buyers typed each supplier into the product file.
B1, B2, B3 = "Brisgate Textiles", "BRISGATE TEXTILES LTD", "Brisgate Textile Ltd"
C1 = "Corran Alloy Works"
M1, M2 = "Mirefield Down Co.", "Mirefield Down Company"
W1 = "Wrenmoor Insulation"
Q1, Q2 = "Quillan Packworks", "Quillan Pack Works"
T1 = "Tallowmere Footwear"

# sku, name, primary category, supplier as typed, price USD, weight g,
# season rating, release date, status, replaced by, main material
PRODUCTS = [
    ("TW-T101", "Backpacking Tent 1P", "TENT-BP", B1, "189.00", "1150", "3", "2024-03-01", "active", "", "ripstop nylon"),
    ("TW-T102", "Backpacking Tent 2P", "TENT-BP", B1, "249.00", "1640", "3", "2024-03-01", "active", "", "ripstop nylon"),
    ("TW-T103", "Ultralight Tent 2P", "TENT-BP", B2, "389.00", "980", "3", "2025-04-15", "active", "", "ripstop nylon"),
    ("TW-T104", "Winter Tent 2P", "TENT-BP", B1, "529.00", "2900", "4", "2024-10-01", "active", "", "ripstop nylon"),
    ("TW-T105", "Backpacking Tent 3P", "TENT-BP", B3, "319.00", "2150", "3", "2023-03-01", "discontinued", "TW-T106", "ripstop nylon"),
    ("TW-T106", "Backpacking Tent 3P Mk II", "TENT-BP", B1, "339.00", "1990", "3", "2025-03-01", "active", "", "ripstop nylon"),
    ("TW-T201", "Family Tent 4P", "TENT-FAM", B1, "399.00", "7800", "3", "2024-04-01", "active", "", "polyester"),
    ("TW-T202", "Family Tent 6P", "TENT-FAM", B2, "549.00", "11200", "3", "2024-04-01", "active", "", "polyester"),
    ("TW-T203", "Cabin Tent 8P", "TENT-FAM", B1, "699.00", "16500", "3", "2025-05-01", "active", "", "polyester"),
    ("TW-T204", "Pop Up Festival Tent 2P", "TENT", B1, "89.00", "2400", "2", "2025-05-15", "active", "", "polyester"),
    ("TW-A101", "Footprint for Backpacking Tent 2P", "TENT-ACC", B1, "49.00", "210", "", "2024-03-01", "active", "", "polyethylene"),
    ("TW-A102", "Footprint for Family Tent 4P", "TENT-ACC", B1, "69.00", "640", "", "2024-04-01", "active", "", "polyethylene"),
    ("TW-A103", "Footprint for Family Tent 6P", "TENT-ACC", B2, "79.00", "820", "", "2024-04-01", "active", "", "polyethylene"),
    ("TW-A104", "Aluminum Tent Stakes (12)", "TENT-ACC", C1, "24.00", "160", "", "2023-01-15", "active", "", "aluminum alloy"),
    ("TW-A105", "Tent Repair Kit", "TENT-ACC", B1, "19.00", "90", "", "2023-01-15", "active", "", "ripstop nylon"),
    ("TW-A106", "Footprint for Ultralight Tent 2P", "TENT-ACC", B2, "59.00", "150", "", "2025-04-15", "active", "", "polyethylene"),
    ("TW-A107", "Seam Sealer", "REPAIR", B1, "12.00", "", "", "2023-01-15", "active", "", "silicone"),
    ("TW-S101", "Down Sleeping Bag 20F", "SLEEP-BAG", M1, "279.00", "980", "", "2023-09-01", "discontinued", "TW-S104", "goose down"),
    ("TW-S102", "Down Sleeping Bag 0F", "SLEEP-BAG", M2, "419.00", "1450", "", "2023-09-01", "active", "", "goose down"),
    ("TW-S103", "Synthetic Sleeping Bag 30F", "SLEEP-BAG", W1, "129.00", "1300", "", "2024-08-01", "active", "", "synthetic insulation"),
    ("TW-S104", "Down Sleeping Bag 20F Mk II", "SLEEP-BAG", W1, "299.00", "940", "", "2025-08-01", "active", "", "duck down"),
    ("TW-S105", "Down Sleeping Bag 0F Mk II", "SLEEP-BAG", W1, "439.00", "1400", "", "2025-08-01", "active", "", "duck down"),
    ("TW-S201", "Self Inflating Mat", "SLEEP-MAT", W1, "89.00", "1100", "", "2024-03-01", "active", "", "polyester"),
    ("TW-S202", "Insulated Air Mat", "SLEEP-MAT", W1, "149.00", "520", "", "2024-03-01", "recalled", "", "nylon"),
    ("TW-S203", "Closed Cell Foam Mat", "SLEEP-MAT", Q1, "39.00", "410", "", "2023-01-15", "active", "", "polyethylene foam"),
    ("TW-K101", "Canister Stove", "STOVE", C1, "59.00", "85", "", "2023-01-15", "active", "", "aluminum alloy"),
    ("TW-K102", "Integrated Stove System", "STOVE", C1, "139.00", "450", "", "2024-05-01", "active", "", "aluminum alloy"),
    ("TW-K103", "Liquid Fuel Stove", "STOVE", C1, "159.00", "390", "", "2023-01-15", "active", "", "stainless steel"),
    ("TW-K201", "Titanium Pot 750 ml", "COOK", C1, "49.00", "105", "", "2023-01-15", "active", "", "titanium"),
    ("TW-K202", "Cook Set 2P", "COOK", C1, "69.00", "420", "", "2023-01-15", "active", "", "aluminum alloy"),
    ("TW-K203", "Camp Kettle 1 L", "COOK", C1, "35.00", "230", "", "2024-05-01", "active", "", "aluminum alloy"),
    ("TW-P101", "Daypack 22 L", "PACK-DAY", Q1, "89.00", "620", "", "2023-01-15", "active", "", "nylon"),
    ("TW-P102", "Daypack 30 L", "PACK-DAY", Q2, "109.00", "780", "", "2023-01-15", "active", "", "nylon"),
    ("TW-P201", "Backpacking Pack 50 L", "PACK-BP", Q1, "229.00", "1500", "", "2023-03-01", "active", "", "nylon"),
    ("TW-P202", "Backpacking Pack 65 L", "PACK-BP", Q2, "269.00", "1850", "", "2023-03-01", "active", "", "nylon"),
    ("TW-P203", "Backpacking Pack 40 L Women's Fit", "PACK-BP", Q1, "219.00", "1350", "", "2024-03-01", "active", "", "nylon"),
    ("TW-F101", "Leather Hiking Boot Men's", "BOOT", T1, "229.00", "1300", "", "2023-03-01", "active", "", "leather"),
    ("TW-F102", "Leather Hiking Boot Women's", "BOOT", T1, "229.00", "1150", "", "2023-03-01", "active", "", "leather"),
    ("TW-F103", "Winter Hiking Boot", "BOOT", T1, "279.00", "1600", "", "2024-10-01", "active", "", "leather"),
    ("TW-F201", "Trail Running Shoe", "SHOE", T1, "149.00", "620", "", "2024-03-01", "active", "", "mesh"),
    ("TW-F202", "Waterproof Hiking Shoe", "SHOE", T1, "169.00", "780", "", "2024-03-01", "active", "", "mesh"),
    ("TW-C101", "Waterproof Jacket Men's", "JACKET-WP", B1, "249.00", "420", "", "2023-09-01", "active", "", "polyester"),
    ("TW-C102", "Waterproof Jacket Women's", "JACKET-WP", B1, "249.00", "380", "", "2023-09-01", "active", "", "polyester"),
    ("TW-C103", "Packable Rain Shell", "JACKET-WP", B3, "159.00", "230", "", "2024-03-01", "active", "", "nylon"),
    ("TW-C201", "Down Insulated Jacket", "JACKET-INS", M1, "249.00", "390", "", "2023-09-01", "discontinued", "TW-C203", "goose down"),
    ("TW-C202", "Synthetic Insulated Jacket", "JACKET-INS", W1, "189.00", "450", "", "2024-09-01", "active", "", "synthetic insulation"),
    ("TW-C203", "Down Insulated Jacket Mk II", "JACKET-INS", W1, "269.00", "360", "", "2025-09-01", "active", "", "duck down"),
    ("TW-C301", "Merino Base Layer Top", "BASE", B1, "89.00", "210", "", "2023-09-01", "active", "", "merino wool"),
    ("TW-C302", "Merino Base Layer Leggings", "BASE", B1, "79.00", "190", "", "2023-09-01", "active", "", "merino wool"),
]

# Products listed in a second category as well as their primary one.
EXTRA_CATEGORIES = [("TW-K102", "COOK"), ("TW-A105", "REPAIR")]

# accessory sku, the product it fits
FITS = [
    ("TW-A101", "TW-T102"),
    ("TW-A102", "TW-T201"),
    ("TW-A103", "TW-T202"),
    ("TW-A106", "TW-T103"),
]

# place id, name, kind, part of
PLACES = [
    ("US", "United States", "country", ""),
    ("MTW", "Mountain West", "region", "US"),
    ("PNW", "Pacific Northwest", "region", "US"),
    ("SE", "Southeast", "region", "US"),
    ("NE", "Northeast", "region", "US"),
    ("CO", "Colorado", "state", "MTW"),
    ("OR", "Oregon", "state", "PNW"),
    ("WA", "Washington", "state", "PNW"),
    ("NC", "North Carolina", "state", "SE"),
    ("VT", "Vermont", "state", "NE"),
    ("BOULDER", "Boulder", "town", "CO"),
    ("DENVER", "Denver", "town", "CO"),
    ("BEND", "Bend", "town", "OR"),
    ("PORTLAND", "Portland", "town", "OR"),
    ("SEATTLE", "Seattle", "town", "WA"),
    ("ASHEVILLE", "Asheville", "town", "NC"),
    ("CHARLOTTE", "Charlotte", "town", "NC"),
    ("BURLINGTON", "Burlington", "town", "VT"),
    ("MONTPELIER", "Montpelier", "town", "VT"),
]

STORES = [
    ("ST-BOU", "Tarnwick Boulder", "BOULDER", "2019-04-01"),
    ("ST-BND", "Tarnwick Bend", "BEND", "2020-05-01"),
    ("ST-AVL", "Tarnwick Asheville", "ASHEVILLE", "2021-03-15"),
    ("ST-BTV", "Tarnwick Burlington", "BURLINGTON", "2022-06-01"),
    ("ST-WEB", "Tarnwick Online", "", "2019-04-01"),
]

RECALLS = [
    ("R-2026-01", "TW-S202", "2026-05-12",
     "The inflation valve can separate from the mat, which then deflates during use.",
     "Full refund or a replacement mat, at the customer's choice."),
]


def build_customers(rng):
    towns = [p[0] for p in PLACES if p[2] == "town"]
    rows = []
    for i in range(1, 161):
        opened = date(2019, 4, 1) + timedelta(days=rng.randrange(0, 2300))
        closed = ""
        if rng.random() < 0.12:
            c = opened + timedelta(days=rng.randrange(120, 900))
            if c < AS_OF:
                closed = c.isoformat()
        rows.append((f"C-{i:04d}", rng.choice(towns), opened.isoformat(), closed,
                     "yes" if rng.random() < 0.6 else "no"))
    return rows


def sellable(sku_row, day):
    release = date.fromisoformat(sku_row[7])
    if day < release:
        return False
    if sku_row[8] == "discontinued" and sku_row[9]:
        replacement = next(p for p in PRODUCTS if p[0] == sku_row[9])
        if day >= date.fromisoformat(replacement[7]):
            return False
    return not (sku_row[8] == "recalled" and day >= date.fromisoformat(RECALLS[0][2]))


def build_orders(rng, customers):
    home_store = {"CO": "ST-BOU", "OR": "ST-BND", "WA": "ST-BND",
                  "NC": "ST-AVL", "VT": "ST-BTV"}
    state_of = {p[0]: p[3] for p in PLACES if p[2] == "town"}
    orders, lines = [], []
    start, end = date(2024, 1, 1), AS_OF
    n = 0
    for cust in customers:
        opened = date.fromisoformat(cust[2])
        closed = date.fromisoformat(cust[3]) if cust[3] else None
        first = max(opened, start)
        last = min(closed, end) if closed else end
        if first >= last:
            continue
        for _ in range(rng.randrange(0, 9)):
            day = first + timedelta(days=rng.randrange(0, (last - first).days + 1))
            store = "ST-WEB" if rng.random() < 0.35 else home_store[state_of[cust[1]]]
            pool = [p for p in PRODUCTS if sellable(p, day)]
            picks = rng.sample(pool, k=min(len(pool), rng.choice([1, 1, 1, 2, 2, 3])))
            # tent buyers often add the footprint that fits
            for acc, tent in FITS:
                if any(p[0] == tent for p in picks) and rng.random() < 0.5:
                    acc_row = next(p for p in PRODUCTS if p[0] == acc)
                    if sellable(acc_row, day) and acc_row not in picks:
                        picks.append(acc_row)
            n += 1
            oid = f"O-{n:05d}"
            orders.append((oid, cust[0], store, day.isoformat()))
            for p in picks:
                qty = 1 if p[2] not in ("TENT-ACC", "COOK", "BASE") else rng.choice([1, 1, 2])
                lines.append((oid, p[0], qty, p[4]))
    # Planted error for Chapter 12: an order for the Ultralight Tent dated
    # five weeks before its release, by a customer whose account was open.
    planted_customer = next(
        c for c in customers
        if c[2] < "2025-01-01" and (not c[3] or c[3] > "2025-06-01"))
    n += 1
    orders.append((f"O-{n:05d}", planted_customer[0], "ST-WEB", "2025-03-10"))
    lines.append((f"O-{n:05d}", "TW-T103", 1, "389.00"))
    # Number orders in date order, as a real order system would.
    orders.sort(key=lambda o: (o[3], o[0]))
    new_id = {o[0]: f"O-{i:05d}" for i, o in enumerate(orders, 1)}
    orders = [(new_id[o[0]],) + o[1:] for o in orders]
    lines = sorted(((new_id[l[0]],) + l[1:] for l in lines), key=lambda l: l[0])
    return orders, lines


def build_stock(rng):
    rows = []
    for store in STORES:
        for p in PRODUCTS:
            if p[8] != "active":
                continue
            if store[0] != "ST-WEB" and rng.random() < 0.25:
                continue
            qty = rng.randrange(0, 40 if store[0] == "ST-WEB" else 15)
            rows.append((store[0], p[0], qty))
    return rows


def write_tickets(rng, orders, lines):
    """Give each ticket to a customer who really bought the product, dated
    after the purchase. The answer key goes to tests/, not data/."""
    from tickets import TICKETS

    order_by_id = {o[0]: o for o in orders}
    drafts = []
    for n, (sku, other, problem, text, *after) in enumerate(TICKETS):
        buyers = sorted({order_by_id[l[0]] for l in lines if l[1] == sku},
                        key=lambda o: o[0])
        order = rng.choice(buyers)
        day = date.fromisoformat(order[3]) + timedelta(days=rng.randrange(2, 60))
        day = min(day, AS_OF)
        if after:  # a ticket that mentions the recall arrives after it
            day = max(day, date.fromisoformat(after[0]) + timedelta(days=rng.randrange(1, 20)))
        drafts.append((day.isoformat(), n, order, sku, other, problem, text))
    drafts.sort()
    rows, key = [], []
    for i, (day, _n, order, sku, other, problem, text) in enumerate(drafts, 1):
        tid = f"T-{i:03d}"
        rows.append((tid, day, order[1], order[0], text))
        key.append((tid, sku, other, problem))
    write("tickets.csv", ["ticket_id", "received", "customer_id", "order_id", "text"], rows)
    out = DATA.parent / "tests" / "tickets_key.csv"
    out.parent.mkdir(exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["ticket_id", "sku", "also_mentions", "problem"])
        w.writerows(sorted(key))


def main():
    rng = random.Random(SEED)
    write("categories.csv", ["code", "label", "parent"], CATEGORIES)
    write("web_catalogue.csv", ["sku", "web_category"],
          [(p[0], WEB_LABELS[p[2]]) for p in PRODUCTS])
    write("suppliers.csv",
          ["supplier_id", "name", "country", "first_supplied", "last_supplied", "parent_org"],
          SUPPLIERS)
    write("organizations.csv", ["org_id", "name", "country"], PARENTS)
    write("products.csv",
          ["sku", "name", "category", "supplier", "price_usd", "weight_g",
           "season_rating", "release_date", "status", "replaced_by", "material"],
          PRODUCTS)
    write("product_categories.csv", ["sku", "category"],
          [(p[0], p[2]) for p in PRODUCTS] + EXTRA_CATEGORIES)
    write("fits.csv", ["accessory_sku", "fits_sku"], FITS)
    write("places.csv", ["place_id", "name", "kind", "part_of"], PLACES)
    write("stores.csv", ["store_id", "name", "town", "opened"], STORES)
    write("recalls.csv", ["recall_id", "sku", "announced", "reason", "remedy"], RECALLS)
    customers = build_customers(rng)
    write("customers.csv",
          ["customer_id", "home_town", "account_opened", "account_closed", "marketing_opt_in"],
          customers)
    orders, lines = build_orders(rng, customers)
    write("orders.csv", ["order_id", "customer_id", "store_id", "order_date"], orders)
    write("order_lines.csv", ["order_id", "sku", "quantity", "unit_price_usd"], lines)
    write("stock.csv", ["store_id", "sku", "quantity"], build_stock(rng))
    write_tickets(rng, orders, lines)
    print(f"{len(PRODUCTS)} products, {len(customers)} customers, "
          f"{len(orders)} orders, {len(lines)} order lines")


if __name__ == "__main__":
    main()
