# TASK: SOL-002: Array Sizing, Inverter Clipping & Balance-of-System Losses

## Role & Worktree Instructions
- **Assigned Agent:** gemini
- **Task ID:** SOL-002 (covers SOL-002.1 onwards as listed in `docs/tasks/status.md`)
- **Branch / Worktree:** `./scripts/task-worktree.sh start SOL-002` (or `git worktree add ../ccis-heat-load-backup-sim-SOL-002 -b task/SOL-002`). **Branch from the current tip of `master` and confirm `src/ccis_sim/core/interfaces.py` and `docs/context/phase2-interface-contract.md` exist; if not, stop: CORE-006 has not landed.**
- **Depends on:** CORE-006. **Runs in parallel with:** SOL-001, DEM-*, BAT-*, OUT-*. Touch only files in your own track; edit only your own rows in `status.md`.
- **Stop-and-report rule:** if the repo differs from this prompt (a signature conflicts with the contract, a reserved ID is already used, a file you need is missing), stop that step and report. Do not improvise or silently change a contract signature.
- **Time-box:** The deadline is tight. Skip stretch goals; if a subtask would take more than ~45 minutes, implement the simplest version, log it as a limitation in the report, and move on.

## Orientation & Required Reading
1. `AGENTS.md` and `docs/context/complete-context.md`
2. `docs/tasks/status.md` (confirm your rows are `open`) and `docs/decisions/decision-log.md` (all entries)
3. `docs/context/phase2-interface-contract.md` and `src/ccis_sim/core/interfaces.py` (from CORE-006): your public signatures are fixed there
4. `src/ccis_sim/core/models.py` and `src/ccis_sim/core/verification.py`, read directly (verification harness conventions: [D-21], [D-25])
5. `SolarArray` in `models.py` (capacity scenarios 0/50/100/200 kWp, [D-18]) and [D-08]

## Context & Objectives
Convert DC power per kWp into AC generation for a sized array. SOL-001 (parallel) applies the explicit thermal derate. **Do not double count temperature losses**: [D-08]'s PR = 0.77 normally already includes thermal losses.

## Scope & Deliverables
### SOL-002.1: Capacity scaling (`src/ccis_sim/solar/array.py`)
- `compute_ac_generation(dc_kw_per_kwp, array) -> ndarray` (kWh AC per hour) exactly per the contract; scenario capacities 0, 50, 100, 200 kWp. Capacity 0 returns zeros.
### SOL-002.2: Inverter
- Peak efficiency 98% and a DC/AC clipping limit. Choose the DC/AC ratio (or read it from `SolarArray` if present), record it, and make AC output never exceed the AC rating.
### SOL-002.3: Balance-of-system derates
- Decompose PR = 0.77 into **named** factors (soiling, wiring, mismatch, availability, inverter, and the thermal share). Because SOL-001 applies thermal explicitly, define a constant `ASSUMED_MEAN_THERMAL_FACTOR` (state your assumption and basis) and set the BOS product so that BOS × inverter × assumed thermal ≈ 0.77. Record the full budget in [D-30]; recalibration against real SOL-001 output happens in SOL-002.4.

## Tests
- `tests/test_solar_array.py`: linearity in kWp below the clipping limit; clipping at high irradiance; AC never exceeds rating; zero at night and at 0 kWp; PR budget factors multiply to the documented total; non-negative, finite, same length; determinism; contract signature conformance (feed it a synthetic `dc_kw_per_kwp` array).
- Run the full `pytest -v` and paste the **real, verbatim** output into the report (not an excerpt reconstructed from memory) with the new total.

## What NOT to Touch
- **Do not implement SOL-002.4** (needs SOL-001 merged); leave it `open` and say so. Do not implement irradiance or temperature models.
- Do not edit `models.py`, `verification.py`, `interfaces.py`, other tracks' modules, or existing decision-log entries. If you believe a shared file needs a change, stop and report it.

## Verification & Acceptance Criteria
- [ ] Your public function(s) match `docs/context/phase2-interface-contract.md` exactly and are exercised through those signatures in tests.
- [ ] Every assumption you introduce is tagged `[ASSUMPTION]` in code docstrings and recorded in [D-30]; no unexplained magic constants.
- [ ] Full suite green; `./scripts/validate-report.py --all` passes.
- [ ] Report lists **every** file touched (including docs, status and fixtures).

## Reserved Decision IDs
**[D-30]** only, reserved for this task. If it is already used in the log, stop and report. If you end up needing no decision, say so in the report; do not reuse the ID for anything else.

## Output & Reporting Instructions
1. Commit on your task branch in logical commits: `feat(SOL-002): ...`. Never amend or rewrite commits on `master`; do not merge.
2. Gitignored patch: `patch/SOL-002-gemini-solar-array.patch` via `git diff <base>..HEAD` (do not `git add -f`).
3. Report: `docs/reports/SOL-002-gemini-solar-array.md` per `docs/reports/TASK-TEMPLATE.md`, with real command output.
4. Update your rows in `docs/tasks/status.md` (`done` only for subtasks you completed; leave deferred ones `open` and explain); append [D-30] to the decision log.
5. Validate: `./scripts/validate-report.py docs/reports/SOL-002-gemini-solar-array.md`.
6. Run `./scripts/apc-bundle.sh core` (or the `.ps1`/`.bat` equivalent) since docs changed.
7. Report back: executive summary, test results, patch path, unified diff, branch name and worktree path. Do not delete the worktree.
