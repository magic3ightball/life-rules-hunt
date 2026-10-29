"""Check every 'new' find (Catagolue census 0) in results/lrh_*.json:

1. regenerate: re-classify the stored cells and check the apgcode matches;
2. strictness: try every split of the object into two parts A, B such that each
   part is a periodic, non-moving object on its own (period dividing p) and the
   two evolve together exactly as they do apart. If such a split exists the
   find is a pseudo-object (two objects that merely touch), not a new object.

Exhaustive for objects up to --max-cells cells; bigger ones are only tested on
splits along 8-connected pieces (marked 'partial').

  python3 verify.py            -> results/verify.json + printed table
"""
import argparse
import glob
import json
import os

from hunt import classify, find_split, parse_rule

HERE = os.path.dirname(os.path.abspath(__file__))


def period_of(code):
    return 1 if code.startswith("xs") else int(code[2:].split("_")[0])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-cells", type=int, default=18)
    ap.add_argument("--only-interesting-s0", action="store_true", default=True,
                    help="for never-censused rules check only xq and xp with p>2")
    a = ap.parse_args()
    out = []
    for path in sorted(glob.glob(os.path.join(HERE, "results", "*_lrh_*.json"))):
        r = json.load(open(path))
        rule_s = r["rule"]
        rule = parse_rule(rule_s)
        new = [o for o in r["objects"] if o["census"] == 0]
        everything_new = len(new) == len([o for o in r["objects"] if o["census"] is not None])
        for o in new:
            code, p = o["code"], period_of(o["code"])
            if everything_new and not (code.startswith("xq") or (code.startswith("xp") and p > 2)):
                continue
            cells = [tuple(c) for c in o["cells"]]
            again, _ = classify(frozenset(cells), rule, max(p, 2) * 2)
            same = again == code
            if code.startswith("xq"):
                split, how = None, "ship (not split)"
            else:
                split, how = find_split(cells, rule, max(p, 1), a.max_cells)
            verdict = ("mismatch" if not same else "pseudo" if split else "strict")
            out.append({"rule": rule_s, "code": code, "cells": len(cells), "soup": o["soup"],
                        "count": o["count"], "verdict": verdict, "how": how, "part": split})
            print(f"{rule_s:12} {code:28} {len(cells):3} cells  {verdict:8} ({how})")
    json.dump(out, open(os.path.join(HERE, "results", "verify.json"), "w"), indent=1)
    from collections import Counter
    print(Counter((x["rule"], x["verdict"]) for x in out))


if __name__ == "__main__":
    main()
