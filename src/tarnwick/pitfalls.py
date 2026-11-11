"""`tarnwick pitfalls`: check an ontology for common modelling mistakes.

The checks are a selection from the OOPS! pitfall catalog (Poveda-Villalon,
Gomez-Perez and Suarez-Figueroa, 2014), which numbers 41 pitfalls P01 to P41.
Only pitfalls a program can find by looking at the file are checked here;
most of the others, such as merging two concepts in one class, need a person
who knows what the terms mean.
"""

import re
from collections import defaultdict
from pathlib import Path

from rdflib import Graph, URIRef
from rdflib.collection import Collection
from rdflib.namespace import DCTERMS, OWL, RDF, RDFS, SKOS

from .namespaces import PREFIXES, TW
from .text import squeeze

ROOT = Path(__file__).resolve().parents[2]
WIDTH = 74
LICENSE = (DCTERMS.license, DCTERMS.rights, URIRef("http://creativecommons.org/ns#license"))


def load(path=None):
    g = Graph()
    for prefix, ns in PREFIXES.items():
        g.bind(prefix, ns, replace=True)
    return squeeze(g.parse(path or ROOT / "ontology" / "tarnwick.ttl"))


def ours(node):
    return str(node).startswith(str(TW))


def check(g, data_predicates=()):
    """[(code, title, [names])] for every pitfall found."""
    nm = g.namespace_manager.normalizeUri
    classes = {c for c in g.subjects(RDF.type, OWL.Class) if ours(c)}
    props = {p for k in (OWL.ObjectProperty, OWL.DatatypeProperty)
             for p in g.subjects(RDF.type, k) if ours(p)}
    objects = {p for p in g.subjects(RDF.type, OWL.ObjectProperty) if ours(p)}
    values = {v for c in classes for v in g.subjects(RDF.type, c) if ours(v)}
    found = []

    def add(code, title, items):
        if items:
            found.append((code, title, sorted(nm(i) for i in items)))

    connected = set()
    for p in props:
        connected |= set(g.objects(p, RDFS.domain)) | set(g.objects(p, RDFS.range))
    for c, d in g.subject_objects(RDFS.subClassOf):
        connected |= {c, d}
    for c, d in g.subject_objects(OWL.unionOf):
        connected |= set(Collection(g, d))
    add("P04", "Creating unconnected ontology elements",
        {c for c in classes if c not in connected})

    add("P08", "Missing annotations",
        {t for t in classes | props | values
         if g.value(t, RDFS.label) is None or g.value(t, SKOS.definition) is None})

    walled = set()
    for node in g.subjects(RDF.type, OWL.AllDisjointClasses):
        walled |= set(Collection(g, g.value(node, OWL.members)))
    for a, b in g.subject_objects(OWL.disjointWith):
        walled |= {a, b}
    def inherits_wall(c):
        seen, todo = set(), [c]
        while todo:
            x = todo.pop()
            if x in walled:
                return True
            if x not in seen:
                seen.add(x)
                todo.extend(g.objects(x, RDFS.subClassOf))
        return False

    add("P10", "Missing disjointness", {c for c in classes if not inherits_wall(c)})

    add("P11", "Missing domain or range in properties",
        {p for p in props if g.value(p, RDFS.domain) is None or g.value(p, RDFS.range) is None})

    inverses = set(g.subjects(OWL.inverseOf)) | set(g.objects(None, OWL.inverseOf))
    add("P13", "Inverse relationships not explicitly declared", objects - inverses)

    add("P19", "Defining multiple domains or ranges in properties",
        {p for p in props if len(set(g.objects(p, RDFS.domain))) > 1
         or len(set(g.objects(p, RDFS.range))) > 1})

    local = {t: str(t)[len(str(TW)):] for t in classes | props}
    add("P22", "Using different naming conventions in the ontology",
        {t for t in classes if not re.fullmatch(r"[A-Z][A-Za-z0-9]*", local[t])}
        | {t for t in props if not re.fullmatch(r"[a-z][A-Za-z0-9]*", local[t])})

    by_label = defaultdict(set)
    for c in classes:
        for label in g.objects(c, RDFS.label):
            by_label[str(label).lower()].add(c)
    add("P32", "Several classes with the same label",
        {c for cs in by_label.values() if len(cs) > 1 for c in cs})

    used_as_class = {o for o in g.objects(None, RDF.type) if ours(o)}
    used_as_class |= {o for o in g.objects(None, RDFS.subClassOf) if ours(o)}
    declared_class = classes | {c for c in g.subjects(RDF.type, RDFS.Class) if ours(c)}
    add("P34", "Untyped class", used_as_class - declared_class)

    used_as_prop = {p for _, p, _ in g if ours(p)} | {p for p in data_predicates if ours(p)}
    add("P35", "Untyped property", used_as_prop - props)

    ontology = g.value(None, RDF.type, OWL.Ontology)
    if ontology is None:
        found.append(("P38", "No OWL ontology declaration", ["the file"]))
    elif not any(g.value(ontology, p) is not None for p in LICENSE):
        found.append(("P41", "No license declared", [nm(ontology)]))
    return found


IMPORTANCE = {"P04": "minor", "P08": "minor", "P10": "important", "P11": "important",
              "P13": "minor", "P19": "critical", "P22": "minor", "P32": "minor",
              "P34": "important", "P35": "important", "P38": "important",
              "P41": "important"}
CHECKED = ("P04", "P08", "P10", "P11", "P13", "P19", "P22", "P32", "P34", "P35",
           "P38", "P41")


def pitfalls_report(ontology=None):
    g = load(ontology)
    data_predicates = ()
    if ontology is None:
        from .classes import load as load_everything
        data_predicates = {p for _, p, _ in load_everything([])}
    found = check(g, data_predicates)
    lines = [f"Checked {len(CHECKED)} of the 41 pitfalls in the OOPS! catalog.", ""]
    if not found:
        lines.append("None of them found.")
        return "\n".join(lines)
    for code, title, items in found:
        lines.append(f"{code}  {title} ({IMPORTANCE[code]}): {len(items)}")
        text = "      " + ", ".join(items)
        while len(text) > WIDTH:
            cut = text.rfind(", ", 0, WIDTH - 1)
            lines.append(text[:cut + 1])
            text = "      " + text[cut + 2:]
        lines.append(text)
    clean = [c for c in CHECKED if c not in {f[0] for f in found}]
    lines += ["", "Not found: " + ", ".join(clean) + "."]
    return "\n".join(lines)
