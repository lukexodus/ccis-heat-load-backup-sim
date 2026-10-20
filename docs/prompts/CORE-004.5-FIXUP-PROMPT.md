# TASK: CORE-004.5 — Phase 1 Closeout Fixup (repo hygiene, harness gaps, D-22 disclosure)

## Role & Worktree Instructions
- **Assigned Agent:** gemini
- **Task ID:** CORE-004.5 (new fixup subtask; also closes the loose ends from CORE-005)
- **Branch / Worktree:** `./scripts/task-worktree.sh start CORE-004.5`. **Verify the branch base is the current tip of `master` (`git log -1 master`, `git merge-base HEAD master`) before touching anything.** A stale base is the likely cause of Part A's problem.
- **Depends on:** CORE-001 – CORE-005 (all `done`).
- **Blocks:** Phase 2, specifically `BAT-001` (needs Part B).
- **Stop-and-report rule:** if the repository state differs from what this prompt describes (a file already restored, a gap already fixed, a decision ID already taken), stop that step and report it. Do not improvise.

## Orientation & Required Reading
1. `AGENTS.md`, `docs/context/complete-context.md`
2. `docs/tasks/status.md`, `docs/decisions/decision-log.md` ([D-09], [D-17], [D-21], [D-22] in particular)
3. `docs/reports/CORE-004-gemini-conservation-harness.md` and `docs/reports/CORE-005-gemini-baseline-smoke-test.md` (§5 lists the harness gaps)
4. `src/ccis_sim/core/models.py` (`Battery`, `HourlyRecord`) and `src/ccis_sim/core/verification.py`, read directly
5. `tests/fixtures/README.md`

## Why this prompt exists
CORE-004 and CORE-005 were reviewed and are functionally sound, but the review found one regression and several gaps that should be closed before four Phase 2 tracks build on this foundation. The review worked from patches and reports, so verify each claim against the live repo first.

## Part A: Repo hygiene (process; no functional code)
1. **Restore the deleted report.** The CORE-005 patch contains `deleted file: docs/reports/ARCH-002.5-gemini-windows-interop.md` (240 lines), and the report is absent from the latest `master` bundle. Confirm on the live repo, then find the deleting commit (`git log --diff-filter=D --oneline -- docs/reports/ARCH-002.5-gemini-windows-interop.md`) and restore the file from its parent commit. Do not rewrite it.
2. **Find the cause** and state it in your report (stale branch base, a bad `git add -A` after a merge, etc.). Do not amend or force-push anything already on `master`; fix forward with a new commit.
3. **Add the missing ARCH-002.5 row** to `docs/tasks/status.md` (`done`, linked to the restored report). Check the report's own claims against the repo: `.gitattributes`, `scripts/*.ps1`, `scripts/*.bat`, `scripts/README.md`.
4. **Fix the stray blank row** inside the Phase 1 table in `status.md`.
5. **Confirm patch hygiene:** `git ls-files patch/` is empty and `.gitignore` contains `patch/*.patch`.
6. **Addendum to the CORE-005 report** (do not rewrite the original): list the two files it omitted from "Files Touched" (`docs/context/repo-tree.txt` and the ARCH-002.5 deletion) and what was done about each.
7. Regenerate `docs/context/repo-tree.txt` so it reflects the restored report.

## Part B: Verification-harness gaps (`src/ccis_sim/core/verification.py`)
Reserved decision: **[D-24]**. Implement each item with a dedicated failing-case test.

1. **SoC continuity.** Add `ViolationType.SOC_CONTINUITY`. For consecutive records, check
   `SoC_t = SoC_{t-1} + η_chg·charge_t − discharge_t/η_dis` within a documented tolerance.
   - Take the efficiency convention from `Battery` if it already defines one. Otherwise, split the [D-09] 92% round-trip efficiency symmetrically (`η = √0.92` per direction) and record that choice in [D-24].
   - Charge and discharge are AC-side flows (the same quantities the hourly energy balance uses), so losses appear only in SoC. State this in the docstring.
   - The first record has no predecessor: accept an optional `initial_soc_kwh` argument and skip the check if it is omitted.
   - Skip the check when battery capacity is 0 (the CORE-005 baseline).
   - Update `create_golden_scenario()` to apply efficiency so it stays exactly valid. Residual must remain 0.000000 kWh. Update `tests/fixtures/README.md` accordingly.
2. **Non-finite values.** Add `ViolationType.NON_FINITE_VALUE`. Any NaN or ±inf in any numeric `HourlyRecord` field is a violation in every checker. First read `HourlyRecord`'s own validation; if it already rejects non-finite values, say so, keep a harness-level guard anyway, and test with `object.__setattr__` on a frozen record or an equivalent route.
3. **Sub-flow decompositions.** Add checks, each with its own `ViolationType`, that
   - `solar_generation = solar_to_demand + solar_to_battery + solar_curtailed`
   - `demand_gross = demand_served + unserved_load`
   using the hourly tolerance.
4. **Signed residual.** Add a `signed_residual_kwh` property to `HourlyRecord` (in = solar + grid + battery discharge; out = served + battery charge + curtailed; signed = in − out) and make the cumulative check use it. **Do not change `energy_balance_residual_kwh` or `is_energy_conserved()`**; existing behaviour and tests must be unchanged. This is the only permitted `models.py` edit.
5. **Reconcile D-09 and D-21** in [D-24]: the 10% floor is non-discretionary during grid-connected operation; the D-21 emergency drawdown override applies only when `allow_emergency_drawdown=True` during an active outage with `active_load_tier < 3`. Say how this relates to the D-17 emergency reserve. The decision log is append-only: do not edit D-09 or D-21.

## Part C: D-22 disclosure addendum
The decision log is append-only (compare how [D-19] corrected [D-16]), so record this as a new entry, **[D-23]**, amending [D-22]:
1. Report the **uncalibrated** baseline annual kWh and EUI (calibration multiplier set to 1.0), so the size of the 1.2286 correction is visible.
2. Document the hardcoded `0.35` cooling-duty factor in `compute_placeholder_demand` (what it represents and why that value). Promote it to a named, documented constant in `baseline.py`.
3. State that the 159.41 kWh/m²·yr match is by construction (same target as the CORE-003 mock bills) and is **not** independent validation.
4. State that the 124.44 kW peak is scaled by the same calibration factor and has no independent check, so it is provisional until DEM-001/002 replace the placeholder.
5. Note that the 2016 vs 2019 sensitivity is weak (+0.89% peak, -0.07% annual) because of the placeholder's gentle cooling response, and must not be cited as a climate finding.
No change to the committed numbers or to the baseline tests' expected values.

## What NOT to Touch
- No changes to baseline demand logic or calibration beyond naming the 0.35 constant (behaviour must be bit-identical; the committed headline test must still pass unchanged).
- No dispatch, solar, battery or outage models; no Phase 2 work.
- No edits to existing decision-log entries.

## Verification & Acceptance Criteria
- [ ] `ARCH-002.5` report restored with its original content; status row present.
- [ ] `git ls-files patch/` empty; `.gitignore` rule present.
- [ ] Every new harness check has a test that fails on a deliberately broken series and passes on the golden scenario.
- [ ] CORE-004's existing 12 tests and CORE-005's 8 tests pass unmodified (golden-scenario-dependent assertions may change only if the efficiency update requires it; list any such change explicitly).
- [ ] Full `pytest -v` green; paste the real output and the new total.
- [ ] `./scripts/validate-report.py --all` passes.
- [ ] The report lists **every** file touched, including `repo-tree.txt`, fixtures and docs.

## Reserved Decision IDs
- **[D-23]**: D-22 disclosure addendum (Part C).
- **[D-24]**: SoC continuity convention, non-finite and sub-flow checks, D-09/D-21 reconciliation (Part B).
If another non-trivial choice arises, report it rather than deciding silently.

## Output & Reporting Instructions
1. Commit on your task branch in logical commits: `fix(CORE-004.5): ...`. Never amend or rewrite commits on `master`.
2. Generate `patch/CORE-004.5-gemini-phase1-closeout.patch` with `git diff <base>..HEAD`; the file is gitignored, so do not `git add -f` it.
3. Report: `docs/reports/CORE-004.5-gemini-phase1-closeout.md` per `docs/reports/TASK-TEMPLATE.md`, with real command output.
4. Update `docs/tasks/status.md` (add a `CORE-004.5` row under the CORE-004 block) and append [D-23], [D-24].
5. Validate: `./scripts/validate-report.py docs/reports/CORE-004.5-gemini-phase1-closeout.md`.
6. Run `./scripts/apc-bundle.sh core` (or the `.ps1` equivalent) after docs change.
7. Report back: executive summary, test results, patch path, unified diff, branch and worktree path. Do not merge or delete the worktree.
