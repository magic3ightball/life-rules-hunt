# Life Rules Hunt — handoff

Goal: find Life-like rules (outer-totalistic B/S, no B0) that are stable (soups settle) and
barely censused on Catagolue, then run real soup searches there and report objects that are
absent from Catagolue (especially spaceships `xq` and oscillators `xp` with period > 2).
Copied from `../life-hunt` (soup.c, hunt.py, gallery.py) on 2026-10-20; life-hunt itself was not touched.

Live: https://life-rules-hunt.vercel.app (Vercel project `life-rules-hunt`, scope magic3ightballs-projects),
also as a claude.ai Artifact (same page, private). Listed in the user's "배포 링크 모음" hub (Vercel group).

## Files
- `soup.c` → `soup`: C soup engine (apgsearch C1 hashsoup layout). Added vs life-hunt:
  optional `argv[2..5]` = maxspan, maxgen, maxpop, maxwork (explosive soups give up early → `U`),
  and stdin lines `R <rule>` switch rule mid-stream (batch screening in one process).
- `screen.py`: rule screen. Stage 1 = every rule × 12 soups (caps 200 span / 3000 gens / 1500 cells),
  stage 2 = survivors × 100 soups, then Catagolue C1 soup counts (`/census/<rule>/C1`, cached in
  `census_cache/c1count_*.txt`). `--family b3` = all rules with B3 and without B2 (16,384).
  `--rescore` re-ranks an existing `results/<out>.json` without re-running soups.
- `hunt.py`: search + object separation + apgcode + Catagolue comparison. Changes vs life-hunt:
  whole C1 textcensus fetched once (`--by-prefix` for huge rules like b3s23); S0 fix in `step`;
  pseudo-object splitting: orbit-component seeds, plus `find_split` = exhaustive two-way split test
  (≤16 cells; larger objects only along 8-connected pieces) so touching objects are separated like
  apgsearch does; `--maxspan`; seeds go to `soup` through a temp file (two-way pipes deadlocked on macOS);
  the worker pool restarts from the first unfinished chunk if a worker is killed (happened once).
- `verify.py`: re-checks every census-0 find (code reproduces + exhaustive pseudo-object test) → `results/verify.json`.
- `unstable.py`: re-runs a search's never-settled soups with maxspan 700 → settled / emitter / unsettled,
  `results/<rule>_unstable.json`.
- `gallery.py` → `gallery.html` (Artifact body) and `site/index.html` (full page for Vercel).
- `run_searches.sh` (three 1M searches), `run_b368.sh` (b368s238 search + unstable pass).
- `results/v1_before_pseudo_fix/`: first-round results kept for comparison (inflated "new" counts).

## Commands that worked
```
cc -O3 -march=native -o soup soup.c
python3 screen.py --family b3 --sample 0 --quick 12 --soups 100 --top 400 --out screen_b3   # ~7 min
./run_searches.sh                    # ~2 min + 2.5 min + ~36 min under load
python3 unstable.py --rule b368s238 --result results/b368s238_lrh_b368s238_1020_.json   # ~35 min
python3 verify.py
python3 gallery.py
cd site && npx vercel@latest deploy --prod --yes --scope magic3ightballs-projects --project life-rules-hunt
# then republish gallery.html to the Artifact (same file path / URL)
```

## Verified results (2026-10-20)
- Screen: 16,384 B3 rules → 4,161 stable → 18 emit spaceships. 600+ C1 counts looked up; only 9 have
  0 C1 soups (8 of them S0). Most stable B3 rules already have ≈1e6 C1 soups.
  Catagolue's `/rules/lifelike` list is NOT a census list: unlisted rules can have 1e8 soups.
- First round flagged 99 "new" objects in b3578s1267; verify.py showed 90 were pseudo-objects
  (touching known objects), including the p12 "find". After the hunt.py fix:
- b3578s1267 (Catagolue 2.5e5 soups): 1M soups, 43 kinds, 9 new strict objects (8 still lifes + xp2_21f0f12).
- b36s034678 (Catagolue 0 soups): 1M soups, 209 kinds (all unrecorded); 24 xp with p>2 all strict,
  e.g. xp18_0ouuv5iz3315 (`lrh_b36s034678_1020_586324`, partial check), xp14_173wso (`..._263880`).
- b368s238 (Catagolue 1.0e7 soups): 1M soups, 122 kinds, 9 new strict objects (8 still lifes 14–17 cells
  + xp2_5t5z555). No new spaceships in any rule.
- b368s238 never-settled soups (5,755): 3,051 settle in a bigger box (no rare objects), 705 emit objects
  regularly (mostly every 48/96 gens: puffers/guns), 1,999 still unsettled. Catagolue already records
  1,017,314 "zz_LINEAR" soups for this rule, so the emitters are not new discoveries.
- verify.py on final results: 42/42 new finds strict, codes reproduce. b3s23 regression: no false "new".
- Links: `https://catagolue.hatsya.com/hashsoup/C1/<soup>/<rule>`. Nothing uploaded to Catagolue.

## Next steps
1. Optional: look at the emitter soups in Golly to identify the p48/p96 puffer (Catagolue does not name it).
2. If the user wants credit for the 18 strict finds in censused rules, run official apgsearch there
   (not done; the user said no upload).

## Risks
- Pseudo-object test is exhaustive only up to 16 cells (18 in verify.py); bigger ones are checked on
  8-connected pieces only (marked "partial" on the page).
- S0 rules: every isolated cell is an object `xs1_1`; all objects are "new" when the census is 0.
- Other sessions load the machine heavily (load 80–600); timings vary a lot.
