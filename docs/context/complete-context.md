# Complete Context — CCIS Heat, Load and Backup Power Simulation

Welcome to CCIS Heat, Load and Backup Power Simulation. This document is the primary orientation file for both
the APC AI (Analyzer, Planner, Controller) and all local coding agents. Read this
before reading individual task specs.

---

## 1. What this project is

CCIS Heat, Load and Backup Power Simulation: a Python model of a Batac college building’s electricity demand under heat waves, with rooftop solar and battery backup tested through Monte Carlo outage scenarios.

### Core Objectives
1. **Primary Goal:** Answer: how much does Batac's heat raise CCIS electricity use, and how much of that load can rooftop solar + battery cover during a heat wave or outage? Deliver a working simulation, scenario charts, a sizing recommendation, and the course report (Project Outline sections 1–10).
2. **Success Metrics:** Daily energy balance holds in every run; battery stays within [0, capacity]; modelled solar yield and building EUI fall within published plausible ranges; Monte Carlo output reported as P5/P50/P95 with confidence intervals; one defensible recommendation (e.g. smallest solar+battery combo covering a 12-hour outage on a hot day).
3. **Key Constraints:** One-week deadline. Python (pandas, numpy, scipy, matplotlib). No institutional data requests. Scope is CCIS only. Results reported in kWh, not pesos. Costs, if shown, are labelled assumptions.

---

## 2. System Architecture & Components

Time-stepped (continuous) energy-balance model, daily and later hourly, wrapped in a Monte Carlo runner:
- **Demand:** bottom-up equipment load × schedule, plus a temperature response (cooling rises above a threshold; lower on breaks and holidays).
- **Solar:** E = P_kWp × H_sun × PR, with PR about 0.75–0.80.
- **Battery:** charge from surplus, discharge to cover the gap, and a reserve for outages. Unserved load is whatever remains during an outage.
- **Outages:** discrete events with a random arrival time and duration.
- **Monte Carlo and scenarios:** replay historical weather years, add outages, and sweep weather (normal, +2 °C, hottest year) × solar (0/50/100/200 kWp) × battery × outage length (4/12/24 h).
- **Decision layer:** AHP or weighted scoring over coverage, outage hours covered and cost.

- **`src`**: Core implementation logic.
- **`tests/`**: Unit, integration, and conformance suites.
- **`docs/`**: Context, tasks, decision records, and per-task reports.
- **`scripts/`**: Automation, deployment, bundling, and workflow helpers.

---

## 3. Data Sources, Interfaces, and External Contracts

- **Weather:** NASA POWER daily data for Batac (about 18.06°N, 120.56°E), 1981–present. Parameters: T2M, T2M_MAX, T2M_MIN, RH2M, ALLSKY_SFC_SW_DWN. `-999` means missing. Cache the download as a committed CSV fixture.
- **Demand inputs:** an equipment audit CSV (item, count, rated kW, hours/day), plus a floor area assumption.
- **Mock bills (synthetic):** generated from the demand model plus noise. Clearly labelled synthetic; real bills would be used only for later calibration.
- **Outage generator:** exponential inter-arrival times and a lognormal or Weibull duration. Parameters come from published reliability figures or are declared as assumptions.
- **Solar and battery parameters:** from published ranges, cited in IEEE format and labelled as assumptions.
- **Interface contract (to lock in ARCH-001):** one `DayState`/hourly record with demand, solar, battery SoC, grid import and unserved load.

---

## 4. Project Structure & Where Things Live

```text
├── AGENTS.md                   # Operational constitution for local agents
├── docs/
│   ├── context/
│   │   ├── complete-context.md # This orientation document
│   │   ├── apc-handoff-template.md # Template for inter-session APC handoffs
│   │   ├── apc-bundle-quickref.md  # Bundle command reference
│   │   └── repo-tree.txt       # Auto-generated snapshot of repository layout
│   ├── tasks/
│   │   ├── high-level-tasks.md # Phased macro plan & roadmap
│   │   └── status.md           # Live per-task status tracker
│   ├── decisions/
│   │   └── decision-log.md     # Append-only immutable architectural decision log
│   ├── reports/                # Completed task reports (one per task)
│   └── prompts/                # Standalone prompt archive
├── scripts/
│   ├── apc-bundle.sh           # Safe packaging tool for APC context bundles
│   └── task-worktree.sh        # Git worktree management script for parallel tasks
├── src                 # Source code
└── tests/                      # Automated test suites
```

---

## 5. The Coordination Model (Why this setup exists)

This project is coordinated by lukexodus relaying work between two distinct entities:

1. **The APC AI ("Analyzer, Planner, Controller")**:
   - High-reasoning AI running in an external chat or API session (Claude Web, ChatGPT, Gemini, etc.).
   - Has **NO filesystem access** to this repository.
   - Plans phases, designs architecture, inspects reports/diffs, enforces consistency, reserves decision IDs, and generates **STANDALONE PROMPTS**.
   - Ephemeral memory: Context resets across sessions or when credit limits are reached. Handoffs are managed via `apc-handoff-template.md`.
2. **Local Coding Agents** (Claude Code, Gemini, opencode, Cursor, etc.):
   - Run on lukexodus's local machine with **full filesystem access and CLI execution**.
   - Implement features, run tests, verify assumptions against actual files, and generate unified git diffs.
   - Ephemeral memory: Each invocation is zero-memory. Agents must consult repo files to discover state.

### Key Operational Rules:
- **The Repo is the Sole Source of Truth (SSOT):** No chat transcript or AI memory is authoritative. If a statement conflicts with what is on disk, the disk is right.
- **Deltas, Not Full Files:** Code and documentation changes are reported as unified git diffs (`git diff`) to conserve context and prevent merge hazards.
- **Mandatory Reporting:** Every completed task must generate a dedicated report file in `docs/reports/`. An undocumented task is equivalent to a task that never happened.
- **Isolated Parallel Worktrees:** Concurrent tasks must operate in dedicated git worktrees (`task/<TASK-ID>`).

---

## 6. Open Items & Active Risks

[List known ambiguities, unresolved design choices, or active risks being investigated.]
- Open Item 1: Real MMSU bills are no longer required. The mock-bill validation is weaker than real-data validation, so frame V&V as verification plus sensitivity analysis plus benchmark plausibility checks.
- Open Item 2: No discrete-event or agent-based component. Frame outages as discrete events (arrival, duration, state change) in the write-up.
- Open Item 3: Confirm that the course accepts Python rather than R.
- Open Item 4: Confirm whether the NASA POWER grid cell is representative of Batac.
