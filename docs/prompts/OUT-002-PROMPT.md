# TASK: OUT-002: Priority-Based Tiered Load Shedding Controller

## Role & Worktree Instructions
- **Assigned Agent:** gemini
- **Task ID:** OUT-002 (covers OUT-002.1 onwards as listed in `docs/tasks/status.md`)
- **Branch / Worktree:** `./scripts/task-worktree.sh start OUT-002` (or `git worktree add ../ccis-heat-load-backup-sim-OUT-002 -b task/OUT-002`). **Branch from the current tip of `master` and confirm `src/ccis_sim/core/interfaces.py` and `docs/context/phase2-interface-contract.md` exist; if not, stop: CORE-006 has not landed.**
- **Depends on:** CORE-006. **Runs in parallel with:** OUT-001, DEM-*, SOL-*, BAT-*. Touch only files in your own track; edit only your own rows in `status.md`.
- **Stop-and-report rule:** if the repo differs from this prompt (a signature conflicts with the contract, a reserved ID is already used, a file you need is missing), stop that step and report. Do not improvise or silently change a contract signature.

## Orientation & Required Reading
1. `AGENTS.md` and `docs/context/complete-context.md`
2. `docs/tasks/status.md` (confirm your rows are `open`) and `docs/decisions/decision-log.md` (all entries)
3. `docs/context/phase2-interface-contract.md` and `src/ccis_sim/core/interfaces.py` (from CORE-006): your public signatures are fixed there
4. `src/ccis_sim/core/models.py` and `src/ccis_sim/core/verification.py`, read directly (verification harness conventions: [D-21], [D-25])
5. `LoadTier` in `models.py`; [D-10], [D-16], [D-17], [D-19]

## Context & Objectives
Decide, hour by hour, which tiers are served, and account for unserved energy. The battery's ability to physically deliver is the dispatcher's job; your controller sets the **policy tier** and tracks shortfalls handed back to it.

## Scope & Deliverables
### OUT-002.1 – .3 (`src/ccis_sim/outage/shedding.py`)
- `shed_for_hour(tier_demand_kwh, *, grid_available, soc_kwh, battery, tier2_shed_soc_fraction=0.20) -> ShedResult` per the contract.
  - Grid up → all tiers served, active tier 3.
  - Grid down → Tier 3 shed **immediately**; Tier 1 + Tier 2 served (active tier 2).
  - Grid down and SoC below `tier2_shed_soc_fraction × capacity` → Tier 2 also shed (active tier 1).
  - Unserved energy per tier equals demand minus served; `served + unserved` equals demand for every tier.
- OUT-002.1 tier mapping: demand arrives already tiered (from the audit). Add a helper that reports tier shares of peak/annual demand and compare them with D-10's nominal 2/18/80 split. The audit's actual split differs slightly ([D-16]/[D-19]): **report the discrepancy, do not force it**.
- The 20% threshold is a separate parameter from `Battery.emergency_reserve_pct` ([D-17]); record in [D-34] how you treat their relationship and leave integration to INT-001.
### OUT-002.4: Tracking
- `UnservedTracker`: `record(result, *, grid_available, battery_shortfall_kwh=0.0)` where a battery shortfall is allocated to the lowest-priority tier still being served; totals of unserved kWh per tier, outage hours, and outage hours in which each tier was fully served.

## Tests
- `tests/test_load_shedding.py`: instant Tier 3 shed on grid loss; exact boundary at the SoC threshold (just below, equal, just above); restoration returns to tier 3; per-tier conservation (`served + unserved = demand`), checked by building `HourlyRecord`s and passing the sub-flow balance check; tracker totals over a multi-hour outage including a battery shortfall; zero demand edge case; contract signature conformance.
- Run the full `pytest -v` and paste the **real, verbatim** output into the report (not an excerpt reconstructed from memory) with the new total.

## What NOT to Touch
- No outage sampling (OUT-001), no battery dynamics, no solar. Do not edit the harness.
- Do not edit `models.py`, `verification.py`, `interfaces.py`, other tracks' modules, or existing decision-log entries. If you believe a shared file needs a change, stop and report it.

## Verification & Acceptance Criteria
- [ ] Your public function(s) match `docs/context/phase2-interface-contract.md` exactly and are exercised through those signatures in tests.
- [ ] Every assumption you introduce is tagged `[ASSUMPTION]` in code docstrings and recorded in [D-34]; no unexplained magic constants.
- [ ] Full suite green; `./scripts/validate-report.py --all` passes.
- [ ] Report lists **every** file touched (including docs, status and fixtures).

## Reserved Decision IDs
**[D-34]** only, reserved for this task. If it is already used in the log, stop and report. If you end up needing no decision, say so in the report; do not reuse the ID for anything else.

## Output & Reporting Instructions
1. Commit on your task branch in logical commits: `feat(OUT-002): ...`. Never amend or rewrite commits on `master`; do not merge.
2. Gitignored patch: `patch/OUT-002-gemini-load-shedding.patch` via `git diff <base>..HEAD` (do not `git add -f`).
3. Report: `docs/reports/OUT-002-gemini-load-shedding.md` per `docs/reports/TASK-TEMPLATE.md`, with real command output.
4. Update your rows in `docs/tasks/status.md` (`done` only for subtasks you completed; leave deferred ones `open` and explain); append [D-34] to the decision log.
5. Validate: `./scripts/validate-report.py docs/reports/OUT-002-gemini-load-shedding.md`.
6. Run `./scripts/apc-bundle.sh core` (or the `.ps1`/`.bat` equivalent) since docs changed.
7. Report back: executive summary, test results, patch path, unified diff, branch name and worktree path. Do not delete the worktree.
