# Task Status & Progress Log

All work must be traceable to a task defined here or in `docs/context/high-level-tasks.md`.
Local agents update this file to reflect actual status (`open`, `in-progress`, `done`, `blocked`, `needs-review`).

Last updated: 2026-10-21 (Phase 2 Integration)

---

## Phase 0 — Architecture & Governance Setup

Status: **done**

| ID         | Task                                                        | Status | Notes / Report                                                    |
| :--------- | :---------------------------------------------------------- | :----- | :---------------------------------------------------------------- |
| **ARCH-001** | **Lock Conceptual Architecture & Operational Assumptions**    | `done` | [Report](docs/reports/ARCH-001-gemini-lock-conceptual-model.md)   |
| ARCH-001.1 | Project conceptual model definition                         | `done` | Model locked                                                      |
| ARCH-001.2 | Mathematical formulation & solver specifications            | `done` | Specs locked                                                      |
| ARCH-001.3 | Institutional constraints & public data governance lock     | `done` | Governance locked                                                 |
| **ARCH-002** | **Repository Structure, Tooling & Verification Pipeline**   | `done` | [Report](docs/reports/ARCH-002-gemini-repo-scaffolding.md)        |
| ARCH-002.1 | Directory tree and package scaffolding                      | `done` | Repo scaffolded                                                   |
| ARCH-002.2 | Virtual environment, dependencies & packaging               | `done` | Poetry / pyproject.toml                                           |
| ARCH-002.3 | Test framework & baseline smoke tests                       | `done` | Pytest configured                                                 |
| ARCH-002.4 | Fixup research synthesis references in context docs         | `done` | [Report](docs/reports/ARCH-002.4-gemini-research-synthesis-fixup.md) |
| ARCH-002.5 | Cross-platform developer interoperability & batch scripts   | `done` | [Report](docs/reports/ARCH-002.5-gemini-windows-interop.md)       |

---

## Phase 1 — Core Infrastructure & Physics Engine

Status: **done**

| ID         | Task                                                                | Status | Notes / Report                                                       |
| :--------- | :------------------------------------------------------------------ | :----- | :------------------------------------------------------------------- |
| **CORE-001** | **Core Domain Models & System Configuration Dataclasses**            | `done` | [Report](docs/reports/CORE-001-gemini-domain-models.md)              |
| CORE-001.1 | Building archetype & envelope dataclasses                           | `done` | CCIS 2,500 m² archetype                                              |
| CORE-001.2 | Solar PV array & inverter configuration dataclasses                 | `done` | Capacity matrix & derate                                             |
| CORE-001.3 | Battery storage system & dispatch limit dataclasses                 | `done` | 0–200 kWh capacities, LFP                                            |
| CORE-001.4 | Outage scenario parameters & grid status dataclasses                | `done` | Reliability baseline                                                 |
| CORE-001.5 | Fix decision log gaps (D-04, D-05, D-08, D-09, D-11)                 | `done` | [Report](docs/reports/CORE-001.5-gemini-decision-gap-fixup.md)        |
| CORE-001.6 | Process fixup: Decision log sync & status alignment                | `done` | [Report](docs/reports/CORE-001.6-gemini-process-fixup.md)             |
| **CORE-002** | **Weather Data Ingestion & Sanitization Engine**                    | `done` | [Report](docs/reports/CORE-002-gemini-weather-ingestion.md)          |
| CORE-002.1 | NASA POWER API hourly weather client                                | `done` | Client implemented                                                   |
| CORE-002.2 | Weather parser, sanitization, missing-data interpolation            | `done` | Sanitizer implemented                                                |
| CORE-002.3 | Batac (18.06°N, 120.56°E) offline fixture dataset commit            | `done` | 2016 & 2019 fixtures                                                 |
| **CORE-003** | **Demand Profiling & Synthetic Billing Validator**                  | `done` | [Report](docs/reports/CORE-003-gemini-equipment-mock-bills.md)       |
| CORE-003.1 | Room-by-room equipment inventory audit model                        | `done` | Audit schema & loader                                                |
| CORE-003.2 | Connected load calculation by room archetype & tier                 | `done` | 18 rooms loaded                                                      |
| CORE-003.3 | Synthetic monthly electric bill generator                           | `done` | Synthetic generator                                                  |
| CORE-003.4 | Monthly billing fixture generation and validation                   | `done` | 12 monthly bills                                                     |
| CORE-003.5 | Equipment audit connected-load reconciliation ([D-19])               | `done` | [Report](docs/reports/CORE-003.5-gemini-equipment-totals-fixup.md)    |
| **CORE-004** | **Simulation Harness, Energy Balance & Verification Module**        | `done` | [Report](docs/reports/CORE-004-gemini-conservation-harness.md)       |
| CORE-004.1 | First-law energy conservation verification harness                  | `done` | Residual $\le 10^{-5}$ kWh                                           |
| CORE-004.2 | Battery State-of-Charge boundary & rate-of-change checker           | `done` | SoC $\in [0, C]$, C-rate                                             |
| CORE-004.3 | Simulation time-step dispatcher & event logger                      | `done` | Dispatch loop & records                                              |
| CORE-004.4 | Golden test scenarios for energy conservation verification          | `done` | 48h test suite passing                                               |
| CORE-004.5 | Phase 1 Closeout Verification Gap Closures ([D-25])                 | `done` | [Report](docs/reports/CORE-004.5-gemini-phase1-closeout.md)           |
| **CORE-005** | **Baseline Grid-Only Smoke Simulation & Headline KPI Verification** | `done` | [Report](docs/reports/CORE-005-gemini-baseline-smoke-test.md)        |
| CORE-005.1 | End-to-end baseline simulation with placeholder profile             | `done` | 8,760h baseline loop                                                 |
| CORE-005.2 | Headline metrics computation (EUI, peak demand, LF)                 | `done` | 159.41 kWh/m²·yr EUI                                                 |
| CORE-005.3 | Regression test suite on baseline KPIs                              | `done` | Invariants verified                                                  |
| **CORE-006** | **Phase 2 Sub-Model Interface Contracts & Verification Upgrades**   | `done` | [Report](docs/reports/CORE-006-gemini-phase2-contracts.md)           |
| CORE-006.1 | Implement Phase 2 canonical interface types                         | `done` | `ccis_sim.core.interfaces`                                           |
| CORE-006.2 | Lock sub-model signatures & cross-track coupling contracts          | `done` | `docs/context/phase2-interface-contract.md`                          |
| CORE-006.3 | Implement battery idle-loss physical model & harness upgrades        | `done` | Verification harness [D-26]                                          |
| CORE-006.4 | Add unit & regression tests for interface types and idle physics   | `done` | Test suite green (120 passed)                                        |

---

## Phase 2 — Parallel Model Tracks

Status: **open**

| ID          | Task                                                                                                 | Status | Notes / Report                                                                                                    |
| :---------- | :--------------------------------------------------------------------------------------------------- | :----- | :---------------------------------------------------------------------------------------------------------------- |
| **DEM-001** | **Equipment Load & Occupancy Schedule Model**                                                        | `done` | [Report](docs/reports/DEM-001-gemini-demand-schedule.md) [D-27]                                                     |
| DEM-001.1   | Implement academic schedule engine (classes, breaks, holidays)                                       | `done` | AcademicCalendar & build_occupancy_schedule [D-27]                                                                |
| DEM-001.2   | Compute diurnal non-cooling base demand (lighting, IT, plug loads)                                   | `done` | Bottom-up non-cooling load [D-27]                                                                                 |
| DEM-001.3   | Model unoccupied nighttime baseload (10% of daytime peak)                                            | `done` | Baseload 6.0659 kW without double-counting [D-27]                                                                 |
| DEM-001.4   | Write unit tests for equipment aggregation across schedule states                                    | `done` | 23 pytest tests passing                                                                                           |
| **DEM-002** | **Temperature & Humidity Cooling Response Model**                                                    | `done` | [Report](docs/reports/DEM-002-gemini-cooling-response.md) [D-28]                                                    |
| DEM-002.1   | Implement CDD model ($T_{\text{base}} = 24.0^\circ\text{C}$, 4%/°C sensitivity)                      | `done` | Sensible cooling                                                                                                  |
| DEM-002.2   | Implement latent cooling psychrometric multiplier (+20% humidity)                                    | `done` | Latent load                                                                                                       |
| DEM-002.3   | Model split AC compressor duty cycle / inverter modulation                                           | `done` | Inverter response                                                                                                 |
| DEM-002.4   | Validate combined hourly demand profile against mock monthly bills                                   | `open` | Deferred until DEM-001 and DEM-002 merged to master                                                               |
| **SOL-001** | **Solar Irradiance Geometry & NOCT Thermal Derating Model**                                          | `done` | [SOL-001-gemini-solar-irradiance.md](../reports/SOL-001-gemini-solar-irradiance.md) [D-29]                         |
| SOL-001.1   | Implement Batac tilted plane irradiance model (15° South tilt)                                       | `done` | Spencer solar position, Erbs GHI->DHI/DNI, Liu-Jordan 15° transposition [D-29]                                      |
| SOL-001.2   | Model cell operating temperature with +10°C rooftop thermal penalty                                  | `done` | NOCT 45°C + 10°C penalty: T_cell = T_amb + (35/800)*G_poa [D-29]                                                    |
| SOL-001.3   | Apply module temperature power derating ($\gamma = -0.40\%/^\circ\text{C}$)                          | `done` | compute_dc_power_per_kwp, 1,695.05 kWh/kWp specific DC yield (2019)                                                 |
| SOL-001.4   | Write unit tests verifying yield drop during high-temperature hours                                  | `done` | 11 pytest unit/integration tests passing (100% green)                                                               |
| **SOL-002** | **Array Sizing, Inverter Clipping & Balance-of-System Losses**                                       | `done` | [SOL-002-gemini-solar-array.md](../reports/SOL-002-gemini-solar-array.md) [D-30] (SOL-002.4 deferred)               |
| SOL-002.1   | Implement DC capacity scaling (0, 50, 100, 200 kWp)                                                  | `done` | compute_ac_generation scenario matrix scaling [D-30]                                                                |
| SOL-002.2   | Model inverter peak efficiency (98%) and DC/AC clipping limits                                       | `done` | 98% peak efficiency, 1.20 DC/AC ratio clipping limit [D-30]                                                         |
| SOL-002.3   | Incorporate balance-of-system derates (PR = 0.77, soiling, wiring)                                   | `done` | Named non-thermal BOS factors decomposed to match 0.77 PR [D-30]                                                     |
| SOL-002.4   | Validate annual specific yield against Luzon benchmark (1,298 kWh/kWp)                               | `open` | Deferred until SOL-001 and SOL-002 are merged into integration runner                                                |
| **BAT-001** | **Battery Dispatch Dynamics, SoC Tracking & Losses**                                                 | `done` | [BAT-001-gemini-battery-dynamics.md](../reports/BAT-001-gemini-battery-dynamics.md)                                 |
| BAT-001.1   | Implement time-stepped State-of-Charge tracking logic                                                | `done` | SoC recursion                                                                                                       |
| BAT-001.2   | Apply LFP round-trip efficiency (92% RTE, $\sqrt{\eta}$ charge/discharge)                            | `done` | Efficiency losses                                                                                                   |
| BAT-001.3   | Enforce charge/discharge power limits (0.5C charge, 1.0C discharge)                                  | `done` | C-rate constraints                                                                                                  |
| BAT-001.4   | Write unit tests for simultaneous charge/discharge prevention                                        | `done` | Boundary tests                                                                                                      |
| **BAT-002** | **Battery Outage Reserve & State-of-Charge Constraints**                                             | `done` | [BAT-002-gemini-battery-reserve.md](../reports/BAT-002-gemini-battery-reserve.md)                                    |
| BAT-002.1   | Enforce 10% minimum SoC reserve floor (90% usable DoD)                                               | `done` | Reserve floor                                                                                                       |
| BAT-002.2   | Implement configurable emergency outage reserve %                                                    | `done` | Outage cushion                                                                                                      |
| BAT-002.3   | Incorporate ambient self-discharge (2%/month) and tare loss                                          | `done` | Idle losses                                                                                                         |
| BAT-002.4   | Write unit tests for deep-discharge protection during long outages                                   | `done` | Protection tests                                                                                                    |
| **OUT-001** | **Stochastic Outage Arrival & Duration Sampler**                                                     | `done` | [Report](docs/reports/OUT-001-gemini-outage-sampler.md) [D-33]                                                     |
| OUT-001.1   | Implement Poisson arrival process ($\lambda = 3$ normal, $\lambda = 8$ typhoon)                      | `done` | Poisson arrivals [D-33]                                                                                           |
| OUT-001.2   | Implement Lognormal duration sampler (Normal: $\mu=1.2, \sigma=0.8$; Typhoon: $\mu=2.3, \sigma=1.0$) | `done` | Duration sampler [D-33]                                                                                           |
| OUT-001.3   | Implement typhoon multi-day solar depression (20–30% GHI for 3–5 days)                               | `done` | Storm coupling [D-33]                                                                                             |
| OUT-001.4   | Add Kolmogorov-Smirnov distribution goodness-of-fit validator                                        | `done` | Distribution fit [D-33]                                                                                           |
| **OUT-002** | **Priority-Based Tiered Load Shedding Controller**                                                   | `done` | [Report](docs/reports/OUT-002-gemini-load-shedding.md)                                                             |
| OUT-002.1   | Implement load categorization: Tier 1 (2%), Tier 2 (18%), Tier 3 (80%)                               | `done` | Tier mapping helper                                                                                                |
| OUT-002.2   | Build automated shedding logic on grid failure (instant Tier 3 drop)                                 | `done` | Shedding logic                                                                                                     |
| OUT-002.3   | Implement battery low-SoC Tier 2 shedding rule (<20% SoC)                                            | `done` | Second-tier shed                                                                                                   |
| OUT-002.4   | Track unserved energy (kWh) and outage hours covered per tier                                        | `done` | Unserved metrics                                                                                                   |

---

## Phase 3 — Integration, Simulation Engine & Experiment Matrix

Status: **open**

| ID          | Task                                                                | Status | Notes / Report                                                     |
| :---------- | :------------------------------------------------------------------ | :----- | :----------------------------------------------------------------- |
| **INT-001** | **Simulation Engine Integration & Full Dispatch Loop**              | `open` | [PROMPT](docs/prompts/INT-001-PROMPT.md) Engine, CLI, verification |
| INT-001.1   | Integrate all sub-models into hourly time loop                      | `open` | Full dispatch engine                                               |
| INT-001.2   | Implement priority bus energy routing (Solar -> Load -> Battery)    | `open` | Bus routing                                                        |
| INT-001.3   | Run full annual simulation for all combinations                     | `open` | Matrix runner                                                      |
| INT-001.4   | Verify energy conservation across all 8,760 hours                   | `open` | Conservation check                                                 |
| **INT-002** | **Monte Carlo Outage Simulation Engine**                            | `open` |                                                                    |
| INT-002.1   | Monte Carlo driver (N = 100 seeds per scenario)                     | `open` | MC engine                                                          |
| INT-002.2   | Stochastic convergence test (sample size sufficiency)               | `open` | Convergence                                                        |
| INT-002.3   | Record distributions: unserved kWh, outage hours survived           | `open` | Distributions                                                      |
| **INT-003** | **Verification, Validation & Headline KPI Reporting**               | `open` |                                                                    |
| INT-003.1   | Final energy balance audit (residual < 10⁻⁵ kWh everywhere)         | `open` | Balance audit                                                      |
| INT-003.2   | Compare uncalibrated simulation vs synthetic bills (NMBE, CV(RMSE)) | `open` | Billing validation                                                 |
| INT-003.3   | Generate publication-quality headline KPI summary tables            | `open` | KPI tables                                                         |

---

## Phase 4 — Decision Analysis, Visualization & Reporting

Status: **open**

| ID          | Task                                                                | Status | Notes / Report                                                    |
| :---------- | :------------------------------------------------------------------ | :----- | :---------------------------------------------------------------- |
| **DEC-001** | **Multi-Criteria Decision Analysis (AHP) Implementation**           | `open` |                                                                   |
| DEC-001.1   | Implement Analytic Hierarchy Process (AHP) weighting engine         | `open` | AHP matrix solver                                                 |
| DEC-001.2   | Compute Consistency Ratio (CR ≤ 0.10 threshold)                     | `open` | Consistency check                                                 |
| DEC-001.3   | Score all sizing combinations across 4 criteria                     | `open` | Scenario scoring                                                  |
| **DEC-002** | **Pareto Frontier & Recommended System Sizing Analysis**             | `open` |                                                                   |
| DEC-002.1   | Compute 2D/3D Pareto frontier (Reliability vs Cost vs Self-Suff)    | `open` | Pareto analysis                                                   |
| DEC-002.2   | Identify recommended sizing configuration                           | `open` | Sizing selection                                                  |
| DEC-002.3   | Sensitivity analysis across weights & weather years                 | `open` | Sensitivity check                                                 |
| **DEC-003** | **Visualization Suite & Final Report Generation**                   | `open` |                                                                   |
| DEC-003.1   | Generate energy balance dispatch stacked area charts                | `open` | Dispatch plots                                                    |
| DEC-003.2   | Generate battery SoC duration curves & unserved load distributions  | `open` | Reliability plots                                                 |
| DEC-003.3   | Compile comprehensive engineering report markdown                   | `open` | Final report                                                      |
