"""The reader's checker, and the chapter files it is shown on."""

from pathlib import Path

from rdflib import BNode, Graph
from rdflib.compare import isomorphic

from tarnwick.build import build
from tarnwick.check import check
from tarnwick.text import squeeze

STAGES = Path(__file__).resolve().parents[1] / "stages"
# files a chapter shows going wrong on purpose
DELIBERATELY_WRONG = {"missing-stop", "broken", "weight-as-text", "wrong-tree", "vendors", "wrong-bag",
                      "opened-before", "supplier-sample", "tents-as-classes",
                      "home-state", "quantity-domain", "two-statuses", "stock-as-arrow", "draft",
                      "quantity-both", "quantity-either", "every-product-supplied",
                      "same-as", "exact-match",
                      "product-shape", "products-sample", "tent-shape", "tarnwick-before",
                      "tarnwick-1.1", "tarnwick-2.0", "task-4-3", 
                      "task-8-2", "task-8-3", "task-9-3", "task-9-3-wrong", "task-10-2",
                      "task-10-2-meant", "task-11-2", "task-11-3", "cust-shape",
                      "customers", "recall-shape", "recall",
                      "task-23-1", "task-23-2"}
# files the book never shows through `tarnwick check`
NOT_CHECKED_IN_BOOK = {"wrong-tree", "opened-before", "tarnwick-before",
                       "tarnwick-1.0", "tarnwick-1.1", "tarnwick-2.0", "task-23-1",
                       "task-23-2"}


def test_every_stage_file_parses_except_the_deliberate_mistakes():
    for path in sorted(STAGES.rglob("*.ttl")):
        ok, report = check(path)
        broken = path.stem in {"missing-stop", "broken"}
        assert ok != broken, report


def test_stage_facts_are_true_of_tarnwick():
    """Every triple a chapter shows must also be in the full graph, so the
    book can never print a number the data does not have."""
    full = build()[0]
    for path in sorted(STAGES.rglob("*.ttl")):
        if path.stem in DELIBERATELY_WRONG | {"task-3-4"}:
            continue
        for triple in squeeze(Graph().parse(path)):
            if any(isinstance(node, BNode) for node in triple):
                continue          # blank nodes cannot be matched by name
            assert triple in full, f"{path.name}: {triple} is not in the Tarnwick data"


def test_messages_name_the_line_to_fix():
    report = check(STAGES / "ch03" / "missing-stop.ttl")[1]
    assert "Line 4 is missing the" in report
    report = check(STAGES / "ch03" / "broken.ttl")[1]
    assert "write tw:weightGrams, not tw:weight grams" in report


def test_reports_fit_the_printed_page():
    for path in sorted(STAGES.rglob("*.ttl")):
        if path.stem in NOT_CHECKED_IN_BOOK:
            continue
        assert max(len(line) for line in check(path)[1].splitlines()) <= 74, path


def test_task_answers_match_what_the_tasks_promise():
    answers = STAGES / "ch03" / "answers"
    assert check(answers / "task-3-1.ttl")[1].startswith(
        "task-3-1.ttl is valid Turtle: 22 triples about 4 things.")
    fixed = (STAGES / "ch03" / "broken.ttl").read_text()
    fixed = fixed.replace("tw:weight grams", "tw:weightGrams").replace(
        "2024-03-01 .", '"2024-03-01"^^xsd:date .')
    g = Graph().parse(data=fixed, format="turtle")
    assert isomorphic(g, Graph().parse(answers / "task-3-3.ttl"))
