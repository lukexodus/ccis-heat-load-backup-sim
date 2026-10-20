# TASK: CORE-006 — Phase 2 Interface Contracts & Harness Idle-Loss Allowance

## Role & Worktree Instructions
- **Assigned Agent:** gemini
- **Task ID:** CORE-006 (new; must land on `master` **before** any Phase 2 track is dispatched)
- **Branch / Worktree:** `./scripts/task-worktree.sh start CORE-006`. Verify the branch base is the current tip of `master` (`git merge-base HEAD master`).
- **Depends on:** CORE-001 – CORE-005, CORE-004.5 (all `done`).
- **Blocks:** DEM-001, DEM-002, SOL-001, SOL-002, BAT-001, BAT-002, OUT-001, OUT-002.
- **Stop-and-report rule:** if the repo differs from what this prompt describes (a type already exists, a decision ID is taken), stop that step and report. Do not improvise.

## Orientation & Required Reading
1. `AGENTS.md`, `docs/context/complete-context.md`, `docs/tasks/status.md`
2. `docs/decisions/decision-log.md` (all; especially [D-07]–[D-11], [D-16]–[D-19], [D-21], [D-24], [D-25])
3. `docs/context/conceptual-model.md` §4 (`HourlyRecord` contract)
4. `src/ccis_sim/core/models.py` (`Building`, `SolarArray`, `Battery`, `OutageEvent`, `HourlyRecord`, `LoadTier`) and `src/ccis_sim/core/verification.py`, read directly
5. `src/ccis_sim/integration/baseline.py` (how weather columns and the audit are consumed today)
6. `docs/tasks/status.md` Phase 2 rows

## Why this task exists
Eight Phase 2 sub-models will be built **in parallel by separate agents** and later composed by INT-001. Unless the shared data shapes and function signatures are fixed first, they will diverge and integration will be rework. Separately, BAT-002.3 (self-discharge and tare loss) would break the [D-25] SoC-continuity invariant: 2%/month of a 100 kWh battery is about 0.0028 kWh/h, far above the 1e-5 kWh tolerance, so the harness must be taught about idle losses *before* BAT-002 is built.

## Scope

### Part 1 — Shared types: `src/ccis_sim/core/interfaces.py`
Frozen dataclasses (and `Protocol`s where noted), validated in `__post_init__` (equal lengths, finite, non-negative where physical). All hourly arrays are `numpy.ndarray`, length N (8,760 for an annual run), index i = hour i+1, units kWh per hour (= kW at Δt = 1 h).
- `TieredDemand(tier1_kwh, tier2_kwh, tier3_kwh)` with `gross_kwh` property and `at(i) -> tuple[float, float, float]`.
- `OccupancySchedule(occupancy_fraction, is_class_day, is_break, is_holiday)`: floats in [0, 1] and boolean arrays.
- `OutageSchedule(events: tuple[OutageEvent, ...], grid_available: ndarray[bool], year_type: Literal["normal", "typhoon"], ghi_multiplier: ndarray)`; `ghi_multiplier` defaults to ones.
- `BatteryStepResult(soc_kwh, charge_kwh, discharge_kwh, charge_curtailed_kwh, discharge_unmet_kwh)`: `charge_kwh`/`discharge_kwh` are **AC-side** flows achieved; `*_curtailed`/`*_unmet` are the shortfalls versus the request.
- `ShedResult(active_tier, served_kwh: tuple[float,float,float], unserved_kwh: tuple[float,float,float])`.
Reuse `LoadTier` and `OutageEvent` from `models.py`; do not redefine them.

### Part 2 — Contract document: `docs/context/phase2-interface-contract.md`
Write the contract below verbatim in spirit (you may tidy wording, not change signatures; if you think a signature is wrong, stop and report). Conventions for all tracks: pure functions, no file I/O inside models, no global RNG (stochastic functions take `rng: numpy.random.Generator`), no mutation of inputs, every function deterministic given inputs, weather frame columns exactly as `load_weather_fixture` returns them (verify: `hour, timestamp, t_amb, rh, ghi`).

| Track | Module | Signature |
| :-- | :-- | :-- |
| DEM-001 | `ccis_sim/demand/schedule.py` | `build_occupancy_schedule(timestamps: pd.Series, *, calendar: AcademicCalendar \| None = None) -> OccupancySchedule` |
| DEM-001 | `ccis_sim/demand/non_cooling.py` | `compute_non_cooling_demand(schedule: OccupancySchedule, audit: EquipmentAudit, building: Building) -> TieredDemand` |
| DEM-002 | `ccis_sim/demand/cooling.py` | `compute_cooling_demand(weather_df: pd.DataFrame, occupancy_fraction: ndarray, audit: EquipmentAudit, building: Building) -> TieredDemand` |
| SOL-001 | `ccis_sim/solar/irradiance.py` | `compute_dc_power_per_kwp(weather_df: pd.DataFrame, *, tilt_deg: float = 15.0, azimuth_deg: float = 180.0, latitude_deg: float = 18.06, longitude_deg: float = 120.56) -> ndarray` (kW DC per kWp, before BOS/inverter) |
| SOL-002 | `ccis_sim/solar/array.py` | `compute_ac_generation(dc_kw_per_kwp: ndarray, array: SolarArray) -> ndarray` (kWh AC per hour) |
| BAT-001 | `ccis_sim/battery/dynamics.py` | `step_battery(soc_kwh: float, battery: Battery, charge_request_kwh: float, discharge_request_kwh: float, *, soc_floor_kwh: float \| None = None, delta_t_hours: float = 1.0) -> BatteryStepResult` |
| BAT-002 | `ccis_sim/battery/reserve.py` | `soc_floor_kwh(battery: Battery, *, grid_available: bool, active_load_tier: LoadTier, allow_emergency_drawdown: bool = False) -> float` and `apply_idle_losses(soc_kwh: float, battery: Battery, delta_t_hours: float = 1.0) -> tuple[float, float]` (new SoC, loss kWh) |
| OUT-001 | `ccis_sim/outage/sampler.py` | `sample_outage_schedule(year_type: str, rng: Generator, *, n_hours: int = 8760) -> OutageSchedule` and `apply_ghi_multiplier(weather_df: pd.DataFrame, schedule: OutageSchedule) -> pd.DataFrame` |
| OUT-002 | `ccis_sim/outage/shedding.py` | `shed_for_hour(tier_demand_kwh: tuple[float,float,float], *, grid_available: bool, soc_kwh: float, battery: Battery, tier2_shed_soc_fraction: float = 0.20) -> ShedResult` and class `UnservedTracker` (per-tier unserved kWh and outage hours) |

Also document, in prose, the intended INT-001 hourly loop so track authors know how their piece is called: demand tiers → outage state → shed tier → solar → battery step (floor from `soc_floor_kwh`, idle losses applied) → grid import as residual → `HourlyRecord`.
Stated cross-track rules to include:
- Cooling and non-cooling demand are separate `TieredDemand`s; INT-001 sums them. Cooling takes `occupancy_fraction` as a plain array so DEM-002 does not depend on DEM-001's code.
- SOL-001 applies the explicit thermal derate; SOL-002 must **not** double-count temperature losses when applying the PR = 0.77 budget ([D-08]): SOL-002 decomposes PR into named factors and states which are already covered by SOL-001.
- The 20% low-SoC Tier 2 shedding threshold (OUT-002.3) is a separate parameter from `Battery.emergency_reserve_pct` ([D-17]); INT-001 decides whether they are linked.
- Idle losses are SoC-side only (see Part 3).

### Part 3 — Harness: idle-loss allowance and cumulative continuity drift
Reserved decision **[D-26]**. In `src/ccis_sim/core/verification.py`:
1. Read `Battery` for any existing self-discharge or tare attribute. If none exists, add `self_discharge_pct_per_month: float = 2.0` and `tare_loss_kw: float = 0.0` (validated, non-negative) and document both in [D-26]. Tare is modelled as a **SoC-side** standby loss (assumption; AC-side demand is unchanged); record that assumption.
2. Make SoC continuity **one-sided with an idle allowance**: `0 − tol ≤ expected_soc − actual_soc ≤ max_idle_loss_per_hour·Δt + tol`, where `max_idle_loss_per_hour` is derived from the battery's self-discharge (on current capacity) plus tare. SoC may never be *higher* than the ideal recursion. With zero idle parameters the behaviour must equal today's.
3. Add a **cumulative** continuity drift check (the same blind spot [D-21] closed for energy balance): total `expected − actual` over the run must not exceed the total allowed idle loss plus the [D-21]-style √N tolerance. New `ViolationType.SOC_CUMULATIVE_DRIFT`.
4. Tests: a series with correct idle losses passes; a series that loses SoC faster than allowed fails; SoC higher than the ideal recursion fails; a 0.9e-5 kWh/hr biased SoC series (zero idle allowance) passes hourly but trips the cumulative check; the existing golden scenario and all existing tests pass unchanged.

## What NOT to Touch
- No sub-model logic (no demand, solar, battery dynamics, outage or shedding implementations); only types, the contract doc and the harness change.
- No edits to existing decision-log entries or to `energy_balance_residual_kwh` / `is_energy_conserved()`.
- Do not change `HourlyRecord` fields.

## Verification & Acceptance Criteria
- [ ] `interfaces.py` types have validation tests (bad lengths, NaN, negatives rejected).
- [ ] Contract doc lists every signature above and the cross-track rules.
- [ ] Harness tests listed in Part 3 pass; existing suite unchanged and green (real `pytest -v` output pasted, new total stated).
- [ ] `./scripts/validate-report.py --all` passes; report lists **every** file touched.

## Reserved Decision IDs
**[D-26]** (idle-loss convention, tare assumption, one-sided continuity, cumulative continuity drift). If it is already used in the log, stop and report.

## Output & Reporting Instructions
Commit on the task branch (`feat(CORE-006): ...`, never amend or rewrite `master`); gitignored patch `patch/CORE-006-gemini-phase2-contracts.patch` via `git diff <base>..HEAD` (do not `git add -f`); report `docs/reports/CORE-006-gemini-phase2-contracts.md` per `TASK-TEMPLATE.md` with real command output; add CORE-006 rows to `docs/tasks/status.md`; append [D-26]; validate the report; run `./scripts/apc-bundle.sh core`. Report back with summary, test results, patch path, diff, branch and worktree path. Do not merge or delete the worktree.
