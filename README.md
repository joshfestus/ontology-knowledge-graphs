# Tarnwick Supply knowledge graph

The companion files for *Ontology and Knowledge Graphs for Beginners: A
Practical Guide to Ontology Engineering, Semantic Modeling, and Building
Knowledge Graphs for AI and LLMs* by Josh Festus.

Tarnwick Supply is an invented outdoor gear retailer. Every name, product and
number in these files was made up for the book, and every result printed in
the book was produced by running these files.

## Set up

Install [uv](https://docs.astral.sh/uv/), then, in this folder:

    uv sync
    source .venv/bin/activate        on Windows: .venv\Scripts\activate
    tarnwick check stages/ch03/first-facts.ttl

Appendix D of the book walks through this on Windows, macOS and Linux.

## Work through a chapter

Each chapter's files are in `stages/chNN`, and the commands in a chapter are
run from inside its folder. Worked answers to the tasks are in each folder's
`answers` subfolder and in Appendix E.

    cd stages/ch10
    tarnwick reason boulder.ttl --about place:BOULDER

## The tarnwick command

| Command | What it does | Chapter |
|---|---|---|
| `tarnwick check FILE` | Reads a Turtle file and lists its triples, naming the line to fix if it cannot | 3 |
| `tarnwick search WORD --using LEVEL` | Searches the categories as a word list, taxonomy or thesaurus | 2 |
| `tarnwick pg FILE` | Shows Turtle as a property graph would hold it | 4 |
| `tarnwick question N` | Answers competency question N from `QUESTIONS.md` | 5, 14 |
| `tarnwick define TERM` | What a Tarnwick term is called and means | 6 |
| `tarnwick classes` | The class tree with counts, and disjointness checks | 7 |
| `tarnwick properties`, `tarnwick implied` | Properties, and what their declarations conclude | 8 |
| `tarnwick skos FILE.csv`, `tarnwick tree` | A category spreadsheet as SKOS, and the taxonomy checked | 9 |
| `tarnwick reason` | What the OWL reasoner adds, and any contradictions | 10 |
| `tarnwick coverage`, `tarnwick validate`, `tarnwick pitfalls` | Testing the ontology and the data | 12 |
| `tarnwick build` | Builds the whole graph and validates it | 13 |
| `tarnwick ask QUERY` | Runs a SPARQL query file | 14 |
| `tarnwick match` | How typed supplier names are matched | 15 |
| `tarnwick pgraph`, `tarnwick gql FILE`, `tarnwick path`, `tarnwick similar` | The property graph copy | 17 |
| `tarnwick diff OLD NEW` | What changed between two ontology versions | 23 |

## What is here

| Folder | Contents |
|---|---|
| `data/` | The source files: products, suppliers, categories, places, stores, customers, orders, stock, recalls, support tickets and four policy documents |
| `ontology/` | The ontology, the SKOS taxonomy, the return rules and the SHACL shapes |
| `queries/` | One SPARQL file per competency question |
| `stages/` | Each chapter's files, with worked answers |
| `src/tarnwick/` | The `tarnwick` command |
| `llm-cache/` | Every answer the language model gave for the book, so the results can be reproduced without an account |
| `tests/` | Every answer checked a second way, straight from the CSV files |
| `QUESTIONS.md` | The thirty competency questions, with the chapter that first answers each |
| `SOURCES.md` | Where each fact the book states about a standard, a date or a published finding comes from |

## Language model settings

The chapters that use a language model work with any service that speaks the
OpenAI API, including a free model run on your own computer.

| Setting | Meaning |
|---|---|
| `OPENAI_API_KEY` | Your key, if you use a hosted service |
| `TARNWICK_LLM_MODEL` | The model; the book used `gpt-5.6-luna` |
| `TARNWICK_LLM_BASE_URL` | The address of another OpenAI-compatible service, such as a local one |
| `TARNWICK_LLM_BUDGET` | The most, in US dollars, the examples may spend (1.00 unless set) |

A request already answered in `llm-cache/` is never sent again, so running the
book's examples unchanged costs nothing.

## Problems planted on purpose

The web catalog calls family tents "Shelters". One supplier's name is typed
three different ways. Two products sit in two categories. Two categories have
no products. One product has no weight. One order sells a tent five weeks
before it was released. Marketing and finance count active customers
differently. Each is found and fixed in a chapter.

## License

The program code is under the MIT License (`LICENSE`). The ontology, data,
queries and saved model answers are under the Creative Commons Attribution
4.0 International License (`LICENSE-DATA`). The text of the book is not
covered by either license.
