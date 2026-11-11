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
    tarnwick extract [TICKET]   facts from ticket text, read by a language model
    tarnwick rag QUESTION       answer from retrieved text, graph facts, or both
    tarnwick write-query QUESTION   a language model writes the SPARQL
    tarnwick mcp                the graph's tools as an MCP server on stdio
    tarnwick agent CUSTOMER MESSAGE   a support agent using those tools
    tarnwick metric NAME            a metric from the semantic layer
    tarnwick measure            the model's answers with and without the graph
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
    cv.add_argument("--before", type=int, metavar="CHAPTER",
                    help="only the questions first answered before this chapter")
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
    va.add_argument("--data", action="store_true",
                    help="check the files together with all of Tarnwick's data")
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
    ex = sub.add_parser("extract", help="facts from ticket text, by a language model")
    ex.add_argument("ticket", nargs="?", help="a ticket ID such as T-024")
    ex.add_argument("--all", action="store_true", help="every ticket, one line each")
    ex.add_argument("--score", action="store_true", help="compare with the answer key")
    ex.add_argument("--turtle", action="store_true",
                    help="the facts that pass every check, as Turtle")
    ex.add_argument("--free", action="store_true", help="read without the ontology")
    ex.add_argument("--policy", help="read the return rules in a policy document")
    mc = sub.add_parser("mcp", help="serve the graph's tools over MCP on stdio")
    mc.add_argument("--demo", action="store_true",
                    help="start a server, send it three requests, print the messages")
    ag = sub.add_parser("agent", help="a support agent with the graph as its memory")
    ag.add_argument("customer")
    ag.add_argument("message")
    tl = sub.add_parser("tool", help="call one agent tool directly, as an agent would")
    tl.add_argument("name")
    tl.add_argument("arguments", nargs="*", metavar="NAME=VALUE",
                    help="the tool's arguments, such as customer=C-0083")
    me = sub.add_parser("metric", help="a metric from the semantic layer")
    me.add_argument("names", nargs="*", metavar="NAME",
                    help="metrics or business terms, such as revenue")
    me.add_argument("--by", help="a dimension to split the metric by")
    me.add_argument("--period", help="a period: 2026-Q3, 2026-09 or 2026")
    me.add_argument("--as-of", default=None, help="the reporting date")
    me.add_argument("--show-query", action="store_true",
                    help="print the SPARQL instead of running it")
    me.add_argument("--list", action="store_true", help="every metric and dimension")
    me.add_argument("--check", action="store_true",
                    help="check every metric and dimension, and run each request")
    me.add_argument("--ask", metavar="QUESTION",
                    help="a language model turns a question into a request")
    wq = sub.add_parser("write-query", help="a language model writes the SPARQL")
    wq.add_argument("question", nargs="?")
    wq.add_argument("--no-map", action="store_true", help="give the model no ontology map")
    wq.add_argument("--no-reasoner", action="store_true",
                    help="run on the facts as written, without inferred facts")
    wq.add_argument("--bench", action="store_true",
                    help="score the model on the competency questions")
    wq.add_argument("--all-rows", action="store_true", help="print every row of the result")
    wq.add_argument("--map-file", help="give the model this map instead of Tarnwick's")
    wq.add_argument("--map", dest="show_map", action="store_true",
                    help="print the ontology map the model is given")
    ms = sub.add_parser("measure", help="the model's answers with and without the graph")
    ms.add_argument("--runs", type=int, default=3, help="times each question is asked")
    ms.add_argument("--question", type=int, metavar="N", help="one question, run by run")
    ms.add_argument("--terms", action="store_true",
                    help="how often the written queries used each inverse pair")
    ms.add_argument("--citations", action="store_true",
                    help="whether cited sentences say what their facts say")
    ms.add_argument("--using", default="both", choices=("text", "graph", "both"),
                    help="retrieval for --citations")
    ms.add_argument("--summary", action="store_true", help="with --citations, counts only")
    ms.add_argument("--facts-only", action="store_true",
                    help="with --citations, the first judge, which never saw the question")
    rg = sub.add_parser("rag", help="answer from retrieved text or graph facts")
    rg.add_argument("question")
    rg.add_argument("--using", default="graph", choices=("text", "graph", "both"))
    rg.add_argument("--top", type=int, default=3,
                    help="how many policy paragraphs to retrieve")
    rg.add_argument("--answer-only", action="store_true",
                    help="leave out what was given to the model")
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
        print(validate_report(args.files, args.shapes, args.data))
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
    if args.command == "mcp":
        from . import mcp
        if args.demo:
            print(mcp.demo())
        else:
            mcp.serve()
        return 0
    if args.command == "agent":
        from .agent import report as agent_report
        print(agent_report(args.customer, args.message))
        return 0
    if args.command == "tool":
        from textwrap import wrap

        from .tools import call
        given = dict(a.split("=", 1) for a in args.arguments if "=" in a)
        text, _ = call(args.name, given)
        for line in text.split("\n"):
            print("\n".join(wrap(line, 74, subsequent_indent="  ")) or "")
        return 0
    if args.command == "metric":
        from . import metrics
        if args.list:
            print(metrics.listing())
            return 0
        if args.check:
            ok, text = metrics.check()
            print(text)
            return 0 if ok else 1
        if args.ask:
            print(metrics.ask(args.ask))
            return 0
        try:
            print(metrics.report(args.names, by=args.by, period=args.period,
                                 as_of=args.as_of or metrics.TODAY,
                                 show_query=args.show_query))
        except metrics.MetricError as e:
            print(e)
            return 1
        return 0
    if args.command == "write-query":
        from . import textquery
        if args.show_map:
            print(textquery.ontology_map())
            return 0
        map_text = None
        if args.map_file:
            from pathlib import Path
            map_text = Path(args.map_file).read_text(encoding="utf-8").rstrip("\n")
        if args.bench:
            print(textquery.bench(not args.no_map, map_text))
        else:
            print(textquery.report(args.question, not args.no_map,
                                   not args.no_reasoner, map_text,
                                   None if args.all_rows else 12))
        return 0
    if args.command == "measure":
        from . import measure
        if args.citations:
            print(measure.citations(args.runs, args.using, not args.summary,
                                    not args.facts_only))
        elif args.terms:
            print(measure.terms_report(args.runs))
        elif args.question:
            print(measure.question_report(args.question, args.runs))
        else:
            print(measure.report(args.runs))
        return 0
    if args.command == "rag":
        from .rag import report as rag_report
        print(rag_report(args.question, args.using, not args.answer_only, args.top))
        return 0
    if args.command == "extract":
        from . import extract
        if args.policy:
            print(extract.policy(args.policy))
        elif args.ticket:
            print(extract.one(args.ticket, args.free))
        elif args.score:
            print(extract.score())
        elif args.turtle:
            print(extract.turtle())
        else:
            print(extract.table())
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
        print(coverage_report(args.summary, args.before))
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
