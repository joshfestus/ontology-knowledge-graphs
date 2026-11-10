"""Chapter 17: Tarnwick's graph copied into a property graph.

`property_graph()` converts the facts as loaded (the files plus the name
matches, before reasoning) into nodes and edges. Things become nodes with a
label and properties. Relationships become edges. The two relationships
Chapter 8 had to turn into things, order lines and stock levels, become
edges with properties of their own, which is what a property graph allows.

This is a small teaching engine in plain Python, not a database: it holds
the whole graph in memory, which is fine for Tarnwick's few thousand nodes.
"""

from collections import defaultdict
from dataclasses import dataclass, field

from rdflib import Literal
from rdflib.namespace import RDF, RDFS

from .namespaces import TW


@dataclass
class Node:
    id: str
    label: str
    props: dict = field(default_factory=dict)


@dataclass
class Edge:
    type: str
    source: str
    target: str
    props: dict = field(default_factory=dict)


@dataclass
class PropertyGraph:
    nodes: dict = field(default_factory=dict)          # id -> Node
    edges: list = field(default_factory=list)
    out: dict = field(default_factory=lambda: defaultdict(list))
    into: dict = field(default_factory=lambda: defaultdict(list))

    def add_node(self, nid, label, **props):
        self.nodes[nid] = Node(nid, label, {k: v for k, v in props.items() if v is not None})

    def add_edge(self, type_, source, target, **props):
        if source in self.nodes and target in self.nodes:
            e = Edge(type_, source, target, props)
            self.edges.append(e)
            self.out[source].append(e)
            self.into[target].append(e)


LABEL = {TW.Product: "Product", TW.Supplier: "Supplier", TW.Organization: "Organization",
         TW.Store: "Store", TW.Customer: "Customer", TW.Order: "Order",
         TW.Town: "Place", TW.State: "Place", TW.Region: "Place", TW.Country: "Place"}


def py(value):
    return value.toPython() if isinstance(value, Literal) else value


def key(iri):
    return str(iri).rsplit("/", 1)[-1]


def property_graph():
    from rdflib.namespace import SKOS

    from .load import load_all
    from .resolve import resolve_suppliers
    ds = load_all()
    resolve_suppliers(ds)
    g = ds
    pg = PropertyGraph()

    def v(s, p):
        return py(g.value(s, p))

    for cls, label in LABEL.items():
        for s in g.subjects(RDF.type, cls):
            nid = key(s)
            props = {"code": nid, "name": v(s, RDFS.label)}
            if label == "Product":
                props = {"sku": nid, "name": v(s, RDFS.label), "priceUSD": v(s, TW.priceUSD),
                         "weightGrams": v(s, TW.weightGrams),
                         "status": key(g.value(s, TW.hasStatus))}
            elif label == "Supplier":
                props["country"] = v(s, TW.country)
            elif label == "Store":
                props["opened"] = v(s, TW.opened)
            elif label == "Customer":
                props = {"code": nid, "accountOpened": v(s, TW.accountOpened)}
            elif label == "Order":
                props = {"code": nid, "date": v(s, TW.orderDate)}
            elif label == "Place":
                props["kind"] = str(cls).rsplit("#")[-1]
            pg.add_node(nid, label, **props)
    for c in g.subjects(RDF.type, SKOS.Concept):
        if g.value(c, SKOS.inScheme) is not None and key(g.value(c, SKOS.inScheme)) == "categories":
            pg.add_node(key(c), "Category", code=key(c), name=str(g.value(c, SKOS.prefLabel)))

    simple = [(TW.suppliedBy, "SUPPLIED_BY"), (TW.parentOrganization, "OWNED_BY"),
              (TW.inCategory, "IN_CATEGORY"), (SKOS.broader, "BROADER"),
              (TW.locatedIn, "LOCATED_IN"), (TW.partOf, "PART_OF"),
              (TW.homeTown, "LIVES_IN"), (TW.soldAt, "SOLD_AT"),
              (TW.fits, "FITS"), (TW.replacedBy, "REPLACED_BY")]
    for pred, type_ in simple:
        for s, o in g.subject_objects(pred):
            pg.add_edge(type_, key(s), key(o))
    for order, customer in g.subject_objects(TW.placedBy):
        pg.add_edge("PLACED", key(customer), key(order))
    for order, line in g.subject_objects(TW.hasLine):
        pg.add_edge("CONTAINS", key(order), key(g.value(line, TW.product)),
                    quantity=v(line, TW.quantity), unitPriceUSD=v(line, TW.unitPriceUSD))
    for level in g.subjects(RDF.type, TW.StockLevel):
        pg.add_edge("STOCKS", key(g.value(level, TW.atStore)), key(g.value(level, TW.product)),
                    quantity=v(level, TW.quantity))
    return pg


def summary_report():
    pg = property_graph()
    nodes = defaultdict(int)
    for n in pg.nodes.values():
        nodes[n.label] += 1
    edges = defaultdict(int)
    with_props = set()
    for e in pg.edges:
        edges[e.type] += 1
        if e.props:
            with_props.add(e.type)
    lines = [f"Nodes: {len(pg.nodes):,}"]
    for label, n in sorted(nodes.items(), key=lambda kv: (-kv[1], kv[0])):
        lines.append(f"  {n:>6,}  {label}")
    lines += ["", f"Edges: {len(pg.edges):,}"]
    for type_, n in sorted(edges.items(), key=lambda kv: (-kv[1], kv[0])):
        note = "  with properties: " + ", ".join(sorted(next(
            e.props for e in pg.edges if e.type == type_))) if type_ in with_props else ""
        lines.append(f"  {n:>6,}  {type_}{note}")
    return "\n".join(lines)


# ------------------------------------------------------------ algorithms

def name_of(pg, nid):
    n = pg.nodes[nid]
    return n.props.get("name") or n.props.get("sku") or n.props.get("code") or nid


def shortest_path(pg, start, goal):
    """The fewest edges from start to goal, ignoring direction (a breadth
    first search: look one step out, then two, and so on)."""
    from collections import deque
    back = {start: None}
    todo = deque([start])
    while todo:
        here = todo.popleft()
        if here == goal:
            break
        steps = [(e, e.target) for e in pg.out[here]] + [(e, e.source) for e in pg.into[here]]
        for e, there in sorted(steps, key=lambda s: (s[0].type, s[1])):
            if there not in back:
                back[there] = (here, e)
                todo.append(there)
    if goal not in back:
        return None
    path, node = [], goal
    while back[node] is not None:
        here, e = back[node]
        path.append((here, e, node))
        node = here
    return list(reversed(path))


def path_report(start, goal):
    pg = property_graph()
    for nid in (start, goal):
        if nid not in pg.nodes:
            return f"No node with the code {nid}."
    path = shortest_path(pg, start, goal)
    if path is None:
        return f"No path from {start} to {goal}."
    lines = [f"{len(path)} steps from {start} to {goal}:"]
    for here, e, there in path:
        arrow = f"-[:{e.type}]->" if e.source == here else f"<-[:{e.type}]-"
        lines.append(f"  ({here}) {arrow} ({there})")
    lines += [""] + [f"  {nid:<9} {pg.nodes[nid].label:<13} {name_of(pg, nid)}"
                     for nid in [start] + [t for _, _, t in path]]
    return "\n".join(lines)


def buyers(pg):
    """product id -> the set of customers who bought it."""
    out = defaultdict(set)
    for e in pg.edges:
        if e.type == "PLACED":
            for c in pg.out[e.target]:
                if c.type == "CONTAINS":
                    out[c.target].add(e.source)
    return out


def similar_report(sku, top=5):
    """Products whose buyers overlap most with the buyers of sku, scored
    by Jaccard similarity: shared buyers divided by all buyers of either."""
    pg = property_graph()
    if sku not in pg.nodes:
        return f"No product with the SKU {sku}."
    who = buyers(pg)
    mine = who[sku]
    scored = []
    for other, theirs in who.items():
        if other != sku and mine & theirs:
            scored.append((len(mine & theirs) / len(mine | theirs), other,
                           len(mine & theirs)))
    scored.sort(key=lambda s: (-s[0], s[1]))
    lines = [f"{name_of(pg, sku)} ({sku}) was bought by {len(mine)} customers.",
             "",
             f"{'sku':<8}  {'name':<33}  {'shared':>6}  {'score':>5}",
             f"{'-' * 8}  {'-' * 33}  {'-' * 6}  {'-' * 5}"]
    for score, other, shared in scored[:top]:
        lines.append(f"{other:<8}  {name_of(pg, other)[:33]:<33}  {shared:>6}  {score:5.2f}")
    return "\n".join(lines)
