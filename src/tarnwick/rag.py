"""`tarnwick rag QUESTION --using text|graph|both`: answer a customer's
question from what is retrieved first (Chapter 18).

    --using text    the policy paragraphs that share the most words with
                    the question
    --using graph   facts about the products the question names, gathered
                    from the knowledge graph, each with the file it came from
    --using both    the graph facts and the policy paragraphs together

The model is told to use only the numbered facts it is given and to cite
them. The answer is then checked: every sentence must cite a fact, and every
cited number must be one the model was given.
"""

import re
from collections import Counter

from rdflib.namespace import DCTERMS, PROV, RDF, RDFS, SKOS

from .build import build
from .chat import plain
from .extract import products
from .llm import ask
from .load import DATA, TW
from .namespaces import iri

WIDTH = 74
STOP = {
    "a", "about", "after", "again", "all", "also", "am", "an", "and",
    "any", "are", "as", "at", "be", "been", "before", "but", "by", "can",
    "could", "did", "do", "does", "for", "from", "had", "has", "have",
    "how", "i", "if", "in", "into", "is", "it", "its", "just", "me", "my",
    "no", "not", "of", "on", "or", "our", "so", "than", "that", "the",
    "their", "them", "then", "there", "these", "they", "this", "to",
    "too", "was", "we", "were", "what", "when", "where", "which", "who",
    "why", "will", "with", "would", "you", "your"}


# ------------------------------------------------------------- text chunks

def words(text):
    out = []
    for w in re.findall(r"[a-z0-9]+", text.lower()):
        if w in STOP or len(w) < 2:
            continue
        out.append(w[:-1] if len(w) > 3 and w.endswith("s") else w)
    return out


def chunks():
    """Every paragraph of every policy document, with the file it is from.
    The title and the version line are left out."""
    out = []
    for path in sorted((DATA / "policies").glob("*.md")):
        paras = path.read_text(encoding="utf-8").split("\n\n")[2:]
        for p in paras:
            out.append((" ".join(p.split()), f"data/policies/{path.name}"))
    return out


def text_retrieve(question, k=3):
    """The k paragraphs that share the most distinct words with the
    question, best first."""
    q = set(words(question))
    scored = [(len(q & set(words(text))), n, text, src)
              for n, (text, src) in enumerate(chunks())]
    scored = [s for s in scored if s[0] > 0]
    best = sorted(scored, key=lambda s: (-s[0], s[1]))[:k]
    return [(text, [src]) for _, _, text, src in best]


# ------------------------------------------------------------ graph facts

def find_products(question):
    """The products a question is about, read by the model from the
    product list, the way Chapter 16 read tickets."""
    names = products()
    instructions = ("List the Tarnwick products this customer question is about, "
                    "using only the codes below. Give an empty list if it names "
                    "none.\n\n" + "\n".join(f"{s} {n}" for s, n in names.items()))
    schema = {"type": "object", "additionalProperties": False, "required": ["skus"],
              "properties": {"skus": {"type": "array",
                                      "items": {"type": "string", "enum": list(names)}}}}
    return ask(instructions, question, schema=schema, max_output_tokens=600)["skus"]


RULE = """
PREFIX tw:   <https://tarnwick.example/ontology#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
SELECT ?rule ?category WHERE {
  ?product tw:inCategory/skos:broader* ?category .
  ?rule tw:appliesToCategory ?category .
  FILTER NOT EXISTS {
    ?product tw:inCategory/skos:broader* ?nearer .
    ?nearer skos:broader+ ?category .
    ?other tw:appliesToCategory ?nearer .
  }
}"""


def sources(ds, triples):
    """Where a set of triples came from: the file or program step that
    made each named graph holding them."""
    found = []
    for t in triples:
        for g in ds.graphs(t):
            name = g.identifier
            label = None
            for s in ds.default_graph.objects(name, DCTERMS.source):
                label = str(ds.default_graph.value(s, RDFS.label))
            for s in ds.default_graph.objects(name, PROV.wasGeneratedBy):
                label = label or str(ds.default_graph.value(s, RDFS.label))
            if label and label not in found:
                found.append(label)
    return found


def graph_facts(skus, ds=None):
    """Facts about each product, as sentences, each with its sources."""
    ds = ds or build()[0]

    def label(node):
        return str(ds.value(node, RDFS.label) or ds.value(node, SKOS.prefLabel))

    facts = []
    for sku in skus:
        p = iri("product", sku)
        name = label(p)
        for cat in ds.objects(p, TW.inCategory):
            chain, node = [label(cat)], cat
            triples = [(p, TW.inCategory, cat),
                       (cat, SKOS.prefLabel, ds.value(cat, SKOS.prefLabel))]
            while (up := ds.value(node, SKOS.broader)) is not None:
                triples.append((node, SKOS.broader, up))
                chain.append(label(up))
                node = up
            text = f"The {name} ({sku}) is in the category {chain[0]}"
            if len(chain) > 1:
                text += ", which is part of " + ", which is part of ".join(chain[1:])
            facts.append((text + ".", sources(ds, triples)))
        status = ds.value(p, TW.hasStatus)
        facts.append((f"The {name} has the status {label(status)}.",
                      sources(ds, [(p, TW.hasStatus, status)])))
        new = ds.value(p, TW.replacedBy)
        if new is not None:
            facts.append(((f"The {name} was replaced by the {label(new)} "
                          f"({ds.value(new, TW.sku)})."),
                          sources(ds, [(p, TW.replacedBy, new)])))
        for rule, cat in ds.query(RULE, initBindings={"product": p}):
            days = ds.value(rule, TW.returnWindowDays)
            cond = ds.value(rule, TW.condition)
            pol = ds.value(rule, TW.definedIn)
            facts.append(((f"The return rule for the {name} is the {label(rule)}, set on "
                          f"{label(cat)}, the nearest category above it with a rule: "
                          f"{days} days after delivery, on condition: {cond} It is "
                          f"stated in the {label(pol)}."),
                          sources(ds, [(rule, TW.appliesToCategory, cat),
                                       (rule, TW.returnWindowDays, days),
                                       (rule, TW.condition, cond),
                                       (rule, TW.definedIn, pol)])))
        for recall in ds.subjects(TW.product, p):
            if (recall, RDF.type, TW.Recall) not in ds:
                continue
            when, why, remedy = (ds.value(recall, x) for x in
                                 (TW.announced, TW.reason, TW.remedy))
            pol = ds.value(recall, TW.handledUnder)
            facts.append(((f"The {name} was recalled on {when}. Reason: {why} "
                          f"Remedy: {remedy} The recall is handled under the "
                          f"{label(pol)}."),
                          sources(ds, [(recall, TW.product, p), (recall, TW.reason, why),
                                       (recall, TW.remedy, remedy),
                                       (recall, TW.handledUnder, pol)])))
    return facts


# -------------------------------------------------------------- answering

INSTRUCTIONS = (
    "You answer questions from customers of Tarnwick Supply, an outdoor "
    "gear retailer. Use only the numbered facts below. After each "
    "sentence, put the numbers of the facts it relies on in square "
    "brackets, such as [2] or [1, 3]. If the facts do not answer the "
    "question, say that you cannot tell from the information you have, "
    "and do not guess. Answer briefly, in plain sentences.")


def retrieve(question, using, top=3):
    facts = []
    if using in ("graph", "both"):
        facts += graph_facts(find_products(question))
    if using in ("text", "both"):
        facts += text_retrieve(question, k=top)
    return facts


def answer(question, using, top=3):
    facts = retrieve(question, using, top)
    numbered = [f"[{n}] {text}" for n, (text, _) in enumerate(facts, 1)]
    request = ("Facts:\n" + "\n".join(numbered)
               + f"\n\nCustomer question: {question}")
    reply = ask(INSTRUCTIONS, request, max_output_tokens=1200)
    return facts, plain(reply).strip()


SENTENCE = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")
CITE = re.compile(r"\[([\d,\s]+)\]")


def check(reply, count):
    """Sentences with no citation, and cited numbers never given."""
    problems, sentences = [], []
    for s in SENTENCE.split(reply):
        # a short reply such as "Yes." leans on the sentence after it
        last = sentences[-1] if sentences else ""
        if last and len(last.split()) <= 3 and not CITE.search(last):
            sentences[-1] += " " + s
        else:
            sentences.append(s)
    for s in sentences:
        # saying the facts do not answer the question needs no citation
        if s.strip() and not CITE.search(s) and "cannot tell" not in s:
            problems.append(f'no citation: "{s.strip()}"')
    cited = Counter(int(n) for m in CITE.findall(reply)
                    for n in re.findall(r"\d+", m))
    for n in sorted(cited):
        if not 1 <= n <= count:
            problems.append(f"cites [{n}], which was never given")
    return problems, sorted(cited)


def wrap(text, first, rest):
    from textwrap import wrap as tw
    return tw(text, WIDTH, initial_indent=first, subsequent_indent=rest)


def report(question, using="graph", show=True, top=3):
    facts, reply = answer(question, using, top)
    out = []
    if show:
        out.append("Given to the model:" if facts else "Given to the model: nothing found")
        for n, (text, srcs) in enumerate(facts, 1):
            out += wrap(text, f"[{n}] ", "    ")
            out += wrap("from " + ", ".join(srcs), "    ", "    ")
        out.append("")
    out.append("Answer:")
    for para in reply.split("\n"):
        out += wrap(para, "  ", "  ") or [""]
    problems, cited = check(reply, len(facts))
    out.append("")
    out.append("Cited: " + (", ".join(f"[{n}]" for n in cited) or "nothing"))
    out += [f"Check: {p}" for p in problems] or ["Check: every sentence cites a fact."]
    return "\n".join(out)

