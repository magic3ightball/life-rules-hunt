"""Second look at soups that never settled in a search (the 'U' list).

Each one is re-run with a larger box (maxspan 700 on the 1024 grid). Then:
- settled: it was just big; its objects are separated and compared with Catagolue
- emitter: it keeps throwing objects out at regular intervals -> gun / puffer / rake candidate
- unsettled: still growing or chaotic after 15000 gens

  python3 unstable.py --rule b368s238 --result results/b368s238_lrh_b368s238_1020_.json
Writes results/<rule>_unstable.json.
"""
import argparse
import collections
import hashlib
import json
import os
import subprocess
import tempfile
from concurrent.futures import ProcessPoolExecutor

import hunt

HERE = os.path.dirname(os.path.abspath(__file__))


def emission_period(gens):
    """Most common gap between ejection events, if the events look regular.
    Ejection is checked every 8 gens, so ejections closer than 17 gens are one
    event (a long object streaming out)."""
    events = []
    for g in sorted(set(gens)):
        if not events or g - last > 16:
            events.append(g)
        last = g
    if len(events) < 5:
        return None
    gaps = collections.Counter(b - a for a, b in zip(events, events[1:]))
    gap, n = gaps.most_common(1)[0]
    return gap if n >= len(events) // 3 else None


def check(args):
    rule_s, soups, maxspan = args
    rule = hunt.parse_rule(rule_s)
    seeds = "".join(f"{i} {hashlib.sha256(s.encode()).hexdigest()}\n" for i, s in enumerate(soups))
    with tempfile.TemporaryFile("w+") as f:
        f.write(seeds)
        f.seek(0)
        out = subprocess.run([os.path.join(HERE, "soup"), rule_s, str(maxspan)], stdin=f,
                             capture_output=True, text=True, check=True).stdout
    ejections = collections.defaultdict(list)
    final = {}
    for line in out.splitlines():
        f = line.split()
        idx = int(f[1])
        if f[0] == "E":
            ejections[idx].append((int(f[2]), int(f[3])))
        else:
            final[idx] = line
    res = []
    for i, s in enumerate(soups):
        ej = ejections.get(i, [])
        big = [g for g, n in ej if n > 30]  # bigger than a small ship: debris trains, rakes' output
        info = {"soup": s, "ejections": len(ej), "big_ejections": len(big)}
        line = final.get(i, "U")
        f = line.split()
        if f[0] == "S":
            period, n = int(f[2]), int(f[4])
            nums = list(map(int, f[5:5 + 2 * n]))
            objs = hunt.separate(list(zip(nums[0::2], nums[1::2])), period, rule) if n else []
            info.update(kind="settled", gen=int(f[3]),
                        objects=[(c, cells) for c, cells in objs if not c.startswith("zz")])
        else:
            info.update(kind="unsettled", gen=int(f[2]) if len(f) > 2 else None)
        p = emission_period([g for g, _ in ej])
        if p and len(ej) >= 6:
            info["kind"] = "emitter" if info["kind"] != "settled" or len(big) >= 3 else info["kind"]
            info["emit_period"] = p
        res.append(info)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rule", required=True)
    ap.add_argument("--result", required=True, help="search result json with the 'unstable' list")
    ap.add_argument("--maxspan", type=int, default=700)
    ap.add_argument("--rare", type=int, default=3)
    a = ap.parse_args()
    soups = json.load(open(a.result))["unstable"]
    jobs = [(a.rule, soups[i:i + 10], a.maxspan) for i in range(0, len(soups), 10)]
    rows = []
    with ProcessPoolExecutor() as ex:
        for i, r in enumerate(ex.map(check, jobs)):
            rows += r
            print(f"\r{len(rows)}/{len(soups)}", end="", flush=True)
    print()
    kinds = collections.Counter(r["kind"] for r in rows)
    tally, sample = collections.Counter(), {}
    for r in rows:
        for code, cells in r.get("objects", []):
            tally[code] += 1
            sample.setdefault(code, (r["soup"], cells))
    finds = []
    for code, n in tally.most_common():
        table = hunt.census(a.rule, code.split("_")[0])
        cens = None if table is None else table.get(code, 0)
        finds.append({"code": code, "count": n, "census": cens, "soup": sample[code][0], "cells": sample[code][1]})
    emitters = sorted([r for r in rows if r["kind"] == "emitter"], key=lambda r: -r["big_ejections"])
    out = {"rule": a.rule, "soups": len(soups), "kinds": dict(kinds), "objects": finds,
           "emitters": [{k: r[k] for k in ("soup", "ejections", "big_ejections", "emit_period", "gen")} for r in emitters],
           "unsettled": [r["soup"] for r in rows if r["kind"] == "unsettled"]}
    json.dump(out, open(os.path.join(HERE, "results", f"{a.rule}_unstable.json"), "w"))
    print(a.rule, dict(kinds))
    for f in finds:
        if f["census"] is not None and f["census"] < a.rare:
            print(f"  census {f['census']}  {f['code']}  https://catagolue.hatsya.com/hashsoup/C1/{f['soup']}/{a.rule}")
    for r in emitters[:15]:
        print(f"  emitter every ~{r['emit_period']} gens, {r['ejections']} ejections ({r['big_ejections']} big)  "
              f"https://catagolue.hatsya.com/hashsoup/C1/{r['soup']}/{a.rule}")


if __name__ == "__main__":
    main()
