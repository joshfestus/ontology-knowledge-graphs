"""Check the graph against the SHACL shapes (Chapter 12).

Validation runs on the data plus what the reasoner inferred, so a shape can
rely on, say, a town being part of its region without that fact being typed.
The result is a list of plain records rather than SHACL's own report graph,
because people read the list and tests compare it.
"""

import textwrap
from dataclasses import dataclass
from pathlib import Path

from pyshacl import validate as shacl_validate
from rdflib import Graph, URIRef
from rdflib.namespace import RDF, SH

from .namespaces import GRAPH
from .text import squeeze

SHAPES = Path(__file__).resolve().parents[2] / "ontology" / "shapes.ttl"


@dataclass(frozen=True, order=True)
class Problem:
    focus: str
    path: str
    value: str
    message: str


def short(node):
    return "" if node is None else str(node).rsplit("/", 1)[-1].rsplit("#", 1)[-1]


def validate(ds):
    data = Graph()
    for g in ds.graphs():
        if g.identifier != GRAPH["ontology"]:
            for triple in g:
                data.add(triple)
    shapes = squeeze(Graph().parse(SHAPES))
    conforms, report, _text = shacl_validate(
        data, shacl_graph=shapes, ont_graph=ds.graph(GRAPH["ontology"]),
        inference="none", advanced=True)
    problems = sorted(
        Problem(short(report.value(r, SH.focusNode)),
                short(report.value(r, SH.resultPath)),
                short(report.value(r, SH.value)),
                str(report.value(r, SH.resultMessage)))
        for r in report.subjects(SH.resultSeverity, SH.Violation))
    return conforms, problems


# -------------------------------------------------- `tarnwick validate`

KIND = {"MinCountConstraintComponent": "missing",
        "MaxCountConstraintComponent": "too many values",
        "InConstraintComponent": "not an allowed value",
        "PatternConstraintComponent": "wrong pattern",
        "DatatypeConstraintComponent": "wrong datatype",
        "ClassConstraintComponent": "wrong class",
        "MinExclusiveConstraintComponent": "too small",
        "MinInclusiveConstraintComponent": "too small"}

def validate_report(files=(), shapes_file=None):
    """Check data against shapes and list every problem in plain words.

    With no files, the full Tarnwick graph (as the build makes it) is
    checked against Tarnwick's shapes. With files, only those files are
    checked, with Tarnwick's ontology available for class membership."""
    from .implied import new_graph
    from .load import ONTOLOGY
    shapes = squeeze(Graph().parse(shapes_file or SHAPES))
    ontology = squeeze(Graph().parse(ONTOLOGY / "tarnwick.ttl"))
    data = new_graph()
    if files:
        # the taxonomy comes along, so a shape can follow a category upward
        squeeze(data.parse(ONTOLOGY / "taxonomy.ttl"))
        for f in files:
            squeeze(data.parse(f, format="turtle"))
    else:
        from .build import build
        ds = build()[0]
        for g in ds.graphs():
            if g.identifier != GRAPH["ontology"]:
                for triple in g:
                    data.add(triple)
    _, report, _ = shacl_validate(data, shacl_graph=shapes, ont_graph=ontology,
                                  inference="none", advanced=True)
    nm = data.namespace_manager

    def name(node):
        if node is None:
            return ""
        if hasattr(node, "datatype"):
            return f'"{node}"'
        return nm.normalizeUri(node) if isinstance(node, URIRef) else str(node)

    targets = sorted({name(t) for t in shapes.objects(None, SH.targetClass)})
    checked = sum(1 for t in shapes.objects(None, SH.targetClass)
                  for _ in data.subjects(RDF.type, t))
    rows = sorted({(name(report.value(r, SH.focusNode)), name(report.value(r, SH.resultPath)),
                    name(report.value(r, SH.value)),
                    KIND.get(str(report.value(r, SH.sourceConstraintComponent))
                             .rsplit("#", 1)[-1], ""),
                    " ".join(str(report.value(r, SH.resultMessage) or "").split()))
                   for r in report.subjects(SH.resultSeverity, SH.Violation)})
    classes = "class" if len(targets) == 1 else "classes"
    things = "thing" if checked == 1 else "things"
    lines = [(f"Checked {checked:,} {things} against shapes for "
              f"{len(targets)} {classes}.")]
    if not rows:
        lines.append("Every record has what its shape requires.")
        return "\n".join(lines)
    lines += [f"Problems: {len(rows)}", ""]
    for focus, path, value, kind, message in rows:
        where = " ".join(x for x in (focus, path, value if value != focus else "") if x)
        lines.append(f"{where}: {kind}" if kind else where)
        lines += ["    " + w for w in textwrap.wrap(message, 70)]
    return "\n".join(lines)
