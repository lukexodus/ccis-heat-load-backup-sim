# TASK: OUT-001: Stochastic Outage Arrival & Duration Sampler

## Role & Worktree Instructions
- **Assigned Agent:** gemini
- **Task ID:** OUT-001 (covers OUT-001.1 onwards as listed in `docs/tasks/status.md`)
- **Branch / Worktree:** `./scripts/task-worktree.sh start OUT-001` (or `git worktree add ../ccis-heat-load-backup-sim-OUT-001 -b task/OUT-001`). **Branch from the current tip of `master` and confirm `src/ccis_sim/core/interfaces.py` and `docs/context/phase2-interface-contract.md` exist; if not, stop: CORE-006 has not landed.**
- **Depends on:** CORE-006. **Runs in parallel with:** OUT-002, DEM-*, SOL-*, BAT-*. Touch only files in your own track; edit only your own rows in `status.md`.
- **Stop-and-report rule:** if the repo differs from this prompt (a signature conflicts with the contract, a reserved ID is already used, a file you need is missing), stop that step and report. Do not improvise or silently change a contract signature.

## Orientation & Required Reading
1. `AGENTS.md` and `docs/context/complete-context.md`
2. `docs/tasks/status.md` (confirm your rows are `open`) and `docs/decisions/decision-log.md` (all entries)
3. `docs/context/phase2-interface-contract.md` and `src/ccis_sim/core/interfaces.py` (from CORE-006): your public signatures are fixed there
4. `src/ccis_sim/core/models.py` and `src/ccis_sim/core/verification.py`, read directly (verification harness conventions: [D-21], [D-25])
5. `OutageEvent` in `models.py` and its tests; [D-11] and `docs/context/research-synthesis.md` §outages

## Context & Objectives
Sample a year of grid outages with the [D-11] parameters and the typhoon coupling, as an `OutageSchedule` the integration loop can read hour by hour. All randomness comes from the `rng` argument.

## Scope & Deliverables
### OUT-001.1 – .2 (`src/ccis_sim/outage/sampler.py`)
- Poisson arrivals: λ = 3.0/yr (normal), 8.0/yr (typhoon). Start times uniform over the year unless you justify seasonal clustering for typhoon years (record it in [D-33]).
- Durations Lognormal(μ, σ) on ln(hours): normal (1.2, 0.8); typhoon (2.3, 1.0). State how you discretize to integer hours (e.g. ceiling, minimum 1 h), clip at year end and merge overlaps; document the bias this introduces.
### OUT-001.3: Typhoon solar depression
- For typhoon years, 3–5 consecutive days with GHI at **20–30% of normal** ([D-11] wording: "depressed solar irradiance (20–30% normal GHI)"). This reading is ambiguous (could mean a 20–30% *reduction*): state which you implement and why in [D-33] so the APC can confirm. Choose how many episodes occur and how they relate to outage events. Expose via `OutageSchedule.ghi_multiplier` and `apply_ghi_multiplier(weather_df, schedule) -> DataFrame` (returns a copy).
### OUT-001.4: Goodness-of-fit validator
- `validate_duration_distribution(...)`: Kolmogorov–Smirnov test of sampled (pre-discretization) durations against the target Lognormal, plus an arrival-count check against Poisson(λ). Returns a result object, not a bare bool.

## Tests
- `tests/test_outage_sampler.py`: same seed → identical schedule; mean outage count ≈ λ over ≥2,000 sampled years; KS test passes at α = 0.01 for correct parameters and **fails** against deliberately wrong parameters; events lie within [1, N], no overlaps; `grid_available` mask agrees with events; typhoon multipliers are 1.0 outside episodes and in the stated range inside; normal years have all-ones multiplier; contract signature conformance.
- Run the full `pytest -v` and paste the **real, verbatim** output into the report (not an excerpt reconstructed from memory) with the new total.

## What NOT to Touch
- No load shedding, no battery or solar logic, no Monte Carlo loop (INT-002). Do not use global RNG state.
- Do not edit `models.py`, `verification.py`, `interfaces.py`, other tracks' modules, or existing decision-log entries. If you believe a shared file needs a change, stop and report it.

## Verification & Acceptance Criteria
- [ ] Your public function(s) match `docs/context/phase2-interface-contract.md` exactly and are exercised through those signatures in tests.
- [ ] Every assumption you introduce is tagged `[ASSUMPTION]` in code docstrings and recorded in [D-33]; no unexplained magic constants.
- [ ] Full suite green; `./scripts/validate-report.py --all` passes.
- [ ] Report lists **every** file touched (including docs, status and fixtures).

## Reserved Decision IDs
**[D-33]** only, reserved for this task. If it is already used in the log, stop and report. If you end up needing no decision, say so in the report; do not reuse the ID for anything else.

## Output & Reporting Instructions
1. Commit on your task branch in logical commits: `feat(OUT-001): ...`. Never amend or rewrite commits on `master`; do not merge.
2. Gitignored patch: `patch/OUT-001-gemini-outage-sampler.patch` via `git diff <base>..HEAD` (do not `git add -f`).
3. Report: `docs/reports/OUT-001-gemini-outage-sampler.md` per `docs/reports/TASK-TEMPLATE.md`, with real command output.
4. Update your rows in `docs/tasks/status.md` (`done` only for subtasks you completed; leave deferred ones `open` and explain); append [D-33] to the decision log.
5. Validate: `./scripts/validate-report.py docs/reports/OUT-001-gemini-outage-sampler.md`.
6. Run `./scripts/apc-bundle.sh core` (or the `.ps1`/`.bat` equivalent) since docs changed.
7. Report back: executive summary, test results, patch path, unified diff, branch name and worktree path. Do not delete the worktree.
