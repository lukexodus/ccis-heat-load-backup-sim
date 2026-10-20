# TASK: DEM-001: Equipment Load & Occupancy Schedule Model

## Role & Worktree Instructions
- **Assigned Agent:** gemini
- **Task ID:** DEM-001 (covers DEM-001.1 onwards as listed in `docs/tasks/status.md`)
- **Branch / Worktree:** `./scripts/task-worktree.sh start DEM-001` (or `git worktree add ../ccis-heat-load-backup-sim-DEM-001 -b task/DEM-001`). **Branch from the current tip of `master` and confirm `src/ccis_sim/core/interfaces.py` and `docs/context/phase2-interface-contract.md` exist; if not, stop: CORE-006 has not landed.**
- **Depends on:** CORE-006. **Runs in parallel with:** DEM-002, SOL-*, BAT-*, OUT-*. Touch only files in your own track; edit only your own rows in `status.md`.
- **Stop-and-report rule:** if the repo differs from this prompt (a signature conflicts with the contract, a reserved ID is already used, a file you need is missing), stop that step and report. Do not improvise or silently change a contract signature.

## Orientation & Required Reading
1. `AGENTS.md` and `docs/context/complete-context.md`
2. `docs/tasks/status.md` (confirm your rows are `open`) and `docs/decisions/decision-log.md` (all entries)
3. `docs/context/phase2-interface-contract.md` and `src/ccis_sim/core/interfaces.py` (from CORE-006): your public signatures are fixed there
4. `src/ccis_sim/core/models.py` and `src/ccis_sim/core/verification.py`, read directly (verification harness conventions: [D-21], [D-25])
5. `src/ccis_sim/demand/equipment.py`, `data/fixtures/equipment-audit-ccis.csv`, `docs/context/research-synthesis.md` (occupancy and schedule evidence)

## Context & Objectives
Replace the CORE-005 placeholder occupancy/base-load logic with a bottom-up, auditable non-cooling demand model. Cooling is **not** yours (DEM-002). Output per-tier hourly demand so OUT-002 can shed by tier.

## Scope & Deliverables
### DEM-001.1: Academic schedule engine (`src/ccis_sim/demand/schedule.py`)
- `AcademicCalendar` dataclass (semester start/end, term breaks, summer break, holiday dates) with a documented default for the weather year. Defaults are `[ASSUMPTION]`s patterned on a Philippine state-university year; list every date and its basis in [D-27]. Include Philippine regular and special non-working holidays for 2019 and 2016 (the two fixture years).
- `build_occupancy_schedule(timestamps, *, calendar=None) -> OccupancySchedule` exactly per the contract: hourly occupancy fraction (class hours by weekday/Saturday, lunch dip, evening), plus `is_class_day`, `is_break`, `is_holiday`.
### DEM-001.2: Diurnal non-cooling demand (`src/ccis_sim/demand/non_cooling.py`)
- `compute_non_cooling_demand(schedule, audit, building) -> TieredDemand`: bottom-up from audit items where `is_cooling` is false (lighting, PCs, IT, plug loads, pumps). Each item is either occupancy-driven (scaled by `occupancy_fraction`, count, rated kW, duty cycle) or continuous (24/7 items such as IDF switches and life safety). Tier comes from the audit row.
### DEM-001.3: Unoccupied baseload
- Unoccupied-hour non-cooling demand equals 10% of the daytime peak non-cooling demand, per the task definition. Define precisely how this interacts with 24/7 audit items so the baseload is **not double counted**; document in [D-27].

## Tests
- `tests/test_demand_schedule.py`, `tests/test_non_cooling_demand.py` (DEM-001.4): calendar edge cases (holiday on weekday, break week, Sunday, DST-free +08:00 timestamps, leap/non-leap year); occupancy bounds [0, 1]; tier sums equal gross; baseload rule holds on a night, a Sunday and a holiday; class-day demand > holiday demand; determinism; contract signature conformance (call exactly as in the contract). Do not tune to the mock bills (DEM-002.4 will compare later).
- Run the full `pytest -v` and paste the **real, verbatim** output into the report (not an excerpt reconstructed from memory) with the new total.

## What NOT to Touch
- No cooling or weather dependence. No calibration multiplier. Do not modify `baseline.py` (it stays as the Phase 1 smoke test).
- Do not edit `models.py`, `verification.py`, `interfaces.py`, other tracks' modules, or existing decision-log entries. If you believe a shared file needs a change, stop and report it.

## Verification & Acceptance Criteria
- [ ] Your public function(s) match `docs/context/phase2-interface-contract.md` exactly and are exercised through those signatures in tests.
- [ ] Every assumption you introduce is tagged `[ASSUMPTION]` in code docstrings and recorded in [D-27]; no unexplained magic constants.
- [ ] Full suite green; `./scripts/validate-report.py --all` passes.
- [ ] Report lists **every** file touched (including docs, status and fixtures).

## Reserved Decision IDs
**[D-27]** only, reserved for this task. If it is already used in the log, stop and report. If you end up needing no decision, say so in the report; do not reuse the ID for anything else.

## Output & Reporting Instructions
1. Commit on your task branch in logical commits: `feat(DEM-001): ...`. Never amend or rewrite commits on `master`; do not merge.
2. Gitignored patch: `patch/DEM-001-gemini-demand-schedule.patch` via `git diff <base>..HEAD` (do not `git add -f`).
3. Report: `docs/reports/DEM-001-gemini-demand-schedule.md` per `docs/reports/TASK-TEMPLATE.md`, with real command output.
4. Update your rows in `docs/tasks/status.md` (`done` only for subtasks you completed; leave deferred ones `open` and explain); append [D-27] to the decision log.
5. Validate: `./scripts/validate-report.py docs/reports/DEM-001-gemini-demand-schedule.md`.
6. Run `./scripts/apc-bundle.sh core` (or the `.ps1`/`.bat` equivalent) since docs changed.
7. Report back: executive summary, test results, patch path, unified diff, branch name and worktree path. Do not delete the worktree.
