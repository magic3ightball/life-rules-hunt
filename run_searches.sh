#!/bin/sh
# Real searches on the rules picked from results/screen_b3.md (2026-10-20).
cd "$(dirname "$0")"
for r in b3578s1267 b36s034678 b368s238; do
  python3 hunt.py --rule $r --soups 1000000 --chunk 2000 --prefix lrh_${r}_1020_ --rare 3 > results/run_$r.log 2>&1
done
echo ALLDONE >> results/run_b368s238.log
