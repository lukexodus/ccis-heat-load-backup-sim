# APC Handoff #4 — Post-DEC-003.3 (2026-10-26)

**Audience:** the APC AI. No filesystem access assumed; this file records verified state at
commit `b38af77` on branch `task/DEC-003.3`.
**Supersedes:** `docs/context/apc-handoff-2026-10-26.md` (Handoff #3), which ends at `master` `6efa69f`.

---

## 1. Where the work is

| Ref | Commit | State |
| :-- | :-- | :-- |
| `master` | `6efa69f` | Unchanged since Handoff #3. **Not merged.** |
| `task/DOC-FIX-001` | `cdc77cf` | Complete, unmerged |
| `task/DEC-003.3` | `b38af77` | Complete, unmerged; **stacked on `task/DOC-FIX-001`** |

Merge order: DOC-FIX-001 first, then DEC-003.3. Merging DEC-003.3 alone also brings DOC-FIX-001.

Two commits live only on `task/DEC-003.3`:
- `cdc77cf` — DOC-FIX-001 (DEC-001 report reconstruction, status fixes, five patch artifacts, hypothesis tests, heat-effect numbers, [D-40]).
- `b38af77` — DEC-003.3 (engineering report, `×100.2` fix, regenerated `results/recommendation.md`, status rows).

A later `docs(context)` commit adds this handoff and a regenerated `repo-tree.txt`.

## 2. What changed in DEC-003.3

- `docs/paper/CCIS-engineering-report.md` (356 lines) — final engineering report, checked
  line-by-line against result artifacts. Corrected bottom-up reliability from 90.5% to
  **90.34%** and fixed the temperature-band confound explanation.
- `scripts/run_decision_pipeline.py:270` — reliability printed as `×100.2`; now `×100`.
- `results/recommendation.md` — regenerated; only difference is `90.5%` → `90.3%`.
- `docs/tasks/status.md` — DEC-003 and DEC-003.3 → `done`.
- `docs/reports/DEC-003.3-claude-code-engineering-report.md` — task report with full diff.

Verified: `290 passed, 17 warnings in 64.28s` on `task/DEC-003.3`; `281 passed in 58.56s`
on `master`; `validate-report.py --all` passes.

## 3. Decision log

Current through **[D-40]**. **D-41 is free.** No new decision was needed for DEC-003.3: the
90.3% correction executes the existing [D-38] rule unchanged.

## 4. Open items for the APC

1. **Merge not done.** Operator has not merged DOC-FIX-001 or DEC-003.3. `master` is still `6efa69f`.
2. **`scripts/validate-report.py` dirty in the main checkout.** 42-line uncommitted diff
   (27+/15−): alternative section-name sets, subtask base-ID fallback, optional patch-file
   check. Not authored in this session; not committed, stashed, or reverted. Needs operator decision.
3. **Bundle security guard** forbids `results/` paths. A rebuilt bundle can carry copies under
   `docs/paper/_bundle_results/` or an operator-approved exception.
4. **References unverified.** §9 of the engineering report still needs primary sources for
   the EUI band, 1,298 kWh/kWp, outage parameters, cooling slope, and battery parameters.
5. **Figures** were verified structurally (filenames + docstrings) but not visually inspected.
6. **Program listing scope** unknown: full source is 42 files / 9,295 lines; Appendix C points
   to `results/program_listing_index.md`.
7. **Still needed from lukexodus:** deadline, presentation date, team members and track
   ownership, report format (Markdown/Word/PDF), slide deck yes/no.
