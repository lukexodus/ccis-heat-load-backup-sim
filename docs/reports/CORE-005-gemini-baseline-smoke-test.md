# Task Report: CORE-005 — Baseline Engine Smoke Test (Phase 1 Exit Gate)

**Task ID:** CORE-005 (covers CORE-005.1 – CORE-005.3)  
**Agent:** Gemini (local coding agent)  
**Date:** 2026-10-20  
**Status:** Completed  
**Decisions Locked:** [D-23]  
**Patch File:** `patch/CORE-005-gemini-baseline-smoke-test.patch`  

---

## 1. Executive Summary

This unit of work completes task `CORE-005` ("Baseline Engine Smoke Test"), the official **Phase 1 Exit Gate** for the CCIS Heat Load & Backup Power Simulation project. It proves end-to-end integration and verification of all core architectural infrastructure built across Phase 0 and Phase 1 (`ARCH-001/002`, `CORE-001` domain models, `CORE-002` NASA POWER weather ingestion, `CORE-003` equipment audit, and `CORE-004` energy balance test harness) before the four parallel Phase 2 tracks (`DEM`, `SOL`, `BAT`, `OUT`) begin.

Key accomplishments:
1. **Grid-Only Baseline Engine (`CORE-005.1`)**: Implemented `src/ccis_sim/integration/baseline.py`, which executes an 8,760-hour continuous simulation using the verified 2019 Batac weather fixture and the bottom-up equipment audit. It employs a deliberately lightweight, isolated placeholder demand schedule calibrated once to match the regional EUI target of $159.41\text{ kWh/m}^2\cdot\text{yr}$ ($398,525.00\text{ kWh/yr}$) per decision `[D-23]`.
2. **Energy Balance Harness Verification & Negative Control (`CORE-005.2`)**: The full 8,760-record baseline time series was evaluated through the `CORE-004` verification harness. It achieved **zero energy balance violations** (max hourly residual $\le 10^{-12}\text{ kWh}$) and zero cumulative drift ($0.000\text{ kWh} \ll 9.359 \times 10^{-4}\text{ kWh}$ tolerance under `[D-21]`). Two negative control tests verified that deliberate hourly imbalances (+1.0 kWh) and small persistent cumulative biases ($+0.9 \times 10^{-5}\text{ kWh/hr}$) reliably trip the harness.
3. **Headline Metrics & Climate Sensitivity (`CORE-005.3`)**: Produced annual energy, peak kW, EUI, load factor, and monthly totals. Simulated the 2016 El Niño hot year without re-tuning, confirming that peak electrical demand increased to **125.55 kW** (+1.11 kW, +0.89%) driven by peak summer heat.
4. **Test Suite Expansion**: Added 8 integration and smoke tests in `tests/test_baseline_smoke.py`. The repository test suite now stands at **99/99 passing tests** (100% green), and Phase 1 is officially marked **done** in `docs/tasks/status.md`.

---

## 2. Implementation Details

### 2.1 Complete List of Files Touched
1. `src/ccis_sim/integration/baseline.py`:
   - `BaselineMetrics`: Dataclass summarizing annual kWh, peak kW, peak timestamp/hour, EUI, load factor, and monthly breakdown with `summary()`.
   - `compute_placeholder_demand()`: Vectorized placeholder demand engine incorporating 10% standby baseload, weekday/Saturday occupancy profile, $+4\%/^\circ\text{C}$ daytime cooling sensitivity above $24.0^\circ\text{C}$ per `[D-07]`, and a fixed calibration multiplier ($c_{\text{calib}} = 1.22857563$) locked under `[D-23]`.
   - `simulate_baseline()`: Emits exactly 8,760 `HourlyRecord` instances with `grid_import_kwh = demand_gross_kwh = demand_served_kwh`, zero solar, zero battery, and `active_load_tier = 3`.
   - `compute_baseline_metrics()`: Computes headline metrics and monthly energy totals.
   - `run_baseline_simulation()`: Top-level driver returning records and metrics.
2. `src/ccis_sim/integration/__init__.py`: Re-exports public baseline simulation functions and metrics.
3. `tests/test_baseline_smoke.py`: 8 unit and integration tests covering record counts, determinism, dispatch contracts, harness verification, negative controls, committed headline values, and 2016 climate sensitivity.
4. `docs/decisions/decision-log.md`: Recorded `[D-23]`.
5. `docs/tasks/status.md`: Marked `CORE-005` and `CORE-005.1`–`CORE-005.3` as `done`, and marked Phase 1 overall status as `done`.
6. `docs/reports/CORE-005-gemini-baseline-smoke-test.md`: This task report.

### 2.2 Demand Placeholder Method & Calibration Rationale ([D-23])
Per the prompt's explicit non-goals, detailed academic calendar disaggregation, student scheduling, and psychrometric enthalpy/humidity solvers belong to Phase 2 tracks (`DEM-001` and `DEM-002`) and were deliberately avoided.
The placeholder model uses:
- **Standby baseload:** 10% continuous 24/7 load ($14.78\text{ kW}$) representing IDF switches, telecom headends, and security lighting.
- **Diurnal occupancy:** Diurnal step fractions (08:00–12:00 at 45%, 12:00–13:00 at 30%, 13:00–17:00 at 50%, 17:00–19:00 at 20% on weekdays; 08:00–13:00 at 15% on Saturdays; 0% Sundays).
- **Cooling sensitivity:** During active hours when $T_{\text{amb}} > 24.0^\circ\text{C}$, cooling equipment load ($77.20\text{ kW}$ connected) scales at $+4.0\%/^\circ\text{C}$ above base per `[D-07]`.
- **Calibration target:** A constant multiplier $c_{\text{calib}} = 1.22857563$ is applied to calibrate the 2019 annual consumption to **398,525.00 kWh/yr**, corresponding to an EUI of **159.4100 kWh/m²·yr** on the $2,500\text{ m}^2$ facility, matching the synthetic billing benchmark established in `[D-16]`/`[D-19]`.

### 2.3 Battery Argument Handling in Zero-Battery Baseline
In a grid-only baseline simulation with no physical battery installed, how should the verification harness be invoked?
1. **`battery=None` (Standard Execution):** Omits battery boundary checking and validates pure energy conservation (checking that $\text{energy\_in} = \text{energy\_out}$).
2. **`battery=Battery(capacity_kwh=0.0)` (Zero-Capacity Boundary Verification):** When evaluated against a zero-capacity battery, all baseline record fields (`battery_soc_kwh=0.0`, `battery_charge_kwh=0.0`, `battery_discharge_kwh=0.0`) satisfy $0.0 \le SoC \le 0.0$, $SoC \ge 0.0$, charge $\le 0.0\text{ kW}$, and discharge $\le 0.0\text{ kW}$.
Both modes were tested in `tests/test_baseline_smoke.py::test_baseline_simulation_passes_verification_harness` and pass with 0 violations.

---

## 3. Verification & Test Evidence

### 3.1 Unit Test Coverage (`tests/test_baseline_smoke.py`)
1. `test_baseline_simulation_record_count_and_hours`: Validates 8,760 records, hours 1 to 8760, ISO 8601 timestamps with `+08:00`.
2. `test_baseline_simulation_dispatch_invariants`: Confirms `grid_import == demand_served == demand_gross`, all solar and battery fields identically 0.0, grid available, Tier 3 active.
3. `test_baseline_simulation_determinism`: Proves identical inputs yield identical outputs.
4. `test_baseline_simulation_passes_verification_harness`: Verifies harness passes with `battery=None` and `battery=Battery(capacity_kwh=0.0)`.
5. `test_baseline_negative_control_single_hour_violation_caught`: Proves harness fails on a 1.0 kWh deficit at Hour 500.
6. `test_baseline_negative_control_cumulative_drift_caught`: Proves harness fails on an 8,760-hour $+0.9 \times 10^{-5}\text{ kWh/hr}$ bias.
7. `test_baseline_headline_metrics_committed_values`: Validates headline numbers: 398,525.00 kWh/yr, 159.41 EUI, 124.44 kW peak at Hour 2030, load factor 0.3656.
8. `test_climate_sensitivity_2016_hot_year_versus_2019`: Confirms 2016 El Niño peak (125.55 kW) exceeds 2019 peak (124.44 kW).

### 3.2 Full Test Suite Output (`pytest -v`)
```text
Test session starts (platform: linux, Python 3.14.8, pytest 9.1.1, pytest-sugar 1.1.1)
cachedir: .pytest_cache
hypothesis profile 'default'
rootdir: /home/lukexodus/projects/ccis-heat-load-backup-sim-CORE-005
configfile: pyproject.toml
plugins: instafail-0.5.0, sugar-1.1.1, case-1.5.3, requests-mock-1.12.1, cov-7.1.0, typeguard-4.6.0, anyio-4.15.1, platformdirs-4.13.0, hypothesis-6.169.0, inline-snapshot-0.36.0, time-machine-3.5.1
collecting ... collecting 99 items                                                            

 tests/test_baseline_smoke.py::test_baseline_simulation_record_count_and_hours ✓1% ▏         
 tests/test_baseline_smoke.py::test_baseline_simulation_dispatch_invariants ✓2% ▎         
 tests/test_baseline_smoke.py::test_baseline_simulation_determinism ✓3% ▍         
 tests/test_baseline_smoke.py::test_baseline_simulation_passes_verification_harness ✓4% ▌         
 tests/test_baseline_smoke.py::test_baseline_negative_control_single_hour_violation_caught ✓5% ▋         
 tests/test_baseline_smoke.py::test_baseline_negative_control_cumulative_drift_caught ✓6% ▊         
 tests/test_baseline_smoke.py::test_baseline_headline_metrics_committed_values ✓7% ▉         
 tests/test_baseline_smoke.py::test_climate_sensitivity_2016_hot_year_versus_2019 ✓8% █         
 tests/test_conservation_checker.py::test_golden_scenario_conservation_passes ✓9% █         
 tests/test_conservation_checker.py::test_deliberate_hourly_residual_violation_caught ✓10% █▏        
 tests/test_conservation_checker.py::test_cumulative_drift_catches_small_consistent_bias ✓11% █▎        
 tests/test_conservation_checker.py::test_cumulative_tolerance_computation ✓12% █▍        
 tests/test_conservation_checker.py::test_battery_negative_soc_caught ✓13% █▌        
 tests/test_conservation_checker.py::test_battery_exceeds_capacity_caught ✓14% █▋        
 tests/test_conservation_checker.py::test_battery_min_soc_floor_normal_vs_emergency ✓15% █▊        
 tests/test_conservation_checker.py::test_battery_charge_c_rate_exceeded_caught ✓16% █▉        
 tests/test_conservation_checker.py::test_battery_discharge_c_rate_exceeded_caught ✓17% █▉        
 tests/test_conservation_checker.py::test_simultaneous_charge_and_discharge_caught ✓18% ██        
 tests/test_conservation_checker.py::test_golden_scenario_battery_and_conservation_fully_valid ✓19% ██▏       
 tests/test_conservation_checker.py::test_empty_records_handling ✓20% ██▎       
 tests/test_core_models.py::test_room_inventory_counts ✓          21% ██▍       
 tests/test_core_models.py::test_building_defaults_and_validation ✓22% ██▌       
 tests/test_core_models.py::test_solar_array_scenario_capacities[0.0] ✓23% ██▌       
 tests/test_core_models.py::test_solar_array_scenario_capacities[50.0] ✓25% ███       
 tests/test_core_models.py::test_solar_array_scenario_capacities[100.0] ✓26% ██▋       
 tests/test_core_models.py::test_solar_array_scenario_capacities[200.0] ✓27% ██▊       
 tests/test_core_models.py::test_solar_array_invalid ✓            28% ██▉       
 tests/test_core_models.py::test_battery_scenario_capacities_and_properties[0.0] ✓29% ██▉       
 tests/test_core_models.py::test_battery_scenario_capacities_and_properties[50.0] ✓30% ███       
 tests/test_core_models.py::test_battery_scenario_capacities_and_properties[100.0] ✓31% ███▎      
 tests/test_core_models.py::test_battery_scenario_capacities_and_properties[200.0] ✓32% ███▎      
 tests/test_core_models.py::test_battery_invalid ✓                33% ███▍      
 tests/test_core_models.py::test_battery_configurable_emergency_reserve ✓34% ███▌      
 tests/test_core_models.py::test_outage_event_normal ✓            35% ███▌      
 tests/test_core_models.py::test_outage_event_typhoon ✓           36% ███▋      
 tests/test_core_models.py::test_outage_invalid ✓                 37% ███▊      
 tests/test_core_models.py::test_hourly_record_dict_serialization_roundtrip ✓38% ███▉      
 tests/test_core_models.py::test_hourly_record_energy_conservation_invariant ✓39% ███▉      
 tests/test_core_models.py::test_hourly_record_validation ✓       40% ████▏     
 tests/test_equipment_audit.py::test_audit_fixture_files_exist ✓  41% ████▎     
 tests/test_equipment_audit.py::test_schema_csv_format ✓          42% ████▎     
 tests/test_equipment_audit.py::test_equipment_item_valid_instantiation ✓43% ████▍     
 tests/test_equipment_audit.py::test_equipment_item_cooling_detection ✓44% ████▌     
 tests/test_equipment_audit.py::test_equipment_item_boundary_validation[kwargs0-count must be a positive integer] ✓45% ████▋     
 tests/test_equipment_audit.py::test_equipment_item_boundary_validation[kwargs1-count must be a positive integer] ✓46% ████▋     
 tests/test_equipment_audit.py::test_equipment_item_boundary_validation[kwargs2-rated_kw must be non-negative] ✓47% ████▊     
 tests/test_equipment_audit.py::test_equipment_item_boundary_validation[kwargs3-hours_per_day must be in [0, 24]] ✓48% ████▉     
 tests/test_equipment_audit.py::test_equipment_item_boundary_validation[kwargs4-hours_per_day must be in [0, 24]] ✓49% ████▉     
 tests/test_equipment_audit.py::test_equipment_item_boundary_validation[kwargs5-tier must be 1, 2, or 3] ✓51% █████▏    
 tests/test_equipment_audit.py::test_equipment_item_boundary_validation[kwargs6-tier must be 1, 2, or 3] ✓52% █████▎    
 tests/test_equipment_audit.py::test_equipment_item_boundary_validation[kwargs7-duty_cycle must be in [0.0, 1.0]] ✓53% █████▍    
 tests/test_equipment_audit.py::test_equipment_item_boundary_validation[kwargs8-duty_cycle must be in [0.0, 1.0]] ✓54% █████▍    
 tests/test_equipment_audit.py::test_load_audit_from_csv ✓        55% █████▌    
 tests/test_equipment_audit.py::test_all_18_rooms_archetype_covered ✓56% █████▋    
 tests/test_equipment_audit.py::test_tier_distribution_and_shedding_alignment ✓57% █████▋    
 tests/test_equipment_audit.py::test_building_dataclass_compatibility ✓58% █████▊    
 tests/test_equipment_audit.py::test_load_nonexistent_file_raises ✓59% █████▉    
 tests/test_equipment_audit.py::test_exact_connected_capacity_reconciliation ✓60% █████▉    
 tests/test_mock_bills.py::test_generate_12_monthly_bills ✓       61% ██████▏   
 tests/test_mock_bills.py::test_mock_bill_internal_energy_conservation ✓62% ██████▎   
 tests/test_mock_bills.py::test_annual_eui_benchmark_conformance ✓63% ██████▍   
 tests/test_mock_bills.py::test_committed_fixture_eui_plausibility ✓64% ██████▍   
 tests/test_mock_bills.py::test_hot_season_cooling_elevation ✓    65% ██████▌   
 tests/test_mock_bills.py::test_academic_break_reduction ✓        66% ██████▋   
 tests/test_mock_bills.py::test_csv_save_and_load_roundtrip ✓     67% ██████▋   
 tests/test_mock_bills.py::test_generator_seed_reproducibility ✓  68% ██████▊   
 tests/test_smoke.py::test_package_version ✓                      69% ██████▉   
 tests/test_smoke.py::test_submodules_importable[ccis_sim.core] ✓ 70% ███████   
 tests/test_smoke.py::test_submodules_importable[ccis_sim.demand] ✓71% ███████▏  
 tests/test_smoke.py::test_submodules_importable[ccis_sim.solar] ✓72% ███████▎  
 tests/test_smoke.py::test_submodules_importable[ccis_sim.battery] ✓73% ███████▍  
 tests/test_smoke.py::test_submodules_importable[ccis_sim.outage] ✓74% ███████▍  
 tests/test_smoke.py::test_submodules_importable[ccis_sim.integration] ✓75% ███████▌  
 tests/test_smoke.py::test_submodules_importable[ccis_sim.decision] ✓76% ███████▋  
 tests/test_smoke.py::test_numpy_environment_sanity ✓             77% ███████▋  
 tests/test_smoke.py::test_scipy_environment_sanity ✓             78% ███████▊  
 tests/test_weather_ingest.py::test_client_defaults ✓             79% ███████▉  
 tests/test_weather_ingest.py::test_client_url_construction ✓     80% ████████  
 tests/test_weather_ingest.py::test_client_raw_io_roundtrip ✓     81% ████████▏ 
 tests/test_weather_ingest.py::test_client_network_failure ✓      82% ████████▎ 
 tests/test_weather_ingest.py::test_parse_hourly_json_lst ✓       83% ████████▍ 
 tests/test_weather_ingest.py::test_parse_hourly_json_utc ✓       84% ████████▍ 
 tests/test_weather_ingest.py::test_parse_daily_json ✓            85% ████████▌ 
 tests/test_weather_ingest.py::test_parse_malformed_json ✓        86% ████████▋ 
 tests/test_weather_ingest.py::test_sanitizer_filter_sentinels ✓  87% ████████▊ 
 tests/test_weather_ingest.py::test_sanitizer_interpolate_missing ✓88% ████████▊ 
 tests/test_weather_ingest.py::test_sanitizer_timezone_alignment_and_midnight_boundary ✓89% ████████▉ 
 tests/test_weather_ingest.py::test_sanitizer_psychrometric_validation ✓90% █████████ 
 tests/test_weather_ingest.py::test_sanitizer_standardize_annual_hourly ✓91% █████████▏
 tests/test_weather_ingest.py::test_daily_disaggregation_energy_conservation ✓92% █████████▎
 tests/test_weather_ingest.py::test_daily_disaggregation_solar_geometry_night_zero ✓93% █████████▍
 tests/test_weather_ingest.py::test_daily_disaggregation_temperature_profile ✓94% █████████▌
 tests/test_weather_ingest.py::test_daily_disaggregation_relative_humidity_coupling ✓95% █████████▌
 tests/test_weather_ingest.py::test_daily_disaggregate_dataframe ✓96% █████████▋
 tests/test_weather_ingest.py::test_committed_fixtures_structure[2016] ✓97% █████████▊
 tests/test_weather_ingest.py::test_committed_fixtures_structure[2019] ✓98% █████████▊
 tests/test_weather_ingest.py::test_committed_fixtures_climate_comparison ✓99% █████████▉
 tests/test_weather_ingest.py::test_raw_files_exist ✓            100% ██████████

Results (7.75s):
      99 passed
```

---

## 4. Methodological Decisions ([D-23])

Recorded in `docs/decisions/decision-log.md`:
- **[D-23] Baseline placeholder demand method, calibration target, and Phase 1 exit gate metrics locked.**  
  Defines the 10% standby baseload, diurnal weekday/Saturday occupancy schedule, $+4\%/^\circ\text{C}$ cooling adjustment above $24.0^\circ\text{C}$, calibration factor $c_{\text{calib}} = 1.22857563$ producing $398,525.00\text{ kWh/yr}$ and $159.41\text{ kWh/m}^2\cdot\text{yr}$ on 2019 baseline weather, 124.44 kW peak, and un-tuned 2016 sensitivity peak of 125.55 kW.

---

## 5. Flagged for APC / Operator Attention (Harness Enhancements Queue)

As instructed by the APC AI in `CORE-005-PROMPT.md`, the verification harness was reused as-is without modification. The following potential enhancements were identified during audit and should be addressed in a subsequent `CORE-004.5` fixup prior to Phase 2 `BAT-001`:
1. **Hour-to-Hour SoC Continuity Invariant:** The current harness checks boundary limits ($0 \le SoC \le C_{\text{bat}}$) and C-rate bounds, but does not enforce that $SoC_t$ strictly equals $SoC_{t-1} + \eta_{\text{chg}} P_{\text{chg},t} - \frac{P_{\text{dis},t}}{\eta_{\text{dis}}}$. A sub-model that teleports energy or omits the 92% round-trip efficiency ([D-09]) would pass the current harness.
2. **NaN and Inf Guarding:** Comparisons like `r.battery_soc_kwh < -tol` evaluate to `False` for `NaN`, which could allow unhandled floating-point NaNs to evade boundary failure detection.
3. **Sub-Flow Balance Decompositions:** Add explicit checks verifying sub-component flow conservation:
   - $\text{solar\_generation} = \text{solar\_to\_demand} + \text{solar\_to\_battery} + \text{solar\_curtailed}$
   - $\text{demand\_gross} = \text{demand\_served} + \text{unserved\_load}$
4. **Signed Residual Property on `HourlyRecord`:** Reconcile cumulative drift computation by adding a canonical `signed_residual_kwh` property on `HourlyRecord` so `verification.py` does not need to recompute `e_in - e_out`.
5. **Reconciliation Note for [D-09] and [D-21]:** Clarify in the decision log that [D-09]'s 10% floor is non-discretionary under normal grid-connected operation, while [D-21]'s emergency drawdown override is strictly restricted to active extended blackouts.

---

## 6. Patch File Reference

The standalone unit-of-work patch file is generated at:
`patch/CORE-005-gemini-baseline-smoke-test.patch`

---

## 7. Git Diff

```diff
diff --git a/docs/decisions/decision-log.md b/docs/decisions/decision-log.md
index 9c8c765..0c31331 100644
--- a/docs/decisions/decision-log.md
+++ b/docs/decisions/decision-log.md
@@ -142,4 +142,23 @@ This file exists so that across API-credit-limited handoffs between APC AI insta
 - **Reasoning:** Zero-mean IEEE 754 floating-point rounding jitter across $N$ independent steps behaves as a 1D random walk with standard deviation $\sigma_N = \sqrt{N} \epsilon$. Scaling cumulative tolerance by $\sqrt{N}$ accommodates harmless numerical rounding while rigorously tripping on any systematic numerical leakage or bias (e.g. an uncorrected bias of $0.9 \times 10^{-5}\text{ kWh/hr}$ accumulates to $0.07884\text{ kWh}$, which is ~84× the allowable threshold, triggering an immediate failure).
 - **Affects:** `CORE-004`, `CORE-005`, `DEM-001`, `DEM-002`, `BAT-001`, `BAT-002`, `SOL-001`, `OUT-001`, `INT-001`, `INT-002`, `INT-003`.
 
+**[D-23]** Baseline placeholder demand method, calibration target, and Phase 1 exit gate metrics locked.  
+- **Date / Session:** 2026-10-20  
+- **Decision:**
+  1. For the Phase 1 exit-gate baseline smoke test (`CORE-005`), implement a lightweight, isolated placeholder demand model:
+     - Baseload: 10% continuous 24/7 standby power (~14.78 kW) for IDF switches, telecom headend, and life safety egress lighting.
+     - Scheduled Occupancy: Documented hourly diurnal step profile (weekdays: 08:00–12:00 at 45%, 12:00–13:00 at 30%, 13:00–17:00 at 50%, 17:00–19:00 at 20%; Saturdays: 08:00–13:00 at 15%; Sundays: 0% occupancy).
+     - Cooling Response: Piecewise-linear temperature adjustment adding $+4.0\%/^\circ\text{C}$ to daytime active cooling equipment load when ambient temperature exceeds $T_{\text{base}} = 24.0^\circ\text{C}$ per [D-07].
+  2. The placeholder demand is scaled by a single fixed calibration factor ($c_{\text{calib}} = 1.22857563$) so that the 2019 baseline annual electricity consumption lands on **398,525.00 kWh/yr**, yielding an annual Energy Use Intensity (EUI) of **159.4100 kWh/m²·yr**, strictly matching the target benchmark established in [D-16]/[D-19] and the 150.0–300.0 kWh/m²·yr regional benchmark band.
+  3. Locked baseline headline figures for the 2019 baseline weather fixture (`Building.gross_floor_area_m2 = 2500.0`):
+     - Annual Consumption: 398,525.00 kWh/yr
+     - Annual EUI: 159.41 kWh/m²·yr
+     - Peak Electrical Demand: 124.44 kW (occurring at Hour 2030, 2019-03-26T13:00:00+08:00)
+     - Annual Load Factor: 0.3656 (36.56%)
+  4. Climate Sensitivity (2016 anomalous hot year, un-tuned): Peak electrical demand reaches **125.55 kW** (+1.11 kW, +0.89% increase driven by peak El Niño heat at 2016-04-19T13:00:00+08:00), while annual consumption totals 398,251.21 kWh (EUI: 159.30 kWh/m²·yr; -273.79 kWh, -0.07% delta due to 2016 calendar having 260 weekdays vs 261 in 2019).
+  5. The placeholder model is explicitly isolated in `src/ccis_sim/integration/baseline.py` and will be formally superseded by the bottom-up academic diversity schedules in `DEM-001` and transient psychrometric cooling response in `DEM-002`.
+- **Reasoning:** Demonstrates end-to-end continuous 8,760-hour execution and verification harness closure for Phase 1 without pre-empting the detailed physics or empirical regressions reserved for Phase 2 demand sub-models.
+- **Affects:** `CORE-005`, `DEM-001`, `DEM-002`, `INT-001`.
+
+
 
diff --git a/docs/tasks/status.md b/docs/tasks/status.md
index 2178e4f..e0bb2b1 100644
--- a/docs/tasks/status.md
+++ b/docs/tasks/status.md
@@ -34,7 +34,7 @@ Status: **done**
 
 ## Phase 1 — Core Infrastructure & Data Pipelines
 
-Status: **open**
+Status: **done**
 
 | ID           | Task                                                                             | Status | Notes / Report                                                                                                    |
 | :----------- | :------------------------------------------------------------------------------- | :----- | :---------------------------------------------------------------------------------------------------------------- |
@@ -61,10 +61,11 @@ Status: **open**
 | CORE-004.1   | Implement strict energy conservation checker ($\le 10^{-5}\text{ kWh}$)          | `done` | Hourly residual + cumulative drift tolerance [D-21]                                                               |
 | CORE-004.2   | Implement battery boundary validator ($0 \le \text{SoC} \le \text{Cap}$, C-rate) | `done` | Physical bounds, min SoC floor, C-rate limits, mutual exclusivity                                                 |
 | CORE-004.3   | Build shared golden fixture runner for sub-model validation                      | `done` | 48h reference fixture `create_golden_scenario()` + self-test                                                      |
-| **CORE-005** | **Baseline Engine Smoke Test (Phase 1 Exit Gate)**                               | `open` | Exit gate                                                                                                         |
-| CORE-005.1   | Implement grid-only, zero-solar, zero-battery simulation                         | `open` | Baseline engine                                                                                                   |
-| CORE-005.2   | Run 8,760-hour baseline through energy-balance test harness                      | `open` | Zero-leak test                                                                                                    |
-| CORE-005.3   | Generate baseline summary metrics (annual kWh, peak kW, base EUI)                | `open` | Baseline KPIs                                                                                                     |
+| **CORE-005** | **Baseline Engine Smoke Test (Phase 1 Exit Gate)**                               | `done` | [CORE-005-gemini-baseline-smoke-test.md](../reports/CORE-005-gemini-baseline-smoke-test.md) |
+| CORE-005.1   | Implement grid-only, zero-solar, zero-battery simulation                         | `done` | 8,760h continuous simulation `simulate_baseline` [D-23]                                                           |
+| CORE-005.2   | Run 8,760-hour baseline through energy-balance test harness                      | `done` | Zero residual, zero drift, negative control verified                                                              |
+| CORE-005.3   | Generate baseline summary metrics (annual kWh, peak kW, base EUI)                | `done` | 398,525 kWh/yr, 159.41 EUI, 124.44 kW peak, 2016 sensitivity                                                      |
+
 |              |                                                                                  |        |                                                                                                                   |
 
 ---
diff --git a/src/ccis_sim/integration/__init__.py b/src/ccis_sim/integration/__init__.py
index 9143bf2..863abab 100644
--- a/src/ccis_sim/integration/__init__.py
+++ b/src/ccis_sim/integration/__init__.py
@@ -1 +1,19 @@
 """Integrated time-step simulation engine, CLI driver, and Monte Carlo scenario runners."""
+
+from ccis_sim.integration.baseline import (
+    CALIBRATION_FACTOR_2019,
+    BaselineMetrics,
+    compute_baseline_metrics,
+    compute_placeholder_demand,
+    run_baseline_simulation,
+    simulate_baseline,
+)
+
+__all__ = [
+    "CALIBRATION_FACTOR_2019",
+    "BaselineMetrics",
+    "compute_baseline_metrics",
+    "compute_placeholder_demand",
+    "run_baseline_simulation",
+    "simulate_baseline",
+]
```
