"""`tarnwick diff OLD NEW`: what changed between two versions of an
ontology, and which of Tarnwick's queries each change affects (Chapter 23).

A removed term, or a term whose domain or range changed, can break a query
or a program that relies on it, so it needs a new major version. Added and
deprecated terms break nothing, so they need only a minor version. Changed
labels and definitions need a patch.
"""

from rdflib import Graph, Literal
from rdflib.namespace import DCTERMS, OWL, RDF, RDFS, SKOS

from .coverage import questions
from .namespaces import PREFIXES, TW
from .text import squeeze

WIDTH = 74


def load(path):
    g = Graph()
    for prefix, ns in PREFIXES.items():
        g.bind(prefix, ns, replace=True)
    return squeeze(g.parse(path))


def terms(g):
    kinds = (OWL.Class, OWL.ObjectProperty, OWL.DatatypeProperty)
    found = {s for k in kinds for s in g.subjects(RDF.type, k) if str(s).startswith(str(TW))}
    found |= {s for s in g.subjects(RDF.type, TW.ProductStatus)}
    return found


def deprecated(g):
    return {s for s in g.subjects(OWL.deprecated, None)
            if g.value(s, OWL.deprecated) == Literal(True)}


def version(g):
    o = g.value(None, RDF.type, OWL.Ontology)
    return str(g.value(o, OWL.versionInfo)) if o is not None else "?"


def local(t):
    return str(t)[len(str(TW)):]


def users(term):
    """The competency questions whose queries use a term."""
    return sorted(n for n, ts in questions().items() if local(term) in ts)


def compare(old, new):
    a, b = terms(old), terms(new)
    added, removed = b - a, a - b
    newly_deprecated = deprecated(new) - deprecated(old)
    reshaped = {t for t in a & b
                if set(old.objects(t, RDFS.domain)) != set(new.objects(t, RDFS.domain))
                or set(old.objects(t, RDFS.range)) != set(new.objects(t, RDFS.range))}
    reworded = {t for t in a & b
                if old.value(t, SKOS.definition) != new.value(t, SKOS.definition)
                or old.value(t, RDFS.label) != new.value(t, RDFS.label)} - reshaped
    return added, removed, newly_deprecated, reshaped, reworded


def report(old_path, new_path):
    old, new = load(old_path), load(new_path)
    nm = new.namespace_manager
    added, removed, dep, reshaped, reworded = compare(old, new)
    name = nm.normalizeUri
    lines = [f"Version {version(old)} to {version(new)}", ""]

    def section(title, items, note=None):
        if not items:
            return
        lines.append(f"{title}: {len(items)}")
        for t in sorted(items, key=name):
            line = f"  {name(t)}"
            extra = note(t) if note else ""
            lines.append(line + (f"  {extra}" if extra else ""))

    def replaced(t):
        r = new.value(t, DCTERMS.isReplacedBy)
        return f"replaced by {name(r)}" if r is not None else ""

    section("Added", added)
    section("Deprecated", dep, replaced)
    section("Removed", removed)
    section("Domain or range changed", reshaped)
    section("Label or definition changed", reworded)

    affected = []
    for t, effect in [(t, "breaks") for t in sorted(removed | reshaped, key=name)] + \
                     [(t, "should move") for t in sorted(dep, key=name)]:
        for q in users(t):
            affected.append(f"  question {q} {effect}: it uses {name(t)}")
    lines.append("")
    if affected:
        lines.append("Queries affected:")
        lines += affected
    else:
        lines.append("Queries affected: none.")

    if removed or reshaped:
        advice = "Breaking change: this needs a new major version."
    elif added or dep:
        advice = "Nothing breaks: a new minor version is enough."
    elif reworded:
        advice = "Wording only: a new patch version is enough."
    else:
        advice = "No term has changed."
    lines += ["", advice]
    for line in lines:
        if len(line) > WIDTH:
            raise ValueError(f"line too wide: {line}")
    return "\n".join(lines)


__all__ = ["compare", "report"]
