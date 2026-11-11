"""Turn the places spreadsheet into Turtle (Task 13.2)."""

import csv
import sys

from rdflib import Graph, Literal, Namespace
from rdflib.namespace import RDF, RDFS

TW = Namespace("https://tarnwick.example/ontology#")
PLACE = Namespace("https://tarnwick.example/id/place/")
KIND = {"country": TW.Country, "region": TW.Region,
        "state": TW.State, "town": TW.Town}

graph = Graph()
graph.bind("tw", TW)
graph.bind("place", PLACE)

filename = sys.argv[1] if len(sys.argv) > 1 else "places.csv"
with open(filename, newline="", encoding="utf-8") as f:
    for row_number, row in enumerate(csv.DictReader(f), start=2):
        place = PLACE[row["place_id"].strip()]
        kind = row["kind"].strip()
        if kind not in KIND:
            sys.exit(f"Row {row_number}: {kind!r} is not a kind of place")
        graph.add((place, RDF.type, KIND[kind]))
        graph.add((place, RDFS.label, Literal(row["name"].strip())))
        parent = row["part_of"].strip()
        if parent:
            graph.add((place, TW.partOf, PLACE[parent]))

print(graph.serialize(format="turtle"), end="")
