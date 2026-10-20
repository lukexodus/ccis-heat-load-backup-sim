# TASK: INT-001: Simulation Engine, CLI Driver and Combined Verify (DEM-002.4 + SOL-002.4)

## Role & Worktree Instructions
- **Assigned Agent:** gemini (or claude-code)
- **Task ID:** INT-001 (covers INT-001.1 to INT-001.4, plus the deferred DEM-002.4 and SOL-002.4 in `docs/tasks/status.md`)
- **Branch / Worktree:** `./scripts/task-worktree.sh start INT-001`, branched from the current tip of `master`.
- **Precondition check (do this first):** confirm that DEM-001, DEM-002, SOL-001, SOL-002, BAT-001, BAT-002, OUT-001 and OUT-002 are all `done` in `docs/tasks/status.md` and that their modules exist: `demand/schedule.py`, `demand/non_cooling.py`, `demand/cooling.py`, `solar/irradiance.py`, `solar/array.py`, `battery/dynamics.py`, `battery/reserve.py`, `outage/sampler.py`, `outage/shedding.py`. **If any is missing, stop and report which. Do not stub it yourself.**
- **Stop-and-report rule:** if a signature on disk differs from `docs/context/phase2-interface-contract.md`, stop that step and report. Do not silently adapt.
- **Time-box:** the deadline is tight. Skip stretch goals; if a subtask would take more than ~45 minutes, implement the simplest version, log it as a limitation in the report, and move on.

## Orientation & Required Reading
1. `AGENTS.md`, `docs/context/complete-context.md`
2. `docs/tasks/status.md`, `docs/decisions/decision-log.md` (all entries, including D-26 to D-34)
3. `docs/context/phase2-interface-contract.md` (§ hourly dispatch sequence) and `src/ccis_sim/core/interfaces.py`
4. `src/ccis_sim/core/models.py`, `core/verification.py`, `integration/baseline.py` (the existing placeholder baseline and `HourlyRecord` conventions)

## Context & Objectives
Wire the Phase 2 components into one deterministic hourly engine and a `ccis-sim` CLI, then run the two deferred cross-checks. INT-002 (Monte Carlo) and INT-003 (V&V) are built on this engine tomorrow, so keep the engine a pure function of (config, weather, seed) with no global state.

## Scope & Deliverables
### INT-001.1: Engine (`src/ccis_sim/integration/engine.py`)
- `simulate(config, weather_df, seed) -> SimulationResult` (hourly `HourlyRecord`s plus summary).
- Follow the contract's eight-step hourly sequence exactly: tiered demand (DEM-001/002) → grid status (OUT-001) → shedding (OUT-002) → solar (SOL-001/002, with the typhoon GHI multiplier from OUT-001 applied to the weather before solar) → bus dispatch and battery step (BAT-001) with the floor from `soc_floor_kwh` (BAT-002) → `apply_idle_losses` → grid import or unserved load → `HourlyRecord`.
- The 20% Tier 2 shed threshold and `Battery.emergency_reserve_pct` stay separate parameters ([D-34]); expose both in config and note the relationship in [D-35].
- Config supports: solar kWp (0 to 200), battery kWh (0 to 200), weather year (2019 or 2016) plus a `temp_offset_c` (for +2 °C), outage regime (`normal` or `typhoon`), and seed.
- Every run must pass `assert_simulation_valid` (the harness). Zero-solar, zero-battery must reproduce a grid-only run.

### INT-001.2: CLI (`ccis-sim`, entry point in `pyproject.toml`)
- `ccis-sim run --solar-kwp 100 --battery-kwh 200 --weather 2019 --outages normal --seed 1 --out results/`
- Prints a summary table and writes the outputs from INT-001.3.

### INT-001.3: Exporters
- Hourly CSV, daily CSV, and an annual summary JSON: grid import, solar generation, curtailment, battery throughput, unserved kWh per tier, outage hours, self-sufficiency, EUI, peak kW, solar specific yield (kWh/kWp).

### INT-001.4: Tests (`tests/test_engine.py`)
- Grid-only case equals the baseline path within tolerance; harness passes; same seed gives byte-identical output, different seed differs; a forced 12 h outage with a full battery serves Tier 1 and 2 and sheds Tier 3; energy balance residual at or below 1e-5 per hour.

### DEM-002.4 (combined verify)
- Run combined DEM-001+002 demand against the mock bills. Report annual kWh, EUI, peak kW and the percentage difference from the **uncalibrated** placeholder (324,379.71 kWh, EUI 129.75, peak 101.29 kW) and from the bills. Do not tune silently: report first, and any calibration multiplier goes in [D-35] with the number.

### SOL-002.4 (combined verify)
- Annual specific yield for 2019 weather versus the 1,298 kWh/kWp target, and the implied mean thermal factor versus the assumed one in SOL-002. If the yield is outside 1,200 to 1,600, or off target by more than 5%, recalibrate the **single** assumed thermal factor in SOL-002 (not PR 0.77 itself), re-run, and record before/after numbers.

### What NOT to touch
- Contract signatures, the harness API, Phase 2 module internals except the single SOL-002 thermal factor above. Do not build the Monte Carlo runner or V&V suite.

## Verification & Acceptance Criteria
- [ ] `pytest` passes in full; paste the **verbatim** output (tail with per-file counts from `pytest --collect-only -q`).
- [ ] `ccis-sim run` produces a valid result for: grid-only; 100 kWp PV only; 100 kWp + 200 kWh; and the typhoon outage regime.
- [ ] Both combined-verify numbers reported with the before/after of any calibration.
- [ ] Report lists every touched file.

## Reserved Decision IDs
- **[D-35]**: engine design, config surface, any calibration applied, relationship of the 20% shed threshold to `emergency_reserve_pct`. If other IDs through D-34 are unused when you branch, ignore them; do not renumber.

## Output & Reporting Instructions
Follow `docs/prompts/STANDALONE-PROMPT-TEMPLATE.md`: commit on `task/INT-001`, patch to `patch/INT-001-<agent>-engine.patch` (gitignored, never `git add -f`), report `docs/reports/INT-001-<agent>-engine.md`, update `status.md`, append [D-35], run `./scripts/validate-report.py`, do not amend `master`, do not merge.
