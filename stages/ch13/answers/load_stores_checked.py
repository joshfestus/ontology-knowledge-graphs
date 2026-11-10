"""load_stores.py, with a check on town codes (Task 13.3)."""

import csv
import sys
from datetime import date

from rdflib import Graph, Literal, Namespace
from rdflib.namespace import RDF, RDFS

TW = Namespace("https://tarnwick.example/ontology#")
STORE = Namespace("https://tarnwick.example/id/store/")
PLACE = Namespace("https://tarnwick.example/id/place/")


def opening_date(text, row_number):
    """The date in a cell, or stop with a message naming the row."""
    try:
        return date.fromisoformat(text)
    except ValueError:
        sys.exit(f"Row {row_number}: {text!r} is not a date "
                 "like 2019-04-01")


with open("places.csv", newline="", encoding="utf-8") as f:
    known_towns = {r["place_id"] for r in csv.DictReader(f)
                   if r["kind"] == "town"}

graph = Graph()
graph.bind("tw", TW)
graph.bind("store", STORE)
graph.bind("place", PLACE)

filename = sys.argv[1] if len(sys.argv) > 1 else "stores.csv"
with open(filename, newline="", encoding="utf-8") as f:
    for row_number, row in enumerate(csv.DictReader(f), start=2):
        store = STORE[row["store_id"].strip()]
        graph.add((store, RDF.type, TW.Store))
        graph.add((store, RDFS.label, Literal(row["name"].strip())))
        opened = opening_date(row["opened"].strip(), row_number)
        graph.add((store, TW.opened, Literal(opened)))
        town = row["town"].strip()
        if town and town not in known_towns:
            sys.exit(f"Row {row_number}: {town!r} is not a town "
                     "in places.csv")
        if town:
            graph.add((store, TW.locatedIn, PLACE[town]))

print(graph.serialize(format="turtle"), end="")
