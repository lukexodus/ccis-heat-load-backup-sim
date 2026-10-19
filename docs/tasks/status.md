# Task Status

Live tracker — what is actually done right now, not the long-term plan (the plan lives in `docs/tasks/high-level-tasks.md`). This file changes every time a task's status changes. A new APC instance or local agent should be able to read this file alone and know the exact state of the project without having to reconstruct it from scattered chat logs or report files.

**Status values:**
- `open` — Not yet started.
- `in-progress` — Actively being worked on (note the agent / branch).
- `blocked` — Cannot proceed (state the specific blocking dependency).
- `needs-review` — Implemented by a local agent; waiting for APC / lukexodus review.
- `done` — Completed, verified, and accepted (must link the completed report file).

---

## Phase 0 — Inception & Architecture Lock

Status: **open**

| ID | Task | Status | Notes / Report |
| :--- | :--- | :--- | :--- |
| ARCH-001 | Lock scope, system boundary, entities/state variables, performance measures, decision variables, and the DayState contract | `open` | Outline §1–3 |
| ARCH-002 | Scaffold repo: Python env, `src/`, `tests/`, pytest, requirements.txt | `open` | |

---

## Phase 1 — Core Infrastructure & Contracts

Status: **open**

| ID | Task | Status | Notes / Report |
| :--- | :--- | :--- | :--- |
| CORE-001 | Domain models: Building, SolarArray, Battery, OutageEvent, DayState | `open` | |
| CORE-002 | NASA POWER fetch + cached CSV fixture; equipment audit CSV; synthetic bill generator | `open` | Outline §4 |
| CORE-003 | Energy-balance engine smoke test with no solar and no battery (baseline) | `open` | Exit gate: energy balance holds |

---

## Phase 2 — Parallel Feature Tracks

Status: **open**

| ID | Task | Status | Notes / Report |
| :--- | :--- | :--- | :--- |
| DEM-001 | Demand model: bottom-up load, schedules, temperature response, fit to mock bills | `open` | |
| SOL-001 | Solar output model (E = P × H × PR) + yield plausibility check | `open` | |
| BAT-001 | Battery dispatch: SoC limits, efficiency, outage reserve | `open` | |
| OUT-001 | Outage generator and distribution fitting | `open` | |

---

## Phase 3 — Integration & Verification

Status: **open**

| ID | Task | Status | Notes / Report |
| :--- | :--- | :--- | :--- |
| INT-001 | Monte Carlo runner + scenario grid (weather × solar × battery × outage) | `open` | |
| INT-002 | Decision layer (AHP/weighted scoring) + V&V suite (energy balance, sensitivity, CIs) | `open` | Outline §6–7 |

---

## Phase 4 — Polish, Documentation & Release

Status: **open**

| ID | Task | Status | Notes / Report |
| :--- | :--- | :--- | :--- |
| DOC-001 | Charts with labelled sample outputs, final report (Outline §1–10), program listing, presentation | `open` | |
