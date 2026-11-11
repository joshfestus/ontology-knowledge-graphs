"""Build the complete Tarnwick knowledge graph and report on it.

    tarnwick build             build, validate and write build/tarnwick.trig
    tarnwick question 13       run queries/q13.rq against the built graph
"""

from functools import lru_cache
from pathlib import Path

from rdflib import Literal, URIRef
from rdflib.namespace import DCTERMS, PROV, RDF, RDFS

from .load import ROOT, load_all, source_file
from .namespaces import GRAPH, ID
from .reason import infer
from .resolve import resolve_suppliers
from .validate import validate

OUT = ROOT / "build" / "tarnwick.trig"
QUERIES = ROOT / "queries"


def describe(ds, name, source=None, made_by=None):
    """Where a graph came from: a file it was read from (dcterms:source), or
    the program step that produced it (prov:wasGeneratedBy)."""
    ds.default_graph.add((GRAPH[name], RDF.type, PROV.Entity))
    if source:
        ds.default_graph.add((GRAPH[name], DCTERMS.source, source_file(ds, source)))
    if made_by:
        step = ID[f"step/{name}"]
        ds.default_graph.add((step, RDF.type, PROV.Activity))
        ds.default_graph.add((step, RDFS.label, Literal(made_by)))
        ds.default_graph.add((GRAPH[name], PROV.wasGeneratedBy, step))


@lru_cache(maxsize=2)
def build(reason=True):
    """The full graph: sources, name matches, inferred facts. Cached so a
    test session builds it once. With reason=False, the facts as written."""
    ds = load_all()
    describe(ds, "ontology", "ontology/tarnwick.ttl")
    describe(ds, "taxonomy", "ontology/taxonomy.ttl")
    describe(ds, "policies", "ontology/policies.ttl")
    describe(ds, "extracted", "extracted/tickets.ttl", made_by="language model extraction")
    describe(ds, "reviewed", "extracted/reviewed.ttl")
    unmatched = resolve_suppliers(ds)
    describe(ds, "resolution", made_by="supplier name matching")
    if reason:
        infer(ds)
        describe(ds, "inferred", made_by="OWL RL reasoner")
    return ds, unmatched


def run_query(name_or_path, ds=None, reason=True):
    """Run a query file and return (column names, rows of plain Python values)."""
    ds = ds or build(reason)[0]
    path = Path(name_or_path)
    if not path.suffix:
        path = QUERIES / f"{name_or_path}.rq"
    result = ds.query(path.read_text(encoding="utf-8"))
    columns = [str(v) for v in result.vars]

    def plain(v):
        """IRIs as prefixed names, the way the reader writes them; values as
        Python values."""
        if v is None:
            return None
        if isinstance(v, URIRef):
            return ds.namespace_manager.normalizeUri(v)
        return v.toPython()

    rows = [tuple(plain(v) for v in row) for row in result]
    return columns, rows


def print_table(columns, rows):
    cells = [[str(c) for c in columns]] + [["" if v is None else str(v) for v in r] for r in rows]
    widths = [max(len(row[i]) for row in cells) for i in range(len(columns))]
    for n, row in enumerate(cells):
        print("  ".join(v.ljust(w) for v, w in zip(row, widths)).rstrip())
        if n == 0:
            print("  ".join("-" * w for w in widths))
    print(f"({len(rows)} {'row' if len(rows) == 1 else 'rows'})")


def main():
    ds, unmatched = build()
    print("Named graphs, with the triples in each:")
    for g in sorted(ds.graphs(), key=lambda g: str(g.identifier)):
        if not len(g):
            continue
        name = str(g.identifier)
        if name.startswith(str(GRAPH)):
            name = name[len(str(GRAPH)):]
        else:
            name = "(default: where each graph came from)"
        print(f"  {len(g):6,}  {name}")
    print(f"  {len(ds):6,}  triples in all")
    if unmatched:
        print("Supplier names not matched:", ", ".join(u[0] for u in unmatched))
    conforms, problems = validate(ds)
    print()
    if conforms:
        print("Validation: every record has what its shape requires.")
    else:
        print(f"Validation: {len(problems)} problems. "
              "Run tarnwick validate to see them.")
    OUT.parent.mkdir(exist_ok=True)
    ds.serialize(OUT, format="trig")
    print(f"Written to {OUT.relative_to(ROOT)}")
