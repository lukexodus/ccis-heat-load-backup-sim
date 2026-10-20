# TASK: CORE-005 — Baseline Engine Smoke Test (Phase 1 Exit Gate)

## Role & Worktree Instructions
- **Assigned Agent:** gemini
- **Task ID:** CORE-005 (covers CORE-005.1 – CORE-005.3)
- **Branch / Worktree:** `./scripts/task-worktree.sh start CORE-005`
  (or `git worktree add ../ccis-heat-load-backup-sim-CORE-005 -b task/CORE-005`).
- **Depends on:** CORE-001, CORE-002, CORE-003, CORE-004 (all `done` at commit `52a64f2`).
- **Blocks:** Phase 2 (DEM / SOL / BAT / OUT tracks).

## Orientation & Required Reading
Read in this order before writing code:
1. `AGENTS.md` and `docs/context/complete-context.md`
2. `docs/tasks/status.md` — confirm CORE-005 / .1–.3 are `open`
3. `docs/decisions/decision-log.md` — especially [D-05], [D-16], [D-19], [D-20], [D-21]
4. `docs/context/conceptual-model.md` §4 (energy-balance invariant) and the `HourlyRecord` field contract
5. `src/ccis_sim/core/models.py` — read `HourlyRecord`, `Building`, `Battery` directly; do not rely on this prompt's description of them
6. `src/ccis_sim/core/verification.py` and `tests/fixtures/README.md` — the harness you must run the baseline through
7. `src/ccis_sim/weather/loader.py`, `data/fixtures/batac-weather-hourly-2019.csv` (baseline year) and `…-2016.csv` (hot year)
8. `data/fixtures/equipment-audit-ccis.csv` and `data/fixtures/synthetic-mock-bills-ccis.csv` (+ their loaders from CORE-003)

## Context & Objectives
This is the Phase 1 exit gate: prove that the foundation (domain models, weather fixtures, equipment audit, verification harness) works end to end *before* four Phase 2 tracks fan out on top of it. Build the smallest possible grid-only simulation (no solar, no battery, no outages), emit a full 8,760-hour `HourlyRecord` series, and run it through the CORE-004 harness.

The demand profile here is a **deliberately simple placeholder**. The real demand models are DEM-001 (schedule/base load) and DEM-002 (temperature/humidity cooling response) and are *not* in scope. Do not pre-empt their design: no academic-calendar engine, no psychrometric latent multiplier, no inverter duty-cycle modelling. Keep the placeholder clearly isolated (one function/module) so DEM-001/002 can replace it without touching the simulation loop.

## Specific Scope & Deliverables

### CORE-005.1 — Grid-only, zero-solar, zero-battery simulation
- New module (suggested `src/ccis_sim/integration/baseline.py`; layout is your call, document it).
- Inputs: the 2019 hourly weather fixture, the equipment audit, a `Building`.
- Placeholder demand: connected load from the audit × a documented hour-of-day / weekday-weekend occupancy profile, plus a simple temperature-driven cooling term. Calibrate once so annual energy lands within the 150–300 kWh/m²·yr EUI band and near the CORE-003 mock-bill annual total (159.41 kWh/m²·yr). State the calibration target and tolerance explicitly.
- Dispatch: `grid_import_kwh = demand_gross_kwh = demand_served_kwh`; `solar_*`, `battery_*`, `unserved_load_kwh` all 0; `grid_available = True`; `active_load_tier = 3`.
- Output: exactly 8,760 `HourlyRecord`s, `hour` numbered 1–8760, timestamps in the same `+08:00` convention as the weather fixture and the CORE-004 golden scenario.
- Deterministic: same inputs → identical records.

### CORE-005.2 — Run through the energy-balance harness
- Run the 8,760 records through `run_verification_harness` / `assert_simulation_valid` and assert a clean report (zero hourly violations, cumulative drift within the [D-21] tolerance).
- State and justify how you handle the battery argument for a zero-battery run (`battery=None` vs. a zero-capacity `Battery`).
- Add a **negative control**: a test that copies the baseline, injects a leak (e.g. a constant per-hour bias and a single-hour mismatch), and proves the harness fails on it. A smoke test that cannot fail proves nothing.

### CORE-005.3 — Baseline summary metrics
- Produce and test: annual kWh, peak kW and its timestamp, base EUI (kWh/m²·yr using the `Building` floor area), monthly kWh, load factor.
- Run the 2016 hot-year fixture as a sensitivity case; report the delta in annual kWh and peak kW versus 2019 (do not tune the model to either year).
- Commit the 2019 headline numbers as expected values in a test (with an explicit tolerance) so later tracks can detect accidental baseline drift.

### Tests
- `tests/test_baseline_smoke.py` (or similar): record count and hour numbering, determinism, harness pass, negative control, metrics within calibration band, 2016 > 2019 peak sanity check.
- Run the full `pytest -v` and paste the real output into the report.

### What NOT to Touch
- `src/ccis_sim/core/models.py` and `src/ccis_sim/core/verification.py`: reuse as-is. If you believe either has a bug, stop and report it specifically rather than working around it.
- No solar, battery dispatch, outage, shedding, Monte Carlo, CLI or plotting work.
- No changes to weather fixtures, the equipment audit, or existing decision-log entries.
- Do not extend the verification harness. Gaps you notice in it (e.g. no hour-to-hour SoC continuity check, no NaN/inf handling in the battery checks) go in your report under "Flagged for APC", not into code.

## Verification & Acceptance Criteria
- [ ] 8,760 records, hour 1–8760, passes the CORE-004 harness with zero violations.
- [ ] Negative control demonstrably fails the harness.
- [ ] Baseline EUI inside 150–300 kWh/m²·yr and within your stated tolerance of 159.41.
- [ ] Full `pytest` suite green (currently 91 tests; report the real new total).
- [ ] `./scripts/validate-report.py --all` passes.
- [ ] Every file you touched is listed in the report's "Changes Made" section, including fixtures, README or doc edits.

## Reserved Decision IDs
- **[D-22]**: placeholder baseline demand method and calibration target (what it is, why it is acceptable as a stand-in, and that DEM-001/002 supersede it). Record in `docs/decisions/decision-log.md`.
- If another non-trivial choice arises, report it instead of silently deciding.

## Output & Reporting Instructions
1. **Commit** on your task branch: `git commit -m "feat(CORE-005): <description>"`. Do not amend or rewrite commits already on `master`.
2. **Patch file:** generate `patch/CORE-005-gemini-baseline-smoke-test.patch` with `git diff HEAD~1`. `patch/*.patch` is gitignored: do **not** `git add -f` it, and do not commit it.
3. **Report:** `docs/reports/CORE-005-gemini-baseline-smoke-test.md` per `docs/reports/TASK-TEMPLATE.md`, with real command output.
4. **Status:** update `docs/tasks/status.md` rows for CORE-005 and .1–.3 (`done` or `needs-review`), linking the report.
5. **Decision log:** append [D-22].
6. **Validate:** `./scripts/validate-report.py docs/reports/CORE-005-gemini-baseline-smoke-test.md`.
7. **Bundle:** run `./scripts/apc-bundle.sh core` since decision log and status changed.
8. **Report back:** executive summary, test results, patch path, the unified diff, branch name and worktree path. Do not merge or delete the worktree.
