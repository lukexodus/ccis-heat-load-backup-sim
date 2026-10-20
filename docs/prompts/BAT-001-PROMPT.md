# TASK: BAT-001: Battery Dispatch Dynamics, SoC Tracking & Losses

## Role & Worktree Instructions
- **Assigned Agent:** gemini
- **Task ID:** BAT-001 (covers BAT-001.1 onwards as listed in `docs/tasks/status.md`)
- **Branch / Worktree:** `./scripts/task-worktree.sh start BAT-001` (or `git worktree add ../ccis-heat-load-backup-sim-BAT-001 -b task/BAT-001`). **Branch from the current tip of `master` and confirm `src/ccis_sim/core/interfaces.py` and `docs/context/phase2-interface-contract.md` exist; if not, stop: CORE-006 has not landed.**
- **Depends on:** CORE-006. **Runs in parallel with:** BAT-002, DEM-*, SOL-*, OUT-*. Touch only files in your own track; edit only your own rows in `status.md`.
- **Stop-and-report rule:** if the repo differs from this prompt (a signature conflicts with the contract, a reserved ID is already used, a file you need is missing), stop that step and report. Do not improvise or silently change a contract signature.

## Orientation & Required Reading
1. `AGENTS.md` and `docs/context/complete-context.md`
2. `docs/tasks/status.md` (confirm your rows are `open`) and `docs/decisions/decision-log.md` (all entries)
3. `docs/context/phase2-interface-contract.md` and `src/ccis_sim/core/interfaces.py` (from CORE-006): your public signatures are fixed there
4. `src/ccis_sim/core/models.py` and `src/ccis_sim/core/verification.py`, read directly (verification harness conventions: [D-21], [D-25])
5. `Battery` in `models.py`; harness SoC-continuity convention in [D-25] and [D-26]

## Context & Objectives
Implement the single-timestep battery update the INT-001 dispatcher will call every hour. It must agree **exactly** with the harness convention: charge/discharge are AC-side flows, `eta_chg = eta_dis = sqrt(round_trip_efficiency)`, `SoC_t = SoC_{t-1} + eta·charge − discharge/eta` ([D-25]).

## Scope & Deliverables
### BAT-001.1 – .3 (`src/ccis_sim/battery/dynamics.py`)
- `step_battery(soc_kwh, battery, charge_request_kwh, discharge_request_kwh, *, soc_floor_kwh=None, delta_t_hours=1.0) -> BatteryStepResult` per the contract.
- Charge is limited by the 0.5C power limit and by headroom to nameplate capacity; discharge by the 1.0C limit and by energy above `soc_floor_kwh` (default `battery.min_soc_kwh`). Report shortfalls in `charge_curtailed_kwh` / `discharge_unmet_kwh`.
- Requesting both charge and discharge (> 1e-6 kWh each) raises `ValueError` (prevention at the source; the harness catches it downstream).
- Idle/self-discharge/tare are **not** yours (BAT-002).
- Zero-capacity battery: all flows zero, SoC zero.

## Tests
- `tests/test_battery_dynamics.py` (BAT-001.4): efficiency split (charge then discharge returns RTE of the energy); C-rate caps; headroom and floor limiting; simultaneous request rejected; zero-capacity case; determinism; **property test** (hypothesis is installed): random request sequences chained over many hours always pass `run_verification_harness(records, battery=...)` boundaries and SoC continuity when wrapped into `HourlyRecord`s; contract signature conformance.
- Run the full `pytest -v` and paste the **real, verbatim** output into the report (not an excerpt reconstructed from memory) with the new total.

## What NOT to Touch
- No dispatch policy (INT-001), no outage logic, no idle losses, no reserve policy. Do not edit the harness.
- Do not edit `models.py`, `verification.py`, `interfaces.py`, other tracks' modules, or existing decision-log entries. If you believe a shared file needs a change, stop and report it.

## Verification & Acceptance Criteria
- [ ] Your public function(s) match `docs/context/phase2-interface-contract.md` exactly and are exercised through those signatures in tests.
- [ ] Every assumption you introduce is tagged `[ASSUMPTION]` in code docstrings and recorded in [D-31]; no unexplained magic constants.
- [ ] Full suite green; `./scripts/validate-report.py --all` passes.
- [ ] Report lists **every** file touched (including docs, status and fixtures).

## Reserved Decision IDs
**[D-31]** only, reserved for this task. If it is already used in the log, stop and report. If you end up needing no decision, say so in the report; do not reuse the ID for anything else.

## Output & Reporting Instructions
1. Commit on your task branch in logical commits: `feat(BAT-001): ...`. Never amend or rewrite commits on `master`; do not merge.
2. Gitignored patch: `patch/BAT-001-gemini-battery-dynamics.patch` via `git diff <base>..HEAD` (do not `git add -f`).
3. Report: `docs/reports/BAT-001-gemini-battery-dynamics.md` per `docs/reports/TASK-TEMPLATE.md`, with real command output.
4. Update your rows in `docs/tasks/status.md` (`done` only for subtasks you completed; leave deferred ones `open` and explain); append [D-31] to the decision log.
5. Validate: `./scripts/validate-report.py docs/reports/BAT-001-gemini-battery-dynamics.md`.
6. Run `./scripts/apc-bundle.sh core` (or the `.ps1`/`.bat` equivalent) since docs changed.
7. Report back: executive summary, test results, patch path, unified diff, branch name and worktree path. Do not delete the worktree.
