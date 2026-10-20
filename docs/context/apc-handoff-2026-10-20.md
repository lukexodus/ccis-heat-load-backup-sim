# APC Handoff — CCIS Heat, Load and Backup Power Simulation

Handoff #2 · Written 2026-10-20 (≈17:55 local) · Repo: `ccis-heat-load-backup-sim` · Bundle: profile `core`, commit `40b1909` (Phase 2 dispatch ready)

Save as `docs/context/apc-handoff-2026-10-20.md`. Paste this file as the first message of the new APC session, accompanied by the latest `docs/tasks/status.md`, `docs/decisions/decision-log.md`, `docs/context/complete-context.md`, and `docs/context/PHASE2-DISPATCH-PLAN.md` (or an `apc-bundle-core-*.tar.gz`).

---

## 1. Orientation (Copy verbatim into first prompt)

You are the APC AI ("Analyzer, Planner, Controller") for CCIS Heat, Load and Backup Power Simulation. You have NO filesystem access to the project repo. You coordinate by writing standalone prompts that lukexodus relays to local coding agents (Claude Code, Gemini CLI, opencode, Cursor) running on their machine, who DO have filesystem access and report back to you via pasted reports and git diffs.

Read, in this order, before taking any action:

1. `docs/context/complete-context.md` — full project orientation
2. `docs/decisions/decision-log.md` — every past decision and why ([D-01] through [D-26])
3. `docs/tasks/status.md` — live tracker of what is actually done right now
4. `docs/context/PHASE2-DISPATCH-PLAN.md` — Phase 2 execution order, reserved decision IDs, and dependencies
5. `docs/context/phase2-interface-contract.md` — Phase 2 data structures and signatures
6. This document's Sections 2–5 below — what changed in the ending session

If lukexodus has pasted current file contents or uploaded an APC bundle archive, inspect those primary artifacts directly before asking for re-pastes.

---

## 2. What Changed This Session

1. **Phase 1 Closeout Verified and Merged:**
   - **`task/CORE-005` (Baseline Smoke Simulation):** Merged into `master` ([`e97176a`](file:///home/lukexodus/projects/ccis-heat-load-backup-sim)). Produces 8,760-hour baseline run calibrated to 159.41 kWh/m²·yr EUI (398,525 kWh/yr), 124.44 kW peak, deterministic with negative controls. Logged `[D-23]`.
   - **`task/CORE-004.5` (Harness Gaps & Closeout Fixup):** Merged into `master` ([`a0dc967`](file:///home/lukexodus/projects/ccis-heat-load-backup-sim)). Closed all 5 harness audit gaps: SoC continuity check, non-finite guard, flow decomposition balance checks, signed residual export, and reconciles D-09/D-21/D-17. Logged disclosures `[D-24]` (calibration caveats) and `[D-25]` (harness enforcement rules).
   - Test suite after Phase 1: 107/107 passing.

2. **Phase 2 Infrastructure Implemented and Merged (`task/CORE-006`):**
   - Implemented `src/ccis_sim/core/interfaces.py` defining common contract classes:
     - `TieredDemand(tier1_kw, tier2_kw, tier3_kw, total_kw, hour, is_school_day)`
     - `OccupancySchedule(is_school_day, active_hours)`
     - `OutageSchedule(outage_hours, is_outage)`
     - `BatteryStepResult(charge_kw, discharge_kw, soc_kwh, soc_pct, unserved_kwh, curtailed_kwh, tare_loss_kwh)`
     - `ShedResult(served_tier1_kw, served_tier2_kw, served_tier3_kw, shed_kw)`
   - Created `docs/context/phase2-interface-contract.md` detailing contracts for DEM, SOL, BAT, and OUT modules.
   - Updated `Battery` model in `src/ccis_sim/core/models.py` with `self_discharge_pct_per_month = 2.0` and `tare_loss_kw = 0.0`.
   - Updated `validate_battery_boundaries` in `src/ccis_sim/core/verification.py` with idle-loss allowance:
     `max_loss = round(chg_eff * chg - dis / dis_eff - (self_discharge + tare), 6)`
     along with `SOC_CUMULATIVE_DRIFT` (tolerance ±0.01 kWh).
   - Added 13 interface unit tests in `tests/test_interfaces.py` and conservation idle-loss tests in `tests/test_conservation_checker.py`.
   - Decision `[D-26]` recorded.
   - Merged `task/CORE-006` into `master` at commit `40b1909`.
   - Full test suite: **120/120 passing (100% green)**.

3. **Repo and Worktree Hygiene:**
   - Completed tasks `CORE-004.5`, `CORE-005`, and `CORE-006` are verified and merged into `master`.
   - Worktrees for `CORE-004.5`, `CORE-005`, and `CORE-006` have been safely removed.
   - Local branches `task/CORE-004.5`, `task/CORE-005`, and `task/CORE-006` have been pruned.
   - `master` is clean and up to date.

---

## 3. What's Currently In-Flight (Active / Blocked)

- **None** — all Phase 1 tasks and prerequisite Phase 2 infrastructure (`CORE-006`) are settled and merged on `master`.
- The repository is completely clean and ready to dispatch the eight Phase 2 parallel track tasks.

---

## 4. What the New APC Instance Should Do First

1. **Confirm the 6 Phase 2 Confirmation Points** (see `docs/context/PHASE2-DISPATCH-PLAN.md` §Points for APC/operator confirmation):
   - Typhoon solar depression: 20–30% of normal GHI.
   - Tare loss: modelled as SoC-side loss.
   - Battery operational floor: `min_soc + emergency_reserve` (grid up), `min_soc` (outage), 0 (emergency drawdown).
   - 20% Tier 2 shed threshold kept separate from `emergency_reserve_pct`.
   - PR decomposition: explicit thermal derate in SOL-001; remainder budgeted against mean thermal factor in SOL-002.
   - Tier split: audit values ≈1.5 / 17 / 81 reported by OUT-002 without forcing D-10's 2 / 18 / 80.
2. **Dispatch Phase 2 Parallel Tasks**:
   - The eight standalone prompts are ready in `docs/prompts/`:
     - `DEM-001` (D-27): School calendar & occupancy schedules
     - `DEM-002` (D-28): Thermal-sensitive cooling load model
     - `SOL-001` (D-29): PV cell temperature & thermal derating
     - `SOL-002` (D-30): Fixed-tilt transposition & yield model
     - `BAT-001` (D-31): Outage duration distribution fitting
     - `BAT-002` (D-32): Battery dispatch & multi-day degradation
     - `OUT-001` (D-33): Synthetic outage generation & typhoon weather coupling
     - `OUT-002` (D-34): Critical load classification & tiered shedding
   - Tasks can be dispatched concurrently using dedicated worktrees via `./scripts/task-worktree.sh start <TASK-ID>`.

---

## 5. Unresolved Items & Edge Cases

- **Post-Merge Verification Tasks:**
  - `DEM-002.4` (validate combined demand against mock bills): requires `DEM-001` and `DEM-002` merged.
  - `SOL-002.4` (annual yield vs 1,298 kWh/kWp target): requires `SOL-001` and `SOL-002` merged.
  - Both remain marked `open` in `docs/tasks/status.md` and will be dispatched as verification prompts once their respective tracks land.
- **Decision ID Collision Prevention:**
  - Decision IDs D-27 through D-34 are strictly reserved one per track. When branches merge back to `master`, resolve conflicts by sorting entries strictly by ID number and preserving all rows.

---

## 6. Primary Content (Summary of Test Outputs)

```text
============================= test session starts ==============================
platform linux -- Python 3.14.8, pytest-9.1.1, pluggy-1.6.0
rootdir: /home/lukexodus/projects/ccis-heat-load-backup-sim
configfile: pyproject.toml
collected 120 items

tests/test_baseline_smoke.py ........                                    [  6%]
tests/test_conservation_checker.py .........................             [ 27%]
tests/test_domain_models.py ....................                         [ 44%]
tests/test_equipment_audit.py ...................                        [ 60%]
tests/test_interfaces.py .............                                   [ 70%]
tests/test_mock_bills.py ........                                        [ 77%]
tests/test_smoke.py ..........                                           [ 85%]
tests/test_weather_ingest.py ......................                     [100%]

============================= 120 passed in 11.05s =============================
```
