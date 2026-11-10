"""Give every query file exactly the PREFIX lines it uses, in one fixed order.

Printed listings stay short and every query in the book declares its
prefixes the same way. Run after editing any file in queries/.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ORDER = [
    ("tw", "https://tarnwick.example/ontology#"),
    ("tid", "https://tarnwick.example/id/"),
    ("prod", "https://tarnwick.example/id/product/"),
    ("cat", "https://tarnwick.example/id/category/"),
    ("place", "https://tarnwick.example/id/place/"),
    ("rdfs", "http://www.w3.org/2000/01/rdf-schema#"),
    ("skos", "http://www.w3.org/2004/02/skos/core#"),
    ("xsd", "http://www.w3.org/2001/XMLSchema#"),
    ("dcterms", "http://purl.org/dc/terms/"),
]
KIND = {"product": "prod", "category": "cat", "place": "place"}


def tidy(text):
    lines = text.splitlines()
    comments = [l for l in lines if l.startswith("#")]
    body = "\n".join(l for l in lines
                     if not l.startswith("#") and not l.startswith("PREFIX")).strip()
    body = re.sub(r"\btid:(product|category|place)/([\w-]+)",
                  lambda m: f"{KIND[m.group(1)]}:{m.group(2)}", body)
    used = [(p, iri) for p, iri in ORDER if re.search(rf"(?<![\w-]){p}:", body)]
    width = max(len(p) for p, _ in used)
    prefixes = [f"PREFIX {p + ':':<{width + 1}} <{iri}>" for p, iri in used]
    return "\n".join(comments + prefixes + ["", body, ""])


def main():
    for path in sorted((ROOT / "queries").glob("*.rq")):
        path.write_text(tidy(path.read_text(encoding="utf-8")), encoding="utf-8")


if __name__ == "__main__":
    main()
