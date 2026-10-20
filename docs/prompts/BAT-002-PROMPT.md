# TASK: BAT-002: Battery Outage Reserve & State-of-Charge Constraints

## Role & Worktree Instructions
- **Assigned Agent:** gemini
- **Task ID:** BAT-002 (covers BAT-002.1 onwards as listed in `docs/tasks/status.md`)
- **Branch / Worktree:** `./scripts/task-worktree.sh start BAT-002` (or `git worktree add ../ccis-heat-load-backup-sim-BAT-002 -b task/BAT-002`). **Branch from the current tip of `master` and confirm `src/ccis_sim/core/interfaces.py` and `docs/context/phase2-interface-contract.md` exist; if not, stop: CORE-006 has not landed.**
- **Depends on:** CORE-006 (idle-loss allowance in the harness). **Runs in parallel with:** BAT-001, DEM-*, SOL-*, OUT-*. Touch only files in your own track; edit only your own rows in `status.md`.
- **Stop-and-report rule:** if the repo differs from this prompt (a signature conflicts with the contract, a reserved ID is already used, a file you need is missing), stop that step and report. Do not improvise or silently change a contract signature.

## Orientation & Required Reading
1. `AGENTS.md` and `docs/context/complete-context.md`
2. `docs/tasks/status.md` (confirm your rows are `open`) and `docs/decisions/decision-log.md` (all entries)
3. `docs/context/phase2-interface-contract.md` and `src/ccis_sim/core/interfaces.py` (from CORE-006): your public signatures are fixed there
4. `src/ccis_sim/core/models.py` and `src/ccis_sim/core/verification.py`, read directly (verification harness conventions: [D-21], [D-25])
5. `Battery` in `models.py` ([D-09], [D-17]); harness idle-loss rule in [D-26]

## Context & Objectives
Provide the floor policy and idle-loss functions that INT-001 composes with BAT-001's `step_battery`. You do **not** depend on BAT-001's code: test with a small local reference loop.

## Scope & Deliverables
### BAT-002.1 – .2: Floors (`src/ccis_sim/battery/reserve.py`)
- `soc_floor_kwh(battery, *, grid_available, active_load_tier, allow_emergency_drawdown=False) -> float`. Proposed semantics, which you must confirm or amend in [D-32]: grid up → operational floor = `min_soc_kwh + emergency_reserve_kwh` ([D-17] holds the reserve back from daily dispatch); grid down → `min_soc_kwh` (reserve released); grid down with `allow_emergency_drawdown` and Tier 1/2 active → 0.0 ([D-25]). The harness hard floor stays `min_soc_kwh`.
### BAT-002.3: Idle losses
- `apply_idle_losses(soc_kwh, battery, delta_t_hours=1.0) -> (new_soc_kwh, loss_kwh)`: self-discharge 2%/month (state the hours-per-month convention) plus tare, both SoC-side per [D-26]. Losses are clamped so SoC never falls below the hard floor `min_soc_kwh` (record this choice) or below 0, and the loss per hour must stay within the harness's `max_idle_loss_per_hour` allowance.

## Tests
- `tests/test_battery_reserve.py` (BAT-002.4): floor values for each grid/tier/drawdown case; reserve released in an outage; a 48-hour outage reference loop never goes below the floor unless emergency drawdown is on; idle losses clamp at the floor; chained series including idle losses pass `run_verification_harness` (continuity with idle allowance); zero idle parameters change nothing; contract signature conformance.
- Run the full `pytest -v` and paste the **real, verbatim** output into the report (not an excerpt reconstructed from memory) with the new total.

## What NOT to Touch
- No charge/discharge dynamics (BAT-001), no shedding (OUT-002). Do not edit the harness or existing decisions.
- Do not edit `models.py`, `verification.py`, `interfaces.py`, other tracks' modules, or existing decision-log entries. If you believe a shared file needs a change, stop and report it.

## Verification & Acceptance Criteria
- [ ] Your public function(s) match `docs/context/phase2-interface-contract.md` exactly and are exercised through those signatures in tests.
- [ ] Every assumption you introduce is tagged `[ASSUMPTION]` in code docstrings and recorded in [D-32]; no unexplained magic constants.
- [ ] Full suite green; `./scripts/validate-report.py --all` passes.
- [ ] Report lists **every** file touched (including docs, status and fixtures).

## Reserved Decision IDs
**[D-32]** only, reserved for this task. If it is already used in the log, stop and report. If you end up needing no decision, say so in the report; do not reuse the ID for anything else.

## Output & Reporting Instructions
1. Commit on your task branch in logical commits: `feat(BAT-002): ...`. Never amend or rewrite commits on `master`; do not merge.
2. Gitignored patch: `patch/BAT-002-gemini-battery-reserve.patch` via `git diff <base>..HEAD` (do not `git add -f`).
3. Report: `docs/reports/BAT-002-gemini-battery-reserve.md` per `docs/reports/TASK-TEMPLATE.md`, with real command output.
4. Update your rows in `docs/tasks/status.md` (`done` only for subtasks you completed; leave deferred ones `open` and explain); append [D-32] to the decision log.
5. Validate: `./scripts/validate-report.py docs/reports/BAT-002-gemini-battery-reserve.md`.
6. Run `./scripts/apc-bundle.sh core` (or the `.ps1`/`.bat` equivalent) since docs changed.
7. Report back: executive summary, test results, patch path, unified diff, branch name and worktree path. Do not delete the worktree.
