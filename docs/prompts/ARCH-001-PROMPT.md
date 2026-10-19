# Standalone Task Prompt: ARCH-001

Copy and paste the text block below into a local agent session (Claude Code, Gemini CLI, Cursor, opencode):

```markdown
# TASK: ARCH-001 — Lock Scope, Conceptual Model & Interface Contracts

## Role & Worktree Instructions
- **Assigned Agent:** any (lead architectural / documentation agent)
- **Task ID:** ARCH-001
- **Branch / Worktree:** If running concurrently with ARCH-002 or another task, use a dedicated worktree:
  `./scripts/task-worktree.sh start ARCH-001`
  (or `git worktree add ../ccis-heat-load-backup-sim-ARCH-001 -b task/ARCH-001`)

## Orientation & Required Reading
Before writing, inspect these repository files in order:
1. `docs/context/complete-context.md` — project background and coordination model
2. `docs/tasks/status.md` — confirm ARCH-001 is open
3. `docs/decisions/decision-log.md` — review past decisions [D-01] through [D-11]
4. `docs/context/research-synthesis.md` — consolidated empirical parameters and formulas
5. `docs/tasks/high-level-tasks.md` — macro roadmap and exit gates

## Context & Objectives
This task formalizes the conceptual model of the CCIS Heat, Load and Backup Power Simulation, directly producing the content required for **Project Outline Sections 1, 2, and 3** of the course deliverable. Decisions [D-05] through [D-11] have been locked in `docs/decisions/decision-log.md`. Your goal is to translate these decisions and research parameters into a formal, rigorous specification document: `docs/context/conceptual-model.md`.

## Specific Scope & Deliverables
Create `docs/context/conceptual-model.md` containing the following complete sections:

1. **System Boundary & Physical Entities (Outline §1 & §2.1):**
   - Define the building entity: MMSU College of Computing and Information Sciences (CCIS), Batac, Ilocos Norte (18.06°N, 120.56°E).
   - Document the 18 dedicated rooms per [D-06]: 2 hyflex smart rooms, 6 lecture rooms, 1 COD room, 1 Dean + Secretary office, 2 faculty rooms, and 6 computer lab rooms. (Explicitly note: NO dedicated central server room; network switches distributed in IDF/office cabinets).
   - Document the sub-system entities: Rooftop Solar PV Array, Lithium Iron Phosphate (LFP) Battery Energy Storage System (BESS), Bidirectional Inverter, Utility Grid Connection (INEC), and Priority Load Controller.
   - External Environment: Ambient temperature, relative humidity, solar irradiance (GHI), and stochastic grid outages.

2. **State Variables, Events & Temporal Dynamics (Outline §3.1):**
   - **Time Step:** Hourly ($t = 1, \dots, 8760$).
   - **Continuous State Variables:** Battery State-of-Charge $SoC(t) \in [SoC_{\min}, C_{\text{bat}}]$, indoor thermal comfort state / cooling load $P_{\text{cool}}(t)$, solar power $P_{\text{pv}}(t)$, grid import $P_{\text{grid}}(t)$, unserved power $P_{\text{unserved}}(t)$.
   - **Discrete State Variables:** Grid connection state $S_{\text{grid}}(t) \in \{\text{UP}, \text{DOWN}\}$, load-shedding tier state $S_{\text{tier}}(t) \in \{\text{TIER\_1}, \text{TIER\_2}, \text{TIER\_3}\}$.
   - **Discrete Events:** Outage arrival event, outage restoration event, class period transition (occupied vs. unoccupied), battery exhaustion ($SoC = SoC_{\min}$).

3. **Performance Measures & Decision Variables (Outline §2.2):**
   - **Performance Measures:**
     - Annual Solar Fraction / Self-Sufficiency: $\text{SSR} = \frac{\sum P_{\text{solar\_used}}}{\sum P_{\text{demand}}}$
     - Annual Solar Self-Consumption: $\text{SCR} = \frac{\sum P_{\text{solar\_used}}}{\sum P_{\text{pv}}}$
     - Outage Hours Fully Covered: Hours with $S_{\text{grid}} = \text{DOWN}$ and $P_{\text{unserved}} = 0$.
     - Critical-Load Hours Covered: Hours where Tier 1 + Tier 2 loads are 100% met during blackouts.
     - Annual Unserved Energy (Loss of Energy Expectation): $\text{EUE} = \sum P_{\text{unserved}}$ (kWh).
     - Minimum State of Charge: $\min_{t} SoC(t)$ during storm/outage events.
   - **Decision Variables:**
     - Solar PV Capacity: $P_{\text{kWp}} \in \{0, 50, 100, 200\}\text{ kWp}$
     - Battery Energy Capacity: $C_{\text{bat}} \in \{0, 50, 100, 200\}\text{ kWh}$
     - Emergency Outage Reserve Fraction: $R_{\text{reserve}} \in [0.10, 0.50]$
     - Shedding Priority Rule: Automatic Tier 3 shed on grid failure; Tier 2 shed if $SoC < 0.20$.

4. **Interface Contract Specification (`HourlyRecord` & Function Protocols):**
   Define the exact dataclass schema and typing for the canonical simulation time-step record:
   ```python
   @dataclass(frozen=True)
   class HourlyRecord:
       hour: int                     # 1 to 8760
       timestamp: str                # ISO 8601 string (PST / UTC+8)
       temp_ambient_c: float         # Dry-bulb temperature (°C)
       ghi_w_m2: float               # Global Horizontal Irradiance (W/m²)
       demand_gross_kwh: float       # Total unconstrained electrical demand
       demand_served_kwh: float      # Actual demand served after shedding
       solar_generation_kwh: float   # AC solar generation
       solar_to_demand_kwh: float    # Direct PV self-consumption
       solar_to_battery_kwh: float   # PV charging energy
       solar_curtailed_kwh: float    # Excess generation curtailed or exported
       battery_soc_kwh: float        # Stored energy at end of hour
       battery_charge_kwh: float     # Energy into battery
       battery_discharge_kwh: float  # Energy out of battery
       grid_import_kwh: float        # Energy bought from utility
       unserved_load_kwh: float      # Deficit during outage
       grid_available: bool          # True if grid is UP, False if OUTAGE
       active_load_tier: int         # 1, 2, or 3
   ```
   Define the governing energy balance equation:
   $$\text{Solar} + \text{Grid} + \text{Discharge} = \text{Served Demand} + \text{Charge} + \text{Curtailment} \pm 10^{-5}\text{ kWh}$$

5. **Mermaid System & Logic Flowcharts (Outline §3.2):**
   - Provide a Mermaid diagram of the physical component connectivity.
   - Provide a Mermaid flowchart of the hourly simulation dispatch logic (checking grid status, comparing solar vs. demand, dispatching battery, applying tiered shedding).

## What NOT to Touch
- Do not implement Python code in `src/` (that belongs to ARCH-002 and CORE-001).
- Do not modify `docs/decisions/decision-log.md` (decisions D-01..D-11 are already locked).

## Verification & Acceptance Criteria
- [ ] `docs/context/conceptual-model.md` created with all 5 sections above.
- [ ] 18 CCIS rooms accurately documented (no server room; Dean/Sec, COD, 2 hyflex, 6 lecture, 2 faculty, 6 labs).
- [ ] Interface contract `HourlyRecord` complete and typed.
- [ ] All Mermaid flowcharts compile and render without Markdown syntax errors.
- [ ] Report created at `docs/reports/ARCH-001-[agent]-lock-conceptual-model.md` and passes `./scripts/validate-report.py`.
- [ ] `docs/tasks/status.md` updated for ARCH-001 and its subtasks.
```
