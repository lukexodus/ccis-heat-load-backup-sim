# STANDALONE PROMPT — CORE-002: NASA POWER Weather Ingestion & Offline CSV Fixture Cache (RE-DISPATCH)

**Task ID:** CORE-002 (covers CORE-002.1 – CORE-002.5)
**Phase:** 1 — Core Infrastructure & Data Pipelines
**Reserved Decision ID:** [D-20] (for the hourly-disaggregation method or
hourly-API choice — see CORE-002.2; [D-14] was reserved for this in an
earlier prompt but was never used or recorded, so this dispatch reserves a
fresh ID rather than assume [D-14] is still "yours" — if you find [D-14] has
since been claimed by something else, use [D-20] without raising a conflict;
if [D-14] is confirmed still unused, you may use it instead and say so)
**Depends on:** ARCH-002 (done)
**Blocks:** CORE-005 (baseline smoke test needs real/cached weather)

**Can run in parallel with:** nothing currently in-progress — `CORE-001` and
`CORE-003` are both `done`. If `CORE-001.5-FIXUP` or `CORE-003.5-FIXUP` are
running concurrently, they touch `src/ccis_sim/core/` and
`data/fixtures/equipment-*.csv` respectively — disjoint from this task's
files, so no conflict, but follow `AGENTS.md`'s worktree rules for shared
docs (`status.md`, `decision-log.md`) regardless.

---

## Why this is a re-dispatch

A prior attempt at `CORE-002` ("weather-ingestion") was reported but never
actually landed: `docs/tasks/status.md` in the current repository state
still shows `CORE-002` and all of `CORE-002.1`–`.5` as `open`. Do not assume
any prior work exists. Start from a clean read of the repo.

**Before doing anything else:** run `find . -path ./node_modules -prune -o
-iname "*weather*" -print` and check `src/ccis_sim/` for any existing
weather-related code or `data/fixtures/`/`data/raw/` content. If you find
partial prior work (e.g. stray files from an earlier, abandoned attempt),
do not silently build on top of it without checking it's sound — note what
you found in your report either way. If the directories are genuinely
empty of weather content, proceed as a fresh implementation.

**One specific thing to avoid, observed in a prior rejected submission:**
do not commit the standalone prompt file itself, or any `.patch` file, into
the repository as a tracked artifact (e.g. a `diff --git a/patch/...`
entry). Prompts belong in `docs/prompts/<TASK-ID>-PROMPT.md` per
`AGENTS.md`'s archiving convention if you want to preserve them; patch
files are an output format for reporting your diff back, not a repo
artifact to commit.

---

## Before you start

1. Read `AGENTS.md` and `docs/context/complete-context.md` §3 (Data
   Sources) in full if you have not this session.
2. Read `docs/context/conceptual-model.md` §2 (temporal framework — hourly,
   8760 steps/year, PST = UTC+8).
3. Read `docs/context/research-synthesis.md` §1 (Geographic & Meteorological
   Baseline) — this now exists and has real content worth using directly:
   it already states NASA POWER's resolution (MERRA-2 meteorology
   0.5°×0.625°, CERES solar 1.0°×1.0°), that NASA POWER offers both daily
   (1981–present) **and hourly (2001–present)** products, the `-999.0`
   missing-value sentinel, and that timestamps default to LST and must be
   converted to PST (UTC+8). It also flags ERA5/ERA5-Land via Open-Meteo as
   an alternative source with tropical temperature agreement typically
   <1.0°C vs MERRA-2 — useful context if NASA POWER's hourly product turns
   out to have gaps or access issues for this location.
4. Confirm `src/ccis_sim/core/models.py` exists (it should, from `CORE-001`)
   — you are not re-implementing `HourlyRecord` or `Building`; you are
   producing the weather inputs those models and later tasks will consume.

## Objective

Build the weather data pipeline every downstream demand (DEM-002) and solar
(SOL-001) model depends on, with offline CSV fixtures committed so the
project runs without live network access.

## Scope

### CORE-002.1 — NASA POWER API client
- Target coordinates: Batac, Ilocos Norte — **18.06°N, 120.56°E**. Do not
  substitute a different coordinate pair.
- Per `research-synthesis.md` §1, NASA POWER has a genuine **hourly**
  product (2001–present), not just daily. **Prefer the hourly endpoint
  over daily-then-disaggregate** if it actually covers this location with
  the needed parameters — check this directly rather than assuming the
  daily-only path from an earlier draft of this task's instructions.
  Verify the exact current endpoint and parameter names yourself (don't
  trust a remembered URL).
- Parameters needed: `T2M`, `T2M_MAX`, `T2M_MIN`, `RH2M`,
  `ALLSKY_SFC_SW_DWN` (daily product) or their hourly equivalents.
- Verify which "community" parameter set (`RE`, `AG`, etc.) actually
  exposes these fields for the hourly endpoint — don't assume it's the same
  as the daily one.

### CORE-002.2 — Hourly weather parser
- **If the hourly NASA POWER product works for Batac:** use it directly.
  Record this as **[D-20]**: "NASA POWER's native hourly product
  (2001–present) was confirmed to cover Batac with the required
  parameters; no daily-to-hourly disaggregation was needed." This is a
  simpler, better-justified path than synthesizing hourly data — prefer it
  if available.
- **If the hourly product has gaps, missing parameters, or doesn't cover
  this location:** fall back to daily data plus a disaggregation method
  (diurnal sinusoidal temperature profile anchored to T2M_MAX/T2M_MIN, an
  irradiance profile shaped by solar geometry scaled to match the daily
  ALLSKY_SFC_SW_DWN total). In this case, record the specific functional
  form you chose as **[D-20]**, since it's a real modeling choice every
  downstream task inherits.
- Either way, do not leave this undocumented — a future session rebuilding
  DEM-002 or SOL-001 needs to know exactly how the hourly weather series
  was produced.

### CORE-002.3 — Missing value handling and timezone alignment
- Filter/interpolate the `-999` sentinel (confirmed in
  `research-synthesis.md` §1) — document your interpolation choice (linear,
  forward-fill, seasonal climatology fallback) in your report.
- NASA POWER timestamps default to **LST** per `research-synthesis.md`
  §1 (not UTC as an earlier draft of this task assumed) — confirm this
  directly against the live API response's actual timestamp convention
  before writing the conversion logic, since getting this backwards would
  silently shift every hourly record by a fixed offset. Convert to PST
  (UTC+8) and test the conversion explicitly, including midnight
  boundary cases.

### CORE-002.4 — Committed offline fixtures
- Commit CSV fixtures under `data/fixtures/` for a **baseline** year and at
  least one **hot year**. Verify from the actual NASA POWER data (or
  published PAGASA/PSA climate records) which candidate year(s) were
  genuinely anomalously hot for Batac specifically — `research-synthesis.md`
  §1 names 2015–2016 and 2019 as strong El Niño years with suppressed cloud
  cover, which is a better-grounded starting point than guessing blind.
  Don't commit a "hot year" fixture without confirming it actually was one.
- Keep `data/raw/` for unprocessed API responses, `data/fixtures/` for the
  cleaned, sanitized, hourly CSV the simulation reads.
- Naming convention: self-descriptive, e.g.
  `data/fixtures/batac-weather-hourly-<year>.csv`. State it clearly in
  your report.

### CORE-002.5 — Unit tests
- Sentinel filtering, timezone alignment correctness (including an
  explicit test of the midnight boundary), and — only if you end up using
  the disaggregation path — a conservation-style check that synthesized
  hourly GHI integrates back to the source daily total.
- RH2M within [0, 100]%, T2M within plausible tropical bounds, no
  NaN/sentinel leakage into the final fixture.
- New test file: `tests/test_weather_ingest.py`.
- Run `pytest -v` (the full suite, not just your new file) and include full
  output in your report.

## Deliverable

- Weather client/parser code under `src/ccis_sim/core/` or a new
  `src/ccis_sim/weather/` subpackage (if you add a new subpackage, note
  that this deviates from ARCH-002's fixed 7-subpackage list and justify
  it briefly).
- `data/fixtures/*.csv` (processed) and `data/raw/*` (raw API responses).
- `tests/test_weather_ingest.py`, green under `pytest -v`.
- Report at `docs/reports/CORE-002-<agent-name>-weather-ingestion.md`,
  containing the **actual** `pytest -v` output you ran, not a
  representative/paraphrased excerpt.
- Update `docs/tasks/status.md`: CORE-002 and CORE-002.1–.5 rows.
- Record **[D-20]** in `docs/decisions/decision-log.md` per CORE-002.2
  above.
- Run `./scripts/validate-report.py` before handoff.

## If you have no network access

Say so clearly and early in your report. Implement everything you can
(parser, sanitizer, timezone/sentinel logic, tests against a small
hand-built synthetic fixture standing in for a real API response) and flag
the live-fetch and fixture-commit steps as blocked pending network access.
Do not fabricate what a real NASA POWER response would contain in order to
make the task look complete — an honest partial submission is far more
useful than invented data silently presented as fetched.

## Explicit non-goals

- No cooling-demand model (DEM-002) — this task only produces weather
  fixtures, not building load.
- No solar generation math (SOL-001) — irradiance here is a weather input.
