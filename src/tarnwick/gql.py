"""A small subset of GQL, the ISO standard property graph query language
(ISO/IEC 39075:2024), enough for Chapter 17.

    MATCH pattern [, pattern ...]
    [WHERE condition]
    RETURN item [AS name] [, ...]
    [ORDER BY item [DESC] [, ...]]
    [LIMIT n]

A pattern is a chain of nodes and edges drawn in text: (s:Store) for a node
with a variable and a label, {code: 'ST-BOU'} for properties it must have,
-[e:STOCKS]-> or <-[:PLACED]- for an edge and its direction. RETURN may use
COUNT(*), COUNT(DISTINCT x), SUM, AVG, MIN and MAX; the other items become
the groups, as in GQL. Within one MATCH no edge is used twice. Anything
outside this subset is reported as not supported, never guessed at.
"""

import re
from collections import defaultdict

TOKEN = re.compile(r"""\s*(?:
    (?P<num>\d+(?:\.\d+)?) |
    (?P<str>'[^']*') |
    (?P<arrow><-\[|\]->|\]-|-\[) |
    (?P<op><>|<=|>=|=|<|>) |
    (?P<word>[A-Za-z_][A-Za-z_0-9]*) |
    (?P<punct>[(){}\[\]:,.*+\-/])
    )""", re.VERBOSE)
KEYWORDS = {"MATCH", "WHERE", "RETURN", "ORDER", "BY", "DESC", "ASC", "LIMIT", "AS",
            "AND", "OR", "NOT", "DISTINCT"}
AGGREGATES = {"COUNT", "SUM", "AVG", "MIN", "MAX"}


class GQLError(Exception):
    pass


def tokenize(text):
    pos, out = 0, []
    while pos < len(text):
        if text[pos:].strip() == "":
            break
        m = TOKEN.match(text, pos)
        if not m or m.end() == pos:
            raise GQLError(f"cannot read the query at: {text[pos:pos + 20]!r}")
        kind = m.lastgroup
        out.append((kind, m.group(kind)))
        pos = m.end()
    return out


class Parser:
    def __init__(self, tokens):
        self.t, self.i = tokens, 0

    def peek(self, value=None):
        if self.i >= len(self.t):
            return None
        tok = self.t[self.i]
        if value is None or tok[1] == value:
            return tok
        if tok[0] == "word" and value in KEYWORDS | AGGREGATES and tok[1].upper() == value:
            return tok
        return None

    def keyword(self):
        """The upper case keyword at this point, or None."""
        tok = self.peek()
        if tok and tok[0] == "word" and tok[1].upper() in KEYWORDS | AGGREGATES:
            return tok[1].upper()
        return None

    def take(self, value=None):
        tok = self.peek(value) if value is not None else self.peek()
        if tok is None:
            found = self.peek()
            raise GQLError(f"expected {value!r} but found "
                           f"{found[1] if found else 'the end'!r}")
        self.i += 1
        return tok

    # --- query
    def query(self):
        self.take("MATCH")
        paths = [self.path()]
        while self.peek(","):
            self.take(",")
            paths.append(self.path())
        where = None
        if self.peek("WHERE"):
            self.take("WHERE")
            where = self.expr()
        self.take("RETURN")
        items = [self.item()]
        while self.peek(","):
            self.take(",")
            items.append(self.item())
        order = []
        if self.peek("ORDER"):
            self.take("ORDER")
            self.take("BY")
            while True:
                e = self.expr()
                desc = bool(self.peek("DESC"))
                if self.peek("DESC") or self.peek("ASC"):
                    self.i += 1
                order.append((e, desc))
                if not self.peek(","):
                    break
                self.take(",")
        limit = None
        if self.peek("LIMIT"):
            self.take("LIMIT")
            limit = int(self.take()[1])
        if self.peek():
            raise GQLError(f"not supported here: {self.peek()[1]!r}")
        return paths, where, items, order, limit

    def item(self):
        e = self.expr()
        name = None
        if self.peek("AS"):
            self.take("AS")
            name = self.take()[1]
        return e, name

    # --- patterns
    def node(self):
        self.take("(")
        var = label = None
        props = {}
        if self.peek() and self.peek()[0] == "word":
            var = self.take()[1]
        if self.peek(":"):
            self.take(":")
            label = self.take()[1]
        if self.peek("{"):
            self.take("{")
            while not self.peek("}"):
                k = self.take()[1]
                self.take(":")
                props[k] = self.literal()
                if self.peek(","):
                    self.take(",")
            self.take("}")
        self.take(")")
        return ("node", var, label, props)

    def edge(self):
        start = self.take()[1]
        if start not in ("-[", "<-["):
            raise GQLError("expected an edge such as -[:TYPE]->")
        var = type_ = None
        if self.peek() and self.peek()[0] == "word":
            var = self.take()[1]
        if self.peek(":"):
            self.take(":")
            type_ = self.take()[1]
        end = self.take()[1]
        if start == "-[" and end == "]->":
            direction = "out"
        elif start == "<-[" and end == "]-":
            direction = "in"
        elif start == "-[" and end == "]-":
            direction = "any"
        else:
            raise GQLError("an edge must point one way, such as -[:TYPE]->")
        return ("edge", var, type_, direction)

    def path(self):
        parts = [self.node()]
        while self.peek() and self.peek()[1] in ("-[", "<-["):
            parts.append(self.edge())
            parts.append(self.node())
        return parts

    # --- expressions
    def literal(self):
        kind, value = self.take()
        if kind == "num":
            return float(value) if "." in value else int(value)
        if kind == "str":
            return value[1:-1]
        raise GQLError(f"expected a value, found {value!r}")

    def expr(self):
        e = self.conj()
        while self.peek("OR"):
            self.take("OR")
            e = ("or", e, self.conj())
        return e

    def conj(self):
        e = self.comparison()
        while self.peek("AND"):
            self.take("AND")
            e = ("and", e, self.comparison())
        return e

    def comparison(self):
        e = self.arith()
        if self.peek() and self.peek()[0] == "op":
            op = self.take()[1]
            e = ("cmp", op, e, self.arith())
        return e

    def arith(self):
        e = self.term()
        while self.peek("+") or self.peek("-"):
            op = self.take()[1]
            e = ("math", op, e, self.term())
        return e

    def term(self):
        e = self.factor()
        while self.peek("*") or self.peek("/"):
            op = self.take()[1]
            e = ("math", op, e, self.factor())
        return e

    def factor(self):
        tok = self.peek()
        if tok is None:
            raise GQLError("the query ends too soon")
        if tok[1] == "(":
            self.take("(")
            e = self.expr()
            self.take(")")
            return e
        if tok[0] in ("num", "str"):
            return ("lit", self.literal())
        if self.keyword() in AGGREGATES and self.t[self.i + 1:self.i + 2] == [("punct", "(")]:
            fn = self.take()[1].upper()
            self.take("(")
            if fn == "COUNT" and self.peek("*"):
                self.take("*")
                self.take(")")
                return ("agg", "COUNT", False, None)
            distinct = bool(self.peek("DISTINCT"))
            if distinct:
                self.take("DISTINCT")
            arg = self.expr()
            self.take(")")
            return ("agg", fn, distinct, arg)
        if tok[0] == "word":
            var = self.take()[1]
            if self.peek("."):
                self.take(".")
                return ("prop", var, self.take()[1])
            return ("var", var)
        raise GQLError(f"not supported here: {tok[1]!r}")


def text_of(e):
    kind = e[0]
    if kind == "prop":
        return f"{e[1]}.{e[2]}"
    if kind == "var":
        return e[1]
    if kind == "agg":
        if e[3] is None:
            return f"{e[1]}(*)"
        return f"{e[1]}({'DISTINCT ' if e[2] else ''}{text_of(e[3])})"
    if kind == "lit":
        return repr(e[1])
    if kind == "math":
        return f"{text_of(e[2])} {e[1]} {text_of(e[3])}"
    return "?"


def has_agg(e):
    if e[0] == "agg":
        return True
    return any(has_agg(x) for x in e[1:] if isinstance(x, tuple))


# ------------------------------------------------------------- matching

def matches(pg, paths):
    """Every binding of variables to nodes and edges that fits all paths."""
    results = []

    def node_ok(n, label, props):
        return (label is None or n.label == label) and all(
            n.props.get(k) == v for k, v in props.items())

    def walk(pi, parts, k, binding, used):
        if pi == len(paths):
            results.append(dict(binding))
            return
        if k == 0:
            _, var, label, props = parts[0]
            if var and var in binding:
                cands = [binding[var]]
            else:
                cands = list(pg.nodes.values())
            for n in cands:
                if node_ok(n, label, props):
                    b = dict(binding)
                    if var:
                        b[var] = n
                    step(pi, parts, 1, b, used, n)
            return

    def step(pi, parts, k, binding, used, current):
        if k >= len(parts):
            nxt = pi + 1
            if nxt == len(paths):
                results.append(dict(binding))
            else:
                walk(nxt, paths[nxt], 0, binding, used)
            return
        _, evar, etype, direction = parts[k]
        _, nvar, label, props = parts[k + 1]
        options = []
        if direction in ("out", "any"):
            options += [(e, e.target) for e in pg.out[current.id]]
        if direction in ("in", "any"):
            options += [(e, e.source) for e in pg.into[current.id]]
        for e, other_id in options:
            if (etype and e.type != etype) or id(e) in used:
                continue
            other = pg.nodes[other_id]
            if not node_ok(other, label, props):
                continue
            if nvar and nvar in binding and binding[nvar] is not other:
                continue
            b = dict(binding)
            if evar:
                b[evar] = e
            if nvar:
                b[nvar] = other
            step(pi, parts, k + 2, b, used | {id(e)}, other)

    walk(0, paths[0], 0, {}, frozenset())
    return results


def value(e, b):
    kind = e[0]
    if kind == "lit":
        return e[1]
    if kind == "prop":
        if e[1] not in b:
            raise GQLError(f"no variable called {e[1]}")
        return b[e[1]].props.get(e[2])
    if kind == "var":
        x = b[e[1]]
        return x.props.get("sku") or x.props.get("code") or x.id
    if kind == "math":
        a, c = value(e[2], b), value(e[3], b)
        if a is None or c is None:
            return None
        return {"+": a + c, "-": a - c, "*": a * c, "/": a / c}[e[1]]
    if kind == "cmp":
        a, c = value(e[2], b), value(e[3], b)
        if a is None or c is None:
            return False
        return {"=": a == c, "<>": a != c, "<": a < c, ">": a > c,
                "<=": a <= c, ">=": a >= c}[e[1]]
    if kind == "and":
        return value(e[1], b) and value(e[2], b)
    if kind == "or":
        return value(e[1], b) or value(e[2], b)
    raise GQLError("an aggregate can only be used in RETURN or ORDER BY")


def aggregate(e, rows):
    kind = e[0]
    if kind == "agg":
        fn, distinct, arg = e[1], e[2], e[3]
        if arg is None:
            return len(rows)
        vals = [value(arg, b) for b in rows]
        if arg[0] == "var":
            vals = [b[arg[1]].id for b in rows]
        vals = [v for v in vals if v is not None]
        if distinct:
            vals = list(dict.fromkeys(vals))
        if fn == "COUNT":
            return len(vals)
        if not vals:
            return None
        if fn == "SUM":
            return sum(vals)
        if fn == "AVG":
            return sum(vals) / len(vals)
        return min(vals) if fn == "MIN" else max(vals)
    if kind == "math":
        a, c = aggregate(e[2], rows), aggregate(e[3], rows)
        return {"+": a + c, "-": a - c, "*": a * c, "/": a / c}[e[1]]
    if kind == "lit":
        return e[1]
    return value(e, rows[0])


def run(pg, text):
    paths, where, items, order, limit = Parser(tokenize(text)).query()
    rows = matches(pg, paths)
    if where is not None:
        rows = [b for b in rows if value(where, b)]
    names = [name or text_of(e) for e, name in items]
    if any(has_agg(e) for e, _ in items):
        keys = [e for e, _ in items if not has_agg(e)]
        groups = defaultdict(list)
        for b in rows:
            groups[tuple(value(k, b) for k in keys)].append(b)
        if not keys and not groups:
            groups[()] = []
        table = []
        for members in groups.values():
            table.append(([aggregate(e, members) if members or has_agg(e) else None
                           for e, _ in items], members))
    else:
        table = [([value(e, b) for e, _ in items], [b]) for b in rows]
    by_text = {text_of(e): i for i, (e, _) in enumerate(items)}
    by_text.update({name: i for i, (_, name) in enumerate(items) if name})
    for e, desc in reversed(order):
        idx = by_text.get(text_of(e)) if e[0] != "var" else by_text.get(e[1])
        if idx is None:
            idx = by_text.get(text_of(e))
        if idx is None:
            raise GQLError(f"ORDER BY {text_of(e)} must be one of the RETURN items")
        table.sort(key=lambda r, i=idx: (r[0][i] is None, r[0][i]), reverse=desc)
    out = [r for r, _ in table]
    if limit is not None:
        out = out[:limit]
    return names, out


def report(path):
    from pathlib import Path

    from .pgraph import property_graph
    text = Path(path).read_text(encoding="utf-8")
    try:
        names, rows = run(property_graph(), text)
    except GQLError as err:
        return f"Query not run: {err}."

    def show(v):
        if v is None:
            return ""
        if isinstance(v, float):
            return f"{v:.2f}"
        return str(v)

    cells = [names] + [[show(v) for v in r] for r in rows]
    widths = [max(len(c[i]) for c in cells) for i in range(len(names))]
    lines = []
    for n, row in enumerate(cells):
        lines.append("  ".join(v.ljust(w) for v, w in zip(row, widths)).rstrip())
        if n == 0:
            lines.append("  ".join("-" * w for w in widths))
    lines.append(f"({len(rows)} {'row' if len(rows) == 1 else 'rows'})")
    return "\n".join(lines)
