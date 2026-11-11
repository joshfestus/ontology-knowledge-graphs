"""Turn the Tarnwick source files into named graphs.

Each CSV file becomes its own named graph, so every fact can be traced to
the file it came from. Nothing here guesses: values are copied as written,
and the supplier names typed in products.csv are kept as text until
resolve.py decides which supplier each one means.
"""

import csv
import re
from decimal import Decimal
from pathlib import Path

from rdflib import Dataset, Literal, URIRef
from rdflib.namespace import DCTERMS, PROV, RDF, RDFS, XSD

from .namespaces import GRAPH, ID, PREFIXES, TW, iri
from .text import squeeze

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
ONTOLOGY = ROOT / "ontology"

STATUS = {"active": TW.Active, "discontinued": TW.Discontinued,
          "recalled": TW.Recalled}
PLACE_CLASS = {"country": TW.Country, "region": TW.Region,
               "state": TW.State, "town": TW.Town}


def rows(name):
    with open(DATA / name, newline="", encoding="utf-8") as fh:
        yield from csv.DictReader(fh)


def date(value):
    return Literal(value, datatype=XSD.date)


def new_dataset():
    ds = Dataset(default_union=True)
    for prefix, ns in PREFIXES.items():
        ds.bind(prefix, ns, replace=True)
    return ds


def source_file(ds, path):
    """The file a graph was read from, as a thing with its path as label.

    Dublin Core intends dcterms:source "to be used with non-literal values",
    so the file is named with an IRI rather than written as text (Ch 11)."""
    f = ID["source/" + path.replace("/", "-")]
    ds.default_graph.add((f, RDFS.label, Literal(path)))
    return f


def source_graph(ds, filename):
    """A named graph for one source file, with a note of where it came from."""
    g = ds.graph(GRAPH[f"source/{filename}"])
    ds.default_graph.add((g.identifier, RDF.type, PROV.Entity))
    ds.default_graph.add((g.identifier, DCTERMS.source, source_file(ds, f"data/{filename}")))
    return g


def load_products(ds):
    g = source_graph(ds, "products.csv")
    for r in rows("products.csv"):
        p = iri("product", r["sku"])
        g.add((p, RDF.type, TW.Product))
        g.add((p, TW.sku, Literal(r["sku"])))
        g.add((p, RDFS.label, Literal(r["name"], lang="en")))
        g.add((p, TW.supplierNameAsTyped, Literal(r["supplier"])))
        g.add((p, TW.priceUSD, Literal(Decimal(r["price_usd"]))))
        if r["weight_g"]:
            g.add((p, TW.weightGrams, Literal(int(r["weight_g"]))))
        if r["season_rating"]:
            g.add((p, TW.seasonRating, Literal(int(r["season_rating"]))))
        g.add((p, TW.releaseDate, date(r["release_date"])))
        g.add((p, TW.hasStatus, STATUS[r["status"]]))
        if r["replaced_by"]:
            g.add((p, TW.replacedBy, iri("product", r["replaced_by"])))
        g.add((p, TW.mainMaterial, Literal(r["material"])))

    g = source_graph(ds, "product_categories.csv")
    for r in rows("product_categories.csv"):
        g.add((iri("product", r["sku"]), TW.inCategory,
               iri("category", r["category"])))

    g = source_graph(ds, "web_catalogue.csv")
    for r in rows("web_catalogue.csv"):
        g.add((iri("product", r["sku"]), TW.webCategoryLabel,
               Literal(r["web_category"])))

    g = source_graph(ds, "fits.csv")
    for r in rows("fits.csv"):
        g.add((iri("product", r["accessory_sku"]), TW.fits,
               iri("product", r["fits_sku"])))


def load_organizations(ds):
    g = source_graph(ds, "organizations.csv")
    for r in rows("organizations.csv"):
        o = iri("org", r["org_id"])
        g.add((o, RDF.type, TW.Organization))
        g.add((o, RDFS.label, Literal(r["name"])))
        g.add((o, TW.country, Literal(r["country"])))

    g = source_graph(ds, "suppliers.csv")
    for r in rows("suppliers.csv"):
        s = iri("supplier", r["supplier_id"])
        g.add((s, RDF.type, TW.Supplier))
        g.add((s, RDFS.label, Literal(r["name"])))
        g.add((s, TW.country, Literal(r["country"])))
        g.add((s, TW.firstSupplied, date(r["first_supplied"])))
        if r["last_supplied"]:
            g.add((s, TW.lastSupplied, date(r["last_supplied"])))
        if r["parent_org"]:
            g.add((s, TW.parentOrganization, iri("org", r["parent_org"])))


def load_places_and_stores(ds):
    g = source_graph(ds, "places.csv")
    for r in rows("places.csv"):
        p = iri("place", r["place_id"])
        g.add((p, RDF.type, PLACE_CLASS[r["kind"]]))
        g.add((p, RDFS.label, Literal(r["name"])))
        if r["part_of"]:
            g.add((p, TW.partOf, iri("place", r["part_of"])))

    g = source_graph(ds, "stores.csv")
    for r in rows("stores.csv"):
        s = iri("store", r["store_id"])
        g.add((s, RDF.type, TW.Store))
        g.add((s, RDFS.label, Literal(r["name"])))
        g.add((s, TW.opened, date(r["opened"])))
        if r["town"]:
            g.add((s, TW.locatedIn, iri("place", r["town"])))

    g = source_graph(ds, "stock.csv")
    for r in rows("stock.csv"):
        s = iri("stock", f"{r['store_id']}-{r['sku']}")
        g.add((s, RDF.type, TW.StockLevel))
        g.add((s, TW.atStore, iri("store", r["store_id"])))
        g.add((s, TW.product, iri("product", r["sku"])))
        g.add((s, TW.quantity, Literal(int(r["quantity"]))))


def load_customers_and_orders(ds):
    g = source_graph(ds, "customers.csv")
    for r in rows("customers.csv"):
        c = iri("customer", r["customer_id"])
        g.add((c, RDF.type, TW.Customer))
        g.add((c, TW.homeTown, iri("place", r["home_town"])))
        g.add((c, TW.accountOpened, date(r["account_opened"])))
        if r["account_closed"]:
            g.add((c, TW.accountClosed, date(r["account_closed"])))
        g.add((c, TW.marketingOptIn, Literal(r["marketing_opt_in"] == "yes")))

    g = source_graph(ds, "orders.csv")
    for r in rows("orders.csv"):
        o = iri("order", r["order_id"])
        g.add((o, RDF.type, TW.Order))
        g.add((o, TW.placedBy, iri("customer", r["customer_id"])))
        g.add((o, TW.soldAt, iri("store", r["store_id"])))
        g.add((o, TW.orderDate, date(r["order_date"])))

    g = source_graph(ds, "order_lines.csv")
    for r in rows("order_lines.csv"):
        line = iri("line", f"{r['order_id']}-{r['sku']}")
        g.add((line, RDF.type, TW.OrderLine))
        g.add((iri("order", r["order_id"]), TW.hasLine, line))
        g.add((line, TW.product, iri("product", r["sku"])))
        g.add((line, TW.quantity, Literal(int(r["quantity"]))))
        g.add((line, TW.unitPriceUSD, Literal(Decimal(r["unit_price_usd"]))))


def load_recalls_and_tickets(ds):
    g = source_graph(ds, "recalls.csv")
    for r in rows("recalls.csv"):
        rc = iri("recall", r["recall_id"])
        g.add((rc, RDF.type, TW.Recall))
        g.add((rc, TW.product, iri("product", r["sku"])))
        g.add((rc, TW.announced, date(r["announced"])))
        g.add((rc, TW.reason, Literal(r["reason"], lang="en")))
        g.add((rc, TW.remedy, Literal(r["remedy"], lang="en")))

    g = source_graph(ds, "tickets.csv")
    for r in rows("tickets.csv"):
        t = iri("ticket", r["ticket_id"])
        g.add((t, RDF.type, TW.SupportTicket))
        g.add((t, TW.received, date(r["received"])))
        g.add((t, TW.raisedBy, iri("customer", r["customer_id"])))
        g.add((t, TW.aboutOrder, iri("order", r["order_id"])))
        g.add((t, TW.text, Literal(r["text"], lang="en")))


POLICY_LINE = re.compile(r"^Policy (POL-[A-Z]+), version (\d+)")


def load_policies(ds):
    """The policy documents, whole, with the rules modelled in policies.ttl."""
    g = ds.graph(GRAPH["policies"])
    squeeze(g.parse(ONTOLOGY / "policies.ttl"))
    for path in sorted((DATA / "policies").glob("*.md")):
        text = path.read_text(encoding="utf-8")
        title = text.splitlines()[0].lstrip("# ").strip()
        m = next(POLICY_LINE.match(line) for line in text.splitlines()
                 if POLICY_LINE.match(line))
        p = iri("policy", m.group(1))
        g.add((p, RDF.type, TW.Policy))
        g.add((p, RDFS.label, Literal(title, lang="en")))
        g.add((p, TW.text, Literal(text, lang="en")))
        g.add((p, DCTERMS.source, source_file(ds, f"data/policies/{path.name}")))
        g.add((p, URIRef("http://www.w3.org/2002/07/owl#versionInfo"), Literal(m.group(2))))


def load_extracted(ds):
    """Facts read from the ticket text (Chapter 16): those a language model
    found and the checks passed, and those a person wrote after reading the
    tickets the checks held back. Each set in its own graph."""
    for name, file in (("extracted", "tickets.ttl"), ("reviewed", "reviewed.ttl")):
        path = ROOT / "extracted" / file
        if path.exists():
            ds.graph(GRAPH[name]).parse(path)


def load_all():
    """Every source in its own named graph, plus the ontology and taxonomy."""
    ds = new_dataset()
    squeeze(ds.graph(GRAPH["ontology"]).parse(ONTOLOGY / "tarnwick.ttl"))
    squeeze(ds.graph(GRAPH["taxonomy"]).parse(ONTOLOGY / "taxonomy.ttl"))
    load_products(ds)
    load_organizations(ds)
    load_places_and_stores(ds)
    load_customers_and_orders(ds)
    load_recalls_and_tickets(ds)
    load_policies(ds)
    load_extracted(ds)
    return ds


__all__ = ["GRAPH", "ID", "TW", "load_all", "new_dataset"]
