"""`tarnwick write-query QUESTION`: a language model writes the SPARQL
(Chapter 19).

    tarnwick write-query "Which region is Bend in?"
    tarnwick write-query "..." --no-map        without the ontology map
    tarnwick write-query "..." --no-reasoner   run on the facts as written
    tarnwick write-query --bench               the competency questions, scored

The model is given a map of the ontology, written from tarnwick.ttl, and
asked for one query. Before the query runs it is checked: it must parse, it
must only read, and every Tarnwick term and every Tarnwick IRI in it must
exist. A query that fails gets one chance to be repaired, with the problems
sent back to the model.
"""

import re
from decimal import Decimal, InvalidOperation

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import OWL, RDF, RDFS, SKOS
from rdflib.plugins.sparql import prepareQuery

from .build import build, run_query
from .llm import ask
from .load import ROOT
from .namespaces import ID, PREFIXES, TW

WIDTH = 74
TODAY = "2026-09-30"


# ------------------------------------------------------------------ the map

def short(node, g):
    return g.namespace_manager.normalizeUri(node)


def ontology_map():
    """The ontology as a model reads it best: prefixes, then each class and
    property in one line, with its definition."""
    g = Graph().parse(ROOT / "ontology" / "tarnwick.ttl")
    for p, ns in PREFIXES.items():
        g.bind(p, ns, replace=True)

    def text(node):
        d = g.value(node, SKOS.definition) or g.value(node, RDFS.comment) or ""
        return " ".join(str(d).split())

    def local(node):
        return isinstance(node, URIRef) and str(node).startswith(str(TW))

    out = ["Prefixes:"]
    out += [f"PREFIX {p}: <{ns}>" for p, ns in PREFIXES.items()]
    out += ["", "Classes:"]
    for c in sorted(filter(local, g.subjects(RDF.type, OWL.Class))):
        up = [short(s, g) for s in g.objects(c, RDFS.subClassOf) if local(s)]
        line = f"{short(c, g)}" + (f" (a kind of {', '.join(up)})" if up else "")
        out.append(f"{line}: {text(c)}")
    out += ["", "Properties (from -> to):"]
    kinds = (OWL.ObjectProperty, OWL.DatatypeProperty)
    props = sorted({p for k in kinds for p in g.subjects(RDF.type, k) if local(p)})
    for p in props:
        dom = g.value(p, RDFS.domain)
        rng = g.value(p, RDFS.range)
        notes = []
        if (p, RDF.type, OWL.TransitiveProperty) in g:
            notes.append("transitive")
        if (p, RDF.type, OWL.FunctionalProperty) in g:
            notes.append("one value at most")
        inv = g.value(p, OWL.inverseOf) or g.value(None, OWL.inverseOf, p)
        if inv is not None:
            notes.append(f"inverse of {short(inv, g)}")
        sup = [short(s, g) for s in g.objects(p, RDFS.subPropertyOf) if local(s)]
        if sup:
            notes.append(f"also implies {', '.join(sup)}")
        ends = f"({short(dom, g) if dom else 'anything'} -> {short(rng, g) if rng else 'anything'})"
        extra = f" [{'; '.join(notes)}]" if notes else ""
        out.append(f"{short(p, g)} {ends}{extra}: {text(p)}")
    out += ["", "How the data is written:",
            ("Products, places, stores, organizations, policies and return "
            "rules have their name in rdfs:label. Product and policy names are "
            "tagged @en, as in \"Backpacking Tent 2P\"@en; the other names have "
            "no language tag. Customers, orders, order lines, stock levels, "
            "support tickets, recalls and name matches have no name: use "
            "their IRIs."),
            ("Categories and problem types are skos:Concept, with skos:prefLabel "
            "for the name, skos:altLabel for other names, skos:notation for the "
            "code, and skos:broader pointing to the parent category. These "
            "labels are tagged @en. A product is linked by tw:inCategory to the "
            "categories it is filed under, usually one; follow skos:broader* "
            "from there to reach the categories above them."),
            "Product statuses are tw:Active, tw:Discontinued and tw:Recalled.",
            ("Categories are in the scheme tid:categories, problem types in "
            "tid:problems."),
            ("Identifiers: products prod:TW-T102, categories cat:TENT, places "
            "place:BEND (towns in capitals), stores store:ST-BND, suppliers "
            "sup:SUP-01, customers cust:C-0001, orders order:O-00001."),
            ("Each source is loaded into its own named graph. In the default "
            "graph, each named graph has dcterms:source pointing to a thing "
            "whose rdfs:label is the file's path, or prov:wasGeneratedBy "
            "pointing to a program step whose rdfs:label names it."),
            ("The graph also holds facts a reasoner inferred: inverses, "
            "transitive partOf links, and the classes implied by subclasses."),
            f"Today is {TODAY}."]
    return "\n".join(out)


INSTRUCTIONS = (
    "You write SPARQL 1.1 SELECT queries over Tarnwick Supply's "
    "knowledge graph. Use only the prefixes, classes and properties in "
    "the map below. Write one query that answers the question, with a "
    "column for each thing the question asks for. Return only the query.")
BARE = (
    "You write SPARQL 1.1 SELECT queries over Tarnwick Supply's "
    "knowledge graph. Its terms use the prefix tw: "
    "<https://tarnwick.example/ontology#>. Write one query that answers "
    "the question. Return only the query.")
SCHEMA = {"type": "object", "additionalProperties": False, "required": ["query"],
          "properties": {"query": {"type": "string"}}}


def write(question, use_map=True, problems=None, previous=None, map_text=None,
          run=1, details=False):
    """The model's query for a question; with problems, its repair."""
    if not use_map:
        instructions = BARE
    else:
        instructions = INSTRUCTIONS + "\n\n" + (map_text or ontology_map())
    text = f"Question: {question}"
    if problems:
        text += ("\n\nYour query was:\n" + previous + "\n\nIt has these problems:\n"
                 + "\n".join(problems) + "\n\nWrite the query again, fixed.")
    answer = ask(instructions, text, schema=SCHEMA, max_output_tokens=4000,
                 run=run, details=details)
    if details:
        return answer[0]["query"], answer[1]
    return answer["query"]


# --------------------------------------------------------------- the checks

IRI = re.compile(r"<([^>\s]+)>|\b([a-z]+):([A-Za-z][\w.-]*)")


def check(query, ds=None):
    """Problems that stop a query from running, in plain words."""
    try:
        parsed = prepareQuery(query, initNs=PREFIXES)
    except Exception as e:      # noqa: BLE001 any parse error
        return [f"It does not parse: {' '.join(str(e).split())[:200]}"]
    if parsed.algebra.name not in ("SelectQuery", "AskQuery"):
        return ["It is not a SELECT or ASK query."]
    ds = ds or build()[0]
    terms = ontology_terms()
    problems = []
    body = re.sub(r"(?im)^\s*PREFIX.*$", "", query)
    body = re.sub(r'"[^"]*"', '""', body)
    for full, prefix, name in IRI.findall(body):
        if full:
            iri = URIRef(full)
        elif prefix in PREFIXES:
            iri = URIRef(str(PREFIXES[prefix]) + name)
        else:
            continue
        if str(iri).startswith(str(TW)):
            if iri not in terms:
                problems.append(
                    f"{short(iri, ds)} is not a term in the ontology.")
        elif (str(iri).startswith(str(ID)) and (iri, None, None) not in ds
              and (None, None, iri) not in ds):
            problems.append(
                f"{short(iri, ds)} is not a thing in the graph.")
    return sorted(set(problems))


def ontology_terms():
    g = Graph().parse(ROOT / "ontology" / "tarnwick.ttl")
    return {s for s in g.subjects() if str(s).startswith(str(TW))}


LIMIT_SECONDS = 30


class TooSlow(Exception):
    pass


def _run_here(ds, query, pipe):
    try:
        result = ds.query(query, initNs=PREFIXES)
        cols = [str(v) for v in result.vars]
        rows = [tuple(None if v is None else
                      (short(v, ds) if isinstance(v, URIRef) else v.toPython())
                      for v in r) for r in result]
        pipe.send((cols, rows))
    except Exception as e:                       # noqa: BLE001 sent back to the caller
        pipe.send(e)


def run(query, reason=True, seconds=LIMIT_SECONDS):
    """Run a query, giving up after a time limit. A written query can be
    correct and still take hours, so it runs in a separate process that is
    stopped when the time is up."""
    import multiprocessing as mp
    ds = build(reason)[0]
    ctx = mp.get_context("fork")
    mine, theirs = ctx.Pipe(duplex=False)
    worker = ctx.Process(target=_run_here, args=(ds, query, theirs))
    worker.start()
    ready = mine.poll(seconds)
    if not ready:
        worker.kill()
        worker.join()
        raise TooSlow(f"The query did not finish in {seconds} seconds.")
    out = mine.recv()
    worker.join()
    if isinstance(out, Exception):
        raise out
    return out


def attempt(question, use_map=True, map_text=None, run=1, calls=None):
    """(first query, its problems, final query, final problems). Each
    call's saved record is added to `calls` when a list is given."""
    first, saved = write(question, use_map, map_text=map_text, run=run, details=True)
    if calls is not None:
        calls.append(saved)
    problems = check(first)
    if not problems:
        return first, [], first, []
    second, saved = write(question, use_map, problems, first, map_text, run, True)
    if calls is not None:
        calls.append(saved)
    return first, problems, second, check(second)


# ------------------------------------------------------------------ reports

def table(cols, rows, limit=12):
    cells = [cols] + [["" if v is None else str(v) for v in r] for r in rows[:limit]]
    widths = [max(len(r[i]) for r in cells) for i in range(len(cols))]
    gap = "  " if sum(widths) + 2 * (len(widths) - 1) <= WIDTH else " "
    out = []
    for n, r in enumerate(cells):
        out.append(gap.join(v.ljust(w) for v, w in zip(r, widths)).rstrip())
        if n == 0:
            out.append(gap.join("-" * w for w in widths))
    more = f", {len(rows) - limit} not shown" if len(rows) > limit else ""
    out.append(f"({len(rows)} {'row' if len(rows) == 1 else 'rows'}{more})")
    return out


def report(question, use_map=True, reason=True, map_text=None, limit=12):
    first, problems, final, left = attempt(question, use_map, map_text)
    out = ["The model's query:", ""] + first.strip().splitlines() + [""]
    if problems:
        out += ["Check:"] + ["  " + p for p in problems] + [""]
        if left or final == first:
            out.append("The repaired query still fails, so nothing was run.")
            out += ["  " + p for p in left]
            return "\n".join(out)
        out += ["The repaired query:", ""] + final.strip().splitlines() + [""]
    out.append("Check: it parses, only reads, and every term and thing exists.")
    out.append("")
    try:
        cols, rows = run(final, reason)
    except TooSlow as e:
        out.append(str(e) + " It was stopped.")
        return "\n".join(out)
    out += table(cols, rows, limit or len(rows))
    return "\n".join(out)


# ------------------------------------------------------------- the bench

# The competency questions, worded with the details each query fixes, such
# as which product or which town, so that one right answer exists.
BENCH = {
    1: "Which products are tents, whatever the website calls them? Give each "
       "product's SKU, name and the website's category label.",
    2: "Which products sit in more than one category, and in how many?",
    3: "Which supplier makes each product? Give the SKU and the supplier's name.",
    4: "Which suppliers does Tarnwick still buy from, and since when?",
    5: "Which active products came from a supplier Tarnwick has stopped "
       "using? Give SKU, name, supplier and the date it last supplied.",
    6: "Which products have been recalled, and which customers bought them?",
    7: "Which stores have the Backpacking Tent 2P in stock, and how many?",
    8: "Which products are in Camping, including every category beneath it?",
    9: "What are all the names the Packs category is known by?",
    10: "Which tents weigh under 2 kg and are rated for at least three seasons?",
    11: "Which customers placed at least one order in the twelve months up "
        "to today?",
    12: "Which customers count as active under one of these definitions but "
        "not the other: finance (account not closed and at least one order "
        "ever) and marketing (an order in the twelve months up to today)?",
    13: "What was the revenue in each region from July to September 2026? "
        "Count orders with no store region as Online.",
    14: "Which accessories fit which tents?",
    15: "Which products contain down, and in which country is their supplier "
        "based?",
    16: "Which supplier names typed in the files were matched to the same "
        "supplier as another typed name?",
    17: "Which product does each support ticket complain about, and what "
        "kind of problem does it report?",
    18: "Which eight products have the most complaints per hundred units "
        "sold? Give complaints, units sold and the rate to one decimal place.",
    19: "Which policy handles each recalled product, and when did it take "
        "effect?",
    20: "Which region is Bend in?",
    21: "Which suppliers belong to the same parent company?",
    22: "Which product replaced each discontinued one?",
    23: "How many days does a customer have to return each product?",
    24: "Which customers bought a tent and also the footprint that fits it? "
        "Give each customer with the tent.",
    25: "Which categories have no products at all, even beneath them?",
    27: "For each fact about product TW-T102, which file or program step did "
        "it come from?",
    29: "Which five store and supplier pairs have the highest share of the "
        "store's stock units coming from that supplier? Give the units and "
        "the share as a percentage rounded to a whole number.",
    30: "Which ten pairs of products are most often bought in the same order?",
}


# The columns of the reference answer that the worded question asks for,
# where it is not all of them.
KEY = {9: [0], 10: [0], 12: [0], 15: [0, 2], 21: [0], 27: [0, 2], 30: [0, 1]}


def names(value, ds):
    """Every way a value can be written: itself, and for a Tarnwick thing,
    its local name, label and SKU."""
    out = {norm(value)}
    if isinstance(value, str) and ":" in value and " " not in value:
        try:
            iri = ds.namespace_manager.expand_curie(value)
        except ValueError:
            return out
        out.add(str(iri).rsplit("/", 1)[-1].rsplit("#", 1)[-1])
        for p in (RDFS.label, SKOS.prefLabel, TW.sku):
            for o in ds.objects(iri, p):
                out.add(str(o))
    return out


NUMBER = re.compile(r"-?\d+(\.\d+)?")


def norm(v):
    """A value as text, with numbers written one way: 12, 12.0 and "12.00"
    all become 12."""
    if isinstance(v, (int, float, Decimal)) and not isinstance(v, bool):
        try:
            return str(Decimal(str(v)).normalize())
        except InvalidOperation:
            return str(v)
    text = "" if v is None else str(v).strip()
    if NUMBER.fullmatch(text):
        return str(Decimal(text).normalize())
    return text


def also_called(value, ds):
    """A reference value and, for a Tarnwick thing given by IRI, SKU or
    name, every other way of writing it."""
    out = names(value, ds)
    if isinstance(value, (str, Literal)) and str(value).strip():
        text = str(value)
        things = set(ds.subjects(TW.sku, Literal(text)))
        for p in (RDFS.label, SKOS.prefLabel):
            things |= {t for t in ds.subjects(p, Literal(text))
                       if isinstance(t, URIRef) and str(t).startswith(str(ID))}
            things |= {t for t in ds.subjects(p, Literal(text, lang="en"))
                       if isinstance(t, URIRef) and str(t).startswith(str(ID))}
        for thing in things:
            out.add(str(thing).rsplit("/", 1)[-1].rsplit("#", 1)[-1])
            for p in (RDFS.label, SKOS.prefLabel, TW.sku):
                out |= {str(o) for o in ds.objects(thing, p)}
    return out


def header(row):
    """True for a row of column names, such as ("sku", "weight_g"): every
    cell is text in lower case with no digits."""
    return bool(row) and all(isinstance(v, str) and v.strip() and v == v.lower()
                             and not any(c.isdigit() for c in v) for v in row)


def found(want, have, text):
    """A wanted value is in a row when one of its names is a cell of the
    row, or, for a name that is not a number, appears in the row's text as
    whole words, as in a cell "SUP-02 Corran Alloy Works"."""
    if want & have:
        return True
    for w in want:
        if len(w) < 3 or NUMBER.fullmatch(w):
            continue
        if re.search(rf"(?<![\w-]){re.escape(w)}(?![\w-])", text, re.I):
            return True
    return False


def same_answer(expected, got, ds):
    """True when both have the same number of rows and each expected row's
    values all appear, in any column, in its own row of the answer. A
    thing counts whether it is given by IRI, code or name. A first row of
    column names is not counted as an answer."""
    got = list(got)
    if got and header(got[0]):
        got = got[1:]
    if len(expected) != len(got):
        return False
    pool = [(set().union(*(names(v, ds) for v in row)) if row else set(),
             " | ".join("" if v is None else str(v) for v in row)) for row in got]
    for row in expected:
        want = [also_called(v, ds) for v in row if v is not None]
        hit = next((i for i, (have, text) in enumerate(pool)
                    if all(found(w, have, text) for w in want)), None)
        if hit is None:
            return False
        pool.pop(hit)
    return True


# Questions whose reference query ends with LIMIT, where rows below the
# cut tie with the last row kept: {question: the column holding the count}.
# Any of the tied rows is a right answer in those last places.
TIES = {30: 2}


def reference(n, ds):
    """The reference rows for question n, keeping only the columns the
    worded question asks for."""
    rows = run_query(f"q{n:02d}", ds)[1]
    return [tuple(r[i] for i in KEY[n]) for r in rows] if n in KEY else rows


def right(n, got, ds):
    """Whether rows `got` answer bench question n correctly."""
    expected = reference(n, ds)
    if n not in TIES or not expected:
        return same_answer(expected, got, ds)
    col = TIES[n]
    text = (ROOT / "queries" / f"q{n:02d}.rq").read_text(encoding="utf-8")
    full = ds.query(re.sub(r"(?im)^\s*LIMIT\s+\d+\s*$", "", text))
    full = [tuple(v.toPython() if v is not None else None for v in r) for r in full]
    last = run_query(f"q{n:02d}", ds)[1][-1][col]
    sure = [r for r in full if r[col] > last]
    tied = [r for r in full if r[col] == last]
    keep = [i for i in range(len(full[0])) if n not in KEY or i in KEY[n]]
    cut = lambda r: tuple(r[i] for i in keep)         # noqa: E731
    got = list(got)
    if got and header(got[0]):
        got = got[1:]
    if len(got) != len(expected):
        return False
    # the rows above the tie must all be there; each other row must be one
    # of the tied rows
    for chosen in _choices(got, [cut(r) for r in sure], ds):
        if all(any(same_answer([cut(t)], [row], ds) for t in tied) for row in chosen):
            return True
    return False


def _choices(got, sure, ds):
    """The rows of `got` left after taking one row for each row of `sure`,
    or nothing when some row of `sure` is missing."""
    left = list(got)
    for row in sure:
        hit = next((i for i, g in enumerate(left) if same_answer([row], [g], ds)), None)
        if hit is None:
            return []
        left.pop(hit)
    return [left]


def bench(use_map=True, map_text=None):
    """Each worded question through write, check, repair and run, with the
    answer compared to the reference query's."""
    ds = build()[0]
    out = [f"{'Q':<4}{'first try':<22}{'after repair':<16}{'answer':<8}",
           f"{'-' * 3:<4}{'-' * 20:<22}{'-' * 14:<16}{'-' * 8}"]
    tally = {"right": 0, "wrong": 0, "too slow": 0, "not run": 0}
    for n, question in BENCH.items():
        _first, problems, final, left = attempt(question, use_map, map_text)
        after = ("still fails" if left else "fixed") if problems else ""
        if left:
            verdict = "not run"
        else:
            try:
                ok = right(n, run(final)[1], ds)
                verdict = "right" if ok else "wrong"
            except TooSlow:
                verdict = "too slow"
            except Exception:                    # noqa: BLE001 a run error is a wrong answer
                verdict = "wrong"
        tally[verdict] += 1
        note = "passes checks"
        if problems:
            note = "does not parse" if "parse" in problems[0] else "unknown term"
        out.append(f"Q{n:<3}{note:<22}{after:<16}{verdict:<8}")
    out += ["", (f"{tally['right']} of {len(BENCH)} right, {tally['wrong']} wrong, "
                 f"{tally['too slow']} too slow, {tally['not run']} not run.")]
    return "\n".join(out)
