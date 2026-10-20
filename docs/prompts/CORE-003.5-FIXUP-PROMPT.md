# STANDALONE PROMPT — CORE-003.5 FIX-UP (Gap Closure, not new scope)

**Task ID:** CORE-003.5 (new subtask, correction pass on CORE-003)
**Type:** Correction / numeric reconciliation
**Reserved Decision ID:** none required — this does not change any decision,
it corrects a reporting error about an already-locked one. If your
investigation finds the underlying equipment list itself needs to change
(not just the write-up), then reserve and use **[D-19]** to supersede
[D-16] per the decision log's append-only convention.
**Depends on:** CORE-003 (done — the CSV fixtures and generator code are
not in question, only the numbers written about them)
**Blocks:** nothing hard, but every future task that cites "140 kW total
connected load" or the Tier 2/Tier 3 split from [D-16] will be citing a
number that doesn't match the actual committed fixture — better to close
this before DEM-001/DEM-002/OUT-002 start consuming it.

---

## Why this prompt exists

`docs/decisions/decision-log.md` **[D-16]** states:

> "...a bottom-up equipment audit of **140.0 kW** total connected capacity
> across 38 distinct equipment categories... Tier 1 life safety (**1.21 kW**,
> ~1%)... Tier 2 operational continuity (**17.5 kW**, ~12%)... Tier 3
> comfort cooling & sheddable loads (**121.3 kW**, ~87%)..."

Computing directly from the actual committed
`data/fixtures/equipment-audit-ccis.csv` (summing `count × rated_kw` per
row, grouped by `tier`, per that file's own schema definition in
`data/fixtures/equipment-audit-schema.csv`) gives different numbers:

| | Decision log [D-16] says | Actual CSV computes to |
|---|---|---|
| Total connected | 140.0 kW | **147.80 kW** |
| Tier 1 | 1.21 kW (~1%) | 1.21 kW (~0.8%) — matches |
| Tier 2 | 17.5 kW (~12%) | **15.36 kW (~10.4%)** |
| Tier 3 | 121.3 kW (~87%) | **131.23 kW (~88.8%)** |

Tier 1 is consistent; Tier 2 and Tier 3 (and the total) are not. This
doesn't break anything functionally — `tests/test_equipment_audit.py`'s
tier-percentage assertions use wide bounds (roughly 0.5–3.0% / 8.0–22.0% /
75.0–90.0%) that the real numbers still satisfy — but the prose in both the
task report and the decision log describes a fixture that isn't quite the
one actually committed. That's exactly the kind of drift `AGENTS.md` asks
agents to catch rather than silently work around.

**Before doing anything else:** confirm this for yourself rather than
trusting this prompt's numbers either. Read
`data/fixtures/equipment-audit-ccis.csv` directly, sum `count × rated_kw`
per row (grouped by `tier`), and compare against both [D-16]'s text and
whatever `SyntheticBillGenerator`/`EquipmentAudit.total_connected_kw()`
actually returns when run live (`src/ccis_sim/demand/equipment.py`,
`mock_bills.py`). If your own computation differs from the table above,
trust your computation and report what you actually found — this prompt's
table is a starting lead, not ground truth.

---

## What to do

1. **Determine the source of the discrepancy.** Most likely explanations,
   in rough order of likelihood — check each:
   - The report/decision-log prose was computed from an earlier draft of
     the equipment list that was later edited (rows added/changed/removed)
     without re-running the totals. Check if `EquipmentAudit.total_connected_kw()`
     and `.tier_breakdown()` (or equivalents) were actually invoked and their
     live output pasted into the report, versus hand-typed/estimated numbers.
   - A unit or arithmetic slip when summarizing by hand (e.g. missing a row,
     double-counting, or mis-transcribing one `rated_kw` value).
   - The schema's semantics were misread at some point (e.g. treating
     `rated_kw` as a group total rather than per-unit) — though the schema
     file itself (`equipment-audit-schema.csv`) is unambiguous on this
     point, so check whether an intermediate calculation elsewhere in the
     codebase has the same misreading baked in.
2. **Fix the actual error, wherever it is:**
   - If the CSV is correct and the prose is wrong: update [D-16]'s text to
     the real, freshly-recomputed numbers. Since the decision log is
     append-only, add a new entry **[D-19]** that explicitly says
     "corrects the connected-load and tier-percentage figures stated in
     [D-16]; the underlying equipment list, tiering, and EUI conclusion are
     unchanged — only the summary numbers were wrong" (do not edit or
     delete [D-16] itself).
   - If, on investigation, the CSV itself has an error (e.g. a row that
     doesn't belong, or a count/rating that's clearly wrong relative to the
     `[ASSUMPTION]` note describing it), fix the CSV and recompute
     everything downstream (tier breakdown, synthetic bills, annual EUI)
     from the corrected fixture, then record that under **[D-19]** instead,
     explaining what was wrong with the original row(s) and why the
     correction is right.
   - Either way, re-verify the EUI conformance claim (150–300 kWh/m²·yr
     band) against the corrected numbers — don't assume the previously
     reported 159.41 kWh/m²·yr still holds if the underlying load changed.
     Recompute it live via the actual bill generator, not by hand.
3. **Update the task report trail.** `docs/tasks/status.md`'s `CORE-003.2`
   row currently says `equipment-audit-ccis.csv (140 kW)` — update this to
   the corrected figure.
4. **Re-run the full equipment/bills test suite** (`pytest -v` on
   `tests/test_equipment_audit.py` and `tests/test_mock_bills.py` at
   minimum, plus the full suite for a regression check) and include the
   output in your report.

## Deliverable

- Either an updated `docs/decisions/decision-log.md` entry **[D-19]**
  (prose-only correction) or an updated
  `data/fixtures/equipment-audit-ccis.csv` plus **[D-19]** explaining the
  fixture-level correction, depending on what you find.
- Updated `docs/tasks/status.md`: add a `CORE-003.5` row under the existing
  `CORE-003` block, status `done`, linking the new report, with the
  corrected kW figure in the notes column.
- Report at `docs/reports/CORE-003.5-<agent-name>-equipment-totals-fixup.md`
  per the standard `AGENTS.md` format, explicitly stating:
  - the actual, freshly-computed total connected kW and tier breakdown,
    shown with the computation (not just asserted),
  - what caused the original discrepancy,
  - the re-verified annual EUI figure and whether it still conforms to the
    150–300 kWh/m²·yr band,
  - full `pytest -v` output.
- Run `./scripts/validate-report.py` before handoff.

## Out of scope

- Do not change the equipment *categories*, room assignments, or tier
  classifications unless you find a specific row is genuinely wrong (not
  just that the summary math was off). The engineering content of the
  audit was reviewed and found sound — this task is about reconciling
  stated totals with committed data, not re-auditing the building.
- Do not touch `src/ccis_sim/core/` — unrelated to this task
  (see `CORE-001.5-FIXUP` for that correction).
