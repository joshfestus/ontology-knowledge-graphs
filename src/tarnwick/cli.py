"""The `tarnwick` command.

    tarnwick check FILE...      is this Turtle valid, and what does it say?
    tarnwick build              build the full Tarnwick graph and validate it
    tarnwick question N         answer competency question N from QUESTIONS.md
    tarnwick search WORD --using LEVEL   find products by a category word
    tarnwick pg FILE...         the same facts as a property graph would hold them
    tarnwick define TERM        what a Tarnwick term is called and means
    tarnwick classes [FILE...]  the class tree, with how many things are in each
    tarnwick properties         the ontology's properties, from and to
    tarnwick implied [FILE...]  what the ontology concludes about some data
    tarnwick reason [FILE...]   what an OWL reasoner adds, and contradictions
    tarnwick validate [FILE...] check data against SHACL shapes
    tarnwick pitfalls           common ontology mistakes, checked
    tarnwick match [NAME...]    how typed supplier names are matched
    tarnwick pgraph             the graph as a property graph: nodes, edges
    tarnwick gql FILE           run a GQL query on the property graph
    tarnwick path FROM TO       the shortest path between two nodes
    tarnwick similar SKU        products bought by the same customers
    tarnwick diff OLD NEW       what changed between two ontology versions
    tarnwick chat QUESTION      ask a language model about Tarnwick
    tarnwick skos FILE.csv      a category spreadsheet as SKOS concepts
    tarnwick tree [FILE...]     a taxonomy as a tree, with its problems
    tarnwick coverage           which ontology terms each question needs
    tarnwick ask QUERY [FILE...] run a SPARQL query on Turtle files, or on the
                                full Tarnwick graph when no files are named
"""

import argparse
import sys


def main(argv=None):
    parser = argparse.ArgumentParser(prog="tarnwick")
    sub = parser.add_subparsers(dest="command", required=True)
    c = sub.add_parser("check", help="check Turtle files and list their triples")
    c.add_argument("files", nargs="+")
    sub.add_parser("build", help="build and validate the full graph")
    q = sub.add_parser("question", help="answer one competency question")
    q.add_argument("number", type=int)
    q.add_argument("--no-reasoner", action="store_true",
                   help="answer from the facts as written, without reasoning")
    s = sub.add_parser("search", help="find products by a category word")
    s.add_argument("word")
    s.add_argument("--using", default="website",
                   choices=("website", "vocabulary", "taxonomy", "thesaurus"))
    s.add_argument("--taxonomy", help="use this taxonomy file instead of Tarnwick's")
    pg = sub.add_parser("pg", help="show Turtle files as a property graph")
    pg.add_argument("files", nargs="+")
    cv = sub.add_parser("coverage", help="ontology terms used by the competency questions")
    cv.add_argument("--summary", action="store_true", help="only the totals and unused terms")
    cl = sub.add_parser("classes", help="the class tree and its members")
    cl.add_argument("files", nargs="*")
    d = sub.add_parser("define", help="what a Tarnwick term is called and means")
    d.add_argument("term")
    d.add_argument("--ontology", help="read this ontology file instead of Tarnwick's")
    pr = sub.add_parser("properties", help="the ontology's properties")
    pr.add_argument("--from", dest="source", help="only properties from this class")
    pr.add_argument("--to", dest="target", help="only properties to this class")
    pr.add_argument("--ontology", help="read this ontology file instead of Tarnwick's")
    im = sub.add_parser("implied", help="what the ontology concludes about data")
    im.add_argument("files", nargs="*")
    im.add_argument("--ontology", help="read this ontology file instead of Tarnwick's")
    im.add_argument("--data", action="store_true",
                    help="include all of Tarnwick's data (the default with no files)")
    rs = sub.add_parser("reason", help="run the OWL RL reasoner and report")
    rs.add_argument("files", nargs="*")
    rs.add_argument("--data", action="store_true",
                    help="include all of Tarnwick's data (the default with no files)")
    rs.add_argument("--about", help="list written and inferred facts about one thing")
    va = sub.add_parser("validate", help="check data against SHACL shapes")
    va.add_argument("files", nargs="*")
    va.add_argument("--shapes", help="use this shapes file instead of Tarnwick's")
    pf = sub.add_parser("pitfalls", help="check an ontology for common mistakes")
    pf.add_argument("--ontology", help="check this ontology file instead of Tarnwick's")
    mt = sub.add_parser("match", help="match typed supplier names to suppliers")
    mt.add_argument("names", nargs="*")
    mt.add_argument("--decisions", help="a CSV file of decisions people have made")
    sub.add_parser("pgraph", help="the graph as a property graph")
    gq = sub.add_parser("gql", help="run a GQL query file on the property graph")
    gq.add_argument("file")
    pa = sub.add_parser("path", help="shortest path between two nodes")
    pa.add_argument("start")
    pa.add_argument("goal")
    si = sub.add_parser("similar", help="products bought by the same customers")
    si.add_argument("sku")
    df = sub.add_parser("diff", help="compare two versions of an ontology")
    df.add_argument("old")
    df.add_argument("new")
    ch = sub.add_parser("chat", help="ask a language model about Tarnwick")
    ch.add_argument("question")
    ch.add_argument("--files", nargs="*", default=[],
                    help="spreadsheets from data/ to paste in with the question")
    sk = sub.add_parser("skos", help="a category spreadsheet as SKOS Turtle")
    sk.add_argument("file")
    tr = sub.add_parser("tree", help="a taxonomy as a tree, checked")
    tr.add_argument("files", nargs="*")
    tr.add_argument("--scheme", default="categories")
    a = sub.add_parser("ask", help="run a SPARQL query file")
    a.add_argument("query")
    a.add_argument("files", nargs="*")
    a.add_argument("--no-reasoner", action="store_true",
                   help="ask the facts as written, without reasoning")
    args = parser.parse_args(argv)

    if args.command == "check":
        from .check import check
        all_ok = True
        for n, f in enumerate(args.files):
            ok, report = check(f)
            print(("\n" if n else "") + report)
            all_ok &= ok
        return 0 if all_ok else 1
    if args.command == "build":
        from .build import main as build_main
        build_main()
        return 0
    if args.command == "question":
        from .build import print_table, run_query
        print_table(*run_query(f"q{args.number:02d}", reason=not args.no_reasoner))
        return 0
    if args.command == "search":
        from .search import report
        print(report(args.word, args.using, args.taxonomy))
        return 0
    if args.command == "pg":
        from .pg import report as pg_report
        print(pg_report(args.files))
        return 0
    if args.command == "classes":
        from .classes import report as classes_report
        print(classes_report(args.files))
        return 0
    if args.command == "define":
        from .define import report as define_report
        print(define_report(args.term, args.ontology))
        return 0
    if args.command == "properties":
        from .implied import properties_report
        print(properties_report(args.source, args.target, args.ontology))
        return 0
    if args.command == "implied":
        from .implied import implied_report
        print(implied_report(args.files, args.ontology, args.data or not args.files))
        return 0
    if args.command == "reason":
        from .reason import reason_report
        print(reason_report(args.files, args.data or not args.files, args.about))
        return 0
    if args.command == "validate":
        from .validate import validate_report
        print(validate_report(args.files, args.shapes))
        return 0
    if args.command == "pitfalls":
        from .pitfalls import pitfalls_report
        print(pitfalls_report(args.ontology))
        return 0
    if args.command == "match":
        from .resolve import match_report
        print(match_report(args.names, args.decisions))
        return 0
    if args.command == "pgraph":
        from .pgraph import summary_report
        print(summary_report())
        return 0
    if args.command == "gql":
        from .gql import report as gql_report
        print(gql_report(args.file))
        return 0
    if args.command == "path":
        from .pgraph import path_report
        print(path_report(args.start, args.goal))
        return 0
    if args.command == "similar":
        from .pgraph import similar_report
        print(similar_report(args.sku))
        return 0
    if args.command == "diff":
        from .diff import report as diff_report
        print(diff_report(args.old, args.new))
        return 0
    if args.command == "chat":
        from .chat import report as chat_report
        print(chat_report(args.question, args.files))
        return 0
    if args.command == "skos":
        from .skos import csv_to_turtle
        print(csv_to_turtle(args.file))
        return 0
    if args.command == "tree":
        from .skos import tree_report
        print(tree_report(args.files, args.scheme))
        return 0
    if args.command == "coverage":
        from .coverage import report as coverage_report
        print(coverage_report(args.summary))
        return 0
    if args.command == "ask":
        from .build import print_table, run_query
        ds = None
        if args.files:
            from .load import new_dataset
            ds = new_dataset()
            for f in args.files:
                ds.graph().parse(f)
        print_table(*run_query(args.query, ds, reason=not args.no_reasoner))
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
