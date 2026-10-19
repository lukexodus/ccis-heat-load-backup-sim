# APC Handoff — CCIS Heat, Load and Backup Power Simulation

Handoff #1 · Written 2026-10-19 (≈21:10 local) · Repo: `ccis-heat-load-backup-sim` · Bundle: profile `core`, commit `04a2b70`, 2026-10-19T12:53:43Z

Save as `docs/context/apc-handoff-2026-10-19.md`. Paste this file as the first message of the new APC session, with the latest `docs/tasks/status.md`, `docs/decisions/decision-log.md` and `docs/context/complete-context.md` (or an `apc-bundle-core-*.tar.gz`).

---

## 0. Role and operating rules

You are the APC AI ("Analyzer, Planner, Controller") for **CCIS Heat, Load and Backup Power Simulation**. You have NO filesystem access. You coordinate through the human operator (`lukexodus` in repo docs), who relays work to local coding agents (Claude Code, Gemini CLI, opencode, Cursor) with full filesystem and CLI access.

1. **Repo is SSOT.** If this handoff conflicts with files on disk, the files win. Anything marked *unverified* below must be checked against the repo before use.
2. **Output = STANDALONE PROMPTS** pasted verbatim into local agents. Each states: Task ID, files to read, requirements, acceptance criteria, test commands, report path, reserved Decision IDs. Template: `docs/prompts/STANDALONE-PROMPT-TEMPLATE.md`.
3. **Deltas, not full files.** Propose edits as unified diffs or before/after blocks. Review agent work via `git diff`.
4. **You reserve Decision IDs** in task prompts. Settled decisions are never re-litigated. The decision log is append-only; supersede, never edit.
5. **Every task ends with a report** in `docs/reports/` that passes `./scripts/validate-report.py`. Parallel work uses worktrees `task/<TASK-ID>` (`scripts/task-worktree.sh`).
6. **Reading order:** `complete-context.md` → `decision-log.md` → `status.md` → `high-level-tasks.md` → `AGENTS.md`.

## 1. Project definition

**What:** Python Modelling and Simulation (MoSi) course group project (3–4 members, all present at the defense). Models a Batac, Ilocos Norte college building's (CCIS) electricity demand under heat, with rooftop solar PV and battery backup tested through Monte Carlo outage scenarios.

**Deadline:** this week (week of 2026-10-19). Exact deadline and presentation date **unconfirmed**; plan assumes Day 1–5.

**Primary question:** How much does Batac heat raise CCIS electricity use, and how much of that load can solar + battery cover during a heat wave or outage? Final output: one defensible sizing recommendation (e.g. smallest solar+battery combination covering a 12 h outage on a hot day).

**Course deliverable:** Project Outline §1–10: (1) Overview: problem, goal, system boundary; (2) Formulation: system description, modeling objectives, performance measures, decision variables; (3) Conceptual model: entities, state variables and events, assumptions, flowcharts; (4) Data collection and input modeling: sources, distribution fitting; (5) Implementation: tool justification, architecture; (6) V&V; (7) Results: CIs, hypothesis tests, trade-offs, recommendations; (8) Labelled sample outputs; (9) IEEE references; (10) Program listing.

**Course-topic coverage to make explicit in the report:** Monte Carlo and stochastic modeling (Wk 4–8); decision analysis incl. AHP and utility (Wk 10–12); continuous simulation (Wk 13–16); V&V, input/output analysis, scenario setting, optimization (Wk 17–18). Known gap: no DES/ABM component; frame outages as discrete events (arrival, duration, state change).

## 2. Model specification (as locked or proposed so far)

| Element | Specification |
| :--- | :--- |
| Engine | Time-stepped continuous energy balance, daily first, hourly later, wrapped in a Monte Carlo runner |
| Demand | Bottom-up: equipment count × rated kW × schedule hours, plus temperature response (cooling rises above a threshold; lower on breaks and holidays) |
| Solar | E = P_kWp × H_sun × PR, PR ≈ 0.75–0.80 (parameters to be refined from research reports) |
| Battery | Charge from surplus, discharge to cover the gap, SoC limits, round-trip efficiency, outage reserve %. Unserved load = remainder during outage |
| Outages | Discrete events. Exponential inter-arrival, lognormal or Weibull duration. Parameters from published reliability figures or declared assumptions |
| Weather | NASA POWER daily, Batac ≈ 18.06°N, 120.56°E, 1981–present. T2M, T2M_MAX, T2M_MIN, RH2M, ALLSKY_SFC_SW_DWN. `-999` = missing. Cached as committed CSV fixture |
| Scenario grid | Weather (normal, +2 °C, hottest year) × solar (0/50/100/200 kWp) × battery kWh × outage length (4/12/24 h) |
| Performance measures | Annual solar share, self-sufficiency, self-consumption, outage hours fully/partly covered, critical-load hours covered, unserved kWh, minimum SoC |
| Decision variables | Weather scenario, kWp, kWh, outage length, outage reserve %, load-shed tier |
| Decision layer | AHP or weighted scoring over coverage, outage hours covered, cost (cost = labelled assumption) |
| Core interface | One `DayState` / `HourlyRecord`: demand, solar, battery SoC, grid import, unserved load (final columns to be locked in ARCH-001.5) |
| Stack | Python: pandas, numpy, scipy, matplotlib; pytest |
| Units | kWh. Pesos only as labelled assumptions |

## 3. Decisions

| ID | Status | Content |
| :--- | :--- | :--- |
| D-01 | Locked (in repo) | APC + local-agent model, repo as SSOT |
| D-02 | Locked (diff issued; **verify applied**) | Project selected: CCIS Heat, Load and Backup Power, over bunching, flood evacuation, misinformation, informal-settlement fire, delivery dispatch, crowd-crush. Reason: local, defendable, fits continuous simulation + Monte Carlo + V&V |
| D-03 | Locked (diff issued; **verify applied**) | No institutional data requests. Use NASA POWER weather, self-conducted equipment audit, synthetic mock bills. Supersedes the original idea's MMSU bills/meter data plan. Reason: deadline this week |
| D-04 | **Proposed, pending** | Python (pandas, numpy, scipy, matplotlib) + pytest. Pending confirmation that the instructor accepts Python (course text says "R or any modelling and simulation software") |
| D-05 to D-11 | **Reserved for ARCH-001** | Open design decisions. Recommended answers are in `docs/tasks/high-level-tasks.md`, section "Decisions to lock". Operator must confirm before ARCH-001.4 |

Do not issue D-12 or higher without first checking the log for what ARCH-001 has actually written.

## 4. Repo bundle state

Files in bundle (commit `04a2b70`): `AGENTS.md`, `docs/context/{complete-context.md, apc-handoff-template.md, apc-bundle-quickref.md, repo-tree.txt}`, `docs/decisions/decision-log.md`, `docs/tasks/{status.md, high-level-tasks.md}`, `docs/prompts/{STANDALONE-ADOPTION-PROMPT.md, STANDALONE-PROMPT-TEMPLATE.md}`, `docs/reports/TASK-TEMPLATE.md`, `docs/guide/COLLABORATOR-GUIDE.md`, `scripts/{apc-bundle.sh, manage-decisions.py, task-worktree.sh, validate-report.py, README.md}`. No `src/` or `tests/` yet.

**Delta edits issued this session** (as diffs; application to the repo **unverified**):

| File | Change |
| :--- | :--- |
| `docs/prompts/STANDALONE-ADOPTION-PROMPT.md` | Replace `[PROJECT_NAME]` with project name and one-line description |
| `docs/context/complete-context.md` | Fill §1 goal/metrics/constraints, §2 architecture, §3 data contracts, §6 open items (placeholders were still present in the bundle) |
| `docs/decisions/decision-log.md` | Replace D-02 template; append D-03 and D-04 |
| `docs/tasks/status.md`, `docs/tasks/high-level-tasks.md` | Replaced by the generated plan below. Earlier interim diff (CORE-001..003, DEM-001, SOL-001, BAT-001, OUT-001, INT-001/002, DOC-001) is superseded |
| `AGENTS.md`, `repo-tree.txt`, handoff/prompt/task templates | No change needed (regenerate `repo-tree.txt` after scaffolding) |

## 5. Plan (generated this session; SSOT is the repo files)

Scale: 6 phases, 23 high-level tasks, about 100 low-level tasks. One-week schedule, Day 1–5, to be re-based once the deadline is confirmed. IDs: high-level `PREFIX-NNN`; low-level `PREFIX-NNN.n` (unit of work for one local agent). ID prefixes in use: `ARCH`, `CORE`, `DEM`, `SOL`, `BAT`, `OUT`, `INT`, `DEC`, `DOC`.

**Critical path:** ARCH-001 → CORE-004 → CORE-005 → (DEM, SOL, BAT, OUT in parallel) → INT-001 → INT-002 → DEC-001/002 → DOC-001.

**Phase 0 — Scope Lock & Repo Foundation (Day 1)**
- **Exit gate:** conceptual model, interface contract and D-05..D-11 written; `pytest` green on a smoke test; research reports committed.
- **ARCH-001** Lock scope and conceptual model (Outline §1–3). Done when `docs/context/conceptual-model.md` has boundary, entities, states, events, assumptions, performance measures, decision variables and flowchart, and D-05..D-11 are logged. Low-level: .1 boundary + entities (building, PV array, battery, grid connection, outage events); .2 state variables (SoC, grid up/down, hour, temperature) + events (outage start/end, class-period change, SoC at min/max); .3 performance measures + decision variables; .4 record D-05..D-11; .5 interface contract (function signatures, `HourlyRecord` columns); .6 Mermaid logic flowchart exported for report §3.
- **ARCH-002** Scaffold repository (Outline §5). Done when a fresh clone installs and `pytest` passes, and research is indexed.

**Phases 1–5:** foundation/data (CORE-001..005: domain models, NASA POWER fetch + cached fixture, equipment audit CSV, synthetic bill generator, baseline engine smoke test with no solar and no battery, exit gate = energy balance holds); parallel model tracks (DEM, SOL, BAT, OUT); integration (INT-001 Monte Carlo runner + scenario grid; INT-002 V&V suite: energy balance, sensitivity, CIs); decision analysis (DEC-001/002, AHP/weighted scoring); report and presentation (DOC-001: labelled charts, final report §1–10, program listing, presentation, all members present). **The exact phase names, task titles and low-level tasks for CORE-004 onward were generated this session but are not reproduced here: read them from `docs/tasks/status.md` and `high-level-tasks.md`.**

## 6. Research inputs

Eight ChatGPT Deep Research reports were uploaded and read by the previous APC. Topics: (1) solar PV and battery parameters, (2) demand and heat response, (3) outage statistics (SAIFI/SAIDI, typhoon restoration), (4) weather data and hot-year scenario (NASA POWER, PAGASA), (5) validation benchmarks, (6) critical-load definition and load-shedding tiers, (7) AHP and decision-analysis method, (8) Monte Carlo design and input modeling. **Their numeric findings are not carried in this handoff.** Re-read the reports as committed in the repo (ARCH-002 indexes them) before locking any parameter. Every parameter must be tagged sourced vs. assumed, with an IEEE citation.

Further research requested only if a report leaves a parameter unsupported. Prompts for all eight areas already exist; do not regenerate them.

## 7. Blockers and inputs needed

| Item | Blocks | Needed from |
| :--- | :--- | :--- |
| CCIS floor area, floors, usable roof area, rough room/equipment counts, or approval to use a synthetic archetype | CORE-003.2, CORE-003.5, solar/battery grid scale | Team |
| Exact deadline and presentation date | Day plan | Team |
| Team size and track ownership | Task assignment | Team |
| Instructor confirmation that Python is accepted | D-04 | Team / instructor |
| Confirmation of D-05..D-11 | ARCH-001.4 | Team |

## 8. Open questions to the operator (unanswered at handoff)

1. Is `lukexodus` the operator's own handle? It appears in `AGENTS.md`, `complete-context.md`, `status.md` and the handoff template; if not, a replace list is needed.
2. Is the deadline literally this week? If yes, compress to about five days.
3. Apply the issued edits via a patched bundle, or will the operator apply the diffs?
4. Which unfilled `complete-context.md` placeholders remain after the operator applied the §1–3 and §6 diffs (check the file).

## 9. Risks and caveats

- **Validation is weak by construction:** mock bills are generated from the demand model, so matching them proves little. Frame V&V as verification (energy balance, SoC bounds, unit tests, seed reproducibility) + sensitivity analysis + plausibility against published yield and EUI ranges (ASHRAE Guideline 14 metrics only if real data appears).
- **No DES/ABM component.** Frame outages as discrete events in the write-up.
- **Weather grid cell:** NASA POWER cell representativeness for Batac is unconfirmed.
- **Cost figures** are assumptions; the model reports energy, not pesos.
- **Citations:** Deep Research outputs may contain unverified or hallucinated references. Spot-check any source before it enters §9 of the report.

## 10. Activation response (do this first)

1. Confirm the APC role and the SSOT and diff-contract constraints.
2. From `status.md`, state the current phase, which tasks are `open`/`blocked`/`needs-review`/`done`, and which §4 deltas appear applied.
3. State the immediate next action. Default: if D-05..D-11 are unconfirmed, ask the operator to confirm the recommended answers from `high-level-tasks.md`; otherwise emit the standalone prompt for **ARCH-001** with D-05..D-11 reserved, then **ARCH-002** in parallel (separate worktree).
4. Ask only for context that the repo files and this handoff do not already supply.
