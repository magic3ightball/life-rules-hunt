"""Soup search for Life-like rules: separate objects, compute apgcodes,
and compare against the Catagolue census to flag rare / unseen objects.

  python3 hunt.py --rule b3s23 --soups 20000
"""
import argparse
import collections
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor
from concurrent.futures.process import BrokenProcessPool

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "census_cache")
ENC = "0123456789abcdefghijklmnopqrstuvwxyz"

# ---------- Life on cell sets ----------

def parse_rule(rule):
    b, s = set(), set()
    cur = None
    for ch in rule.lower():
        if ch == "b":
            cur = b
        elif ch == "s":
            cur = s
        elif ch.isdigit() and cur is not None:
            cur.add(int(ch))
    return b, s


def step(cells, rule):
    b, s = rule
    cnt = collections.Counter()
    for x, y in cells:
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx or dy:
                    cnt[(x + dx, y + dy)] += 1
    out = {c for c, n in cnt.items() if (n in s if c in cells else n in b)}
    if 0 in s:  # S0: isolated cells never appear in cnt but survive
        out |= {c for c in cells if c not in cnt}
    if 0 in b:
        raise ValueError("B0 rules not supported")
    return frozenset(out)


def normalize(cells):
    if not cells:
        return frozenset(), (0, 0)
    mx = min(x for x, _ in cells)
    my = min(y for _, y in cells)
    return frozenset((x - mx, y - my) for x, y in cells), (mx, my)

# ---------- apgcode (extended Wechsler) ----------

def wechsler(cells):
    w = max(x for x, _ in cells) + 1
    h = max(y for _, y in cells) + 1
    strips = []
    for sy in range(0, h, 5):
        cols = []
        for x in range(w):
            v = 0
            for k in range(5):
                if (x, sy + k) in cells:
                    v |= 1 << k
            cols.append(v)
        while cols and cols[-1] == 0:
            cols.pop()
        s = "".join(ENC[v] for v in cols)
        strips.append(compress_zeros(s))
    return "z".join(strips)


def compress_zeros(s):
    out, i = [], 0
    while i < len(s):
        if s[i] != "0":
            out.append(s[i])
            i += 1
            continue
        j = i
        while j < len(s) and s[j] == "0":
            j += 1
        n = j - i
        while n > 0:
            if n == 1:
                out.append("0"); n = 0
            elif n == 2:
                out.append("w"); n = 0
            elif n == 3:
                out.append("x"); n = 0
            else:
                k = min(n, 39)
                out.append("y" + ENC[k - 4]); n -= k
        i = j
    return "".join(out)


TRANSFORMS = [
    lambda x, y: (x, y), lambda x, y: (-x, y), lambda x, y: (x, -y), lambda x, y: (-x, -y),
    lambda x, y: (y, x), lambda x, y: (-y, x), lambda x, y: (y, -x), lambda x, y: (-y, -x),
]


def canon(phases):
    best = None
    for ph in phases:
        for t in TRANSFORMS:
            c, _ = normalize({t(x, y) for x, y in ph})
            w = wechsler(c)
            key = (len(w), w)
            if best is None or key < best:
                best = key
    return best[1]

# ---------- object classification ----------

def classify(cells, rule, maxp):
    """Evolve an isolated object; return (apgcode, phases) or (None, reason)."""
    start, _ = normalize(cells)
    cur = frozenset(cells)
    phases = [cur]
    pop0 = len(cur)
    for g in range(1, maxp + 1):
        cur = step(cur, rule)
        if not cur:
            return None, "dies"
        nc, off = normalize(cur)
        if nc == start:
            nph = [normalize(p)[0] for p in phases]
            o0 = normalize(cells)[1]
            moved = off != o0
            if moved:
                return "xq%d_%s" % (g, canon(nph)), nph
            if g == 1:
                return "xs%d_%s" % (pop0, canon(nph)), nph
            return "xp%d_%s" % (g, canon(nph)), nph
        phases.append(cur)
    return None, "noperiod"


def components(cells, radius=2):
    cells = set(cells)
    seen, comps = set(), []
    for c in cells:
        if c in seen:
            continue
        stack, comp = [c], []
        seen.add(c)
        while stack:
            x, y = stack.pop()
            comp.append((x, y))
            for dx in range(-radius, radius + 1):
                for dy in range(-radius, radius + 1):
                    q = (x + dx, y + dy)
                    if q in cells and q not in seen:
                        seen.add(q)
                        stack.append(q)
        comps.append(comp)
    return comps


def orbit(cells, rule, gens):
    out = [frozenset(cells)]
    for _ in range(gens):
        out.append(step(out[-1], rule))
    return out


def split_pseudo(sub, rule, gens):
    """Split an object into groups that evolve independently (pseudo-objects).
    Start from 8-connected pieces and merge any pair whose joint evolution
    differs from their separate evolutions."""
    groups = [frozenset(p) for p in components(sub, 1)]
    # seed groups from the components of the whole orbit, so an oscillator whose
    # phase is disconnected stays one piece
    orb = set().union(*orbit(sub, rule, gens))
    seeds = [frozenset(c for c in sub if c in set(comp)) for comp in components(orb, 1)]
    seeds = [g for g in seeds if g]
    if len(seeds) >= 2:
        groups = seeds
    if len(groups) < 2:
        return None
    merged = True
    while merged and len(groups) > 1:
        merged = False
        orbs = [orbit(g, rule, gens) for g in groups]
        reach = [set().union(*o) for o in orbs]
        for i in range(len(groups)):
            for j in range(i + 1, len(groups)):
                near = any((x + dx, y + dy) in reach[j] for x, y in reach[i]
                           for dx in range(-2, 3) for dy in range(-2, 3))
                if not near:
                    continue
                joint = orbit(groups[i] | groups[j], rule, gens)
                if any(joint[t] != orbs[i][t] | orbs[j][t] for t in range(gens + 1)):
                    groups[i] = groups[i] | groups[j]
                    del groups[j]
                    merged = True
                    break
            if merged:
                break
    return groups if len(groups) > 1 else None


def lives_alone(part, rule, p):
    """part comes back to itself, in place, after p gens (period divides p)."""
    cur = frozenset(part)
    for _ in range(p):
        cur = step(cur, rule)
        if not cur:
            return False
    return cur == frozenset(part)


def find_split(cells, rule, p, max_cells=16):
    """Look for a split of a (non-moving) object into two parts A, B that each
    live on their own and evolve together exactly as apart: a pseudo-object.
    Exhaustive up to max_cells cells, otherwise only along 8-connected pieces.
    Returns (part A or None, 'exhaustive' | 'partial')."""
    cells = sorted(cells)
    n = len(cells)
    joint = orbit(cells, rule, p)

    def ok(a):
        b = [c for c in cells if c not in a]
        if not b or not lives_alone(a, rule, p) or not lives_alone(b, rule, p):
            return False
        oa, ob = orbit(a, rule, p), orbit(b, rule, p)
        return all(joint[t] == oa[t] | ob[t] for t in range(p + 1))

    if n <= max_cells:
        first, rest = cells[0], cells[1:]
        for mask in range(0, (1 << (n - 1)) - 1):
            a = {first} | {rest[i] for i in range(n - 1) if mask >> i & 1}
            if ok(a):
                return sorted(a), "exhaustive"
        return None, "exhaustive"
    pieces = components(cells, 1)
    for mask in range(1, (1 << len(pieces)) - 1):
        a = set().union(*[set(pieces[i]) for i in range(len(pieces)) if mask >> i & 1])
        if ok(a):
            return sorted(a), "partial"
    return None, "partial"


def identify(sub, rule, period):
    """Classify one object, splitting pseudo-objects into their constituents."""
    code, info = classify(sub, rule, period)
    if not code:
        return [("zz_" + info, sorted(sub))]
    p = int(code[2:].split("_")[0])
    parts = split_pseudo(sub, rule, max(p, 2))
    # only accept the split if every part is a periodic object on its own
    if parts and all(classify(part, rule, period)[0] for part in parts):
        out = []
        for part in parts:
            out += identify(part, rule, period)
        return out
    # touching objects (e.g. two still lifes sharing a border) are not split by
    # the orbit test above; try every two-way split like apgsearch's pseudo check
    if not code.startswith("xq") and len(sub) <= 40:
        part, _ = find_split(sub, rule, max(p, 1), SPLIT_MAX)
        if part:
            a = frozenset(part)
            return identify(a, rule, period) + identify(frozenset(sub) - a, rule, period)
    return [(code, sorted(sub))]


SPLIT_MAX = 16  # exhaustive pseudo-object check up to this many cells


def separate(state, period, rule):
    """Split a periodic soup ash into objects. Returns list of (code, cells)."""
    phases = [frozenset(state)]
    for _ in range(period - 1):
        phases.append(step(phases[-1], rule))
    union = set().union(*phases)
    results = []
    for comp in components(union):
        comp = set(comp)
        sub = frozenset(c for c in phases[0] if c in comp)
        if not sub:
            continue
        key, (ox, oy) = normalize(sub)
        if key not in MEMO:
            MEMO[key] = identify(key, rule, period)
        results += [(code, [(x + ox, y + oy) for x, y in cells]) for code, cells in MEMO[key]]
    return results


MEMO = {}
FULL_CENSUS = True  # set False for heavily searched rules (b3s23)


def work(args):
    rule_s, prefix, start, count, maxspan = args
    rule = parse_rule(rule_s)
    seeds = "".join(f"{i} {hashlib.sha256(f'{prefix}{i}'.encode()).hexdigest()}\n"
                    for i in range(start, start + count))
    # seeds go through a temp file: piping both ways can deadlock on macOS
    with tempfile.TemporaryFile("w+") as f:
        f.write(seeds)
        f.seek(0)
        out = subprocess.run([os.path.join(HERE, "soup"), rule_s, str(maxspan)], stdin=f,
                             capture_output=True, text=True, check=True).stdout
    tally = collections.Counter()
    samples = {}
    unstable = []
    for line in out.splitlines():
        f = line.split()
        kind, idx = f[0], int(f[1])
        if kind == "U":
            unstable.append(idx)
            continue
        if kind == "S":
            period, n = int(f[2]), int(f[4])
            nums = list(map(int, f[5:5 + 2 * n]))
            state = list(zip(nums[0::2], nums[1::2]))
            objs = separate(state, period, rule) if state else []
        else:
            n = int(f[3])
            nums = list(map(int, f[4:4 + 2 * n]))
            cells = frozenset(zip(nums[0::2], nums[1::2]))
            objs = []
            for piece in components(cells):
                objs += identify(frozenset(piece), rule, 64)
        for code, cells in objs:
            tally[code] += 1
            if code not in samples:
                samples[code] = (idx, cells)
    return tally, samples, unstable

# ---------- Catagolue census ----------

def census(rule, prefix):
    """Catagolue C1 counts for one apgcode prefix. For lightly searched rules the
    whole census is fetched once (prefix ALL); an empty census means no C1 soups."""
    os.makedirs(CACHE, exist_ok=True)
    if prefix != "ALL" and FULL_CENSUS:
        return census(rule, "ALL")
    path = os.path.join(CACHE, f"{rule}_{prefix}.csv")
    if not os.path.exists(path):
        url = f"https://catagolue.hatsya.com/textcensus/{rule}/C1" + ("" if prefix == "ALL" else f"/{prefix}")
        r = subprocess.run(["curl", "-sf", "--max-time", "60", url], capture_output=True, text=True)
        if r.returncode != 0 or not r.stdout.startswith('"apgcode"'):
            print("census fetch failed", url, file=sys.stderr)
            return None
        data = r.stdout
        open(path, "w").write(data)
    d = {}
    for line in open(path).read().splitlines()[1:]:
        parts = line.replace('"', "").split(",")
        if len(parts) == 2:
            d[parts[0]] = int(parts[1])
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rule", default="b3s23")
    ap.add_argument("--soups", type=int, default=10000)
    ap.add_argument("--prefix", default="hunt" + time.strftime("%Y%m%d%H%M%S"))
    ap.add_argument("--chunk", type=int, default=50)
    ap.add_argument("--rare", type=int, default=1000, help="flag codes with census count below this")
    ap.add_argument("--by-prefix", action="store_true", help="fetch census per prefix (big rules)")
    ap.add_argument("--maxspan", type=int, default=300, help="give up (U) when the soup grows wider than this")
    a = ap.parse_args()
    global FULL_CENSUS
    FULL_CENSUS = not a.by_prefix

    jobs = [(a.rule, a.prefix, s, min(a.chunk, a.soups - s), a.maxspan) for s in range(0, a.soups, a.chunk)]
    tally, samples, unstable = collections.Counter(), {}, []
    t0 = time.time()
    done, restarts = 0, 0
    while done < len(jobs):
        try:
            with ProcessPoolExecutor() as ex:
                for t, smp, u in ex.map(work, jobs[done:]):
                    tally.update(t)
                    for k, v in smp.items():
                        samples.setdefault(k, v)
                    unstable += u
                    done += 1
                    if done % 10 == 0:
                        print(f"\r{done * a.chunk} soups, {time.time() - t0:.0f}s", end="", file=sys.stderr)
        except BrokenProcessPool:
            # a worker was killed from outside (memory pressure, a stray pkill): results are
            # consumed in order, so restart the pool from the first unfinished chunk
            restarts += 1
            print(f"\nworker died at chunk {done}; restarting pool ({restarts})", file=sys.stderr)
            if restarts > 10:
                raise
    print(file=sys.stderr)

    finds = []
    for code, n in tally.most_common():
        if code.startswith("zz"):
            cens = None
        else:
            prefix = code.split("_")[0]
            table = census(a.rule, prefix)
            cens = None if table is None else table.get(code, 0)
        idx, cells = samples[code]
        finds.append({"code": code, "count": n, "census": cens, "soup": f"{a.prefix}{idx}",
                      "cells": cells})

    report = {"rule": a.rule, "prefix": a.prefix, "soups": a.soups, "seconds": round(time.time() - t0),
              "unstable": [f"{a.prefix}{i}" for i in unstable], "objects": finds}
    out = os.path.join(HERE, "results", f"{a.rule}_{a.prefix}.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump(report, open(out, "w"))

    print(f"rule {a.rule}: {a.soups} soups in {report['seconds']}s, {len(tally)} distinct objects")
    print("most common:", ", ".join(f"{c}×{n}" for c, n in tally.most_common(6)))
    print(f"\nRARE (census < {a.rare}) or UNSEEN:")
    for f in finds:
        if f["census"] is not None and f["census"] < a.rare:
            tag = "NEW?" if f["census"] == 0 else f"census {f['census']}"
            print(f"  {tag:>14}  {f['code']}  https://catagolue.hatsya.com/hashsoup/C1/{f['soup']}/{a.rule}")
    odd = [f for f in finds if f["code"].startswith("zz")]
    if odd:
        print("unclassified:", ", ".join(f"{f['code']}×{f['count']}" for f in odd))
    if unstable:
        print("never stabilized (possible guns/puffers):", ", ".join(report["unstable"][:10]))
    print("saved", out)


if __name__ == "__main__":
    main()
