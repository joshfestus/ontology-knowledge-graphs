"""`tarnwick classes [FILE...]`: the class hierarchy, how many things are in
each class, and any thing that sits in two classes declared disjoint.

A thing in a subclass is counted in every class above it too, because every
supplier is an organization. That one step of reasoning is done here by
hand; Chapter 10 hands the whole job to a reasoner.
"""

from collections import defaultdict

from rdflib import Graph
from rdflib.collection import Collection
from rdflib.namespace import OWL, RDF, RDFS

from .namespaces import PREFIXES, TW


def load(paths):
    if paths:
        g = Graph()
        for prefix, ns in PREFIXES.items():
            g.bind(prefix, ns, replace=True)
        for p in paths:
            g.parse(p, format="turtle")
        return g
    # the facts as written: the files, before any reasoning
    from .load import load_all
    from .resolve import resolve_suppliers
    ds = load_all()
    resolve_suppliers(ds)
    g = Graph()
    g.namespace_manager = ds.namespace_manager
    for t in ds.triples((None, None, None)):
        g.add(t)
    return g


def hierarchy(g, own_only=False):
    """Classes and their parents. With own_only, classes from borrowed
    vocabularies (Chapter 11's schema.org mappings) are left out."""
    classes = set(g.subjects(RDF.type, OWL.Class)) | set(g.subjects(RDF.type, RDFS.Class))
    parents = defaultdict(set)
    for c, p in g.subject_objects(RDFS.subClassOf):
        if own_only and not str(p).startswith(str(TW)):
            continue
        parents[c].add(p)
        classes |= {c, p}
    return classes, parents


def above(c, parents):
    """c and every class above it."""
    seen, todo = set(), [c]
    while todo:
        x = todo.pop()
        if x not in seen:
            seen.add(x)
            todo.extend(parents.get(x, ()))
    return seen


def disjoint_groups(g):
    groups = []
    for node in g.subjects(RDF.type, OWL.AllDisjointClasses):
        groups.append(list(Collection(g, g.value(node, OWL.members))))
    groups += [[a, b] for a, b in g.subject_objects(OWL.disjointWith)]
    return groups


def analyse(g, own_only=False):
    classes, parents = hierarchy(g, own_only)
    direct = defaultdict(set)
    for thing, c in g.subject_objects(RDF.type):
        if c in classes:
            direct[c].add(thing)
    member = defaultdict(set)          # class -> every thing in it
    kinds = defaultdict(set)           # thing -> every class it is in
    for c, things in direct.items():
        for up in above(c, parents):
            member[up] |= things
            for t in things:
                kinds[t].add(up)
    problems = []
    for group in disjoint_groups(g):
        for thing, ks in sorted(kinds.items()):
            clash = [c for c in group if c in ks]
            if len(clash) > 1:
                problems.append((thing, clash))
    return classes, parents, direct, member, problems


def report(paths):
    g = load(paths)
    nm = g.namespace_manager
    classes, parents, direct, member, problems = analyse(g, own_only=True)
    children = defaultdict(list)
    roots = []
    for c in classes:
        ps = [p for p in parents.get(c, ()) if p in classes]
        for p in ps:
            children[p].append(c)
        if not ps:
            roots.append(c)
    name = nm.normalizeUri
    lines = [f"{'class':<26}  {'things':>6}  {'through a subclass':>18}",
             f"{'-' * 26}  {'-' * 6}  {'-' * 18}"]

    def walk(c, depth):
        total, own = len(member[c]), len(direct[c])
        through = total - own
        lines.append(f"{'  ' * depth + name(c):<26}  {total:>6}  "
                     f"{through if through else '':>18}".rstrip())
        for child in sorted(children[c], key=name):
            walk(child, depth + 1)

    for r in sorted(roots, key=name):
        walk(r, 0)
    groups = disjoint_groups(g)
    lines += ["", f"Disjoint groups declared: {len(groups)}"]
    if problems:
        lines.append("Things in two classes that cannot share members:")
        for thing, clash in problems:
            lines.append(f"  {name(thing)} is a {' and a '.join(name(c) for c in clash)}")
    else:
        lines.append("No thing is in two classes that cannot share members.")
    return "\n".join(lines)
