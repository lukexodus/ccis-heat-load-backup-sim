# TASK: INT-003: Verification, Plausibility and KPI Tables (deadline-compressed, parallel to INT-002)

## Role & Worktree
- **Agent:** a different agent from INT-002 if possible. **Task ID:** INT-003. **Branch:** `./scripts/task-worktree.sh start INT-003` from the current tip of `master`.
- **Precondition:** `engine.py` and INT-001 are done (stop and report otherwise). **First run `pytest -q 2>&1 | tail -5` and paste it verbatim.**
- **Time-box:** the deadline is tonight; skip stretch goals; 30-minute cap per subtask; simplest version + logged limitation.
- **Do not edit `engine.py`.** INT-002 adds `demand_scale` there; you must not conflict. You work in `src/ccis_sim/validation/` (new) and `tests/test_validation.py`.

## Framing (important, state it in the report)
The mock bills come from the same audit as the model, so this is **verification plus plausibility, not empirical validation**. Say so.

## Deliverables
1. **`validation/audit.py`:** `audit_run(config)` running `simulate(..., verify=True)` and returning: max |hourly residual|, cumulative residual, SoC min/max vs bounds, non-finite count, tier-conservation check (served + unserved = demand per tier, per hour). Run it for 8 configs: grid-only, PV-only 100, PV+battery 100/100, 200/200 × {2019 normal, 2019 typhoon, 2016 normal}. All must pass; list the 8 results in a table.
2. **Reproducibility:** same seed twice → identical hourly CSV hash; different seed → different outage schedule.
3. **Negative controls:** 3 deliberate breaks (a perturbed record with +1e-3 kWh residual, an SoC below `min_soc`, a NaN) must each be caught by `assert_simulation_valid`. (Reuse existing harness tests if present; cite them.)
4. **Plausibility table:** annual kWh, EUI, peak kW, load factor, monthly profile (12 values), weekday vs weekend vs vacation daily means. Compare against: mock bills (NMBE and CV(RMSE) monthly, with the caveat that bills are not independent; ASHRAE Guideline 14 thresholds are ±5% NMBE / 15% CV(RMSE) monthly), the placeholder baseline (D-23/D-24), and a published tropical university EUI range **only if you can cite it from `docs/` research files; otherwise write "no external benchmark checked"**. Solar: specific yield 1,508.74 kWh/kWp vs the 1,298 target (+16.24%): present the POA × PR reconciliation (1,945.98 × 0.77 ≈ 1,498) and state this is a resource-data gap, not a tuned number.
5. **One-at-a-time sensitivity** (2019, normal outages, 100 kWp / 100 kWh, seed 0): battery RTE (0.88/0.92/0.96), emergency reserve (0.10/0.20/0.50), tier-2 shed threshold (0.10/0.20/0.30), PR-driving BOS factor ±5% via the existing constant (monkeypatch in the test harness only, never edit source), cooling slope 3/4/5 %/°C if exposed. Report the change in grid import and in unserved T1+2 kWh. Skip any parameter that is not exposed without editing source and say so.
6. **`results/kpi_tables.md`** (and paste into the report): headline KPIs for the 4 reference cases (grid-only; PV 100; PV 100 + battery 100; PV 200 + battery 200) on 2019 normal seed 0: grid import, solar generation, curtailment, self-sufficiency, peak grid kW, outage hours served for Tier 1+2, unserved kWh per tier, battery cycles.
7. Decision **[D-37]** recording the framing, checks, and any failures.

## Acceptance
- [ ] Verbatim `pytest -q` tail at start and end. No annotations.
- [ ] Every audited config passes, or the failure is listed with a root cause. **Do not weaken tolerances to pass.**
- [ ] Report lists every touched file.

## Output
Template as usual: branch `task/INT-003`, gitignored patch, report `docs/reports/INT-003-<agent>-validation.md`, update `status.md`, append [D-37], run `./scripts/validate-report.py`. Do not amend `master`; do not merge.
