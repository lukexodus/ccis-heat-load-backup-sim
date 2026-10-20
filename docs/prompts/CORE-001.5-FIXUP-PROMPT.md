# STANDALONE PROMPT — CORE-001.5 FIX-UP (Gap Closure, not new scope)

**Task ID:** CORE-001.5 (new subtask, correction pass on CORE-001)
**Type:** Correction / decision-recording gap closure
**Reserved Decision ID:** [D-17] (use this one ID to cover both parameters
below unless they genuinely need separate reasoning — your call, but don't
burn two IDs for what's really one "solar array physical siting" decision
if a single entry can cover it cleanly)
**Depends on:** CORE-001 (done — do not redo the dataclasses themselves,
only patch the two issues below)
**Blocks:** nothing hard, but CORE-004 and later BAT-002/SOL-002 tasks will
inherit these fields as if they were already decided; better to close this
before those land.

---

## Why this prompt exists

`CORE-001`'s report states: *"No new decision IDs were reserved or required
for `CORE-001`. Reserved decision IDs D-12 and D-13 remain unused as all
domain parameters and interfaces strictly conform to previously locked
decisions `[D-05]` through `[D-11]`."*

That claim is not accurate. `src/ccis_sim/core/models.py` defines two
numeric defaults with no basis in any existing decision:

1. **`Battery.emergency_reserve_pct: float = 0.20`** — a second reserve
   layer, separate from the `min_soc_pct = 0.10` floor already locked in
   **[D-09]**. [D-09] says nothing about an additional 20% "emergency
   blackout reserve" on top of the 10% min-SoC floor. This is a real
   modeling choice (it materially changes how much usable battery capacity
   the dispatch logic in BAT-001/BAT-002 will see) that was introduced
   without being recorded.
2. **`Building.usable_rooftop_area_m2: float = 1200.0`** — [D-06] locks
   gross floor area (~2,500 m², 18 rooms) but never specifies rooftop area.
   1,200 m² is a plausible but uncited number (roughly half the floor
   area, consistent with a 2-storey building footprint, but that
   derivation isn't written down anywhere).

Per `AGENTS.md`'s core rule, anything not written into the repo's files is
lost the moment the session ends — an unrecorded default silently becomes
unexplainable "ground truth" the next time someone reads `models.py` without
also reading this conversation. Decision IDs are reserved precisely so this
doesn't happen quietly.

**Before doing anything else:** confirm this for yourself. Read
`src/ccis_sim/core/models.py` directly and check both fields' current
default values and docstring comments against `docs/decisions/decision-log.md`
[D-05]–[D-16]. If you find either field already has a decision citation I
missed, or the values have since changed, say so in your report rather than
proceeding on the assumption this prompt is still accurate.

---

## What to do

### 1. `Battery.emergency_reserve_pct`
Decide, deliberately, whether this field should exist at all:
- If the project genuinely wants a configurable "extra" reserve on top of
  the 10% min-SoC floor (e.g. for BAT-002's "configurable emergency outage
  reserve %" subtask, which is explicitly named in `docs/tasks/status.md`
  under `BAT-002.2`) — then this field has a real home, but it belongs to
  BAT-002's scope, not CORE-001's. Either:
  - (a) keep the field in `Battery` since BAT-002 will need somewhere to
    put it, but change its default to something explicitly provisional
    (e.g. document in the docstring/comment that 0.20 is a placeholder
    pending BAT-002's own decision, not a locked value), or
  - (b) remove the field entirely from `CORE-001`'s `Battery` dataclass and
    let `BAT-002` introduce it when that task actually implements the
    configurable reserve logic.
  Pick one. Either is defensible; don't leave it as an unexplained locked
  default.
- Whichever you choose, record **[D-17]** in `docs/decisions/decision-log.md`
  stating: what the field is for, why 20% (or why it's being removed /
  deferred to BAT-002), and that it is distinct from and additional to
  (or not — state clearly) the [D-09] 10% min-SoC floor.

### 2. `Building.usable_rooftop_area_m2`
- Either find and cite a real basis for 1,200 m² (e.g. a reasonable
  footprint-to-floor-area ratio for a 2-storey, ~2,500 m² gross-floor-area
  building, or a specific assumption about available unshaded roof space
  after accounting for stairwells/mechanical equipment), or revise the
  number if your own quick sanity check suggests it's off.
- Label it clearly as `[ASSUMPTION]` in the field's inline comment if no
  stronger citation is available — consistent with the project's existing
  labelling convention (see `docs/context/research-synthesis.md` §§2–3 for
  examples of how other assumptions are tagged).
- Record this under **[D-17]** as well (same entry as above, or split into
  **[D-18]** if you'd rather keep the battery and rooftop-area reasoning in
  separate entries — your call, just don't conflate two different
  justifications under one muddled entry).

### 3. Update the code and tests
- Patch `src/ccis_sim/core/models.py` with whatever change you land on
  (new default value, updated comment, or field removal).
- If you remove `emergency_reserve_pct`, update
  `tests/test_core_models.py` accordingly (check for any test asserting
  on `emergency_reserve_kwh` or the property depending on it) and run
  `pytest -v` to confirm nothing breaks. If you keep it, add or adjust a
  test that documents its provisional status.
- Do not touch any other part of `models.py` — this is a narrow
  correction, not a re-architecture.

## Deliverable

- Updated `src/ccis_sim/core/models.py` (small diff).
- Updated `tests/test_core_models.py` if needed.
- `docs/decisions/decision-log.md`: new entry/entries under **[D-17]**
  (and **[D-18]** only if you split them).
- Report at `docs/reports/CORE-001.5-<agent-name>-decision-gap-fixup.md`
  per the standard `AGENTS.md` format, explicitly stating:
  - that the prior CORE-001 report's "no new decisions needed" claim was
    inaccurate, and why,
  - what you changed for each of the two fields and your reasoning,
  - full `pytest -v` output.
- Update `docs/tasks/status.md`: add a `CORE-001.5` row under the existing
  `CORE-001` block, status `done`, linking the new report.
- Run `./scripts/validate-report.py` before handoff.

## Out of scope

- Do not touch `RoomInventory`, `HourlyRecord`, `OutageEvent`, or any other
  part of `CORE-001`'s deliverable — those were reviewed and are fine as-is.
- Do not implement BAT-002's actual configurable-reserve dispatch logic
  here, even if you choose option (a) above and keep the field — that
  belongs to Phase 2.
