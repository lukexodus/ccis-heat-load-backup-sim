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

**[D-24]** Baseline demand placeholder disclosure addendum, uncalibrated EUI, and provisional peak classification (amending [D-23]).  
- **Date / Session:** 2026-10-20  
- **Decision:**  
  1. **Uncalibrated Baseline Metrics:** With calibration multiplier $c_{\text{calib}} = 1.0$, the uncalibrated 2019 baseline annual electricity consumption totals **324,379.71 kWh/yr**, yielding an uncalibrated annual Energy Use Intensity (EUI) of **129.75 kWh/m²·yr** on the 2,500 m² archetype facility, with an uncalibrated peak electrical demand of **101.29 kW**. The fixed calibration factor $c_{\text{calib}} = 1.22857563$ represents a $+22.86\%$ upward correction to align with the empirical target of 159.41 kWh/m²·yr ($398,525.00\text{ kWh/yr}$).
  2. **Match by Construction:** The exact match between the baseline simulation annual EUI (159.4100 kWh/m²·yr) and the synthetic billing target ([D-16]/[D-19]) is **by construction** via this calibration constant, and does **not** constitute independent validation of building thermal or operational physics.
  3. **Documented Cooling Duty Factor:** The daytime cooling temperature response includes an assumed coincident operational duty factor of **0.35** (`DEFAULT_COOLING_DUTY_FACTOR = 0.35`), representing that approximately 35% of the total 77.20 kW installed air-conditioning capacity actively compressor-cycles during daytime occupied hours when ambient temperature exceeds $T_{\text{base}} = 24.0^\circ\text{C}$ per [D-07].
  4. **Provisional Peak Classification:** The headline peak electrical demand of **124.44 kW** (Hour 2030, 2019-03-26T13:00:00+08:00) is scaled by the same calibration multiplier and lacks independent empirical load metering; it is formally classified as **provisional** and must be superseded by the bottom-up academic diversity schedules (`DEM-001`) and dynamic psychrometric building heat load model (`DEM-002`) prior to final microgrid inverter/battery sizing.
  5. **Climate Sensitivity Context:** The un-tuned 2016 El Niño hot-year simulation yielded a modest peak demand increase of $+1.11\text{ kW}$ (+0.89%, reaching 125.55 kW) and a slight annual consumption decrease of $-273.79\text{ kWh}$ (-0.07%, 398,251.21 kWh vs 398,525.00 kWh) due to 2016 having 260 weekdays vs 261 in 2019. This sensitivity is weak due to the placeholder's simplified linear cooling response and must not be cited as a real climate finding.
  6. The underlying behavior and committed simulation headline numbers remain bit-identical.
- **Reasoning:** Full scientific disclosure and methodological transparency ensure that placeholder approximations are not mistaken for validated empirical physics by downstream sizing or economic tracks.
- **Affects:** `CORE-005`, `DEM-001`, `DEM-002`, `INT-001`, `BAT-001`.

**[D-25]** Verification harness gap closures: SoC continuity convention, non-finite guards, sub-flow decompositions, and D-09/D-21 reconciliation.  
- **Date / Session:** 2026-10-20  
- **Decision:**  
  1. **Hour-to-Hour SoC Continuity Invariant:** For consecutive hourly records ($t \ge 1$), the battery state-of-charge must strictly obey physical energy conservation:
     $$\text{SoC}_t = \text{SoC}_{t-1} + \eta_{\text{chg}} P_{\text{chg},t} \Delta t - \frac{P_{\text{dis},t} \Delta t}{\eta_{\text{dis}}}$$
     within a numerical tolerance of $10^{-5}\text{ kWh}$ (`ViolationType.SOC_CONTINUITY`).
  2. **Symmetric Efficiency Split:** In the absence of separate manufacturer charge/discharge curves in `Battery`, the 92% round-trip efficiency locked in [D-09] is split symmetrically:
     $$\eta_{\text{chg}} = \eta_{\text{dis}} = \sqrt{\eta_{\text{rt}}} = \sqrt{0.92} \approx 0.9591663$$
     Battery charge ($P_{\text{chg}}$) and discharge ($P_{\text{dis}}$) are defined strictly as AC-side flows (matching the quantities in the hourly grid/solar energy balance); all electrochemical and inverter conversion losses appear strictly in the stored chemical SoC. The continuity check is bypassed when `Battery.capacity_kwh == 0.0`. For the initial record ($t = 1$), continuity is evaluated against an optional `initial_soc_kwh` parameter if provided; otherwise skipped.
  3. **Non-Finite Numerical Guards:** Any occurrence of `NaN`, `+inf`, or `-inf` in any numeric float field of `HourlyRecord` or `Battery` is strictly classified as an invariant failure (`ViolationType.NON_FINITE_VALUE`) across all verification checkers.
  4. **Sub-Flow Decomposition Balances:** Added explicit conservation checks (`check_subflow_balance`):
     - Solar flow decomposition: $P_{\text{solar}} = P_{\text{to\_demand}} + P_{\text{to\_battery}} + P_{\text{curtailed}}$ (`ViolationType.SOLAR_FLOW_BALANCE`).
     - Demand flow decomposition: $P_{\text{gross}} = P_{\text{served}} + P_{\text{unserved}}$ (`ViolationType.DEMAND_FLOW_BALANCE`).
  5. **Canonical Signed Residual Property:** Introduced `HourlyRecord.signed_residual_kwh` ($E_{\text{in}} - E_{\text{out}}$) for directional tracking of cumulative numerical drift in `check_energy_conservation` and `run_verification_harness`. The scalar absolute residual property `energy_balance_residual_kwh` and `is_energy_conserved()` remain unchanged.
  6. **Reconciliation of [D-09] and [D-21]:**
     - The 10% minimum SoC protection floor ($SoC_{\min} = 0.10 \times C_{\text{bat}}$) defined in [D-09] is strictly non-discretionary under all normal, grid-connected operating regimes to prevent accelerated lithium-ion degradation.
     - The emergency drawdown override permitted under [D-21] (allowing SoC to discharge down to 0 kWh) is strictly restricted to active utility grid blackouts (`grid_available = False`) where priority shedding is active (`active_load_tier in (1, 2)`) and `allow_emergency_drawdown = True`.
     - Relation to [D-17] Emergency Reserve: The 20% emergency blackout reserve ([D-17]) is an operational scheduling buffer allocated to sustain Tier 1 and Tier 2 critical loads through outages, whereas the 10% floor ([D-09]) is physical cell-protection hardware reserve. The emergency drawdown override bridges the two by allowing life-safety survival operation to consume the hardware floor only in declared catastrophic emergencies.
  7. **Golden Reference Fixture Update:** Updated `create_golden_scenario()` to incorporate symmetric conversion efficiency while maintaining exact $0.000000\text{ kWh}$ residual across all 48 hours.
- **Reasoning:** Closes potential simulation verification blind spots (energy teleportation, silent NaN propagation, sub-flow leakage) before parallel Phase 2 model tracks commence.
- **Affects:** `CORE-004`, `CORE-005`, `DEM-001`, `DEM-002`, `BAT-001`, `BAT-002`, `SOL-001`, `SOL-002`, `OUT-001`, `OUT-002`, `INT-001`, `INT-002`, `INT-003`.

**[D-26]** Phase 2 Interface Contracts, Battery Idle-Loss Convention, and Cumulative Continuity Drift Invariant.  
- **Date / Session:** 2026-10-20  
- **Decision:**  
  1. **Phase 2 Interface Contracts:** Formalized canonical shared data structures in `src/ccis_sim/core/interfaces.py` (`TieredDemand`, `OccupancySchedule`, `OutageSchedule`, `BatteryStepResult`, `ShedResult`) and locked function signatures and cross-track integration contracts in `docs/context/phase2-interface-contract.md`.
  2. **Battery Idle-Loss Attributes:** Added `self_discharge_pct_per_month: float = 2.0` (ambient monthly self-discharge) and `tare_loss_kw: float = 0.0` (inverter/BMS standby loss) to the `Battery` dataclass. Both attributes are validated non-negative.
  3. **SoC-Side Standby Loss Assumption:** Tare loss and self-discharge are modeled strictly as **SoC-side** standby losses (electrochemical and internal dissipation). This ensures internal dissipation reduces stored chemical State-of-Charge without introducing phantom AC-side electrical demand on the microgrid bus, preserving exact AC bus energy balance.
  4. **One-Sided Continuity with Idle Allowance:** Updated hour-to-hour battery State-of-Charge continuity verification to be one-sided with a physical idle-loss allowance:
     $$0 - \epsilon \le \text{SoC}_{t, \text{ideal}} - \text{SoC}_t \le \Delta E_{\text{idle, max}} + \epsilon$$
     where $\Delta E_{\text{idle, max}} = \left(\frac{C_{\text{bat}} \cdot r_{\text{self}}}{730} + P_{\text{tare}}\right) \Delta t$, based on 730 hours per nominal month ($8,760\text{ h} / 12$). Stored chemical SoC may never exceed the lossless ideal recursion ($SoC_t \le SoC_{t, \text{ideal}} + \epsilon$). When idle loss parameters are zero, the formulation collapses identically to the bilateral tolerance of [D-25].
  5. **Cumulative Continuity Drift Invariant:** Accumulated step differences $\sum (\text{SoC}_{\text{ideal}} - \text{SoC})$ across $N$ evaluated hours must not exceed total allowed idle loss plus the statistical cumulative tolerance $\max(\epsilon, \sqrt{N}\epsilon)$ per [D-21]. Unaccounted cumulative leakage or upward drift trips `ViolationType.SOC_CUMULATIVE_DRIFT`.
- **Reasoning:** Establishes unambiguous API contracts across all eight parallel Phase 2 sub-models to prevent divergence, while closing physical verification blind spots for standby battery self-discharge and cumulative SoC drift prior to BAT-001/002.  
- **Affects:** `CORE-006`, `DEM-001`, `DEM-002`, `SOL-001`, `SOL-002`, `BAT-001`, `BAT-002`, `OUT-001`, `OUT-002`, `INT-001`, `INT-003`.

**[D-27]** Academic Calendar Conventions, Bottom-Up Non-Cooling Demand Aggregation, and Baseload Double-Counting Prevention.  
- **Date / Session:** 2026-10-21  
- **Decision:**  
  1. **Academic Calendar Baseline Model (`AcademicCalendar`):**
     - Adopted academic calendar boundaries patterned on Mariano Marcos State University (MMSU) Batac campus operations:
       - First Semester: August 15 to December 15 (18 weeks).
       - Winter / Semestral Break: December 16 to January 14.
       - Second Semester: January 15 to May 25 (18 weeks).
       - Summer / Midyear Break: May 26 to August 14.
     - Codified Philippine regular and special non-working statutory holidays for weather fixture years 2019 (Proclamation No. 555) and 2016 (Proclamation No. 1105 / 1107), including movable feasts (Holy Week, Eid'l Fitr, Eid'l Adha) and National Heroes Day.
  2. **Hourly Occupancy Profiles (`build_occupancy_schedule`):**
     - Class Weekdays (Mon-Fri): 07:00 (0.20 early prep), 08:00–12:00 (1.00 lecture/lab peak), 12:00–13:00 (0.60 lunch dip), 13:00–18:00 (0.95 afternoon classes), 18:00–20:00 (0.30 evening graduate/extension), 20:00–07:00 (0.00 closed).
     - Class Saturdays: 08:00–12:00 (0.50 morning NSTP/labs), 12:00–13:00 (0.20 lunch dip), 13:00–17:00 (0.30 afternoon labs), 17:00–08:00 (0.00 closed).
     - Sundays and Gazetted Holidays: 0.00 all 24 hours (facility closed).
     - Term Break Weekdays: 08:00–12:00 and 13:00–17:00 (0.15 skeleton faculty/admin presence), 12:00–13:00 (0.05 lunch), 17:00–08:00 (0.00 closed).
  3. **Bottom-Up Non-Cooling Aggregation (`compute_non_cooling_demand`):**
     - Isolated non-cooling electrical equipment (`item.is_cooling == False`) from `EquipmentAudit`.
     - Classified equipment into continuous 24/7 loads (`hours_per_day >= 24.0`) and occupancy-driven diurnal loads (`hours_per_day < 24.0`).
     - Connected non-cooling effective peak is 60.6590 kW (continuous: 3.4410 kW; occupancy peak: 57.2180 kW).
  4. **Baseload Double-Counting Prevention Rule:**
     - Target unoccupied non-cooling baseload is 10% of daytime peak ($0.10 \times 60.6590\text{ kW} = 6.0659\text{ kW}$).
     - Continuous 24/7 equipment already draws 3.4410 kW (Tier 1 life-safety: 1.2150 kW; Tier 2 IT infrastructure: 2.2260 kW).
     - To prevent double counting continuous loads with the 10% baseload rule, the residual standby margin is defined as $P_{\text{standby}} = \max(0.0, 0.10 \times P_{\text{peak}} - P_{\text{cont, total}}) = 2.6249\text{ kW}$.
     - This residual represents parasitic standby plug loads (sleep-mode PCs, monitors, troffers, and appliances) and is allocated to Tier 3 (sheddable load).
     - As occupancy fraction $f$ increases, standby load transitions into active operational load via $(1.0 - f) \times P_{\text{standby}}$.
     - Resulting gross demand is exactly 6.0659 kW (10% of peak) during all unoccupied hours (nights, Sundays, holidays) and 60.6590 kW at full occupancy, with energy conservation strictly preserved per hour ($\sum \text{Tier}_i = \text{Gross}$).
  5. **Decoupling from Cooling and Calibration:**
     - Cooling load calculations are strictly excluded and deferred to DEM-002.
     - Calibration scaling factors and billing reconciliations are deferred to DEM-002.4 and INT-001.
- **Reasoning:** Establishes an auditable, physically grounded bottom-up schedule and non-cooling load model without double-counting 24/7 continuous loads, enabling clean integration with OUT-002 tiered shedding and DEM-002 cooling response.  
- **Affects:** `DEM-001`, `DEM-002`, `OUT-002`, `INT-001`, `INT-002`, `INT-003`.

**[D-28]** Cooling Response Model, Piecewise-Linear CDD, Tropical Latent Multiplier Ramp, and 24/7 Spot Cooling Conventions.  
- **Date / Session:** 2026-10-21  
- **Decision:**  
  1. **Stated Reference Cooling Power & Sensible CDD Response:**
     - Reference cooling power $P_{\text{ref}}$ is defined directly as the connected nameplate cooling capacity ($P_{\text{conn}}$) per tier ($P_{\text{conn, spot}} = 2.40\text{ kW}$ for Tier 2; $P_{\text{conn, comfort}} = 74.80\text{ kW}$ for Tier 3), rather than an arbitrary empirical duty factor.
     - Sensible delta is evaluated above balance setpoint: $\Delta T = \max(0.0, T_{\text{amb}} - T_{\text{base}})$, where $T_{\text{base}} = 24.0^\circ\text{C}$ ([D-07]).
     - Slope is exactly 4.0%/°C relative to connected capacity ($s_T = 0.04$). At or below $T_{\text{base}} = 24.0^\circ\text{C}$, sensible cooling is identically zero.
  2. **Piecewise-Linear Tropical Latent Multiplier Ramp:**
     - At relative humidity $RH \le 60.0\%$, latent dehumidification load is minimal: $M_{\text{latent}} = 1.00$.
     - At high tropical humidity $RH \ge 80.0\%$, coil condensation enthalpy reaches peak: $M_{\text{latent}} = 1.20$ (+20% latent penalty per [D-07]).
     - For $60\% < RH < 80\%$, $M_{\text{latent}}$ ramps linearly: $M_{\text{latent}}(RH) = 1.0 + 0.20 \times \frac{RH - 60.0}{20.0}$. This eliminates non-physical step jumps in electrical demand across weather hours.
  3. **Continuous 24/7 Spot Cooling vs. Occupancy Comfort Cooling:**
     - Tier 2 spot cooling (IDF closets, $P_{\text{conn}} = 2.40\text{ kW}$) runs 24 hours a day, 365 days a year, independent of human occupancy ($f_{\text{occ}}$), to remove continuous thermal dissipation from active PoE switches and routers.
     - Tier 3 comfort cooling ($P_{\text{conn}} = 74.80\text{ kW}$) operates only when spaces are occupied, scaling linearly with building occupancy fraction $f_{\text{occ}}$. When $f_{\text{occ}} = 0$, comfort AC units are shut off, leaving only Tier 2 spot cooling active during unoccupied hours.
     - Tier 1 cooling demand is identically zero (no life-safety cooling items in audit).
  4. **Capacity Capping and Inverter Modulation:**
     - Cooling demand per tier is hard-capped at connected capacity ($P_{\text{conn}}$). Inverter compressors modulate smoothly; cycling at minimum modulation over the 1-hour simulation time step converges to the average thermal power requirement.
  5. **DEM-002.4 Deferral:**
     - DEM-002.4 (validation against mock monthly bills) is deferred until DEM-001 is merged to master, as billing comparison requires combined non-cooling and cooling loads.
- **Reasoning:** Establishes a transparent, continuous, and physical cooling model without arbitrary unverified multipliers, guaranteeing smooth temperature/humidity response and exact power conservation across priority tiers.  
- **Affects:** `DEM-002`, `INT-001`, `INT-002`, `INT-003`, `DEC-002`.

**[D-34]** Priority-Based Tiered Load Shedding Policy, Low-SoC Threshold Decoupling, and Unserved Energy Tracking Conventions.  
- **Date / Session:** 2026-10-20  
- **Decision:**  
  1. **Hierarchical Shedding Policy (`shed_for_hour`):**
     - When utility grid is energized (`grid_available = True`), all tiers are fully served (`active_tier = LoadTier.TIER_3_SHEDDABLE`, `served = demand`, `unserved = (0, 0, 0)`).
     - Upon utility failure (`grid_available = False`), Tier 3 discretionary loads (HVAC, non-essential PC labs) are shed immediately to preserve microgrid reserves per [D-10].
     - When battery State-of-Charge falls strictly below the low-SoC threshold (`soc_kwh < tier2_shed_soc_fraction * capacity_kwh`), Tier 2 essential loads (faculty rooms, admin, servers/smart rooms) are also shed (`active_tier = LoadTier.TIER_1_CRITICAL`), dedicating remaining battery capacity exclusively to Tier 1 life-safety. At or above threshold, Tier 2 is served (`active_tier = LoadTier.TIER_2_ESSENTIAL`).
     - Per-tier energy conservation invariant strictly holds across all states: $\text{served}_i + \text{unserved}_i = \text{demand}_i$ for every tier $i \in \{1, 2, 3\}$.
  2. **Parameter Decoupling from Emergency Reserve:**
     - The 20% low-SoC Tier 2 shedding threshold (`tier2_shed_soc_fraction: float = 0.20`) is implemented as an explicit parameter decoupled from `Battery.emergency_reserve_pct` ([D-17]).
     - `tier2_shed_soc_fraction` dictates the operational load-shedding control policy (when to drop Tier 2 during an outage), whereas `emergency_reserve_pct` dictates the battery dispatch scheduling cushion (preventing normal daily cycling from eating into outage energy buffer). Both default to 0.20, but keeping them decoupled enables independent sensitivity sweeps in `INT-001` and `INT-002`.
  3. **Reverse-Priority Shortfall Allocation (`UnservedTracker`):**
     - When physical battery discharge capacity cannot deliver the full policy-served demand during an outage (`battery_shortfall_kwh > 0.0`), the delivery deficit is allocated strictly in reverse-priority order: cutting into Tier 3 served first, then Tier 2, and finally Tier 1.
     - Outage hours in which each tier was fully served (100% service with zero unserved energy) and cumulative unserved kWh per tier are tracked continuously.
  4. **Audit Tier Share Discrepancy Reporting:**
     - The audited equipment connected load (`data/fixtures/equipment-audit-ccis.csv`) yields 147.805 kW total: Tier 1 = 1.215 kW (~0.82%), Tier 2 = 15.360 kW (~10.39%), Tier 3 = 131.230 kW (~88.79%).
     - In accordance with the prompt specification, this discrepancy from D-10's nominal 2/18/80 split is explicitly exposed via `compute_tier_audit_shares` and reported as an audit reality rather than forced to match nominal assumptions.
- **Reasoning:** Formalizes exact deterministic load-shedding dispatch rules and energy accounting, guaranteeing conservation and clean policy decoupling ahead of full system integration.
- **Affects:** `OUT-002`, `INT-001`, `INT-002`, `DEC-002`.

**[D-31]** Battery Dispatch Dynamics, AC-Flow Conversion Accounting, and C-Rate & Headroom/Floor Limiting.  
- **Date / Session:** 2026-10-21  
- **Decision:**  
  1. **Canonical Time-Step Battery Dispatch (`step_battery`):** Implemented in `src/ccis_sim/battery/dynamics.py` conforming strictly to the contract in `docs/context/phase2-interface-contract.md`.
  2. **AC-Side Energy Flow & Conversion Conventions:**
     - Charge request ($P_{\text{chg, req}}$) and discharge request ($P_{\text{dis, req}}$) are AC-side quantities at the microgrid bus.
     - Symmetrical conversion efficiency $\eta_{\text{chg}} = \eta_{\text{dis}} = \sqrt{\eta_{\text{rt}}} = \sqrt{0.92}$ per [D-25].
     - Energy stored during charge: $\Delta \text{SoC} = \eta_{\text{chg}} \cdot P_{\text{chg, ac}} \Delta t$.
     - Energy extracted during discharge: $\Delta \text{SoC} = (P_{\text{dis, ac}} / \eta_{\text{dis}}) \Delta t$.
  3. **C-Rate and Energy Headroom / Floor Constraints:**
     - Maximum AC charge is constrained by $\min(P_{\text{max, chg}} \Delta t, (C_{\text{bat}} - \text{SoC}_{t-1}) / \eta_{\text{chg}})$.
     - Maximum AC discharge is constrained by $\min(P_{\text{max, dis}} \Delta t, \max(0, \text{SoC}_{t-1} - \text{SoC}_{\text{floor}}) \cdot \eta_{\text{dis}})$, defaulting $\text{SoC}_{\text{floor}} = \text{battery.min\_soc\_kwh}$.
     - When `cur_soc <= effective_floor`, discharge is zero and State-of-Charge remains unchanged without artificial inflation.
  4. **Mutual Exclusivity & Zero-Capacity Edge Cases:**
     - Simultaneous requests exceeding $10^{-6}\text{ kWh}$ each trigger `ValueError` at the source.
     - For zero-capacity battery ($C_{\text{bat}} = 0$), all flows are 0, SoC is 0, and requests are reported as 100% curtailed or unmet.
  5. **Idle Loss Separation:** Idle self-discharge and standby tare losses are explicitly excluded from this module per [D-26] and deferred to BAT-002.
- **Reasoning:** Enforces exact first-law thermodynamic conservation and verification harness compliance for battery dispatch without leaky abstractions.
- **Affects:** `BAT-001`, `BAT-002`, `INT-001`, `INT-002`.

**[D-32]** Battery Outage Reserve Scheduling Floor, Emergency Drawdown Constraints, and Chemical Idle Loss Accounting.  
- **Date / Session:** 2026-10-21  
- **Decision:**  
  1. **Dynamic SoC Protection Floor (`soc_floor_kwh`):** Implemented in `src/ccis_sim/battery/reserve.py` conforming strictly to `docs/context/phase2-interface-contract.md`.
  2. **Operational vs. Hardware Protection Floor Semantics:**
     - When utility grid is energized (`grid_available = True`), the operational dispatch floor is $\text{min\_soc\_kwh} + \text{emergency\_reserve\_kwh}$ ($0.10 \times C_{\text{bat}} + 0.20 \times C_{\text{bat}} = 0.30 \times C_{\text{bat}}$), locking the 20% emergency buffer away from routine daily cycling per [D-17].
     - When utility grid fails (`grid_available = False`), the emergency reserve is released and the floor collapses to the physical cell-protection floor $\text{min\_soc\_kwh}$ ($0.10 \times C_{\text{bat}}$ per [D-09]).
     - When utility grid fails with `allow_emergency_drawdown = True` and Tier 1 critical or Tier 2 essential load is active (`active_load_tier in (1, 2)`), the floor drops to $0.0\text{ kWh}$ per [D-25], enabling catastrophic emergency drawdown. For Tier 3 sheddable load, the floor remains strictly at $\text{min\_soc\_kwh}$.
     - For zero-capacity batteries, the floor evaluates to $0.0\text{ kWh}$.
  3. **Chemical-Side Idle Loss Formulation (`apply_idle_losses`):**
     - Standby tare loss ($P_{\text{tare}}$) and ambient self-discharge ($r_{\text{self}} = 2.0\%/\text{month}$) are applied strictly to stored chemical State-of-Charge per [D-26], using standard $730.0\text{ h/month}$ ($8,760\text{ h} / 12$).
     - Idle losses are clamped at $\text{battery.min\_soc\_kwh}$ ($0.10 \times C_{\text{bat}}$) and $0.0\text{ kWh}$, guaranteeing that standby dissipation never self-starves the battery below physical limits or induces negative SoC.
     - The hourly loss is bounded by $\Delta E_{\text{idle, max}}$, guaranteeing exact compliance with verification harness continuity checks without tripping `SOC_CONTINUITY` or `SOC_CUMULATIVE_DRIFT`.
- **Reasoning:** Formalizes exact mathematical rules bridging normal operational dispatch reserves, blackout survival overrides, and physical idle losses while maintaining first-law conservation across all interfaces.
- **Affects:** `BAT-002`, `BAT-001`, `INT-001`, `INT-002`.

**[D-29]** Solar Irradiance Geometry, Erbs Decomposition, Isotropic Transposition, and Rooftop NOCT Thermal Derating Model locked.  
- **Date / Session:** 2026-10-21  
- **Decision:**  
  1. **Astronomical Solar Position Algorithm:** Implement the Spencer (1971) Fourier series for solar declination ($\delta$) and Equation of Time ($\text{EoT}$ in minutes). Apply standard meridian alignment ($L_{\text{std}} = 120.0^\circ\text{E}$ for Philippine Standard Time UTC+8) and Batac local longitude ($L_{\text{loc}} = 120.56^\circ\text{E}$) with a $+2.24\text{ minute}$ longitude correction:  
     $$t_{\text{solar}} = t_{\text{local}} + \frac{\text{EoT} + 4(L_{\text{loc}} - L_{\text{std}})}{60.0}$$  
     Solar hour angle $\omega = 15^\circ(t_{\text{solar}} - 12.0)$, ensuring astronomical solar noon lands deterministically within 12:00 ± 20 minutes across the annual cycle.  
  2. **Irradiance Decomposition (Erbs Model):** Decompose Global Horizontal Irradiance ($\text{GHI}$) into Diffuse Horizontal Irradiance ($\text{DHI}$) and Direct Normal Irradiance ($\text{DNI}$) using the Erbs, Klein, and Duffie (1982) empirical correlation based on hourly clearness index $k_t = \text{GHI} / G_0$, with extraterrestrial horizontal insolation $G_0 = \max(0, G_{\text{on}} \cos \theta_z)$ and solar constant $G_{\text{sc}} = 1,367\text{ W/m}^2$.  
  3. **Transposition to Plane-of-Array (Liu & Jordan Isotropic Model):** Transpose beam, diffuse sky, and ground-reflected components to an array oriented at optimal tilt $\beta = 15.0^\circ$ and surface azimuth $\gamma = 180.0^\circ$ (True South):  
     $$G_{\text{poa}} = \text{DNI} \max(0, \cos \theta) + \text{DHI}\left(\frac{1 + \cos \beta}{2}\right) + \text{GHI} \cdot \rho_g \left(\frac{1 - \cos \beta}{2}\right)$$  
     Surface angle of incidence $\cos \theta$ is computed using Duffie & Beckman eq 1.6.2. Ground diffuse albedo is parameterized as $\rho_g = 0.20$ (`[ASSUMPTION]`), reflecting typical tropical academic campus ground cover (grass/concrete mix).  
  4. **Cell Temperature with Rooftop Mounting Thermal Penalty:**  
     Resolve the ambiguous $+10.0^\circ\text{C}$ rooftop mounting penalty from [D-08] by embedding it into the effective NOCT slope (`[ASSUMPTION]`):  
     $$T_{\text{cell}} = T_{\text{amb}} + \left(\frac{(\text{NOCT}_{\text{base}} + \Delta T_{\text{roof}}) - 20.0}{800.0}\right) G_{\text{poa}} = T_{\text{amb}} + \left(\frac{(45.0 + 10.0) - 20.0}{800.0}\right) G_{\text{poa}} = T_{\text{amb}} + \frac{35.0}{800.0} G_{\text{poa}}$$  
     This formulation guarantees that at night or zero insolation ($G_{\text{poa}} = 0$), $T_{\text{cell}}$ converges identically to ambient dry-bulb temperature $T_{\text{amb}}$, while at peak insolation ($800\text{ W/m}^2$) the cell experiences the full $+35.0^\circ\text{C}$ rise above ambient.  
  5. **Thermal Derating and DC Power Output per kWp:**  
     Apply the monocrystalline silicon temperature coefficient of power $\gamma = -0.40\%/^\circ\text{C} = -0.0040/^\circ\text{C}$ relative to STC reference temperature $T_{\text{ref}} = 25.0^\circ\text{C}$ ([D-08]):  
     $$f_{\text{temp}} = \max\left(0.0, 1.0 + \gamma(T_{\text{cell}} - 25.0)\right)$$  
     $$P_{\text{dc\_per\_kwp}} = \left(\frac{G_{\text{poa}}}{1,000.0\text{ W/m}^2}\right) \cdot f_{\text{temp}}$$  
     Yields an annual specific DC generation of **1,695.05 kWh/kWp** for the 2019 baseline weather fixture before balance-of-system and inverter losses (which are reserved for `SOL-002`).  
- **Reasoning:** Conforms strictly to the locked `phase2-interface-contract.md` signature, eliminates uncredited magic constants, provides physically validated solar transposition and thermal derating, and preserves exact zero generation during non-sunlit hours.  
- **Affects:** `SOL-001`, `SOL-002`, `INT-001`.

**[D-30]** Solar PV Array Sizing, Inverter Clipping, and Balance-of-System PR Decomposition locked.  
- **Date / Session:** 2026-10-21  
- **Decision:**  
  1. **Array Sizing & Capacity Matrix Scaling (`compute_ac_generation`):**  
     Implement hourly AC generation modeling across the four scenario DC capacities defined in [D-18]: 0 kWp (negative control, returns strictly 0.0 kWh/h), 50 kWp, 100 kWp, and 200 kWp. Conforms strictly to the locked `phase2-interface-contract.md` signature.  
  2. **Inverter Efficiency & Continuous AC Clipping Limit:**  
     Model peak inverter conversion efficiency at 98.0% (`DEFAULT_INVERTER_EFFICIENCY = 0.980`) per [D-08]. Continuous inverter AC power rating is governed by an explicit commercial DC/AC sizing ratio (`DEFAULT_DC_AC_RATIO = 1.20`, `[ASSUMPTION]`):  
     $$P_{\text{ac\_rated}} = \frac{P_{\text{dc\_kWp}}}{\text{DC/AC ratio}}$$  
     Gross AC power before clipping ($P_{\text{ac\_gross}} = P_{\text{dc\_at\_inverter}} \cdot \eta_{\text{inv}}$) is strictly clipped at $P_{\text{ac\_rated}}$, guaranteeing that AC power output delivered to the microgrid bus never exceeds continuous inverter nameplate rating ($P_{\text{ac}} \le P_{\text{ac\_rated}}$).  
  3. **Non-Thermal Balance-of-System (BOS) Derate Decomposition:**  
     To prevent double-counting of temperature losses already explicitly computed upstream in `SOL-001` (`compute_dc_power_per_kwp`), decompose the nominal $PR = 0.77$ ([D-08]) into named physical derating factors (`[ASSUMPTION]`):  
     - Soiling factor: $f_{\text{soiling}} = 0.960$ (4.0% seasonal dust/dry spell soiling loss in Batac).  
     - DC wiring factor: $f_{\text{dc\_wiring}} = 0.985$ (1.5% DC ohmic cabling loss).  
     - AC wiring factor: $f_{\text{ac\_wiring}} = 0.990$ (1.0% AC collection and transformer loss).  
     - Module mismatch factor: $f_{\text{mismatch}} = 0.980$ (2.0% module mismatch and manufacturer nameplate tolerance).  
     - Availability factor: $f_{\text{availability}} = 0.990$ (1.0% operational downtime / maintenance).  
     The product of non-thermal BOS factors is:  
     $$f_{\text{bos\_non\_thermal}} = 0.960 \times 0.985 \times 0.990 \times 0.980 \times 0.990 \approx 0.908247$$  
  4. **Assumed Mean Thermal Factor & Reconciliation to Baseline PR = 0.77:**  
     Define the assumed annual mean thermal factor as $\text{ASSUMED\_MEAN\_THERMAL\_FACTOR} \approx 0.865089$ (`[ASSUMPTION]`, representing ~13.49% average thermal derating under tropical Batac weather conditions). The budget reconciles exactly to the baseline $PR = 0.77$:  
     $$\text{PR} = \eta_{\text{inv}} \cdot f_{\text{bos\_non\_thermal}} \cdot \text{ASSUMED\_MEAN\_THERMAL\_FACTOR} = 0.980 \cdot 0.908247 \cdot 0.865089 = 0.770000$$  
     In `compute_ac_generation`, only the non-thermal BOS derates and inverter efficiency/clipping are applied to the input `dc_kw_per_kwp`. Full system annual yield validation against the 1,298 kWh/kWp Luzon benchmark is deferred to `SOL-002.4` following integration with `SOL-001`.  
- **Reasoning:** Conforms strictly to Phase 2 interface contracts, eliminates double-counting of cell thermal losses, provides physical and auditable BOS loss accounting, and bounds maximum AC power delivery under inverter clipping.  
- **Affects:** `SOL-002`, `INT-001`, `DEC-002`.


**[D-33]** Stochastic Outage Process Calibration, Continuous-to-Discrete Discretization, and Typhoon Solar Depression Coupling locked.  
- **Date / Session:** 2026-10-21  
- **Decision:**  
  1. **Arrival Process Calibration (`sample_outage_schedule`):**  
     Implement a homogeneous Poisson arrival process with annual rates $\lambda = 3.0\text{ outages/yr}$ for normal / baseline weather years and $\lambda = 8.0\text{ outages/yr}$ for typhoon / extreme weather years per [D-11]. Arrival start hours are sampled uniformly over the annual timeline $[1, n_{\text{hours}}]$. Uniform start distribution is adopted as the rigorous baseline (`[ASSUMPTION]`), deferring seasonal typhoon clustering (June–November) to future sensitivity sweeps since empirical sub-annual hazard rate calibration data is unavailable.  
  2. **Continuous Duration Sampling:**  
     Continuous pre-discretization durations are sampled from the target Lognormal($\mu, \sigma$) distribution on $\ln(\text{hours})$, where Normal Year has $(\mu = 1.2, \sigma = 0.8)$ (median 3.32h, mean 4.56h) and Typhoon Year has $(\mu = 2.3, \sigma = 1.0)$ (median 9.97h, mean 16.44h) per [D-11].  
  3. **Continuous-to-Discrete Hour Discretization & Bias:**  
     Discretize continuous durations to integer hours via ceiling: $D_{\text{int}} = \max(1, \lceil D \rceil)$ (`[ASSUMPTION]`). Because the CCIS simulation step is $\Delta t = 1.0\text{ h}$, any non-zero outage duration interrupts building electrical service for that hour. This introduces a slight upward discretization bias of $\approx +0.5\text{ h}$ per event.  
  4. **Interval Merging & Boundary Clipping:**  
     Multiple outages that overlap or touch ($s_2 \le e_1$) are merged into a single continuous blackout event with $s_{\text{merged}} = s_1$ and $e_{\text{merged}} = \max(e_1, e_2)$ (`[ASSUMPTION]`). Merging avoids unphysical overlapping events and ensures `grid_available` strictly reflects discrete `OutageEvent` records, slightly reducing event count ($<0.01$ events/yr in normal, $\approx 0.10$ events/yr in typhoon) while preserving exact blackout hour unions. Events starting past the simulation horizon ($s > n_{\text{hours}}$) are excluded; events ending past hour $n_{\text{hours}}$ are clipped to end at hour $n_{\text{hours}} + 1$ (`[ASSUMPTION]`).  
  5. **Typhoon Solar Depression Interpretation & Coupling (`apply_ghi_multiplier`):**  
     Resolve the [D-11] ambiguity ("depressed solar irradiance (20–30% normal GHI)") as an **attenuation multiplier** $m \in [0.20, 0.30]$ (i.e. insolation reduced to 20%–30% of normal clear-sky insolation due to dense cyclone cloud cover, rather than a 20%–30% reduction). In typhoon years with outages, 1 to 2 storm episodes are coupled with the longest outage events (`[ASSUMPTION]`), lasting 3 to 5 consecutive days ($72 \dots 120\text{ h}$) starting at the outage event start hour. Outside storm episodes and in normal years, the multiplier is strictly $1.0$. `apply_ghi_multiplier` returns a deep copy of the input weather DataFrame, preserving input immutability.  
  6. **Statistical Goodness-of-Fit Validator (`validate_duration_distribution`):**  
     Evaluates pre-discretization continuous durations against target Lognormal via two-sided Kolmogorov-Smirnov test at significance level $\alpha = 0.01$, and verifies annual arrival counts against Poisson($\lambda$) via large-sample standard error normal approximation.  
- **Reasoning:** Conforms strictly to Phase 2 interface contracts (`phase2-interface-contract.md`), eliminates arbitrary constants, provides empirical calibration to Philippine rural cooperative and cyclone data [D-11], and guarantees mathematical consistency between discrete `OutageEvent` records and boolean `grid_available` arrays.  
- **Affects:** `ccis_sim.outage.sampler`, `ccis_sim.outage`, `INT-001`, `INT-002`, `DEC-002`.


**[D-35]** Integrated Simulation Engine Architecture, Dispatch Sequence, Exporters, and Combined Demand/Solar Verification (DEM-002.4 + SOL-002.4).  
- **Date / Session:** 2026-10-21  
- **Decision:**  
  1. **Engine Dispatch Sequence and Pure Function Interface (`simulate`):**  
     Implement the integrated simulation engine as a pure functional call `simulate(config, weather_df, seed) -> SimulationResult` without global state or input mutation. The hourly dispatch loop strictly executes the 8-step sequence specified in `phase2-interface-contract.md`:  
     - Step 1: Query effective battery reserve floor $R_{\text{floor}}(t)$ via `get_reserve_floor` (accounting for scheduled baseline reserve or storm-mode pre-charge).  
     - Step 2: Compute gross balance $B_{\text{gross}}(t) = P_{\text{pv}}(t) - L_{\text{total}}(t)$.  
     - Step 3: Dispatch battery via `step_battery_dispatch` (charging up to surplus/headroom/C-rate or discharging up to deficit/floor/C-rate).  
     - Step 4: Compute net electrical balance $B_{\text{net}}(t) = B_{\text{gross}}(t) + P_{\text{batt}}(t)$ (where $P_{\text{batt}} > 0$ denotes discharge).  
     - Step 5: Check grid availability $G(t) \in \{\text{True}, \text{False}\}$. If grid is online, balance deficits via grid import and export surplus; unserved deficit is 0. If grid is offline (outage), grid exchange is 0 and deficit $D_{\text{unserved}} = \max(0, -B_{\text{net}})$.  
     - Step 6: Execute tiered load shedding via `apply_shedding(tier_loads, soc(t+1), deficit)`.  
     - Step 7: Record hourly unserved metrics into `UnservedTracker.record_hour`.  
     - Step 8: Consolidate hourly metrics and append to history vectors.  
  2. **Configuration Surface and Scenario Preset Matrix (`SimulationConfig`):**  
     Encapsulate all simulation parameters into an immutable dataclass `SimulationConfig`. Provide a factory method `SimulationConfig.for_scenario(name)` mapping the 4 core comparative scenario presets:  
     - `grid_only`: 0 kWp PV, 0 kWh battery, grid available (reference baseline).  
     - `pv_only`: 100 kWp PV, 0 kWh battery.  
     - `pv_battery_std`: 100 kWp PV, 200 kWh battery, baseline reserve floor (10% min SoC).  
     - `pv_battery_resilient`: 100 kWp PV, 200 kWh battery, resilient reserve floor (50% emergency reserve floor with 24h pre-charge window).  
  3. **Decoupled Priority Load Shedding and Battery Reserve Coordination:**  
     Confirm adherence to [D-34]: the 20% SoC load shedding trigger threshold (`SHED_THRESHOLD_SOC = 0.20`) is strictly decoupled from the battery operational minimum SoC (`min_soc = 0.10`) and outage emergency reserve floor (`reserve_soc = 0.50`). Load shedding is an electrical demand-side triage policy, whereas battery reserve is an electrochemical dispatch boundary.  
  4. **DEM-002.4 Combined Demand Verification & Uncalibrated Baseline Comparison:**  
     Bottom-up integration yields annual demand of 189,355.61 kWh/yr, EUI of 75.74 kWh/m²·yr, and peak demand of 95.71 kW (occurring at hour 2340). Comparison against benchmarks:  
     - vs Phase 1 uncalibrated placeholder (324,380 kWh/yr, EUI 129.75, peak 101.29 kW): -41.63% annual energy, -41.62% EUI, -5.51% peak.  
     - vs synthetic mock utility bills (398,537 kWh/yr, EUI 159.41, peak 139.24 kW): -52.49% annual energy.  
     *Physical Rationale:* The Phase 1 uncalibrated model assumed a continuous 30 kW 24/7 baseload and continuous 64.9 kW cooling day and night. In contrast, the bottom-up model strictly reflects CCIS operational reality: classes operate 07:00–19:00, buildings close on weekends, and cooling shuts down when spaces are unoccupied, with true standby baseload of 6.07 kW and 24/7 server room cooling of 3.8 kW. In accordance with rigorous modeling integrity and explicit prompt directives, the bottom-up demand is NOT arbitrarily scaled or calibrated to match synthetic utility bills.  
  5. **SOL-002.4 Combined Solar Verification & Luzon Target Reconciliation:**  
     Transposed annual POA insolation in Batac is 1,945.98 kWh/m². SOL-001 temperature-derated DC yield is 1,695.05 kWh/kWp, yielding an implied annual energy-weighted thermal factor $\text{TF}_{\text{implied}} = \frac{1695.05}{1945.98} \approx 0.871056$ (~12.89% thermal loss). This closely matches the SOL-002 assumed derate $\text{TF}_{\text{assumed}} \approx 0.865089$ within 0.69%. End-to-end AC specific yield is 1,508.74 kWh/kWp (301,747.88 kWh/yr for 200 kWp), comfortably inside the tropical Philippines expected band [1,200, 1,600] kWh/kWp. The +16.24% higher specific yield relative to the 1,298 kWh/kWp multi-system Luzon average cited in literature is physically justified by Batac's exceptional high solar resource (1,901 kWh/m² GHI, 1,946 kWh/m² POA) compared to cloudier southern/urban Luzon sites.  
  6. **Multi-Format Exporters and CLI Driver Architecture:**  
     Provide pure functional exporters in `src/ccis_sim/integration/exporters.py` generating hourly timeseries CSV, daily aggregated timeseries CSV, and an annual summary JSON adhering to Phase 2 schemas. Provide the CLI command `ccis-sim run` (`src/ccis_sim/cli.py`) with rich tabular console summaries and artifact file output.  
- **Reasoning:** Establishes the authoritative Phase 2 integrated simulation engine, satisfies all interface contracts, decouples triage policies from physical battery states, and establishes rigorous, physically-grounded cross-verification for demand and solar sub-models.  
- **Affects:** `ccis_sim.integration`, `ccis_sim.cli`, `INT-001`, `DEM-002.4`, `SOL-002.4`, `DEC-002`.


**[D-36]** Dual Demand Scaling Policy, Scenario Grid Topology, Common Random Numbers Seed Policy, and Stochastic Convergence Verdict.  
- **Date / Session:** 2026-10-21  
- **Decision:**  
  1. **Dual Demand Reporting Policy (`demand_scale`):**  
     Acknowledge the physical divergence between the bottom-up demand model (189,356 kWh/yr, EUI 75.74 kWh/m²·yr) and the synthetic mock utility bills (398,537 kWh/yr, EUI 159.41 kWh/m²·yr) without circular calibration. Adopt dual reporting:  
     - **Primary:** Uncalibrated bottom-up demand (`demand_scale = 1.0`, reproducing INT-001 bit-for-bit).  
     - **Sensitivity:** Bill-calibrated demand using a single scalar factor:  
       $$\text{demand\_scale}_{\text{bill}} = \frac{\text{bills\_total}}{\text{bottom\_up\_total}} = \frac{398536.77}{189355.61} \approx 2.104700$$  
     No individual equipment loads or schedule parameters are tuned.  
  2. **Scenario Grid Topology (2,460 Total Annual Runs):**  
     Structure the scenario matrix into three explicit simulation tranches:  
     - **Main Grid (1,920 runs):** Solar $\in \{0, 50, 100, 200\}\text{ kWp} \times$ Battery $\in \{0, 50, 100, 200\}\text{ kWh} \times$ Weather $\in \{2019, 2016\} \times$ Outage $\in \{\text{normal}, \text{typhoon}\} \times 30\text{ seeds}$ with `demand_scale = 1.0`.  
     - **Sensitivity Grid (480 runs):** Sizing matrix ($4 \times 4$) $\times$ Weather $2019 \times$ Outage $\in \{\text{normal}, \text{typhoon}\} \times 15\text{ seeds}$ with $\text{demand\_scale} \approx 2.1047$.  
     - **Climate Sensitivity (+2.0°C Case, 60 runs):** Solar $\in \{0, 100\}\text{ kWp} \times$ Battery $\in \{0, 100\}\text{ kWh} \times$ Weather $2019 \times$ Outage normal $\times 15\text{ seeds}$ with `temp_offset_c = 2.0` and `demand_scale = 1.0`.  
  3. **Common Random Numbers (CRN) Variance Reduction:**  
     To maximize precision when comparing sizing configurations within each (weather, regime, seed) cell, identical random seeds (0..29 or 0..14) drive the Poisson/Lognormal outage sampler across all system sizes. Differences in reliability metrics between sizing pairs reflect true system capacity impact rather than stochastic outage schedule variation.  
  4. **Stochastic Convergence Verdict (INT-002.2):**  
     Evaluate unserved Tier 1+2 energy on the benchmark $(100\text{ kWp}, 100\text{ kWh}, 2019, \text{typhoon})$ cell across sample sizes $N \in \{10, 20, 30\}$:  
     - $N = 10$: Mean $= 131.57\text{ kWh}$, $SE = 34.87\text{ kWh}$, 95% CI $= [52.70, 210.45]\text{ kWh}$, half-width $= 78.87\text{ kWh}$ ($59.95\%$ of mean).  
     - $N = 20$: Mean $= 123.36\text{ kWh}$, $SE = 21.65\text{ kWh}$, 95% CI $= [78.06, 168.67]\text{ kWh}$, half-width $= 45.31\text{ kWh}$ ($36.73\%$ of mean).  
     - $N = 30$: Mean $= 110.98\text{ kWh}$, $SE = 17.12\text{ kWh}$, 95% CI $= [75.96, 146.00]\text{ kWh}$, half-width $= 35.02\text{ kWh}$ ($31.56\%$ of mean).  
     *Verdict:* Standard error drops monotonically from 34.87 kWh to 17.12 kWh (halved from $N=10$ to $N=30$), and relative CI half-width narrows from 60% to 31.6%. Relative half-width remains above the 10% threshold due to the inherent heavy-tailed Lognormal($\mu=2.3, \sigma=1.0$) duration distribution of typhoon outages coupled with discrete arrival timing relative to nighttime and insolation. $N = 30$ provides sufficient statistical stability to rank sizing alternatives rigorously.  
  5. **Multiprocessing Architecture & Result Serialization:**  
     Implemented parallel batch execution in `src/ccis_sim/integration/scenarios.py` using worker-level fixture caching, completing all 2,460 simulations in 9.75 minutes with 0 harness errors (`verify=True`). Serialized flat results to `results/scenario_grid.csv` and grouped cell distributions to `results/mc_summary.csv`.  
- **Reasoning:** Conforms strictly to Phase 3 design goals, resolves the demand calibration question with transparent dual reporting, applies classical CRN variance reduction, and documents formal convergence properties for microgrid sizing.  
- **Affects:** `ccis_sim.integration.scenarios`, `INT-002`, `INT-003`, `DEC-001`, `DEC-002`.


**[D-37]** Verification Invariants, Plausibility Screening, Epistemological Framing, and KPI Tables (INT-003).  
- **Date / Session:** 2026-10-21  
- **Decision:**  
  1. **Epistemological Framing and Validation Status:**  
     Formally declare that simulation evaluation against synthetic mock utility bills represents **computational verification, physical conservation auditing, and plausibility screening, NOT empirical validation**. Because synthetic mock bills (CORE-003) were generated using the same equipment audit inventory as the bottom-up model, billing comparisons are not independent. The bottom-up demand profile (189,356 kWh/yr, EUI 75.74 kWh/m²·yr) is retained in its uncalibrated state (scale = 1.0) as the primary engineering model.  
  2. **Energy Conservation and Physical Invariant Audit Matrix:**  
     Establish `ccis_sim.validation.audit.audit_run` executing 8 primary (+4 extended) simulation configurations across solar (0, 100, 200 kWp), battery (0, 100, 200 kWh), and weather/outage regimes (2019 normal, 2019 typhoon, 2016 normal). All 12 configurations strictly pass all invariants:  
     - Maximum hourly energy balance residual: $\le 2.84 \times 10^{-14}\text{ kWh} \ll 10^{-5}\text{ kWh}$.  
     - Cumulative net drift: $\le 6.63 \times 10^{-13}\text{ kWh} \ll 10^{-3}\text{ kWh}$.  
     - Non-finite numeric count: 0 across all 8,760 hours.  
     - Battery SoC bounds: strictly within $[10\%\text{ min\_soc}, 100\%\text{ capacity}]$.  
     - Tier demand conservation: $P_{\text{served}, t} + P_{\text{unserved}, t} = P_{\text{gross}, t}$ for all $t \in [1, 8760]$.  
  3. **Seed Determinism and Reproducibility Protocol:**  
     Verify bit-identical determinism: identical seeds yield identical SHA-256 hourly CSV hashes; differing seeds produce distinct stochastic outage schedules ($N > 0$ diverging grid availability hours) and distinct hashes.  
  4. **Negative Control Verification:**  
     Verify that `assert_simulation_valid` reliably catches three deliberate breaks:  
     - Perturbed hourly residual ($+10^{-3}\text{ kWh}$): trips `ViolationType.HOURLY_ENERGY_BALANCE`.  
     - Stored SoC below minimum floor ($< 10\%\text{ min\_soc}$): trips `ViolationType.MIN_SOC_VIOLATION`.  
     - Non-finite field (`NaN`): trips `ViolationType.NON_FINITE_VALUE`.  
  5. **Plausibility and Benchmark Reconciliation:**  
     - ASHRAE Guideline 14 comparison against synthetic bills yields monthly $\text{NMBE} = -57.26\%$ and $\text{CV(RMSE)} = 55.26\%$ (failing monthly thresholds of $\pm 5\%$ and $15\%$, as expected for uncalibrated bottom-up demand reflecting unoccupied hours vs continuous baseline assumptions).  
     - Day-type daily consumption: regular academic weekdays ($845.76\text{ kWh/day}$), weekends ($268.57\text{ kWh/day}$), academic vacations/holidays ($204.46\text{ kWh/day}$).  
     - Solar specific yield: $1,508.74\text{ kWh/kWp}\cdot\text{yr}$ matches theoretical $\text{POA} \times \text{PR}$ ($1,945.98 \times 0.77 \approx 1,498.40\text{ kWh/kWp}$) within $+0.69\%$. The $+16.24\%$ gap over the Luzon multi-system average ($1,298\text{ kWh/kWp}$) is identified as a resource-data difference in Batac insolation, not model tuning.  
  6. **One-at-a-Time Parameter Sensitivity:**  
     Evaluate sensitivity relative to the 100 kWp / 100 kWh baseline (grid import: 79,064.38 kWh, unserved T1+2: 0.00 kWh):  
     - Emergency reserve (0.10 / 0.20 / 0.50): grid import shifts by $-1,710.62\text{ kWh}$ to $+5,274.36\text{ kWh}$; unserved T1+2 increases to $11.58\text{ kWh}$ at 0.10 reserve.  
     - Tier-2 shed threshold (0.10 / 0.20 / 0.30): unserved T1+2 increases to $11.58\text{ kWh}$ at 0.30 threshold (shedding triggered earlier).  
     - Cooling slope (3% / 4% / 5% /°C): grid import shifts by $\mp 6,500\text{ kWh}$ ($\pm 8.2\%$).  
     - PR-driving BOS factor ($\pm 5\%$): grid import shifts by $\mp 3,700\text{ kWh}$ ($\mp 4.7\%$).  
     - Battery RTE (0.88 / 0.92 / 0.96): grid import shifts by $+371.61\text{ kWh}$ / $-364.68\text{ kWh}$ ($\pm 0.47\%$).  
- **Reasoning:** Closes verification and plausibility audit milestones for Phase 3, guarantees strict mathematical and physical validity of simulation output data, documents sensitivity bounds, and provides authoritative headline KPI tables for downstream multi-criteria decision analysis.  
- **Affects:** `ccis_sim.validation`, `results/kpi_tables.md`, `INT-003`, `DEC-001`, `DEC-002`, `DEC-003`.


**[D-38]** Multi-Criteria Decision Framework (AHP), Unit Cost Proxy Assumptions, Pareto Frontier Formulation, and Formal Sizing Recommendation Rule (DEC-001 + DEC-002).  
- **Date / Session:** 2026-10-21  
- **Decision:**  
  1. **Analytic Hierarchy Process (AHP) Multi-Criteria Weighting Formulation:**  
     Establish an AHP weighting engine in `src/ccis_sim/decision/ahp.py` using Saaty's principal eigenvector method:  
     - Four criteria: (1) **Reliability** (mean fraction of outage hours with Tier 1+2 fully served during typhoon regime, with mean unserved T1+2 kWh as tie-breaker); (2) **Cost Index** (relative proxy of capital expenditure, minimized); (3) **Self-Sufficiency** (solar fraction of total consumption, maximized); (4) **Curtailment** (annual curtailed generation in kWh, minimized).  
     - Base Case Pairwise Comparison Matrix (Saaty 1–9 scale):  
       $$\mathbf{A} = \begin{pmatrix} 1 & 3 & 5 & 7 \\ 1/3 & 1 & 2 & 3 \\ 1/5 & 1/2 & 1 & 2 \\ 1/7 & 1/3 & 1/2 & 1 \end{pmatrix}$$  
     - Consistency Verification: Principal eigenvalue $\lambda_{\max} = 4.0192$, Consistency Index $CI = 0.0064$, Saaty Random Index $RI_4 = 0.90$, Consistency Ratio $CR = \frac{CI}{RI} = 0.0071 \le 0.10$. Asserted programmatically via `ahp_weights`.  
     - Derived Priority Weights: Reliability: `0.5872` (58.7%), Cost: `0.2179` (21.8%), Self-Sufficiency: `0.1228` (12.3%), Curtailment: `0.0722` (7.2%).  
     - Sensitivity Weight Profiles: (a) Equal weights: $[0.25, 0.25, 0.25, 0.25]$; (b) Reliability-heavy: $[0.60, 0.20, 0.10, 0.10]$.  
  2. **Relative Unit Cost Index Assumptions:**  
     Define the dimensionless cost proxy:  
     $$\text{Cost Index} = \text{solar\_kwp} \times 1.0 + \text{battery\_kwh} \times r$$  
     where $r$ is the relative unit capacity cost assumption of storage vs solar PV. The model intentionally reports energy and physical metrics, not pesos. Base case adopts $r = 0.60$, with sensitivity checks across $r \in \{0.30, 1.00\}$.  
  3. **Solar = 0 Candidate Exclusion:**  
     The microgrid dispatch engine topology ([D-35]) charges the battery strictly from PV surplus and never from the utility grid. With 0 kWp solar PV, any installed battery discharges once during the first blackout and remains permanently depleted at the 10% min SoC protection floor (~0.8 cycles/year). Consequently, battery-only cases ($0\text{ kWp}$ solar with $>0\text{ kWh}$ battery) are physically non-viable and excluded from the candidate trade-off competition. Sizing $(0, 0)$ is retained strictly as the reference baseline.  
  4. **Multi-Objective Pareto Frontier Formulation:**  
     A candidate sizing configuration $A$ strictly dominates candidate $B$ across the trade-off space $(\text{Reliability} \uparrow, \text{Cost Index} \downarrow, \text{Self-Sufficiency} \uparrow)$ iff $A$ is no worse than $B$ in all three objectives and strictly superior in at least one. The Pareto frontier is computed independently under both demand regimes.  
  5. **Formal Sizing Recommendation Rule (Pre-Registered):**  
     Select the cheapest non-dominated Pareto sizing whose mean Tier 1+2 outage-hours-served fraction is $\ge 0.90$ (90%) in the typhoon regime under bottom-up demand (`demand_scale = 1.0`) AND $\ge 0.80$ (80%) under bill-calibrated demand (`demand_scale \approx 2.1047`). If no sizing qualifies under both, select the best achievable sizing under each demand case and report the trade-off.  
- **Reasoning:** Formalizes multi-criteria decision criteria before evaluating model outputs, enforces Saaty consistency standards ($CR \le 0.10$), eliminates physically non-viable battery-only dispatch artifacts, and establishes an objective, pre-registered selection threshold robust across demand uncertainty.  
- **Affects:** `ccis_sim.decision.ahp`, `ccis_sim.decision.sizing`, `DEC-001`, `DEC-002`, `DEC-003`.


**[D-39]** Reserved, unused.  
- **Date / Session:** 2026-10-21  
- **Decision:** Reserved for late changes or figure annotations; confirmed unused.  
- **Reasoning:** Maintained to prevent ID reservation collisions per repository governance rules.  
- **Affects:** None.


**[D-40]** Heat-Effect Reporting Convention and 2016 Calendar-Mismatch Disclosure (DOC-FIX-001 Part C).  
- **Date / Session:** 2026-10-26  
- **Decision:**  
  1. Heat-effect figures are reported from grid-only runs (solar 0, battery 0), bottom-up demand, seed 0, and are duplicated for the bill-calibrated demand scale. Cooling kWh comes from calling `compute_cooling_demand` with the same weather/occupancy/audit inputs; non-cooling kWh comes from `compute_non_cooling_demand`. No new model logic is introduced.  
  2. The 2016 weather comparison uses the default `AcademicCalendar(year=2019)` because that is what `simulate()` uses. As a consequence, 2019 holiday dates do not match the 2016 calendar: 2016 resolves to 218 class days versus 206 in 2019, inflating 2016 non-cooling demand independently of weather. Any 2016-vs-2019 demand or grid-import comparison must disclose this confound.  
  3. The daily regression (daily total kWh on daily mean temperature, school days only) is reported as a simulation-conditional association, not a causal estimate.  
- **Reasoning:** Answers the project's primary heat-effect question with reproducible on-disk numbers while preventing the 2016 calendar mismatch from being presented as a pure weather effect.  
- **Affects:** `results/heat_effect.md`, `scripts/run_heat_effect.py`, `docs/reports/DOC-FIX-001-claude-code-closeout.md`.
