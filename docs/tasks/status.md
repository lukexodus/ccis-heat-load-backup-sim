# Task Status

Live tracker — what is actually done right now, not the long-term plan (the plan lives in `docs/tasks/high-level-tasks.md`). This file changes every time a task's status changes. A new APC instance or local agent should be able to read this file alone and know the exact state of the project without having to reconstruct it from scattered chat logs or report files.

**Status values:**
- `open` — Not yet started.
- `in-progress` — Actively being worked on (note the agent / branch).
- `blocked` — Cannot proceed (state the specific blocking dependency).
- `needs-review` — Implemented by a local agent; waiting for APC / lukexodus review.
- `done` — Completed, verified, and accepted (must link the completed report file).

---

## Phase 0 — Inception, Scope Lock & Repository Foundation

Status: **done**

| ID           | Task                                                         | Status | Notes / Report                                                                                  |
| :----------- | :----------------------------------------------------------- | :----- | :---------------------------------------------------------------------------------------------- |
| **ARCH-001** | **Lock Scope, Conceptual Model & Interface Contracts**       | `done` | [ARCH-001-gemini-lock-conceptual-model.md](../reports/ARCH-001-gemini-lock-conceptual-model.md) |
| ARCH-001.1   | Formalize system boundary, entities, and environment         | `done` | Building (18 rooms), PV, BESS, grid                                                             |
| ARCH-001.2   | Define state variables, discrete events, and transitions     | `done` | Hourly, continuous & discrete states                                                            |
| ARCH-001.3   | Specify performance measures and decision variables          | `done` | SSR, SCR, Autonomy, EUE, kWp, kWh                                                               |
| ARCH-001.4   | Review and record decisions `[D-05]` through `[D-11]`        | `done` | Logged in decision-log.md                                                                       |
| ARCH-001.5   | Lock `HourlyRecord` schema and function signatures           | `done` | Canonical contract                                                                              |
| ARCH-001.6   | Generate conceptual model Mermaid flowcharts                 | `done` | Architecture & dispatch diagrams                                                                |
| **ARCH-002** | **Scaffold Repository, Toolchain, Linting & Research Index** | `done` | [ARCH-002-gemini-repo-scaffolding.md](../reports/ARCH-002-gemini-repo-scaffolding.md)           |
| ARCH-002.1   | Set up Python env, `pyproject.toml`, and `requirements.txt`  | `done` | pandas, numpy, scipy, matplotlib, pytest                                                        |
| ARCH-002.2   | Create package directory layout (`src/ccis_sim/`, `tests/`)  | `done` | Scaffolding (subpackages, tests, data)                                                          |
| ARCH-002.3   | Configure linting, formatting, and pytest test harness       | `done` | Verification gate (pytest 10/10 passing)                                                        |
| ARCH-002.4   | Create and commit `docs/context/research-synthesis.md`       | `done` | [ARCH-002.4-gemini-research-synthesis-fixup.md](../reports/ARCH-002.4-gemini-research-synthesis-fixup.md)     |

---

## Phase 1 — Core Infrastructure & Data Pipelines

Status: **open**

| ID           | Task                                                                             | Status | Notes / Report        |
| :----------- | :------------------------------------------------------------------------------- | :----- | :-------------------- |
| **CORE-001** | **Implement Canonical Domain Models & Interface Contracts**                      | `done` | [CORE-001-gemini-domain-models.md](../reports/CORE-001-gemini-domain-models.md) |
| CORE-001.1   | Implement `Building`, `SolarArray`, and `Battery` dataclasses                    | `done` | Building (18 rooms), SolarArray, Battery                                         |
| CORE-001.2   | Implement `OutageEvent` and `HourlyRecord` time-step models                      | `done` | OutageEvent & HourlyRecord (18 fields)                                           |
| CORE-001.3   | Build CSV/dict serialization protocols for simulation output                     | `done` | to_dict / from_dict serialization                                                |
| CORE-001.4   | Write unit test suite for domain models and data invariants                      | `done` | 29 pytest tests passing (100% green)                                             |
| **CORE-002** | **NASA POWER Weather Ingestion & Offline CSV Fixture Cache**                     | `open` | Outline §4            |
| CORE-002.1   | Implement NASA POWER API client for Batac (18.06°N, 120.56°E)                    | `open` | REST client           |
| CORE-002.2   | Build hourly/daily weather parser (T2M, RH2M, ALLSKY_SFC_SW_DWN)                 | `open` | Met parsing           |
| CORE-002.3   | Add missing value sentinel `-999` filter & UTC→PST alignment                     | `open` | Sanitization          |
| CORE-002.4   | Commit cached offline CSV fixtures (baseline, hot-year 2016/2019)                | `open` | Committed fixtures    |
| CORE-002.5   | Write unit tests for weather ingest and psychrometric sanity                     | `open` | Verification          |
| **CORE-003** | **Equipment Audit Model & Synthetic Mock Bill Generator**                        | `done` | [CORE-003-gemini-equipment-mock-bills.md](../reports/CORE-003-gemini-equipment-mock-bills.md) |
| CORE-003.1   | Define equipment audit CSV schema (`item, count, kW, hours, tier`)               | `done` | `equipment-audit-schema.csv` committed |
| CORE-003.2   | Create CCIS archetype fixture (~2,500 m², 18 rooms, ACs, labs)                   | `done` | `equipment-audit-ccis.csv` (140 kW)    |
| CORE-003.3   | Implement synthetic monthly electricity bill generator                           | `done` | `SyntheticBillGenerator` + noise       |
| CORE-003.4   | Validate synthetic bills against regional EUI (150–300 kWh/m²·yr)                | `done` | EUI = 159.41 kWh/m²·yr (pass)          |
| **CORE-004** | **Shared Test Harness & Energy Balance Invariant Checker**                       | `open` | Critical test gate    |
| CORE-004.1   | Implement strict energy conservation checker ($\le 10^{-5}\text{ kWh}$)          | `open` | Conservation rule     |
| CORE-004.2   | Implement battery boundary validator ($0 \le \text{SoC} \le \text{Cap}$, C-rate) | `open` | State boundaries      |
| CORE-004.3   | Build shared golden fixture runner for sub-model validation                      | `open` | Shared runner         |
| **CORE-005** | **Baseline Engine Smoke Test (Phase 1 Exit Gate)**                               | `open` | Exit gate             |
| CORE-005.1   | Implement grid-only, zero-solar, zero-battery simulation                         | `open` | Baseline engine       |
| CORE-005.2   | Run 8,760-hour baseline through energy-balance test harness                      | `open` | Zero-leak test        |
| CORE-005.3   | Generate baseline summary metrics (annual kWh, peak kW, base EUI)                | `open` | Baseline KPIs         |
|              |                                                                                  |        |                       |

---

## Phase 2 — Parallel Model Tracks

Status: **open**

| ID          | Task                                                                                                 | Status | Notes / Report     |
| :---------- | :--------------------------------------------------------------------------------------------------- | :----- | :----------------- |
| **DEM-001** | **Equipment Load & Occupancy Schedule Model**                                                        | `open` |                    |
| DEM-001.1   | Implement academic schedule engine (classes, breaks, holidays)                                       | `open` | Schedule calendar  |
| DEM-001.2   | Compute diurnal non-cooling base demand (lighting, IT, plug loads)                                   | `open` | Bottom-up load     |
| DEM-001.3   | Model unoccupied nighttime baseload (10% of daytime peak)                                            | `open` | Baseload rule      |
| DEM-001.4   | Write unit tests for equipment aggregation across schedule states                                    | `open` | Test suite         |
| **DEM-002** | **Temperature & Humidity Cooling Response Model**                                                    | `open` |                    |
| DEM-002.1   | Implement CDD model ($T_{\text{base}} = 24.0^\circ\text{C}$, 4%/°C sensitivity)                      | `open` | Sensible cooling   |
| DEM-002.2   | Implement latent cooling psychrometric multiplier (+20% humidity)                                    | `open` | Latent load        |
| DEM-002.3   | Model split AC compressor duty cycle / inverter modulation                                           | `open` | Inverter response  |
| DEM-002.4   | Validate combined hourly demand profile against mock monthly bills                                   | `open` | Calibration check  |
| **SOL-001** | **Solar Irradiance Geometry & NOCT Thermal Derating Model**                                          | `open` |                    |
| SOL-001.1   | Implement Batac tilted plane irradiance model (15° South tilt)                                       | `open` | Irradiance model   |
| SOL-001.2   | Model cell operating temperature with +10°C rooftop thermal penalty                                  | `open` | NOCT model         |
| SOL-001.3   | Apply module temperature power derating ($\gamma = -0.40\%/^\circ\text{C}$)                          | `open` | Thermal derate     |
| SOL-001.4   | Write unit tests verifying yield drop during high-temperature hours                                  | `open` | Thermal tests      |
| **SOL-002** | **Array Sizing, Inverter Clipping & Balance-of-System Losses**                                       | `open` |                    |
| SOL-002.1   | Implement DC capacity scaling (0, 50, 100, 200 kWp)                                                  | `open` | Capacity scaling   |
| SOL-002.2   | Model inverter peak efficiency (98%) and DC/AC clipping limits                                       | `open` | Inverter clipping  |
| SOL-002.3   | Incorporate balance-of-system derates (PR = 0.77, soiling, wiring)                                   | `open` | BOS losses         |
| SOL-002.4   | Validate annual specific yield against Luzon benchmark (1,298 kWh/kWp)                               | `open` | Yield benchmark    |
| **BAT-001** | **Battery Dispatch Dynamics, SoC Tracking & Losses**                                                 | `open` |                    |
| BAT-001.1   | Implement time-stepped State-of-Charge tracking logic                                                | `open` | SoC recursion      |
| BAT-001.2   | Apply LFP round-trip efficiency (92% RTE, $\sqrt{\eta}$ charge/discharge)                            | `open` | Efficiency losses  |
| BAT-001.3   | Enforce charge/discharge power limits (0.5C charge, 1.0C discharge)                                  | `open` | C-rate constraints |
| BAT-001.4   | Write unit tests for simultaneous charge/discharge prevention                                        | `open` | Boundary tests     |
| **BAT-002** | **Battery Outage Reserve & State-of-Charge Constraints**                                             | `open` |                    |
| BAT-002.1   | Enforce 10% minimum SoC reserve floor (90% usable DoD)                                               | `open` | Reserve floor      |
| BAT-002.2   | Implement configurable emergency outage reserve %                                                    | `open` | Outage cushion     |
| BAT-002.3   | Incorporate ambient self-discharge (2%/month) and tare loss                                          | `open` | Idle losses        |
| BAT-002.4   | Write unit tests for deep-discharge protection during long outages                                   | `open` | Protection tests   |
| **OUT-001** | **Stochastic Outage Arrival & Duration Sampler**                                                     | `open` |                    |
| OUT-001.1   | Implement Poisson arrival process ($\lambda = 3$ normal, $\lambda = 8$ typhoon)                      | `open` | Poisson arrivals   |
| OUT-001.2   | Implement Lognormal duration sampler (Normal: $\mu=1.2, \sigma=0.8$; Typhoon: $\mu=2.3, \sigma=1.0$) | `open` | Duration sampler   |
| OUT-001.3   | Implement typhoon multi-day solar depression (20–30% GHI for 3–5 days)                               | `open` | Storm coupling     |
| OUT-001.4   | Add Kolmogorov-Smirnov distribution goodness-of-fit validator                                        | `open` | Distribution fit   |
| **OUT-002** | **Priority-Based Tiered Load Shedding Controller**                                                   | `open` |                    |
| OUT-002.1   | Implement load categorization: Tier 1 (2%), Tier 2 (18%), Tier 3 (80%)                               | `open` | Tier mapping       |
| OUT-002.2   | Build automated shedding logic on grid failure (instant Tier 3 drop)                                 | `open` | Shedding logic     |
| OUT-002.3   | Implement battery low-SoC Tier 2 shedding rule (<20% SoC)                                            | `open` | Second-tier shed   |
| OUT-002.4   | Track unserved energy (kWh) and outage hours covered per tier                                        | `open` | Unserved metrics   |

---

## Phase 3 — Integration, Simulation Engine & Verification

Status: **open**

| ID | Task | Status | Notes / Report |
| :--- | :--- | :--- | :--- |
| **INT-001** | **Simulation Engine & CLI Application Driver** | `open` | |
| INT-001.1 | Wire Demand, Solar, Battery, Outage, and Shedding into time loop | `open` | Main engine loop |
| INT-001.2 | Implement CLI interface (`ccis-sim`) with scenario arguments | `open` | CLI driver |
| INT-001.3 | Add tabular summary exporters (hourly time series, daily, annual) | `open` | Output export |
| INT-001.4 | Write end-to-end integration test suite | `open` | Smoke test suite |
| **INT-002** | **Monte Carlo Runner & Scenario Grid Sweeper** | `open` | Outline §4 & §7 |
| INT-002.1 | Implement multi-replication runner with reproducible PRNG seeds | `open` | MC runner |
| INT-002.2 | Build full scenario matrix (Weather × Solar × Battery × Outages) | `open` | Scenario grid |
| INT-002.3 | Compute output distribution statistics (Mean, StdErr, P5, P50, P95) | `open` | Risk percentiles |
| INT-002.4 | Implement sequential stopping rule ($z \cdot s / \sqrt{n} \le \delta$) | `open` | Convergence gate |
| **INT-003** | **Verification, Validation & Plausibility Suite** | `open` | Outline §6 |
| INT-003.1 | Audit energy conservation across all Monte Carlo replications | `open` | Conservation audit |
| INT-003.2 | Check ASHRAE Guideline 14 metrics (NMBE $\le \pm 5\%$, CV(RMSE) $\le 25\%$) | `open` | ASHRAE checks |
| INT-003.3 | Validate annual solar specific yield ($1,200\text{--}1,600\text{ kWh/kWp}\cdot\text{yr}$) | `open` | Yield benchmark |
| INT-003.4 | Validate building EUI ($150\text{--}300\text{ kWh/m}^2\cdot\text{yr}$) | `open` | EUI benchmark |
| INT-003.5 | Run One-At-A-Time (OAT) sensitivity sweeps on key parameters | `open` | Sensitivity suite |

---

## Phase 4 — Decision Analysis & System Sizing Optimization

Status: **open**

| ID | Task | Status | Notes / Report |
| :--- | :--- | :--- | :--- |
| **DEC-001** | **Analytic Hierarchy Process (AHP) Weighting Engine** | `open` | Outline §7 |
| DEC-001.1 | Implement Saaty 1–9 pairwise comparison matrix evaluator | `open` | Pairwise matrix |
| DEC-001.2 | Implement principal eigenvector weight extraction algorithm | `open` | Weight vector |
| DEC-001.3 | Implement Consistency Ratio calculation ($CR \le 0.10$) with $RI$ lookup | `open` | Consistency check |
| DEC-001.4 | Encode default criteria hierarchy (Reliability, Cost, LCOE, Env, Risk) | `open` | Baseline weights |
| DEC-001.5 | Implement criteria weight sensitivity analysis (Dirichlet/perturbation) | `open` | Weight sensitivity |
| **DEC-002** | **Sizing Optimization & Trade-Off Recommendation Evaluator** | `open` | |
| DEC-002.1 | Implement composite multi-criteria scoring across all sizing candidates | `open` | Scoring engine |
| DEC-002.2 | Extract Pareto frontier (Reliability vs. System Cost trade-offs) | `open` | Pareto extraction |
| DEC-002.3 | Formulate defensible recommendation (smallest system covering 12h outage) | `open` | Final recommendation |

---

## Phase 5 — Documentation, Visualizations & Defense Preparation

Status: **open**

| ID          | Task                                                             | Status | Notes / Report     |
| :---------- | :--------------------------------------------------------------- | :----- | :----------------- |
| **DOC-001** | **Visualizations & Labelled Sample Output Generator**            | `open` | Outline §8         |
| DOC-001.1   | Generate daily load vs. outdoor temperature regression curve     | `open` | Temp-load curve    |
| DOC-001.2   | Plot 12-hour heatwave outage hourly dispatch profile             | `open` | Dispatch plot      |
| DOC-001.3   | Plot Monte Carlo P5/P50/P95 histograms and risk boxplots         | `open` | Risk distributions |
| DOC-001.4   | Plot Pareto sizing trade-off frontier (Cost vs. Outage Hours)    | `open` | Pareto frontier    |
| DOC-001.5   | Plot AHP criteria sensitivity tornado diagram                    | `open` | AHP sensitivity    |
| **DOC-002** | **Course Project Final Report Compilation**                      | `open` | Outline §1–10      |
| DOC-002.1   | Draft §1 Overview, §2 Formulation & §3 Conceptual Model          | `open` | Sections 1–3       |
| DOC-002.2   | Draft §4 Data Collection & Input Modeling & §5 Implementation    | `open` | Sections 4–5       |
| DOC-002.3   | Draft §6 Verification & Validation & §7 Results & Analysis       | `open` | Sections 6–7       |
| DOC-002.4   | Assemble §8 Labelled Sample Outputs & §9 IEEE References         | `open` | Sections 8–9       |
| DOC-002.5   | Compile §10 Program Listing and format final report PDF/Markdown | `open` | Section 10         |
| **DOC-003** | **Defense Presentation Deck & Group Handoff**                    | `open` |                    |
| DOC-003.1   | Construct presentation slide deck structured for 4 group members | `open` | Slide deck         |
| DOC-003.2   | Prepare speaking notes aligned with course syllabus topics       | `open` | Speaking notes     |
| DOC-003.3   | Compile dry-run Q&A defense cheat sheet                          | `open` | Defense prep       |
