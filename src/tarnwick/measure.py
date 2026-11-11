"""`tarnwick measure`: does the graph make the model's answers better?
(Chapter 22)

    tarnwick measure                 the questions with and without the graph
    tarnwick measure --question N    one question's answers, run by run
    tarnwick measure --terms         which ontology terms the written queries used
    tarnwick measure --citations     whether cited sentences say what their facts say

Without the graph, the model is given every file in data/, pasted in as
they are, with the question, and asked for its answer as a table. With the
graph, it writes a SPARQL query from the ontology map, as in Chapter 19,
and the query's rows are the answer. Both are scored by the same rule
against the reference query for the question.

Each question is asked RUNS times in each way. Run 1 of the graph side is
the run printed in Chapter 19. A language model does not give the same
answer twice, so a single run says little; the spread across runs is part
of the result.
"""

import re
import statistics
import time
from pathlib import Path

from .build import build
from .llm import ask
from .textquery import BENCH, TooSlow, attempt, reference, right, run

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
RUNS = 3
WIDTH = 74


# ------------------------------------------------------ without the graph

FILES_INSTRUCTIONS = (
    "You answer questions about Tarnwick Supply, an outdoor equipment "
    "retailer, using only its files, which are pasted below. Today is "
    "2026-09-30. Answer with a table: one row for each item in the "
    "answer, and a column for each thing the question asks for. Give "
    "products by SKU and other things by the identifier the files use, "
    "or by name where there is none. Write dates as YYYY-MM-DD and "
    "numbers as plain digits, with no units, currency signs or thousands "
    "separators. If the files do not answer the question, return no rows "
    "and say why in the note.")
FILES_SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["rows", "note"],
    "properties": {
        "rows": {"type": "array", "items": {"type": "array", "items": {"type": "string"}}},
        "note": {"type": "string"}}}


def all_files():
    """Every data file, in a fixed order, as one block of text."""
    paths = sorted(DATA.glob("*.csv")) + sorted((DATA / "policies").glob("*.md"))
    return "\n\n".join(f"File {p.relative_to(DATA).as_posix()}:\n"
                       f"{p.read_text(encoding='utf-8')}" for p in paths)


def from_files(question, run_no):
    """(rows, the saved call)"""
    instructions = FILES_INSTRUCTIONS + "\n\n" + all_files()
    answer, saved = ask(instructions, f"Question: {question}", schema=FILES_SCHEMA,
                        max_output_tokens=8000, run=run_no, details=True)
    return [tuple(r) for r in answer["rows"]], [saved]


# --------------------------------------------------------- with the graph

def from_graph(question, run_no):
    """(rows, the saved calls). Rows are None when no query could be run."""
    calls = []
    _first, _problems, final, left = attempt(question, run=run_no, calls=calls)
    if left:
        return None, calls
    started = time.monotonic()
    try:
        rows = run(final)[1]
    except TooSlow:
        rows = None
    except Exception:                      # noqa: BLE001 a failed run answers nothing
        rows = []
    calls.append({"seconds": time.monotonic() - started, "cost_usd": 0.0, "query": True})
    return rows, calls


# ------------------------------------------------------------- scoring

def expected(n, ds):
    return reference(n, ds)


def trial(n, side, run_no, ds):
    """One question, one side, one run: a dict of what happened."""
    ask_side = from_files if side == "files" else from_graph
    rows, calls = ask_side(BENCH[n], run_no)
    timed = [c["seconds"] for c in calls if "seconds" in c]
    model_calls = [c for c in calls if not c.get("query")]
    return {
        "right": rows is not None and right(n, rows, ds),
        "answered": bool(rows),
        "rows": rows,
        "cost": sum(c.get("cost_usd", 0.0) for c in model_calls),
        "seconds": sum(timed) if len(timed) == len(calls) else None,
        "queries": [c["answer"]["query"] for c in model_calls
                    if isinstance(c.get("answer"), dict) and "query" in c["answer"]],
    }


def trials(runs=RUNS):
    """{(question, side, run): trial}"""
    ds = build()[0]
    return {(n, side, r): trial(n, side, r, ds)
            for n in BENCH for side in ("files", "graph") for r in range(1, runs + 1)}


def spread(values):
    return f"{min(values)} to {max(values)}" if min(values) != max(values) else str(values[0])


def report(runs=RUNS):
    t = trials(runs)
    rr = range(1, runs + 1)
    out = [f"{'':<5}{'right, of ' + str(runs) + ' runs':^22}".rstrip(),
           f"{'Q':<5}{'files':>8}{'graph':>9}   change",
           f"{'-' * 3:<5}{'-' * 6:>8}{'-' * 6:>9}   {'-' * 12}"]
    better, worse = [], []
    for n in BENCH:
        f = sum(t[n, "files", r]["right"] for r in rr)
        g = sum(t[n, "graph", r]["right"] for r in rr)
        change = ""
        if g > f:
            change = "graph better"
            better.append(n)
        elif f > g:
            change = "graph worse"
            worse.append(n)
        out.append(f"Q{n:<4}{f:>8}{g:>9}   {change}")

    def side_lines(side):
        right = [sum(t[n, side, r]["right"] for n in BENCH) for r in rr]
        always = sum(all(t[n, side, r]["right"] for r in rr) for n in BENCH)
        never = sum(not any(t[n, side, r]["right"] for r in rr) for n in BENCH)
        answered = [sum(t[n, side, r]["answered"] for n in BENCH) for r in rr]
        cost = statistics.mean(t[n, side, r]["cost"] for n in BENCH for r in rr)
        secs = [t[n, side, r]["seconds"] for n in BENCH for r in rr
                if t[n, side, r]["seconds"] is not None]
        return [", ".join(map(str, right)), str(always), str(never),
                spread(answered), f"${cost:.4f}",
                f"{statistics.median(secs):.1f}" if secs else "not timed"]

    labels = ["Right, run by run", "Right in every run", "Right in no run",
              "Gave rows", "Cost per question", "Seconds, median"]
    f, g = side_lines("files"), side_lines("graph")
    out += ["", f"{'':<22}{'files':>18}{'graph':>18}"]
    out += [f"{a:<22}{b:>18}{c:>18}" for a, b, c in zip(labels, f, g)]
    out += ["", f"Graph better on {len(better)} questions, worse on {len(worse)}"
            + (": " + ", ".join(f"Q{n}" for n in worse) + "." if worse else ".")]
    return "\n".join(out)


def fit(cells, width=WIDTH - 4):
    """Cells joined by " | ", leaving off whole cells at the end, marked
    "...", when the row would be too wide."""
    line = " | ".join(cells)
    while len(line) > width and len(cells) > 1:
        cells = cells[:-1]
        line = " | ".join(cells) + " | ..."
    return line[:width]


def question_report(n, runs=RUNS):
    """One question's answers, run by run, first rows only."""
    ds = build()[0]
    want = expected(n, ds)
    from textwrap import wrap
    out = wrap(f"Q{n}. {BENCH[n]}", WIDTH) + ["", f"Reference answer: {len(want)} rows"]
    for side in ("files", "graph"):
        for r in range(1, runs + 1):
            got = trial(n, side, r, ds)
            rows = got["rows"]
            shown = ("no query run" if rows is None else
                     f"{len(rows)} rows, {'right' if got['right'] else 'wrong'}")
            out.append(f"{side} run {r}: {shown}")
            for row in (rows or [])[:3]:
                out.append("    " + fit([("" if v is None else str(v)) for v in row]))
    return "\n".join(out)


# ----------------------------------------------- which terms were used

INVERSES = {"lineOf": "hasLine", "replaces": "replacedBy", "supplies": "suppliedBy"}


def terms_report(runs=RUNS):
    """How often the written queries used each inverse pair."""
    t = {k: v for k, v in trials(runs).items() if k[1] == "graph"}
    queries = [q for v in t.values() for q in v["queries"]]
    out = [f"{len(queries)} written queries, from {len(BENCH)} questions "
           f"and {runs} runs.", "",
           f"{'used':<14}{'queries':>8}   {'its inverse':<14}{'queries':>8}",
           f"{'-' * 12:<14}{'-' * 7:>8}   {'-' * 12:<14}{'-' * 7:>8}"]
    for a, b in INVERSES.items():
        ca = sum(bool(re.search(rf"tw:{a}\b", q)) for q in queries)
        cb = sum(bool(re.search(rf"tw:{b}\b", q)) for q in queries)
        out.append(f"{'tw:' + a:<14}{ca:>8}   {'tw:' + b:<14}{cb:>8}")
    return "\n".join(out)


# --------------------------------------------- do citations say the facts?

CUSTOMER_QUESTIONS = [
    "I bought an Insulated Air Mat four months ago and it keeps going flat. "
    "Can I return it?",
    "I unpacked my Closed Cell Foam Mat and broke the packaging seal, but I "
    "have not used it. Can I still return it?",
    "I have the old Down Sleeping Bag 20F. Is it still sold, and what "
    "replaced it?",
    "I have only worn my Leather Hiking Boot Women's indoors. It is 45 days "
    "since delivery. Can I still return them?",
    "I mailed my Leather Hiking Boot Women's back for a refund. How long "
    "does the refund take?",
    "My Backpacking Tent 2P arrived 20 days ago and I have not opened it. "
    "Can I return it?",
    "My Trail Running Shoe split after two months of running on trails. "
    "Can I return it?",
    "Is the Down Insulated Jacket still sold, and what replaced it?",
    "Who pays the shipping if I send back my Insulated Air Mat?",
    "I opened the seal on my Self Inflating Mat ten days ago. Can I return it?",
    "I ordered a Winter Tent 2P from Tarnwick Online. Can I return it to a "
    "store?",
    "I bought a Daypack 22 L 40 days ago and never used it. Can I return it?",
    "How long do I have to return a Waterproof Jacket Women's?",
    "Has the Liquid Fuel Stove been recalled?",
    "It is 25 days since my Down Sleeping Bag 0F arrived, and the compression "
    "sack is unbroken. Can I return it?",
    "What is the remedy for the Insulated Air Mat recall?",
]

JUDGE_FIRST = (
    "You check a customer service answer against the numbered facts it was "
    "written from. For each sentence, read only the facts it cites and "
    "decide: \"supported\" if everything the sentence says is in those "
    "facts; \"misstated\" if it changes something in them, such as a number, "
    "a condition, a product or who does what; \"added\" if it makes a claim "
    "the cited facts do not contain. Give a short reason for any verdict "
    "other than supported.")
JUDGE_INSTRUCTIONS = (
    "You check a customer service answer against the customer's question "
    "and the numbered facts it was written from. What the customer says "
    "about their own situation, such as how long ago something arrived, "
    "may be taken as true. For each sentence, read the question and the "
    "facts it cites and decide: \"supported\" if everything the sentence "
    "says follows from those; \"misstated\" if it changes something in "
    "them, such as a number, a date, a condition, a product or who does "
    "what; \"added\" if it makes a claim neither the question nor the cited "
    "facts contain. Give a short reason for any verdict other than "
    "supported.")
JUDGE_SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["sentences"],
    "properties": {"sentences": {"type": "array", "items": {
        "type": "object", "additionalProperties": False,
        "required": ["number", "verdict", "reason"],
        "properties": {"number": {"type": "integer"},
                       "verdict": {"type": "string",
                                   "enum": ["supported", "misstated", "added"]},
                       "reason": {"type": "string"}}}}}}


def cited_sentences(reply):
    """The reply's sentences that cite at least one fact, with the facts they
    cite, joining a short sentence such as "Yes." to the one after it, as
    the check in Chapter 18 does."""
    from .rag import CITE, SENTENCE
    sentences = []
    for s in SENTENCE.split(reply.replace("\n", " ")):
        last = sentences[-1] if sentences else ""
        if last and len(last.split()) <= 3 and not CITE.search(last):
            sentences[-1] += " " + s
        else:
            sentences.append(s)
    out = []
    for s in sentences:
        nums = sorted({int(n) for m in CITE.findall(s) for n in re.findall(r"\d+", m)})
        if nums:
            out.append((s.strip(), nums))
    return out


def judge(facts, sentences, run_no, question=None):
    """{sentence number: verdict}. Without the question, the judge sees
    only the facts, as the first version of this check did."""
    lines = [f"Customer question: {question}", ""] if question else []
    lines += ["Facts:"] + [f"[{n}] {text}" for n, (text, _) in enumerate(facts, 1)]
    lines += ["", "Sentences:"] + [f"{i}. {s}" for i, (s, _) in enumerate(sentences, 1)]
    answer = ask(JUDGE_INSTRUCTIONS if question else JUDGE_FIRST, "\n".join(lines),
                 schema=JUDGE_SCHEMA,
                 max_output_tokens=3000, run=run_no)
    return {v["number"]: v for v in answer["sentences"]}


def citations(runs=RUNS, using="both", show=True, with_question=True):
    from .rag import retrieve
    from .chat import plain
    from .rag import INSTRUCTIONS as RAG_INSTRUCTIONS
    tally = {"supported": 0, "misstated": 0, "added": 0}
    flagged = []
    for r in range(1, runs + 1):
        for q in CUSTOMER_QUESTIONS:
            facts = retrieve(q, using)
            numbered = [f"[{n}] {text}" for n, (text, _) in enumerate(facts, 1)]
            request = "Facts:\n" + "\n".join(numbered) + f"\n\nCustomer question: {q}"
            reply = plain(ask(RAG_INSTRUCTIONS, request, max_output_tokens=1200,
                              run=r)).strip()
            sentences = cited_sentences(reply)
            if not sentences:
                continue
            verdicts = judge(facts, sentences, r, q if with_question else None)
            for i, (s, nums) in enumerate(sentences, 1):
                v = verdicts.get(i, {"verdict": "supported", "reason": ""})
                tally[v["verdict"]] += 1
                if v["verdict"] != "supported":
                    flagged.append((r, q, s, nums, v, facts))
    total = sum(tally.values())
    out = [f"{len(CUSTOMER_QUESTIONS)} customer questions, {runs} runs, "
           f"retrieval using {using}: {total} cited sentences.",
           "The judge saw the facts" + (" and the question." if with_question
                                        else " only."), ""]
    for k, v in tally.items():
        out.append(f"{k:<12}{v:>5}{100 * v / total:>7.1f}%")
    if show and flagged:
        from textwrap import wrap
        out += ["", "Sentences the judge flagged:"]
        for r, q, s, nums, v, facts in flagged:
            out.append("")
            out += wrap(f"Run {r}. {q}", WIDTH)
            out += wrap(f'Sentence: "{s}"', WIDTH, initial_indent="  ",
                        subsequent_indent="    ")
            for n in nums:
                if 1 <= n <= len(facts):
                    out += wrap(f"[{n}] {facts[n - 1][0]}", WIDTH,
                                initial_indent="  ", subsequent_indent="    ")
            out += wrap(f"Judge: {v['verdict']}. {v['reason']}", WIDTH,
                        initial_indent="  ", subsequent_indent="    ")
    return "\n".join(out)
