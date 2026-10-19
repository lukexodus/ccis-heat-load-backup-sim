# STANDALONE PROMPT — ARCH-002.4 FIX-UP (Gap Closure, not new scope)

**Task ID:** ARCH-002.4 (re-opened)
**Type:** Correction / gap closure, Phase 0
**Reserved Decision ID:** none required (no new architectural decision)
**Depends on:** none (docs-only, no code dependency)
**Blocks:** nothing directly, but Phase 0 cannot be honestly closed without it

---

## Why this prompt exists

`docs/tasks/status.md` currently marks `ARCH-002.4` as `done` with the note
"Index 8 research reports in synthesis," crediting it to
`docs/reports/ARCH-002-gemini-repo-scaffolding.md`. On inspection of that
report's actual unified diff, **no `docs/context/research-synthesis.md` file
was ever added** — it is not in the diff, not in the repository, and not
referenced by path anywhere except the status table row and the report's own
prose summary.

`docs/tasks/high-level-tasks.md` explicitly lists this file as a required
ARCH-002 deliverable:

> *Deliverable:* Standard Python structure (`src/ccis_sim/`, `tests/`,
> `data/fixtures/`), `requirements.txt`, working `pytest` baseline, and
> `docs/context/research-synthesis.md`.

So this is a real gap, not a stylistic nitpick: a subtask is marked complete
without its stated artifact existing. Per `AGENTS.md`'s core rule, the repo
is the sole source of truth — the status table's claim does not make the
file real.

**Before doing anything else:** confirm this for yourself. Run
`find . -iname "*research-synthesis*"` and `git log --all --oneline -- docs/context/research-synthesis.md`
(or equivalent) in the actual working repository. If the file turns out to
already exist (e.g. it was added in a commit not captured in the bundle this
prompt was generated from), stop, do not recreate it, and report that the
gap was already closed — note the commit that closed it.

If it is indeed still missing, proceed below.

---

## What "8 research reports" refers to

The report's phrase "Index 8 research reports" is **not independently
substantiated anywhere in the repo** — no such 8 reports are named,
numbered, or linked in `ARCH-002-gemini-repo-scaffolding.md`,
`conceptual-model.md`, or the decision log. The 7 decisions [D-05]–[D-11]
each cite a research basis in prose (e.g. "Validated against empirical field
monitoring study of 103 Philippine rooftop PV installations across Luzon"
for [D-08]), but these are inline claims, not indexed/cited sources with
retrievable references.

Do not invent 8 specific external sources to backfill this claim. Instead:

1. Search the repo (`docs/`, any report files, any prior session notes) for
   whatever research grounding already exists in writing for decisions
   [D-05] through [D-11].
2. Build `docs/context/research-synthesis.md` as an **honest index of what
   actually exists**: one entry per decision area ([D-05] temporal
   resolution, [D-06] building archetype, [D-07] CDD cooling model, [D-08]
   solar PV/NOCT, [D-09] LFP battery, [D-10] load tiers, [D-11] stochastic
   outages), each entry stating the claimed empirical/published basis exactly
   as already recorded in `docs/decisions/decision-log.md`, with a note on
   whether that basis is a real citable source (give full IEEE-format
   citation if you can responsibly produce one) or should be labeled an
   **assumption** per `[D-03]`/`[D-04]`'s "labelled assumption" convention.
3. If you cannot verify a real citation for a given decision's claimed
   source, label it `[ASSUMPTION — uncited]` rather than fabricating a
   plausible-looking reference. Fabricated citations are worse than an
   honest gap; `complete-context.md` §3 already requires "published ranges,
   cited in IEEE format and labelled as assumptions" — the labelling is not
   optional when the citation can't be produced.
4. If, after this search, there are fewer than 8 distinct research threads
   to index, index exactly as many as genuinely exist and say so in your
   report — do not pad the file to hit "8." The number in the old status
   row was never verified against anything; don't let it anchor your output.

---

## Deliverable

- `docs/context/research-synthesis.md`: the index described above.
- Update `docs/tasks/status.md`: ARCH-002.4's row should stay `done` only if
  you're confident the new file genuinely satisfies the roadmap's
  deliverable line; otherwise mark it `needs-review` and say why in your
  report.
- A report file at
  `docs/reports/ARCH-002.4-<agent-name>-research-synthesis-fixup.md`
  following the standard `AGENTS.md` report format, and explicitly stating:
  - that the prior `done` status was found to be unsupported by the repo
    state, and what was missing,
  - how many research threads were actually indexed and why,
  - which entries are real citations vs. `[ASSUMPTION — uncited]`.

## Out of scope for this task

- Do not touch `src/`, `tests/`, `pyproject.toml`, or anything from
  ARCH-002.1–002.3 — those were independently verified (pytest 10/10
  passing against the actual patch content) and are not in question.
- Do not re-open or re-litigate [D-05]–[D-11] themselves. This task indexes
  their existing stated bases; it does not change the decisions.
