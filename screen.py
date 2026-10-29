"""Screen Life-like rules (outer-totalistic B/S, no B0/B1) for searchability.

Stage 1 runs a few soups per rule over many rules and drops explosive or
trivial ones; stage 2 runs more soups on survivors; stage 3 looks up the
Catagolue C1 soup count for the best ones.

  python3 screen.py --sample 6000 --quick 12 --soups 100 --top 60
Writes results/screen.json and results/screen.md (ranked table).
"""
import argparse
import collections
import hashlib
import json
import math
import os
import random
import re
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "census_cache")


def rule_name(b, s):
    return "b" + "".join(map(str, sorted(b))) + "s" + "".join(map(str, sorted(s)))


def all_rules():
    out = []
    for bm in range(1 << 7):  # births from {2..8}
        b = [i + 2 for i in range(7) if bm >> i & 1]
        if not b:
            continue
        for sm in range(1 << 9):
            out.append(rule_name(b, [i for i in range(9) if sm >> i & 1]))
    return out


def comp_sizes(nums):
    cells = set(zip(nums[0::2], nums[1::2]))
    sizes = []
    while cells:
        stack = [cells.pop()]
        k = 0
        while stack:
            x, y = stack.pop()
            k += 1
            for dx in range(-2, 3):
                for dy in range(-2, 3):
                    q = (x + dx, y + dy)
                    if q in cells:
                        cells.remove(q)
                        stack.append(q)
        sizes.append(k)
    return sizes


def new_stat(rule, n):
    return {"rule": rule, "n": n, "done": 0, "U": 0, "empty": 0, "gens": 0, "ships": 0, "p_hi": 0,
            "periods": collections.Counter(), "cells": 0, "objs": 0, "big": 0, "seconds": 0.0}


def add_line(st, f):
    if f[0] == "E":
        st["ships"] += 1
        return
    st["done"] += 1
    if f[0] == "U":
        st["U"] += 1
        return
    p, gen, cells = int(f[2]), int(f[3]), int(f[4])
    st["gens"] += gen
    st["cells"] += cells
    st["periods"][p] += 1
    if cells == 0:
        st["empty"] += 1
    if p > 2:
        st["p_hi"] += 1
    sizes = comp_sizes(list(map(int, f[5:5 + 2 * cells]))) if cells <= 1500 else [cells]
    st["objs"] += len(sizes)
    if sizes and max(sizes) > 40:
        st["big"] += 1


def run_batch(rules, n, maxspan, maxgen, maxpop=1500, maxwork=2_000_000, prefix="screen_"):
    """One soup process for many rules ("R <rule>" lines); per-rule wall time from the stream."""
    seeds = "".join(f"{i} {hashlib.sha256(f'{prefix}{i}'.encode()).hexdigest()}\n" for i in range(n))
    proc = subprocess.Popen([os.path.join(HERE, "soup"), "b3s23", str(maxspan), str(maxgen), str(maxpop), str(maxwork)],
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
    import threading
    feed = "".join(f"R {r}\n{seeds}" for r in rules) + "R end\n"
    threading.Thread(target=lambda: (proc.stdin.write(feed), proc.stdin.close()), daemon=True).start()
    stats, cur, t = [], None, time.time()
    for line in proc.stdout:
        f = line.split()
        if f[0] == "R":
            now = time.time()
            if cur:
                cur["seconds"] = now - t
                stats.append(cur)
            t = now
            cur = new_stat(f[1], n) if f[1] != "end" else None
            continue
        add_line(cur, f)
    proc.wait()
    for st in stats:
        st["missing"] = n - st["done"]
        st["periods"] = dict(st["periods"])
    return stats


def summarize(st):
    n = st["n"]
    unstable = (st["U"] + st["missing"]) / n
    fin = max(1, st["done"] - st["U"])
    return {
        "rule": st["rule"], "n": n, "unstable": round(unstable, 3),
        "empty": round(st["empty"] / n, 3),
        "mean_gen": round(st["gens"] / fin), "mean_ash": round(st["cells"] / fin, 1),
        "soups_per_s": round(st["done"] / max(st["seconds"], 1e-3), 1),
        "ships_per_soup": round(st["ships"] / n, 3), "p_hi": round(st["p_hi"] / n, 3),
        "periods": st["periods"],
        "objs_per_soup": round(st["objs"] / fin, 1), "blob": round(st["big"] / fin, 3),
    }


def job(args):
    return [summarize(st) for st in run_batch(*args)]


def batches(rules, k):
    return [rules[i:i + k] for i in range(0, len(rules), k)]


def censused_rules():
    path = os.path.join(CACHE, "rules_lifelike.html")
    if not os.path.exists(path):
        subprocess.run(["curl", "-sf", "--max-time", "60", "-o", path,
                        "https://catagolue.hatsya.com/rules/lifelike"], check=True)
    return set(re.findall(r'href="/census/(b\d*s\d*)"', open(path).read()))


def c1_soups(rule):
    """Catagolue C1 soup count (0 when nobody searched C1 for this rule)."""
    path = os.path.join(CACHE, f"c1count_{rule}.txt")
    if not os.path.exists(path):
        r = subprocess.run(["curl", "-sf", "--max-time", "60", f"https://catagolue.hatsya.com/census/{rule}/C1"],
                           capture_output=True, text=True)
        if r.returncode != 0:
            return None
        m = re.search(r"generated from ([\d&#;]+) soups", r.stdout)
        if m:
            n = int(re.sub(r"&#\d+;|\D", "", m.group(1).replace("&#8201;", "")))
        elif "no-one has yet investigated" in r.stdout:
            n = 0
        else:
            return None
        open(path, "w").write(str(n))
        time.sleep(0.5)
    return int(open(path).read())


def score(r):
    """Higher is better: stable, varied (oscillators/ships), fast, little-searched."""
    if r["unstable"] > 0.05 or r["empty"] > 0.9 or r.get("blob", 0) > 0.5:
        return -1  # explosive, dead, or ash is one big frozen mass (no separable objects)
    interest = (1 + 2 * r["p_hi"] + 6 * min(r["ships_per_soup"], 1)) * min(1, r.get("objs_per_soup", 0) / 3)
    interest *= 1 - r.get("blob", 0)
    speed = math.log10(max(r["soups_per_s"], 1))
    novelty = 10 - math.log10(1 + (r.get("c1") or 0))  # 0 soups -> 10, 1e9 -> 1  # 0 soups -> 10, 1e9 -> 1
    return round(novelty * interest * (1 - r["unstable"] * 10) * (0.5 + speed / 4), 2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=6000, help="rules in stage 1 (0 = all 65k)")
    ap.add_argument("--quick", type=int, default=12, help="soups per rule in stage 1")
    ap.add_argument("--soups", type=int, default=100, help="soups per rule in stage 2")
    ap.add_argument("--top", type=int, default=60, help="rules to look up on Catagolue")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--family", default="", help="'b3': only rules with B3 and without B2")
    ap.add_argument("--out", default="screen")
    ap.add_argument("--rescore", action="store_true", help="re-rank results/<out>.json without re-running soups")
    a = ap.parse_args()
    if a.rescore:
        d = json.load(open(os.path.join(HERE, "results", a.out + ".json")))
        return rank(d["stage1"], d["stage2"], censused_rules(), a, time.time() - d["seconds"])

    rules = all_rules()
    if a.family == "b3":
        rules = [r for r in rules if "3" in r.split("s")[0] and "2" not in r.split("s")[0]]
    random.Random(a.seed).shuffle(rules)
    if a.sample:
        rules = rules[:a.sample]
    known = censused_rules()
    t0 = time.time()

    with ProcessPoolExecutor() as ex:
        s1 = []
        for i, rs in enumerate(ex.map(job, [(b, a.quick, 200, 3000) for b in batches(rules, 40)])):
            s1 += rs
            print(f"\rstage1 {len(s1)}/{len(rules)} {time.time() - t0:.0f}s", end="", file=sys.stderr)
        print(file=sys.stderr)
        keep = [r["rule"] for r in s1 if r["unstable"] <= 0.15 and r["empty"] < 0.9]
        print(f"stage1: {len(keep)}/{len(rules)} rules stable & non-trivial", file=sys.stderr)
        s2 = []
        for i, rs in enumerate(ex.map(job, [(b, a.soups, 300, 15000, 3000, 20_000_000) for b in batches(keep, 4)])):
            s2 += rs
            print(f"\rstage2 {len(s2)}/{len(keep)} {time.time() - t0:.0f}s", end="", file=sys.stderr)
        print(file=sys.stderr)

    rank(s1, s2, known, a, t0)


def rank(s1, s2, known, a, t0):
    """Score rules; fetch real Catagolue C1 counts for the most interesting ones."""
    for r in s2:
        r["listed"] = r["rule"] in known
        r["c1"] = 0
        r["intrinsic"] = score(r)  # novelty term = 10 for everyone here
    s2.sort(key=lambda r: -r["intrinsic"])
    todo = [r for r in s2 if r["intrinsic"] > 0][:a.top]
    todo += [r for r in s2 if r["intrinsic"] > 0 and r["ships_per_soup"] >= 0.03 and r not in todo]
    todo += [r for r in s2 if r["intrinsic"] > 0 and "s0" not in r["rule"] and r not in todo][:a.top // 2]
    todo += [r for r in s2 if r not in todo and os.path.exists(os.path.join(CACHE, f"c1count_{r['rule']}.txt"))]
    for i, r in enumerate(todo):
        print(f"\rcatagolue {i + 1}/{len(todo)}", end="", file=sys.stderr)
        r["c1"] = c1_soups(r["rule"])
        r["c1_checked"] = r["c1"] is not None
        if r["c1"] is None:
            r["c1"] = 10 ** 9 if r["listed"] else 0
    print(file=sys.stderr)
    for r in s2:
        if "c1_checked" not in r:
            r["c1_checked"] = False
            r["c1"] = 10 ** 9 if r["listed"] else 0  # listed = censused under some symmetry
        r["score"] = score(r)
    s2.sort(key=lambda r: -r["score"])

    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    json.dump({"stage1": s1, "stage2": s2, "seconds": round(time.time() - t0)},
              open(os.path.join(HERE, "results", a.out + ".json"), "w"))
    head = ("| # | rule | score | unstable | empty | blob | objs/soup | p>2 ash | ships/soup | soups/s | mean gen | C1 soups on Catagolue |\n"
            "|---|---|---|---|---|---|---|---|---|---|---|---|")

    def row(i, r):
        if r["c1_checked"]:
            c1 = f"{r['c1']:,}"
        else:
            c1 = "listed, not looked up (assumed 1e9)" if r["listed"] else "0? (not on rules list)"
        return (f"| {i} | {r['rule']} | {r['score']} | {r['unstable']:.0%} | {r['empty']:.0%} | {r['blob']:.0%} | "
                f"{r['objs_per_soup']} | {r['p_hi']:.0%} | {r['ships_per_soup']} | {r['soups_per_s']} | {r['mean_gen']} | {c1} |")

    good = [r for r in s2 if r["score"] > 0]
    ships = sorted([r for r in good if r["ships_per_soup"] >= 0.03], key=lambda r: -r["ships_per_soup"])
    nos0 = [r for r in good if "s0" not in r["rule"]]
    md = (f"# Rule screen\n\nStage 1: {len(s1)} rules × {a.quick} soups; stage 2: {len(s2)} stable rules × {a.soups} soups.\n"
          "unstable = soups that hit the size/population/work cap (explosive); blob = soups whose ash has a >40-cell component;\n"
          "p>2 ash = soups whose final period > 2; ships/soup = escaping objects per soup.\n\n"
          "## Top 60 by score\n\n" + head + "\n" + "\n".join(row(i, r) for i, r in enumerate(good[:60], 1)) +
          "\n\n## Rules that emit spaceships (ships/soup ≥ 0.03)\n\n" + head + "\n" + "\n".join(row(i, r) for i, r in enumerate(ships, 1)) +
          "\n\n## Top 40 without S0 (S0 = lone cells survive, so ash is littered with dots)\n\n" + head + "\n" +
          "\n".join(row(i, r) for i, r in enumerate(nos0[:40], 1)) + "\n")
    open(os.path.join(HERE, "results", a.out + ".md"), "w").write(md)
    print(md[:6000])

if __name__ == "__main__":
    main()
