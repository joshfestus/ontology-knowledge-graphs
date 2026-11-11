"""Write ontology/taxonomy.ttl from categories.csv plus the curated choices
below. Run once; after that taxonomy.ttl is the maintained source and the
tests check it still agrees with categories.csv."""

import csv
from pathlib import Path

from fit_page import fit

ROOT = Path(__file__).resolve().parent.parent

# Web team words, attached to the concept they really mean.
ALT = {
    "TENT-FAM": ["Shelters"],
    "TENT-ACC": ["Tent Extras"],
    "SLEEP": ["Sleep Systems"],
    "KITCHEN": ["Cook Systems"],
    "BOOT": ["Boots"],
    "SHOE": ["Trail Runners"],
    "PACK": ["Rucksacks", "Backpacks"],
    "JACKET-WP": ["Hardshells", "Rain Jackets"],
    "JACKET-INS": ["Insulation", "Puffer Jackets"],
}
# Thesaurus related terms: different ideas a searcher often wants together.
RELATED = [("TENT", "TENT-ACC"), ("SLEEP-BAG", "SLEEP-MAT"), ("STOVE", "COOK")]
DEF = {
    "CAMP": "Equipment for sleeping, cooking and sheltering outdoors overnight.",
    "TENT": "Portable shelters made of fabric held up by poles or air beams.",
    "TENT-BP": "Tents light and small enough to carry on foot for several days.",
    "TENT-FAM": "Tents for car camping, too heavy to carry far, with room to stand up.",
    "TENT-ACC": "Parts and add-ons that are used with a tent but sold separately.",
    "SLEEP": "Products that keep a person warm and comfortable while sleeping outdoors.",
    "SLEEP-BAG": "Insulated bags to sleep inside, rated by the lowest comfortable temperature.",
    "SLEEP-MAT": "Pads that go under a sleeping bag to insulate from the ground.",
    "KITCHEN": "Equipment for cooking and boiling water outdoors.",
    "STOVE": "Portable burners that run on gas canisters or liquid fuel.",
    "COOK": "Pots, pans and kettles for outdoor cooking.",
    "REPAIR": "Products for fixing and maintaining outdoor gear.",
    "HIKE": "Equipment for walking on trails, for a day or for longer.",
    "FOOT": "Boots and shoes made for walking on rough ground.",
    "BOOT": "Footwear that covers the ankle, for support on rough or wet ground.",
    "SHOE": "Low cut footwear for trails, lighter than boots.",
    "PACK": "Bags carried on the back.",
    "PACK-DAY": "Packs under 35 litres, for trips that end the same day.",
    "PACK-BP": "Packs of 35 litres or more with a hip belt, for overnight trips.",
    "CLOTH": "Garments made for outdoor use.",
    "JACKET": "Outer garments for the upper body.",
    "JACKET-WP": "Jackets that keep rain out while letting sweat escape.",
    "JACKET-INS": "Jackets filled with down or synthetic fibres to keep heat in.",
    "BASE": "Garments worn next to the skin to move sweat away from it.",
    "CLIMB": "Equipment for rock climbing. Tarnwick plans to start selling it.",
    "HARNESS": "Climbing harnesses. No products yet.",
}
PROBLEMS = [
    ("leak", "leak", "Water getting in through fabric, seams or vents."),
    ("zipper", "zipper fault", "A zip that splits, sticks or breaks."),
    ("deflation", "loss of air", "An inflatable product going soft or flat."),
    ("strap", "strap or buckle fault", "A strap, buckle or adjuster that breaks or slips."),
    ("ignition", "stove will not light or burns badly", "A stove that will not light, or burns unsafely."),
    ("missing-part", "missing part", "A product arrived without one of its parts."),
    ("sizing", "size or fit", "A product that does not fit the customer."),
    ("delivery", "delivery problem", "A late, lost or damaged delivery."),
    ("wrong-item", "wrong item sent", "The customer received a different product from the one ordered."),
    ("seam", "seam or stitching failure", "Stitching or bonding coming apart."),
]


def lit(s):
    return '"' + s.replace('"', '\\"') + '"@en'


def main():
    with open(ROOT / "data" / "categories.csv", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    out = [
        "@prefix cat:  <https://tarnwick.example/id/category/> .",
        "@prefix prob: <https://tarnwick.example/id/problem/> .",
        "@prefix tid:  <https://tarnwick.example/id/> .",
        "@prefix skos: <http://www.w3.org/2004/02/skos/core#> .",
        "",
        "tid:categories a skos:ConceptScheme ;",
        '    skos:prefLabel "Tarnwick product categories"@en .',
        "",
    ]
    for r in rows:
        c = r["code"]
        lines = [f"cat:{c} a skos:Concept ;",
                 "    skos:inScheme tid:categories ;",
                 f"    skos:prefLabel {lit(r['label'])} ;"]
        for a in ALT.get(c, []):
            lines.append(f"    skos:altLabel {lit(a)} ;")
        lines.append(f'    skos:notation "{c}" ;')
        for a, b in RELATED:
            if c in (a, b):
                lines.append(f"    skos:related cat:{b if c == a else a} ;")
        if r["parent"]:
            lines.append(f"    skos:broader cat:{r['parent']} ;")
        else:
            lines.append("    skos:topConceptOf tid:categories ;")
        lines.append(f"    skos:definition {lit(DEF[c])} .")
        out += lines + [""]
    out += ["tid:problems a skos:ConceptScheme ;",
            '    skos:prefLabel "Tarnwick support problem types"@en .', ""]
    for code, label, d in PROBLEMS:
        out += [f"prob:{code} a skos:Concept ;",
                "    skos:inScheme tid:problems ;",
                "    skos:topConceptOf tid:problems ;",
                f"    skos:prefLabel {lit(label)} ;",
                f"    skos:definition {lit(d)} .", ""]
    path = ROOT / "ontology" / "taxonomy.ttl"
    path.write_text("\n".join(out), encoding="utf-8")
    fit(path)
    # Chapter 2's mistake: the same taxonomy with Tent Accessories filed
    # under Tents instead of under Camping
    text = path.read_text(encoding="utf-8")
    start = text.index("cat:TENT-ACC a skos:Concept")
    end = text.index(" .\n", start)
    block = text[start:end].replace("skos:broader cat:CAMP", "skos:broader cat:TENT")
    (ROOT / "stages" / "ch02" / "wrong-tree.ttl").write_text(
        text[:start] + block + text[end:], encoding="utf-8")


if __name__ == "__main__":
    main()
