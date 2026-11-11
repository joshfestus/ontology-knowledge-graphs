"""Ontology version comparison in Chapter 23."""

from pathlib import Path

from tarnwick.diff import compare, load, report

CH23 = Path(__file__).resolve().parents[1] / "stages" / "ch23"
ROOT = Path(__file__).resolve().parents[1]


def test_deleting_breaks_question_15():
    r = report(CH23 / "tarnwick-1.0.ttl", CH23 / "tarnwick-2.0.ttl")
    assert "question 15 breaks" in r and "major version" in r


def test_deprecating_breaks_nothing():
    r = report(CH23 / "tarnwick-1.0.ttl", CH23 / "tarnwick-1.1.ttl")
    assert "question 15 should move" in r and "minor version" in r


def test_range_change_is_breaking(tmp_path):
    text = (CH23 / "tarnwick-1.0.ttl").read_text(encoding="utf-8")
    changed = text.replace(
        "rdfs:domain tw:Product ; rdfs:range xsd:integer .\n\ntw:releaseDate",
        "rdfs:domain tw:Product ; rdfs:range xsd:string .\n\ntw:releaseDate", 1)
    path = tmp_path / "changed.ttl"
    path.write_text(changed, encoding="utf-8")
    _, _, _, reshaped, _ = compare(load(CH23 / "tarnwick-1.0.ttl"), load(path))
    assert [str(t).rsplit("#")[-1] for t in reshaped] == ["seasonRating"]


def test_version_1_0_is_the_current_ontology():
    assert (CH23 / "tarnwick-1.0.ttl").read_text() == (ROOT / "ontology" / "tarnwick.ttl").read_text()
