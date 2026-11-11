"""The loader in Chapter 13."""

import subprocess
import sys
from pathlib import Path

from rdflib import Graph
from rdflib.compare import isomorphic

from tarnwick.build import build
from tarnwick.namespaces import GRAPH

ROOT = Path(__file__).resolve().parents[1]
CH13 = ROOT / "stages" / "ch13"


def run(*args):
    return subprocess.run([sys.executable, "load_stores.py", *args], cwd=CH13,
                          capture_output=True, text=True, check=False)


def test_first_loader_writes_what_the_build_loads():
    out = run()
    assert out.returncode == 0
    mine = Graph().parse(data=out.stdout, format="turtle")
    theirs = Graph()
    for t in build()[0].graph(GRAPH["source/stores.csv"]):
        theirs.add(t)
    assert len(mine) == 19 and isomorphic(mine, theirs)
    assert (CH13 / "stores.ttl").read_text(encoding="utf-8") == out.stdout


def test_messy_date_stops_with_the_row():
    out = run("stores-messy.csv")
    assert out.returncode == 1 and "Row 3" in out.stderr


def test_stage_stores_csv_is_the_real_one():
    assert (CH13 / "stores.csv").read_text() == (ROOT / "data" / "stores.csv").read_text()


def test_places_answer_writes_what_the_build_loads():
    out = subprocess.run([sys.executable, "answers/load_places.py"], cwd=CH13,
                         capture_output=True, text=True, check=False)
    mine = Graph().parse(data=out.stdout, format="turtle")
    theirs = Graph()
    for t in build()[0].graph(GRAPH["source/places.csv"]):
        theirs.add(t)
    assert len(mine) == 56 and isomorphic(mine, theirs)


def test_checked_loader_stops_on_unknown_town():
    out = subprocess.run([sys.executable, "answers/load_stores_checked.py",
                          "answers/stores-bnd.csv"], cwd=CH13,
                         capture_output=True, text=True, check=False)
    assert out.returncode == 1 and "'BND' is not a town" in out.stderr
