"""Chapter 8's two commands about properties.

`tarnwick properties` lists the ontology's properties: whether each one
leads to a thing or a value, from which class to which class or datatype, and whether it has
an inverse, allows only one value, or chains.

`tarnwick implied [FILE...]` shows what the ontology's property declarations
let a program conclude about some data, which is not the same as checking
it. A domain or range does not reject a fact that does not fit; it adds a
class to the thing. Only when that class cannot be combined with one the
thing already has, because of a disjointness declaration, does the
conclusion become a contradiction. The same goes for properties allowed one
value: two values are taken to be one thing, unless the ontology says they
are different. This is the part of OWL reasoning that Chapter 8 needs, done
by hand; Chapter 10 hands the whole job to a reasoner.
"""

from collections import defaultdict
from pathlib import Path

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import OWL, RDF, RDFS, XSD

from .classes import above, analyse, hierarchy
from .namespaces import PREFIXES, TW
from .text import squeeze

ROOT = Path(__file__).resolve().parents[2]
ONTOLOGY = ROOT / "ontology" / "tarnwick.ttl"
WIDTH = 74

# Value types a value of another type also satisfies.
ALSO_SATISFIES = {XSD.integer: {XSD.decimal}}


def new_graph():
    g = Graph()
    for prefix, ns in PREFIXES.items():
        g.bind(prefix, ns, replace=True)
    return g


def load(files=(), ontology=None, data=False):
    """The ontology plus the files; with data=True, all of Tarnwick's data."""
    if data:
        from .classes import load as load_everything
        g = load_everything([])
        if ontology:
            raise ValueError("--ontology cannot be combined with --data")
    else:
        g = new_graph()
        squeeze(g.parse(ontology or ONTOLOGY))
    for f in files:
        squeeze(g.parse(f, format="turtle"))
    return g


# ------------------------------------------------------------ properties

def properties(g):
    """Every declared property with what it links, from, to and notes."""
    inverse = {}
    for a, b in g.subject_objects(OWL.inverseOf):
        inverse[a], inverse[b] = b, a
    rows = []
    for kind, word in ((OWL.ObjectProperty, "thing"), (OWL.DatatypeProperty, "value")):
        for p in g.subjects(RDF.type, kind):
            notes = []
            if p in inverse:
                notes.append("inverse")
            if (p, RDF.type, OWL.FunctionalProperty) in g:
                notes.append("one value")
            if (p, RDF.type, OWL.TransitiveProperty) in g:
                notes.append("chains")
            rows.append((p, word, g.value(p, RDFS.domain), g.value(p, RDFS.range), notes))
    return rows


def short(g, node):
    if node is None:
        return "(any)"
    return g.namespace_manager.normalizeUri(node)


def properties_report(source=None, target=None, ontology=None):
    g = load(ontology=ontology)
    want = {"from": source, "to": target}

    def matches(node, name):
        return name is None or (node is not None and short(g, node).split(":")[-1] == name)

    rows = [r for r in properties(g)
            if matches(r[2], want["from"]) and matches(r[3], want["to"])]
    rows.sort(key=lambda r: (r[1], short(g, r[0])))
    head = f"{'property':<23}{'object':<8}{'from':<17}{'to':<17}notes"
    lines = [head, "-" * WIDTH]
    for p, word, dom, rng, notes in rows:
        line = (f"{short(g, p):<23}{word:<8}{short(g, dom):<17}"
                f"{short(g, rng):<17}{', '.join(notes)}")
        lines.append(line.rstrip())
    lines += ["", f"{len(rows)} properties"]
    shown = {r[0] for r in rows}
    pairs = sorted({tuple(sorted((short(g, a), short(g, b))))
                    for a, b in g.subject_objects(OWL.inverseOf)
                    if a in shown or b in shown})
    if pairs:
        lines.append("Inverse pairs:")
        lines += [f"  {a} and {b}" for a, b in pairs]
    return "\n".join(lines)


# --------------------------------------------------------------- implied

def value_type(lit):
    if lit.datatype is not None:
        return lit.datatype
    return XSD.string


def fits_type(lit, wanted):
    got = value_type(lit)
    return got == wanted or wanted in ALSO_SATISFIES.get(got, set())


def conclusions(g):
    """What the property declarations add to g, and what cannot all be true."""
    inverse = {}
    for a, b in g.subject_objects(OWL.inverseOf):
        inverse[a], inverse[b] = b, a
    work = Graph()
    for t in g:
        work.add(t)

    # 1. Inverses: every fact can be read in the other direction.
    added_facts = []
    for p, q in inverse.items():
        for s, o in g.subject_objects(p):
            if isinstance(o, URIRef) and (o, q, s) not in g:
                added_facts.append((o, q, s))
                work.add((o, q, s))

    # 2. Domains and ranges: a fact puts its subject and object in classes.
    _, parents = hierarchy(work)
    known = defaultdict(set)
    for thing, c in work.subject_objects(RDF.type):
        known[thing] |= above(c, parents)
    added_types = defaultdict(list)          # (class, property) -> things
    wrong_values = []
    for p in set(work.subjects(RDFS.domain, None)) | set(work.subjects(RDFS.range, None)):
        dom, rng = work.value(p, RDFS.domain), work.value(p, RDFS.range)
        for s, o in work.subject_objects(p):
            if dom is not None and dom not in known[s]:
                added_types[(dom, p)].append(s)
                known[s] |= above(dom, parents)
            if rng is None:
                continue
            if isinstance(o, Literal):
                if str(rng).startswith(str(XSD)) and not fits_type(o, rng):
                    wrong_values.append((s, p, o, rng))
            elif rng not in known[o] and not str(rng).startswith(str(XSD)):
                added_types[(rng, p)].append(o)
                known[o] |= above(rng, parents)
    for (c, _), things in added_types.items():
        for t in things:
            work.add((t, RDF.type, c))

    # 3. Classes that cannot share members (Chapter 7's walls).
    *_, clashes = analyse(work)

    # 4. Properties allowed one value.
    different = set()
    for a, b in work.subject_objects(OWL.differentFrom):
        different |= {(a, b), (b, a)}
    one_value = []
    for p in work.subjects(RDF.type, OWL.FunctionalProperty):
        values = defaultdict(set)
        for s, o in work.subject_objects(p):
            values[s].add(o)
        for s, vs in values.items():
            if len(vs) > 1:
                vs = sorted(vs)
                literal = isinstance(vs[0], Literal)
                declared = literal or any((a, b) in different for a in vs for b in vs)
                one_value.append((s, p, vs, declared))
    return added_facts, added_types, clashes, wrong_values, one_value


def implied_report(files=(), ontology=None, data=False):
    g = load(files, ontology, data)
    nm = g.namespace_manager

    def name(node):
        if isinstance(node, Literal):
            return f'"{node}"'
        return nm.normalizeUri(node)

    facts, types, clashes, wrong, one_value = conclusions(g)
    lines = [f"Read {len(g):,} triples, the ontology included.", ""]

    lines.append(f"Facts the inverses add: {len(facts)}")
    if len(facts) <= 4:
        for s, p, o in sorted(facts):
            lines.append(f"  {name(s)} {name(p)} {name(o)}")
    else:
        by_property = defaultdict(int)
        for _, p, _ in facts:
            by_property[p] += 1
        for p, n in sorted(by_property.items(), key=lambda kv: -kv[1]):
            source = g.value(p, OWL.inverseOf) or g.value(None, OWL.inverseOf, p)
            lines.append(f"  {n:>5} {name(p)} facts, from {name(source)}")

    total = sum(len(t) for t in types.values())
    lines += ["", f"Classes the domains and ranges add: {total}"]
    for (c, p), things in sorted(types.items(), key=lambda kv: (-len(kv[1]), name(kv[0][0]))):
        who = name(things[0]) if len(things) == 1 else f"{len(things)} things"
        verb = "is" if len(things) == 1 else "are"
        lines.append(f"  {who} {verb} a {name(c)}, from {name(p)}")

    contradictions = 0
    if clashes:
        lines += ["", "Things in two classes that cannot share members:"]
        groups = defaultdict(list)
        for thing, clash in clashes:
            groups[tuple(clash)].append(thing)
        for clash, things in sorted(groups.items(), key=lambda kv: -len(kv[1])):
            pair = " and a ".join(name(c) for c in clash)
            who = name(things[0]) if len(things) == 1 else f"{len(things)} things"
            verb = "is" if len(things) == 1 else "are"
            lines.append(f"  {who} {verb} a {pair}")
        contradictions += len(clashes)

    if wrong:
        lines += ["", "Values of the wrong type:"]
        for s, p, o, rng in wrong[:5]:
            lines.append(f"  {name(s)} {name(p)} {name(o)}, not {name(rng)}")
        contradictions += len(wrong)

    if one_value:
        lines += ["", "More than one value for a property allowed one:"]
        for s, p, vs, declared in one_value:
            lines.append(f"  {name(s)} {name(p)} {', '.join(name(v) for v in vs)}")
            if declared:
                lines.append("    these are different, so both cannot be right")
                contradictions += 1
            else:
                lines.append("    so these must be two names for one thing")

    lines.append("")
    if contradictions:
        lines.append(f"Contradictions: {contradictions}. The data and the ontology "
                     "cannot both be right.")
    else:
        lines.append("Contradictions: none.")
    return "\n".join(lines)


__all__ = ["TW", "conclusions", "implied_report", "load", "properties", "properties_report"]
