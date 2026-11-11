"""`tarnwick pg`: show Turtle files as a property graph would hold them.

The conversion is the plainest one. Every thing with an IRI becomes a node.
Its values become the node's properties, with the IRI kept as a property
called iri. Every triple whose object is another thing becomes an edge,
named in capitals the way property graph tools usually name them. The node
ids n1, n2 and so on are local: they mean nothing outside this one graph,
which is the point Chapter 4 makes about them.
"""

import re
from pathlib import Path

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF, RDFS

from .check import file_order

KIND = {"prod": "Product", "sup": "Supplier", "order": "Order", "line": "OrderLine",
        "cust": "Customer", "store": "Store", "cat": "Category", "place": "Place",
        "vendor": "Vendor"}


def local(iri):
    return re.split(r"[#/]", str(iri))[-1]


def edge_type(predicate):
    """suppliedBy -> SUPPLIED_BY"""
    return re.sub(r"(?<!^)(?=[A-Z])", "_", local(predicate)).upper()


def show(value):
    if isinstance(value, Literal):
        v = value.toPython()
        return f'"{v}"' if isinstance(v, str) else str(v)
    return str(value)


def convert(paths):
    g = Graph()
    texts = []
    for p in paths:
        g.parse(p, format="turtle")
        texts.append(Path(p).read_text(encoding="utf-8"))
    nm = g.namespace_manager
    order = []
    for text in texts:
        one = Graph()
        one.namespace_manager = nm
        one.parse(data=text, format="turtle")
        for s, _ in file_order(one, text):
            if s not in order:
                order.append(s)
    for o in sorted(g.objects(), key=str):
        if isinstance(o, URIRef) and o not in order and (None, RDF.type, o) not in g \
                and not any(p == RDF.type for p in g.predicates(None, o)):
            order.append(o)
    ids = {node: f"n{i}" for i, node in enumerate(order, 1)}

    nodes = []
    for node in order:
        name = nm.normalizeUri(node)
        label = next((local(t) for t in g.objects(node, RDF.type)), None) \
            or KIND.get(name.split(":")[0], "Thing")
        props = [("iri", name)]
        for p, o in g.predicate_objects(node):
            if isinstance(o, Literal):
                props.append(("label" if p == RDFS.label else local(p), show(o)))
        nodes.append((ids[node], label, props))
    edges = sorted(((ids[s], edge_type(p), ids[o]) for s, p, o in g
                    if isinstance(o, URIRef) and p != RDF.type and s in ids and o in ids),
                   key=lambda e: (int(e[0][1:]), e[1], int(e[2][1:])))
    return nodes, edges


def report(paths):
    nodes, edges = convert(paths)
    names = ", ".join(Path(p).name for p in paths)
    out = [f"{names} as a property graph: {len(nodes)} nodes, {len(edges)} edges", ""]
    rows = [(nid if i == 0 else "", label if i == 0 else "", k, v)
            for nid, label, props in nodes for i, (k, v) in enumerate(props)]
    heads = ("node", "label", "property", "value")
    widths = [max(len(r[i]) for r in [*rows, heads]) for i in range(4)]
    out.append("  ".join(h.ljust(w) for h, w in zip(heads, widths)).rstrip())
    out.append("  ".join("-" * w for w in widths))
    for n, r in enumerate(rows):
        if r[0] and n:
            out.append("")
        out.append("  ".join(c.ljust(w) for c, w in zip(r, widths)).rstrip())
    if edges:
        heads = ("from", "edge", "to")
        widths = [max(len(e[i]) for e in [*edges, heads]) for i in range(3)]
        out += ["", "  ".join(h.ljust(w) for h, w in zip(heads, widths)).rstrip(),
                "  ".join("-" * w for w in widths)]
        out += ["  ".join(c.ljust(w) for c, w in zip(e, widths)).rstrip() for e in edges]
    return "\n".join(out)
