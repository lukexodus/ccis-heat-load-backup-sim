# Task Report: DOC-004 — Report follow-ups: readable Figure 3, §5.2 CLI row, test-file count

**Date:** 2026-10-26  
**Agent:** claude-code  
**Task ID:** DOC-004  
**Status:** done  
**Commit:** `1cc40d5` — `docs([DOC-004]): readable Figure 3, correct §5.2 CLI row, test-file count`  
**Patch File:** `patch/DOC-004-claude-code-report-followups.patch`  
**Branch / Worktree:** `task/DOC-004` at `../ccis-heat-load-backup-sim-DOC-004`, based on `c2f68bc` (`task/DOC-003` tip)

---

## 1. Executive Summary

Three defects found in the DOC-003 review are closed. Figure 3's x-axis labels no longer overlap: the three categories are drawn on two lines each and the figure is slightly wider, with the same data, colours, boxplots, means and outliers. The §5.2 architecture table no longer claims `cli.py` lives under `integration/`; it records the module as top-level. The test-side count is now stated the same way everywhere: 22 test modules plus `tests/__init__.py`, which is why `results/program_listing_index.md` counts 23 test-side entries.

No finding, number or conclusion changed. Source-line totals are unchanged at 9,298 on disk and 9,679 in the listing; the `plots.py` edit was kept line-neutral on purpose.

Tests: **290 passed** at start and **290 passed** at end.

---

## 2. Implementation Details

### 2.1 Figure 3 (`src/ccis_sim/decision/plots.py`)

- Category labels changed from single long strings ("Moderate System (100 kWp / 50 kWh)", …) to two lines each: `100 kWp / 50 kWh` + `(moderate system)`, `200 kWp / 150 kWh` + `(recommended)`, `200 kWp / 200 kWh` + `(max grid cap)`. Same order, same sizing identifiers.
- Figure size 8.5 × 5 → 9.0 × 5.2 in; x tick label size set to 9 pt. One additional statement, offset by merging a blank line, so the module stays at 368 lines and no source-line total moves.
- Boxplot call, series colours (`#3498db`, `#2ecc71`, `#9b59b6`), median/mean rendering, y-axis and title are untouched.
- Regenerated **only** Figure 3, without running the decision pipeline: a throw-away script regenerated the 600 underlying runs (three sizings × 50 seeds × two regimes × two demand scales, 2019 weather, same `generate_dec_configs`/`run_candidate_simulations` calls the pipeline uses) and called `plot_unserved_distribution(runs, recommended_pair=(200, 150))`. The script lives in `/tmp`, is not committed, and writes only `results/figures/fig3_unserved_distribution.png`.
- Figure 3 caption in §7.5 updated: the sentence about overlapping labels is gone; the caption now names the three groups in plot order.

### 2.2 §5.2 architecture table

Verified against the tree: `src/ccis_sim/cli.py` sits at the top level, beside the `core/`, `weather/`, … packages; `src/ccis_sim/integration/` contains `engine.py`, `scenarios.py`, `exporters.py`, `baseline.py`. The `integration/` row now reads "Engine, exporters, Monte Carlo scenario runner", and a new row records `cli.py` (top level) as the command-line entry point. `docs/paper/illustrations.md` D3 already shows `cli.py` at the top and was not changed; §10's command block refers to the console script, which remains accurate.

### 2.3 Test-file count

`tests/` contains **22** `test_*.py` modules plus `tests/__init__.py` and a `fixtures/` directory; there is no `conftest.py`. `results/program_listing_index.md` counts 23 because it lists `tests/__init__.py` as an entry. The generator only walks `test_*.py`, hence "22". Standard wording now used in the report (§5.2, §10, Appendix C) and in the generator: **"22 test modules plus `tests/__init__.py`"**. Both listings were regenerated so the generated text matches.

### 2.4 Conformance

Figures and statistics are governed by [D-38] and unchanged; the figure fix is presentation-only. No decision ID was reserved for DOC-004 and none was needed; nothing was logged to the decision log.

---

## 3. Verification & Test Evidence

### 3.1 Test execution

Start of task, clean worktree at `c2f68bc`:

```text
290 passed, 17 warnings in 385.86s (0:06:25)
```

End of task, after all edits:

```text
290 passed, 17 warnings in 102.83s (0:01:42)
```

### 3.2 Figure 3 data and appearance

The regenerated runs give exactly 50 samples per group (typhoon regime, bottom-up demand):

| Group | n | Median | Mean | Q1 | Q3 |
| :-- | --: | --: | --: | --: | --: |
| 100 kWp / 50 kWh | 50 | 174.68 | 171.08 | 73.45 | 217.51 |
| 200 kWp / 150 kWh (recommended) | 50 | 23.14 | 34.28 | 6.77 | 45.20 |
| 200 kWp / 200 kWh | 50 | 13.71 | 25.89 | 2.23 | 24.61 |

Image opened after regeneration. Verdict: the three labels are fully readable at page width with no overlap; order is moderate, recommended, maximum grid cap, left to right; boxes, whiskers, outlier circles, means (dashed green) and medians (orange) are visually identical to the previous figure — e.g. the 100/50 box still spans about 73–218 kWh with a whisker to about 390 and one outlier near 450; the recommended box is still much tighter with outliers to about 210.

The quartiles and means match the previous image; the medians I recorded in the DOC-003 report as "about 170, 27 and 16 kWh" were eyeball readings from the old figure. The exact values are 174.68, 23.14 and 13.71 kWh. Same data, corrected readings; the old figure is not kept, so this note is the record.

### 3.3 Only Figure 3 changed among results files

```text
 M docs/paper/CCIS-engineering-report.md
 M docs/paper/program-listing-core.md
 M docs/paper/program-listing.md
 M docs/tasks/status.md
 M results/figures/fig3_unserved_distribution.png
 M scripts/build_program_listing.py
 M src/ccis_sim/decision/plots.py
```

`results/figures/fig3_unserved_distribution.png` is the only results file in the list; no other CSV, figure or JSON was touched. SHA-256 of the new image: `29c1cca22607e8b256f376c208fbe4090283c80f6afb951f012e737a328db40d` (66,475 → 64,473 bytes).

### 3.4 Listing determinism

Two consecutive regenerations after the wording fix:

```text
8a5c7568713a02ce69a4fa2af39d6bada28f05d448646900188340613be98ea9  docs/paper/program-listing-core.md
dad9f95df30105219290dba17f757f726e64fc7cdad941532ed28b20af1cb029  docs/paper/program-listing.md
8a5c7568713a02ce69a4fa2af39d6bada28f05d448646900188340613be98ea9  docs/paper/program-listing-core.md
dad9f95df30105219290dba17f757f726e64fc7cdad941532ed28b20af1cb029  docs/paper/program-listing.md
```

Line counts unchanged: `program-listing.md` 10,063 lines (398,097 bytes), `program-listing-core.md` 4,768 lines (202,444 bytes). Source total in the listing is still 9,679 lines, on-disk source still 9,298.

### 3.5 Consistency and path checks

- Report, §10 and Appendix C all use "22 test modules plus `tests/__init__.py`"; the generator prints the same.
- Every relative image path in the report resolves from `docs/paper/` (five paths, all `OK`, checked with a small path script).
- `./scripts/validate-report.py docs/reports/DOC-004-claude-code-report-followups.md` and `--all` pass.

---

## 4. Decisions Recorded

None. No decision ID was reserved; the changes are presentation and wording only and do not alter any recorded choice.

---

## 5. Unified Git Diff

Generated listings and the Figure 3 binary are excluded from the pasted diff; their hashes and line counts are in §3.4. The committed patch in `patch/` includes them.

```diff
diff --git i/docs/paper/CCIS-engineering-report.md w/docs/paper/CCIS-engineering-report.md
index 30df2ad..bb6d2b6 100644
--- i/docs/paper/CCIS-engineering-report.md
+++ w/docs/paper/CCIS-engineering-report.md
@@ -163,11 +163,12 @@ Python 3.14 with NumPy, pandas and SciPy: transparent, scriptable, easy to test.
 | `solar/` | Irradiance transposition, NOCT thermal derating, array scaling and inverter clipping |
 | `battery/` | Dispatch dynamics, reserve floors, idle losses |
 | `outage/` | Outage sampler with typhoon coupling, tiered shedding, unserved-energy tracker |
-| `integration/` | Engine, CLI, exporters, Monte Carlo scenario runner |
+| `integration/` | Engine, exporters, Monte Carlo scenario runner |
 | `validation/` | Audit, plausibility, sensitivity, hypothesis tests |
 | `decision/` | AHP, Pareto frontier, sizing rule, figures |
+| `cli.py` (top level, beside the packages) | Command-line entry point (`ccis-sim run`): argument parsing and summary printing |
 
-About 9,300 lines of source (42 files) and 6,000 lines of tests (23 files); the full per-file index is in Appendix C.
+About 9,300 lines of source (42 files) and 6,000 lines of tests (22 test modules plus `tests/__init__.py`); the full per-file index is in Appendix C.
 
 ### 5.3 Engine limitations that shape the results
 1. **The battery never charges from the grid.** With no PV, a battery discharges once and stays at its floor (about 0.8 cycles per year). Battery-only designs are therefore excluded ([D-38]) and no conclusion about grid-charged storage should be drawn.
@@ -310,7 +311,7 @@ The five figures below are tracked images in `results/figures/` and are referenc
 
 ![Figure 3: Distribution of unserved Tier 1+2 energy across 50 seeds for three sizings](../../results/figures/fig3_unserved_distribution.png)
 
-**Figure 3.** Box plots of annual unserved Tier 1+2 energy across 50 typhoon-regime seeds for three sizings: 100 kWp / 50 kWh, the recommended 200 kWp / 150 kWh, and 200 kWp / 200 kWh. The boxes show the interquartile range, the orange line the median, the dashed green line the mean, and the circles are outliers. The x-axis category labels overlap and are hard to read at page width; the three groups are, left to right, the order just listed.
+**Figure 3.** Box plots of annual unserved Tier 1+2 energy across 50 typhoon-regime seeds for three sizings, left to right on the x-axis: 100 kWp / 50 kWh (moderate system), the recommended 200 kWp / 150 kWh, and 200 kWp / 200 kWh (maximum grid cap). The boxes show the interquartile range, the orange line the median, the dashed green line the mean, and the circles are outliers.
 
 ![Figure 4: Pareto trade-off, cost index versus Tier 1+2 outage hours served, both demand cases](../../results/figures/fig4_pareto_scatter.png)
 
@@ -412,7 +413,7 @@ Simulation artifacts saved to: /tmp/tmp.Q3VZu5NzpW
 The listing is generated by `scripts/build_program_listing.py` (deterministic: sorted paths, no timestamps). Two versions are provided, because the instructor has not said whether the full source or a core selection is required:
 
 - **`docs/paper/program-listing.md`** — the **full listing**: all 42 files of `src/ccis_sim/` plus `scripts/run_decision_pipeline.py`, 43 files and 9,679 lines, about 389 KB. Tests are listed by path, length and purpose, not reproduced.
-- **`docs/paper/program-listing-core.md`** — the **core selection**: 15 files and 4,572 lines, about 198 KB, covering the domain models, equipment audit, occupancy, demand, solar, battery, outage, shedding, engine and the AHP/Pareto sizing pipeline; the remaining 28 source files and all 22 test files are listed by index only.
+- **`docs/paper/program-listing-core.md`** — the **core selection**: 15 files and 4,572 lines, about 198 KB, covering the domain models, equipment audit, occupancy, demand, solar, battery, outage, shedding, engine and the AHP/Pareto sizing pipeline; the remaining 28 source files and all 22 test modules (plus `tests/__init__.py`) are listed by index only.
 
 Appendix C gives the index of every file. Reproduce the results with:
 
@@ -464,7 +465,7 @@ Bottom-up demand, 2019 typhoon, N = 50 (selected rows; the full table is in `res
 
 Two generated listings are supplied (§10): `docs/paper/program-listing.md` (full, 43 source files, 9,679 lines) and `docs/paper/program-listing-core.md` (core selection, 15 files, 4,572 lines, plus an index of the rest).
 
-The complete per-file index, including every test file, is `results/program_listing_index.md` (65 entries: 42 source and 23 test files; largest files `core/verification.py` 919 lines, `outage/sampler.py` 510, `integration/engine.py` 490, `solar/irradiance.py` 429). One entry in that index is stale by three lines: `validation/hypothesis.py` is listed at 340 lines and the file on disk has 343; the generated listings use the on-disk count, so total source lines are 9,298 rather than the index's 9,295.
+The complete per-file index, including every test file, is `results/program_listing_index.md` (65 entries: 42 source files and 23 test-side files, the latter being 22 test modules plus `tests/__init__.py`; largest files `core/verification.py` 919 lines, `outage/sampler.py` 510, `integration/engine.py` 490, `solar/irradiance.py` 429). One entry in that index is stale by three lines: `validation/hypothesis.py` is listed at 340 lines and the file on disk has 343; the generated listings use the on-disk count, so total source lines are 9,298 rather than the index's 9,295.
 
 ## Appendix D. Known limitations and open items
 
diff --git i/docs/tasks/status.md w/docs/tasks/status.md
index 9f37b23..124e6b7 100644
--- i/docs/tasks/status.md
+++ w/docs/tasks/status.md
@@ -158,3 +158,4 @@ Status: **in-progress**
 | DEC-003.3   | Compile comprehensive engineering report markdown                   | `done` | [CCIS-engineering-report.md](../paper/CCIS-engineering-report.md) [report](../reports/DEC-003.3-claude-code-engineering-report.md) |
 | **DOC-FIX-001** | **Report Gap Closure, Hygiene, Hypothesis Tests & Heat-Effect Numbers** | `done` | [DOC-FIX-001-claude-code-closeout.md](../reports/DOC-FIX-001-claude-code-closeout.md) [D-40] |
 | **DOC-003** | **Complete engineering report against course Project Outline** | `done` | [DOC-003-claude-code-report-completion.md](../reports/DOC-003-claude-code-report-completion.md) [D-41] Title block, §3.4 diagrams, §4.3–4.4 data handling, §6.6 SME status, §7.5 figures 1–6, §10 listings, Appendix E |
+| **DOC-004** | **Report follow-ups: readable Figure 3, §5.2 CLI row, test-file count** | `done` | [DOC-004-claude-code-report-followups.md](../reports/DOC-004-claude-code-report-followups.md) Figure 3 labels, `cli.py` row, "22 test modules plus `tests/__init__.py`" |
diff --git i/scripts/build_program_listing.py w/scripts/build_program_listing.py
index 8ceb36c..03c34a4 100644
--- i/scripts/build_program_listing.py
+++ w/scripts/build_program_listing.py
@@ -141,7 +141,8 @@ def build_full(files: list[str], tests: list[str], index, counts) -> str:
             "script after any source change.",
             "",
             f"Source files: **{len(files)}** ({src_lines:,} lines). "
-            f"Test files are listed by index only: **{len(tests)}** ({test_lines:,} lines).",
+            f"Test modules are listed by index only: **{len(tests)}** "
+            f"(plus `tests/__init__.py`), {test_lines:,} lines.",
         ],
     )
     lines.extend(render_index_table(files, index, counts, "Contents"))
@@ -168,7 +169,8 @@ def build_core(files: list[str], tests: list[str], index, counts) -> str:
             "the integration engine, and the AHP/Pareto sizing pipeline.",
             "",
             f"Reproduced here: **{len(core)}** files ({core_lines:,} lines). "
-            f"Indexed only: **{len(rest_src)}** remaining source files and **{len(tests)}** test files.",
+            f"Indexed only: **{len(rest_src)}** remaining source files and **{len(tests)}** "
+            f"test modules (plus `tests/__init__.py`).",
         ],
     )
     lines.extend(render_index_table(core, index, counts, "Core modules included"))
diff --git i/src/ccis_sim/decision/plots.py w/src/ccis_sim/decision/plots.py
index eb29aea..4fc830e 100644
--- i/src/ccis_sim/decision/plots.py
+++ w/src/ccis_sim/decision/plots.py
@@ -176,9 +176,9 @@ def plot_unserved_distribution(
 
     rec_sol, rec_bat = recommended_pair
     triplet = [
-        (100.0, 50.0, "Moderate System (100 kWp / 50 kWh)"),
-        (rec_sol, rec_bat, f"Recommended ({rec_sol:.0f} kWp / {rec_bat:.0f} kWh)"),
-        (200.0, 200.0, "Maximum Grid Cap (200 kWp / 200 kWh)"),
+        (100.0, 50.0, "100 kWp / 50 kWh\n(moderate system)"),
+        (rec_sol, rec_bat, f"{rec_sol:.0f} kWp / {rec_bat:.0f} kWh\n(recommended)"),
+        (200.0, 200.0, "200 kWp / 200 kWh\n(max grid cap)"),
     ]
 
     data_to_plot = []
@@ -192,7 +192,7 @@ def plot_unserved_distribution(
             data_to_plot.append(np.array([0.0]))
             labels.append(name)
 
-    fig, ax = plt.subplots(figsize=(8.5, 5), dpi=150)
+    fig, ax = plt.subplots(figsize=(9.0, 5.2), dpi=150)
     box = ax.boxplot(
         data_to_plot,
         tick_labels=labels,
@@ -200,7 +200,7 @@ def plot_unserved_distribution(
         showmeans=True,
         meanline=True,
     )
-
+    ax.tick_params(axis="x", labelsize=9)
     colors = ["#3498db", "#2ecc71", "#9b59b6"]
     for patch, color in zip(box["boxes"], colors):
         patch.set_facecolor(color)
```

---

## 6. Flagged for APC / Operator Attention

- [ ] **DOC-003 flagged item closed.** "Figure 3 is defective" no longer applies: labels are readable and the figure was regenerated. The DOC-003 report was not edited, per instruction.
- [ ] **Median readings in the DOC-003 report were approximate.** It says "medians ~170, ~27, ~16 kWh"; exact values are 174.68, 23.14 and 13.71 kWh. Quartiles and means match the old image, so the underlying data are the same — the earlier numbers were eyeball readings, not different results. If the APC quotes medians anywhere, use the exact set.
- [ ] **§5.2 table header now spans a module.** The row is labelled "`cli.py` (top level, beside the packages)" under a "Package | Role" header. Accurate but slightly off-header; a reviewer may prefer a separate sentence under the table. Left as a row because it is easier to find.
- [ ] **`results/program_listing_index.md` still counts 23 test-side entries.** That is correct (22 modules + `tests/__init__.py`) and the report now says so explicitly. The index also still lists `validation/hypothesis.py` at 340 lines against 343 on disk (pre-existing, disclosed in Appendix C).
- [ ] **Figure 3 was regenerated from a local re-run, not from committed data.** The 600 runs are reproducible from `generate_dec_configs` + `run_candidate_simulations` with the same seeds, but no CSV is committed (CSVs are gitignored by policy), so the image cannot be re-derived without re-running.
- [ ] **`scripts/validate-report.py` is still modified in the main checkout** (not authored here; not touched). This worktree has the committed validator.
- [ ] **Merge order unchanged:** DOC-FIX-001 → DEC-003.3 → DOC-003 → DOC-004. `master` is still `6efa69f`.
