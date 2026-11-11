"""Make every Turtle and SPARQL file fit the printed page, 74 columns.

Long quoted text in Turtle becomes triple quoted text over several lines.
Turtle keeps the line breaks inside it, so every program that reads these
files squeezes the spaces in such text back to single spaces
(`tarnwick.text.squeeze`). Long comment lines in queries wrap onto
continuation lines. Anything else that is too long is reported for a person
to fix, because only a person can choose a good place to break it.
"""

import re
import sys
import textwrap
from pathlib import Path

WIDTH = 74
ROOT = Path(__file__).resolve().parent.parent
QUOTED = re.compile(r'^(\s*)(.*?)"((?:[^"\\]|\\.)*)"(@[A-Za-z-]+)?(\s*[;.,]?\s*)$')


def fit_turtle_line(line):
    """Wrap one line of quoted text into triple quoted text that fits."""
    if len(line) <= WIDTH or '"""' in line:
        return [line]
    m = QUOTED.match(line)
    if not m:
        return [line]
    indent, before, text, lang, after = m.groups()
    tail = '"""' + (lang or "") + (" " + after.strip() if after.strip() else "")
    first = f'{indent}{before}"""'
    inner = indent + "    "
    lines, cur, room = [], first, WIDTH
    for word in text.split():
        candidate = cur + ("" if cur.endswith('"""') else " ") + word
        if len(candidate) <= room:
            cur = candidate
        else:
            lines.append(cur)
            cur = inner + word
    if len(cur + tail) > WIDTH:
        words = cur.split()
        lines.append(inner + " ".join(words[:-1]))
        cur = inner + words[-1]
    lines.append(cur + tail)
    return lines


def fit_query_line(line):
    if len(line) <= WIDTH or not line.startswith("#"):
        return [line]
    m = re.match(r"^(#\s*(?:\d+\.\s+)?)(.*)$", line)
    head, text = m.groups()
    words = textwrap.wrap(text, WIDTH - len(head))
    return [head + words[0]] + ["#" + " " * (len(head) - 1) + w for w in words[1:]]


def fit(path):
    fitter = fit_turtle_line if path.suffix == ".ttl" else fit_query_line
    lines = path.read_text(encoding="utf-8").split("\n")
    out = [piece for line in lines for piece in fitter(line)]
    path.write_text("\n".join(out), encoding="utf-8")
    return [(n, line) for n, line in enumerate(out, 1) if len(line) > WIDTH]


def main(paths):
    left = 0
    for p in paths:
        for n, line in fit(Path(p)):
            print(f"{p}:{n}: {len(line)} columns: {line.strip()[:60]}")
            left += 1
    return 1 if left else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
