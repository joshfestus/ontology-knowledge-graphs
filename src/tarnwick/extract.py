"""`tarnwick extract`: facts from text, read by a language model and guided
by the ontology (Chapter 16).

    tarnwick extract T-024             one ticket, the model's reading, the checks
    tarnwick extract --all             every ticket, one line each
    tarnwick extract --all --score     compared with the answers a person wrote
    tarnwick extract --all --turtle    the facts that pass every check, as Turtle
    tarnwick extract T-016 --free      the same ticket read without the ontology
    tarnwick extract --policy returns.md   return rules read from a policy

The model is given the ticket text and nothing else: not the order, not the
customer. Its answer must use the product codes and problem types the
ontology lists, and must quote the words of the ticket behind each choice.
Each answer is then checked against the graph, which the model never saw.
"""

import csv
import re

from rdflib import Graph
from rdflib.namespace import SKOS

from .llm import ask, model_name
from .load import DATA, ROOT, load_all

KEY = ROOT / "tests" / "tickets_key.csv"
OUT = ROOT / "extracted" / "tickets.ttl"
WIDTH = 74


def products():
    with open(DATA / "products.csv", encoding="utf-8") as fh:
        return {r["sku"]: r["name"] for r in csv.DictReader(fh)}


def problems():
    """{code: (label, definition)} for the problem types in the taxonomy."""
    g = Graph().parse(ROOT / "ontology" / "taxonomy.ttl")
    scheme = "https://tarnwick.example/id/problems"
    base = "https://tarnwick.example/id/problem/"
    out = {}
    for c in g.subjects(SKOS.inScheme, None):
        if str(g.value(c, SKOS.inScheme)) == scheme:
            out[str(c)[len(base):]] = (" ".join(str(g.value(c, SKOS.prefLabel)).split()),
                                       " ".join(str(g.value(c, SKOS.definition)).split()))
    return dict(sorted(out.items()))


def categories():
    with open(DATA / "categories.csv", encoding="utf-8") as fh:
        return {r["code"]: r["label"] for r in csv.DictReader(fh)}


def tickets():
    with open(DATA / "tickets.csv", encoding="utf-8") as fh:
        return {r["ticket_id"]: r for r in csv.DictReader(fh)}


# ------------------------------------------------------------ the requests

def instructions():
    lines = [
        ("You read support tickets written to Tarnwick Supply, an "
         "outdoor gear retailer, and record what each ticket is about, "
         "using only the products and problem types listed below."),
        ("complaint_about: the product the customer reports a problem "
         "with. Use \"none\" if the ticket does not say enough to tell "
         "which product it is."),
        ("also_mentions: any other Tarnwick product the ticket refers "
         "to, such as one ordered with it or one the customer wants "
         "instead. Leave it empty if there is none."),
        "problem: the problem type that fits best.",
        ("For each choice, copy the words from the ticket that show it, "
         "exactly as the customer wrote them."),
        "", "Products (code, name):"]
    lines += [f"{sku} {name}" for sku, name in products().items()]
    lines += ["", "Problem types (code: definition):"]
    lines += [f"{code}: {d}" for code, (_, d) in problems().items()]
    return "\n".join(lines)


def schema():
    skus = list(products())
    mention = {"type": "object", "additionalProperties": False,
               "required": ["sku", "words"],
               "properties": {"sku": {"type": "string", "enum": skus},
                              "words": {"type": "string"}}}
    complaint = {"type": "object", "additionalProperties": False,
                 "required": ["sku", "words"],
                 "properties": {"sku": {"type": "string", "enum": skus + ["none"]},
                                "words": {"type": "string"}}}
    return {"type": "object", "additionalProperties": False,
            "required": ["complaint_about", "also_mentions", "problem", "problem_words"],
            "properties": {"complaint_about": complaint,
                           "also_mentions": {"type": "array", "items": mention},
                           "problem": {"type": "string", "enum": list(problems())},
                           "problem_words": {"type": "string"}}}


FREE_INSTRUCTIONS = ("You read support tickets written to Tarnwick Supply, an "
                     "outdoor gear retailer. Say which product the customer has a "
                     "problem with, and what the problem is, in a few words each.")
FREE_SCHEMA = {"type": "object", "additionalProperties": False,
               "required": ["product", "problem"],
               "properties": {"product": {"type": "string"},
                              "problem": {"type": "string"}}}


def read_ticket(ticket_id, free=False):
    text = tickets()[ticket_id]["text"]
    if free:
        return ask(FREE_INSTRUCTIONS, text, schema=FREE_SCHEMA, max_output_tokens=800)
    return ask(instructions(), text, schema=schema(), max_output_tokens=1500)


# ------------------------------------------------------------------ checks

ON_ORDER = """
PREFIX tw: <https://tarnwick.example/ontology#>
SELECT ?ticket ?sku WHERE {
  ?ticket a tw:SupportTicket ; tw:aboutOrder/tw:hasLine/tw:product/tw:sku ?sku .
}"""


def ordered():
    """{ticket id: the SKUs on the order the ticket is about}, from the graph."""
    out = {}
    for t, sku in load_all().query(ON_ORDER):
        out.setdefault(str(t).rsplit("/", 1)[1], set()).add(str(sku))
    return out


def plain(s):
    s = s.replace("’", "'").replace("‘", "'").lower()
    return re.sub(r"\s+", " ", s).strip(" .,\"'")


PIECES = re.compile(r"\s*(?:\.\.\.|\u2026|;)\s*")


def quoted_from(words, text):
    """True if the words are the text's own, allowing a quote shortened with
    an ellipsis or two quotes joined by a semicolon, the pieces in order."""
    at = 0
    for piece in filter(None, (plain(p) for p in PIECES.split(words))):
        at = text.find(piece, at)
        if at < 0:
            return False
        at += len(piece)
    return True


def checks(ticket_id, answer, on_order):
    """What a person must look at before these facts enter the graph."""
    text = plain(tickets()[ticket_id]["text"])
    found = []
    quoted = [answer["problem_words"]]
    quoted += [m["words"] for m in answer["also_mentions"]]
    if answer["complaint_about"]["sku"] != "none":
        quoted.append(answer["complaint_about"]["words"])
    if not all(quoted_from(q, text) for q in quoted):
        found.append("words not in ticket")
    sku = answer["complaint_about"]["sku"]
    if sku == "none":
        found.append("no product named")
    elif sku not in on_order:
        found.append("not on the order")
    return found


# ----------------------------------------------------------------- reports

def wrap(text, indent):
    from textwrap import wrap as tw
    return tw(text, WIDTH, initial_indent=" " * indent, subsequent_indent=" " * indent)


def one(ticket_id, free=False):
    row = tickets()[ticket_id]
    out = [f"{ticket_id}, about order {row['order_id']}:"]
    out += wrap(f'"{row["text"]}"', 2) + [""]
    answer = read_ticket(ticket_id, free)
    if free:
        out += wrap(f"product  {answer['product']}", 0)
        out += [ln if i == 0 else "         " + ln.lstrip()
                for i, ln in enumerate(wrap(f"problem  {answer['problem']}", 0))]
        return "\n".join(out)
    names, probs = products(), problems()
    c = answer["complaint_about"]
    if c["sku"] == "none":
        out.append("complaint about  none")
    else:
        out.append(f"complaint about  prod:{c['sku']}  {names[c['sku']]}")
        out += wrap(f'"{c["words"]}"', 17)
    for m in answer["also_mentions"]:
        out.append(f"also mentions    prod:{m['sku']}  {names[m['sku']]}")
        out += wrap(f'"{m["words"]}"', 17)
    out.append(f"problem type     prob:{answer['problem']}  {probs[answer['problem']][0]}")
    out += wrap(f'"{answer["problem_words"]}"', 17)
    found = checks(ticket_id, answer, ordered().get(ticket_id, set()))
    out += ["", "checks           " + (", ".join(found) if found else
                                       "words found in the ticket, product on the order")]
    return "\n".join(out)


def everything(free=False):
    return {t: read_ticket(t, free) for t in tickets()}


def table():
    answers, on_order = everything(), ordered()
    out = [f"{'ticket':<7} {'complaint':<9} {'also':<9} {'problem':<13} check",
           f"{'-' * 6:<7} {'-' * 9:<9} {'-' * 9:<9} {'-' * 12:<13} {'-' * 18}"]
    held = 0
    for t, a in answers.items():
        found = checks(t, a, on_order.get(t, set()))
        held += bool(found)
        also = ",".join(m["sku"] for m in a["also_mentions"]) or ""
        out.append(f"{t:<7} {a['complaint_about']['sku']:<9} {also:<9} "
                   f"{a['problem']:<13} {', '.join(found) or 'ok'}")
    out += ["", (f"{len(answers)} tickets: {len(answers) - held} pass every "
                 f"check, {held} held for a person.")]
    return "\n".join(out)


def key():
    with open(KEY, encoding="utf-8") as fh:
        return {r["ticket_id"]: r for r in csv.DictReader(fh)}


def score():
    answers, truth = everything(), key()
    tally = {"complaint product": [0, 0, 0], "other product": [0, 0, 0],
             "problem type": [0, 0, 0]}
    wrong = []
    for t, a in answers.items():
        k = truth[t]
        got = a["complaint_about"]["sku"]
        if got == k["sku"]:
            tally["complaint product"][0] += 1
        elif got == "none":
            tally["complaint product"][2] += 1
            wrong.append(f"{t}  complaint {k['sku']}, model gave none")
        else:
            tally["complaint product"][1] += 1
            wrong.append(f"{t}  complaint {k['sku']}, model gave {got}")
        want = {k["also_mentions"]} - {""}
        gave = {m["sku"] for m in a["also_mentions"]}
        tally["other product"][0] += len(want & gave)
        tally["other product"][1] += len(gave - want)
        tally["other product"][2] += len(want - gave)
        for s in sorted(gave - want):
            wrong.append(f"{t}  other product {s} is not in the key")
        for s in sorted(want - gave):
            wrong.append(f"{t}  other product {s} missed")
        if a["problem"] == k["problem"]:
            tally["problem type"][0] += 1
        else:
            tally["problem type"][1] += 1
            wrong.append(f"{t}  problem {k['problem']}, model gave {a['problem']}")
    out = [f"{'':<18} {'right':>5} {'wrong':>5} {'missed':>6}"]
    for name, (r, w, m) in tally.items():
        out.append(f"{name:<18} {r:>5} {w:>5} {m:>6}")
    out += ["", "Where the model and the key differ:"] + ["  " + w for w in wrong]
    return "\n".join(out)


def turtle():
    """The facts from every ticket that passes its checks."""
    answers, on_order = everything(), ordered()
    out = ["@prefix tw:     <https://tarnwick.example/ontology#> .",
           "@prefix ticket: <https://tarnwick.example/id/ticket/> .",
           "@prefix prod:   <https://tarnwick.example/id/product/> .",
           "@prefix prob:   <https://tarnwick.example/id/problem/> .", "",
           f"# Read from data/tickets.csv by {model_name()} with tarnwick extract.",
           "# Tickets that failed a check are left out for a person to read:"]
    held = [t for t, a in answers.items() if checks(t, a, on_order.get(t, set()))]
    out += [f"# {', '.join(held) or 'none'}.", ""]
    for t, a in answers.items():
        if t in held:
            continue
        lines = [f"ticket:{t} tw:complaintAbout prod:{a['complaint_about']['sku']} ;"]
        for m in a["also_mentions"]:
            lines.append(f"    tw:mentions prod:{m['sku']} ;")
        lines.append(f"    tw:problemType prob:{a['problem']} .")
        out += lines
    return "\n".join(out)


# ------------------------------------------------------------------ policies

def policy_schema():
    rule = {"type": "object", "additionalProperties": False,
            "required": ["days", "condition", "categories", "words"],
            "properties": {
                "days": {"type": ["integer", "null"]},
                "condition": {"type": "string"},
                "categories": {"type": "array",
                               "items": {"type": "string", "enum": list(categories())}},
                "words": {"type": "string"}}}
    return {"type": "object", "additionalProperties": False, "required": ["rules"],
            "properties": {"rules": {"type": "array", "items": rule}}}


def policy_instructions():
    lines = [("You read a Tarnwick Supply policy document and list each rule "
              "that says how many days a customer has to return products."),
             "days: the number of days, or null if the rule sets no limit.",
             "condition: what must be true of the product, in a few plain words.",
             ("categories: the product categories the rule covers, from the "
              "list below. A category covers every category beneath it."),
             ("words: the sentence of the document that states the rule, "
              "exactly as written."),
             "", "Categories (code, name, the category it is under):"]
    with open(DATA / "categories.csv", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            lines.append(f"{r['code']} {r['label']}" +
                         (f", under {r['parent']}" if r["parent"] else ""))
    return "\n".join(lines)


def policy(name):
    text = (DATA / "policies" / name).read_text(encoding="utf-8")
    answer = ask(policy_instructions(), text, schema=policy_schema(),
                 max_output_tokens=2000)
    out = [f"Return rules the model read in data/policies/{name}:", ""]
    for r in answer["rules"]:
        days = "no limit" if r["days"] is None else f"{r['days']} days"
        cats = ", ".join(r["categories"]) or "no category"
        out.append(f"{days}, {cats}")
        out += wrap(f"condition: {r['condition']}", 2)
        out += wrap(f'"{r["words"]}"', 2)
        if not quoted_from(r["words"], plain(text)):
            out.append("  check: words not in the document")
        out.append("")
    return "\n".join(out).rstrip()
