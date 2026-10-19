# STANDALONE PROMPT — CORE-003: Equipment Audit Model & Synthetic Mock Bill Generator

**Task ID:** CORE-003 (covers CORE-003.1 – CORE-003.4)
**Phase:** 1 — Core Infrastructure & Data Pipelines
**Reserved Decision ID:** [D-16] (only if you must fix an equipment-count or
wattage assumption not already in [D-06]; most of [D-06]'s content is room
*types* and counts, not individual equipment wattages, so you will likely
need this)
**Depends on:** ARCH-002 (repo scaffold — done)
**Blocks:** CORE-005 (baseline smoke test needs a demand profile to run
against, even in its simplest form)

**Can run in parallel with:** CORE-001, CORE-002 (no shared files other than
`docs/tasks/status.md`, `docs/decisions/decision-log.md`)

---

## Before you start

1. Read `AGENTS.md` and `docs/context/complete-context.md` §3 (Data Sources)
   if you have not this session.
2. Read `docs/decisions/decision-log.md` **[D-06]** carefully — it locks the
   18-room building archetype (2 hyflex smart rooms, 6 lecture rooms, 1 COD
   room, 1 Dean + Secretary office, 2 faculty rooms, 6 computer labs; no
   central server room — telecom/networking is distributed in IDF cabinets
   and office closets). This is ground truth confirmed by the project
   operator — do not substitute a generic university-building equipment
   list without grounding it in this specific room inventory.
3. Check whether `CORE-001` has already landed a `Building` dataclass in
   `src/ccis_sim/core/` by the time you start. If it has, your equipment
   audit model should produce data **consumable by** that dataclass, not a
   competing building representation. If CORE-001 hasn't landed yet (you're
   running in parallel), build your CSV schema and loader independently and
   note in your report that the join point with `CORE-001`'s `Building`
   dataclass still needs to be reconciled by whichever task finishes second
   — do not block on it.

## Objective

Produce the concrete, auditable equipment-and-schedule inventory for the
CCIS building (what's actually plugged in, how many, how many hours/day) and
a synthetic monthly electricity bill generator calibrated against that
inventory — all without any real MMSU billing data, per **[D-03]**'s "no
institutional data requests" constraint.

## Scope

### CORE-003.1 — Equipment audit CSV schema
- Columns at minimum: `item, room_type, count, rated_kw, hours_per_day,
  tier`. The `tier` column should align with the Tier 1/2/3 load
  classification already locked in **[D-10]** (2% life safety, 18%
  operational IT/telecom, 80% comfort AC/general lighting) — every
  equipment row needs an unambiguous tier assignment, since OUT-002's load
  shedding logic will key off this later.
- Store the schema file under `data/fixtures/` (e.g.
  `data/fixtures/equipment-audit-schema.csv` or similar — your call on exact
  naming, document it).

### CORE-003.2 — CCIS archetype fixture
- Populate the schema with a concrete equipment inventory for all 18 rooms
  from **[D-06]**:
  - 2 hyflex smart rooms: AV/smart-classroom equipment (projectors,
    cameras, smart boards, inverter AC).
  - 6 lecture rooms: lighting, fans or non-inverter AC, basic AV.
  - 1 COD room (Chairperson of Department office): office equipment,
    AC.
  - 1 Dean + Secretary office: office equipment, AC, higher-priority
    tier (likely Tier 2 per [D-10]'s mention of "Dean/COD offices" under
    Tier 2 operational continuity).
  - 2 faculty rooms: workstations, AC.
  - 6 computer labs: the highest equipment-density rooms — lab PCs (state
    your assumed PC count per lab and cite a reasonable basis or label it
    an assumption), lab AC (likely higher-capacity given heat load from
    PCs), distributed IDF networking equipment (since there's no central
    server room per [D-06]).
- Every wattage/count assumption not already locked in the decision log
  needs either a citable source (equipment spec sheets, typical PH
  classroom audits) or an explicit `[ASSUMPTION]` label, consistent with
  `complete-context.md` §3's labelling convention. Record your overall
  approach as **[D-16]** in the decision log if it involves a real
  methodological choice (e.g. "we assume split-type inverter ACs at X
  BTU/room based on Y m² room size using Z rule of thumb").
- Total floor area should reconcile with the ~2,500 m² total from [D-06].

### CORE-003.3 — Synthetic monthly bill generator
- Build a function that takes the equipment audit + an occupancy/schedule
  assumption (full implementation of the academic calendar is DEM-001's
  job — here you only need something simple enough to produce a
  plausible monthly kWh total, e.g. a flat weekday/weekend occupancy
  split) and produces 12 synthetic monthly bills with added noise.
- Explicitly label output as synthetic — per `complete-context.md` §3:
  "Clearly labelled synthetic; real bills would be used only for later
  calibration." Do not produce output that could be mistaken for real
  MMSU billing data if it leaked out of context (filenames, headers,
  docstrings should all say "synthetic/mock").

### CORE-003.4 — Plausibility validation against EUI benchmark
- Regional EUI (Energy Use Intensity) benchmark per `status.md`:
  **150–300 kWh/m²·yr**. Compute your synthetic bills' implied annual EUI
  (`total annual kWh ÷ 2,500 m²`) and confirm it falls in this band.
- If your first-pass equipment assumptions produce an EUI outside this
  range, **do not silently force-fit the numbers** — iterate on the
  equipment counts/hours honestly, and if you still can't land in range
  after a genuine attempt, report the discrepancy clearly rather than
  padding or truncating synthetic noise to mask it. A too-convenient
  validation pass is worse than an honestly reported miss.

## Deliverable

- `data/fixtures/equipment-audit-ccis.csv` (or your chosen name) — the full
  18-room inventory.
- Bill generator code under `src/ccis_sim/demand/` (this is squarely
  `demand`'s territory per ARCH-002's subpackage layout).
- `tests/test_equipment_audit.py` and/or `tests/test_mock_bills.py`:
  - schema validation (every row has a valid tier, non-negative kW/hours),
  - EUI plausibility check as an automated test (not just a manual report
    claim — assert the computed EUI falls in [150, 300] kWh/m²·yr, or
    document exactly why it's expected to fall outside and assert that
    narrower, justified range instead).
- Report at `docs/reports/CORE-003-<agent-name>-equipment-mock-bills.md`
  with full unified diff and the actual computed EUI number stated plainly.
- Update `docs/tasks/status.md`: CORE-003 and CORE-003.1–.4 rows.
- Record **[D-16]** (and further IDs if needed) in
  `docs/decisions/decision-log.md` for your equipment-assumption
  methodology.
- Run `./scripts/validate-report.py` before handoff.

## Explicit non-goals

- No academic calendar/schedule engine (holidays, breaks, class timing) —
  that's DEM-001. Your "schedule" here is a simplified stand-in just
  sufficient to generate plausible monthly bills, not the real occupancy
  model.
- No temperature-driven cooling response — that's DEM-002. Your mock bills
  can use a flat or very simple seasonal multiplier, not the CDD model.
