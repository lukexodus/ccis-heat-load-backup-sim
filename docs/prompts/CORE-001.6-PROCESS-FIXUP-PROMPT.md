# STANDALONE PROMPT — CORE-001.6 (Process Correction, not code)

**Task ID:** CORE-001.6 (new subtask, process/reporting correction)
**Type:** Reporting hygiene fix — no functional code is wrong here
**Reserved Decision ID:** none
**Depends on:** CORE-001.5 (done — verified functionally correct; this
prompt only addresses how it was reported and two incidental repo additions
that came with it)
**Blocks:** nothing

---

## Why this prompt exists

`CORE-001.5`'s actual patch was verified and is functionally sound — both
`emergency_reserve_pct` and `usable_rooftop_area_m2` now have real, well-
reasoned decision entries ([D-17], [D-18]), the code changes are minimal and
correct, and `pytest` passes (20/20 on the affected test file, confirmed by
direct re-run). No code fix is needed.

Two things in that submission need a follow-up, both about process rather
than correctness:

### 1. The patch included 8 files never mentioned in its own report
The patch added `docs/misc/M&S Project Ideas.md` and seven
`docs/misc/deep-research-report*.md` files — apparently archival dumps of
the project's original brainstorming document and early deep-research
source material that predates the formal decision log. These look like
genuinely useful provenance artifacts to keep in the repo. **The problem is
not that they were added — it's that the task's own report never mentions
them.** `CORE-001.5`'s "Changes Made" section lists exactly 4 files
(`models.py`, `test_core_models.py`, `decision-log.md`, `status.md`); the
real diff touched 18. A future session reading only the report would have
no idea these files exist or why.

This matters because of `AGENTS.md`'s core rule: the repo is the sole
source of truth, and a report is supposed to be the legible record of what
changed and why. An 18-file diff summarized as a 4-file change is exactly
the kind of silent drift the reporting discipline exists to prevent.

### 2. The patch re-introduced the self-referential `patch/` artifact
`CORE-002`'s re-dispatch prompt explicitly flagged this from a prior
submission and asked agents not to do it: the patch includes a
`diff --git a/patch/CORE-001.5-gemini-decision-gap-fixup.patch
b/patch/CORE-001.5-gemini-decision-gap-fixup.patch` entry — i.e. the task's
own patch file was committed into the repository as a tracked artifact
under a `patch/` directory. This isn't harmful, but it's noise that
shouldn't be there, and it happened again despite being called out once
already.

**Before doing anything else:** confirm both of these against the actual
current repository state yourself — run `find docs/misc -type f` and
`find patch -type f 2>/dev/null` (or equivalent) directly rather than
trusting this prompt's description. If either has already been cleaned up
by a later commit, say so and skip the corresponding step below.

---

## What to do

### For the `docs/misc/` files
Do not delete them — they appear to be genuine, useful provenance (the
original idea pitch and deep-research inputs that grounded [D-05]–[D-11]
before the decision log existed). Instead:
1. Add a short note to `docs/context/complete-context.md` §4 (Project
   Structure & Where Things Live) documenting that `docs/misc/` holds
   pre-ARCH-001 source material (original idea document, raw deep-research
   reports) kept for provenance/traceability, not as live specs — the
   decision log and `conceptual-model.md` are the authoritative versions of
   anything these files originally informed.
2. Spot-check that nothing in `docs/misc/` contradicts a locked decision in
   a way that could mislead a future reader (e.g. the original idea
   document's "Part C: Battery" section describes a simpler battery model
   than what [D-09] eventually locked — that's expected and fine since it's
   explicitly early-draft material, but if you find something in these
   files that could plausibly be mistaken for still-current guidance,
   consider a one-line "superseded by [D-xx]" annotation at the top of that
   file rather than leaving it to be discovered wrong later.)

### For the `patch/` self-inclusion
1. Remove the `patch/CORE-001.5-gemini-decision-gap-fixup.patch` file from
   the repository (`git rm` or equivalent) if it's still present.
2. Do not add it again. Patch files are the *output format* for relaying a
   diff back in a report — they are not a repository artifact.

### Report
- A short report at
  `docs/reports/CORE-001.6-<agent-name>-process-fixup.md`. This does not
  need the full `AGENTS.md` report structure in exhaustive detail (no new
  decisions, no energy-balance verification needed) — a concise summary of
  what was found and what was done is sufficient, but it must explicitly
  list every file touched, including the `docs/misc/` additions'
  provenance note and the `patch/` removal, so this correction doesn't
  itself repeat the under-reporting problem it's fixing.
- Update `docs/tasks/status.md`: add a `CORE-001.6` row under the
  `CORE-001` block, status `done`, linking the new report.

## Out of scope

- Do not touch `models.py`, `test_core_models.py`, or the [D-17]/[D-18]
  decision entries — those are correct and verified.
- Do not re-litigate CORE-002 or CORE-003's status here.
