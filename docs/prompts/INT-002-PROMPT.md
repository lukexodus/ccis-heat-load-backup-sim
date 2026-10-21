# TASK: INT-002: Scenario Grid and Monte Carlo Runner (deadline-compressed)

## Role & Worktree
- **Agent:** gemini (or claude-code). **Task ID:** INT-002. **Branch:** `./scripts/task-worktree.sh start INT-002` from the current tip of `master`.
- **Precondition (stop and report if false):** `src/ccis_sim/integration/engine.py` exists, `simulate()` runs, and INT-001 is `done`. **First run `pytest -q 2>&1 | tail -5` and paste the verbatim output**; the INT-001 report's pytest block was not trustworthy (it listed test files that do not exist).
- **Time-box:** the deadline is tonight. Skip stretch goals; if a subtask would take more than ~30 minutes, implement the simplest version, log the limitation, and move on. Total wall time for the full run must be under 40 minutes: use `multiprocessing`.
- Read: `AGENTS.md`, `docs/context/complete-context.md`, `docs/decisions/decision-log.md` (D-11, D-17, D-33 to D-35), `src/ccis_sim/integration/engine.py`.

## Context
Demand from DEM-001/002 is **189,356 kWh/yr** (EUI 75.7), about half of the mock bills (398,537 kWh/yr, EUI 159.4). The APC decision [D-36]: report BOTH. "bottom-up" (scale 1.0) is primary; "bill-calibrated" (one scale factor = bills_total / bottom-up_total ≈ 2.105) is a labelled sensitivity. Do not tune anything else.

## Deliverables
1. **`demand_scale: float = 1.0`** in `SimulationConfig` (validate > 0). Multiply the three tier demand arrays by it before the hourly loop. The default must reproduce INT-001 results bit-for-bit (test that). No other engine change.
2. **`src/ccis_sim/integration/scenarios.py`** with `run_grid(...)`, using `multiprocessing.Pool`, writing `results/scenario_grid.csv` (one row per run: solar_kwp, battery_kwh, weather_year, outage_regime, demand_scale, seed, grid_import_kwh, solar_gen_kwh, curtailed_kwh, unserved_t1/t2/t3_kwh, total_outage_hours, outage_hours_t1_served, outage_hours_t2_served, battery_cycles, self_sufficiency, peak_grid_kw).
   - **Main grid:** solar ∈ {0, 50, 100, 200} kWp × battery ∈ {0, 50, 100, 200} kWh × weather ∈ {2019, 2016} × outage ∈ {normal, typhoon} × seeds 0..29, `demand_scale` 1.0. Use the same seed for every sizing within a (weather, outage, seed) cell (common random numbers).
   - **Sensitivity grid:** same sizes, weather 2019 only, both regimes, 15 seeds, `demand_scale` = bill-calibrated (computed once from a grid-only run and recorded).
   - **+2 °C case:** `temp_offset_c = 2.0`, weather 2019, normal regime, 15 seeds, solar ∈ {0,100}, battery ∈ {0,100}.
3. **Convergence check (INT-002.2):** for the (100 kWp, 100 kWh, 2019, typhoon) cell, report mean and 95% CI of unserved Tier 1+2 kWh at N = 10, 20, 30 and state whether the CI half-width is < 10% of the mean (or note it is zero because the battery covers every outage).
4. **`results/mc_summary.csv`:** per (solar, battery, weather, outage, demand_scale) cell, mean/std/P5/P95 of unserved T1+2 kWh and of outage hours with Tier 1+2 fully served (as a fraction of outage hours).
5. **Tests (`tests/test_scenarios.py`)**: determinism of `run_grid` on a tiny grid (2 seeds); `demand_scale=1.0` equals INT-001 result; `demand_scale=2` doubles gross demand. Keep tests fast (under 30 s).
6. Decision **[D-36]**: demand-scale policy (primary vs sensitivity), grid definition, seed policy, convergence verdict.

## Acceptance
- [ ] Verbatim `pytest -q` tail pasted (start and end of the task). No annotations or edited lines.
- [ ] CSVs exist under `results/` (**gitignored is fine; also copy `mc_summary.csv` and a 30-row head of `scenario_grid.csv` into the report**).
- [ ] Report lists every touched file. Note any run that failed the harness (`verify=True`) and why.

## Output
Follow `docs/prompts/STANDALONE-PROMPT-TEMPLATE.md`: commit on `task/INT-002`, patch in `patch/` (gitignored), report `docs/reports/INT-002-<agent>-scenarios.md`, update `status.md`, append [D-36], run `./scripts/validate-report.py`. Do not amend `master`; do not merge.
