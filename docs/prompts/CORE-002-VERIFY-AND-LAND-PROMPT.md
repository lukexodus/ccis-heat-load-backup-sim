# STANDALONE PROMPT — CORE-002 Verify-and-Land (not a re-implementation)

**Task ID:** CORE-002 (landing pass on the existing re-dispatch submission)
**Type:** Verification + commit/status-sync — the implementation itself
looked sound on review; this task is about confirming that and making the
repository's status tracker reflect reality.
**Reserved Decision ID:** none — [D-20] was already reserved and used by
the submission under review; do not reserve a new one unless your own
verification surfaces something the submission didn't address.
**Depends on:** CORE-001 (done), CORE-003 (done)
**Blocks:** CORE-005 (baseline smoke test needs these fixtures)

---

## Why this prompt exists

A `CORE-002` submission (weather ingestion) was reviewed off its patch and
report content and found to be substantively solid:

- It correctly checked for NASA POWER's native hourly product first (per
  the re-dispatch prompt's preference) and confirmed it covers Batac with
  zero missing values, avoiding unnecessary disaggregation — while still
  building a disaggregation engine as a documented, tested fallback rather
  than silently dropping that capability.
- The raw JSON fixtures (`data/raw/nasa_power_hourly_batac_2019.json`,
  `..._2016.json`) were spot-checked directly: 8,760 hours for 2019 / 8,784
  for leap-year 2016 (correctly including Feb 29 in the raw capture before
  downstream standardization), coordinates matching 18.06°N/120.56°E,
  temperature and irradiance values following a physically plausible
  diurnal curve (trough ~05:00–06:00, peak ~12:00–13:00), and the report's
  stated summary statistics (mean temp 26.44°C, annual GHI 1,900.6
  kWh/m²·yr for 2019; peak temp 36.64°C for 2016) match the raw data
  exactly rather than being invented prose.
- 2016 was chosen as the hot year with a real citation (2015–2016 super El
  Niño event), consistent with what `docs/context/research-synthesis.md`
  §1 already flagged as the strongest hot-year candidate.
- Decision **[D-20]** was recorded, citing the hourly-vs-disaggregation
  choice and the leap-year/timezone handling.

**However:** as of the most recent repository snapshot available at the
time this prompt was written, `docs/tasks/status.md` still shows `CORE-002`
and all of `CORE-002.1`–`.5` as `open`, with no report file for `CORE-002`
present. This means the submission's patch either was never actually
applied/committed, or was applied in a working tree that was never merged
back. Per `AGENTS.md`, status.md — not any prior chat, review, or patch
file — is the authority on what's actually done, so until it says `done`
with a linked report, treat this work as **not yet landed**, however good
it looked on paper.

---

## What to do

1. **Check the actual current repository state first**, not this prompt's
   description of a prior review. Run `find . -iname "*weather*"` under
   `src/` and `data/`, check `docs/tasks/status.md`'s CORE-002 rows, and
   check `git log --oneline -- src/ccis_sim/weather/` (or equivalent) to
   see what's really there right now. If a later commit already landed
   this work and updated status.md since this prompt was written, stop
   here and report that — don't redo work that's already in.

2. **If the weather code genuinely isn't in the working tree yet:**
   apply the submission's changes (the files are:
   `src/ccis_sim/weather/{__init__,client,disaggregator,loader,parser,sanitizer}.py`,
   `src/ccis_sim/core/weather.py`, `data/fixtures/batac-weather-hourly-{2016,2019}.csv`,
   `data/raw/nasa_power_{daily,hourly}_batac_{2016,2019}.json`,
   `tests/test_weather_ingest.py`). Do not re-derive this code from
   scratch — re-implementing from the re-dispatch prompt a second time
   would duplicate already-reviewed, working code. If you cannot locate the
   actual submission content (e.g. it only exists as a patch file handed to
   you out-of-band, not in the repo), apply that patch directly.

3. **Re-run the full test suite yourself** (`pytest -v`, the whole suite,
   not just the new weather tests) and confirm the claimed "77 tests, 100%
   green" figure independently. If your count differs, report the actual
   number — don't restate the prior claim without checking.

4. **Spot-check at least one more statistical claim** beyond what's
   described above, to add an independent data point rather than only
   re-confirming what was already checked: for example, verify the 2016
   fixture's claimed "25 days ≥34°C, 11 days ≥35°C" by actually computing
   daily maxima from the committed hourly CSV, or verify the timezone
   conversion logic produces solar noon (peak GHI) at or near hour 12 PST
   for a clear-sky day.

5. **If everything checks out:** update `docs/tasks/status.md` so
   `CORE-002` and `CORE-002.1`–`.5` show `done`, linking a report at
   `docs/reports/CORE-002-<agent-name>-weather-ingestion.md` (use the
   submission's own report content if it's accurate, or write a fresh one
   if you had to reconstruct/reapply the work — either way, the report
   must reflect what you yourself verified, not just restate the prior
   claim).

6. **If something doesn't check out** (tests fail, a statistic doesn't
   match, the raw data looks fabricated rather than fetched, etc.): do not
   mark it `done`. Mark the affected subtask(s) `needs-review`, describe
   exactly what failed to verify, and stop there — do not attempt to
   silently patch over a discrepancy you find without recording it.

## Deliverable

- Working `src/ccis_sim/weather/` subpackage and `data/fixtures/` /
  `data/raw/` weather content, actually present in the repository (not just
  described in a patch file sitting outside it).
- `docs/tasks/status.md` updated to match reality — `done` only for what
  you've personally re-verified.
- Report at `docs/reports/CORE-002-<agent-name>-weather-ingestion.md`
  (overwrite/supersede a prior draft if one already exists at that path and
  was never actually linked from status.md — note in your report if you're
  doing this and why).
- Run `./scripts/validate-report.py` before handoff.

## Out of scope

- Do not touch `CORE-001`, `CORE-003`, or their fix-ups — unrelated.
- Do not start `CORE-004` or `CORE-005` here even if this lands cleanly —
  separate dispatch.
