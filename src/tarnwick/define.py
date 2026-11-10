"""`tarnwick define TERM`: what a Tarnwick term is called and what it means.

Looks the term up in the ontology, or in the category taxonomy, and prints
its IRI, what kind of term it is, its label, its definition and, for a
relationship or a value, what it connects. Everything printed comes from the
ontology files, which is the point: a definition is data.
"""

import textwrap
from pathlib import Path

from rdflib import Graph, URIRef
from rdflib.namespace import OWL, RDF, RDFS, SKOS

from .namespaces import PREFIXES, TW
from .text import squeeze

ROOT = Path(__file__).resolve().parents[2]
WIDTH = 74


def graph(ontology=None):
    g = Graph()
    for prefix, ns in PREFIXES.items():
        g.bind(prefix, ns, replace=True)
    if ontology:
        g.parse(ontology)
    else:
        g.parse(ROOT / "ontology" / "tarnwick.ttl")
        g.parse(ROOT / "ontology" / "taxonomy.ttl")
    return squeeze(g)


def find(g, term):
    """The IRI for a term given as tw:name, name, a category code or a label."""
    name = term.split(":", 1)[-1]
    iri = TW[name]
    if (iri, None, None) in g:
        return iri
    for s, code in g.subject_objects(SKOS.notation):
        if str(code).lower() == name.lower():
            return s
    for s, label in g.subject_objects(RDFS.label | SKOS.prefLabel | SKOS.altLabel):
        if str(label).lower() == term.lower():
            return s
    return None


def kind(g, iri):
    types = set(g.objects(iri, RDF.type))
    if OWL.Class in types:
        return "class (a kind of thing)"
    if OWL.ObjectProperty in types:
        return "property linking a thing to another thing"
    if OWL.DatatypeProperty in types:
        return "property linking a thing to a value"
    if SKOS.Concept in types:
        return "category in the taxonomy"
    if TW.ProductStatus in types:
        return "one of the values of product status"
    return "term"


def name(g, node):
    return g.namespace_manager.normalizeUri(node) if isinstance(node, URIRef) else str(node)


def report(term, ontology=None):
    g = graph(ontology)
    iri = find(g, term)
    if iri is None:
        return f"No Tarnwick term called {term!r}."
    rows = [("term", name(g, iri)), ("IRI", str(iri)), ("is a", kind(g, iri))]
    label = g.value(iri, RDFS.label) or g.value(iri, SKOS.prefLabel)
    if label:
        rows.append(("label", str(label)))
    for alt in sorted(str(a) for a in g.objects(iri, SKOS.altLabel)):
        rows.append(("also called", alt))
    for field, pred in (("from", RDFS.domain), ("to", RDFS.range),
                        ("a kind of", RDFS.subClassOf), ("inside", SKOS.broader)):
        for o in g.objects(iri, pred):
            if pred == RDFS.subClassOf and not str(o).startswith(str(TW)):
                continue          # borrowed classes belong to Chapter 11
            rows.append((field, name(g, o)))
    definition = g.value(iri, SKOS.definition)
    lines = [f"{k:<11} {v}" for k, v in rows]
    if definition:
        wrapped = textwrap.wrap(str(definition), WIDTH - 12)
        lines.append(f"{'definition':<11} {wrapped[0]}")
        lines += [" " * 12 + w for w in wrapped[1:]]
    return "\n".join(lines)
