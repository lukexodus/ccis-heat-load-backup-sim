# CCIS Heat, Load and Backup Power Simulation (`ccis-sim`)

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Code Style: Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Testing: Pytest](https://img.shields.io/badge/testing-pytest-green.svg)](https://docs.pytest.org/)

A physics-based, time-stepped simulation model of the electricity demand of the **College of Computing and Information Sciences (CCIS)** building at Mariano Marcos State University (MMSU) in **Batac, Ilocos Norte, Philippines** (18.06°N, 120.56°E). The model evaluates building cooling response during extreme heat waves and assesses the resilience of rooftop solar photovoltaic (PV) and battery energy storage system (BESS) microgrid configurations under stochastic utility grid outage scenarios.

---

## Table of Contents

- [1. Overview & Research Questions](#1-overview--research-questions)
- [2. System Architecture & Energy Balance](#2-system-architecture--energy-balance)
- [3. Building Archetype & Load Tiers](#3-building-archetype--load-tiers)
- [4. Repository Layout](#4-repository-layout)
- [5. Installation & Setup](#5-installation--setup)
- [6. Running Simulations & Tests](#6-running-simulations--tests)
- [7. Verification & Validation Framework](#7-verification--validation-framework)
- [8. Tooling & Automation Scripts](#8-tooling--automation-scripts)
- [9. Governance & Coordination Model](#9-governance--coordination-model)
- [10. Roadmap & Project Phases](#10-roadmap--project-phases)
- [11. License & Citation](#11-license--citation)

---

## 1. Overview & Research Questions

Batac experiences prolonged tropical heat waves and frequent grid reliability challenges (elevated heat indexes, tropical cyclones, and distribution feeder trips). The CCIS building houses computer laboratories, faculty offices, lecture rooms, and network infrastructure that face significant operational disruptions during utility blackouts.

### Core Objectives
1. **Heat-Load Quantification:** Model how ambient temperature and relative humidity drive diurnal air-conditioning electricity demand across academic semesters and break periods.
2. **Microgrid Resilience Assessment:** Determine how much critical demand can be reliably served by rooftop solar PV paired with lithium-ion (LFP) battery storage across multi-hour and multi-day grid blackouts.
3. **Defensible Sizing Recommendation:** Execute Monte Carlo uncertainty sweeps over historical weather years (baseline 2019, extreme hot year 2016) and outage distributions to identify the most cost-effective PV and BESS capacity combination meeting target autonomy levels.

---

## 2. System Architecture & Energy Balance

The simulation tracks hourly continuous state variables over full annual cycles (8,760 hours) enforcing strict first-law thermodynamic conservation:

$$E_{\text{in}} = E_{\text{out}}$$
$$P_{\text{solar}} + P_{\text{grid\_import}} + P_{\text{battery\_discharge}} = P_{\text{demand\_served}} + P_{\text{solar\_curtailed}} + P_{\text{battery\_charge}}$$

```mermaid
flowchart TD
    subgraph Generation ["Energy Sources"]
        Solar["Rooftop Solar PV Array\n(0–200 kWp, Batac Tilted Plane)"]
        Grid["Utility Grid\n(Ilec II 13.2 kV Feeder)"]
    end

    subgraph Storage ["Energy Storage"]
        Battery["Battery Energy Storage (BESS)\n(LFP, 92% RTE, 10% Protection Floor)"]
    end

    subgraph Dispatch ["Energy Balance & Dispatch Controller"]
        Bus(("Microgrid AC Bus\n(Residual <= 1e-5 kWh)"))
    end

    subgraph Demand ["Building Electrical Demand"]
        T1["Tier 1: Life-Safety & Network (2%)"]
        T2["Tier 2: Servers, Security & Offices (18%)"]
        T3["Tier 3: Heavy AC & Instruction Labs (80%)"]
    end

    subgraph Losses ["Losses & Discards"]
        Curtailment["Solar Curtailment"]
        Unserved["Unserved Energy (EUE)"]
    end

    Solar -->|Solar Generation| Bus
    Grid -->|Grid Import (when available)| Bus
    Battery <-->|Charge / Discharge| Bus

    Bus -->|Demand Served| T1
    Bus -->|Demand Served| T2
    Bus -->|Demand Served| T3
    Bus -->|Overproduction| Curtailment
    Demand -.->|Deficit during Outage| Unserved
```

---

## 3. Building Archetype & Load Tiers

The CCIS facility archetype is parameterized as a two-storey institutional building with **2,500 m²** gross floor area, 18 distinct thermal zones, and an audited connected load of **147.81 kW**:

| Priority Tier | Share | Connected Load | Equipment Covered | Outage Policy |
| :--- | :--- | :--- | :--- | :--- |
| **Tier 1 (Critical)** | **2%** | **2.96 kW** | Emergency egress lighting, main telecom/fiber switches, core routers, IoT monitoring gateway. | Always sustained; protected by 20% emergency battery reserve. |
| **Tier 2 (Essential)** | **18%** | **26.61 kW** | Department server rack, dean & administrative offices, security CCTV, critical refrigeration. | Shed when battery State-of-Charge falls below 20%. |
| **Tier 3 (Discretionary)** | **80%** | **118.25 kW** | Split-system inverter ACs, computer teaching labs (100+ workstations), general classroom lighting. | Shed immediately upon grid failure during blackouts. |

---

## 4. Repository Layout

```text
.
├── AGENTS.md                   # Operational rules and protocol for AI coding agents
├── pyproject.toml              # Build specifications, dependencies, and tool settings
├── requirements.txt            # Pinned dependencies
├── README.md                   # Project overview and orientation (this file)
├── docs/
│   ├── context/                # High-level architecture, complete context, and research synthesis
│   │   ├── complete-context.md # Comprehensive orientation document
│   │   ├── research-synthesis.md # Index of empirical benchmarks and parameters
│   │   └── repo-tree.txt       # Auto-generated filesystem tree snapshot
│   ├── decisions/              # Append-only architectural decision log (ADR)
│   │   └── decision-log.md     # Locked architectural and methodological decisions ([D-01]–[D-25])
│   ├── tasks/                  # Task tracking and phase execution roadmaps
│   │   ├── high-level-tasks.md # Phased macro plan & roadmap
│   │   └── status.md           # Live per-task status tracker
│   ├── reports/                # Completed task reports (one per completed task)
│   └── prompts/                # Standalone prompt archive for reproducible tasks
├── scripts/                    # Automation utilities (Linux/macOS .sh & Windows .bat/.ps1)
│   ├── apc-bundle.sh           # Verifiable context bundle packager for remote APC AI
│   ├── task-worktree.sh        # Isolated Git worktree manager for parallel agent tasks
│   ├── validate-report.py      # Task report format and repository alignment linter
│   └── manage-decisions.py     # Decision ID collision checker and reservation tool
├── src/
│   └── ccis_sim/               # Core Python package
│       ├── core/               # Canonical domain models (Building, Battery, HourlyRecord) and verification
│       ├── weather/            # NASA POWER API client, parser, -999 filter, and psychrometrics
│       ├── demand/             # Equipment inventory audit and synthetic billing calibrator
│       ├── solar/              # Tilted-plane solar irradiance and NOCT thermal derating
│       ├── battery/            # Time-stepped SoC tracking and boundary constraints
│       ├── outage/             # Stochastic Poisson arrival and lognormal duration sampler
│       ├── integration/        # Continuous simulation engines and baseline smoke runner
│       └── decision/           # Multi-criteria decision analysis (AHP / weighted scoring)
└── tests/                      # Automated test suite (unit, integration, and golden fixtures)
    ├── fixtures/               # Offline cached weather data and reference scenario generators
    └── test_*.py               # Automated pytest verification suites
```

---

## 5. Installation & Setup

### Prerequisites
- Python 3.10 or higher
- Git

### Installation Steps

1. **Clone the repository:**
   ```bash
   git clone https://github.com/lukexodus/ccis-heat-load-backup-sim.git
   cd ccis-heat-load-backup-sim
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate       # On Linux / macOS
   # .venv\Scripts\activate        # On Windows CMD / PowerShell
   ```

3. **Install the package and development dependencies:**
   ```bash
   pip install --upgrade pip
   pip install -e ".[dev]"
   ```

---

## 6. Running Simulations & Tests

### Executing the Test Suite
The repository includes comprehensive unit, integration, and regression suites enforcing strict physics invariants:

```bash
# Run all tests
pytest

# Run tests with detailed verbose output
pytest -v

# Run verification harness tests specifically
pytest tests/test_conservation_checker.py
```

### Running the Baseline Simulation Engine
Run an 8,760-hour continuous grid-only baseline simulation for the 2019 reference year:

```python
from ccis_sim.core import Building
from ccis_sim.weather import load_weather_fixture
from ccis_sim.integration import simulate_baseline, calculate_baseline_metrics

# Load cached NASA POWER weather data for Batac (2019 baseline)
weather_df = load_weather_fixture(year=2019)

# Run 8,760-hour continuous simulation
records = simulate_baseline(weather_df=weather_df, calendar_year=2019)

# Calculate summary metrics (kWh, peak kW, EUI)
metrics = calculate_baseline_metrics(records)
print(metrics.summary())
# Annual Demand: 398,525.00 kWh/yr | EUI: 159.41 kWh/m²·yr | Peak Demand: 124.44 kW
```

---

## 7. Verification & Validation Framework

To guarantee scientific reproducibility and numerical integrity across sub-models, all simulations pass through the shared invariant checker (`ccis_sim.core.verification`):

1. **Strict Energy Conservation (`[D-21]`):** Every hour must balance with absolute residual $\le 10^{-5}\text{ kWh}$. Cumulative annual drift is constrained by $\max(\epsilon, \sqrt{N} \epsilon) \approx 0.001\text{ kWh}$.
2. **Battery State-of-Charge Continuity (`[D-25]`):** Hour-to-hour chemical storage transitions enforce:
   $$\text{SoC}_t = \text{SoC}_{t-1} + \sqrt{\eta_{\text{rt}}} P_{\text{chg},t} \Delta t - \frac{P_{\text{dis},t} \Delta t}{\sqrt{\eta_{\text{rt}}}}$$
   with symmetric 92% round-trip efficiency ($\sqrt{0.92} \approx 0.9592$).
3. **Sub-Flow Decomposition Balances:** Explicitly validates that solar generation equals the exact sum of solar-to-demand, solar-to-battery, and curtailment, and that gross demand equals served plus unserved load.
4. **Non-Finite Numeric Guards:** Traps any `NaN`, `+inf`, or `-inf` across all record fields.
5. **Shared Golden Scenario:** A hand-calculated 48-hour reference fixture (`create_golden_scenario`) exercises all operational microgrid modes (solar generation, battery charging, curtailment at 100% SoC, nighttime discharge, 8-hour grid blackout with Tier 3 shedding, and grid recovery) with exact $0.000000\text{ kWh}$ residual closure.

---

## 8. Tooling & Automation Scripts

The project includes dual-platform automation tools supporting Linux/macOS and Windows (Command Prompt and PowerShell):

| Utility | Script (Linux/macOS) | Script (Windows) | Purpose |
| :--- | :--- | :--- | :--- |
| **APC Bundle** | `./scripts/apc-bundle.sh` | `.\scripts\apc-bundle.bat` | Packages verifiable tarballs with SHA-256 manifests for external AI planning. |
| **Task Worktree** | `./scripts/task-worktree.sh` | `.\scripts\task-worktree.bat` | Automates dedicated Git worktree creation for concurrent agent tasks. |
| **Validate Report** | `./scripts/validate-report.py` | `.\scripts\validate-report.bat` | Lints task markdown reports, diff blocks, and status alignment. |
| **Manage Decisions** | `./scripts/manage-decisions.py` | `.\scripts\manage-decisions.bat` | Allocates non-colliding Decision IDs for architectural records. |

Example report validation:
```bash
./scripts/validate-report.py --all
```

---

## 9. Governance & Coordination Model

This repository is governed by the **APC Coordination Architecture** (`AGENTS.md`, `docs/context/complete-context.md`):

- **APC AI (Analyzer, Planner, Controller):** Operates as an external high-reasoning planning agent without direct filesystem access. Analyzes task progress, authors standalone prompts, reviews diffs, and maintains architectural invariants.
- **Local Coding Agents (Gemini, Claude Code, etc.):** Run locally on the codebase with full terminal and filesystem access to execute tasks in isolated Git worktrees (`task/<TASK-ID>`).
- **Source of Truth:** The repository files on disk are the sole source of truth (SSOT).
- **Four Unit-of-Work Deliverables:** Every completed task must provide:
  1. Staged and committed code on a task branch with a clean working tree.
  2. A standalone patch file in `patch/`.
  3. A verified task report in `docs/reports/<TASK-ID>-<agent>-<slug>.md`.
  4. Updated status in `docs/tasks/status.md` and locked decisions in `docs/decisions/decision-log.md`.

---

## 10. Roadmap & Project Phases

- [x] **Phase 0 — Inception, Scope Lock & Repository Foundation** (`ARCH-001`, `ARCH-002`)
  - Conceptual boundary, interfaces, linting toolchain, research index, and cross-platform tooling.
- [x] **Phase 1 — Core Infrastructure & Data Pipelines** (`CORE-001`–`CORE-005`)
  - Domain models, NASA POWER weather ingest, equipment audit (147.81 kW), synthetic bills, invariant test harness, and 8,760h baseline simulation.
- [ ] **Phase 2 — Parallel Model Tracks**
  - `DEM`: Academic schedule generator (`DEM-001`) and CDD/psychrometric cooling model (`DEM-002`).
  - `SOL`: Batac tilted irradiance/NOCT derating (`SOL-001`) and inverter clipping/BOS losses (`SOL-002`).
  - `BAT`: Time-stepped SoC tracking (`BAT-001`) and emergency reserve protection (`BAT-002`).
  - `OUT`: Stochastic Poisson/Lognormal outage sampler (`OUT-001`) and tiered load shedder (`OUT-002`).
- [ ] **Phase 3 — Integration, Simulation Engine & Verification**
  - Main simulation loop and scenario runner (`INT-001`), Monte Carlo parameter sweep (`INT-002`), full verification suite (`INT-003`), and AHP multi-criteria decision sizing recommendation (`INT-004`).

---

## 11. License & Citation

Developed for academic research and educational evaluation at the **College of Computing and Information Sciences (CCIS)**, **Mariano Marcos State University (MMSU)**, Batac City, Ilocos Norte, Philippines.
