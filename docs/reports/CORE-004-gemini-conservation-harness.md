# Task Report: CORE-004 — Shared Test Harness & Energy Balance Invariant Checker

**Task ID:** CORE-004 (subtasks CORE-004.1 – CORE-004.3)  
**Agent:** Gemini (local coding agent)  
**Date:** 2026-10-20  
**Status:** Completed  
**Decisions Locked:** [D-21]  
**Patch File:** `patch/CORE-004-gemini-conservation-harness.patch`  

---

## 1. Executive Summary

This unit of work completes task `CORE-004` ("Shared Test Harness & Energy Balance Invariant Checker"), delivering the shared verification and validation infrastructure that acts as the primary quality gate for all simulation engines and sub-model tracks across the project (`CORE-005` baseline, `DEM-001/002`, `SOL-001/002`, `BAT-001/002`, `OUT-001/002`, and Phase 3 V&V in `INT-003`).

Specifically, it delivers:
1. **Time-series energy balance invariant checker (`CORE-004.1`)**: Evaluates a sequence of `HourlyRecord` instances, reusing `HourlyRecord.energy_balance_residual_kwh` and `HourlyRecord.is_energy_conserved(tolerance=1e-5)` to ensure a single, consistent definition of physical conservation across the codebase. Captures detailed diagnostics (hour, timestamp, flow breakdown, residual vs tolerance) for any failing hour. Evaluates cumulative energy drift across the time series against a statistically scaled tolerance bound locked under decision `[D-21]`.
2. **Battery boundary validator (`CORE-004.2`)**: Enforces hard physical boundaries ($0 \le SoC(t) \le C_{\text{bat}}$), non-discretionary minimum protection floor ($SoC(t) \ge 0.10 \times C_{\text{bat}}$ per `[D-09]`), continuous C-rate charging ($0.5\text{C}$) and discharging ($1.0\text{C}$) power limits, and mutual exclusivity preventing simultaneous battery charging and discharging in the same hour.
3. **Shared golden reference fixture & runner (`CORE-004.3`)**: Implements `create_golden_scenario()`, constructing a hand-calculated 48-hour synthetic scenario exercising all operational microgrid modes (solar generation, battery charging, solar curtailment at 100% SoC, exact zero net-load balance, evening battery discharge, 8-hour grid blackout with Tier 2 load shedding, and post-outage grid recovery) with exact $0.000000\text{ kWh}$ residuals. Self-tests both checkers against this golden fixture and documents import and usage patterns in `tests/fixtures/README.md`.

All 12 new unit tests pass cleanly, bringing the total repository test suite to 91/91 passing tests.

---

## 2. Implementation Details

### 2.1 File Structure & Public Exports
- **`src/ccis_sim/core/verification.py`**:
  - `ViolationType(str, Enum)`: Categorizes violations (`HOURLY_ENERGY_BALANCE`, `CUMULATIVE_ENERGY_BALANCE`, `NEGATIVE_SOC`, `EXCEEDS_CAPACITY`, `MIN_SOC_VIOLATION`, `CHARGE_RATE_EXCEEDED`, `DISCHARGE_RATE_EXCEEDED`, `SIMULTANEOUS_CHARGE_DISCHARGE`).
  - `ConservationViolation` & `BatteryBoundaryViolation`: Immutable frozen dataclasses storing hour number, timestamp, actual value, threshold limit, and diagnostic summary.
  - `VerificationReport`: Dataclass summarizing simulation run validity, violation counts, maximum residual, net cumulative drift, and human-readable `summary()`.
  - `compute_cumulative_tolerance(n_records, tolerance_hour=1e-5)`: Computes statistical cumulative tolerance per `[D-21]`.
  - `check_energy_conservation(records, tolerance=1e-5, cumulative_tolerance=None)`: Verifies hourly and cumulative conservation.
  - `validate_battery_boundaries(records, battery, allow_emergency_drawdown=False, delta_t_hours=1.0)`: Validates physical battery operating boundaries.
  - `run_verification_harness(records, battery=None, ...)`: High-level verification runner returning `VerificationReport`.
  - `assert_simulation_valid(records, battery=None, ...)`: Pytest assertion helper raising `AssertionError` with detailed report diagnostics upon any failure.
  - `create_golden_scenario(battery=None)`: Shared 48-hour golden reference fixture generator.
- **`src/ccis_sim/core/__init__.py`**: Re-exports all public verification functions and types.
- **`tests/fixtures/README.md`**: Technical documentation guiding downstream sub-model authors on how to import and use `create_golden_scenario` and `assert_simulation_valid`.
- **`tests/test_conservation_checker.py`**: 12 unit tests exercising all failure modes, boundary conditions, and golden scenarios.

### 2.2 Methodological Decision: Cumulative Drift Tolerance (`[D-21]`)
In floating-point simulation of continuous time-series (e.g. 8,760 hours in an annual simulation), numerical rounding jitter under IEEE 754 arithmetic behaves as a 1D zero-mean random walk with variance $\sigma_N^2 = N \epsilon^2$, yielding expected drift scaling as $\mathcal{O}(\sqrt{N} \epsilon)$.

Conversely, an uncorrected systematic leakage or biased calculation in a sub-model accumulates linearly as $\mathcal{O}(N \epsilon)$.
Under `[D-21]`:
$$\text{tolerance}_{\text{cum}} = \max\left(\epsilon_{\text{hour}},\; \sqrt{N} \times \epsilon_{\text{hour}}\right)$$
For $N = 8,760$ hours with baseline tolerance $\epsilon_{\text{hour}} = 10^{-5}\text{ kWh}$:
$$\text{tolerance}_{\text{cum}} = \sqrt{8760} \times 10^{-5} \approx 9.359 \times 10^{-4}\text{ kWh} \approx 0.001\text{ kWh}$$

If an engine exhibits a tiny systematic bias of $0.9 \times 10^{-5}\text{ kWh/hr}$ (passing every single individual-hour check because $0.9 \times 10^{-5} \le 1.0 \times 10^{-5}$), the accumulated error across 8,760 hours equals:
$$\Delta E_{\text{net}} = 8760 \times 0.9 \times 10^{-5} = 0.07884\text{ kWh}$$
Because $0.07884\text{ kWh} \gg 9.359 \times 10^{-4}\text{ kWh}$, the cumulative drift check fails and trips `CUMULATIVE_ENERGY_BALANCE`, preventing hidden energy leaks from corrupting downstream resilience and economic metrics.

### 2.3 Battery Boundary & Emergency Drawdown Rules
Per `[D-09]`, the 10% minimum state-of-charge ($SoC_{\min} = 0.10 \times C_{\text{bat}}$) is a non-discretionary cell protection floor designed to prevent copper shunting and accelerated degradation in LFP cells.
The boundary validator treats dropping below `min_soc_kwh` as an illegal violation during normal grid-connected operation (`grid_available == True` or `active_load_tier == 3`).
When simulating extreme extended emergency blackouts where operator protocols allow emergency deep discharge, setting `allow_emergency_drawdown=True` permits SoC to drop below $SoC_{\min}$ (strictly bounded by $0.0\text{ kWh}$) only when `grid_available is False` and `active_load_tier in (1, 2)`.

---

## 3. Verification & Test Evidence

### 3.1 Unit Test Coverage (`tests/test_conservation_checker.py`)
12 test cases were created and executed:
1. `test_golden_scenario_conservation_passes`: Asserts that the 48-hour golden scenario has zero residuals and satisfies all invariants.
2. `test_deliberate_hourly_residual_violation_caught`: Deliberately injects a 0.5 kWh mismatch in Hour 12; verifies that the checker detects Hour 12, records the exact residual, and fails the harness.
3. `test_cumulative_drift_catches_small_consistent_bias`: Simulates 8,760 hours with a persistent $0.9 \times 10^{-5}\text{ kWh/hr}$ bias; proves that every individual hour passes, but the cumulative check triggers `CUMULATIVE_ENERGY_BALANCE` failure.
4. `test_cumulative_tolerance_computation`: Validates mathematical scaling across $N \le 1$ and $N = 8,760$.
5. `test_battery_negative_soc_caught`: Injects negative SoC ($-0.5\text{ kWh}$); asserts detection of `NEGATIVE_SOC`.
6. `test_battery_exceeds_capacity_caught`: Injects $105.0\text{ kWh}$ SoC on a $100.0\text{ kWh}$ battery; asserts detection of `EXCEEDS_CAPACITY`.
7. `test_battery_min_soc_floor_normal_vs_emergency`: Validates floor protection under grid-available conditions, outage without emergency drawdown, and permitted drawdown during outage.
8. `test_battery_charge_c_rate_exceeded_caught`: Injects $55.0\text{ kW}$ charge on a $50.0\text{ kW}$ limit ($0.5\text{C}$); asserts `CHARGE_RATE_EXCEEDED`.
9. `test_battery_discharge_c_rate_exceeded_caught`: Injects $110.0\text{ kW}$ discharge on a $100.0\text{ kW}$ limit ($1.0\text{C}$); asserts `DISCHARGE_RATE_EXCEEDED`.
10. `test_simultaneous_charge_and_discharge_caught`: Injects simultaneous charging and discharging; asserts `SIMULTANEOUS_CHARGE_DISCHARGE`.
11. `test_golden_scenario_battery_and_conservation_fully_valid`: End-to-end integration test validating all battery flows and energy balances across the 48-hour scenario.
12. `test_empty_records_handling`: Verifies clean graceful handling of empty inputs.

### 3.2 Full Test Suite Output (`pytest -v`)
```text
Test session starts (platform: linux, Python 3.14.8, pytest 9.1.0, pytest-sugar 1.1.1)
cachedir: .pytest_cache
hypothesis profile 'default'
rootdir: /home/lukexodus/projects/ccis-heat-load-backup-sim
configfile: pyproject.toml
testpaths: tests
plugins: instafail-0.5.0, sugar-1.1.1, case-1.5.3, requests-mock-1.12.1, cov-7.1.0, inline-snapshot-0.32.6, typeguard-4.6.0, time-machine-3.5.0, anyio-4.15.1, hypothesis-6.167.1, platformdirs-4.13.0
collecting ... collecting 51 items                                                            

 tests/test_conservation_checker.py::test_golden_scenario_conservation_passes ✓1% ▏         
 tests/test_conservation_checker.py::test_deliberate_hourly_residual_violation_caught ✓2% ▎         
 tests/test_conservation_checker.py::test_cumulative_drift_catches_small_consistent_bias ✓3% ▍         
 tests/test_conservation_checker.py::test_cumulative_tolerance_computation ✓4% ▌         
 tests/test_conservation_checker.py::test_battery_negative_soc_caught ✓5% ▋         
 tests/test_conservation_checker.py::test_battery_exceeds_capacity_caught ✓7% ▊         
 tests/test_conservation_checker.py::test_battery_min_soc_floor_normal_vs_emergency ✓8% ▉         
 tests/test_conservation_checker.py::test_battery_charge_c_rate_exceeded_caught ✓9% █         
 tests/test_conservation_checker.py::test_battery_discharge_c_rate_exceeded_caught ✓10% █         
 tests/test_conservation_checker.py::test_simultaneous_charge_and_discharge_caught ✓11% █▏        
 tests/test_conservation_checker.py::test_golden_scenario_battery_and_conservation_fully_valid ✓12% █▎        
 tests/test_conservation_checker.py::test_empty_records_handling ✓13% █▍        
 tests/test_core_models.py::test_room_inventory_counts ✓          14% █▌        
 tests/test_core_models.py::test_building_defaults_and_validation ✓15% █▋        
 tests/test_core_models.py::test_solar_array_scenario_capacities[0.0] ✓16% █▊        
 tests/test_core_models.py::test_solar_array_scenario_capacities[50.0] ✓19% █▉        
 tests/test_core_models.py::test_solar_array_scenario_capacities[100.0] ✓20% ██        
 tests/test_core_models.py::test_solar_array_scenario_capacities[200.0] ✓21% ██▏       
 tests/test_core_models.py::test_solar_array_invalid ✓            22% ██▎       
 tests/test_core_models.py::test_battery_scenario_capacities_and_properties[0.0] ✓23% ██▍       
 tests/test_core_models.py::test_battery_scenario_capacities_and_properties[50.0] ✓24% ██▌       
 tests/test_core_models.py::test_battery_scenario_capacities_and_properties[100.0] ✓25% ██▌       
 tests/test_core_models.py::test_battery_scenario_capacities_and_properties[200.0] ✓26% ██▋       
 tests/test_core_models.py::test_battery_invalid ✓                27% ██▊       
 tests/test_core_models.py::test_battery_configurable_emergency_reserve ✓29% ██▉       
 tests/test_core_models.py::test_outage_event_normal ✓            30% ███       
 tests/test_core_models.py::test_outage_event_typhoon ✓           31% ███▏      
 tests/test_core_models.py::test_outage_invalid ✓                 32% ███▎      
 tests/test_core_models.py::test_hourly_record_dict_serialization_roundtrip ✓33% ███▍      
 tests/test_core_models.py::test_hourly_record_energy_conservation_invariant ✓34% ███▌      
 tests/test_core_models.py::test_hourly_record_validation ✓       35% ███▌      
 tests/test_equipment_audit.py::test_audit_fixture_files_exist ✓  36% ███▋      
 tests/test_equipment_audit.py::test_schema_csv_format ✓          37% ███▊      
 tests/test_equipment_audit.py::test_equipment_item_valid_instantiation ✓38% ███▉      
 tests/test_equipment_audit.py::test_equipment_item_cooling_detection ✓40% ███▉      
 tests/test_equipment_audit.py::test_equipment_item_boundary_validation[kwargs0-count must be a positive integer] ✓41% ████▏     
 tests/test_equipment_audit.py::test_equipment_item_boundary_validation[kwargs1-count must be a positive integer] ✓42% ████▎     
 tests/test_equipment_audit.py::test_equipment_item_boundary_validation[kwargs2-rated_kw must be non-negative] ✓43% ████▍     
 tests/test_equipment_audit.py::test_equipment_item_boundary_validation[kwargs3-hours_per_day must be in [0, 24]] ✓44% ████▌     
 tests/test_equipment_audit.py::test_equipment_item_boundary_validation[kwargs4-hours_per_day must be in [0, 24]] ✓45% ████▌     
 tests/test_equipment_audit.py::test_equipment_item_boundary_validation[kwargs5-tier must be 1, 2, or 3] ✓46% ████▋     
 tests/test_equipment_audit.py::test_equipment_item_boundary_validation[kwargs6-tier must be 1, 2, or 3] ✓47% ████▊     
 tests/test_equipment_audit.py::test_equipment_item_boundary_validation[kwargs7-duty_cycle must be in [0.0, 1.0]] ✓48% ████▉     
 tests/test_equipment_audit.py::test_equipment_item_boundary_validation[kwargs8-duty_cycle must be in [0.0, 1.0]] ✓49% ████▉     
 tests/test_equipment_audit.py::test_load_audit_from_csv ✓        51% █████▏    
 tests/test_equipment_audit.py::test_all_18_rooms_archetype_covered ✓52% █████▎    
 tests/test_equipment_audit.py::test_tier_distribution_and_shedding_alignment ✓53% █████▍    
 tests/test_equipment_audit.py::test_building_dataclass_compatibility ✓54% █████▍    
 tests/test_equipment_audit.py::test_load_nonexistent_file_raises ✓55% █████▌    
 tests/test_equipment_audit.py::test_exact_connected_capacity_reconciliation ✓56% █████▋    
 tests/test_mock_bills.py::test_generate_12_monthly_bills ✓       57% █████▊    
 tests/test_mock_bills.py::test_mock_bill_internal_energy_conservation ✓58% █████▉    
 tests/test_mock_bills.py::test_annual_eui_benchmark_conformance ✓59% █████▉    
 tests/test_mock_bills.py::test_committed_fixture_eui_plausibility ✓60% ██████▏   
 tests/test_mock_bills.py::test_hot_season_cooling_elevation ✓    62% ██████▎   
 tests/test_mock_bills.py::test_academic_break_reduction ✓        63% ██████▍   
 tests/test_mock_bills.py::test_csv_save_and_load_roundtrip ✓     64% ██████▍   
 tests/test_mock_bills.py::test_generator_seed_reproducibility ✓  65% ██████▌   
 tests/test_smoke.py::test_package_version ✓                      66% ██████▋   
 tests/test_smoke.py::test_submodules_importable[ccis_sim.core] ✓ 67% ██████▊   
 tests/test_smoke.py::test_submodules_importable[ccis_sim.demand] ✓68% ██████▊   
 tests/test_smoke.py::test_submodules_importable[ccis_sim.solar] ✓69% ██████▉   
 tests/test_smoke.py::test_submodules_importable[ccis_sim.battery] ✓70% ███████   
 tests/test_smoke.py::test_submodules_importable[ccis_sim.outage] ✓71% ███████▎  
 tests/test_smoke.py::test_submodules_importable[ccis_sim.integration] ✓73% ███████▍  
 tests/test_smoke.py::test_submodules_importable[ccis_sim.decision] ✓74% ███████▍  
 tests/test_smoke.py::test_numpy_environment_sanity ✓             75% ███████▌  
 tests/test_smoke.py::test_scipy_environment_sanity ✓             76% ███████▋  
 tests/test_weather_ingest.py::test_client_defaults ✓             77% ███████▊  
 tests/test_weather_ingest.py::test_client_url_construction ✓     78% ███████▊  
 tests/test_weather_ingest.py::test_client_raw_io_roundtrip ✓     79% ███████▉  
 tests/test_weather_ingest.py::test_client_network_failure ✓      80% ████████  
 tests/test_weather_ingest.py::test_parse_hourly_json_lst ✓       81% ████████▎ 
 tests/test_weather_ingest.py::test_parse_hourly_json_utc ✓       82% ████████▎ 
 tests/test_weather_ingest.py::test_parse_daily_json ✓            84% ████████▍ 
 tests/test_weather_ingest.py::test_parse_malformed_json ✓        85% ████████▌ 
 tests/test_weather_ingest.py::test_sanitizer_filter_sentinels ✓  86% ████████▋ 
 tests/test_weather_ingest.py::test_sanitizer_interpolate_missing ✓87% ████████▊ 
 tests/test_weather_ingest.py::test_sanitizer_timezone_alignment_and_midnight_boundary ✓88% ████████▊ 
 tests/test_weather_ingest.py::test_sanitizer_psychrometric_validation ✓89% ████████▉ 
 tests/test_weather_ingest.py::test_sanitizer_standardize_annual_hourly ✓90% █████████ 
 tests/test_weather_ingest.py::test_daily_disaggregation_energy_conservation ✓91% █████████▎
 tests/test_weather_ingest.py::test_daily_disaggregation_solar_geometry_night_zero ✓92% █████████▎
 tests/test_weather_ingest.py::test_daily_disaggregation_temperature_profile ✓93% █████████▍
 tests/test_weather_ingest.py::test_daily_disaggregation_relative_humidity_coupling ✓95% █████████▌
 tests/test_weather_ingest.py::test_daily_disaggregate_dataframe ✓96% █████████▋
 tests/test_weather_ingest.py::test_committed_fixtures_structure[2016] ✓97% █████████▋
 tests/test_weather_ingest.py::test_committed_fixtures_structure[2019] ✓98% █████████▊
 tests/test_weather_ingest.py::test_committed_fixtures_climate_comparison ✓99% █████████▉
 tests/test_weather_ingest.py::test_raw_files_exist ✓            100% ██████████

Results (12.02s):
      91 passed
```

---

## 4. Methodological Decisions ([D-21])

The methodological choices governing cumulative drift tolerance and battery boundary invariants were formally recorded in `docs/decisions/decision-log.md` under reserved identifier `[D-21]`:
- **Hourly residual tolerance:** $\epsilon_{\text{hour}} = 10^{-5}\text{ kWh}$.
- **Cumulative net drift tolerance:** $\text{tolerance}_{\text{cum}} = \max\left(\epsilon_{\text{hour}},\; \sqrt{N} \times \epsilon_{\text{hour}}\right)$, representing the theoretical diffusion limit of zero-mean floating-point rounding error across $N$ hourly calculations.
- **Battery operational boundaries:** Validates $0 \le SoC(t) \le C_{\text{bat}}$, non-discretionary 10% minimum SoC protection floor (permitting emergency deep discharge down to 0 exclusively when `allow_emergency_drawdown=True` during active blackouts), C-rate limits ($0.5\text{C}$ charge, $1.0\text{C}$ discharge), and strict mutual exclusivity of charge and discharge.

---

## 5. Patch File Reference

The standalone patch file representing this complete unit of work is generated and stored in:
`patch/CORE-004-gemini-conservation-harness.patch`

---

## 6. Git Diff

```diff
diff --git a/docs/decisions/decision-log.md b/docs/decisions/decision-log.md
index cd882ff..e445163 100644
--- a/docs/decisions/decision-log.md
+++ b/docs/decisions/decision-log.md
@@ -123,4 +123,24 @@
 - **Reasoning:** Confirms empirical data availability directly from NASA POWER MERRA-2/CERES hourly product for Batac, avoiding synthetic disaggregation approximations for canonical simulation baselines. Preserves strict energy and state vector contracts across 8,760 annual hours [D-05].
 - **Affects:** `CORE-002`, `CORE-005`, `DEM-002`, `SOL-001`, `INT-001`.
 
+**[D-21]** Cumulative energy conservation tolerance scaling and battery boundary verification methodology locked.  
+- **Date / Session:** 2026-10-20  
+- **Decision:**
+  1. The shared test harness checks per-hour energy conservation against $\epsilon_{\text{hour}} = 10^{-5}\text{ kWh}$ using the canonical formula:
+     $$\text{residual}_t = |(\text{solar}_t + \text{grid}_t + \text{bat\_dis}_t) - (\text{demand\_served}_t + \text{bat\_chg}_t + \text{solar\_curt}_t)|$$
+     reusing `HourlyRecord.energy_balance_residual_kwh` and `HourlyRecord.is_energy_conserved()`.
+  2. Cumulative time-series conservation tolerance across $N$ hours scales statistically as:
+     $$\text{tolerance}_{\text{cum}} = \max\left(\epsilon_{\text{hour}},\; \sqrt{N} \times \epsilon_{\text{hour}}\right)$$
+     For an 8,760-hour annual simulation run, $\text{tolerance}_{\text{cum}} = \sqrt{8760} \times 10^{-5} \approx 9.359 \times 10^{-4}\text{ kWh}$ (~$0.001\text{ kWh}$). Cumulative conservation evaluates the absolute net drift:
+     $$\Delta E_{\text{net}} = \left| \sum_{t=1}^N \left[(\text{solar}_t + \text{grid}_t + \text{bat\_dis}_t) - (\text{demand\_served}_t + \text{bat\_chg}_t + \text{solar\_curt}_t)\right] \right|$$
+  3. Battery boundary validator enforces four physical invariants:
+     - Hard physical bounds: $0 \le SoC(t) \le C_{\text{bat}}$.
+     - Non-discretionary minimum protection floor: $SoC(t) \ge SoC_{\min} = 0.10 \times C_{\text{bat}}$ [D-09] during normal operation (`grid_available == True` or `active_load_tier == 3`). Drawdown below $SoC_{\min}$ (down to 0) is permitted only when `allow_emergency_drawdown=True` during active utility blackouts (`grid_available == False` and `active_load_tier < 3`).
+     - Continuous C-rate power limits: $P_{\text{chg}}(t) \le 0.5\text{C}$ and $P_{\text{dis}}(t) \le 1.0\text{C}$ (evaluated over $\Delta t = 1.0\text{h}$).
+     - Mutual exclusivity: simultaneous charging and discharging in the same hour ($P_{\text{chg}} > 10^{-6}\text{ kWh}$ and $P_{\text{dis}} > 10^{-6}\text{ kWh}$) is strictly prohibited.
+  4. Provides a reusable 48-hour golden reference fixture (`create_golden_scenario()`) covering all microgrid operating regimes with exact $0.000000\text{ kWh}$ residual.
+- **Reasoning:** Zero-mean IEEE 754 floating-point rounding jitter across $N$ independent steps behaves as a 1D random walk with standard deviation $\sigma_N = \sqrt{N} \epsilon$. Scaling cumulative tolerance by $\sqrt{N}$ accommodates harmless numerical rounding while rigorously tripping on any systematic numerical leakage or bias (e.g. an uncorrected bias of $0.9 \times 10^{-5}\text{ kWh/hr}$ accumulates to $0.07884\text{ kWh}$, which is ~84× the allowable threshold, triggering an immediate failure).
+- **Affects:** `CORE-004`, `CORE-005`, `DEM-001`, `DEM-002`, `BAT-001`, `BAT-002`, `SOL-001`, `OUT-001`, `INT-001`, `INT-002`, `INT-003`.
+
+
diff --git a/docs/tasks/status.md b/docs/tasks/status.md
index 101867c..79fbb9b 100644
--- a/docs/tasks/status.md
+++ b/docs/tasks/status.md
@@ -57,10 +57,10 @@ Status: **open**
 | CORE-003.3   | Implement synthetic monthly electricity bill generator                           | `done` | `SyntheticBillGenerator` + noise       |
 | CORE-003.4   | Validate synthetic bills against regional EUI (150–300 kWh/m²·yr)                | `done` | EUI = 159.41 kWh/m²·yr (pass)          |
 | CORE-003.5   | Reconcile equipment audit connected load & tier split summary                    | `done` | [CORE-003.5-gemini-equipment-totals-fixup.md](../reports/CORE-003.5-gemini-equipment-totals-fixup.md) (147.81 kW) |
-| **CORE-004** | **Shared Test Harness & Energy Balance Invariant Checker**                       | `open` | Critical test gate    |
-| CORE-004.1   | Implement strict energy conservation checker ($\le 10^{-5}\text{ kWh}$)          | `open` | Conservation rule     |
-| CORE-004.2   | Implement battery boundary validator ($0 \le \text{SoC} \le \text{Cap}$, C-rate) | `open` | State boundaries      |
-| CORE-004.3   | Build shared golden fixture runner for sub-model validation                      | `open` | Shared runner         |
+| **CORE-004** | **Shared Test Harness & Energy Balance Invariant Checker**                       | `done` | [CORE-004-gemini-conservation-harness.md](../reports/CORE-004-gemini-conservation-harness.md) |
+| CORE-004.1   | Implement strict energy conservation checker ($\le 10^{-5}\text{ kWh}$)          | `done` | Hourly residual + cumulative drift tolerance [D-21]                              |
+| CORE-004.2   | Implement battery boundary validator ($0 \le \text{SoC} \le \text{Cap}$, C-rate) | `done` | Physical bounds, min SoC floor, C-rate limits, mutual exclusivity                |
+| CORE-004.3   | Build shared golden fixture runner for sub-model validation                      | `done` | 48h reference fixture `create_golden_scenario()` + self-test                     |
 | **CORE-005** | **Baseline Engine Smoke Test (Phase 1 Exit Gate)**                               | `open` | Exit gate             |
 | CORE-005.1   | Implement grid-only, zero-solar, zero-battery simulation                         | `open` | Baseline engine       |
 | CORE-005.2   | Run 8,760-hour baseline through energy-balance test harness                      | `open` | Zero-leak test        |
diff --git a/src/ccis_sim/core/__init__.py b/src/ccis_sim/core/__init__.py
index ece2fe6..2783856 100644
--- a/src/ccis_sim/core/__init__.py
+++ b/src/ccis_sim/core/__init__.py
@@ -10,10 +10,24 @@ from ccis_sim.core.models import (
     RoomInventory,
     SolarArray,
 )
+from ccis_sim.core.verification import (
+    BatteryBoundaryViolation,
+    ConservationViolation,
+    VerificationReport,
+    ViolationType,
+    assert_simulation_valid,
+    check_energy_conservation,
+    compute_cumulative_tolerance,
+    create_golden_scenario,
+    run_verification_harness,
+    validate_battery_boundaries,
+)
 
 __all__ = [
     "Battery",
+    "BatteryBoundaryViolation",
     "Building",
+    "ConservationViolation",
     "HourlyRecord",
     "LoadTier",
     "OutageEvent",
@@ -20,4 +20,13 @@ __all__ = [
     "RoomInventory",
     "SolarArray",
+    "VerificationReport",
+    "ViolationType",
+    "assert_simulation_valid",
+    "check_energy_conservation",
+    "compute_cumulative_tolerance",
+    "create_golden_scenario",
+    "run_verification_harness",
+    "validate_battery_boundaries",
 ]
+
diff --git a/src/ccis_sim/core/verification.py b/src/ccis_sim/core/verification.py
new file mode 100644
index 0000000..f67c3b2
--- /dev/null
+++ b/src/ccis_sim/core/verification.py
@@ -0,0 +1,417 @@
+"""Verification and validation harness for CCIS energy simulation.
+
+Implements strict energy conservation and battery boundary checking across
+simulation time series, per:
+- docs/context/conceptual-model.md §4
+- docs/decisions/decision-log.md [D-09], [D-10], [D-17], [D-21]
+"""
+
+from __future__ import annotations
+
+import math
+from dataclasses import dataclass
+from enum import Enum
+from typing import Sequence
+
+from ccis_sim.core.models import Battery, HourlyRecord, LoadTier
+
+
+class ViolationType(str, Enum):
+    """Classification of verification and boundary invariant violations."""
+
+    HOURLY_ENERGY_BALANCE = "hourly_energy_balance"
+    CUMULATIVE_ENERGY_BALANCE = "cumulative_energy_balance"
+    NEGATIVE_SOC = "negative_soc"
+    EXCEEDS_CAPACITY = "exceeds_capacity"
+    MIN_SOC_VIOLATION = "min_soc_violation"
+    CHARGE_RATE_EXCEEDED = "charge_rate_exceeded"
+    DISCHARGE_RATE_EXCEEDED = "discharge_rate_exceeded"
+    SIMULTANEOUS_CHARGE_DISCHARGE = "simultaneous_charge_discharge"
+
+
+@dataclass(frozen=True)
+class ConservationViolation:
+    """Detailed record of an energy balance conservation failure."""
+
+    hour: int
+    timestamp: str
+    residual_kwh: float
+    tolerance_kwh: float
+    energy_in_kwh: float
+    energy_out_kwh: float
+    violation_type: ViolationType = ViolationType.HOURLY_ENERGY_BALANCE
+    details: str = ""
+
+    def summary(self) -> str:
+        """Return formatted single-line violation summary."""
+        return (
+            f"Hour {self.hour} ({self.timestamp}): residual {self.residual_kwh:.6e} kWh "
+            f"> tolerance {self.tolerance_kwh:.6e} kWh "
+            f"[In={self.energy_in_kwh:.4f} kWh, Out={self.energy_out_kwh:.4f} kWh] - {self.details}"
+        )
+
+
+@dataclass(frozen=True)
+class BatteryBoundaryViolation:
+    """Detailed record of a battery boundary or operating invariant violation."""
+
+    hour: int
+    timestamp: str
+    violation_type: ViolationType
+    actual_value: float
+    limit_value: float
+    details: str = ""
+
+    def summary(self) -> str:
+        """Return formatted single-line violation summary."""
+        return (
+            f"Hour {self.hour} ({self.timestamp}): {self.violation_type.value} "
+            f"- actual={self.actual_value:.4f}, limit={self.limit_value:.4f} - {self.details}"
+        )
+
+
+@dataclass(frozen=True)
+class VerificationReport:
+    """Comprehensive outcome of verification harness across a simulation run."""
+
+    total_records: int
+    conservation_violations: list[ConservationViolation]
+    battery_violations: list[BatteryBoundaryViolation]
+    cumulative_net_drift_kwh: float
+    cumulative_tolerance_kwh: float
+    cumulative_conserved: bool
+    max_residual_kwh: float
+
+    @property
+    def is_valid(self) -> bool:
+        """Whether the time series satisfies all physical invariants and boundary rules."""
+        return (
+            self.cumulative_conserved
+            and len(self.conservation_violations) == 0
+            and len(self.battery_violations) == 0
+        )
+
+    @property
+    def total_violations(self) -> int:
+        """Total number of failed checks detected across all categories."""
+        return (
+            len(self.conservation_violations)
+            + len(self.battery_violations)
+            + (0 if self.cumulative_conserved else 1)
+        )
+
+    def summary(self) -> str:
+        """Format a human-readable verification summary report."""
+        status = "PASSED" if self.is_valid else "FAILED"
+        lines = [
+            f"=== Simulation Verification Report: {status} ===",
+            f"Evaluated Records: {self.total_records}",
+            f"Max Hourly Residual: {self.max_residual_kwh:.6e} kWh",
+            f"Cumulative Net Drift: {self.cumulative_net_drift_kwh:.6e} kWh "
+            f"(tolerance: {self.cumulative_tolerance_kwh:.6e} kWh, "
+            f"conserved: {self.cumulative_conserved})",
+            f"Hourly Conservation Violations: {len(self.conservation_violations)}",
+            f"Battery Boundary Violations: {len(self.battery_violations)}",
+        ]
+
+        if self.conservation_violations:
+            lines.append("\n--- Top Conservation Violations ---")
+            for v in self.conservation_violations[:10]:
+                lines.append(f"  * {v.summary()}")
+            if len(self.conservation_violations) > 10:
+                lines.append(f"  ... and {len(self.conservation_violations) - 10} more.")
+
+        if self.battery_violations:
+            lines.append("\n--- Top Battery Boundary Violations ---")
+            for v in self.battery_violations[:10]:
+                lines.append(f"  * {v.summary()}")
+            if len(self.battery_violations) > 10:
+                lines.append(f"  ... and {len(self.battery_violations) - 10} more.")
+
+        return "\n".join(lines)
+
+
+def compute_cumulative_tolerance(n_records: int, tolerance_hour: float = 1e-5) -> float:
+    """Compute statistically defensible cumulative conservation tolerance per [D-21].
+
+    Random numerical rounding across independent hourly calculations scales as
+    O(sqrt(N) * epsilon). To permit benign zero-mean IEEE 754 floating point jitter
+    while reliably catching systematic numerical bias, the cumulative tolerance is:
+        tolerance_cum = max(tolerance_hour, sqrt(N) * tolerance_hour)
+
+    For N = 8,760 hours and epsilon = 1e-5 kWh, tolerance_cum ~= 9.359e-4 kWh (~0.001 kWh).
+    A systematic bias of 0.9e-5 kWh/hr produces 0.0788 kWh >> 9.359e-4 kWh, tripping cleanly.
+    """
+    if n_records <= 0:
+        return tolerance_hour
+    return max(tolerance_hour, math.sqrt(n_records) * tolerance_hour)
+
+
+def check_energy_conservation(
+    records: Sequence[HourlyRecord],
+    tolerance: float = 1e-5,
+    cumulative_tolerance: float | None = None,
+) -> list[ConservationViolation]:
+    """Verify strict physical energy balance conservation across a sequence of records.
+
+    Reuses HourlyRecord.energy_balance_residual_kwh and HourlyRecord.is_energy_conserved()
+    to guarantee identical residual calculation logic as canonical models.
+
+    Args:
+        records: Sequence of HourlyRecord instances.
+        tolerance: Maximum allowable residual per hour (default 1e-5 kWh per [D-05]).
+        cumulative_tolerance: Maximum allowable cumulative net drift across all records.
+            If None, defaults to compute_cumulative_tolerance(len(records), tolerance) per [D-21].
+
+    Returns:
+        List of ConservationViolation instances for any hourly or cumulative failures.
+    """
+    violations: list[ConservationViolation] = []
+    if not records:
+        return violations
+
+    total_in = 0.0
+    total_out = 0.0
+
+    for r in records:
+        e_in = r.solar_generation_kwh + r.grid_import_kwh + r.battery_discharge_kwh
+        e_out = r.demand_served_kwh + r.battery_charge_kwh + r.solar_curtailed_kwh
+        total_in += e_in
+        total_out += e_out
+
+        residual = r.energy_balance_residual_kwh
+        if not r.is_energy_conserved(tolerance=tolerance):
+            violations.append(
+                ConservationViolation(
+                    hour=r.hour,
+                    timestamp=r.timestamp,
+                    residual_kwh=residual,
+                    tolerance_kwh=tolerance,
+                    energy_in_kwh=e_in,
+                    energy_out_kwh=e_out,
+                    violation_type=ViolationType.HOURLY_ENERGY_BALANCE,
+                    details=(
+                        f"Hourly energy balance residual {residual:.6e} kWh exceeded "
+                        f"tolerance {tolerance:.6e} kWh"
+                    ),
+                )
+            )
+
+    net_drift = total_in - total_out
+    cum_tol = (
+        cumulative_tolerance
+        if cumulative_tolerance is not None
+        else compute_cumulative_tolerance(len(records), tolerance)
+    )
+
+    if abs(net_drift) > cum_tol:
+        violations.append(
+            ConservationViolation(
+                hour=0,
+                timestamp="CUMULATIVE_RUN",
+                residual_kwh=abs(net_drift),
+                tolerance_kwh=cum_tol,
+                energy_in_kwh=total_in,
+                energy_out_kwh=total_out,
+                violation_type=ViolationType.CUMULATIVE_ENERGY_BALANCE,
+                details=(
+                    f"Cumulative energy imbalance drift of {abs(net_drift):.6e} kWh "
+                    f"exceeded cumulative tolerance {cum_tol:.6e} kWh across {len(records)} hours."
+                ),
+            )
+        )
+
+    return violations
+
+
+def validate_battery_boundaries(
+    records: Sequence[HourlyRecord],
+    battery: Battery,
+    allow_emergency_drawdown: bool = False,
+    delta_t_hours: float = 1.0,
+) -> list[BatteryBoundaryViolation]:
+    """Validate physical and operational battery boundaries across a simulation time series.
+
+    Per [D-09] and [D-21], verifies:
+    1. 0 <= battery_soc_kwh <= Battery.capacity_kwh (hard physical limits)
+    2. battery_soc_kwh >= Battery.min_soc_kwh (cell protection floor, unless
+       allow_emergency_drawdown=True during an active grid blackout with Tier 1/2 shedding)
+    3. battery_charge_kwh <= max_charge_power_kw * delta_t_hours (0.5C limit)
+    4. battery_discharge_kwh <= max_discharge_power_kw * delta_t_hours (1.0C limit)
+    5. Mutual exclusivity: battery_charge_kwh and battery_discharge_kwh cannot both be > 1e-6 kWh
+
+    Args:
+        records: Sequence of HourlyRecord instances.
+        battery: Battery specification defining capacity and operational limits.
+        allow_emergency_drawdown: If True, allows SoC to dip below min_soc_kwh (down to 0)
+            strictly during active blackout hours (grid_available=False, active_load_tier in (1, 2)).
+        delta_t_hours: Timestep duration in hours (default 1.0).
+
+    Returns:
+        List of BatteryBoundaryViolation instances for any boundary violations.
+    """
+    violations: list[BatteryBoundaryViolation] = []
+    if not records:
+        return violations
+
+    fp_tol = 1e-9  # Floating-point numerical tolerance
+    max_charge_kwh = battery.max_charge_power_kw * delta_t_hours
+    max_discharge_kwh = battery.max_discharge_power_kw * delta_t_hours
+
+    for r in records:
+        # 1. Negative SoC check
+        if r.battery_soc_kwh < -fp_tol:
+            violations.append(
+                BatteryBoundaryViolation(
+                    hour=r.hour,
+                    timestamp=r.timestamp,
+                    violation_type=ViolationType.NEGATIVE_SOC,
+                    actual_value=r.battery_soc_kwh,
+                    limit_value=0.0,
+                    details=f"Battery SoC {r.battery_soc_kwh:.6f} kWh is physically negative.",
+                )
+            )
+
+        # 2. Exceeds nameplate capacity check
+        if r.battery_soc_kwh > battery.capacity_kwh + fp_tol:
+            violations.append(
+                BatteryBoundaryViolation(
+                    hour=r.hour,
+                    timestamp=r.timestamp,
+                    violation_type=ViolationType.EXCEEDS_CAPACITY,
+                    actual_value=r.battery_soc_kwh,
+                    limit_value=battery.capacity_kwh,
+                    details=(
+                        f"Battery SoC {r.battery_soc_kwh:.4f} kWh exceeds rated "
+                        f"capacity {battery.capacity_kwh:.4f} kWh."
+                    ),
+                )
+            )
+
+        # 3. Minimum SoC floor check
+        is_emergency = (not r.grid_available) and (
+            r.active_load_tier in (LoadTier.TIER_1_CRITICAL, LoadTier.TIER_2_ESSENTIAL, 1, 2)
+        )
+        if r.battery_soc_kwh < battery.min_soc_kwh - fp_tol:
+            if not (allow_emergency_drawdown and is_emergency):
+                violations.append(
+                    BatteryBoundaryViolation(
+                        hour=r.hour,
+                        timestamp=r.timestamp,
+                        violation_type=ViolationType.MIN_SOC_VIOLATION,
+                        actual_value=r.battery_soc_kwh,
+                        limit_value=battery.min_soc_kwh,
+                        details=(
+                            f"Battery SoC {r.battery_soc_kwh:.4f} kWh fell below minimum protection floor "
+                            f"{battery.min_soc_kwh:.4f} kWh ({battery.min_soc_pct*100:.0f}%) "
+                            f"outside permitted emergency conditions."
+                        ),
+                    )
+                )
+
+        # 4. Charge rate limit (C-rate)
+        if r.battery_charge_kwh > max_charge_kwh + fp_tol:
+            violations.append(
+                BatteryBoundaryViolation(
+                    hour=r.hour,
+                    timestamp=r.timestamp,
+                    violation_type=ViolationType.CHARGE_RATE_EXCEEDED,
+                    actual_value=r.battery_charge_kwh,
+                    limit_value=max_charge_kwh,
+                    details=(
+                        f"Battery charge {r.battery_charge_kwh:.4f} kWh exceeded "
+                        f"max power limit {max_charge_kwh:.4f} kWh (C-rate {battery.max_charge_c_rate}C)."
+                    ),
+                )
+            )
+
+        # 5. Discharge rate limit (C-rate)
+        if r.battery_discharge_kwh > max_discharge_kwh + fp_tol:
+            violations.append(
+                BatteryBoundaryViolation(
+                    hour=r.hour,
+                    timestamp=r.timestamp,
+                    violation_type=ViolationType.DISCHARGE_RATE_EXCEEDED,
+                    actual_value=r.battery_discharge_kwh,
+                    limit_value=max_discharge_kwh,
+                    details=(
+                        f"Battery discharge {r.battery_discharge_kwh:.4f} kWh exceeded "
+                        f"max power limit {max_discharge_kwh:.4f} kWh (C-rate {battery.max_discharge_c_rate}C)."
+                    ),
+                )
+            )
+
+        # 6. Simultaneous charge and discharge prevention
+        if r.battery_charge_kwh > 1e-6 and r.battery_discharge_kwh > 1e-6:
+            violations.append(
+                BatteryBoundaryViolation(
+                    hour=r.hour,
+                    timestamp=r.timestamp,
+                    violation_type=ViolationType.SIMULTANEOUS_CHARGE_DISCHARGE,
+                    actual_value=min(r.battery_charge_kwh, r.battery_discharge_kwh),
+                    limit_value=0.0,
+                    details=(
+                        f"Simultaneous charge ({r.battery_charge_kwh:.4f} kWh) and discharge "
+                        f"({r.battery_discharge_kwh:.4f} kWh) in same hour."
+                    ),
+                )
+            )
+
+    return violations
+
+
+def run_verification_harness(
+    records: Sequence[HourlyRecord],
+    battery: Battery | None = None,
+    tolerance: float = 1e-5,
+    cumulative_tolerance: float | None = None,
+    allow_emergency_drawdown: bool = False,
+    delta_t_hours: float = 1.0,
+) -> VerificationReport:
+    """Execute complete verification harness across a simulation time series.
+
+    Validates both hourly energy conservation invariants and (if battery is provided)
+    battery physical boundary conditions.
+
+    Args:
+        records: Sequence of HourlyRecord instances.
+        battery: Optional Battery instance. If provided, battery boundaries are checked.
+        tolerance: Per-hour energy balance tolerance (default 1e-5 kWh).
+        cumulative_tolerance: Optional cumulative net drift tolerance (default per [D-21]).
+        allow_emergency_drawdown: Whether to permit SoC below min_soc during emergency blackouts.
+        delta_t_hours: Hourly timestep duration.
+
+    Returns:
+        VerificationReport containing full diagnostics.
+    """
+    conservation_violations = check_energy_conservation(
+        records=records,
+        tolerance=tolerance,
+        cumulative_tolerance=cumulative_tolerance,
+    )
+
+    battery_violations: list[BatteryBoundaryViolation] = []
+    if battery is not None:
+        battery_violations = validate_battery_boundaries(
+            records=records,
+            battery=battery,
+            allow_emergency_drawdown=allow_emergency_drawdown,
+            delta_t_hours=delta_t_hours,
+        )
+
+    # Compute aggregate stats
+    total_in = sum(
+        r.solar_generation_kwh + r.grid_import_kwh + r.battery_discharge_kwh for r in records
+    )
+    total_out = sum(
+        r.demand_served_kwh + r.battery_charge_kwh + r.solar_curtailed_kwh for r in records
+    )
+    net_drift = total_in - total_out
+    cum_tol = (
+        cumulative_tolerance
+        if cumulative_tolerance is not None
+        else compute_cumulative_tolerance(len(records), tolerance)
+    )
+    cum_conserved = abs(net_drift) <= cum_tol
+    max_residual = max((r.energy_balance_residual_kwh for r in records), default=0.0)
+
+    # Filter out cumulative violation from conservation_violations list if we want to separate
+    # hourly vs cumulative in the report object:
+    hourly_conservation_violations = [
+        v for v in conservation_violations if v.violation_type != ViolationType.CUMULATIVE_ENERGY_BALANCE
+    ]
+
+    return VerificationReport(
+        total_records=len(records),
+        conservation_violations=hourly_conservation_violations,
+        battery_violations=battery_violations,
+        cumulative_net_drift_kwh=net_drift,
+        cumulative_tolerance_kwh=cum_tol,
+        cumulative_conserved=cum_conserved,
+        max_residual_kwh=max_residual,
+    )
+
+
+def assert_simulation_valid(
+    records: Sequence[HourlyRecord],
+    battery: Battery | None = None,
+    tolerance: float = 1e-5,
+    cumulative_tolerance: float | None = None,
+    allow_emergency_drawdown: bool = False,
+    delta_t_hours: float = 1.0,
+) -> None:
+    """Assertion helper for test suites. Raises AssertionError with detailed report on failure."""
+    report = run_verification_harness(
+        records=records,
+        battery=battery,
+        tolerance=tolerance,
+        cumulative_tolerance=cumulative_tolerance,
+        allow_emergency_drawdown=allow_emergency_drawdown,
+        delta_t_hours=delta_t_hours,
+    )
+    if not report.is_valid:
+        raise AssertionError(f"Simulation verification failed:\n{report.summary()}")
+
+
+def create_golden_scenario(battery: Battery | None = None) -> list[HourlyRecord]:
+    """Construct a canonical 48-hour synthetic reference scenario with exact energy conservation.
+
+    The scenario exercises all primary physical microgrid states:
+    - Day 1 (Hours 1–24): Normal grid operation.
+      - Hours 1–4: Nighttime battery discharge down to min_soc floor (10.0 kWh).
+      - Hours 5–6: Nighttime grid import sustaining baseload while battery sits at floor.
+      - Hours 7–9: Morning solar generation ramp, serving demand and charging battery.
+      - Hours 10–14: Peak midday solar surplus filling battery to 100% capacity, then curtailing.
+      - Hour 15: Exact zero net-load balance (solar generation strictly equals demand).
+      - Hours 16–20: Afternoon/evening solar decline supplemented by battery discharge.
+      - Hours 21–24: Evening transition back to grid import after battery reaches min_soc.
+    - Day 2 (Hours 25–48): Outage resilience and recovery.
+      - Hours 25–29: Morning pre-outage charging to full capacity (100 kWh).
+      - Hours 30–37: 8-hour grid blackout (grid_available=False), shedding Tier 3 comfort
+        cooling to Tier 2 essential load (5.0 kWh), sustained by islanded battery and solar.
+      - Hours 38–48: Grid restoration, battery post-outage evening discharge and recovery.
+
+    All 48 hours have identically zero energy balance residuals (residual = 0.000000)
+    and strictly conform to Battery boundaries.
+    """
+    bat = battery or Battery(capacity_kwh=100.0)
+    records: list[HourlyRecord] = []
+
+    # State tracking
+    current_soc = 50.0  # Initial SoC at start of Day 1 (kWh)
+
+    # 48-hour schedule definitions: (hour, solar_gen, demand_gross, grid_avail, tier, target_bat_dis, target_bat_chg)
+    # We will compute the exact flows to guarantee strict mathematical balance.
+    # Day 1:
+    day_1_plan = [
+        # Night: battery discharges 10 kWh/hr down to min_soc (10 kWh)
+        (1, 0.0, 10.0, True, 3, 10.0, 0.0),
+        (2, 0.0, 10.0, True, 3, 10.0, 0.0),
+        (3, 0.0, 10.0, True, 3, 10.0, 0.0),
+        (4, 0.0, 10.0, True, 3, 10.0, 0.0),  # hits 10.0 kWh min_soc
+        # Night: battery at floor, grid imports 10 kWh
+        (5, 0.0, 10.0, True, 3, 0.0, 0.0),
+        (6, 0.0, 10.0, True, 3, 0.0, 0.0),
+        # Morning ramp: solar serves demand and charges battery
+        (7, 20.0, 10.0, True, 3, 0.0, 10.0),  # SoC -> 20.0
+        (8, 40.0, 15.0, True, 3, 0.0, 25.0),  # SoC -> 45.0
+        (9, 65.0, 20.0, True, 3, 0.0, 45.0),  # SoC -> 90.0 (45 <= 50kW max charge)
+        # Midday: battery reaches full (100 kWh), remainder curtailed
+        (10, 80.0, 25.0, True, 3, 0.0, 10.0), # SoC -> 100.0, curtailed = 45.0
+        (11, 85.0, 30.0, True, 3, 0.0, 0.0),  # SoC = 100.0, curtailed = 55.0
+        (12, 90.0, 30.0, True, 3, 0.0, 0.0),  # SoC = 100.0, curtailed = 60.0
+        (13, 70.0, 30.0, True, 3, 0.0, 0.0),  # SoC = 100.0, curtailed = 40.0
+        (14, 45.0, 25.0, True, 3, 0.0, 0.0),  # SoC = 100.0, curtailed = 20.0
+        # Zero net-load hour
+        (15, 25.0, 25.0, True, 3, 0.0, 0.0),  # Net load = 0
+        # Afternoon decline: solar + battery discharge
+        (16, 10.0, 25.0, True, 3, 15.0, 0.0), # SoC -> 85.0
+        (17, 5.0, 20.0, True, 3, 15.0, 0.0),  # SoC -> 70.0
+        (18, 0.0, 20.0, True, 3, 20.0, 0.0),  # SoC -> 50.0
+        # Evening: battery discharge down to min_soc
+        (19, 0.0, 15.0, True, 3, 15.0, 0.0),  # SoC -> 35.0
+        (20, 0.0, 15.0, True, 3, 15.0, 0.0),  # SoC -> 20.0
+        (21, 0.0, 15.0, True, 3, 10.0, 0.0),  # SoC -> 10.0 (hits floor), grid import = 5
+        (22, 0.0, 10.0, True, 3, 0.0, 0.0),   # grid import = 10
+        (23, 0.0, 10.0, True, 3, 0.0, 0.0),   # grid import = 10
+        (24, 0.0, 10.0, True, 3, 0.0, 0.0),   # grid import = 10
+    ]
+
+    # Day 2:
+    day_2_plan = [
+        # Early morning grid import
+        (25, 0.0, 10.0, True, 3, 0.0, 0.0),   # SoC = 10.0
+        (26, 0.0, 10.0, True, 3, 0.0, 0.0),   # SoC = 10.0
+        # Solar ramp pre-charging battery
+        (27, 25.0, 10.0, True, 3, 0.0, 15.0), # SoC -> 25.0
+        (28, 50.0, 15.0, True, 3, 0.0, 35.0), # SoC -> 60.0
+        (29, 60.0, 20.0, True, 3, 0.0, 40.0), # SoC -> 100.0 (full!)
+        # Hours 30-37: 8-hour blackout! Shedding to Tier 2 (served = 5.0 kW)
+        (30, 10.0, 25.0, False, 2, 0.0, 0.0), # Solar 10 serves 5kW, curtails 5kW, SoC=100
+        (31, 0.0, 25.0, False, 2, 5.0, 0.0),  # Islanded battery discharge -> SoC 95.0
+        (32, 0.0, 25.0, False, 2, 5.0, 0.0),  # SoC -> 90.0
+        (33, 0.0, 25.0, False, 2, 5.0, 0.0),  # SoC -> 85.0
+        (34, 0.0, 25.0, False, 2, 5.0, 0.0),  # SoC -> 80.0
+        (35, 0.0, 25.0, False, 2, 5.0, 0.0),  # SoC -> 75.0
+        (36, 0.0, 25.0, False, 2, 5.0, 0.0),  # SoC -> 70.0
+        (37, 0.0, 25.0, False, 2, 5.0, 0.0),  # SoC -> 65.0
+        # Hours 38-48: Grid restored, Tier 3 active
+        (38, 0.0, 15.0, True, 3, 15.0, 0.0),  # SoC -> 50.0
+        (39, 0.0, 15.0, True, 3, 15.0, 0.0),  # SoC -> 35.0
+        (40, 0.0, 15.0, True, 3, 15.0, 0.0),  # SoC -> 20.0
+        (41, 0.0, 15.0, True, 3, 10.0, 0.0),  # SoC -> 10.0 (hits floor), grid import = 5
+        (42, 0.0, 10.0, True, 3, 0.0, 0.0),   # grid import = 10
+        (43, 0.0, 10.0, True, 3, 0.0, 0.0),   # grid import = 10
+        (44, 0.0, 10.0, True, 3, 0.0, 0.0),   # grid import = 10
+        (45, 0.0, 10.0, True, 3, 0.0, 0.0),   # grid import = 10
+        (46, 0.0, 10.0, True, 3, 0.0, 0.0),   # grid import = 10
+        (47, 0.0, 10.0, True, 3, 0.0, 0.0),   # grid import = 10
+        (48, 0.0, 10.0, True, 3, 0.0, 0.0),   # grid import = 10
+    ]
+
+    for (h, solar_gen, demand_gross, grid_avail, tier, bat_dis, bat_chg) in (day_1_plan + day_2_plan):
+        # Determine demand served based on tier and grid availability
+        if grid_avail:
+            demand_served = demand_gross
+            unserved = 0.0
+        else:
+            # During blackout, Tier 2 served = 5.0 kWh; unserved = gross - served
+            demand_served = 5.0
+            unserved = demand_gross - demand_served
+
+        # Compute direct solar to demand
+        solar_to_demand = min(solar_gen, demand_served)
+        solar_surplus = solar_gen - solar_to_demand
+
+        solar_to_bat = bat_chg
+        solar_curtailed = solar_surplus - solar_to_bat
+
+        # Deficit after solar and battery discharge
+        remaining_demand = demand_served - solar_to_demand - bat_dis
+        if remaining_demand > 1e-9:
+            grid_import = remaining_demand
+        else:
+            grid_import = 0.0
+
+        current_soc = current_soc + bat_chg - bat_dis
+
+        # Format ISO timestamp (starting 2026-04-15)
+        day_offset = (h - 1) // 24
+        hour_in_day = (h - 1) % 24
+        ts = f"2026-04-{15 + day_offset:02d}T{hour_in_day:02d}:00:00+08:00"
+
+        rec = HourlyRecord(
+            hour=h,
+            timestamp=ts,
+            temp_ambient_c=25.0 + (5.0 if 8 <= hour_in_day <= 16 else 0.0),
+            humidity_rel_pct=75.0,
+            ghi_w_m2=solar_gen * 10.0,
+            demand_gross_kwh=demand_gross,
+            demand_served_kwh=demand_served,
+            solar_generation_kwh=solar_gen,
+            solar_to_demand_kwh=solar_to_demand,
+            solar_to_battery_kwh=solar_to_bat,
+            solar_curtailed_kwh=solar_curtailed,
+            battery_soc_kwh=round(current_soc, 6),
+            battery_charge_kwh=bat_chg,
+            battery_discharge_kwh=bat_dis,
+            grid_import_kwh=grid_import,
+            unserved_load_kwh=unserved,
+            grid_available=grid_avail,
+            active_load_tier=tier,
+        )
+        records.append(rec)
+
+    return records
diff --git a/tests/fixtures/README.md b/tests/fixtures/README.md
new file mode 100644
index 0000000..7aa29b9
--- /dev/null
+++ b/tests/fixtures/README.md
@@ -0,0 +1,63 @@
+# Shared Golden Reference Fixtures
+
+This directory and the `ccis_sim.core.verification` module provide shared golden reference fixtures and assertion harnesses for validating simulation outputs across sub-model tasks (`DEM-001/002`, `SOL-001/002`, `BAT-001/002`, `OUT-001/002`, `CORE-005`, and `INT-001/002/003`).
+
+## Golden Scenario Fixture: `create_golden_scenario()`
+
+`create_golden_scenario(battery: Battery | None = None) -> list[HourlyRecord]`
+
+Constructs a 48-hour continuous synthetic scenario (Hour 1 to Hour 48) containing known-correct, hand-calculated energy flows covering all primary microgrid operational modes:
+- **Nighttime battery discharge**: Discharges down to the 10% non-discretionary minimum protection floor ($SoC_{\min} = 10.0\text{ kWh}$).
+- **Nighttime grid import**: Grid sustains building baseload while battery remains at the protection floor.
+- **Solar generation ramp**: PV output serves building load and routes excess into battery storage.
+- **Solar curtailment**: Battery reaches 100% capacity ($100.0\text{ kWh}$), and remaining solar surplus is curtailed.
+- **Zero net-load hour**: Hour 15 has solar generation exactly matching building load.
+- **Afternoon/evening battery dispatch**: Battery supplements declining solar generation.
+- **Grid outage & priority load shedding**: Hours 30–37 simulate an 8-hour utility blackout (`grid_available = False`), shedding Tier 3 load to Tier 2 essential load ($5.0\text{ kW}$), sustained by islanded battery and depressed solar.
+- **Grid restoration & recovery**: Grid returns at Hour 38, restoring normal Tier 3 operations.
+
+Every single record has an exact residual of $0.000000\text{ kWh}$ and strictly satisfies all battery boundary conditions.
+
+## Usage in Downstream Test Suites
+
+Instead of reinventing fixture generation or copy-pasting assertion boilerplate, import and use the shared harness:
+
+```python
+import pytest
+from ccis_sim.core import (
+    Battery,
+    HourlyRecord,
+    assert_simulation_valid,
+    check_energy_conservation,
+    create_golden_scenario,
+    run_verification_harness,
+    validate_battery_boundaries,
+)
+
+def test_my_submodel_energy_balance():
+    # 1. Obtain golden reference sequence or generate records from your submodel
+    battery = Battery(capacity_kwh=100.0)
+    records = create_golden_scenario(battery=battery)
+
+    # 2. Run verification harness
+    report = run_verification_harness(records, battery=battery)
+    assert report.is_valid, report.summary()
+
+def test_my_submodel_assertions():
+    # Or use direct assertion helper (raises AssertionError with full diagnostic summary on failure)
+    records = ... # your simulation records
+    assert_simulation_valid(records, battery=battery)
+```
+
+## Available Verification Functions
+
+1. `check_energy_conservation(records, tolerance=1e-5, cumulative_tolerance=None) -> list[ConservationViolation]`
+   - Validates per-hour energy conservation ($\text{residual} \le 10^{-5}\text{ kWh}$).
+   - Validates cumulative conservation drift ($\Delta E_{\text{net}} \le \max(10^{-5}, \sqrt{N} \times 10^{-5})$ per decision `[D-21]`).
+2. `validate_battery_boundaries(records, battery, allow_emergency_drawdown=False) -> list[BatteryBoundaryViolation]`
+   - Validates $0 \le SoC(t) \le C_{\text{bat}}$.
+   - Validates $SoC(t) \ge SoC_{\min}$ (10% floor outside permitted emergency blackouts).
+   - Validates C-rate power bounds ($0.5\text{C}$ charge, $1.0\text{C}$ discharge).
+   - Validates mutual exclusivity (no simultaneous charge and discharge $> 10^{-6}\text{ kWh}$).
+3. `run_verification_harness(records, battery=None, ...) -> VerificationReport`
+   - Complete verification run returning structured diagnostic report with `summary()`.
+4. `assert_simulation_valid(records, battery=None, ...) -> None`
+   - Test assertion helper.
diff --git a/tests/test_conservation_checker.py b/tests/test_conservation_checker.py
new file mode 100644
index 0000000..f82d126
--- /dev/null
+++ b/tests/test_conservation_checker.py
@@ -0,0 +1,245 @@
+"""Unit tests for verification harness and invariant checker (CORE-004).
+
+Tests strict hourly and cumulative energy balance conservation, battery boundary
+validation, and the shared golden reference fixture.
+"""
+
+from __future__ import annotations
+
+import pytest
+
+from ccis_sim.core import (
+    Battery,
+    HourlyRecord,
+    ViolationType,
+    assert_simulation_valid,
+    check_energy_conservation,
+    compute_cumulative_tolerance,
+    create_golden_scenario,
+    run_verification_harness,
+    validate_battery_boundaries,
+)
+
+
+def _make_dummy_record(
+    hour: int = 1,
+    solar_gen: float = 0.0,
+    grid_import: float = 10.0,
+    bat_dis: float = 0.0,
+    demand_served: float = 10.0,
+    bat_chg: float = 0.0,
+    solar_curt: float = 0.0,
+    soc: float = 50.0,
+    grid_avail: bool = True,
+    tier: int = 3,
+):
+    """Helper to construct a single HourlyRecord with specific energy flows."""
+    return HourlyRecord(
+        hour=hour,
+        timestamp=f"2026-04-15T{((hour - 1) % 24):02d}:00:00+08:00",
+        temp_ambient_c=25.0,
+        humidity_rel_pct=70.0,
+        ghi_w_m2=solar_gen * 10.0,
+        demand_gross_kwh=demand_served,
+        demand_served_kwh=demand_served,
+        solar_generation_kwh=solar_gen,
+        solar_to_demand_kwh=min(solar_gen, demand_served),
+        solar_to_battery_kwh=bat_chg,
+        solar_curtailed_kwh=solar_curt,
+        battery_soc_kwh=soc,
+        battery_charge_kwh=bat_chg,
+        battery_discharge_kwh=bat_dis,
+        grid_import_kwh=grid_import,
+        unserved_load_kwh=0.0,
+        grid_available=grid_avail,
+        active_load_tier=tier,
+    )
+
+
+# =========================================================================
+# CORE-004.1: Energy Conservation Checker Tests
+# =========================================================================
+
+
+def test_golden_scenario_conservation_passes():
+    """Verify that the 48-hour golden reference scenario satisfies strict conservation."""
+    records = create_golden_scenario()
+    assert len(records) == 48
+
+    violations = check_energy_conservation(records, tolerance=1e-5)
+    assert len(violations) == 0
+
+    report = run_verification_harness(records)
+    assert report.is_valid
+    assert report.cumulative_conserved
+    assert report.max_residual_kwh <= 1e-12
+    assert "PASSED" in report.summary()
+
+
+def test_deliberate_hourly_residual_violation_caught():
+    """Verify that a single unphysical imbalance (> 1e-5 kWh) is caught with exact diagnostics."""
+    records = create_golden_scenario()
+
+    # Tamper with Hour 12: inject 0.5 kWh unphysical energy imbalance
+    tampered_rec = HourlyRecord(
+        hour=12,
+        timestamp=records[11].timestamp,
+        temp_ambient_c=records[11].temp_ambient_c,
+        humidity_rel_pct=records[11].humidity_rel_pct,
+        ghi_w_m2=records[11].ghi_w_m2,
+        demand_gross_kwh=records[11].demand_gross_kwh,
+        demand_served_kwh=records[11].demand_served_kwh + 0.5,  # Unbalanced +0.5 kWh out
+        solar_generation_kwh=records[11].solar_generation_kwh,
+        solar_to_demand_kwh=records[11].solar_to_demand_kwh,
+        solar_to_battery_kwh=records[11].solar_to_battery_kwh,
+        solar_curtailed_kwh=records[11].solar_curtailed_kwh,
+        battery_soc_kwh=records[11].battery_soc_kwh,
+        battery_charge_kwh=records[11].battery_charge_kwh,
+        battery_discharge_kwh=records[11].battery_discharge_kwh,
+        grid_import_kwh=records[11].grid_import_kwh,
+        unserved_load_kwh=records[11].unserved_load_kwh,
+        grid_available=records[11].grid_available,
+        active_load_tier=records[11].active_load_tier,
+    )
+    records[11] = tampered_rec
+
+    violations = check_energy_conservation(records, tolerance=1e-5)
+    assert len(violations) >= 1
+
+    hourly_violations = [v for v in violations if v.violation_type == ViolationType.HOURLY_ENERGY_BALANCE]
+    assert len(hourly_violations) == 1
+    v = hourly_violations[0]
+    assert v.hour == 12
+    assert abs(v.residual_kwh - 0.5) < 1e-9
+    assert v.tolerance_kwh == 1e-5
+    assert "Hour 12" in v.summary()
+
+    report = run_verification_harness(records)
+    assert not report.is_valid
+    assert len(report.conservation_violations) == 1
+
+    with pytest.raises(AssertionError, match="Simulation verification failed"):
+        assert_simulation_valid(records)
+
+
+def test_cumulative_drift_catches_small_consistent_bias():
+    """Verify that a small persistent bias (0.9e-5 kWh/hr) passes individual checks but trips cumulative check.
+
+    Over 8,760 hours:
+    - Per-hour residual = 0.9e-5 kWh <= 1e-5 kWh (individually valid).
+    - Cumulative drift = 8,760 * 0.9e-5 = 0.07884 kWh.
+    - Cumulative tolerance = sqrt(8760) * 1e-5 ~= 9.359e-4 kWh.
+    - Since 0.07884 >> 9.359e-4, the cumulative invariant trips.
+    """
+    bias_per_hour = 0.9e-5  # Under per-hour 1e-5 tolerance
+    records: list[HourlyRecord] = []
+
+    for h in range(1, 8761):
+        rec = _make_dummy_record(
+            hour=h,
+            solar_gen=0.0,
+            grid_import=10.0 + bias_per_hour,  # Persistent upward bias
+            bat_dis=0.0,
+            demand_served=10.0,
+            bat_chg=0.0,
+            solar_curt=0.0,
+            soc=50.0,
+        )
+        assert rec.is_energy_conserved(tolerance=1e-5), f"Hour {h} should individually pass!"
+        records.append(rec)
+
+    # All 8,760 hours pass individual tolerance check
+    violations = check_energy_conservation(records, tolerance=1e-5)
+    hourly_violations = [v for v in violations if v.violation_type == ViolationType.HOURLY_ENERGY_BALANCE]
+    assert len(hourly_violations) == 0, "Individual hours must not trip per-hour check"
+
+    # Cumulative check trips
+    cumulative_violations = [
+        v for v in violations if v.violation_type == ViolationType.CUMULATIVE_ENERGY_BALANCE
+    ]
+    assert len(cumulative_violations) == 1
+    cum_v = cumulative_violations[0]
+    assert cum_v.hour == 0
+    assert abs(cum_v.residual_kwh - (8760 * bias_per_hour)) < 1e-6
+    expected_cum_tol = compute_cumulative_tolerance(8760, 1e-5)
+    assert abs(cum_v.tolerance_kwh - expected_cum_tol) < 1e-9
+
+    # Verification report reflects cumulative failure
+    report = run_verification_harness(records, tolerance=1e-5)
+    assert not report.is_valid
+    assert not report.cumulative_conserved
+    assert report.total_violations == 1
+    assert "FAILED" in report.summary()
+
+
+def test_cumulative_tolerance_computation():
+    """Verify compute_cumulative_tolerance scaling rules per [D-21]."""
+    # 0 or negative records
+    assert compute_cumulative_tolerance(0, 1e-5) == 1e-5
+    assert compute_cumulative_tolerance(-10, 1e-5) == 1e-5
+
+    # Small records where sqrt(N) <= 1
+    assert compute_cumulative_tolerance(1, 1e-5) == 1e-5
+
+    # Annual run N=8,760
+    tol_8760 = compute_cumulative_tolerance(8760, 1e-5)
+    expected = (8760**0.5) * 1e-5
+    assert abs(tol_8760 - expected) < 1e-12
+    assert 0.0009 < tol_8760 < 0.0010
+
+
+# =========================================================================
+# CORE-004.2: Battery Boundary Validator Tests
+# =========================================================================
+
+
+def test_battery_negative_soc_caught():
+    """Verify that physically negative SoC is caught."""
+    bat = Battery(capacity_kwh=100.0)
+    rec = _make_dummy_record(hour=1, soc=-0.5)
+
+    violations = validate_battery_boundaries([rec], battery=bat)
+    assert len(violations) == 2  # Negative SoC and below min_soc floor
+    neg_violations = [v for v in violations if v.violation_type == ViolationType.NEGATIVE_SOC]
+    assert len(neg_violations) == 1
+    assert neg_violations[0].actual_value == -0.5
+    assert neg_violations[0].limit_value == 0.0
+
+
+def test_battery_exceeds_capacity_caught():
+    """Verify that SoC exceeding rated nameplate capacity is caught."""
+    bat = Battery(capacity_kwh=100.0)
+    rec = _make_dummy_record(hour=1, soc=105.0)
+
+    violations = validate_battery_boundaries([rec], battery=bat)
+    assert len(violations) == 1
+    assert violations[0].violation_type == ViolationType.EXCEEDS_CAPACITY
+    assert violations[0].actual_value == 105.0
+    assert violations[0].limit_value == 100.0
+
+
+def test_battery_min_soc_floor_normal_vs_emergency():
+    """Verify min_soc floor protection and emergency drawdown rules."""
+    bat = Battery(capacity_kwh=100.0, min_soc_pct=0.10)  # min_soc = 10.0 kWh
+
+    # Case 1: Grid available (normal operation), SoC below floor (5.0 kWh) -> FAILS
+    rec_normal = _make_dummy_record(hour=1, soc=5.0, grid_avail=True, tier=3)
+    violations = validate_battery_boundaries([rec_normal], battery=bat, allow_emergency_drawdown=False)
+    assert len(violations) == 1
+    assert violations[0].violation_type == ViolationType.MIN_SOC_VIOLATION
+    assert violations[0].limit_value == 10.0
+
+    # Even with allow_emergency_drawdown=True, normal operation must NOT allow drawdown below min_soc
+    violations_normal_drawdown = validate_battery_boundaries(
+        [rec_normal], battery=bat, allow_emergency_drawdown=True
+    )
+    assert len(violations_normal_drawdown) == 1
+    assert violations_normal_drawdown[0].violation_type == ViolationType.MIN_SOC_VIOLATION
+
+    # Case 2: Outage condition (grid_avail=False, tier=2), allow_emergency_drawdown=False -> FAILS
+    rec_outage = _make_dummy_record(hour=2, soc=5.0, grid_avail=False, tier=2)
+    violations_outage_no_drawdown = validate_battery_boundaries(
+        [rec_outage], battery=bat, allow_emergency_drawdown=False
+    )
+    assert len(violations_outage_no_drawdown) == 1
+    assert violations_outage_no_drawdown[0].violation_type == ViolationType.MIN_SOC_VIOLATION
+
+    # Case 3: Outage condition (grid_avail=False, tier=2), allow_emergency_drawdown=True -> PASSES
+    violations_outage_allowed = validate_battery_boundaries(
+        [rec_outage], battery=bat, allow_emergency_drawdown=True
+    )
+    assert len(violations_outage_allowed) == 0
+
+
+def test_battery_charge_c_rate_exceeded_caught():
+    """Verify that charge rate exceeding max_charge_power_kw is caught."""
+    bat = Battery(capacity_kwh=100.0, max_charge_c_rate=0.5)  # 50.0 kW limit
+    rec = _make_dummy_record(hour=1, bat_chg=55.0, solar_curt=0.0, solar_gen=55.0, grid_import=0.0)
+
+    violations = validate_battery_boundaries([rec], battery=bat)
+    c_violations = [v for v in violations if v.violation_type == ViolationType.CHARGE_RATE_EXCEEDED]
+    assert len(c_violations) == 1
+    assert c_violations[0].actual_value == 55.0
+    assert c_violations[0].limit_value == 50.0
+
+
+def test_battery_discharge_c_rate_exceeded_caught():
+    """Verify that discharge rate exceeding max_discharge_power_kw is caught."""
+    bat = Battery(capacity_kwh=100.0, max_discharge_c_rate=1.0)  # 100.0 kW limit
+    rec = _make_dummy_record(hour=1, bat_dis=110.0, demand_served=110.0, grid_import=0.0)
+
+    violations = validate_battery_boundaries([rec], battery=bat)
+    d_violations = [v for v in violations if v.violation_type == ViolationType.DISCHARGE_RATE_EXCEEDED]
+    assert len(d_violations) == 1
+    assert d_violations[0].actual_value == 110.0
+    assert d_violations[0].limit_value == 100.0
+
+
+def test_simultaneous_charge_and_discharge_caught():
+    """Verify that simultaneous charging and discharging in the same hour is caught."""
+    bat = Battery(capacity_kwh=100.0)
+    rec = _make_dummy_record(hour=1, bat_chg=15.0, bat_dis=10.0)
+
+    violations = validate_battery_boundaries([rec], battery=bat)
+    sim_violations = [
+        v for v in violations if v.violation_type == ViolationType.SIMULTANEOUS_CHARGE_DISCHARGE
+    ]
+    assert len(sim_violations) == 1
+    assert sim_violations[0].actual_value == 10.0
+    assert "Simultaneous charge" in sim_violations[0].details
+
+
+# =========================================================================
+# CORE-004.3: Golden Fixture & Verification Harness Integration
+# =========================================================================
+
+
+def test_golden_scenario_battery_and_conservation_fully_valid():
+    """Verify that the 48-hour golden fixture satisfies all boundary conditions and invariants."""
+    battery = Battery(capacity_kwh=100.0)
+    records = create_golden_scenario(battery=battery)
+
+    # 1. Assert full verification harness
+    report = run_verification_harness(records, battery=battery)
+    assert report.is_valid
+    assert len(report.conservation_violations) == 0
+    assert len(report.battery_violations) == 0
+    assert report.cumulative_conserved
+    assert report.total_records == 48
+
+    # 2. Test assertion function does not raise
+    assert_simulation_valid(records, battery=battery)
+
+    # 3. Check specific scenario characteristics
+    # Hour 15 has exact zero net-load balance (solar == demand)
+    h15 = records[14]
+    assert h15.hour == 15
+    assert h15.solar_generation_kwh == h15.demand_served_kwh
+    assert h15.grid_import_kwh == 0.0
+    assert h15.battery_charge_kwh == 0.0
+    assert h15.battery_discharge_kwh == 0.0
+
+    # Hours 30-37 simulate outage event
+    outage_records = records[29:37]
+    assert all(not r.grid_available for r in outage_records)
+    assert all(r.active_load_tier == 2 for r in outage_records)
+    assert all(r.unserved_load_kwh == 20.0 for r in outage_records)  # 25 gross - 5 served
+
+
+def test_empty_records_handling():
+    """Verify that empty sequences return valid clean reports without crashing."""
+    assert check_energy_conservation([]) == []
+    bat = Battery(capacity_kwh=100.0)
+    assert validate_battery_boundaries([], battery=bat) == []
+
+    report = run_verification_harness([])
+    assert report.is_valid
+    assert report.total_records == 0
+    assert report.max_residual_kwh == 0.0
```
