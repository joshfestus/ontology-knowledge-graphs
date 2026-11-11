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


FIRST = re.compile(r"^\| (\d+) \|.*\| Ch (\d+) \|", re.MULTILINE)


def first_chapter():
    """{question number: the chapter that first answers it}, from QUESTIONS.md"""
    text = (ROOT / "QUESTIONS.md").read_text(encoding="utf-8")
    return {int(q): int(ch) for q, ch in FIRST.findall(text)}


def questions(before=None):
    """{question number: set of terms its query uses}. With a chapter
    number, only the questions first answered before that chapter."""
    first = first_chapter()
    out = {}
    for path in sorted((ROOT / "queries").glob("q*.rq")):
        n = int(path.stem[1:])
        if before is None or first.get(n, 99) < before:
            out[n] = set(TERM.findall(path.read_text(encoding="utf-8")))
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


def used_terms(before=None):
    named = set().union(*questions(before).values())
    return named | implied_classes(named)


def unused(before=None):
    return sorted(ontology_terms() - used_terms(before))


def wrap(text, indent):
    lines = []
    while len(text) > 74:
        cut = text.rfind(", ", 0, 73)
        lines.append(text[:cut + 1])
        text = " " * indent + text[cut + 2:]
    return lines + [text]


def report(summary=False, before=None):
    qs = questions(before)
    terms = ontology_terms()
    used = used_terms(before)
    lines = [(f"{len(qs)} questions with queries use {len(used & terms)} of the "
              f"{len(terms)} ontology terms."), ""]
    if summary:
        lines.append("Terms no question uses yet:")
        lines += wrap("  " + ", ".join(unused(before)), 2)
        return "\n".join(lines)
    for n, ts in qs.items():
        text = f"Q{n:<3} " + ", ".join(sorted(ts))
        while len(text) > 74:
            cut = text.rfind(", ", 0, 73)
            lines.append(text[:cut + 1])
            text = "     " + text[cut + 2:]
        lines.append(text)
    lines += ["", "Terms no question uses yet:"]
    text = "  " + ", ".join(unused(before))
    while len(text) > 74:
        cut = text.rfind(", ", 0, 73)
        lines.append(text[:cut + 1])
        text = "  " + text[cut + 2:]
    lines.append(text)
    return "\n".join(lines)
