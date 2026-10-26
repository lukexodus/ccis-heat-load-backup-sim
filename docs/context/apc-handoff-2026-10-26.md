# APC Handoff — CCIS Heat, Load and Backup Power Simulation

Handoff #3 · Written 2026-10-26 (≈14:55 local) · Repo: `ccis-heat-load-backup-sim` · Master tip at writing: `44f0fb1` · Bundle: profile `core`

Save as `docs/context/apc-handoff-2026-10-26.md`. Paste this file as the first message of the new APC session, accompanied by an `apc-bundle-core-*.tar.gz` (built after this file was committed) or the live contents of `docs/tasks/status.md`, `docs/decisions/decision-log.md`, and `docs/context/complete-context.md`.

---

## 1. Orientation (Copy verbatim into first prompt)

You are the APC AI ("Analyzer, Planner, Controller") for CCIS Heat, Load and Backup Power Simulation. You have NO filesystem access to the project repo. You coordinate by writing standalone prompts that lukexodus relays to local coding agents (Claude Code, Gemini, opencode, Cursor) running on their machine, who DO have filesystem access and report back to you via pasted reports and git diffs.

Read, in this order, before taking any action:

1. `docs/context/complete-context.md` — full project orientation
2. `docs/decisions/decision-log.md` — every past decision and why ([D-01] through [D-39])
3. `docs/tasks/status.md` — live tracker of what is actually done right now
4. This document's Sections 2–5 below — what changed since handoff #2 (2026-10-20)

If lukexodus has pasted current file contents or uploaded an APC bundle archive, inspect those primary artifacts directly before asking for re-pastes.

---

## 2. What Changed This Session

Since handoff #2 (`e1f6a81`, 2026-10-20), **all remaining Phase 2 tracks, Phase 3, and the decision layer through DEC-002 have been implemented, verified, and merged into `master`.**

### Merged task branches

| Task | Merge commit | Scope |
| :--- | :--- | :--- |
| BAT-001 | `1db0799` | Battery dispatch dynamics, SoC tracking, C-rate limits [D-31] |
| BAT-002 | `c469eb2` | Outage reserve, SoC floors, idle losses [D-32] |
| SOL-001 | `23b68be` | Irradiance geometry, NOCT thermal derating [D-29] |
| SOL-002 | `d7d84cd` | Array sizing, inverter clipping, BOS/PR decomposition [D-30] |
| OUT-002 | `a0f0f18` | Priority-based tiered load shedding [D-34] |
| DEM-001 | `18d4b59` | Academic calendar, occupancy, non-cooling demand [D-27] |
| DEM-002 | `c1c5bf9` | Temperature/humidity cooling response [D-28] |
| OUT-001 | `6710ffc` | Stochastic outage sampler and typhoon coupling [D-33] |
| INT-001 | `c674177` | Integrated simulation engine, CLI, DEM-002.4 + SOL-002.4 verification [D-35] |
| INT-002 | `47883b2` (linear) | Monte Carlo scenario grid, convergence, distributions [D-36] |
| INT-003 | `83c3cb0` | Conservation audit, plausibility screening, KPI tables [D-37] |
| DEC-001 / DEC-002 / DEC-003 plots | `2f03669` | AHP weighting, Pareto frontier, sizing recommendation, figures [D-38] |

### Key results now on `master`

- **Test suite:** 281 tests passing (`pytest -q`, 104.79 s, Python 3.14.8, pytest 9.1.1).
- **Conservation:** all 12 audited configurations PASS; max per-hour residual `2.84e-14 kWh`, cumulative `-6.63e-13 kWh`; SoC within bounds; tier conservation PASS.
- **Headline KPIs (2019 normal, seed 0):**
  - Grid-only: 189,142.12 kWh import, EUI 75.74 kWh/m²·yr, peak 95.71 kW.
  - 100 kWp PV + 100 kWh: 58.21% self-sufficiency; 8/8 outage hours T1 and T2 served.
  - 200 kWp PV + 200 kWh: 87.38% self-sufficiency; 8/8 outage hours T1 and T2 served.
- **Recommended sizing (DEC-002, [D-38]):** **200 kWp PV / 150 kWh battery**, cost index 290.0 (`r = 0.6`), classified **DEMAND-DEPENDENT**.
  - Bottom-up demand: 90.5% mean T1+2 outage served (95% CI ±2.61%); 84.9% self-sufficiency; 34.3 kWh mean unserved T1+2.
  - Bill-calibrated demand (~2.10×): 68.4% served (±3.76%); 54.5% self-sufficiency; 321.9 kWh mean unserved.
  - Pre-registered rule required ≥90% BU and ≥80% BC; no candidate met both, so the rule's fallback selected the best achievable case and reports the trade-off.
- **AHP:** λmax = 4.0192, CR = 0.0071; weights Reliability 0.5872, Cost 0.2179, Self-Sufficiency 0.1228, Curtailment 0.0722.
- **Demand discrepancy (by design, not a bug):** uncalibrated bottom-up EUI 75.74 vs synthetic-bill 159.41 kWh/m²·yr; NMBE −57.26%, CV(RMSE) 55.26%. Framed as computational verification + plausibility screening, not empirical validation, per [D-37].
- **Solar yield:** 1,508.74 kWh/kWp vs Luzon benchmark 1,298 (+16.2%), flagged as plausible-but-high.
- **Artifacts:** `results/kpi_tables.md`, `results/recommendation.md`, `results/figures/fig1`–`fig5`, `patch/DEC-001-gemini-decision.patch`.

### Decisions recorded

- [D-27] DEM-001 academic calendar/occupancy/non-cooling demand
- [D-28] DEM-002 cooling response
- [D-29] SOL-001 irradiance geometry and thermal derating
- [D-30] SOL-002 sizing, clipping, PR decomposition
- [D-31] BAT-001 dispatch dynamics and limits
- [D-32] BAT-002 reserve/floor/idle-loss accounting
- [D-33] OUT-001 outage process and typhoon coupling
- [D-34] OUT-002 tiered shedding policy
- [D-35] INT-001 engine architecture, dispatch order, exporters, combined demand/solar verification
- [D-36] INT-002 dual demand scaling, scenario grid, CRN seeds, convergence verdict
- [D-37] INT-003 verification invariants, plausibility framing, KPI tables
- [D-38] DEC-001/002 AHP framework, cost proxy, Pareto formulation, pre-registered recommendation rule
- [D-39] Reserved, unused

### Repository state

- `master` is clean except one pre-existing uncommitted file: `scripts/validate-report.py` (42-line local modification, author unknown, not part of this session's work).
- Seven task worktrees (`BAT-001`, `BAT-002`, `DEC-001`, `DEM-001`, `DEM-002`, `INT-003`, `OUT-001`) and their branches remain for operator audit/cleanup. `DEM-001` and `DEM-002` worktrees carry stale regenerated `docs/context/repo-tree.txt` diffs that are not unmerged work.
- `patch/` is missing artifacts for SOL-001, BAT-001, BAT-002, OUT-001, and INT-003 (see §5).

---

## 3. What's Currently In-Flight (Active / Blocked)

- **No task is `in-progress` or `blocked`.**
- **`DEC-003.3` is `open`:** "Compile comprehensive engineering report markdown" — the course report (Project Outline sections 1–10). Per `docs/prompts/DEC-001-002-PROMPT.md`, the APC writes this, not a local agent.
- All implementation work through DEC-002 is merged; the remaining deliverable is the engineering report itself, plus hygiene fixes listed in §5.

---

## 4. What the New APC Instance Should Do First

1. **Inspect the uploaded `apc-bundle-core-*.tar.gz`** and confirm the state described above. Do not trust this handoff over the files.
2. **Resolve the DEC-001 report gap before writing the final report** (§5 item 1). `status.md` marks DEC-001/DEC-002 `done` and links `docs/reports/DEC-001-gemini-decision.md`, which does not exist. Either dispatch a small documentation fixup (local agent writes a report from `results/recommendation.md`, `src/ccis_sim/decision/*`, `tests/test_decision.py`, and [D-38]) or correct the status rows to point at an existing artifact.
3. **Then write `DEC-003.3`** — the comprehensive engineering report. Use `results/kpi_tables.md`, `results/recommendation.md`, `results/figures/`, `docs/decisions/decision-log.md` [D-01]–[D-38], and the INT-003 framing (verification + plausibility + sensitivity, not empirical validation). Keep the demand-scaling trade-off explicit: the recommendation is demand-dependent, and the bill-calibrated case does not reach the pre-registered 80% threshold.
4. **Dispatch a hygiene fixup** for the status/patch inconsistencies in §5 so the repo is self-consistent at handoff #4.

---

## 5. Unresolved Items & Edge Cases

1. **Missing DEC-001 report.** `docs/tasks/status.md` lines for DEC-001, DEC-002, DEC-003 link `docs/reports/DEC-001-gemini-decision.md`; the file is absent. The DEC-001 work was committed from the worktree without the mandatory report deliverable.
2. **Contradictory DEC-003 row.** Parent row `DEC-003` is marked `done` while `DEC-003.3` is `open`. Parent should be `in-progress`/`open` until the report exists.
3. **Stale phase status lines.** Phase 2, Phase 3, and Phase 4 sections still read `Status: open` even though every child row is `done` (except DEC-003.3).
4. **Missing patch artifacts:** SOL-001, BAT-001, BAT-002, OUT-001, INT-003 have reports but no `patch/<task>-<agent>-<slug>.patch`. Repo policy asks for one per unit of work; backfill or record an explicit waiver.
5. **Uncommitted `scripts/validate-report.py`** in the main checkout. Not created by this session; inspect before committing or discarding.
6. **DEM-001/DEM-002 worktrees are dirty** with stale `docs/context/repo-tree.txt` regenerations. Branches are already merged; operator can discard those worktrees.
7. **Demand-calibration gap is unresolved by design.** Bottom-up EUI 75.74 vs synthetic bills 159.41 (`demand_scale ≈ 2.1047`). The recommendation differs materially between regimes (90.5% vs 68.4% T1+2 served). The final report must present both, not cherry-pick the bottom-up case.
8. **Solar yield +16.2% above benchmark** (1,508.74 vs 1,298 kWh/kWp). Int-003 treats this as plausible screening; keep the caveat in the report.
9. **Battery-only configurations excluded** ([D-38]) because the dispatch topology never grid-charges the battery. If the report claims "solar + battery" trade-offs, state this exclusion and why.
10. **Costs are dimensionless proxies** (`r = 0.6` base, sensitivities 0.3/1.0). No peso figures exist and none should be invented.

---

## 6. Primary Content (Test Evidence)

Full run after the DEC-001 merge (`python -m pytest -q`):

```text
281 passed in 104.79s (0:01:44)
```

Per-file collected counts (`python -m pytest --collect-only -q`):

| Test file | Count |
| :--- | ---: |
| tests/test_baseline_smoke.py | 8 |
| tests/test_battery_dynamics.py | 10 |
| tests/test_battery_reserve.py | 11 |
| tests/test_conservation_checker.py | 24 |
| tests/test_cooling_response.py | 11 |
| tests/test_core_models.py | 20 |
| tests/test_decision.py | 10 |
| tests/test_demand_schedule.py | 13 |
| tests/test_engine.py | 14 |
| tests/test_equipment_audit.py | 19 |
| tests/test_interfaces.py | 9 |
| tests/test_load_shedding.py | 18 |
| tests/test_mock_bills.py | 8 |
| tests/test_non_cooling_demand.py | 10 |
| tests/test_outage_sampler.py | 17 |
| tests/test_scenarios.py | 6 |
| tests/test_smoke.py | 10 |
| tests/test_solar_array.py | 12 |
| tests/test_solar_irradiance.py | 11 |
| tests/test_validation.py | 18 |
| tests/test_weather_ingest.py | 22 |
| **Total** | **281** |

