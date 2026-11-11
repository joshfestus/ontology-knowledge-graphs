"""Chapter 9's two commands about taxonomies.

`tarnwick skos FILE.csv` turns a category spreadsheet into SKOS concepts in
Turtle. The spreadsheet has the columns code, label and parent, and may have
a fourth, other_names, holding other names separated by semicolons. Every
row becomes one concept with a preferred label, a notation, and either a
broader concept or a place at the top of the scheme. Nothing is invented:
definitions and related concepts are a person's work, added afterwards.

`tarnwick tree [FILE...]` draws a taxonomy as a tree, with how many of
Tarnwick's products are filed at or below each concept, and checks it
against the SKOS rules and a few habits of good taxonomies.
"""

import csv
import textwrap
from collections import defaultdict
from pathlib import Path

from rdflib import Graph
from rdflib.namespace import RDF, SKOS

from .namespaces import ID, PREFIXES
from .text import squeeze

ROOT = Path(__file__).resolve().parents[2]
WIDTH = 74


# ------------------------------------------------------------------ skos

def turtle_text(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"@en'


def csv_to_turtle(path, scheme="categories", title="Tarnwick product categories"):
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    out = ["@prefix cat:  <https://tarnwick.example/id/category/> .",
           "@prefix tid:  <https://tarnwick.example/id/> .",
           "@prefix skos: <http://www.w3.org/2004/02/skos/core#> .",
           "",
           f"tid:{scheme} a skos:ConceptScheme ;",
           f"    skos:prefLabel {turtle_text(title)} .",
           ""]
    for r in rows:
        code = r["code"].strip()
        lines = [f"cat:{code} a skos:Concept ;",
                 f"    skos:inScheme tid:{scheme} ;",
                 f"    skos:prefLabel {turtle_text(r['label'].strip())} ;"]
        for other in (r.get("other_names") or "").split(";"):
            if other.strip():
                lines.append(f"    skos:altLabel {turtle_text(other.strip())} ;")
        lines.append(f'    skos:notation "{code}" ;')
        parent = (r.get("parent") or "").strip()
        if parent:
            lines.append(f"    skos:broader cat:{parent} .")
        else:
            lines.append(f"    skos:topConceptOf tid:{scheme} .")
        out += lines + [""]
    return "\n".join(out).rstrip("\n")


# ------------------------------------------------------------------ tree

def load(paths):
    g = Graph()
    for prefix, ns in PREFIXES.items():
        g.bind(prefix, ns, replace=True)
    for p in paths or [ROOT / "ontology" / "taxonomy.ttl"]:
        g.parse(p, format="turtle")
    return squeeze(g)


def product_codes():
    """Category code -> the SKUs Tarnwick files directly under it."""
    filed = defaultdict(set)
    with open(ROOT / "data" / "product_categories.csv", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            filed[r["category"]].add(r["sku"])
    return filed


def concepts_in(g, scheme):
    found = set(g.subjects(SKOS.inScheme, scheme)) | set(g.subjects(SKOS.topConceptOf, scheme))
    found |= set(g.objects(scheme, SKOS.hasTopConcept))
    return found


def checks(g, concepts):
    """[(heading, [lines])] for every rule the taxonomy breaks."""
    nm = g.namespace_manager.normalizeUri
    found = []
    is_concept = set(g.subjects(RDF.type, SKOS.Concept))

    missing = [(c, b) for c in concepts for b in g.objects(c, SKOS.broader)
               if b not in is_concept]
    if missing:
        found.append(("Broader concepts that do not exist:",
                      [f"{nm(c)} is under {nm(b)}, which is not a concept"
                       for c, b in sorted(missing)]))

    parents = {c: set(g.objects(c, SKOS.broader)) for c in concepts}
    looped = []
    for c in sorted(concepts):
        seen, todo = set(), list(parents[c])
        while todo:
            x = todo.pop()
            if x == c:
                looped.append(c)
                break
            if x not in seen:
                seen.add(x)
                todo.extend(parents.get(x, ()))
    if looped:
        found.append(("Concepts that are broader than themselves:",
                      [f"{nm(c)} is somewhere above itself" for c in looped]))

    many = []
    for c in sorted(concepts):
        by_lang = defaultdict(list)
        for label in g.objects(c, SKOS.prefLabel):
            by_lang[label.language].append(str(label))
        many += [f"{nm(c)} has {len(v)}: {', '.join(sorted(v))}"
                 for v in by_lang.values() if len(v) > 1]
    if many:
        found.append(("More than one preferred label in one language:", many))

    both = []
    for c in sorted(concepts):
        pref = {str(x).lower() for x in g.objects(c, SKOS.prefLabel)}
        for alt in g.objects(c, SKOS.altLabel):
            if str(alt).lower() in pref:
                both.append(f'{nm(c)} has "{alt}" as preferred and alternative')
    if both:
        found.append(("Labels that are preferred and alternative at once:", both))

    owners, spelled = defaultdict(set), {}
    for c in sorted(concepts):
        for p in (SKOS.prefLabel, SKOS.altLabel, SKOS.hiddenLabel):
            for label in g.objects(c, p):
                owners[str(label).lower()].add(c)
                spelled.setdefault(str(label).lower(), str(label))
    shared = [(spelled[label], sorted(cs)) for label, cs in sorted(owners.items())
              if len(cs) > 1]
    if shared:
        found.append(("Labels on more than one concept, so a search cannot tell which:",
                      [f'"{label}": {" and ".join(nm(c) for c in cs)}'
                       for label, cs in shared]))

    def above(c):
        seen, todo = set(), list(parents.get(c, ()))
        while todo:
            x = todo.pop()
            if x not in seen:
                seen.add(x)
                todo.extend(parents.get(x, ()))
        return seen

    clash = sorted({tuple(sorted((a, b))) for a, b in g.subject_objects(SKOS.related)
                    if a in concepts and (b in above(a) or a in above(b))})
    if clash:
        found.append(("Related concepts that are also one above the other:",
                      [f"{nm(a)} and {nm(b)}" for a, b in clash]))
    return found


def tree_report(paths=(), scheme_name="categories"):
    g = load(paths)
    scheme = ID[scheme_name]
    concepts = concepts_in(g, scheme)
    if not concepts:
        return f"No concepts in the scheme tid:{scheme_name}."
    code = {c: str(g.value(c, SKOS.notation) or "") for c in concepts}
    label = {c: str(g.value(c, SKOS.prefLabel) or g.namespace_manager.normalizeUri(c))
             for c in concepts}
    children = defaultdict(list)
    for c in concepts:
        for b in g.objects(c, SKOS.broader):
            if b in concepts:
                children[b].append(c)
    tops = [c for c in concepts
            if (c, SKOS.topConceptOf, scheme) in g or (scheme, SKOS.hasTopConcept, c) in g]
    filed = product_codes()

    def below(c, seen=None):
        seen = seen or set()
        if c in seen:
            return set()
        seen.add(c)
        skus = set(filed.get(code[c], ()))
        for k in children[c]:
            skus |= below(k, seen)
        return skus

    head = f"{'concept':<26}{'code':<12}{'products':>8}  other names"
    lines = [head, "-" * WIDTH]
    shown = set()

    def walk(c, depth):
        if c in shown:
            return
        shown.add(c)
        others = ", ".join(sorted(str(a) for a in g.objects(c, SKOS.altLabel)))
        parts = textwrap.wrap(others, WIDTH - 48) or [""]
        line = f"{'  ' * depth + label[c]:<26}{code[c]:<12}{len(below(c)):>8}  {parts[0]}"
        lines.append(line.rstrip())
        lines.extend(" " * 48 + more for more in parts[1:])
        for k in sorted(children[c], key=lambda x: label[x]):
            walk(k, depth + 1)

    for t in sorted(tops, key=lambda x: label[x]):
        walk(t, 0)
    lost = sorted(c for c in concepts if c not in shown)
    lines += ["", f"{len(concepts)} concepts, {len(tops)} at the top"]
    if lost:
        lines.append("Not reachable from the top: "
                     + ", ".join(g.namespace_manager.normalizeUri(c) for c in lost))
    undefined = [c for c in concepts if g.value(c, SKOS.definition) is None]
    if undefined:
        lines.append(f"Concepts with no definition: {len(undefined)}")

    problems = checks(g, concepts)
    lines.append("")
    if problems:
        for heading, items in problems:
            lines.append(heading)
            lines += [f"  {item}" for item in items]
    else:
        lines.append("No problems found in the labels or the tree.")
    return "\n".join(lines)


__all__ = ["checks", "csv_to_turtle", "load", "tree_report"]
