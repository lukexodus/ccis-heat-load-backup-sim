# Decision Log

**Append-only.** Never edit or delete a past entry — if a decision changes, add a new entry that supersedes it and say so explicitly ("supersedes entry [D-xx]").

This file exists so that across API-credit-limited handoffs between APC AI instances and zero-memory local agent sessions, a settled question is **never re-litigated from scratch** because nobody could find the earlier reasoning. When in doubt about whether something belongs here: if re-deriving it would cost more than one paragraph of reasoning, it belongs here.

**Format for each entry:**
- **[D-xx]** Decision title
- **Date / Session:** When it was locked
- **Decision:** What was locked or selected
- **Reasoning:** Why this choice was made over alternatives
- **Affects:** Components, interfaces, or tasks impacted

**Reserved Decision IDs:** Decision IDs are reserved per task by the APC AI in the task prompt, not invented on the fly by local agents. This prevents ID collisions during concurrent worktree tasks.

---

**[D-01]** Architecture baseline and repository governance locked.  
- **Date / Session:** Inception  
- **Decision:** Adopted APC (Analyzer, Planner, Controller) + Local Agent orchestration model with strict repository-as-source-of-truth governance.  
- **Reasoning:** Decouples high-level strategic reasoning and cross-session memory from filesystem-level implementation and execution, preventing hallucinated drifts and lost context across credit resets.  
- **Affects:** All documents, tasks, and development workflows.

**[D-02]** Project selected: CCIS Heat, Load and Backup Power Simulation.  
- **Date / Session:** 2026-10-19  
- **Decision:** Chose this idea over bunching, evacuation, misinformation, fire spread, dispatch and crowd-crush alternatives.  
- **Reasoning:** Local, defendable, fits continuous simulation, Monte Carlo and V&V, and needs no external agent-based tooling.  
- **Affects:** All tasks.

**[D-03]** No institutional data requests; use public and synthetic data only.  
- **Date / Session:** 2026-10-19  
- **Decision:** Replace MMSU bills and meter data with NASA POWER weather, a self-conducted equipment audit and synthetic mock bills. This supersedes the original idea's data plan.  
- **Reasoning:** The deadline is this week, and administrative turnaround is too slow and uncertain.  
- **Affects:** Data ingestion, calibration, V&V.

**[D-04]** Python (pandas, numpy, scipy, matplotlib) with pytest. *Proposed, pending confirmation that the course permits it.*  
- **Date / Session:** 2026-10-19  
- **Decision:** Implement in Python.  
- **Reasoning:** Course allows "any modelling and simulation software," and `AGENTS.md` already assumes pytest.  
- **Affects:** `src/`, `tests/`.

**[D-05]** Simulation temporal resolution locked to hourly time-step.  
- **Date / Session:** 2026-10-19  
- **Decision:** Execute the core continuous simulation on an hourly (8,760 hours/year) basis rather than daily.  
- **Reasoning:** Essential for capturing the physical coincidence between peak afternoon outdoor heat/cooling loads (11:00–16:00) and peak solar PV generation. Daily averaging suppresses diurnal cooling spikes and distorts battery state-of-charge cycling.  
- **Affects:** All domain models, weather ingestion, simulation engine, and interface contracts (`HourlyRecord`).

**[D-06]** CCIS building layout and archetype baseline locked.  
- **Date / Session:** 2026-10-19  
- **Decision:** Model the MMSU CCIS building as a ~2,500 m² 2-storey facility comprising 18 dedicated rooms: 2 hyflex smart rooms, 6 lecture rooms, 1 COD room, 1 Dean + Secretary office, 2 faculty rooms, and 6 computer lab rooms. No dedicated central server room (telecom/networking hardware distributed in IDF cabinets and office closets).  
- **Reasoning:** Confirmed by operator as local ground truth for MMSU CCIS. Sets equipment counts, occupancy profiles, and spatial power density.  
- **Affects:** `CORE-003`, `DEM-001`, `DEM-002`, `OUT-002`.

**[D-07]** Piecewise-linear Cooling Degree Day (CDD) heat-response model locked.  
- **Date / Session:** 2026-10-19  
- **Decision:** Model cooling electrical demand using a piecewise-linear CDD model with base temperature $T_{\text{base}} = 24.0^\circ\text{C}$, 4.0% load sensitivity increase per $1^\circ\text{C}$ rise above base, and a 20% latent cooling penalty for tropical relative humidity.  
- **Reasoning:** Grounded in empirical regressions from tropical Southeast Asian institutional audits (3–5%/°C sensitivity, 10–30% latent penalty) without requiring heavy transient thermodynamic solvers.  
- **Affects:** `DEM-002`, `INT-001`.

**[D-08]** Solar PV performance ratio and NOCT thermal derating locked.  
- **Date / Session:** 2026-10-19  
- **Decision:** Model rooftop solar PV AC generation with nominal PR = 0.77 (77%), Batac tilt = 15° True South, monocrystalline module temperature coefficient $\gamma = -0.40\%/^\circ\text{C}$ above 25°C, and $\text{NOCT} = 45^\circ\text{C} + 10^\circ\text{C}$ rooftop mounting thermal penalty. Target annual specific yield benchmark: ~1,300 kWh/kWp·yr.  
- **Reasoning:** Validated against empirical field monitoring study of 103 Philippine rooftop PV installations across Luzon (mean measured yield: 1,298 kWh/kWp·yr; PR range 0.70–0.80).  
- **Affects:** `SOL-001`, `SOL-002`, `INT-003`.

**[D-09]** Lithium Iron Phosphate (LFP) battery chemistry and dispatch logic locked.  
- **Date / Session:** 2026-10-19  
- **Decision:** Adopt Lithium Iron Phosphate (LFP / $\text{LiFePO}_4$) battery storage with 92% round-trip efficiency (RTE), 90% usable Depth of Discharge (DoD), 10% non-discretionary minimum SoC reserve floor, continuous limits of 0.5C charge and 1.0C discharge, and 4,000 cycles life. Dispatch priority: Self-consumption first (Solar → Demand → Battery → Grid; Deficit → Battery → Grid).  
- **Reasoning:** LFP is the Philippine industry standard for stationary BESS due to superior thermal safety in tropical climates ($>30^\circ\text{C}$) and high cycle durability compared to NMC or lead-acid.  
- **Affects:** `BAT-001`, `BAT-002`, `INT-001`.

**[D-10]** Priority-based critical load classification and shedding tiers locked.  
- **Date / Session:** 2026-10-19  
- **Decision:** Classify building electrical loads into three operational tiers: Tier 1 (Life safety: emergency exit lighting, fire alarms, ~2% peak, transfer <10s); Tier 2 (Operational continuity: telecom, core switches, Dean/COD offices, priority lab workstations, ~18% peak, transfer $\le 60$s); Tier 3 (Comfort HVAC & non-essential lighting, ~80% peak, shed immediately upon utility outage).  
- **Reasoning:** Conforms to Philippine Electrical Code (PEC) and NFPA 110. Shedding Tier 3 extends battery survival runtime by 4× to 5× during sustained grid blackouts.  
- **Affects:** `OUT-002`, `INT-001`, `DEC-002`.

**[D-11]** Stochastic outage generation and typhoon coupling locked.  
- **Date / Session:** 2026-10-19  
- **Decision:** Model utility outages using a Poisson arrival process and Lognormal duration distributions. Normal Year: $\lambda = 3.0\text{ outages/yr}$, duration $\text{Lognormal}(\mu=1.2, \sigma=0.8)$ (median 3.3h, mean 4h). Typhoon Year: $\lambda = 8.0\text{ outages/yr}$, duration $\text{Lognormal}(\mu=2.3, \sigma=1.0)$ (median 10h, mean 14h, tails 24–48h), coupled with 3–5 consecutive days of depressed solar irradiance (20–30% normal GHI).  
- **Reasoning:** Calibrated against empirical rural cooperative outage data (ALECO SAIFI ~53) and DOE Super Typhoon Nando post-disaster records for Region I / INEC (100% blackout, 66% 48h restoration).  
- **Affects:** `OUT-001`, `INT-002`.

**[D-16]** CCIS equipment inventory, load density, and synthetic billing calibration baseline locked.  
- **Date / Session:** 2026-10-19  
- **Decision:** Parameterize the MMSU CCIS 18-room facility (~2,500 m²) with a bottom-up equipment audit of 140.0 kW total connected capacity across 38 distinct equipment categories. Loads are strictly mapped to the three priority tiers defined in [D-10]: Tier 1 life safety (1.21 kW connected, ~1% connected, ~1.5% peak; 24/7 continuous egress, FACP, CCTV), Tier 2 operational continuity (17.5 kW connected, ~12% connected, ~17% peak; 24/7 IDF switches, spot cooling, Dean/COD offices, faculty PCs, and water pump), and Tier 3 comfort cooling & sheddable loads (121.3 kW connected, ~87% connected, ~81% peak; lab PCs, lecture rooms, and split AC units). Synthetic 12-month billing calibrated with Philippine SUC academic schedule, Batac seasonal cooling degree factors (0.85–1.25), 10% nighttime standby baseload (8.0 kW), and Gaussian meter noise ($\sigma = 2.5\%$). Yields annual consumption of ~398,500 kWh/yr and annual Energy Use Intensity (EUI) of 159.41 kWh/m²·yr, strictly conforming to the regional benchmark band of 150–300 kWh/m²·yr.  
- **Reasoning:** Reconciles the operator-confirmed 18-room spatial ground truth [D-06] with verified hardware power ratings (dual 3.0 HP inverter ACs and 40 desktop PCs per lab to reject high thermal heat loads in Batac). Replaces inaccessible real utility bills with an auditable, reproducible synthetic calibration baseline satisfying the zero-institutional-data constraint [D-03].  
- **Affects:** `CORE-003`, `CORE-005`, `DEM-001`, `DEM-002`, `OUT-002`, `INT-001`.

**[D-17]** Battery configurable emergency outage reserve allocation locked.  
- **Date / Session:** 2026-10-20  
- **Decision:** Establish `Battery.emergency_reserve_pct` with a provisional default value of 0.20 (20% of rated capacity), representing a dedicated operational blackout reserve buffer. This parameter is distinct from and additional to the non-discretionary 10% minimum state-of-charge protection floor ($SoC_{\text{min}} = 0.10 \times C_{\text{bat}}$) locked in [D-09]. It is configurable across $[0.10, 0.50]$ to support the outage resilience sweeps in `BAT-002.2` and multi-criteria decision analysis in `DEC-002`.  
- **Reasoning:** While [D-09] protects battery cell physical longevity by preventing deep discharge below 10% SoC under all conditions, resilience during extended blackouts requires an operational buffer held in reserve rather than depleted during daily evening peak load. A default 20% allocation ensures critical Tier 1 and Tier 2 loads can sustain initial transfer and runtime during unanticipated utility outages while preserving the cell longevity floor.  
- **Affects:** `Battery`, `BAT-001`, `BAT-002`, `INT-001`, `DEC-002`.

**[D-18]** CCIS usable rooftop solar PV area sizing constraint locked.  
- **Date / Session:** 2026-10-20  
- **Decision:** Parameterize the CCIS facility with a maximum usable unshaded rooftop PV mounting area of 1,200 m² (`Building.usable_rooftop_area_m2 = 1200.0`), tagged as an explicit `[ASSUMPTION]`. At a commercial monocrystalline packing density of 6.0 m²/kWp (~167 W/m² module rating accounting for maintenance walkways and inter-row spacing), this directly caps maximum rooftop solar capacity at 200 kWp, bounding the project's scenario matrix ($P_{\text{kWp}} \in \{0, 50, 100, 200\}\text{ kWp}$).  
- **Reasoning:** Conforms to physical building geometry: a 2-storey building of ~2,500 m² gross floor area has a building footprint of ~1,250 m². Deducting ~50 m² for parapets, rooftop access, and mechanical HVAC compressor clearances yields ~1,200 m² of usable racking space.  
- **Affects:** `Building`, `SOL-001`, `SOL-002`, `INT-003`.

**[D-19]** Equipment audit connected-load and tier-percentage summary figures corrected.  
- **Date / Session:** 2026-10-20  
- **Decision:** Corrects the connected-load and tier-percentage figures stated in [D-16]; the underlying equipment list (38 item categories across 18 rooms plus infrastructure), tier assignments, and EUI conclusion are unchanged — only the summary numbers in prose were wrong. Recomputed directly from `data/fixtures/equipment-audit-ccis.csv`:  
  - Total connected electrical capacity: **147.81 kW** (147.805 kW), not 140.0 kW.  
  - Tier 1 (Life safety): **1.215 kW** (~0.82% of connected load; ~1.5% peak), 4 items.  
  - Tier 2 (Operational continuity): **15.36 kW** (~10.39% of connected load; ~17% peak), 16 items.  
  - Tier 3 (Comfort cooling & sheddable loads): **131.23 kW** (~88.79% of connected load; ~81% peak), 18 items.  
  Re-verified downstream billing and EUI: Annual electricity consumption remains **398,536.77 kWh/yr**, yielding an annual Energy Use Intensity (EUI) of **159.41 kWh/m²·yr**, strictly within the regional benchmark band of 150.0–300.0 kWh/m²·yr.  
- **Reasoning:** In `CORE-003`, equipment line counts and ratings were upgraded during final calibration (including student PCs from 228 to 240 units to reflect 40 PCs/lab, and dual 3.0 HP lab AC units to 2.8 kW for Batac heat conditions). The synthetic bill fixture was correctly computed from the final CSV, but the prose in [D-16] and the initial report retained pre-final draft totals (140.0 kW).  
- **Affects:** `CORE-003`, `CORE-003.5`, `CORE-005`, `DEM-001`, `DEM-002`, `OUT-002`.

**[D-20]** NASA POWER native hourly ingestion, timezone alignment, offline fixture selection, and 8,760-hour standardization locked.  
- **Date / Session:** 2026-10-20  
- **Decision:**
  1. Offline weather fixtures are ingested directly from NASA POWER's native hourly product (`temporal/hourly/point`, 2001–present, `community=RE`) for Batac, Ilocos Norte (`18.06°N, 120.56°E`), with parameters `T2M` (dry-bulb temperature), `RH2M` (relative humidity), and `ALLSKY_SFC_SW_DWN` (all-sky surface shortwave downward irradiance). Native hourly empirical data was confirmed to completely cover Batac with zero missing values across target years, rendering synthetic daily-to-hourly disaggregation unnecessary for canonical fixtures.
  2. Baseline representative year is locked to **2019** (non-leap year, 8,760 hours, annual mean temperature 26.44°C, annual solar insolation 1,900.6 kWh/m²·yr).
  3. Anomalous hot year is locked to **2016** (confirmed 2015–2016 super El Niño event in Northern Luzon: peak temperature 36.64°C, 25 days with $T_{\max} \ge 34^\circ\text{C}$, 11 days $\ge 35^\circ\text{C}$, April–May mean 29.18°C).
  4. Leap-year standardization: 2016 leap year (8,784 hours) is standardized to exactly 8,760 hours by omitting February 29 per ASHRAE/TMY3 convention to preserve the continuous 8,760-hour contract of [D-05].
  5. Timezone alignment: NASA POWER native hourly data is requested in Local Solar Time (LST), which for Batac (`120.56°E`, within 2.2 minutes of the 120°E UTC+8 central meridian) is localized directly to Philippine Standard Time (PST = UTC+8), preserving true diurnal solar noon at hour 12 (12:00 PST). UTC ingestion with a +8h conversion is also supported and verified.
  6. Implemented an auxiliary physical `DailyDisaggregator` (half-sine solar geometry irradiance with strict energy conservation, diurnal sinusoidal temperature, and Tetens vapor pressure psychrometrics) as a fallback for daily scenario inputs.
  7. Implemented dedicated `src/ccis_sim/weather/` subpackage (with re-exports in `src/ccis_sim/core/weather.py`) for modular weather ingestion and caching.
- **Reasoning:** Confirms empirical data availability directly from NASA POWER MERRA-2/CERES hourly product for Batac, avoiding synthetic disaggregation approximations for canonical simulation baselines. Preserves strict energy and state vector contracts across 8,760 annual hours [D-05].
- **Affects:** `CORE-002`, `CORE-005`, `DEM-002`, `SOL-001`, `INT-001`.

**[D-21]** Cumulative energy conservation tolerance scaling and battery boundary verification methodology locked.  
- **Date / Session:** 2026-10-20  
- **Decision:**
  1. The shared test harness checks per-hour energy conservation against $\epsilon_{\text{hour}} = 10^{-5}\text{ kWh}$ using the canonical formula:
     $$\text{residual}_t = |(\text{solar}_t + \text{grid}_t + \text{bat\_dis}_t) - (\text{demand\_served}_t + \text{bat\_chg}_t + \text{solar\_curt}_t)|$$
     reusing `HourlyRecord.energy_balance_residual_kwh` and `HourlyRecord.is_energy_conserved()`.
  2. Cumulative time-series conservation tolerance across $N$ hours scales statistically as:
     $$\text{tolerance}_{\text{cum}} = \max\left(\epsilon_{\text{hour}},\; \sqrt{N} \times \epsilon_{\text{hour}}\right)$$
     For an 8,760-hour annual simulation run, $\text{tolerance}_{\text{cum}} = \sqrt{8760} \times 10^{-5} \approx 9.359 \times 10^{-4}\text{ kWh}$ (~$0.001\text{ kWh}$). Cumulative conservation evaluates the absolute net drift:
     $$\Delta E_{\text{net}} = \left| \sum_{t=1}^N \left[(\text{solar}_t + \text{grid}_t + \text{bat\_dis}_t) - (\text{demand\_served}_t + \text{bat\_chg}_t + \text{solar\_curt}_t)\right] \right|$$
  3. Battery boundary validator enforces four physical invariants:
     - Hard physical bounds: $0 \le SoC(t) \le C_{\text{bat}}$.
     - Non-discretionary minimum protection floor: $SoC(t) \ge SoC_{\min} = 0.10 \times C_{\text{bat}}$ [D-09] during normal operation (`grid_available == True` or `active_load_tier == 3`). Drawdown below $SoC_{\min}$ (down to 0) is permitted only when `allow_emergency_drawdown=True` during active utility blackouts (`grid_available == False` and `active_load_tier < 3`).
     - Continuous C-rate power limits: $P_{\text{chg}}(t) \le 0.5\text{C}$ and $P_{\text{dis}}(t) \le 1.0\text{C}$ (evaluated over $\Delta t = 1.0\text{h}$).
     - Mutual exclusivity: simultaneous charging and discharging in the same hour ($P_{\text{chg}} > 10^{-6}\text{ kWh}$ and $P_{\text{dis}} > 10^{-6}\text{ kWh}$) is strictly prohibited.
  4. Provides a reusable 48-hour golden reference fixture (`create_golden_scenario()`) covering all microgrid operating regimes with exact $0.000000\text{ kWh}$ residual.
- **Reasoning:** Zero-mean IEEE 754 floating-point rounding jitter across $N$ independent steps behaves as a 1D random walk with standard deviation $\sigma_N = \sqrt{N} \epsilon$. Scaling cumulative tolerance by $\sqrt{N}$ accommodates harmless numerical rounding while rigorously tripping on any systematic numerical leakage or bias (e.g. an uncorrected bias of $0.9 \times 10^{-5}\text{ kWh/hr}$ accumulates to $0.07884\text{ kWh}$, which is ~84× the allowable threshold, triggering an immediate failure).
- **Affects:** `CORE-004`, `CORE-005`, `DEM-001`, `DEM-002`, `BAT-001`, `BAT-002`, `SOL-001`, `OUT-001`, `INT-001`, `INT-002`, `INT-003`.

**[D-22]** Windows developer interoperability, script parity, and repository line-ending normalization locked.  
- **Date / Session:** 2026-10-20  
- **Decision:**  
  1. Full cross-platform parity between Linux/macOS and Windows developer environments:
     - Implemented native PowerShell (`.ps1`) scripts and Windows Command Prompt (`.bat`) wrappers for all repository automation tools: `apc-bundle` (`.bat`, `.ps1`), `task-worktree` (`.bat`, `.ps1`), `validate-report` (`.bat`, `.ps1`), and `manage-decisions` (`.bat`, `.ps1`).
     - Batch wrappers invoke PowerShell with `-NoProfile -ExecutionPolicy Bypass -File` to prevent Windows execution policy restrictions from blocking developer workflows, and automatically auto-detect `pwsh` (PowerShell Core) or `powershell.exe` (Windows PowerShell).
     - Python runners dynamically detect `py -3`, `python`, or `python3` across Windows environments.
     - `task-worktree.sh` and `apc-bundle.sh` hardened with fallback detection for `python` on Windows Git Bash and GNU tree verification to avoid clashes with Windows `tree.com`.
  2. Repository-wide line-ending normalization via `.gitattributes`:
     - Global default `* text=auto eol=lf`.
     - Explicit `*.bat` and `*.cmd` locked to `eol=crlf` to prevent CMD parser anomalies.
     - Shell scripts `*.sh` and PowerShell `*.ps1` locked to `eol=lf` to prevent syntax corruption in WSL/Git Bash/Linux CI.
     - Source files (`*.py`), documentation (`*.md`), and data files (`*.csv`, `*.toml`, `*.json`) locked to `eol=lf`.
     - Binary asset patterns explicitly flagged as `binary`.
- **Reasoning:** Accommodates Windows teammates without requiring WSL, third-party shells, or manual line-ending conversions, while ensuring Git does not introduce CRLF corruption into Linux/WSL environments.  
- **Affects:** All developers, `scripts/`, `.gitattributes`, `docs/guide/COLLABORATOR-GUIDE.md`.

**[D-23]** Baseline placeholder demand method, calibration target, and Phase 1 exit gate metrics locked.  
- **Date / Session:** 2026-10-20  
- **Decision:**
  1. For the Phase 1 exit-gate baseline smoke test (`CORE-005`), implement a lightweight, isolated placeholder demand model:
     - Baseload: 10% continuous 24/7 standby power (~14.78 kW) for IDF switches, telecom headend, and life safety egress lighting.
     - Scheduled Occupancy: Documented hourly diurnal step profile (weekdays: 08:00–12:00 at 45%, 12:00–13:00 at 30%, 13:00–17:00 at 50%, 17:00–19:00 at 20%; Saturdays: 08:00–13:00 at 15%; Sundays: 0% occupancy).
     - Cooling Response: Piecewise-linear temperature adjustment adding $+4.0\%/^\circ\text{C}$ to daytime active cooling equipment load when ambient temperature exceeds $T_{\text{base}} = 24.0^\circ\text{C}$ per [D-07].
  2. The placeholder demand is scaled by a single fixed calibration factor ($c_{\text{calib}} = 1.22857563$) so that the 2019 baseline annual electricity consumption lands on **398,525.00 kWh/yr**, yielding an annual Energy Use Intensity (EUI) of **159.4100 kWh/m²·yr**, strictly matching the target benchmark established in [D-16]/[D-19] and the 150.0–300.0 kWh/m²·yr regional benchmark band.
  3. Locked baseline headline figures for the 2019 baseline weather fixture (`Building.gross_floor_area_m2 = 2500.0`):
     - Annual Consumption: 398,525.00 kWh/yr
     - Annual EUI: 159.41 kWh/m²·yr
     - Peak Electrical Demand: 124.44 kW (occurring at Hour 2030, 2019-03-26T13:00:00+08:00)
     - Annual Load Factor: 0.3656 (36.56%)
  4. Climate Sensitivity (2016 anomalous hot year, un-tuned): Peak electrical demand reaches **125.55 kW** (+1.11 kW, +0.89% increase driven by peak El Niño heat at 2016-04-19T13:00:00+08:00), while annual consumption totals 398,251.21 kWh (EUI: 159.30 kWh/m²·yr; -273.79 kWh, -0.07% delta due to 2016 calendar having 260 weekdays vs 261 in 2019).
  5. The placeholder model is explicitly isolated in `src/ccis_sim/integration/baseline.py` and will be formally superseded by the bottom-up academic diversity schedules in `DEM-001` and transient psychrometric cooling response in `DEM-002`.
- **Reasoning:** Demonstrates end-to-end continuous 8,760-hour execution and verification harness closure for Phase 1 without pre-empting the detailed physics or empirical regressions reserved for Phase 2 demand sub-models.
- **Affects:** `CORE-005`, `DEM-001`, `DEM-002`, `INT-001`.



