# TASK: DOC-FIX-001: Close the DEC-001 report gap, repo hygiene, hypothesis tests, heat-effect numbers, and artifact dump for the final report

## Role & Worktree
- **Agent:** gemini (or claude-code). **Task ID:** DOC-FIX-001. **Branch:** `./scripts/task-worktree.sh start DOC-FIX-001` from the current tip of `master` (expected `44f0fb1` or later; if the tip is different, report it and continue).
- **First:** `git status --short`, `git log --oneline -5`, `ls docs/reports | grep DEC`, `ls patch/`, and `pytest -q 2>&1 | tail -5`. Paste all of it verbatim (expect `281 passed`).
- **Do NOT touch** `scripts/validate-report.py` in the main checkout (an uncommitted 42-line change of unknown origin): run `git diff scripts/validate-report.py` in the main checkout and paste the diff in your report; do not commit, stash or discard it. **Do not delete any worktree or branch.**
- **Time-box:** skip stretch goals; 30-minute cap per part; simplest version plus a logged limitation. No new decision may change the model or the recommendation.
- Reserved decision ID **[D-40]** for part C only (record it even if small).

## Part A: Hygiene (no model changes)
1. Write the missing report `docs/reports/DEC-001-gemini-decision.md` (template: `docs/reports/TASK-TEMPLATE.md`). Source it ONLY from files on disk: `results/recommendation.md`, `src/ccis_sim/decision/*`, `tests/test_decision.py`, `results/figures/`, [D-38]. Do not invent numbers; if a number is not in a file, omit it. List every touched file for the DEC task from `git log --stat` of the merge `2f03669`.
2. `docs/tasks/status.md`: set parent row `DEC-003` to `in-progress` (DEC-003.1/.2 stay `done`, DEC-003.3 stays `open`); set the `Status:` line of Phase 2 and Phase 3 to `done` and Phase 4 to `in-progress`. Change nothing else.
3. Patches: for SOL-001, BAT-001, BAT-002, OUT-001, INT-003 backfill `patch/<TASK>-gemini-<slug>.patch` from the merge commits (`git diff <merge>^1 <merge>`), where the slug matches the existing report file name. `patch/` is gitignored: never `git add -f`. If a merge commit cannot be found, write a one-line note in your report instead.
4. `./scripts/validate-report.py --all` must pass.

## Part B: Hypothesis tests (`src/ccis_sim/validation/hypothesis.py`, `tests/test_hypothesis.py`)
Use the existing `results/scenario_grid.csv` (re-run the small grid if the file is missing; do not run anything above ~5 minutes). Seeds are common random numbers across sizings, so tests are **paired by seed** where both sides share (weather, regime, seed).
1. Paired tests (Wilcoxon signed-rank as primary, paired t as secondary; report n, median difference, mean difference with 95% CI, p, Holm-adjusted p, and a paired effect size) on **unserved T1+2 kWh**, 2019 typhoon, bottom-up demand, for: (100 kWp, 50 kWh) vs (100, 100); (100, 100) vs (200, 100); (200, 100) vs (200, 200); and 0/0 vs (100, 100).
2. Paired by seed, grid import: 2016 vs 2019 weather (normal regime, grid-only and (100, 100)); +2 °C vs base (2019 normal, grid-only; 15 seeds from the +2 °C tranche).
3. Unpaired (Mann-Whitney U and Welch): typhoon vs normal regime unserved T1+2 for (100, 100), 2019.
4. State plainly in the output that p-values describe seed-to-seed simulation variability, not real-world inference, and that N is small. No claims of precision beyond the data.

## Part C: Heat-effect numbers (answers the project's primary question) → `results/heat_effect.md`, [D-40]
From grid-only runs (solar 0, battery 0, bottom-up demand, seed 0, deterministic demand) report a table for: 2019 baseline; 2019 with `temp_offset_c = +2`; 2016 hot year. Columns: annual kWh, cooling kWh (from `compute_cooling_demand` directly, same inputs), non-cooling kWh, cooling share, peak kW and its timestamp, mean daily kWh on days with mean temperature ≥ 30 °C vs < 26 °C, and the number of days ≥ 34 °C. Then fit and report a simple linear regression of **daily total kWh on daily mean temperature, school days only**, 2019: slope kWh/°C, intercept, R², n. Report the same numbers for the bill-calibrated demand (`demand_scale` ≈ 2.1047) in a second table. No new model code beyond calling existing functions.

## Part D: Artifact dump for the report writer (paste VERBATIM into the report; do not summarise)
1. `results/recommendation.md` (full), `results/kpi_tables.md` (full), `results/pareto_frontier.csv` (full), the first 40 rows of `results/dec_candidates.csv` (plus the column header and total row count).
2. The 2016 robustness table for the top-5 sizings, if it exists as a file.
3. `ls -la results/figures/` and the first line of each figure's generating function docstring.
4. `docs/context/research-synthesis.md`: output of `grep -n -i "http\|doi\|et al\|IEEE\|ref" docs/context/research-synthesis.md | head -80`, so the writer can see which references exist and with what completeness.
5. `wc -l` for every file under `src/ccis_sim/**.py` and `tests/*.py`, and write `results/program_listing_index.md` (table: path, lines, one-line purpose from the module docstring). Do not paste source code.
6. `git log --oneline -20` and the output of `./scripts/validate-report.py --all`.

## Acceptance
- [ ] Verbatim `pytest -q` tail at start and end (no annotations). Report lists every touched file.
- [ ] `DEC-001` report exists; status rows corrected; patches backfilled or noted; `validate-report.py --all` passes.
- [ ] Parts B, C and D outputs present in the report (tables, not prose). If a part fails, say why; do not weaken anything to make it pass.

## Output
Standard template: branch `task/DOC-FIX-001`, gitignored patch, report `docs/reports/DOC-FIX-001-<agent>-closeout.md`, append [D-40], update `status.md`, run `./scripts/validate-report.py`. Do not amend `master`; do not merge.
