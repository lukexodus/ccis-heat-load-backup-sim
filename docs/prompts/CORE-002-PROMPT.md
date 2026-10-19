# STANDALONE PROMPT — CORE-002: NASA POWER Weather Ingestion & Offline CSV Fixture Cache

**Task ID:** CORE-002 (covers CORE-002.1 – CORE-002.5)
**Phase:** 1 — Core Infrastructure & Data Pipelines
**Reserved Decision ID:** [D-14] (only if you must fix a parameter not
already locked — e.g. exact date ranges for "baseline" vs. "hot year"
fixtures; see CORE-002.4)
**Depends on:** ARCH-002 (repo scaffold — done; `src/ccis_sim/demand/` and
`data/fixtures/`, `data/raw/` directories already exist)
**Blocks:** CORE-005 (baseline smoke test needs real/cached weather to run
against)

**Can run in parallel with:** CORE-001, CORE-003 (no shared files other than
`docs/tasks/status.md`, `docs/decisions/decision-log.md` — follow the
"Parallel work and worktrees" section of `AGENTS.md` if running concurrently
with another live agent session)

---

## Before you start

1. Read `AGENTS.md` and `docs/context/complete-context.md` §3 (Data Sources)
   in full if you have not this session.
2. Read `docs/context/conceptual-model.md` §2 (temporal framework — hourly,
   8760 steps/year, PST = UTC+8).
3. Confirm `src/ccis_sim/` currently has no weather-ingestion code anywhere
   (check `core/`, and any stray files) — if you find partial prior work,
   stop and report rather than overwrite.
4. **This task needs network access to NASA POWER's API.** If your
   environment has no outbound network access, say so clearly in your
   report, implement everything you can (parser, sanitizer, tests against
   a hand-built synthetic fixture) and flag the live-fetch step as blocked
   pending network access, rather than fabricating what a real API response
   would contain.

## Objective

Build the weather data pipeline that every downstream demand (DEM-002) and
solar (SOL-001) model depends on, plus commit offline CSV fixtures so the
project can run fully without live network access (`complete-context.md` §3:
"Cache the download as a committed CSV fixture").

## Scope

### CORE-002.1 — NASA POWER API client
- Target coordinates: Batac, Ilocos Norte — **18.06°N, 120.56°E** (confirmed
  in both `complete-context.md` and `conceptual-model.md`; do not
  re-derive or substitute a different coordinate pair).
- Use NASA POWER's daily point API
  (`https://power.larc.nasa.gov/api/temporal/daily/point`) — confirm the
  exact current endpoint and parameter names yourself (don't assume your
  training data's URL is still correct; this is exactly the kind of
  externally-verifiable fact `AGENTS.md` asks you to check rather than
  assume).
- Parameters needed (per `complete-context.md` §3): `T2M`, `T2M_MAX`,
  `T2M_MIN`, `RH2M`, `ALLSKY_SFC_SW_DWN`.
- Community parameter: use `RE` (renewable energy) or `AG` as appropriate —
  verify against the live API docs rather than guessing.
- Date range: 1981–present per spec, but for this task's committed fixtures
  you only need specific years (see CORE-002.4) — don't bulk-download the
  full 40+ year history unless you have a specific reason to.

### CORE-002.2 — Hourly/daily weather parser
- NASA POWER's daily endpoint gives **daily** T2M/RH2M/ALLSKY values, not
  hourly. Since the simulation runs on an **hourly** basis ([D-05]), you
  need a disaggregation strategy to go from daily to hourly — e.g. a diurnal
  sinusoidal temperature profile anchored to T2M_MAX/T2M_MIN, and an
  irradiance profile shaped by solar geometry (sunrise/sunset, zenith angle)
  scaled to match the daily ALLSKY_SFC_SW_DWN total.
- **This disaggregation method is not yet locked by any existing decision.**
  If you pick a specific functional form (e.g. a particular sinusoidal
  temperature model or a particular clear-sky irradiance shape function),
  this is a real architectural choice affecting every downstream model —
  reserve and record it as **[D-14]** in `docs/decisions/decision-log.md`
  with your reasoning. Do not leave this un-recorded; a future session
  re-deriving DEM-002 or SOL-001 needs to know exactly how hourly values
  were synthesized from daily NASA POWER data.
- If NASA POWER's **hourly** endpoint (a separate product,
  `temporal/hourly/point`) turns out to cover Batac with the needed
  parameters, prefer that over disaggregating daily data yourself, and
  record that choice too — it's a materially different and better-justified
  approach if available. Check before assuming it isn't.

### CORE-002.3 — Missing value handling and timezone alignment
- NASA POWER uses `-999` as a missing-value sentinel (not NaN) — filter and
  interpolate these to the conceptual-model's audited standard (document
  your interpolation choice — linear, forward-fill, seasonal climatology
  fallback — in your report).
- NASA POWER timestamps are UTC; the simulation runs in PST (UTC+8) per
  [D-05]. Confirm your conversion direction and off-by-one-day edge cases
  around midnight are tested, not just implemented.

### CORE-002.4 — Committed offline fixtures
- Commit CSV fixtures under `data/fixtures/` for:
  - a **baseline** representative year,
  - at least one **hot year** — the task table names "2016/2019" as
    candidates. Verify from NASA POWER data (or published PAGASA/PSA
    climate records) which of these was actually anomalously hot for Batac
    specifically, rather than assuming both qualify — if your fetch
    confirms one is clearly hotter, say so and consider committing only the
    confirmed one plus a second genuinely distinct year, rather than
    committing two years on faith in the table's placeholder names.
- Keep `data/raw/` for the raw, unprocessed API response (useful for
  reproducibility/debugging) and `data/fixtures/` for the cleaned,
  sanitized, hourly-disaggregated CSV the simulation actually reads.
- Fixture file naming: self-descriptive, e.g.
  `data/fixtures/batac-weather-hourly-<year>.csv`. State your exact naming
  convention in the report so CORE-005 / DEM-002 / SOL-001 know what to
  expect.

### CORE-002.5 — Unit tests
- Weather ingest: sentinel filtering, timezone alignment, disaggregation
  sums back to the original daily total (a conservation-style sanity check:
  the 24 synthesized hourly GHI values for a day should integrate back to
  approximately the source daily ALLSKY_SFC_SW_DWN).
- Psychrometric sanity: RH2M stays within [0, 100]%, T2M within plausible
  tropical bounds, no NaN/sentinel leakage into the final fixture.
- New test file, e.g. `tests/test_weather_ingest.py`.
- Run `pytest -v`, include full output in report.

## Deliverable

- Weather client/parser code, likely under `src/ccis_sim/core/` (shared
  infrastructure) or a new `src/ccis_sim/weather/` subpackage if you judge
  the existing 7 subpackages don't cleanly fit it — if you add a new
  subpackage, note that this deviates from ARCH-002's fixed subpackage list
  and justify it.
- `data/fixtures/*.csv` (processed, hourly) and `data/raw/*.csv` or `.json`
  (raw API responses).
- `tests/test_weather_ingest.py`, green under `pytest -v`.
- Report at `docs/reports/CORE-002-<agent-name>-weather-ingestion.md`.
- Update `docs/tasks/status.md`: CORE-002 and CORE-002.1–.5 rows.
- If you introduce the hourly-disaggregation method or a new subpackage,
  record it under **[D-14]** (and reserve **[D-15]** if a second distinct
  choice arises) in `docs/decisions/decision-log.md`.
- Run `./scripts/validate-report.py` before handoff.

## Explicit non-goals

- No cooling-demand model (that's DEM-002) — this task only produces clean
  weather fixtures, it does not compute building load.
- No solar generation math (that's SOL-001) — irradiance here is a weather
  *input*, not a PV output calculation.
