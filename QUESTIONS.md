# The Thirty Questions

The competency questions Tarnwick Supply wants its knowledge graph to answer.
Chapter 5 writes them; every later chapter checks which ones the model can now
answer; Chapters 19 and 22 use them to measure the AI assistant. Each question
has a query in `queries/` named by its number, and a test in
`tests/test_questions.py` that checks the query's answer against an answer
computed directly from the raw files, so a query can never pass by accident.

| No. | Question | First answerable | Needs |
|---|---|---|---|
| 1 | Which products are tents, whatever the website calls them? | Ch 9 | Taxonomy with alternative labels |
| 2 | Which products sit in more than one category? | Ch 7 | Many to many category links |
| 3 | Which supplier makes each product? | Ch 13 | Supplier links |
| 4 | Which suppliers does Tarnwick still buy from? | Ch 8 | Supplier status and dates |
| 5 | Which products on sale today came from a supplier Tarnwick has stopped using? | Ch 14 | Dates on the supplier relationship |
| 6 | Which products have been recalled, and which customers bought them? | Ch 14 | Recalls, orders |
| 7 | Which stores have a given product in stock, and how many? | Ch 14 | Stock levels |
| 8 | Which products are in Camping, including every category beneath it? | Ch 9 | Category hierarchy |
| 9 | What are all the names a category is known by? | Ch 9 | Preferred and alternative labels |
| 10 | Which tents weigh under 2 kg and are rated for at least three seasons? | Ch 14 | Weights, season ratings |
| 11 | Which customers are active under the marketing definition? | Ch 21 | Order dates |
| 12 | Which customers are active under the finance definition, and how do the two lists differ? | Ch 21 | Account dates |
| 13 | What was the revenue in each region last quarter? | Ch 14 | Place hierarchy, orders |
| 14 | Which accessories fit which tents? | Ch 8 | Fit relationship |
| 15 | Which products contain down, and in which country is their supplier based? | Ch 14 | Materials, supplier country |
| 16 | Which supplier names in the files refer to the same company? | Ch 15 | Entity resolution |
| 17 | Which support tickets mention a product, and what went wrong? | Ch 16 | LLM extraction from text |
| 18 | Which products have the most complaints per hundred sold? | Ch 16 | Tickets and orders together |
| 19 | Which policy applies when a customer returns a recalled product? | Ch 18 | Policies linked to recalls |
| 20 | Which region is a given town in? | Ch 10 | Transitive place hierarchy and reasoning |
| 21 | Which suppliers belong to the same parent company? | Ch 11 | Reused organization vocabulary |
| 22 | Which product replaced a discontinued one? | Ch 8 | Replacement relationship |
| 23 | How many days does a customer have to return a given product? | Ch 18 | Policy rules by category |
| 24 | Which customers bought a tent and the footprint that fits it? | Ch 14 | Fit relationship and orders |
| 25 | Which categories have no products at all? | Ch 9 | Taxonomy against products |
| 26 | Which product records are missing a required value? | Ch 12 | SHACL shapes |
| 27 | Where did each fact about a product come from? | Ch 13 | Named graphs per source file |
| 28 | Which sales are dated before the product was released? | Ch 12 | SHACL with a SPARQL constraint |
| 29 | Which store relies most on a single supplier for the stock on its shelves? | Ch 17 | Traversal from store to stock to supplier |
| 30 | Which products are most often bought together? | Ch 17 | Graph algorithms |
