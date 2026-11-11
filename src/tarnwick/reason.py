"""Add the facts the ontology implies but nobody wrote (Chapter 10).

The OWL RL reasoner works on a copy of everything, then only the new facts
about Tarnwick's own things are kept, in the "inferred" graph. The reasoner
also produces many housekeeping triples (every thing is the same as itself,
every class is a subclass of itself); those are dropped because no question
needs them and they would bury the useful ones.
"""

import re
import textwrap
from collections import defaultdict

import owlrl
from rdflib import Graph, URIRef
from rdflib.namespace import RDF, XSD

from .namespaces import GRAPH, ID, TW

OURS = str(ID)


def is_useful(s, p, o, borrowed=()):
    """A new fact about a Tarnwick thing, stated in Tarnwick's vocabulary or
    in a vocabulary the reader's files borrow from (Chapter 11)."""
    if not str(s).startswith(OURS):
        return False
    wanted = (str(TW), *borrowed)
    if p == RDF.type:
        return isinstance(o, URIRef) and str(o).startswith(wanted)
    return str(p).startswith(wanted)


CORE = ("http://www.w3.org/1999/02/22-rdf-syntax-ns#",
        "http://www.w3.org/2000/01/rdf-schema#", "http://www.w3.org/2002/07/owl#",
        "http://www.w3.org/2001/XMLSchema#")


def borrowed_from(files):
    """The outside vocabularies the given files name with a prefix."""
    found = set()
    for f in files:
        for _, ns in Graph(bind_namespaces="none").parse(f, format="turtle").namespaces():
            ns = str(ns)
            if ns not in CORE and not ns.startswith((OURS, str(TW))):
                found.add(ns)
    return tuple(sorted(found))


def infer(ds):
    work = Graph()
    for triple in ds.triples((None, None, None)):
        work.add(triple)
    before = set(work)
    owlrl.DeductiveClosure(owlrl.OWLRL_Semantics).expand(work)
    g = ds.graph(GRAPH["inferred"])
    for triple in set(work) - before:
        if is_useful(*triple):
            g.add(triple)
    return g


# ---------------------------------------------------- `tarnwick reason`

ERR = "http://www.daml.org/2002/03/agents/agent-ont#error"
IRI_IN_TEXT = re.compile(r"https?://[^\s,;()]+")
DISJOINT = re.compile(r"Disjoint classes (\S+) and (\S+) have a common individual (\S+)$")


def run(g, borrowed=()):
    """Reason over a copy of g: (new useful facts, contradiction messages)."""
    work = Graph()
    for t in g:
        work.add(t)
    before = set(work)
    owlrl.DeductiveClosure(owlrl.OWLRL_Semantics).expand(work)
    new = {t for t in set(work) - before if is_useful(*t, borrowed=borrowed)}
    errors = sorted(str(m) for m in work.objects(None, URIRef(ERR)))
    return new, errors


def load_for(files=(), data=False):
    from .implied import load
    return load(files, data=data)


def reason_report(files=(), data=False, about=None):
    g = load_for(files, data)
    nm = g.namespace_manager

    def name(node):
        if isinstance(node, URIRef):
            return nm.normalizeUri(node)
        if getattr(node, "datatype", None) and str(node.datatype) != str(XSD.string):
            return str(node)
        return f'"{node}"'

    def shorten(message):
        message = IRI_IN_TEXT.sub(lambda m: name(URIRef(m.group(0))), message)
        m = DISJOINT.match(message)
        if m:
            a, b, thing = m.groups()
            return f"{thing} is both a {a} and a {b}"
        return message

    new, errors = run(g, borrowed_from(files))
    lines = []
    if about:
        thing = URIRef(nm.expand_curie(about)) if ":" in about else None
        if thing is None:
            return f"Give the thing as a prefixed name, such as place:BOULDER, not {about!r}."
        rows = [(name(p), name(o), "written") for p, o in g.predicate_objects(thing)]
        rows += [(name(p), name(o), "inferred") for s, p, o in new if s == thing]
        if not rows:
            return f"Nothing is known about {about}."
        rows.sort(key=lambda r: (r[2] == "inferred", r[0] != "rdf:type", r[0], r[1]))
        w1 = max(len(r[0]) for r in rows)
        w2 = max(len(r[1]) for r in rows)
        lines.append(f"Facts about {about}:")
        for p, o, how in rows:
            p = "a" if p == "rdf:type" else p
            lines.append(f"  {p:<{w1}}  {o:<{w2}}  {how}".rstrip())
    else:
        lines.append(f"Read {len(g):,} triples, the ontology included.")
        if new:
            lines.append(f"The reasoner added {len(new):,} facts about Tarnwick's things:")
        else:
            lines.append("The reasoner added no facts about Tarnwick's things.")
        counts = defaultdict(int)
        for s, p, o in new:
            counts["a " + name(o) if p == RDF.type else name(p)] += 1
        for key, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
            lines.append(f"  {n:>6}  {key}")
    lines.append("")
    if errors:
        lines.append(f"Contradictions found: {len(errors)}")
        for m in errors[:4]:
            wrapped = textwrap.wrap(shorten(m), 70)
            lines.append("  " + wrapped[0])
            lines += ["    " + more for more in wrapped[1:]]
        if len(errors) > 4:
            lines.append(f"  and {len(errors) - 4} more")
    else:
        lines.append("Contradictions found: none.")
    return "\n".join(lines)
