"""Tools an agent can call on the Tarnwick graph (Chapter 20).

Three read from the graph. One writes to it: `record_contact` keeps a note
of a conversation as a support ticket, in the ontology's own terms, in a
memory file of its own. Before anything is written, the record is checked
the way Chapter 16 checked tickets read by a model: the customer, order and
product must exist and belong together, the problem type must come from the
problem list, and the ticket shape must be met.
"""

import os
import re
from pathlib import Path

from rdflib import Graph, Literal
from rdflib.namespace import RDF, RDFS, SKOS, XSD

from .build import build
from .namespaces import ID, PREFIXES, TW, iri
from .rag import graph_facts
from .text import squeeze

TODAY = "2026-09-30"
MEMORY_DEFAULT = "memory.ttl"


def memory_path():
    return Path(os.environ.get("TARNWICK_MEMORY", MEMORY_DEFAULT))


def memory():
    g = Graph()
    for p, ns in PREFIXES.items():
        g.bind(p, ns, replace=True)
    if memory_path().exists():
        squeeze(g.parse(memory_path()))
    return g


def save(g):
    """Write the memory as Turtle, with long summaries wrapped onto several
    lines inside triple quotes so the file fits a page. The squeeze in
    memory() reads them back as one line."""
    from textwrap import wrap
    out = []
    for line in g.serialize(format="turtle").splitlines():
        m = re.match(r'^(\s*)tw:text "(.*)"@en( [;.])$', line)
        if m and len(line) > 74:
            pad, text, end = m.groups()
            body = wrap(text, 74 - len(pad) - 8)
            line = (f'{pad}tw:text """' + f"\n{pad}    ".join(body)
                    + f'"""@en{end}')
        out.append(line)
    memory_path().write_text("\n".join(out) + "\n", encoding="utf-8")


def graph():
    """The full graph with the agent's memory added."""
    ds = build()[0]
    return ds, memory()


def label(ds, node):
    return str(ds.value(node, RDFS.label) or ds.value(node, SKOS.prefLabel) or "")


# ------------------------------------------------------------- read tools

def customer_orders(customer):
    ds, _ = graph()
    c = iri("customer", customer)
    if (c, RDF.type, TW.Customer) not in ds:
        return f"There is no customer {customer}."
    lines = []
    for order in sorted(ds.subjects(TW.placedBy, c)):
        date = ds.value(order, TW.orderDate)
        store = label(ds, ds.value(order, TW.soldAt))
        bought = sorted(f"{ds.value(ds.value(line, TW.product), TW.sku)} "
                        f"{label(ds, ds.value(line, TW.product))}"
                        for line in ds.objects(order, TW.hasLine))
        lines.append(f"{str(order).rsplit('/', 1)[1]} on {date} at {store}: "
                     + "; ".join(bought))
    return "\n".join(lines) or f"Customer {customer} has no orders."


def product_facts(sku):
    if (iri("product", sku), RDF.type, TW.Product) not in build()[0]:
        return f"There is no product {sku}."
    return "\n".join(text for text, _ in graph_facts([sku]))


def customer_history(customer):
    """Support tickets the customer raised, from the ticket file and from
    the agent's own memory."""
    ds, mem = graph()
    c = iri("customer", customer)
    lines = []
    for g, where in ((ds, "ticket file"), (mem, "agent memory")):
        for t in sorted(g.subjects(TW.raisedBy, c)):
            name = str(t).rsplit("/", 1)[1]
            prod = ds.value(t, TW.complaintAbout) or g.value(t, TW.complaintAbout)
            prob = ds.value(t, TW.problemType) or g.value(t, TW.problemType)
            text = g.value(t, TW.text)
            lines.append(f"{name} ({where}) on {g.value(t, TW.received)}, order "
                         f"{str(g.value(t, TW.aboutOrder)).rsplit('/', 1)[1]}, "
                         f"product {label(ds, prod)}, problem {label(ds, prob)}: {text}")
    return "\n".join(lines) or f"Customer {customer} has no support history."


# ------------------------------------------------------------ the write tool

def contact_problems(customer, order, sku, problem, summary):
    """Why a contact record cannot be written, in plain words."""
    ds = build()[0]
    c = iri("customer", customer)
    o = iri("order", order)
    p = iri("product", sku)
    found = []
    if (c, RDF.type, TW.Customer) not in ds:
        found.append(f"There is no customer {customer}.")
    if (o, TW.placedBy, c) not in ds:
        found.append(f"Order {order} was not placed by {customer}.")
    lines = list(ds.objects(o, TW.hasLine))
    if (p, RDF.type, TW.Product) not in ds:
        found.append(f"There is no product {sku}.")
    elif not any((line, TW.product, p) in ds for line in lines):
        found.append(f"Product {sku} is not on order {order}.")
    codes = sorted(str(s).rsplit("/", 1)[1]
                   for s in ds.subjects(SKOS.inScheme, ID["problems"]))
    if problem not in codes:
        found.append(f"{problem} is not a problem type; use one of "
                     + ", ".join(codes) + ".")
    if not summary.strip() or len(summary) > 300:
        found.append("The summary must be between 1 and 300 characters.")
    return found


def record_contact(customer, order, sku, problem, summary):
    found = contact_problems(customer, order, sku, problem, summary)
    if found:
        return "Not recorded:\n" + "\n".join(found)
    mem = memory()
    n = sum(1 for _ in mem.subjects(RDF.type, TW.SupportTicket)) + 1
    t = iri("ticket", f"A-{n:03d}")
    mem.add((t, RDF.type, TW.SupportTicket))
    mem.add((t, TW.raisedBy, iri("customer", customer)))
    mem.add((t, TW.aboutOrder, iri("order", order)))
    mem.add((t, TW.complaintAbout, iri("product", sku)))
    mem.add((t, TW.problemType, iri("problem", problem)))
    mem.add((t, TW.received, Literal(TODAY, datatype=XSD.date)))
    mem.add((t, TW.text, Literal(summary.strip(), lang="en")))
    save(mem)
    return f"Recorded as ticket:A-{n:03d} in {memory_path().name}."


# -------------------------------------------------------------- the list

def _schema(**props):
    return {"type": "object", "additionalProperties": False,
            "required": list(props),
            "properties": {k: {"type": "string", "description": v}
                           for k, v in props.items()}}


TOOLS = {
    "customer_orders": (
        ("List a customer's orders: order ID, date, store and the products "
        "on each."),
        _schema(customer="A customer ID such as C-0083."), customer_orders),
    "product_facts": (
        ("Facts about one product from the knowledge graph: category, status, "
        "replacement, return rule and any recall."),
        _schema(sku="A product SKU such as TW-S202."), product_facts),
    "customer_history": (
        ("The support tickets a customer has raised, including notes of "
        "earlier conversations with this assistant."),
        _schema(customer="A customer ID such as C-0083."), customer_history),
    "record_contact": (
        ("Keep a note of this conversation as a support ticket, so a later "
        "conversation can find it. The order must be the customer's and the "
        "product must be on it."),
        _schema(customer="A customer ID such as C-0083.",
                order="The order the conversation is about, such as O-00077.",
                sku="The product the customer has a problem with.",
                problem="A problem type code, such as deflation or leak.",
                summary="One or two sentences: the problem and what was offered."),
        record_contact),
}


def call(name, arguments):
    """(text, is_error) for one tool call."""
    if name not in TOOLS:
        return f"There is no tool called {name}.", True
    _, schema, fn = TOOLS[name]
    missing = [k for k in schema["required"] if not str(arguments.get(k, "")).strip()]
    if missing:
        return f"Missing arguments: {', '.join(missing)}.", True
    text = fn(**{k: str(arguments[k]) for k in schema["required"]})
    return text, text.startswith(("Not recorded", "There is no"))
