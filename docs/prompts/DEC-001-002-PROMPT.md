# TASK: DEC-001 + DEC-002 (+ DEC-003.1/.2 figures): AHP, Pareto Frontier, Recommended Sizing (deadline-compressed)

## Role & Worktree
- **Agent:** gemini (or claude-code). **Task IDs:** DEC-001, DEC-002, DEC-003.1, DEC-003.2 (NOT DEC-003.3; the APC writes the report). **Branch:** `./scripts/task-worktree.sh start DEC-001` from the current tip of `master` (INT-002 and INT-003 must already be merged: check `src/ccis_sim/integration/scenarios.py` and `src/ccis_sim/validation/` exist; stop and report otherwise).
- **First:** `pytest -q 2>&1 | tail -5`, paste verbatim (expect about 271 passed).
- **Time-box:** the deadline is tonight. Total compute under 25 minutes (multiprocessing, reuse `run_grid`). Skip stretch goals; 30-minute cap per subtask; simplest version plus a logged limitation.
- Read: `docs/decisions/decision-log.md` (D-08, D-11, D-17, D-18, D-34 to D-37), `docs/reports/INT-002-*.md`, `docs/reports/INT-003-*.md`, `src/ccis_sim/integration/scenarios.py`.

## Facts you must respect (do not "fix" them)
- Bottom-up demand = primary (`demand_scale` 1.0). Bill-calibrated (`demand_scale` ≈ 2.1047) = labelled sensitivity ([D-36]). **Every recommendation must be shown under both.**
- **Engine limitation:** the battery charges only from PV surplus, never from the grid, so any 0-kWp battery case is not meaningful. **Exclude solar = 0 from the candidate set** (keep 0/0 as the reference baseline only). State this in [D-38].
- Tier 3 (including cooling) is shed during outages **by policy**, so "reliability" means **Tier 1+2** only.
- N = 30 seeds gave a 95% CI half-width of ~32% of the mean for typhoon unserved energy (INT-002.2). Heavy-tailed. Use common random numbers, report CIs, and do not claim precision the data lack.
- PV cap 200 kWp, battery cap 200 kWh ([D-18]). Costs are **assumptions**, not data: the model reports energy, not pesos.

## DEC-001: AHP (`src/ccis_sim/decision/ahp.py`)
1. `ahp_weights(matrix) -> (weights, lambda_max, CI, CR)` using the principal eigenvector; Saaty RI table; **CR ≤ 0.10 asserted** (raise otherwise).
2. Criteria (4): **Reliability** (mean fraction of outage hours with Tier 1+2 fully served, typhoon regime, plus mean unserved T1+2 kWh as the tie-breaker); **Cost index**; **Self-sufficiency**; **Curtailment** (lower is better).
3. Pairwise judgments, base case (Saaty 1–9; state them in [D-38] as the APC's proposal, editable): Reliability vs Cost = 3, vs Self-sufficiency = 5, vs Curtailment = 7; Cost vs Self-sufficiency = 2, vs Curtailment = 3; Self-sufficiency vs Curtailment = 2. Report the weights and CR. Also run **equal weights** and a **reliability-heavy** set (0.6/0.2/0.1/0.1).
4. Cost index (assumptions, labelled): `cost = pv_kwp × 1.0 + battery_kwh × r`, with **r = 0.6** base (relative unit costs; no pesos) and r ∈ {0.3, 1.0} in sensitivity.
5. Score candidates with min-max normalized criteria; report a ranked table.

## DEC-002: Pareto frontier and recommendation (`src/ccis_sim/decision/sizing.py`)
1. **Candidates:** solar ∈ {50, 100, 150, 200} kWp × battery ∈ {0, 25, 50, 100, 150, 200} kWh (24 sizings) plus the 0/0 reference. 2019 weather, regimes normal and typhoon, both demand scales, **N = 50 seeds** (seeds 0..49, CRN). Then re-run only the top 5 by AHP (base weights, bottom-up) with 2016 weather, N = 50, as a robustness check.
2. Pareto frontier over (reliability ↑, cost ↓, self-sufficiency ↑) for each demand case; list the non-dominated sizings.
3. **Recommendation rule (state it in [D-38] before computing):** the cheapest non-dominated sizing whose mean Tier 1+2 outage-hours-served fraction is ≥ 0.90 in the typhoon regime under the bottom-up demand AND ≥ 0.80 under the bill-calibrated demand. If none qualifies, report the best achievable and say so. Do not move thresholds after seeing results.
4. Sensitivity: weights (3 sets), r (0.3/0.6/1.0), weather (2019/2016), demand case. Report whether the recommended sizing changes, and which sizings are "robust" (top-3 in at least 6 of the 8 combinations of weight set × demand case ... or state a simpler robust criterion).
5. Write `results/dec_candidates.csv`, `results/pareto_frontier.csv`, `results/recommendation.md` (tables with CIs).

## DEC-003.1/.2: Figures (matplotlib, `results/figures/*.png`, 150 dpi, readable axis labels and units)
1. Dispatch stacked area for 7 days (one in a typhoon outage window) for the recommended sizing: PV to load, battery discharge, grid import, unserved; with SoC on a secondary axis.
2. Battery SoC duration curve for the recommended sizing (normal vs typhoon).
3. Unserved T1+2 distribution (box or histogram) across seeds for 3 sizings: 100/50, the recommended, 200/200.
4. Pareto scatter (cost vs reliability, colour = self-sufficiency), recommended point marked, both demand cases as two panels.
5. Monthly demand: bottom-up vs mock bills (bars), so the 2.1× gap is visible.
Keep the code in `src/ccis_sim/decision/plots.py`; tests may only check that the files are created.

## Tests (`tests/test_decision.py`, fast)
AHP: a known 3×3 matrix with a known eigenvector, CR for a perfectly consistent matrix ≈ 0, and an inconsistent matrix raises; Pareto: a toy set with a known frontier; sizing rule: toy data where the cheapest qualifying sizing is unambiguous.

## Acceptance
- [ ] Verbatim `pytest -q` tail at start and end (no annotations). Report lists every touched file.
- [ ] [D-38] (AHP, criteria, cost assumptions, recommendation rule, solar=0 exclusion). Reserve [D-39] for anything that comes out of the figures or a late change; if unused, record "reserved, unused".
- [ ] `recommendation.md` states the recommended sizing under both demand cases with mean, std and P5/P95 of unserved T1+2 kWh and the fraction of outage hours served, and says whether the recommendation is **robust** or **demand-dependent**.

## Output
Standard template: branch `task/DEC-001`, gitignored patch, report `docs/reports/DEC-001-<agent>-decision.md`, update `status.md` (DEC-001, DEC-002, DEC-003.1, DEC-003.2; leave DEC-003.3 `open`), append [D-38], run `./scripts/validate-report.py`. Do not amend `master`; do not merge.
