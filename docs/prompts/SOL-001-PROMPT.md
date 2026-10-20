# TASK: SOL-001: Solar Irradiance Geometry & NOCT Thermal Derating Model

## Role & Worktree Instructions
- **Assigned Agent:** gemini
- **Task ID:** SOL-001 (covers SOL-001.1 onwards as listed in `docs/tasks/status.md`)
- **Branch / Worktree:** `./scripts/task-worktree.sh start SOL-001` (or `git worktree add ../ccis-heat-load-backup-sim-SOL-001 -b task/SOL-001`). **Branch from the current tip of `master` and confirm `src/ccis_sim/core/interfaces.py` and `docs/context/phase2-interface-contract.md` exist; if not, stop: CORE-006 has not landed.**
- **Depends on:** CORE-006. **Runs in parallel with:** SOL-002, DEM-*, BAT-*, OUT-*. Touch only files in your own track; edit only your own rows in `status.md`.
- **Stop-and-report rule:** if the repo differs from this prompt (a signature conflicts with the contract, a reserved ID is already used, a file you need is missing), stop that step and report. Do not improvise or silently change a contract signature.
- **Time-box:** The deadline is tight. Skip stretch goals; if a subtask would take more than ~45 minutes, implement the simplest version, log it as a limitation in the report, and move on.

## Orientation & Required Reading
1. `AGENTS.md` and `docs/context/complete-context.md`
2. `docs/tasks/status.md` (confirm your rows are `open`) and `docs/decisions/decision-log.md` (all entries)
3. `docs/context/phase2-interface-contract.md` and `src/ccis_sim/core/interfaces.py` (from CORE-006): your public signatures are fixed there
4. `src/ccis_sim/core/models.py` and `src/ccis_sim/core/verification.py`, read directly (verification harness conventions: [D-21], [D-25])
5. `src/ccis_sim/weather/disaggregator.py` (existing solar-geometry code you may reuse), `docs/context/research-synthesis.md` §solar

## Context & Objectives
Turn hourly **GHI only** (no DNI/DHI in the fixtures) into plane-of-array irradiance for a 15° south-tilted array at Batac, then cell temperature and thermal derating. You output DC power per kWp **before** balance-of-system and inverter effects (SOL-002 owns those).

## Scope & Deliverables
### SOL-001.1: Tilted-plane irradiance (`src/ccis_sim/solar/irradiance.py`)
- Solar position (state the algorithm and time convention). Fixture timestamps are local standard time +08:00 while the standard meridian is 120°E and the site is 120.56°E: apply the longitude and equation-of-time correction and sanity-check that solar noon lands near 12:00 ± a few minutes.
- GHI→DNI/DHI decomposition (e.g. Erbs) and transposition to 15° tilt, azimuth 180° (e.g. isotropic or Hay-Davies); ground albedo is an `[ASSUMPTION]`. Choices go in [D-29].
### SOL-001.2: Cell temperature
- NOCT 45°C with the +10°C rooftop mounting penalty ([D-08]). The decision text is ambiguous about where the +10°C enters: state your formula explicitly (e.g. `T_cell = T_amb + ((45+10) - 20)/800 · G_poa`) and record it.
### SOL-001.3: Thermal derating
- γ = −0.40%/°C above the 25°C reference ([D-08]). `compute_dc_power_per_kwp(weather_df, *, tilt_deg=15.0, azimuth_deg=180.0, latitude_deg=18.06, longitude_deg=120.56) -> ndarray` (kW DC per kWp) exactly per the contract.

## Tests
- `tests/test_solar_irradiance.py` (SOL-001.4): night is exactly zero; solar noon near 12:00 on a clear day; for equal irradiance, a hotter hour yields strictly lower DC power than a cooler hour; POA is within a sane band of GHI at 15° tilt; no negative or NaN output; array length equals input; determinism; contract signature conformance. Report (do not assert against the benchmark) annual specific DC yield for 2019; the 1,298 kWh/kWp validation is SOL-002.4.
- Run the full `pytest -v` and paste the **real, verbatim** output into the report (not an excerpt reconstructed from memory) with the new total.

## What NOT to Touch
- No inverter, clipping, soiling, wiring or PR budget (SOL-002). No curtailment (dispatch). **Do not implement SOL-002.4.**
- Do not edit `models.py`, `verification.py`, `interfaces.py`, other tracks' modules, or existing decision-log entries. If you believe a shared file needs a change, stop and report it.

## Verification & Acceptance Criteria
- [ ] Your public function(s) match `docs/context/phase2-interface-contract.md` exactly and are exercised through those signatures in tests.
- [ ] Every assumption you introduce is tagged `[ASSUMPTION]` in code docstrings and recorded in [D-29]; no unexplained magic constants.
- [ ] Full suite green; `./scripts/validate-report.py --all` passes.
- [ ] Report lists **every** file touched (including docs, status and fixtures).

## Reserved Decision IDs
**[D-29]** only, reserved for this task. If it is already used in the log, stop and report. If you end up needing no decision, say so in the report; do not reuse the ID for anything else.

## Output & Reporting Instructions
1. Commit on your task branch in logical commits: `feat(SOL-001): ...`. Never amend or rewrite commits on `master`; do not merge.
2. Gitignored patch: `patch/SOL-001-gemini-solar-irradiance.patch` via `git diff <base>..HEAD` (do not `git add -f`).
3. Report: `docs/reports/SOL-001-gemini-solar-irradiance.md` per `docs/reports/TASK-TEMPLATE.md`, with real command output.
4. Update your rows in `docs/tasks/status.md` (`done` only for subtasks you completed; leave deferred ones `open` and explain); append [D-29] to the decision log.
5. Validate: `./scripts/validate-report.py docs/reports/SOL-001-gemini-solar-irradiance.md`.
6. Run `./scripts/apc-bundle.sh core` (or the `.ps1`/`.bat` equivalent) since docs changed.
7. Report back: executive summary, test results, patch path, unified diff, branch name and worktree path. Do not delete the worktree.
