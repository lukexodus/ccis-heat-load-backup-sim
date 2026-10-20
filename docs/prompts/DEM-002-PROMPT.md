# TASK: DEM-002: Temperature & Humidity Cooling Response Model

## Role & Worktree Instructions
- **Assigned Agent:** gemini
- **Task ID:** DEM-002 (covers DEM-002.1 onwards as listed in `docs/tasks/status.md`)
- **Branch / Worktree:** `./scripts/task-worktree.sh start DEM-002` (or `git worktree add ../ccis-heat-load-backup-sim-DEM-002 -b task/DEM-002`). **Branch from the current tip of `master` and confirm `src/ccis_sim/core/interfaces.py` and `docs/context/phase2-interface-contract.md` exist; if not, stop: CORE-006 has not landed.**
- **Depends on:** CORE-006. **Runs in parallel with:** DEM-001, SOL-*, BAT-*, OUT-*. Touch only files in your own track; edit only your own rows in `status.md`.
- **Stop-and-report rule:** if the repo differs from this prompt (a signature conflicts with the contract, a reserved ID is already used, a file you need is missing), stop that step and report. Do not improvise or silently change a contract signature.
- **Time-box:** The deadline is tight. Skip stretch goals; if a subtask would take more than ~45 minutes, implement the simplest version, log it as a limitation in the report, and move on.

## Orientation & Required Reading
1. `AGENTS.md` and `docs/context/complete-context.md`
2. `docs/tasks/status.md` (confirm your rows are `open`) and `docs/decisions/decision-log.md` (all entries)
3. `docs/context/phase2-interface-contract.md` and `src/ccis_sim/core/interfaces.py` (from CORE-006): your public signatures are fixed there
4. `src/ccis_sim/core/models.py` and `src/ccis_sim/core/verification.py`, read directly (verification harness conventions: [D-21], [D-25])
5. `src/ccis_sim/demand/equipment.py`, `data/fixtures/equipment-audit-ccis.csv`, `src/ccis_sim/integration/baseline.py` (the placeholder you supersede), `src/ccis_sim/weather/` (psychrometric helpers)

## Context & Objectives
Build the physical-ish cooling response that [D-07] locked: piecewise-linear CDD, latent penalty, and inverter modulation. It consumes `occupancy_fraction` as a plain array, so you do not depend on DEM-001's code; use a synthetic occupancy array in tests.

## Scope & Deliverables
### DEM-002.1: Sensible cooling (`src/ccis_sim/demand/cooling.py`)
- Cooling electrical demand rises 4.0%/°C above T_base = 24.0°C ([D-07]) relative to a stated reference cooling power. Define the reference (e.g. connected cooling kW × a reference duty at T_base) explicitly in [D-28]; do **not** reuse the placeholder's unexplained 0.35 factor without justification.
### DEM-002.2: Latent multiplier
- +20% latent penalty at tropical humidity ([D-07]). The task text does not define the RH shape: choose threshold and ramp (step vs linear between two RH values), document and record it in [D-28].
### DEM-002.3: Split-AC duty cycle / inverter modulation
- Model compressor duty and a minimum modulation floor. Cooling demand is **capped at connected cooling capacity** from the audit. Cooling items keep the tier from the audit (Tier 3 comfort cooling; Tier 2 spot cooling per [D-16]); decide whether spot cooling runs 24/7 and record it.
- `compute_cooling_demand(weather_df, occupancy_fraction, audit, building) -> TieredDemand` exactly per the contract.

## Tests
- `tests/test_cooling_response.py`: zero sensible cooling at or below T_base; slope is 4%/°C above it; latent multiplier at low vs high RH; capacity cap never exceeded; unoccupied hours produce only the Tier 2 spot-cooling term (if any); tier sums equal gross; monotonic in temperature; determinism; contract signature conformance.
- Also report (do not assert) the implied annual cooling kWh on the 2019 and 2016 fixtures with a stated synthetic occupancy, for later calibration.
- Run the full `pytest -v` and paste the **real, verbatim** output into the report (not an excerpt reconstructed from memory) with the new total.

## What NOT to Touch
- **Do not implement DEM-002.4** (validation against mock bills needs DEM-001 merged). Leave DEM-002.4 `open` in status.md and say so in the report; the APC will dispatch it after both merge.
- No calibration multiplier; do not touch `baseline.py`.
- Do not edit `models.py`, `verification.py`, `interfaces.py`, other tracks' modules, or existing decision-log entries. If you believe a shared file needs a change, stop and report it.

## Verification & Acceptance Criteria
- [ ] Your public function(s) match `docs/context/phase2-interface-contract.md` exactly and are exercised through those signatures in tests.
- [ ] Every assumption you introduce is tagged `[ASSUMPTION]` in code docstrings and recorded in [D-28]; no unexplained magic constants.
- [ ] Full suite green; `./scripts/validate-report.py --all` passes.
- [ ] Report lists **every** file touched (including docs, status and fixtures).

## Reserved Decision IDs
**[D-28]** only, reserved for this task. If it is already used in the log, stop and report. If you end up needing no decision, say so in the report; do not reuse the ID for anything else.

## Output & Reporting Instructions
1. Commit on your task branch in logical commits: `feat(DEM-002): ...`. Never amend or rewrite commits on `master`; do not merge.
2. Gitignored patch: `patch/DEM-002-gemini-cooling-response.patch` via `git diff <base>..HEAD` (do not `git add -f`).
3. Report: `docs/reports/DEM-002-gemini-cooling-response.md` per `docs/reports/TASK-TEMPLATE.md`, with real command output.
4. Update your rows in `docs/tasks/status.md` (`done` only for subtasks you completed; leave deferred ones `open` and explain); append [D-28] to the decision log.
5. Validate: `./scripts/validate-report.py docs/reports/DEM-002-gemini-cooling-response.md`.
6. Run `./scripts/apc-bundle.sh core` (or the `.ps1`/`.bat` equivalent) since docs changed.
7. Report back: executive summary, test results, patch path, unified diff, branch name and worktree path. Do not delete the worktree.
