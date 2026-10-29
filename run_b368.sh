#!/bin/sh
cd "$(dirname "$0")"
python3 hunt.py --rule b368s238 --soups 1000000 --chunk 2000 --prefix lrh_b368s238_1020_ --rare 3 > results/run_b368s238.log 2>&1
python3 unstable.py --rule b368s238 --result results/b368s238_lrh_b368s238_1020_.json > results/unstable_b368s238.log 2>&1
echo ALLDONE >> results/unstable_b368s238.log
