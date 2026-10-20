# STANDALONE PROMPT — CORE-004: Shared Test Harness & Energy Balance Invariant Checker

**Task ID:** CORE-004 (covers CORE-004.1 – CORE-004.3)
**Phase:** 1 — Core Infrastructure & Data Pipelines
**Reserved Decision ID:** [D-21] (only if you need to fix a tolerance or
methodology choice not already locked — see CORE-004.1's note on the
existing `HourlyRecord.is_energy_conserved()` method)
**Depends on:** CORE-001 (done — `Battery`, `HourlyRecord`,
`is_energy_conserved()` already exist in `src/ccis_sim/core/models.py`)
**Blocks:** CORE-005 (baseline smoke test needs this harness to validate
against)

**Can run in parallel with:** `CORE-002-VERIFY-AND-LAND` if that's still
in flight — this task does not touch `src/ccis_sim/weather/` or
`data/fixtures/weather*`. Follow `AGENTS.md`'s worktree rules for shared
docs regardless.

---

## Before you start

1. Read `AGENTS.md` and `docs/context/complete-context.md` if you have not
   this session.
2. Read `docs/context/conceptual-model.md` §4 (the canonical energy balance
   invariant: residual ≤ 10⁻⁵ kWh).
3. **Read `src/ccis_sim/core/models.py` directly before writing anything.**
   This is important: `CORE-001` already implemented
   `HourlyRecord.energy_balance_residual_kwh` (a property) and
   `HourlyRecord.is_energy_conserved(tolerance=1e-5)` (a method) — a
   single-record conservation check already exists. Do not reimplement
   this from scratch as if it doesn't exist. Your job is to build the
   **shared harness** that applies this check (and the battery boundary
   checks, which don't yet exist) across a full simulation run — i.e.
   thousands of `HourlyRecord`s at once — with good failure reporting, not
   to redefine what "conserved" means for one record.
4. Also read `Battery`'s properties in the same file
   (`min_soc_kwh`, `max_soc_kwh`, `usable_capacity_kwh`,
   `max_charge_power_kw`, `max_discharge_power_kw`, and the
   `emergency_reserve_pct`/`emergency_reserve_kwh` pair locked under
   [D-17]) — your boundary validator checks a time series of SoC values
   against these, it doesn't redefine the battery's limits.

## Objective

Build the shared verification infrastructure that every later simulation
run (CORE-005's baseline, and eventually the full Monte Carlo engine in
INT-002) will be checked against. This is explicitly called out in
`docs/context/complete-context.md` as a "critical test gate" — get the
failure modes and reporting right, because a silent false-pass here would
let a broken simulation look correct all the way through Phase 3's V&V
suite (INT-003).

## Scope

### CORE-004.1 — Strict energy conservation checker across a time series
- Build a function/class that takes a **sequence** of `HourlyRecord`s (e.g.
  a full 8,760-hour annual run, or any sub-range) and:
  - Calls each record's own `is_energy_conserved()` and aggregates
    failures — don't recompute the residual formula independently; reuse
    `HourlyRecord.energy_balance_residual_kwh` so there's exactly one
    definition of "residual" in the codebase.
  - Reports **which specific hours** failed and by how much (not just a
    pass/fail boolean for the whole run) — this is what makes the harness
    actually useful for debugging a broken sub-model later.
  - Additionally checks **cumulative** conservation across the whole run
    (sum of all residuals, not just whether each individual hour passed
    its own tolerance) — a model that's consistently off by a tiny biased
    amount every hour could pass every individual-hour check yet drift
    significantly over 8,760 hours. Decide a reasonable cumulative
    tolerance (e.g. scaling the per-hour 10⁻⁵ kWh tolerance by
    √8760 for a random-walk-style bound, or a simple fixed multiple — your
    call, but state your reasoning for whichever you pick) and record it as
    **[D-21]** since it's a real methodological choice not already in the
    decision log.

### CORE-004.2 — Battery boundary validator
- Build a function/class that takes a sequence of `HourlyRecord`s (which
  carry `battery_soc_kwh`) plus the `Battery` instance that produced them,
  and validates:
  - `0 ≤ battery_soc_kwh ≤ Battery.capacity_kwh` for every hour (hard
    physical bound — SoC can never be negative or exceed nameplate
    capacity).
  - `battery_soc_kwh ≥ Battery.min_soc_kwh` for every hour **except**
    during active, validly-flagged emergency conditions (define what
    counts as "validly-flagged" — likely tied to `active_load_tier` or
    `grid_available` — your call, document it) — since [D-09]'s 10%
    min-SoC floor is meant to be a hard protection floor, not merely a
    soft target.
  - C-rate limits: hour-over-hour `battery_charge_kwh` and
    `battery_discharge_kwh` don't exceed `Battery.max_charge_power_kw` /
    `Battery.max_discharge_power_kw` (remember these are power limits in
    kW; over a 1-hour timestep, kWh and kW are numerically equal, but make
    the unit handling explicit in your code/docstring so a future hourly-
    vs-subhourly change doesn't silently break this).
  - Flag (don't necessarily hard-fail, your call, but at least flag)
    simultaneous nonzero `battery_charge_kwh` AND `battery_discharge_kwh`
    in the same hour — this is listed as its own boundary condition
    worth guarding against in `docs/tasks/status.md`'s `BAT-001.4`
    ("Write unit tests for simultaneous charge/discharge prevention"), and
    your shared harness is a natural place to catch it generically before
    BAT-001 exists yet to prevent it at the source.

### CORE-004.3 — Shared golden fixture runner
- Build a small, reusable test utility that lets later sub-model tasks
  (DEM-001/002, SOL-001/002, BAT-001/002, OUT-001/002) validate their
  output against a shared "golden" reference scenario without each
  reinventing fixture-loading and assertion boilerplate. Concretely:
  - A way to construct a minimal but complete sequence of `HourlyRecord`s
    for a short synthetic scenario (e.g. 24–48 hours) with hand-computed,
    known-correct expected values for at least one full energy-balance
    cycle (solar generation → demand → battery charge → battery discharge
    → grid import, hitting zero, positive, and negative net-load hours).
  - Wire this fixture through both the CORE-004.1 and CORE-004.2 checkers
    as a self-test — i.e. this harness should validate itself against data
    it knows is correct, not just be a bag of assertion helpers with no
    reference case.
  - Document (in a docstring or a short `tests/fixtures/README.md`) how a
    later task should use this golden fixture: what the expected
    import/call pattern looks like, so DEM-001 or SOL-001's own test
    suites can import and reuse it rather than copy-pasting fixture
    construction logic.

### Tests
- `tests/test_conservation_checker.py` (or similar) covering:
  - a fully-conserved time series passes,
  - a deliberately broken record (residual > tolerance) is caught and
    correctly reported with its hour number,
  - the cumulative-drift check catches a small-but-consistent bias that
    individual-hour checks would miss (construct a synthetic series where
    every hour has, say, a 0.9×10⁻⁵ kWh residual — each hour individually
    passes, but the sum across 8,760 hours should trip your cumulative
    check; if your chosen cumulative tolerance wouldn't catch this
    specific case, that's fine, but say so explicitly and justify why — don't
    silently pick a cumulative tolerance so loose it can never fire).
  - battery boundary violations (SoC below floor outside emergency, SoC
    above capacity, C-rate exceeded, simultaneous charge+discharge) are
    each individually caught by a dedicated test case.
- Run `pytest -v` (the full suite) and include actual output in your
  report.

## Deliverable

- New module(s) under `src/ccis_sim/core/` (e.g.
  `src/ccis_sim/core/conservation.py`, `src/ccis_sim/core/boundaries.py`,
  or a single `src/ccis_sim/core/verification.py` — your call on file
  layout, document it in your report) implementing CORE-004.1–.3.
- `tests/test_conservation_checker.py` and any companion test files, green
  under `pytest -v`.
- Report at `docs/reports/CORE-004-<agent-name>-conservation-harness.md`
  with the real `pytest -v` output and your reasoning for the cumulative-
  tolerance choice.
- Update `docs/tasks/status.md`: CORE-004 and CORE-004.1–.3 rows.
- Record **[D-21]** in `docs/decisions/decision-log.md` for the cumulative
  conservation tolerance methodology.
- Run `./scripts/validate-report.py` before handoff.

## Explicit non-goals

- No simulation engine, no CLI, no actual dispatch logic — this task
  builds the *checker*, not anything that produces `HourlyRecord`s to
  check. CORE-005 is what will first exercise this harness against a real
  (if minimal) simulation.
- Do not modify `HourlyRecord.is_energy_conserved()` or
  `energy_balance_residual_kwh` in `models.py` — reuse them as-is. If you
  believe the existing per-hour formula itself has a bug, stop and report
  that specifically rather than silently working around it in your harness.
