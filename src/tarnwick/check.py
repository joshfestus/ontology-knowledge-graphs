"""`tarnwick check`: read a Turtle file and say what it contains, or what is
wrong with it, in plain English.

This is the reader's only tool in Parts One and Two of the book, so its
messages are written for someone who has never seen a parser error.
"""

import re
import textwrap
from pathlib import Path

from rdflib import BNode, Graph, Literal, URIRef
from rdflib.namespace import RDF, XSD
from rdflib.plugins.parsers.notation3 import BadSyntax

WIDTH = 74

# What the parser says, and what it means for a person writing Turtle by hand.
EXPLAIN = [
    (r"Prefix \"(.*?)\" not bound",
     ("The prefix {0} is used here but was never declared. Add a line such as\n"
      "@prefix {0} <...> . at the top of the file, with the right address.")),
    (r"expected qname after @prefix",
     ("A prefix declaration needs a colon straight after the prefix, as in\n"
      "@prefix tw: <https://tarnwick.example/ontology#> .")),
    (r"newline found in string literal",
     ("A piece of text in quotes is never closed. The closing quote mark is\n"
      "missing on this line.")),
    (r"EOF found after object|EOF found when expected",
     ("The file ends before the last statement does. The last statement needs\n"
      "a full stop at its end.")),
    (r"objectList expected", None),
]
AFTER_COMMA = ("A comma means another object follows, but none does. Remove the\n"
               "comma, or add the next object after it.")
SPACE_IN_NAME = ("Turtle expected an object here and found a second word. A name\n"
                 "cannot contain a space: write {1}, not {0}.")
MISSING_STOP = ("The statement before this one never ended. Line {0} is missing the\n"
                "full stop at its end.")
BAD_VALUE = ("Turtle could not read the value that starts here. Text needs quote\n"
             "marks around it, and a date needs quotes and a datatype, as in\n"
             "\"2024-03-01\"^^xsd:date.")


def explain(err, text):
    """(line number, the line, a plain English explanation) for a parse error."""
    pos = min(err._i, len(text))
    line_no = text.count("\n", 0, pos) + 1
    line_start = text.rfind("\n", 0, pos) + 1
    at_line_start = not text[line_start:pos].strip()
    lines = text.split("\n")
    why = err._why
    for pattern, message in EXPLAIN:
        m = re.search(pattern, why)
        if m:
            if message is None:
                line_text = lines[line_no - 1]
                words = re.match(r"\s*(\S+)\s+(\w+)", text[pos:]) if not \
                    re.search(r",\s*(\.|;|$)", line_text) else None
                last = text[line_start:pos].split()[-1:] or [""]
                if words is None:
                    message = AFTER_COMMA
                else:
                    first, second = last[0], words.group(1)
                    joined = first + second[:1].upper() + second[1:]
                    message = SPACE_IN_NAME.format(f"{first} {second}", joined)
            else:
                message = message.format(*m.groups())
            break
    else:
        if "end of statement" in why and at_line_start:
            previous = line_no - 1
            while previous > 1 and not lines[previous - 1].strip():
                previous -= 1
            message = MISSING_STOP.format(previous)
        elif "end of statement" in why:
            message = BAD_VALUE
        else:
            message = f"The parser reports: {why}"
    if "EOF" in why:
        line_no = len(lines) if lines[-1] else len(lines) - 1
        while line_no > 1 and not lines[line_no - 1].strip():
            line_no -= 1
    return line_no, lines[line_no - 1], message


def short(node, g):
    """A node written the way it would appear in the reader's own Turtle."""
    if isinstance(node, Literal):
        if node.datatype in (XSD.integer, XSD.decimal, XSD.boolean):
            return str(node)
        quoted = '"' + " ".join(str(node).split()).replace('"', '\\"') + '"'
        if node.language:
            return quoted + "@" + node.language
        if node.datatype and node.datatype != XSD.string:
            return quoted + "^^" + g.namespace_manager.normalizeUri(node.datatype)
        return quoted
    if node == RDF.type:
        return "a"
    if isinstance(node, BNode):
        return "[ ]"
    return g.namespace_manager.normalizeUri(node)


def file_order(g, text):
    """Subjects, then each subject's predicates, in the order the file has them,
    so the report reads alongside the listing."""
    def pos(word, start=0):
        m = re.search(r"(?<![\w:<-])" + re.escape(word) + r"(?![\w-])", text[start:])
        return start + m.start() if m else len(text)

    def opens(word):
        """Where a statement about this subject starts, at the start of a line."""
        m = re.search(r"^" + re.escape(word) + r"(?![\w-])", text, re.MULTILINE)
        return m.start() if m else pos(word)

    subjects = sorted({s for s in g.subjects()}, key=lambda s: (opens(short(s, g)), short(s, g)))
    for s in subjects:
        start = opens(short(s, g))
        pairs = sorted(g.predicate_objects(s),
                       key=lambda po: (pos(short(po[0], g), start), pos(short(po[1], g), start)))
        yield s, pairs


NUMBER_AS_TEXT = re.compile(r"^\s*-?\d+(\.\d+)?\s*[A-Za-z%]*\s*$")


def warnings(g):
    """Things that are valid Turtle but probably not what the writer meant."""
    out = []
    for s, p, o in sorted(g):
        if isinstance(o, Literal) and o.datatype in (None, XSD.string) \
                and not o.language and NUMBER_AS_TEXT.match(str(o)):
            out.append(f"{short(s, g)} {short(p, g)} {short(o, g)} is text, not a number.\n"
                       "  Write the number with no quote marks, and put any unit in the\n"
                       "  predicate's name instead.")
    subjects = {s for s in g.subjects()}
    for o in sorted({o for o in g.objects() if isinstance(o, URIRef)}):
        if o in subjects or g.namespace_manager.normalizeUri(o).startswith("<"):
            continue
        prefix = g.namespace_manager.normalizeUri(o).split(":")[0]
        same_prefix = [s for s in subjects
                       if g.namespace_manager.normalizeUri(s).split(":")[0] == prefix]
        if same_prefix and prefix not in ("tw", "rdfs", "xsd", "owl", "skos"):
            out.append(f"{short(o, g)} is pointed to, but the file says nothing\n"
                       "  about it. If that is a typing mistake, the arrow leads nowhere.")
    return out


def table(rows, headings):
    """Three columns, the object column wrapping onto further lines when it
    is long. One triple per block when even the first two columns are too
    wide for the page."""
    widths = [max(len(r[i]) for r in [*rows, headings]) for i in range(2)]
    room = WIDTH - widths[0] - widths[1] - 4
    if room >= 24:
        obj_w = min(room, max(len(r[2]) for r in [*rows, headings]))
        lines = ["  ".join(h.ljust(w) for h, w in zip(headings, [*widths, obj_w])).rstrip(),
                 "  ".join("-" * w for w in [*widths, obj_w])]
        pad = " " * (widths[0] + widths[1] + 4)
        for r in rows:
            parts = textwrap.wrap(r[2], obj_w, break_on_hyphens=False) or [""]
            lines.append(f"{r[0]:<{widths[0]}}  {r[1]:<{widths[1]}}  {parts[0]}".rstrip())
            lines += [pad + p for p in parts[1:]]
        return lines
    lines = []
    for r in rows:
        for h, c in zip(headings, r):
            parts = textwrap.wrap(c, WIDTH - 11, break_on_hyphens=False) or [""]
            lines.append(f"{h:<10} {parts[0]}")
            lines += [" " * 11 + p for p in parts[1:]]
        lines.append("")
    return lines[:-1]


def check(path):
    """Returns (ok, report text)."""
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    g = Graph()
    try:
        g.parse(data=text, format="turtle")
    except BadSyntax as err:
        line_no, line, message = explain(err, text)
        report = [f"{path.name}, line {line_no}: not valid Turtle.", "",
                  f"  {line_no:>3} | {line}", "", message]
        return False, "\n".join(report)
    rows, subjects = [], 0
    for s, pairs in file_order(g, text):
        subjects += 1
        rows += [(short(s, g), short(p, g), short(o, g)) for p, o in pairs]
    triples = "triple" if len(g) == 1 else "triples"
    things = "thing" if subjects == 1 else "things"
    report = [(f"{path.name} is valid Turtle: {len(g)} {triples} about "
               f"{subjects} {things}."), ""]
    report += table(rows, ("subject", "predicate", "object"))
    notes = warnings(g)
    if notes:
        report += ["", "Worth a second look:"] + ["  " + n for n in notes]
    return True, "\n".join(report)
