# Task Report: DEC-001 — Multi-Criteria Decision Analysis (AHP), Pareto Sizing, and Decision Figures

**Date:** 2026-10-26 (reconstructed from on-disk artifacts; original work merged 2026-10-21)
**Agent:** gemini (original implementation) — report reconstructed on disk by claude-code under DOC-FIX-001
**Task ID:** DEC-001 (covers DEC-002 and DEC-003.1/.2)
**Status:** done
**Commit:** merge `2f03669` (branch tip `06dc3f9`)
**Patch File:** `patch/DEC-001-gemini-decision.patch`

---

## 1. Executive Summary

DEC-001 implements the Analytic Hierarchy Process (AHP) weighting engine, DEC-002 applies it to candidate sizing configurations with a Pareto frontier and a pre-registered recommendation rule, and DEC-003.1/.2 produce five publication figures. The implementation landed on `master` via merge commit `2f03669`; its code, tests, results, and figures are on disk, but the mandatory task report was never written by the original agent. This report reconstructs that missing deliverable **only from files on disk** — no numbers are invented.

Headline outcome: **200 kWp PV / 150 kWh battery** is the recommended sizing under the pre-registered rule, classified **DEMAND-DEPENDENT**. It reaches 90.5% mean Tier 1+2 outage-hours served under bottom-up demand (95% CI ±2.61%) but only 68.4% (±3.76%) under bill-calibrated demand, so it does not satisfy the 80% bill-calibrated threshold; the rule's documented fallback reports the best achievable case and the trade-off.

---

## 2. Implementation Details

### 2.1 Changes Made (from merge `2f03669`)

Files touched by the DEC task, verbatim from `git diff --name-status 917b95b 2f03669`:

- `A src/ccis_sim/decision/ahp.py` — Saaty principal-eigenvector AHP solver, consistency ratio, weight sets, candidate scoring.
- `A src/ccis_sim/decision/sizing.py` — candidate generation (24 sizings + 0/0 reference), batch simulation, aggregation, Pareto frontier, pre-registered selection rule.
- `A src/ccis_sim/decision/plots.py` — five matplotlib figures (7-day dispatch, SoC duration, unserved distribution, Pareto scatter, monthly demand comparison).
- `M src/ccis_sim/decision/__init__.py` — package exports.
- `A scripts/run_decision_pipeline.py` — orchestrates 5,000 candidate runs, 1,000 robustness runs, AHP scoring, Pareto analysis, recommendation markdown, and figures.
- `A tests/test_decision.py` — 10 tests covering AHP consistency, scoring, Pareto dominance, and recommendation selection.
- `A results/recommendation.md`, `A results/figures/fig1`–`fig5` — generated outputs.
- `A patch/DEC-001-gemini-decision.patch` — the original patch artifact.
- `M docs/decisions/decision-log.md` — appended [D-38] and reserved [D-39].
- `M docs/tasks/status.md` — marks DEC-001, DEC-002, DEC-003.1, DEC-003.2 done.

### 2.2 Conformance to Specifications & Decisions

- [D-38] fixes the AHP matrix, cost proxy, solar = 0 exclusion, Pareto dominance definition, and the 90%/80% recommendation rule before evaluation.
- [D-35] dispatch topology means the battery never charges from the grid; [D-38] therefore excludes battery-only cases as physically non-viable.
- [D-36] common random numbers (CRN) are reused across sizings so paired seed comparisons are valid.
- [D-18] caps sizing at 200 kWp / 200 kWh.
- Costs remain a dimensionless index (`solar_kwp × 1.0 + battery_kwh × r`, base `r = 0.6`); no peso figures are produced.

### 2.3 AHP Parameters (from [D-38])

| Quantity | Value |
| :--- | :--- |
| λmax | 4.0192 |
| Consistency index (CI) | 0.0064 |
| Random index (RI₄) | 0.90 |
| Consistency ratio (CR) | 0.0071 (threshold ≤ 0.10) |
| Reliability weight | 0.5872 |
| Cost weight | 0.2179 |
| Self-sufficiency weight | 0.1228 |
| Curtailment weight | 0.0722 |

Sensitivity weight sets: equal (`0.25` each) and reliability-heavy (`0.60 / 0.20 / 0.10 / 0.10`); cost-ratio sensitivity `r ∈ {0.3, 0.6, 1.0}`.

---

## 3. Verification & Test Evidence

### 3.1 Test Execution

Command executed in the DOC-FIX-001 worktree:

```bash
python -m pytest tests/test_decision.py -q
```

**Results:**
- Tests passed: 10
- Tests failed: 0
- Tests skipped: 0

```text
..........                                                               [100%]
10 passed in 18.79s
```

Full suite on the same commit: `281 passed in 61.53s`.

### 3.2 Result Evidence (from `results/recommendation.md`)

Recommended sizing performance ($N = 50$ CRN seeds):

| Demand case | Solar (kWp) | Battery (kWh) | Cost index | T1+2 outage served mean | 95% CI | Self-sufficiency |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| Bottom-up (1.0×) | 200 | 150 | 290.0 | 90.5% | ±2.61% | 84.9% |
| Bill-calibrated (~2.10×) | 200 | 150 | 290.0 | 68.4% | ±3.76% | 54.5% |

AHP top candidate under bottom-up demand is 150 kWp / 150 kWh (score 0.7506); the pre-registered selection rule still selects 200 kWp / 150 kWh because the rule prioritizes the reliability threshold, not the AHP rank, and requires the cheapest qualifying non-dominated sizing.

2016 robustness re-run on the top-5 sizings keeps every candidate within +1.9 to +4.5 percentage points of its 2019 reliability (all "Consistent").

### 3.3 Figures

`results/figures/fig1_dispatch_7day.png`, `fig2_soc_duration_curve.png`, `fig3_unserved_distribution.png`, `fig4_pareto_scatter.png`, `fig5_monthly_demand_comparison.png`.

---

## 4. Decisions Recorded

- **[D-38]**: AHP formulation, cost proxy, solar = 0 exclusion, Pareto dominance rule, and pre-registered recommendation rule (90% bottom-up / 80% bill-calibrated).
- **[D-39]**: Reserved, unused.

---

## 5. Unified Git Diff

`patch/DEC-001-gemini-decision.patch` contains the complete verbatim unified diff of the DEC task (1,994 lines). Because this report is a reconstruction, the full 3,897-line merge diff is not re-pasted here; the merge diffstat is:

```text
 docs/decisions/decision-log.md                     |   32 +
 docs/tasks/status.md                               |   24 +-
 patch/DEC-001-gemini-decision.patch                | 1994 ++++++++++++++++++++
 results/figures/fig1_dispatch_7day.png             |  Bin 0 -> 253139 bytes
 results/figures/fig2_soc_duration_curve.png        |  Bin 0 -> 99312 bytes
 results/figures/fig3_unserved_distribution.png     |  Bin 0 -> 66475 bytes
 results/figures/fig4_pareto_scatter.png            |  Bin 0 -> 236503 bytes
 results/figures/fig5_monthly_demand_comparison.png |  Bin 0 -> 75907 bytes
 results/recommendation.md                          |  129 ++
 scripts/run_decision_pipeline.py                   |  381 ++++
 src/ccis_sim/decision/__init__.py                  |   56 +-
 src/ccis_sim/decision/ahp.py                       |  283 +++
 src/ccis_sim/decision/plots.py                     |  368 +++
 src/ccis_sim/decision/sizing.py                    |  392 +++
 tests/test_decision.py                             |  251 +++
 15 files changed, 3897 insertions(+), 13 deletions(-)
```

Representative verbatim excerpt (`git diff 917b95b 2f03669 -- src/ccis_sim/decision/__init__.py`):

```diff
diff --git a/src/ccis_sim/decision/__init__.py b/src/ccis_sim/decision/__init__.py
index 2f2746f..9355c04 100644
--- a/src/ccis_sim/decision/__init__.py
+++ b/src/ccis_sim/decision/__init__.py
@@ -1 +1,55 @@
-"""Multi-criteria decision analysis (AHP) and sizing trade-off optimization engines."""
+"""Multi-criteria decision analysis (AHP), Pareto trade-off optimization, and figure visualization."""
+
+from __future__ import annotations
+
+from ccis_sim.decision.ahp import (
+    CRITERIA_NAMES,
+    ahp_weights,
+    compute_cost_index,
+    get_ahp_weight_sets,
+    get_base_pairwise_matrix,
+    score_candidates,
+)
+from ccis_sim.decision.plots import (
+    ensure_figures_dir,
+    plot_7day_dispatch,
+    plot_monthly_demand_comparison,
+    plot_pareto_scatter,
+    plot_soc_duration_curve,
+    plot_unserved_distribution,
+)
+from ccis_sim.decision.sizing import (
+    CANDIDATE_BATTERY_SIZES,
+    CANDIDATE_SOLAR_SIZES,
+    aggregate_candidates_for_decision,
+    compute_cell_statistics,
+    generate_dec_configs,
+    get_candidate_sizing_pairs,
+    identify_pareto_frontier,
+    run_candidate_simulations,
+    select_recommended_sizing,
+)
+
+__all__ = [
+    "CRITERIA_NAMES",
+    "ahp_weights",
+    "compute_cost_index",
+    "get_ahp_weight_sets",
+    "get_base_pairwise_matrix",
+    "score_candidates",
+    "CANDIDATE_SOLAR_SIZES",
+    "CANDIDATE_BATTERY_SIZES",
+    "get_candidate_sizing_pairs",
+    "generate_dec_configs",
+    "run_candidate_simulations",
+    "compute_cell_statistics",
+    "aggregate_candidates_for_decision",
+    "identify_pareto_frontier",
+    "select_recommended_sizing",
+    "ensure_figures_dir",
+    "plot_7day_dispatch",
+    "plot_soc_duration_curve",
+    "plot_unserved_distribution",
+    "plot_pareto_scatter",
+    "plot_monthly_demand_comparison",
+]
```

The complete unified diff is the on-disk patch artifact.

---

## 6. Flagged for APC / Operator Attention

- [x] This report was missing from the original DEC merge; it is reconstructed from `results/recommendation.md`, `src/ccis_sim/decision/*`, `tests/test_decision.py`, `results/figures/`, and [D-38].
- [ ] `DEC-003.3` (final engineering report) remains open; the APC writes it per `docs/prompts/DEC-001-002-PROMPT.md`.
- [ ] The recommendation is demand-dependent: the bill-calibrated case misses the 80% threshold (68.4%).
- [ ] AHP top-ranked candidate (150 kWp / 150 kWh) differs from the rule-selected recommendation (200 kWp / 150 kWh). The final report must explain that the rule, not the AHP score, drives selection.
