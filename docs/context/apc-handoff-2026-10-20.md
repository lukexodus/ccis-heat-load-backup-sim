# APC Handoff — CCIS Heat, Load and Backup Power Simulation

Handoff #2 · Written 2026-10-20 (≈18:10 local) · Repo: `ccis-heat-load-backup-sim` · Bundle: profile `core`, tip commit `e1f6a81` (CORE-006 merged into `master` at `40b1909`)

Save as `docs/context/apc-handoff-2026-10-20.md`. Paste this file as the first message of the new APC session, accompanied by `docs/tasks/status.md`, `docs/decisions/decision-log.md`, `docs/context/complete-context.md`, `docs/context/PHASE2-DISPATCH-PLAN.md`, and `docs/context/phase2-interface-contract.md` (or an `apc-bundle-core-*.tar.gz`).

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
   - **`task/CORE-004.5` (Harness Gaps & Closeout Fixup):** Merged into `master` ([`a0dc967`](file:///home/lukexodus/projects/ccis-heat-load-backup-sim)). Closed all 5 harness audit gaps: SoC continuity check, non-finite guard, flow decomposition balance checks, signed residual export, and reconciled D-09/D-21/D-17. Logged disclosures `[D-24]` (calibration caveats) and `[D-25]` (harness enforcement rules).

2. **Phase 2 Infrastructure Implemented and Merged (`task/CORE-006`):**
   - Implemented `src/ccis_sim/core/interfaces.py` defining canonical frozen dataclasses with numpy array time series:
     - `TieredDemand(tier1_kwh, tier2_kwh, tier3_kwh)` with `gross_kwh` property and `at(i)` indexing method.
     - `OccupancySchedule(occupancy_fraction, is_class_day, is_break, is_holiday)` with float bounds $[0.0, 1.0]$ and boolean flags.
     - `OutageSchedule(events, grid_available, year_type, ghi_multiplier)` with default unit solar multipliers and regime validation.
     - `BatteryStepResult(charge_kwh, discharge_kwh, soc_kwh, charge_curtailed_kwh, discharge_unmet_kwh)` representing AC-side achieved flows and chemical SoC.
     - `ShedResult(active_tier, served_kwh, unserved_kwh)` capturing per-tier served and unserved allocations under load shedding.
   - Created `docs/context/phase2-interface-contract.md` detailing contracts for DEM, SOL, BAT, and OUT modules.
   - Updated `Battery` model in `src/ccis_sim/core/models.py` with `self_discharge_pct_per_month = 2.0` and `tare_loss_kw = 0.0`.
   - Updated `validate_battery_boundaries` in `src/ccis_sim/core/verification.py` with idle-loss allowance:
     `max_loss = round(chg_eff * chg - dis / dis_eff - (self_discharge + tare), 6)`
     along with `SOC_CUMULATIVE_DRIFT` (tolerance ±0.01 kWh).
   - Added 9 unit tests in `tests/test_interfaces.py` and 4 idle-loss tests in `tests/test_conservation_checker.py`.
   - Decision `[D-26]` recorded.
   - Merged `task/CORE-006` (commit `a7aaacd`, based on `a0dc967`) into `master` at commit `40b1909`.
   - Full test suite: **120/120 passing (100% green)**.

3. **Repo and Worktree Hygiene:**
   - Completed tasks `CORE-004.5`, `CORE-005`, and `CORE-006` are verified and merged into `master`.
   - Dedicated task worktrees (`CORE-004.5`, `CORE-005`, `CORE-006`) safely pruned via `./scripts/task-worktree.sh remove`.
   - Task branches pruned; `patch/CORE-006-gemini-phase2-contracts.patch` preserved in `patch/`.
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
- **Harness Fixup Queue (Carried-over nits):**
  - Idle-allowance blind spot: cumulative cap includes the full allowed idle loss, so a small bias can hide under a non-zero allowance.
  - NaN poisoning of cumulative residual value.
  - Duplicate non-finite reporting when battery argument is supplied.
- **Decision ID Collision Prevention:**
  - Decision IDs D-27 through D-34 are strictly reserved one per track. When branches merge back to `master`, resolve conflicts by sorting entries strictly by ID number and preserving all rows.

---

## 6. Primary Content (Verbatim Test Breakdown)

```text
============================= test session starts ==============================
platform linux -- Python 3.14.8, pytest-9.1.1, pluggy-1.6.0
rootdir: /home/lukexodus/projects/ccis-heat-load-backup-sim
configfile: pyproject.toml
collected 120 items

tests/test_baseline_smoke.py ........                                    [  6%] (8 passed)
tests/test_conservation_checker.py .........................             [ 26%] (24 passed)
tests/test_core_models.py ....................                           [ 43%] (20 passed)
tests/test_equipment_audit.py ...................                        [ 59%] (19 passed)
tests/test_interfaces.py .........                                       [ 66%] (9 passed)
tests/test_mock_bills.py ........                                        [ 73%] (8 passed)
tests/test_smoke.py ..........                                           [ 81%] (10 passed)
tests/test_weather_ingest.py ......................                     [100%] (22 passed)

============================= 120 passed in 7.32s ==============================
```
