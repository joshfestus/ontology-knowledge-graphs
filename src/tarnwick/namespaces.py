"""The IRIs used throughout the Tarnwick graph.

tarnwick.example is a reserved domain (RFC 2606): it can never belong to a
real company, so the book's identifiers cannot collide with anyone's site.
"""

from rdflib import Namespace
from rdflib.namespace import DCTERMS, OWL, PROV, RDF, RDFS, SKOS, XSD

TW = Namespace("https://tarnwick.example/ontology#")
ID = Namespace("https://tarnwick.example/id/")
GRAPH = Namespace("https://tarnwick.example/graph/")

PREFIXES = {
    "tw": TW, "tid": ID, "rdf": RDF, "rdfs": RDFS, "owl": OWL,
    "skos": SKOS, "xsd": XSD, "prov": PROV, "dcterms": DCTERMS,
    "prod": ID["product/"], "cat": ID["category/"], "place": ID["place/"],
    "sup": ID["supplier/"], "store": ID["store/"], "cust": ID["customer/"],
    "order": ID["order/"], "line": ID["line/"], "stock": ID["stock/"],
    "prob": ID["problem/"], "pol": ID["policy/"],
    "ticket": ID["ticket/"], "recall": ID["recall/"], "company": ID["org/"],
    "match": ID["match/"], "rule": ID["rule/"], "source": ID["source/"],
    "schema": "https://schema.org/", "wd": "http://www.wikidata.org/entity/",
}


def iri(kind, key):
    """The IRI for one Tarnwick thing, such as iri("product", "TW-T102")."""
    return ID[f"{kind}/{key}"]
