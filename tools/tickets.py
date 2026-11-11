"""Support ticket texts for Chapter 16, with the true answers kept apart.

Each entry: the product the customer means (sku), the problem type, and the
message as the customer wrote it. Customers do not use SKUs, rarely use the
exact product name, and sometimes mention two products. The extraction in
Chapter 16 sees only the text; the sku and problem type are the answer key.
"""

# sku, other sku mentioned or "", problem type, text
TICKETS = [
    ("TW-T102", "", "leak",
     ("Hi, I used the two person backpacking tent for the first time last weekend "
      "and water came in along the floor seam on the door side. It rained most of "
      "the night but nothing extreme. Is this normal or is the tent faulty?")),
    ("TW-S202", "", "deflation",
     ("My insulated air mat went flat twice in one night. I can't find a hole. The "
      "valve feels loose when I press it. I saw something online about a recall?"), "2026-05-12"),
    ("TW-S202", "", "deflation",
     ("Bought the air mat a while back. The little valve came right off in my "
      "hand on day two of a trip. Not happy, I slept on the ground.")),
    ("TW-P202", "", "strap",
     ("The hip belt buckle on my 65 litre pack cracked on a cold morning. The pack "
      "is not very old.")),
    ("TW-K101", "", "ignition",
     ("The canister stove won't light with the built in igniter any more. It "
      "clicks but no flame. Matches still work.")),
    ("TW-T201", "TW-A102", "missing-part",
     ("We received the 4 person family tent and the footprint together but there "
      "were only two of the long poles in the tent bag, should be three.")),
    ("TW-F101", "", "sizing",
     ("The men's leather boots run at least half a size small. Can I swap for a "
      "10.5 even though I wore them around the house?")),
    ("TW-C102", "", "zipper",
     ("Main zip on my women's waterproof jacket separates from the bottom when "
      "I pull it up.")),
    ("TW-T103", "", "delivery",
     ("Ordered the ultralight 2 person tent and tracking hasn't "
      "moved since it left the warehouse.")),
    ("TW-S104", "", "wrong-item",
     ("I ordered the 20 degree down bag, the new version, but the box had the "
      "synthetic 30 degree one in it.")),
    ("TW-P101", "", "zipper",
     "Front pocket zipper pull snapped off my 22L daypack."),
    ("TW-T202", "", "leak",
     ("Our big six person tent leaks at the top where the poles cross. Happened "
      "in two storms now.")),
    ("TW-K102", "", "ignition",
     ("Integrated stove system, igniter sparks but the burner doesn't catch unless "
      "I hold a lighter to it.")),
    ("TW-C202", "", "seam",
     "Stitching is coming apart under the arm on the synthetic insulated jacket."),
    ("TW-F201", "", "sizing",
     "Trail runners are too narrow for me. Do you have a wide fit?"),
    ("TW-S202", "", "deflation",
     ("The Insulated Air Mat I bought for my son loses air through the valve. "
      "Please advise how to get a refund.")),
    ("TW-A104", "", "missing-part",
     "Pack of tent stakes says 12 but there were 10 in the bag."),
    ("TW-T104", "", "zipper",
     "Inner door zip on the winter tent is stiff and has started to split."),
    ("TW-P203", "", "strap",
     ("Shoulder strap adjuster on the women's 40 litre pack keeps slipping, I "
      "have to retighten it every hour.")),
    ("TW-K202", "", "delivery",
     "Cook set arrived but the box was crushed and the lid is dented."),
    ("TW-C101", "TW-C301", "wrong-item",
     ("I ordered a men's waterproof jacket and a merino top. Got two merino tops, "
      "no jacket.")),
    ("TW-T106", "", "leak",
     ("New 3 person backpacking tent, the Mk II one. The fly is dripping at the "
      "vent after an hour of rain.")),
    ("TW-S201", "", "deflation",
     ("Self inflating mat doesn't self inflate much any more and slowly goes soft "
      "overnight.")),
    ("TW-F103", "", "seam",
     "Sole is separating from the upper at the toe on my winter boots already."),
    ("TW-T204", "", "leak",
     ("The pop up tent is fine for festivals but it let in a lot of water the "
      "first time it actually rained.")),
    ("TW-C203", "", "delivery",
     ("Is the new down jacket back in stock? Your site says ships in 2 days but "
      "I've waited a week.")),
    ("TW-P102", "TW-P101", "sizing",
     ("Bought the 30 litre daypack but it's bigger than I expected. Can I swap "
      "it for the 22 litre one?")),
    ("TW-K103", "", "ignition",
     "Liquid fuel stove flares up badly when priming. Is it safe to keep using?"),
]
