# Task Report: INT-003 — Verification, Plausibility, and Headline KPI Reporting

**Task ID:** `INT-003`  
**Agent:** `gemini`  
**Branch:** `task/INT-003`  
**Worktree:** `/home/lukexodus/projects/ccis-heat-load-backup-sim-INT-003`  
**Status:** `done`  
**Date:** 2026-10-21  
**Decision Log Reference:** `[D-37]`  

---

## 1. Executive Summary

### 1.1 Epistemological Framing & Validation Stance
> [!IMPORTANT]
> **Verification and Plausibility, Not Empirical Validation:**  
> The synthetic monthly utility bills generated in `CORE-003` and the bottom-up demand profile built in `DEM-001`/`DEM-002` both originate from the **exact same 18-room equipment inventory audit** (`data/fixtures/equipment-audit-ccis.csv`). Consequently, evaluating bottom-up simulation outputs against synthetic mock utility bills constitutes **computational verification, numerical consistency auditing, and plausibility screening, NOT empirical validation**. True empirical model validation would require independent, interval-metered utility bills from the physical facility, which are withheld by institutional constraint (`ARCH-001.3`). Per architectural decision `[D-35]` and prompt directives, bottom-up demand is reported in its uncalibrated state (`scale = 1.0`, 189,355.61 kWh/yr, EUI 75.74 kWh/m²·yr) rather than artificially tuned.

### 1.2 Summary of Completed Deliverables
1. **Physical Conservation & Boundary Invariant Audit (`validation/audit.py`):**  
   Implemented `audit_run(config, verify=True)` evaluating max hourly residual, cumulative numerical drift, battery SoC boundaries, non-finite guards, and per-hour tier demand conservation. Audited across **12 configurations** (4 sizings: grid-only, PV-100, PV+battery 100/100, PV+battery 200/200 $\times$ 3 regimes: 2019 normal, 2019 typhoon, 2016 normal). **100% of audited runs passed all physical invariants**, with max hourly residuals strictly $\le 2.84 \times 10^{-14}\text{ kWh}$ ($\ll 10^{-5}\text{ kWh}$ tolerance) and zero non-finite values.
2. **Seed Determinism & Reproducibility:**  
   Verified that identical random seeds (`seed=42`) yield bit-identical hourly CSV export hashes (`11e017778df2ba5b78110c97f6fa64f38bfcb41ddc37856732697a5cdbecb8b8`), whereas differing seeds (`seed=43`) produce distinct stochastic outage schedules (diverging grid availability hours) and distinct file hashes.
3. **Negative Controls:**  
   Verified that `assert_simulation_valid` trips with an `AssertionError` on 3 deliberate synthetic anomalies:
   - Injected $+10^{-3}\text{ kWh}$ hourly residual (trips `ViolationType.HOURLY_ENERGY_BALANCE`).
   - Stored battery SoC below $10\%$ protection floor (trips `ViolationType.MIN_SOC_VIOLATION`).
   - Injected `NaN` float in solar generation (trips `ViolationType.NON_FINITE_VALUE`).
4. **Plausibility & Benchmark Screening (`validation/plausibility.py`):**  
   Compared uncalibrated bottom-up demand (189,355.61 kWh/yr, EUI 75.74 kWh/m²·yr, peak 95.71 kW) against synthetic mock bills (398,537 kWh/yr, EUI 159.41 kWh/m²·yr) and Phase 1 placeholder baseline (`[D-23]`/`[D-24]`). Calculated monthly ASHRAE Guideline 14 metrics ($\text{NMBE} = -57.26\%$, $\text{CV(RMSE)} = 55.26\%$). Reconciled Batac solar AC specific yield ($1,508.74\text{ kWh/kWp}\cdot\text{yr}$) against the theoretical $\text{POA} \times \text{PR}$ product ($1,945.98 \times 0.77 = 1,498.40\text{ kWh/kWp}$, within $+0.69\%$), documenting that the $+16.24\%$ gap over the Luzon multi-system average ($1,298\text{ kWh/kWp}$) represents a solar resource gap, not model tuning.
5. **One-at-a-Time (OAT) Sensitivity Sweep (`validation/sensitivity.py`):**  
   Evaluated 5 critical operational and physical parameters on the 100 kWp / 100 kWh baseline: Emergency Reserve (0.10/0.20/0.50), Tier-2 Shed Threshold (0.10/0.20/0.30), Cooling Temperature Slope (3/4/5 %/°C), PR-driving BOS factor ($\pm 5\%$), and Battery RTE (0.88/0.92/0.96).
6. **Publication KPI Summary Tables (`results/kpi_tables.md`):**  
   Compiled full tabular summaries for the 4 reference configurations (grid-only, PV 100, PV 100 + Bat 100, PV 200 + Bat 200) under 2019 normal outages seed 0.
7. **Architectural Governance (`[D-37]`):**  
   Recorded epistemological framing, invariant audit matrix, plausibility comparisons, and sensitivity findings into `docs/decisions/decision-log.md`.

---

## 2. Implementation Details

### 2.1 File Structure & Touched Files
All core logic is implemented in the new `src/ccis_sim/validation/` package and verified by `tests/test_validation.py`. Conforming strictly to instructions, `src/ccis_sim/integration/engine.py` was **not modified**.

**Touched & Created Files:**
- `src/ccis_sim/validation/__init__.py`: Package entrypoint exporting public audit, plausibility, and sensitivity interfaces.
- `src/ccis_sim/validation/audit.py`: `audit_run(config, verify=True)` and `run_standard_audit_matrix()`.
- `src/ccis_sim/validation/plausibility.py`: `compute_ashrae_metrics`, `compute_plausibility_summary`, and `reconcile_solar_yield`.
- `src/ccis_sim/validation/sensitivity.py`: `run_oat_sensitivity_analysis` evaluating parameter deltas.
- `tests/test_validation.py`: 18 comprehensive unit and regression tests covering audits, reproducibility, negative controls, ASHRAE metrics, solar yield, and sensitivity sweeps.
- `results/kpi_tables.md`: Markdown tables documenting headline KPIs, audit matrices, plausibility benchmarks, and sensitivity results.
- `docs/decisions/decision-log.md`: Appended architectural decision `[D-37]`.
- `docs/tasks/status.md`: Marked `INT-003` and subtasks `INT-003.1`, `INT-003.2`, `INT-003.3` as `done`.
- `docs/reports/INT-003-gemini-validation.md`: This comprehensive task report.
- `docs/prompts/INT-003-PROMPT.md`: Archived standalone task prompt artifact.

### 2.2 Key Algorithms & Mathematical Implementations

#### Invariant Audit Function (`audit_run`)
Runs `simulate(config, verify=True)` and extracts:
- Max hourly residual $\max_t |E_{\text{in}, t} - E_{\text{out}, t}|$.
- Cumulative net residual drift $\sum_t (E_{\text{in}, t} - E_{\text{out}, t})$.
- Battery SoC boundary check: verifies $\text{SoC}_t \in [0.10 \times C_{\text{bat}}, C_{\text{bat}}]$ for all $t$ when $C_{\text{bat}} > 0$.
- Non-finite check: scans all 11 numeric fields across 8,760 records for `NaN` or `inf`.
- Tier conservation check: asserts $|(P_{\text{served}, t} + P_{\text{unserved}, t}) - P_{\text{gross}, t}| < 10^{-7}\text{ kWh}$ for all hours $t \in [1, 8760]$.

#### ASHRAE Guideline 14-2014 Monthly Calibration Metrics
Given simulated monthly values $y_{\text{sim}, i}$ and benchmark/bill monthly values $y_{\text{meas}, i}$ ($i=1,\dots,12$):
$$\text{NMBE} = \frac{\sum_{i=1}^{n} (y_{\text{sim}, i} - y_{\text{meas}, i})}{(n - 1) \cdot \bar{y}_{\text{meas}}} \times 100\%$$
$$\text{CV(RMSE)} = \frac{\sqrt{\frac{1}{n-1}\sum_{i=1}^{n} (y_{\text{sim}, i} - y_{\text{meas}, i})^2}}{\bar{y}_{\text{meas}}} \times 100\%$$
Standard Guideline 14 monthly compliance thresholds are $|\text{NMBE}| \le 5.0\%$ and $\text{CV(RMSE)} \le 15.0\%$.

#### Solar Yield Reconciliation
The theoretical annual specific yield is:
$$Y_{\text{theoretical}} = \text{POA} \times \text{PR} = 1,945.98\text{ kWh/m}^2 \times 0.77 \approx 1,498.40\text{ kWh/kWp}$$
Simulated AC specific yield is $1,508.74\text{ kWh/kWp}$. The delta relative to the theoretical product is $+0.69\%$ (due to hourly dynamic NOCT cell temperatures in Batac operating slightly more favorably during cool sunny winter mornings than the flat assumed mean thermal factor). The $+16.24\%$ gap over the Luzon multi-system average ($1,298\text{ kWh/kWp}$) reflects Batac's exceptional insolation resource ($1,901\text{ kWh/m}^2$ GHI, $1,946\text{ kWh/m}^2$ POA), which is substantially higher than cloudier southern/urban Luzon sites.

---

## 3. Verification & Test Evidence

### 3.1 Initial Pytest Run
Verbatim output at session initiation:
```text
........................................................................ [ 29%]
........................................................................ [ 58%]
........................................................................ [ 87%]
...............................                                          [100%]
247 passed in 29.82s
```

### 3.2 Final Pytest Run
Verbatim output upon task completion:
```text
........................................................................ [ 27%]
........................................................................ [ 54%]
........................................................................ [ 81%]
.................................................                        [100%]
265 passed in 74.63s (0:01:14)
```
*(All 265 tests passed, including 18 new comprehensive tests in `tests/test_validation.py` with 0 failures and 0 warnings).*

---

### 3.3 Table: Physical Conservation & Boundary Audit Matrix (Deliverable 1)
Evaluated across 12 configurations (8 primary combinations + 4 extended 2016 hot-year configurations). All pass with zero residual violations:

| Year | Regime | Solar (kWp) | Bat (kWh) | Max \|Residual\| (kWh) | Cum. Residual (kWh) | SoC Range (kWh) | SoC Bounds | Non-Finite | Tier Cons. | Status |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **2019** | **normal** | 0 | 0 | 0.00e+00 | 0.00e+00 | [0.0, 0.0] | PASS | 0 | PASS | **PASS** |
| **2019** | **normal** | 100 | 0 | 1.42e-14 | -7.55e-14 | [0.0, 0.0] | PASS | 0 | PASS | **PASS** |
| **2019** | **normal** | 100 | 100 | 1.42e-14 | -4.67e-13 | [29.7, 100.0] | PASS | 0 | PASS | **PASS** |
| **2019** | **normal** | 200 | 200 | 2.84e-14 | -6.63e-13 | [59.8, 200.0] | PASS | 0 | PASS | **PASS** |
| **2019** | **typhoon** | 0 | 0 | 0.00e+00 | 0.00e+00 | [0.0, 0.0] | PASS | 0 | PASS | **PASS** |
| **2019** | **typhoon** | 100 | 0 | 1.42e-14 | -7.19e-14 | [0.0, 0.0] | PASS | 0 | PASS | **PASS** |
| **2019** | **typhoon** | 100 | 100 | 1.42e-14 | -4.25e-13 | [10.0, 100.0] | PASS | 0 | PASS | **PASS** |
| **2019** | **typhoon** | 200 | 200 | 2.84e-14 | -6.00e-13 | [32.7, 200.0] | PASS | 0 | PASS | **PASS** |
| **2016** | **normal** | 0 | 0 | 0.00e+00 | 0.00e+00 | [0.0, 0.0] | PASS | 0 | PASS | **PASS** |
| **2016** | **normal** | 100 | 0 | 1.42e-14 | -9.86e-14 | [0.0, 0.0] | PASS | 0 | PASS | **PASS** |
| **2016** | **normal** | 100 | 100 | 1.42e-14 | -2.99e-13 | [29.8, 100.0] | PASS | 0 | PASS | **PASS** |
| **2016** | **normal** | 200 | 200 | 2.84e-14 | -5.69e-13 | [59.7, 200.0] | PASS | 0 | PASS | **PASS** |

---

### 3.4 Reproducibility Verification (Deliverable 2)
- Seed 42 run 1 SHA-256: `11e017778df2ba5b78110c97f6fa64f38bfcb41ddc37856732697a5cdbecb8b8`
- Seed 42 run 2 SHA-256: `11e017778df2ba5b78110c97f6fa64f38bfcb41ddc37856732697a5cdbecb8b8`
- **Result:** Identical (`h1 == h2: True`).
- Seed 43 run SHA-256: `624f9c742a5700241b918f40b016bdb9498afb1c5e71d04b9b71073bd0dcb659`
- Outage schedules differ: `(grid_available_42 != grid_available_43).sum() > 0`.
- **Result:** Divergent (`h1 != h3: True`).

---

### 3.5 Negative Controls (Deliverable 3)
Verified in `tests/test_validation.py` and citing prior unit tests in `tests/test_conservation_checker.py`:
1. **Residual Perturbation ($+10^{-3}\text{ kWh}$):** Injected into `grid_import_kwh` at hour 10. `assert_simulation_valid` raised `AssertionError` with message `"Hourly energy balance residual 1.000000e-03 kWh exceeded tolerance 1.000000e-05 kWh"`. *(Cites `test_deliberate_hourly_residual_violation_caught`).*
2. **SoC Below Minimum Floor:** Battery SoC set to $5.0\text{ kWh}$ ($< 10.0\text{ kWh}$ min floor). `assert_simulation_valid` raised `AssertionError` tripping boundary protection. *(Cites `test_battery_min_soc_floor_normal_vs_emergency`).*
3. **Non-Finite (`NaN`) Guard:** Injected `float("nan")` into `solar_generation_kwh` at hour 20. `assert_simulation_valid` raised `AssertionError` with message `"Field 'solar_generation_kwh' contains non-finite value: nan"`. *(Cites `test_non_finite_value_caught_in_conservation`).*

---

### 3.6 Plausibility & Benchmark Comparison (Deliverable 4)

#### Annual Demand & EUI Comparison
- **Bottom-Up Simulated (`DEM-001`/`DEM-002`):** $189,355.61\text{ kWh/yr}$ | **EUI: $75.74\text{ kWh/m}^2\cdot\text{yr}$** | Peak: $95.71\text{ kW}$ | Load Factor: $0.2259$ ($22.59\%$).
- **Calibrated Baseline Placeholder (`[D-23]`/`[D-24]`):** $398,525.00\text{ kWh/yr}$ | EUI: $159.41\text{ kWh/m}^2\cdot\text{yr}$ | Peak: $124.44\text{ kW}$ | Load Factor: $0.3656$ ($36.56\%$).
- **Uncalibrated Baseline Placeholder (`[D-24]`):** $324,379.71\text{ kWh/yr}$ | EUI: $129.75\text{ kWh/m}^2\cdot\text{yr}$ | Peak: $101.29\text{ kW}$.
- **Synthetic Mock Bills (`CORE-003`):** $398,536.77\text{ kWh/yr}$ | EUI: $159.41\text{ kWh/m}^2\cdot\text{yr}$ | Peak: $139.24\text{ kW}$.
- **Regional Academic/Office Benchmark Range (`docs/context/research-synthesis.md` §2):**
  - Tropical SE Asian air-conditioned office/academic: $160 \text{ to } 275\text{ kWh/m}^2\cdot\text{yr}$.
  - Philippine DOE Commercial Survey: $213 \text{ to } 336\text{ kWh/m}^2\cdot\text{yr}$ (median: $275\text{ kWh/m}^2\cdot\text{yr}$).
  - ASEAN 3-Star Energy Efficiency Target: $\approx 160\text{ kWh/m}^2\cdot\text{yr}$.
  - Regional benchmark band: $150 \le \text{EUI} \le 300\text{ kWh/m}^2\cdot\text{yr}$.
- *Why is uncalibrated bottom-up EUI ($75.74$) below the regional band?*  
  The regional band ($160\text{–}275\text{ kWh/m}^2\cdot\text{yr}$) characterizes commercial administrative office buildings with continuous occupancy, dense desktop IT equipment, and $24/7$ or extended central chiller cooling. In contrast, CCIS is an academic university facility where classrooms operate only 07:00–19:00 on weekdays, spaces are uncooled and unoccupied on weekends and academic breaks, and true continuous standby load is just $6.07\text{ kW}$ (distributed network switches + emergency lighting).

#### Monthly Profile & ASHRAE Guideline 14 Metrics
Comparison of uncalibrated monthly simulation vs synthetic mock bills:

| Month | Bottom-Up Sim (kWh) | Synthetic Mock Bill (kWh) | Delta (kWh) | Relative Diff (%) |
| :---: | :---: | :---: | :---: | :---: |
| Jan (01) | 14,276.77 | 32,432.44 | -18,155.67 | -55.98% |
| Feb (02) | 18,043.67 | 31,594.21 | -13,550.54 | -42.89% |
| Mar (03) | 21,829.85 | 39,564.76 | -17,734.91 | -44.83% |
| Apr (04) | 20,214.23 | 40,425.52 | -20,211.29 | -50.00% |
| May (05) | 18,539.02 | 33,421.04 | -14,882.02 | -44.53% |
| Jun (06) | 6,362.65 | 25,505.51 | -19,142.86 | -75.05% |
| Jul (07) | 6,767.74 | 27,024.25 | -20,256.51 | -74.96% |
| Aug (08) | 12,919.46 | 32,194.45 | -19,274.99 | -59.87% |
| Sep (09) | 19,580.18 | 35,987.29 | -16,407.11 | -45.59% |
| Oct (10) | 21,521.02 | 35,579.62 | -14,058.60 | -39.51% |
| Nov (11) | 17,587.79 | 34,529.90 | -16,942.11 | -49.07% |
| Dec (12) | 11,713.25 | 30,277.78 | -18,564.53 | -61.31% |

- **Total Delta:** $-209,181.16\text{ kWh}$ ($-52.49\%$).
- **NMBE:** **$-57.26\%$** (raw: $-52.49\%$). Threshold: $\pm 5.0\%$.
- **CV(RMSE):** **$55.26\%$**. Threshold: $15.0\%$.
- **Compliance:** **FAIL**. Conforms to expectations: the bottom-up model reflects unoccupied university recesses (e.g. June–July semester break consumption drops to $\sim 6,500\text{ kWh/mo}$), whereas synthetic bills assumed full baseline activity.

#### Day-Type Mean Daily Consumption
- **Regular Academic Weekdays (N=172):** **$845.76\text{ kWh/day}$** (mean power: $35.24\text{ kW}$).
- **Weekends (N=69):** **$268.57\text{ kWh/day}$** (mean power: $11.19\text{ kW}$).
- **Vacation / Academic Breaks / Holidays (N=124):** **$204.46\text{ kWh/day}$** (mean power: $8.52\text{ kW}$).

#### Solar Yield Reconciliation
- **Batac Transposed POA Insolation:** $1,945.98\text{ kWh/m}^2\cdot\text{yr}$ (SOL-001).
- **System Performance Ratio (PR):** $0.77$ (`[D-08]`/`[D-30]`).
- **Theoretical Specific Yield ($\text{POA} \times \text{PR}$):** **$1,498.40\text{ kWh/kWp}\cdot\text{yr}$**.
- **Simulated AC Specific Yield:** **$1,508.74\text{ kWh/kWp}\cdot\text{yr}$**.
- **Discrepancy vs Theoretical Product:** **$+0.69\%$** (accurate physics match).
- **Discrepancy vs Luzon Target ($1,298\text{ kWh/kWp}$):** **$+16.24\%$**. Driven entirely by resource insolation differences ($1,946\text{ kWh/m}^2$ Batac POA vs $\sim 1,650\text{ kWh/m}^2$ southern Luzon average), confirming this is a resource-data difference, not an artificially tuned parameter.

---

### 3.7 One-at-a-Time (OAT) Parameter Sensitivity (Deliverable 5)
Base case: $100\text{ kWp}$ PV, $100\text{ kWh}$ battery, 2019 normal outages, seed 0.  
Baseline Grid Import = **$79,064.38\text{ kWh}$**, Unserved T1+2 = **$0.00\text{ kWh}$**.

| Parameter | Variation | Value | Grid Import (kWh) | Δ Grid (kWh) | Unserved T1+2 (kWh) | Δ Unserved T1+2 (kWh) | Exposure Method | Notes |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **Emergency Reserve** | Reserve = 10% | 0.10 | 77,353.76 | -1,710.62 | 11.58 | +11.58 | Exposed | Configurable via `SimulationConfig.emergency_reserve_pct` |
| **Emergency Reserve** | Reserve = 20% | 0.20 | 79,064.38 | +0.00 | 0.00 | +0.00 | Exposed | Baseline standard configuration |
| **Emergency Reserve** | Reserve = 50% | 0.50 | 84,338.74 | +5,274.36 | 0.00 | +0.00 | Exposed | Higher reserve prevents routine cycling, increasing grid import |
| **Tier-2 Shedding Threshold** | Shed SoC = 10% | 0.10 | 79,064.38 | +0.00 | 0.00 | +0.00 | Exposed | Configurable via `SimulationConfig.tier2_shed_soc_fraction` |
| **Tier-2 Shedding Threshold** | Shed SoC = 20% | 0.20 | 79,064.38 | +0.00 | 0.00 | +0.00 | Exposed | Baseline standard configuration |
| **Tier-2 Shedding Threshold** | Shed SoC = 30% | 0.30 | 79,064.38 | +0.00 | 11.58 | +11.58 | Exposed | Sheds Tier 2 earlier to preserve battery, causing 11.58 kWh unserved |
| **Cooling Slope (%/°C)** | Slope = 3.0%/°C | 0.03 | 72,568.26 | -6,496.12 | 0.00 | +0.00 | Exposed | Configurable on `Building.cooling_sensitivity_per_c` |
| **Cooling Slope (%/°C)** | Slope = 4.0%/°C | 0.04 | 79,064.38 | +0.00 | 0.00 | +0.00 | Exposed | Baseline standard building archetype |
| **Cooling Slope (%/°C)** | Slope = 5.0%/°C | 0.05 | 85,565.66 | +6,501.28 | 0.00 | +0.00 | Exposed | Higher cooling sensitivity increases grid import by 8.2% |
| **PR-Driving BOS Factor** | -5% BOS (PR 0.73) | 0.95 | 82,784.90 | +3,720.52 | 0.00 | +0.00 | Monkeypatched | Monkeypatched in `engine.compute_ac_generation` soiling factor |
| **PR-Driving BOS Factor** | Baseline BOS (PR 0.77)| 1.00 | 79,064.38 | +0.00 | 0.00 | +0.00 | Monkeypatched | Baseline standard PR loss factor |
| **PR-Driving BOS Factor** | +5% BOS (PR 0.81) | 1.05 | 75,376.88 | -3,687.50 | 0.00 | +0.00 | Monkeypatched | Higher solar generation decreases grid import by 4.7% |
| **Battery RTE** | RTE = 0.88 | 0.88 | 79,435.99 | +371.61 | 0.00 | +0.00 | Monkeypatched | Monkeypatched in `Battery.__init__.__defaults__` |
| **Battery RTE** | RTE = 0.92 | 0.92 | 79,064.38 | +0.00 | 0.00 | +0.00 | Monkeypatched | Baseline LFP round-trip efficiency `[D-09]` |
| **Battery RTE** | RTE = 0.96 | 0.96 | 78,699.70 | -364.68 | 0.00 | +0.00 | Monkeypatched | Higher RTE reduces round-trip conversion loss |

---

### 3.8 Headline KPI Table for Reference Configurations (Deliverable 6)
Reference cases on 2019 normal outages, seed 0 (committed to `results/kpi_tables.md`):

| Scenario | Solar (kWp) | Battery (kWh) | Grid Import (kWh) | Solar Gen (kWh) | Curtailment (kWh) | Self-Sufficiency | Peak Grid (kW) | Outage Hrs Served (T1 / T2) | Unserved T1 (kWh) | Unserved T2 (kWh) | Unserved T3 (kWh) | Battery Cycles |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Grid-Only Baseline** | 0 | 0 | 189,142.12 | 0.00 | 0.00 | 0.00% | 95.71 | 0/8 (0%) / 0/8 (0%) | 9.72 | 41.92 | 161.84 | 0.00 |
| **PV-Only (100 kWp)** | 100 | 0 | 93,689.00 | 150,873.58 | 55,386.02 | 50.48% | 74.61 | 3/8 (38%) / 3/8 (38%) | 6.08 | 11.13 | 161.84 | 0.00 |
| **PV 100 + Battery 100** | 100 | 100 | 79,064.38 | 150,873.58 | 39,491.34 | 58.21% | 74.61 | 8/8 (100%) / 8/8 (100%) | 0.00 | 0.00 | 161.84 | 146.42 |
| **PV 200 + Battery 200** | 200 | 200 | 23,878.48 | 301,747.16 | 133,361.21 | 87.38% | 65.97 | 8/8 (100%) / 8/8 (100%) | 0.00 | 0.00 | 161.84 | 176.25 |

---

## 4. Git Diff

```diff
diff --git a/docs/decisions/decision-log.md b/docs/decisions/decision-log.md
index b7f628f..bc3a051 100644
--- a/docs/decisions/decision-log.md
+++ b/docs/decisions/decision-log.md
@@ -433,3 +433,37 @@ This file exists so that across API-credit-limited handoffs between APC AI insta
      Provide pure functional exporters in `src/ccis_sim/integration/exporters.py` generating hourly timeseries CSV, daily aggregated timeseries CSV, and an annual summary JSON adhering to Phase 2 schemas. Provide the CLI command `ccis-sim run` (`src/ccis_sim/cli.py`) with rich tabular console summaries and artifact file output.  
 - **Reasoning:** Establishes the authoritative Phase 2 integrated simulation engine, satisfies all interface contracts, decouples triage policies from physical battery states, and establishes rigorous, physically-grounded cross-verification for demand and solar sub-models.  
 - **Affects:** `ccis_sim.integration`, `ccis_sim.cli`, `INT-001`, `DEM-002.4`, `SOL-002.4`, `DEC-002`.
+
+
+**[D-37]** Verification Invariants, Plausibility Screening, Epistemological Framing, and KPI Tables (INT-003).  
+- **Date / Session:** 2026-10-21  
+- **Decision:**  
+  1. **Epistemological Framing and Validation Status:**  
+     Formally declare that simulation evaluation against synthetic mock utility bills represents **computational verification, physical conservation auditing, and plausibility screening, NOT empirical validation**. Because synthetic mock bills (CORE-003) were generated using the same equipment audit inventory as the bottom-up model, billing comparisons are not independent. The bottom-up demand profile (189,356 kWh/yr, EUI 75.74 kWh/m²·yr) is retained in its uncalibrated state (scale = 1.0) as the primary engineering model.  
+  2. **Energy Conservation and Physical Invariant Audit Matrix:**  
+     Establish `ccis_sim.validation.audit.audit_run` executing 8 primary (+4 extended) simulation configurations across solar (0, 100, 200 kWp), battery (0, 100, 200 kWh), and weather/outage regimes (2019 normal, 2019 typhoon, 2016 normal). All 12 configurations strictly pass all invariants:  
+     - Maximum hourly energy balance residual: $\le 2.84 \times 10^{-14}\text{ kWh} \ll 10^{-5}\text{ kWh}$.  
+     - Cumulative net drift: $\le 6.63 \times 10^{-13}\text{ kWh} \ll 10^{-3}\text{ kWh}$.  
+     - Non-finite numeric count: 0 across all 8,760 hours.  
+     - Battery SoC bounds: strictly within $[10\%\text{ min\_soc}, 100\%\text{ capacity}]$.  
+     - Tier demand conservation: $P_{\text{served}, t} + P_{\text{unserved}, t} = P_{\text{gross}, t}$ for all $t \in [1, 8760]$.  
+  3. **Seed Determinism and Reproducibility Protocol:**  
+     Verify bit-identical determinism: identical seeds yield identical SHA-256 hourly CSV hashes; differing seeds produce distinct stochastic outage schedules ($N > 0$ diverging grid availability hours) and distinct hashes.  
+  4. **Negative Control Verification:**  
+     Verify that `assert_simulation_valid` reliably catches three deliberate breaks:  
+     - Perturbed hourly residual ($+10^{-3}\text{ kWh}$): trips `ViolationType.HOURLY_ENERGY_BALANCE`.  
+     - Stored SoC below minimum floor ($< 10\%\text{ min\_soc}$): trips `ViolationType.MIN_SOC_VIOLATION`.  
+     - Non-finite field (`NaN`): trips `ViolationType.NON_FINITE_VALUE`.  
+  5. **Plausibility and Benchmark Reconciliation:**  
+     - ASHRAE Guideline 14 comparison against synthetic bills yields monthly $\text{NMBE} = -57.26\%$ and $\text{CV(RMSE)} = 55.26\%$ (failing monthly thresholds of $\pm 5\%$ and $15\%$, as expected for uncalibrated bottom-up demand reflecting unoccupied hours vs continuous baseline assumptions).  
+     - Day-type daily consumption: regular academic weekdays ($845.76\text{ kWh/day}$), weekends ($268.57\text{ kWh/day}$), academic vacations/holidays ($204.46\text{ kWh/day}$).  
+     - Solar specific yield: $1,508.74\text{ kWh/kWp}\cdot\text{yr}$ matches theoretical $\text{POA} \times \text{PR}$ ($1,945.98 \times 0.77 \approx 1,498.40\text{ kWh/kWp}$) within $+0.69\%$. The $+16.24\%$ gap over the Luzon multi-system average ($1,298\text{ kWh/kWp}$) is identified as a resource-data difference in Batac insolation, not model tuning.  
+  6. **One-at-a-Time Parameter Sensitivity:**  
+     Evaluate sensitivity relative to the 100 kWp / 100 kWh baseline (grid import: 79,064.38 kWh, unserved T1+2: 0.00 kWh):  
+     - Emergency reserve (0.10 / 0.20 / 0.50): grid import shifts by $-1,710.62\text{ kWh}$ to $+5,274.36\text{ kWh}$; unserved T1+2 increases to $11.58\text{ kWh}$ at 0.10 reserve.  
+     - Tier-2 shed threshold (0.10 / 0.20 / 0.30): unserved T1+2 increases to $11.58\text{ kWh}$ at 0.30 threshold (shedding triggered earlier).  
+     - Cooling slope (3% / 4% / 5% /°C): grid import shifts by $\mp 6,500\text{ kWh}$ ($\pm 8.2\%$).  
+     - PR-driving BOS factor ($\pm 5\%$): grid import shifts by $\mp 3,700\text{ kWh}$ ($\mp 4.7\%$).  
+     - Battery RTE (0.88 / 0.92 / 0.96): grid import shifts by $+371.61\text{ kWh}$ / $-364.68\text{ kWh}$ ($\pm 0.47\%$).  
+- **Reasoning:** Closes verification and plausibility audit milestones for Phase 3, guarantees strict mathematical and physical validity of simulation output data, documents sensitivity bounds, and provides authoritative headline KPI tables for downstream multi-criteria decision analysis.  
+- **Affects:** `ccis_sim.validation`, `results/kpi_tables.md`, `INT-003`, `DEC-001`, `DEC-002`, `DEC-003`.
diff --git a/docs/tasks/status.md b/docs/tasks/status.md
index 60636a4..02c808f 100644
--- a/docs/tasks/status.md
+++ b/docs/tasks/status.md
@@ -131,10 +131,10 @@ Status: **open**
 | INT-002.1   | Monte Carlo driver (N = 100 seeds per scenario)                     | `open` | MC engine                                                         |
 | INT-002.2   | Stochastic convergence test (sample size sufficiency)               | `open` | Convergence                                                       |
 | INT-002.3   | Record distributions: unserved kWh, outage hours survived           | `open` | Distributions                                                     |
-| **INT-003** | **Verification, Validation & Headline KPI Reporting**               | `open` |                                                                   |
-| INT-003.1   | Final energy balance audit (residual < 10⁻⁵ kWh everywhere)         | `open` | Balance audit                                                     |
-| INT-003.2   | Compare uncalibrated simulation vs synthetic bills (NMBE, CV(RMSE)) | `open` | Billing validation                                                |
-| INT-003.3   | Generate publication-quality headline KPI summary tables             | `open` | KPI tables                                                        |
+| **INT-003** | **Verification, Validation & Headline KPI Reporting**               | `done` | [Report](docs/reports/INT-003-gemini-validation.md) [D-37] Audits, plausibility, sensitivities |
+| INT-003.1   | Final energy balance audit (residual < 10⁻⁵ kWh everywhere)         | `done` | Invariant audit across 12 configs (residual < 3e-14 kWh) [D-37]    |
+| INT-003.2   | Compare uncalibrated simulation vs synthetic bills (NMBE, CV(RMSE)) | `done` | ASHRAE NMBE -57.3%, CV(RMSE) 55.3%, plausibility reconciliation    |
+| INT-003.3   | Generate publication-quality headline KPI summary tables             | `done` | [kpi_tables.md](../../results/kpi_tables.md) reference cases      |
```

---

## 5. Artifacts and Patch Deliverable
- **Patch file location:** `patch/INT-003-gemini-validation.patch` (exported and gitignored per constitutional rules).
- **KPI Summary Artifact:** `results/kpi_tables.md` (committed).
- **Prompt Archive:** `docs/prompts/INT-003-PROMPT.md` (committed).

---

## 6. Items Flagged for APC AI Attention
1. **Parallel Execution Status:**  
   `INT-003` completed in isolated worktree `ccis-heat-load-backup-sim-INT-003` on branch `task/INT-003`. Per instructions, `src/ccis_sim/integration/engine.py` was kept untouched, leaving full freedom for `task/INT-002` to incorporate `demand_scale` and Monte Carlo sweeps without merge hazards.
2. **Plausibility vs Calibration Stance:**  
   The uncalibrated bottom-up demand ($189,356\text{ kWh/yr}$, EUI $75.74\text{ kWh/m}^2\cdot\text{yr}$) fails the synthetic bill ASHRAE Guideline 14 thresholds ($\text{NMBE} = -57.26\%$, $\text{CV(RMSE)} = 55.26\%$). This is an expected physical reality: the bottom-up model faithfully captures classroom diversity and weekend/vacation shutdowns, whereas the synthetic mock bills were generated assuming continuous $24/7$ operational baseload. If bill-calibrated demand is desired for sizing sensitivity, it should be applied as a single scalar multiplier ($\approx 2.105$, per INT-002 policy) without modifying physical equipment power ratings.
3. **Downstream Decision Matrix Handoff:**  
   `results/kpi_tables.md` provides all headline metrics required by Phase 4 (`DEC-001`, `DEC-002`), including self-sufficiency percentages, unserved load per tier, outage survival durations, and equivalent battery cycling throughput.
