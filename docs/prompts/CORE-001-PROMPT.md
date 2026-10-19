# STANDALONE PROMPT — CORE-001: Canonical Domain Models & Interface Contracts

**Task ID:** CORE-001 (covers CORE-001.1 – CORE-001.4)
**Phase:** 1 — Core Infrastructure & Data Pipelines
**Reserved Decision IDs:** [D-12], [D-13] (reserve these only if you must make
a new architectural choice not already covered by [D-05]–[D-11]; if nothing
new arises, do not invent a use for them — leave them unused and say so)
**Depends on:** ARCH-001 (done), ARCH-002 (done — see note below)
**Blocks:** CORE-004 (test harness needs these dataclasses to validate against)

---

## Before you start

1. Read `AGENTS.md` and `docs/context/complete-context.md` in full if you
   have not this session.
2. Read `docs/context/conceptual-model.md` — this is the canonical spec for
   everything you're about to implement. Do not re-derive the `HourlyRecord`
   schema from the task report prose; read it from that file directly.
3. Read `docs/decisions/decision-log.md`, specifically [D-05] through [D-11].
4. **Known gap:** `docs/tasks/status.md` currently (possibly) shows
   `ARCH-002.4` as `done`, crediting a `docs/context/research-synthesis.md`
   file that may not exist yet (a separate fix-up task,
   `ARCH-002.4-FIXUP`, addresses this). This does not block you — none of
   your subtasks depend on that file — but if you notice it's still absent,
   do not silently assume it exists; note it in your report per `AGENTS.md`'s
   "verify it" rule.
5. Confirm `src/ccis_sim/core/__init__.py` exists and is currently just a
   docstring stub (no implementation yet). If you find it already contains
   dataclasses, stop and report the conflict rather than overwriting.

## Objective

Implement the canonical, immutable domain model layer in `src/ccis_sim/core/`
that every other subpackage (`demand`, `solar`, `battery`, `outage`,
`integration`, `decision`) will import and depend on. This is the single
most load-bearing interface contract in the project — get the field names,
types, and immutability right the first time, because every parallel-track
task in Phase 2 (DEM/SOL/BAT/OUT) will be written against this exact
contract and cannot be re-negotiated cheaply later.

## Scope

### CORE-001.1 — `Building`, `SolarArray`, `Battery` dataclasses
- `@dataclass(frozen=True)` for all three (immutability is a project-wide
  convention established in ARCH-001 — see `HourlyRecord`'s own
  `frozen=True` in `conceptual-model.md` §4).
- `Building`: encode the 18-room archetype locked in [D-06] — floor area
  (~2,500 m²), room inventory (counts per room type), and whatever
  equipment-load parameterization CORE-003 will need to consume (don't
  hard-code equipment wattages here if that's CORE-003's job — check
  `status.md`'s CORE-003 scope before deciding the boundary; if ambiguous,
  put the static building shell here and leave equipment loading to
  CORE-003, noting that boundary call in your report).
- `SolarArray`: capacity (kWp), tilt (15° per [D-08]), PR (0.77 default per
  [D-08]), temperature coefficient (-0.40%/°C), NOCT parameters. Should be
  constructible at 0/50/100/200 kWp per the roadmap's scenario matrix
  (`complete-context.md` §2) without needing a new class per size.
- `Battery`: capacity (kWh), RTE (92% per [D-09]), usable DoD (90%), min SoC
  reserve (10%), C-rate limits (0.5C charge / 1.0C discharge per
  `status.md`'s BAT-001.3). Do not implement dispatch *logic* here — that's
  BAT-001/BAT-002's job in Phase 2. This dataclass holds static parameters
  and current state (SoC), not behavior.

### CORE-001.2 — `OutageEvent` and `HourlyRecord`
- `OutageEvent`: start hour, duration, type (normal vs. typhoon per [D-11]),
  and whatever solar-depression coupling field typhoon outages need (see
  [D-11]'s "3–5 consecutive days of depressed solar irradiance" clause).
- `HourlyRecord`: **copy the field list verbatim from
  `conceptual-model.md` §4** (`hour`, `timestamp`, `temp_ambient_c`,
  `humidity_rel_pct`, `ghi_w_m2`, `demand_gross_kwh`, `demand_served_kwh`,
  `solar_generation_kwh`, `solar_to_demand_kwh`, `solar_to_battery_kwh`,
  `solar_curtailed_kwh`, `battery_soc_kwh`, `battery_charge_kwh`,
  `battery_discharge_kwh`, `grid_import_kwh`, `unserved_load_kwh`,
  `grid_available`, `active_load_tier`). Do not add, rename, or drop fields
  without reserving a new decision ID and recording why — this schema is
  explicitly called "canonical" and "locked" in ARCH-001.
- `frozen=True` on both.

### CORE-001.3 — CSV/dict serialization protocols
- A `to_dict()` / `from_dict()` (or equivalent) pair for `HourlyRecord` at
  minimum, since the simulation engine (INT-001) will need to export 8,760
  rows/year to CSV for the Monte Carlo runner and report plotting (DOC-001).
- Keep it dependency-light — plain dict/CSV round-tripping, not a bespoke
  ORM. pandas is already a project dependency if you want
  `DataFrame`-friendly output, but don't introduce a new dependency.

### CORE-001.4 — Unit tests
- New test file(s) under `tests/` (e.g. `tests/test_core_models.py`),
  not appended to `tests/test_smoke.py`.
- Cover: immutability (attempting to mutate a frozen dataclass raises),
  the energy conservation invariant check as a *property of HourlyRecord*
  if you choose to implement a validator here (note: the dedicated
  conservation **checker** is explicitly CORE-004's job per `status.md` —
  if you build a one-off assertion here for your own tests, make clear
  in your report that it's test-local scaffolding, not the shared checker
  CORE-004 will build, to avoid duplicate/competing implementations later).
- Cover boundary values: SoC at 0% and 100%, zero-capacity solar array,
  zero-capacity battery (the "baseline" configuration CORE-005 needs).
- Run `pytest -v` and include the full output in your report.

## Explicit non-goals for this task

- No dispatch logic, no weather ingestion, no CLI, no Monte Carlo. Those are
  later tasks (BAT-001, CORE-002, INT-001, INT-002 respectively). If you
  find yourself writing a charge/discharge loop, stop — that's scope creep
  into BAT-001/BAT-002.
- Do not touch `docs/context/research-synthesis.md` — unrelated task.

## Deliverable

- Updated `src/ccis_sim/core/__init__.py` (or submodules under
  `src/ccis_sim/core/` if you split dataclasses into separate files —
  your call, document the layout choice in your report).
- `tests/test_core_models.py` (or similar), green under `pytest -v`.
- Report at `docs/reports/CORE-001-<agent-name>-domain-models.md` per the
  standard `AGENTS.md` format, including the full unified diff.
- Update `docs/tasks/status.md`: CORE-001 and CORE-001.1–.4 rows.
- Record any new decisions under reserved IDs [D-12]/[D-13] in
  `docs/decisions/decision-log.md` **only if genuinely needed** — if the
  existing [D-05]–[D-11] already cover every choice you had to make, leave
  the reserved IDs unused and say so explicitly in your report (per
  `AGENTS.md`: "If a reserved ID is already used in the file, stop and
  report the conflict; do not renumber unilaterally" — the inverse also
  holds: don't force a decision entry where none is needed just because an
  ID was reserved).
- Run `./scripts/validate-report.py` before handoff.
