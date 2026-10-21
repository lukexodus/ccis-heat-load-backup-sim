# CCIS Microgrid Simulation Verification, Plausibility, and KPI Tables (INT-003)

> [!IMPORTANT]
> **Framing & Epistemological Status:** The synthetic utility bills and bottom-up model originate from the same equipment audit inventory. Consequently, this study represents **computational verification, physical conservation auditing, and plausibility screening**, rather than empirical field validation. Bottom-up demand is deliberately reported in its uncalibrated state (scale = 1.0) rather than tuned artificially to match synthetic utility bills.

---

## Table 1: Headline KPIs for Reference Configurations (2019 Normal, Seed 0)

| Scenario | Solar (kWp) | Battery (kWh) | Grid Import (kWh) | Solar Gen (kWh) | Curtailment (kWh) | Self-Sufficiency | Peak Grid (kW) | Outage Hrs Served (T1 / T2) | Unserved T1 (kWh) | Unserved T2 (kWh) | Unserved T3 (kWh) | Battery Cycles |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| Grid-Only Baseline | 0 | 0 | 189,142.12 | 0.00 | 0.00 | 0.00% | 95.71 | 0/8 (0%) / 0/8 (0%) | 9.72 | 41.92 | 161.84 | 0.00 |
| PV-Only (100 kWp) | 100 | 0 | 93,689.00 | 150,873.58 | 55,386.02 | 50.48% | 74.61 | 3/8 (38%) / 3/8 (38%) | 6.08 | 11.13 | 161.84 | 0.00 |
| PV (100 kWp) + Battery (100 kWh) | 100 | 100 | 79,064.38 | 150,873.58 | 39,491.34 | 58.21% | 74.61 | 8/8 (100%) / 8/8 (100%) | 0.00 | 0.00 | 161.84 | 146.42 |
| PV (200 kWp) + Battery (200 kWh) | 200 | 200 | 23,878.48 | 301,747.16 | 133,361.21 | 87.38% | 65.97 | 8/8 (100%) / 8/8 (100%) | 0.00 | 0.00 | 161.84 | 176.25 |

---

## Table 2: Physical Conservation & Boundary Audit Matrix (8 Primary + 4 Extended Configurations)

| Year | Regime | Solar (kWp) | Bat (kWh) | Max |Residual| (kWh) | Cum. Residual (kWh) | SoC Range (kWh) | SoC Bounds | Non-Finite | Tier Conservation | Status |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 2019 | normal | 0 | 0 | 0.00e+00 | 0.00e+00 | [0.0, 0.0] | PASS | 0 | PASS | **PASS** |
| 2019 | normal | 100 | 0 | 1.42e-14 | -7.55e-14 | [0.0, 0.0] | PASS | 0 | PASS | **PASS** |
| 2019 | normal | 100 | 100 | 1.42e-14 | -4.67e-13 | [29.7, 100.0] | PASS | 0 | PASS | **PASS** |
| 2019 | normal | 200 | 200 | 2.84e-14 | -6.63e-13 | [59.8, 200.0] | PASS | 0 | PASS | **PASS** |
| 2019 | typhoon | 0 | 0 | 0.00e+00 | 0.00e+00 | [0.0, 0.0] | PASS | 0 | PASS | **PASS** |
| 2019 | typhoon | 100 | 0 | 1.42e-14 | -7.19e-14 | [0.0, 0.0] | PASS | 0 | PASS | **PASS** |
| 2019 | typhoon | 100 | 100 | 1.42e-14 | -4.25e-13 | [10.0, 100.0] | PASS | 0 | PASS | **PASS** |
| 2019 | typhoon | 200 | 200 | 2.84e-14 | -6.00e-13 | [32.7, 200.0] | PASS | 0 | PASS | **PASS** |
| 2016 | normal | 0 | 0 | 0.00e+00 | 0.00e+00 | [0.0, 0.0] | PASS | 0 | PASS | **PASS** |
| 2016 | normal | 100 | 0 | 1.42e-14 | -9.86e-14 | [0.0, 0.0] | PASS | 0 | PASS | **PASS** |
| 2016 | normal | 100 | 100 | 1.42e-14 | -2.99e-13 | [29.8, 100.0] | PASS | 0 | PASS | **PASS** |
| 2016 | normal | 200 | 200 | 2.84e-14 | -5.69e-13 | [59.7, 200.0] | PASS | 0 | PASS | **PASS** |

---

## Table 3: Plausibility & Benchmark Comparison

### 3.1 Facility Demand & EUI Benchmark Comparison

| Metric | Bottom-Up Simulated (DEM-001/002) | Calibrated Baseline Placeholder (D-23/D-24) | Synthetic Mock Bills (CORE-003) | Regional Benchmark Band (docs/context/research-synthesis.md §2) |
| :--- | :---: | :---: | :---: | :---: |
| **Annual Energy (kWh/yr)** | 189,355.61 | 398,525.00 | 398,536.77 | 375,000 – 687,500 (implied for 2,500 m²) |
| **Energy Use Intensity (EUI)** | **75.74 kWh/m²·yr** | 159.41 kWh/m²·yr | 159.41 kWh/m²·yr | 160 – 275 kWh/m²·yr (Office/Academic); ASEAN 3-Star: ~160 |
| **Peak Electrical Demand (kW)** | 95.71 kW (Hour 2340) | 124.44 kW (provisional) | 139.24 kW | Peak coincident capacity |
| **Annual Load Factor** | 0.2259 (22.59%) | 0.3656 (36.56%) | ~0.3267 | Diurnal academic occupancy pattern |

### 3.2 Monthly Consumption Profile & ASHRAE Guideline 14 Metrics

| Month | Bottom-Up Sim (kWh) | Synthetic Mock Bill (kWh) | Delta (kWh) | Relative Difference (%) |
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

- **Total Annual Delta:** -209,181.16 kWh (-52.49%)
- **NMBE (Normalized Mean Bias Error):** -57.26% (Degrees of freedom $n-1=11$; raw ratio: -52.49%) [Threshold: ±5.0%]
- **CV(RMSE) (Coefficient of Variation of RMSE):** 55.26% [Threshold: 15.0%]
- **Compliance Status:** **FAIL** (Expected: bottom-up uncalibrated demand is physically based on actual room schedules and shuts off unoccupied loads, whereas synthetic bills assumed 24/7 continuous baseload and continuous cooling).

### 3.3 Diurnal & Day-Type Mean Daily Consumption

| Day Classification | Number of Days | Daily Mean Energy (kWh/day) | Equivalent Mean Power (kW) | Physical Operational Drivers |
| :--- | :---: | :---: | :---: | :--- |
| **Regular Academic Weekday** | 172 | **845.76 kWh/day** | 35.24 kW | High occupancy, 6 computer labs, 18 rooms active cooling (07:00–19:00) |
| **Weekend (Saturday/Sunday)** | 69 | **268.57 kWh/day** | 11.19 kW | Standby IT equipment, network switches, zero student cooling |
| **Academic Break / Holiday** | 124 | **204.46 kWh/day** | 8.52 kW | Summer/Christmas break; minimal administrative staff load |

### 3.4 Solar Specific Yield Reconciliation

| Parameter / Metric | Value | Reference / Derivation |
| :--- | :---: | :--- |
| **Batac Transposed POA Insolation** | **1,945.98 kWh/m²·yr** | 15° True South transposition from NASA POWER 2019 hourly GHI (SOL-001) |
| **System Baseline Performance Ratio (PR)** | **0.77** | Locked in [D-08] and decomposed into BOS losses in [D-30] |
| **Theoretical Specific Yield (POA × PR)** | **1,498.40 kWh/kWp·yr** | $1,945.98 \times 0.77 \approx 1,498.40\text{ kWh/kWp}$ |
| **Simulated AC Specific Yield (SOL-001/002)** | **1,508.74 kWh/kWp·yr** | End-to-end simulated AC generation at inverter output |
| **Luzon Multi-System Benchmark Target** | **1,298.00 kWh/kWp·yr** | Regional average from Philippine literature [D-30] |
| **Discrepancy vs Luzon Target** | **+16.24%** | Driven by resource-data gap: Batac POA (1,946 kWh/m²) is significantly sunnier than cloudier southern/urban Luzon sites |
| **Discrepancy vs Theoretical POA × PR** | **+0.69%** | Physics model matches theoretical prediction within 0.69% |

---

## Table 4: One-at-a-Time (OAT) Sensitivity Analysis (100 kWp / 100 kWh, 2019 Normal, Seed 0)

**Baseline Reference (100 kWp / 100 kWh):** Grid Import = **79,064.38 kWh**, Unserved T1+2 = **0.00 kWh**.

| Parameter | Variation | Value | Grid Import (kWh) | Δ Grid (kWh) | Unserved T1+2 (kWh) | Δ Unserved T1+2 (kWh) | Exposure Method | Notes |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| Emergency Reserve Fraction | Reserve = 10% | 0.1 | 77353.76 | -1710.62 | 11.58 | +11.58 | Yes | Configurable on SimulationConfig.emergency_reserve_pct |
| Emergency Reserve Fraction | Reserve = 20% | 0.2 | 79064.38 | +0.0 | 0.0 | +0.0 | Yes | Configurable on SimulationConfig.emergency_reserve_pct |
| Emergency Reserve Fraction | Reserve = 50% | 0.5 | 84338.74 | +5274.36 | 0.0 | +0.0 | Yes | Configurable on SimulationConfig.emergency_reserve_pct |
| Tier-2 Shedding Threshold | Shed SoC = 10% | 0.1 | 79064.38 | +0.0 | 0.0 | +0.0 | Yes | Configurable on SimulationConfig.tier2_shed_soc_fraction |
| Tier-2 Shedding Threshold | Shed SoC = 20% | 0.2 | 79064.38 | +0.0 | 0.0 | +0.0 | Yes | Configurable on SimulationConfig.tier2_shed_soc_fraction |
| Tier-2 Shedding Threshold | Shed SoC = 30% | 0.3 | 79064.38 | +0.0 | 11.58 | +11.58 | Yes | Configurable on SimulationConfig.tier2_shed_soc_fraction |
| Cooling Slope (%/°C) | Slope = 3.0%/°C | 0.03 | 72568.26 | -6496.12 | 0.0 | +0.0 | Yes | Exposed on Building archetype constructor |
| Cooling Slope (%/°C) | Slope = 4.0%/°C | 0.04 | 79064.38 | +0.0 | 0.0 | +0.0 | Yes | Exposed on Building archetype constructor |
| Cooling Slope (%/°C) | Slope = 5.0%/°C | 0.05 | 85565.66 | +6501.28 | 0.0 | +0.0 | Yes | Exposed on Building archetype constructor |
| PR-Driving BOS Factor | -5% BOS (lower PR) | 95% of base | 82784.9 | +3720.52 | 0.0 | +0.0 | Monkeypatched | Monkeypatched in engine.compute_ac_generation (soiling factor) |
| PR-Driving BOS Factor | Baseline BOS (PR 0.77) | 100% of base | 79064.38 | +0.0 | 0.0 | +0.0 | Monkeypatched | Monkeypatched in engine.compute_ac_generation (soiling factor) |
| PR-Driving BOS Factor | +5% BOS (higher PR) | 105% of base | 75376.88 | -3687.5 | 0.0 | +0.0 | Monkeypatched | Monkeypatched in engine.compute_ac_generation (soiling factor) |
| Battery Round-Trip Efficiency (RTE) | RTE = 0.88 | 0.88 | 79435.99 | +371.61 | 0.0 | +0.0 | Monkeypatched | Monkeypatched in Battery.__init__.__defaults__ (not on SimulationConfig) |
| Battery Round-Trip Efficiency (RTE) | RTE = 0.92 | 0.92 | 79064.38 | +0.0 | 0.0 | +0.0 | Monkeypatched | Monkeypatched in Battery.__init__.__defaults__ (not on SimulationConfig) |
| Battery Round-Trip Efficiency (RTE) | RTE = 0.96 | 0.96 | 78699.7 | -364.68 | 0.0 | +0.0 | Monkeypatched | Monkeypatched in Battery.__init__.__defaults__ (not on SimulationConfig) |
