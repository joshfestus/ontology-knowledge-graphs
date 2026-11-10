"""`tarnwick coverage`: which ontology terms each competency question needs,
and which terms no question needs at all.

A question's terms are the Tarnwick terms its query uses. A term no query
uses is not wrong, but it has not yet earned its place: either a question is
missing from the list, or the term is.
"""

import re
from pathlib import Path

from rdflib import Graph
from rdflib.namespace import OWL, RDF, RDFS

from .namespaces import TW

ROOT = Path(__file__).resolve().parents[2]
TERM = re.compile(r"(?<![\w])tw:([A-Za-z]\w*)")


def ontology_terms():
    g = Graph().parse(ROOT / "ontology" / "tarnwick.ttl")
    kinds = (OWL.Class, OWL.ObjectProperty, OWL.DatatypeProperty)
    names = {str(s)[len(str(TW)):] for k in kinds for s in g.subjects(RDF.type, k)
             if str(s).startswith(str(TW))}
    names |= {str(s)[len(str(TW)):] for s in g.subjects(RDF.type, TW.ProductStatus)}
    return names


def questions():
    """{question number: set of terms its query uses}"""
    out = {}
    for path in sorted((ROOT / "queries").glob("q*.rq")):
        out[int(path.stem[1:])] = set(TERM.findall(path.read_text(encoding="utf-8")))
    return out


def implied_classes(used):
    """Classes a question uses without naming: the domain or range of a
    property it uses, and every class above those."""
    g = Graph().parse(ROOT / "ontology" / "tarnwick.ttl")
    found = set()
    for name in used:
        for p in (RDFS.domain, RDFS.range):
            o = g.value(TW[name], p)
            if o is not None and str(o).startswith(str(TW)):
                found.add(str(o)[len(str(TW)):])
    todo = list(found)
    while todo:
        for parent in g.objects(TW[todo.pop()], RDFS.subClassOf):
            name = str(parent)[len(str(TW)):]
            if str(parent).startswith(str(TW)) and name not in found:
                found.add(name)
                todo.append(name)
    return found


def used_terms():
    named = set().union(*questions().values())
    return named | implied_classes(named)


def unused():
    return sorted(ontology_terms() - used_terms())


def wrap(text, indent):
    lines = []
    while len(text) > 74:
        cut = text.rfind(", ", 0, 73)
        lines.append(text[:cut + 1])
        text = " " * indent + text[cut + 2:]
    return lines + [text]


def report(summary=False):
    qs = questions()
    terms = ontology_terms()
    used = used_terms()
    lines = [(f"{len(qs)} questions with queries use {len(used & terms)} of the "
              f"{len(terms)} ontology terms."), ""]
    if summary:
        lines.append("Terms no question uses yet:")
        lines += wrap("  " + ", ".join(unused()), 2)
        return "\n".join(lines)
    for n, ts in qs.items():
        text = f"Q{n:<3} " + ", ".join(sorted(ts))
        while len(text) > 74:
            cut = text.rfind(", ", 0, 73)
            lines.append(text[:cut + 1])
            text = "     " + text[cut + 2:]
        lines.append(text)
    lines += ["", "Terms no question uses yet:"]
    text = "  " + ", ".join(unused())
    while len(text) > 74:
        cut = text.rfind(", ", 0, 73)
        lines.append(text[:cut + 1])
        text = "  " + text[cut + 2:]
    lines.append(text)
    return "\n".join(lines)
