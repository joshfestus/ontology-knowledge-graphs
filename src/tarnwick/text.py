"""Text written over several lines in a Turtle file means the same as text
written on one line. Turtle keeps the line breaks inside triple quoted text,
so every Tarnwick tool squeezes runs of spaces and line breaks in such text
down to single spaces as it reads a file."""

import re

from rdflib import Literal

SPACES = re.compile(r"\s+")


def squeeze_literal(value):
    if isinstance(value, Literal) and "\n" in str(value):
        return Literal(SPACES.sub(" ", str(value)).strip(), lang=value.language,
                       datatype=value.datatype)
    return value


def squeeze(graph):
    """Squeeze every multi-line literal in a graph, in place."""
    changed = [(s, p, o) for s, p, o in graph if squeeze_literal(o) is not o]
    for s, p, o in changed:
        graph.remove((s, p, o))
        graph.add((s, p, squeeze_literal(o)))
    return graph
