"""Decide which supplier each typed supplier name means (Chapter 15).

Buyers typed supplier names into products.csv by hand, so one company
appears under several spellings. This module cleans each name, compares it
with the registered supplier names, and writes two things into the
"resolution" graph: a NameMatch record for every decision, and the
tw:suppliedBy links that follow from them. A name that matches nothing well
enough is left unlinked and reported, never guessed.
"""

import re
from decimal import Decimal
from difflib import SequenceMatcher

from rdflib import Literal
from rdflib.namespace import RDF, RDFS

from .namespaces import GRAPH, TW, iri

# Words that say what kind of company it is, not which company it is.
LEGAL_WORDS = {"ltd", "limited", "inc", "incorporated", "co", "company",
               "llc"}
THRESHOLD = 0.85


def clean(name):
    """Lower case, drop punctuation and legal words, ignore spaces."""
    words = re.sub(r"[^\w\s]", " ", name.lower()).split()
    return "".join(w for w in words if w not in LEGAL_WORDS)


def slug(name):
    """An identifier made from the name exactly as typed, one per spelling."""
    return re.sub(r"[^A-Za-z0-9]+", "-", name).strip("-")


def similarity(a, b):
    return SequenceMatcher(None, clean(a), clean(b)).ratio()


def best_match(typed, registered):
    """The registered (iri, name) most like the typed name, and its score."""
    scored = [(similarity(typed, name), s, name) for s, name in registered]
    score, s, name = max(scored)
    return s, name, round(score, 3)


def resolve_suppliers(ds):
    g = ds.graph(GRAPH["resolution"])
    registered = [(s, str(name)) for s, name in ds.subject_objects(RDFS.label)
                  if (s, RDF.type, TW.Supplier) in ds]
    typed_names = sorted({str(n) for n in ds.objects(None, TW.supplierNameAsTyped)})
    unmatched = []
    for typed in typed_names:
        s, name, score = best_match(typed, registered)
        if score < THRESHOLD:
            unmatched.append((typed, name, score))
            continue
        method = "exact after cleaning" if score == 1 else "similar spelling"
        m = iri("match", slug(typed))
        g.add((m, RDF.type, TW.NameMatch))
        g.add((m, TW.typedName, Literal(typed)))
        g.add((m, TW.matchedTo, s))
        g.add((m, TW.matchScore, Literal(Decimal(str(score)))))
        g.add((m, TW.matchMethod, Literal(method)))
        for product in ds.subjects(TW.supplierNameAsTyped, Literal(typed)):
            g.add((product, TW.suppliedBy, s))
    return unmatched


# ------------------------------------------------------ `tarnwick match`

def decide(score, runner_up):
    if score >= THRESHOLD and runner_up >= THRESHOLD:
        return "two candidates"
    if score == 1:
        return "exact after cleaning"
    if score >= THRESHOLD:
        return "similar spelling"
    return "for a person"


def load_decisions(path):
    """{typed name: (supplier code or None, who decided)} from a CSV file of
    decisions people have made about names the rules could not settle."""
    import csv
    with open(path, newline="", encoding="utf-8") as fh:
        return {r["typed_name"]: (None if r["decision"] == "none" else r["decision"],
                                  r["decided_by"]) for r in csv.DictReader(fh)}


def match_report(names=(), decisions=None):
    """Every typed supplier name (or the names given), its best and
    second best registered supplier, and the decision the rules make."""
    import csv

    from .load import DATA
    with open(DATA / "suppliers.csv", encoding="utf-8") as fh:
        registered = [(r["supplier_id"], r["name"]) for r in csv.DictReader(fh)]
    decided = load_decisions(decisions) if decisions else {}
    if not names and decided:
        names = list(decided)
    if not names:
        with open(DATA / "products.csv", encoding="utf-8") as fh:
            names = sorted({r["supplier"] for r in csv.DictReader(fh)})
    head = f"{'name as typed':<23} {'best':<8} {'score':>5} {'next':>5}  decision"
    lines = [head, "-" * 74]
    for typed in names:
        scored = sorted(((similarity(typed, n), code) for code, n in registered),
                        reverse=True)
        (score, code), (runner_up, _) = scored[0], scored[1]
        verdict = decide(round(score, 3), round(runner_up, 3))
        if typed in decided:
            choice, who = decided[typed]
            code = choice or "none"
            verdict = f"decided by {who}"
        lines.append(f"{typed[:23]:<23} {code:<8} {score:5.3f} {runner_up:5.3f}  {verdict}")
    lines += ["",
              f"Threshold: {THRESHOLD}. Names are compared after clean() lowercases",
              "them and drops punctuation, spaces and words such as Ltd and Inc."]
    return "\n".join(lines)
