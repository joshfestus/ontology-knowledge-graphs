"""`tarnwick metric NAME`: Tarnwick's semantic layer (Chapter 21).

The business terms people use in reports, the metrics that define them and
the dimensions a metric may be split by are written in ontology/metrics.ttl.
This module reads that file and turns a request, a metric with perhaps a
dimension, a reporting date and a period, into one SPARQL query over the
built graph. A dashboard, an agent or a person asks for a metric by name and
gets the same number, because there is only one place the rule is written.

A business term with more than one metric, such as active customer, cannot
be asked for by the term alone. The request has to name a definition.
"""

import re
from datetime import date
from textwrap import wrap

from pyparsing import ParseException
from rdflib import Graph, URIRef
from rdflib.namespace import RDF, RDFS, SKOS

from .build import build
from .load import ROOT
from .namespaces import ID
from .tools import TODAY

METRICS = ROOT / "ontology" / "metrics.ttl"
SHAPES = ROOT / "ontology" / "metric-shapes.ttl"
TWM = "https://tarnwick.example/metrics#"
WIDTH = 74

PREFIXES = """PREFIX tw:   <https://tarnwick.example/ontology#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX xsd:  <http://www.w3.org/2001/XMLSchema#>
"""


class MetricError(Exception):
    """A request the semantic layer cannot answer as asked."""


# ------------------------------------------------------------ the catalog

def catalog():
    return Graph().parse(METRICS)


def _short(node):
    return str(node).rsplit("/", 1)[1]


def _text(g, node, prop):
    v = g.value(node, prop)
    return " ".join(str(v).split()) if v is not None else ""


def _p(name):
    return URIRef(TWM + name)


def metrics(g=None):
    """Every metric, keyed by its short name."""
    g = g or catalog()
    out = {}
    for m in g.subjects(RDF.type, _p("Metric")):
        out[_short(m)] = {
            "label": _text(g, m, RDFS.label),
            "definition": _text(g, m, SKOS.definition),
            "term": _short(g.value(m, _p("defines"))),
            "steward": _text(g, m, _p("steward")),
            "aggregate": _text(g, m, _p("aggregate")),
            "measure": _text(g, m, _p("measure")),
            "where": str(g.value(m, _p("where"))),
            "dimensions": sorted(_short(d) for d in g.objects(m, _p("dimension"))),
        }
    return dict(sorted(out.items()))


def dimensions(g=None):
    g = g or catalog()
    return {_short(d): {"label": _text(g, d, RDFS.label),
                        "definition": _text(g, d, SKOS.definition),
                        "needs": _text(g, d, _p("needs")),
                        "by_group": bool(g.value(d, _p("sortByGroup"))),
                        "where": str(g.value(d, _p("where")))}
            for d in sorted(g.subjects(RDF.type, _p("Dimension")))}


def terms(g=None):
    """Business terms: short name -> (labels, scope note)."""
    g = g or catalog()
    out = {}
    for t in g.subjects(SKOS.inScheme, ID["business-terms"]):
        labels = [str(x).lower() for x in
                  [*g.objects(t, SKOS.prefLabel), *g.objects(t, SKOS.altLabel)]]
        out[_short(t)] = (labels, _text(g, t, SKOS.scopeNote))
    return out


def resolve(name):
    """The metric a name means: a metric's short name or label, or a
    business term that has exactly one metric."""
    found = metrics()
    key = name.strip().lower()
    for m, info in found.items():
        if key in (m, info["label"].lower()):
            return m
    for t, (labels, note) in terms().items():
        if key in labels or key == t:
            defs = [m for m, info in found.items() if info["term"] == t]
            if len(defs) == 1:
                return defs[0]
            lines = [(f'"{name}" has {len(defs)} definitions. '
                      "Name the one you mean:")]
            for m in defs:
                info = found[m]
                lines += wrap(f"{m}  {info['definition']} Steward: "
                              f"{info['steward']}.", WIDTH,
                              initial_indent="  ", subsequent_indent="    ")
            raise MetricError("\n".join(lines))
    raise MetricError(f'No metric or business term is called "{name}". '
                      "Run tarnwick metric --list to see them.")


# ------------------------------------------------------- building a query

def period_dates(period):
    """(first day, last day) of a period written 2026-Q3, 2026-09 or 2026."""
    m = re.fullmatch(r"(\d{4})(?:-Q([1-4])|-(\d{2}))?", period or "")
    if not m:
        raise MetricError(f"{period!r} is not a period. "
                          "Write one as 2026-Q3, 2026-09 or 2026.")
    year, quarter, month = m.groups()
    year = int(year)
    if quarter:
        first, last = 3 * int(quarter) - 2, 3 * int(quarter)
    elif month:
        first = last = int(month)
    else:
        first, last = 1, 12
    end = date(year + (last == 12), last % 12 + 1, 1).toordinal() - 1
    return date(year, first, 1), date.fromordinal(end)


def needs_period(metric):
    return "?from" in metrics()[metric]["where"]


def compose(metric, by=None, as_of=TODAY, period=None):
    """The SPARQL query for one request."""
    info = metrics()[metric]
    if by and by not in info["dimensions"]:
        raise MetricError(f"{metric} cannot be split by {by}. It can be split by: "
                          + (", ".join(info["dimensions"]) or "nothing") + ".")
    agg = info["aggregate"]
    value = (f"COUNT(DISTINCT {info['measure']})" if agg == "COUNT DISTINCT"
             else f"SUM({info['measure']})")
    where = info["where"].rstrip()
    if by:
        where += "\n" + dimensions()[by]["where"].rstrip()
    day = date.fromisoformat(as_of)
    try:
        year_before = day.replace(year=day.year - 1)
    except ValueError:  # 29 February
        year_before = day.replace(year=day.year - 1, day=28)
    dates = {"asOf": day, "yearBefore": year_before}
    if needs_period(metric):
        if not period:
            raise MetricError(f"{metric} needs a period, such as --period 2026-Q3.")
        dates["from"], dates["to"] = period_dates(period)
    for name, d in dates.items():
        where = re.sub(rf"\?{name}\b", f'"{d.isoformat()}"^^xsd:date', where)
    lines = [PREFIXES, f"SELECT {'?group ' if by else ''}({value} AS ?value) WHERE {{"]
    lines.append("\n".join(line.removeprefix("    ")
                           for line in where.split("\n")).strip("\n"))
    lines.append("}")
    if by:
        order = "?group" if dimensions()[by]["by_group"] else "DESC(?value)"
        lines.append(f"GROUP BY ?group\nORDER BY {order}")
    return "\n".join(lines)


def compute(metric, by=None, as_of=TODAY, period=None):
    """(rows of (group, value)) for one request; group is None without by."""
    query = compose(metric, by, as_of, period)
    rows = []
    for row in build()[0].query(query):
        value = row.value.toPython() if row.value is not None else 0
        group = str(row.group) if by else None
        rows.append((group, value))
    return rows


def _fmt(metric, value):
    if metrics()[metric]["aggregate"] == "SUM":
        return f"{value:,.2f}"
    return f"{value:,}"


def report(names, by=None, as_of=TODAY, period=None, show_query=False):
    """What `tarnwick metric` prints."""
    chosen = [resolve(n) for n in names]
    info = metrics()
    out = []
    if show_query:
        for m in chosen:
            out.append(compose(m, by, as_of, period))
        return "\n\n".join(out)
    when = f"as of {as_of}"
    if period:
        first, last = period_dates(period)
        when = f"{first} to {last}"
    if by:
        for m in chosen:
            rows = compute(m, by, as_of, period)
            head = (dimensions()[by]["label"], info[m]["label"])
            cells = [(g, _fmt(m, v)) for g, v in rows]
            total = ("Total", _fmt(m, sum(val for _, val in rows)))
            if info[m]["aggregate"] != "SUM":
                total = None  # a customer can be counted in two groups
            every = [head, *cells, *([total] if total else [])]
            w = max(len(c[0]) for c in every)
            v = max(len(c[1]) for c in every)
            out.append(f"{head[0].ljust(w)}  {head[1].rjust(v)}")
            out.append(f"{'-' * w}  {'-' * v}")
            out += [f"{g.ljust(w)}  {x.rjust(v)}" for g, x in cells]
            if total:
                out.append(f"{'-' * w}  {'-' * v}")
                out.append(f"{total[0].ljust(w)}  {total[1].rjust(v)}")
            out.append(f"({when})")
        return "\n".join(out)
    values = [(info[m]["label"], _fmt(m, compute(m, None, as_of, period)[0][1]))
              for m in chosen]
    w = max(len(label) for label, _ in values)
    v = max(len(x) for _, x in values)
    out += [f"{label.ljust(w)}  {x.rjust(v)}" for label, x in values]
    out.append(f"({when})")
    return "\n".join(out)


def listing():
    """The catalog, as `tarnwick metric --list` prints it."""
    out = []
    dims = dimensions()
    for m, info in metrics().items():
        out.append(m)
        body = (f"{info['definition']} Steward: {info['steward']}. "
                f"Split by: {', '.join(info['dimensions']) or 'nothing'}."
                + (" Needs a period." if needs_period(m) else ""))
        out += wrap(body, WIDTH, initial_indent="    ", subsequent_indent="    ")
    out.append("")
    out.append("Dimensions:")
    for d, info in dims.items():
        out += wrap(f"{d}  {info['definition']}", WIDTH,
                    initial_indent="    ", subsequent_indent="      ")
    return "\n".join(out)


# --------------------------------------------------------------- checking

def check():
    """Shapes, then every metric with every dimension it allows, run."""
    from pyshacl import validate as shacl
    g = catalog()
    conforms, _, text = shacl(g, shacl_graph=Graph().parse(SHAPES))
    out = []
    problems = 0
    if conforms:
        out.append("Shapes: every metric and dimension has what its shape requires.")
    else:
        problems += 1
        out.append("Shapes: problems found.")
        out.append(text)
    found, dims = metrics(g), dimensions(g)
    tried = 0
    for m, info in found.items():
        period = "2026-Q3" if needs_period(m) else None
        for by in [None, *info["dimensions"]]:
            tried += 1
            label = m + (f" by {by}" if by else "")
            if by and not re.search(rf"\{dims[by]['needs']}\b", info["where"]):
                problems += 1
                out.append(f"{label}: the metric does not bind {dims[by]['needs']}.")
                continue
            try:
                rows = compute(m, by, period=period)
            except (MetricError, ParseException, ValueError) as e:
                problems += 1
                out.append(f"{label}: {e}")
                continue
            if not rows or all(not v for _, v in rows):
                problems += 1
                out.append(f"{label}: ran, but found nothing.")
    out.append(f"Metrics: {len(found)}. Dimensions: {len(dims)}. "
               f"Requests tried: {tried}. "
               + ("All ran and found something." if not problems
                  else f"Problems: {problems}."))
    for t, (labels, _) in sorted(terms(g).items()):
        defs = [m for m, info in found.items() if info["term"] == t]
        if len(defs) > 1:
            out += wrap(f'"{labels[0]}" has {len(defs)} definitions: '
                        + ", ".join(defs) + ".", WIDTH, subsequent_indent="  ",
                        break_on_hyphens=False)
    return problems == 0, "\n".join(out)


# ------------------------------------------------ a model asks the layer

INSTRUCTIONS = (
    "You turn a question about Tarnwick Supply into a request to its "
    "semantic layer, which holds the only approved definitions of "
    "Tarnwick's metrics. You never compute a number yourself. Choose the "
    "metric that answers the question, a dimension if the question asks "
    "for the answer split into groups, and a period if the metric needs "
    "one, written as 2026-Q3, 2026-09 or 2026. Today is 30 September 2026. "
    "If the question could mean more than one metric, choose unclear and "
    "write a short question back that names the choices. If no metric "
    "answers the question, choose none and say so in reply. Never stretch "
    "a metric to fit a question it does not answer.")


def described():
    """The catalog as the model reads it."""
    lines = []
    for m, info in metrics().items():
        lines.append(f"{m}: {info['definition']} Split by: "
                     f"{', '.join(info['dimensions']) or 'nothing'}."
                     + (" Needs a period." if needs_period(m) else ""))
    lines.append("")
    lines += [f"{d}: {info['definition']}" for d, info in dimensions().items()]
    return "\n".join(lines)


def schema():
    return {"type": "object", "additionalProperties": False,
            "required": ["metric", "by", "period", "reply"],
            "properties": {
                "metric": {"type": "string",
                           "enum": [*metrics(), "unclear", "none"]},
                "by": {"type": "string", "enum": [*dimensions(), "none"]},
                "period": {"type": "string"},
                "reply": {"type": "string"}}}


def ask(question):
    """What the model chose, and the layer's answer to it."""
    from .llm import ask as model
    text = f"Metrics:\n{described()}\n\nQuestion: {question}"
    choice = model(INSTRUCTIONS, text, schema=schema(), max_output_tokens=800)
    out = []
    if choice["metric"] in ("unclear", "none"):
        out.append(f"The model chose: {choice['metric']}")
        out += wrap(choice["reply"], WIDTH, initial_indent="  ", subsequent_indent="  ",
                    break_on_hyphens=False)
        return "\n".join(out)
    m = choice["metric"]
    by = None if choice["by"] == "none" else choice["by"]
    period = choice["period"].strip() if needs_period(m) else None
    out.append("The model chose: " + m + (f" by {by}" if by else "")
               + (f", period {period}" if period else ""))
    out.append("")
    try:
        out.append(report([m], by=by, period=period))
    except MetricError as e:
        out.append(f"The layer refused: {e}")
    return "\n".join(out)
