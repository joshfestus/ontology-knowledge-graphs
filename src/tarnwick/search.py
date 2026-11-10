"""`tarnwick search`: find products by a category word, using one of the
structures from Chapter 2, so the same search can be compared across them.

    website     the web catalogue's own category word, matched as typed
    vocabulary  the agreed category names, each matched exactly, nothing more
    taxonomy    an agreed name, plus every category beneath it in the tree
    thesaurus   an agreed name or any other name for it, plus everything beneath
"""

import csv
from pathlib import Path

from rdflib import Graph
from rdflib.namespace import SKOS

ROOT = Path(__file__).resolve().parents[2]
LEVELS = ("website", "vocabulary", "taxonomy", "thesaurus")
NAME_WIDTH = 34


def rows(name):
    with open(ROOT / "data" / name, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def taxonomy(path=None):
    """(preferred labels, alternative labels, children) keyed by category code."""
    g = Graph().parse(path or ROOT / "ontology" / "taxonomy.ttl")
    code = {s: str(n) for s, n in g.subject_objects(SKOS.notation)}
    pref = {code[s]: str(o) for s, o in g.subject_objects(SKOS.prefLabel) if s in code}
    alt = {}
    for s, o in g.subject_objects(SKOS.altLabel):
        alt.setdefault(code[s], []).append(str(o))
    children = {}
    for s, o in g.subject_objects(SKOS.broader):
        # a broader concept missing from the file still holds its children,
        # where no search can reach them
        children.setdefault(code.get(o, str(o)), []).append(code[s])
    return pref, alt, children


def beneath(start, children):
    """A category code and every code below it."""
    found, todo = [], [start]
    while todo:
        c = todo.pop()
        found.append(c)
        todo.extend(children.get(c, []))
    return set(found)


def search(term, level, taxonomy_file=None):
    """(matched category names, [(sku, name, category label)])."""
    word = term.strip().lower()
    products = {r["sku"]: r for r in rows("products.csv")}
    if level == "website":
        hits = [(r["sku"], r["web_category"]) for r in rows("web_catalogue.csv")
                if r["web_category"].lower() == word]
        found = sorted((s, products[s]["name"], label) for s, label in hits)
        return sorted({h[1] for h in hits}), found
    pref, alt, children = taxonomy(taxonomy_file)
    if level == "vocabulary":
        codes = {c for c, p in pref.items() if p.lower() == word}
    else:
        names = {c: [pref[c]] + (alt.get(c, []) if level == "thesaurus" else []) for c in pref}
        matched = {c for c, ns in names.items() if word in (n.lower() for n in ns)}
        codes = set().union(*(beneath(c, children) for c in matched)) if matched else set()
    # a product filed in two matching categories is one product, shown once
    labels = {}
    for r in rows("product_categories.csv"):
        if r["category"] in codes:
            labels.setdefault(r["sku"], set()).add(pref[r["category"]])
    found = sorted((s, products[s]["name"], " / ".join(sorted(ls)))
                   for s, ls in labels.items())
    return sorted(pref[c] for c in codes), found


def report(term, level, taxonomy_file=None):
    names, found = search(term, level, taxonomy_file)
    things = "product" if len(found) == 1 else "products"
    lines = [f'"{term}" using the {level}: {len(found)} {things}']
    if level != "website" and names:
        lines.append("Categories searched: " + ", ".join(names))
    if not found:
        return "\n".join(lines)
    lines.append("")
    for sku, name, label in found:
        lines.append(f"{sku}  {name[:NAME_WIDTH]:<{NAME_WIDTH}}  {label}")
    return "\n".join(_wrap(line) for line in lines)


def _wrap(line, width=74):
    """Long category lists wrap with an indent, as a terminal would show them."""
    if len(line) <= width:
        return line
    out, cur = [], ""
    for word in line.split(" "):
        if len(cur) + len(word) + 1 > width:
            out.append(cur)
            cur = "  " + word
        else:
            cur = f"{cur} {word}" if cur else word
    return "\n".join([*out, cur])
