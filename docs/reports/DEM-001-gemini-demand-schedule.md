# Task Report: DEM-001 — Equipment Load & Occupancy Schedule Model

**Date:** 2026-10-21  
**Agent:** gemini  
**Task ID:** DEM-001  
**Status:** done  
**Commit:** `537d47d` (feat(DEM-001): implement academic schedule and diurnal non-cooling demand model)  
**Patch File:** `patch/DEM-001-gemini-demand-schedule.patch`  

---

## 1. Executive Summary

Task DEM-001 implements the bottom-up academic schedule engine and diurnal non-cooling electrical demand model for the CCIS facility, replacing the placeholder static occupancy profile from Phase 1 with a fully auditable, physics-grounded formulation conforming strictly to `docs/context/phase2-interface-contract.md` and recorded in decision `[D-27]`.

The implementation delivers two core sub-models:
1. **Academic Calendar & Occupancy Engine (`src/ccis_sim/demand/schedule.py`):** Models Philippine state-university academic calendars (Mariano Marcos State University baseline) spanning Semesters 1 and 2, semestral/winter and summer breaks, and gazetted national regular/special holidays for weather fixture years 2016 and 2019. Produces hourly operational flags and occupancy profiles ($[0.0, 1.0]$) accounting for lecture/lab peaks, lunch dips, Saturday NSTP sessions, and break weekday administrative presence.
2. **Diurnal Non-Cooling Demand Aggregation (`src/ccis_sim/demand/non_cooling.py`):** Evaluates non-cooling electrical equipment (`item.is_cooling == False`) across priority tiers 1 to 3 from `EquipmentAudit`. Crucially, it resolves the unoccupied baseload requirement (10% of daytime peak, or 6.0659 kW) without double-counting continuous 24/7 loads (3.4410 kW), allocating the residual 2.6249 kW standby margin dynamically to Tier 3 sheddable plug loads. Cooling demand is completely decoupled and deferred to DEM-002.

All 23 new unit tests pass cleanly, expanding the full test suite from 138 to 161 passed tests with zero regressions.

---

## 2. Implementation Details

### 2.1 Changes Made

- `src/ccis_sim/demand/schedule.py`:
  - Implemented `AcademicCalendar` dataclass parameterized by semester dates, holiday sets, and skeleton administrative break ratios. Codified historical statutory holidays for 2016 (Proclamation No. 1105/1107) and 2019 (Proclamation No. 555) as well as recurring national holidays.
  - Implemented `build_occupancy_schedule(timestamps: pd.Series, *, calendar: AcademicCalendar | None = None) -> OccupancySchedule` returning 8,760-hour arrays for `occupancy_fraction`, `is_class_day`, `is_break`, and `is_holiday`.
- `src/ccis_sim/demand/non_cooling.py`:
  - Implemented `compute_non_cooling_demand(schedule: OccupancySchedule, audit: EquipmentAudit, building: Building) -> TieredDemand`.
  - Disaggregates equipment into continuous 24/7 items (exit signs, fire alarms, CCTV, stairwell, IDF switches, core routers) and diurnal occupancy-scaled items.
  - Computes daytime peak non-cooling demand ($P_{\text{peak}} = 60.6590\text{ kW}$) and enforces the 10% baseload rule ($P_{\text{unocc}} = 6.0659\text{ kW}$) without double-counting continuous loads, transitioning residual standby power $(1 - f) \times 2.6249\text{ kW}$ into active load as occupancy rises.
- `src/ccis_sim/demand/__init__.py`:
  - Exported `AcademicCalendar`, `build_occupancy_schedule`, and `compute_non_cooling_demand`.
- `tests/test_demand_schedule.py`:
  - 13 comprehensive unit tests verifying keyword-only signature conformance, array dtypes, boundary conditions $[0.0, 1.0]$, weekday diurnal profiles, Saturday sessions, Sunday closures, holiday suppression, DST-free UTC+8 continuity, leap-year handling (2016), determinism, and input validation.
- `tests/test_non_cooling_demand.py`:
  - 10 unit tests verifying contract signature conformance, tier sum conservation ($\sum \text{Tier}_i \equiv \text{Gross}$), exact 10% baseload across nights/Sundays/holidays, no double-counting of continuous loads, Tier 1 constancy (1.215 kW), Tier 2/3 dynamic ranges, class-day demand dominance over holidays, exclusion of AC equipment, and determinism.
- `docs/decisions/decision-log.md`:
  - Appended decision `[D-27]` documenting academic calendar parameters, occupancy fractions, bottom-up demand aggregation, and baseload double-counting avoidance.
- `docs/tasks/status.md`:
  - Marked DEM-001, DEM-001.1, DEM-001.2, DEM-001.3, and DEM-001.4 as `done` linked to this report.

### 2.2 Conformance to Specifications & Decisions

- **Contract Conformance (`docs/context/phase2-interface-contract.md`):** Signatures for `build_occupancy_schedule` and `compute_non_cooling_demand` match the contract verbatim, taking keyword-only `calendar` and returning immutable `OccupancySchedule` and `TieredDemand` instances.
- **Priority Tiering (`[D-10]`):** Loads map directly to Tiers 1 (life-safety), 2 (essential IT/admin), and 3 (discretionary computing and lighting).
- **Decoupled Cooling & Calibration:** AC cooling is completely omitted (reserved for DEM-002); no billing calibration multipliers were applied (reserved for DEM-002.4 / INT-001).

---

## 3. Verification & Test Evidence

### 3.1 Test Execution

Command executed:
```bash
pytest -v -p no:sugar --color=no
```

**Results:**
- Tests passed: 161
- Tests failed: 0
- Tests skipped: 0

Verbatim test runner output:
```text
============================= test session starts ==============================
platform linux -- Python 3.14.8, pytest-9.1.1, pluggy-1.7.0 -- /usr/bin/python
cachedir: .pytest_cache
hypothesis profile 'default'
rootdir: /home/lukexodus/projects/ccis-heat-load-backup-sim-DEM-001
configfile: pyproject.toml
testpaths: tests
plugins: instafail-0.5.0, case-1.5.3, requests-mock-1.12.1, cov-7.1.0, typeguard-4.6.0, anyio-4.15.1, platformdirs-4.13.0, hypothesis-6.169.0, inline-snapshot-0.36.0, time-machine-3.5.1
collecting ... collecting 0 items                                                             collecting 139 items                                                           collected 161 items                                                            

tests/test_baseline_smoke.py::test_baseline_simulation_record_count_and_hours PASSED [  0%]
tests/test_baseline_smoke.py::test_baseline_simulation_dispatch_invariants PASSED [  1%]
tests/test_baseline_smoke.py::test_baseline_simulation_determinism PASSED [  1%]
tests/test_baseline_smoke.py::test_baseline_simulation_passes_verification_harness PASSED [  2%]
tests/test_baseline_smoke.py::test_baseline_negative_control_single_hour_violation_caught PASSED [  3%]
tests/test_baseline_smoke.py::test_baseline_negative_control_cumulative_drift_caught PASSED [  3%]
tests/test_baseline_smoke.py::test_baseline_headline_metrics_committed_values PASSED [  4%]
tests/test_baseline_smoke.py::test_climate_sensitivity_2016_hot_year_versus_2019 PASSED [  4%]
tests/test_conservation_checker.py::test_golden_scenario_conservation_passes PASSED [  5%]
tests/test_conservation_checker.py::test_deliberate_hourly_residual_violation_caught PASSED [  6%]
tests/test_conservation_checker.py::test_cumulative_drift_catches_small_consistent_bias PASSED [  6%]
tests/test_conservation_checker.py::test_cumulative_tolerance_computation PASSED [  7%]
tests/test_conservation_checker.py::test_battery_negative_soc_caught PASSED [  8%]
tests/test_conservation_checker.py::test_battery_exceeds_capacity_caught PASSED [  8%]
tests/test_conservation_checker.py::test_battery_min_soc_floor_normal_vs_emergency PASSED [  9%]
tests/test_conservation_checker.py::test_battery_charge_c_rate_exceeded_caught PASSED [  9%]
tests/test_conservation_checker.py::test_battery_discharge_c_rate_exceeded_caught PASSED [ 10%]
tests/test_conservation_checker.py::test_simultaneous_charge_and_discharge_caught PASSED [ 11%]
tests/test_conservation_checker.py::test_golden_scenario_battery_and_conservation_fully_valid PASSED [ 11%]
tests/test_conservation_checker.py::test_empty_records_handling PASSED   [ 12%]
tests/test_conservation_checker.py::test_soc_continuity_golden_scenario_passes PASSED [ 13%]
tests/test_conservation_checker.py::test_soc_continuity_teleport_violation_caught PASSED [ 13%]
tests/test_conservation_checker.py::test_soc_continuity_zero_capacity_skipped PASSED [ 14%]
tests/test_conservation_checker.py::test_non_finite_value_caught_in_conservation PASSED [ 14%]
tests/test_conservation_checker.py::test_non_finite_value_caught_in_battery_boundaries PASSED [ 15%]
tests/test_conservation_checker.py::test_solar_flow_balance_violation_caught PASSED [ 16%]
tests/test_conservation_checker.py::test_demand_flow_balance_violation_caught PASSED [ 16%]
tests/test_conservation_checker.py::test_hourly_record_signed_residual_property PASSED [ 17%]
tests/test_conservation_checker.py::test_soc_continuity_idle_loss_passes PASSED [ 18%]
tests/test_conservation_checker.py::test_soc_continuity_excessive_idle_loss_fails PASSED [ 18%]
tests/test_conservation_checker.py::test_soc_continuity_higher_than_ideal_recursion_fails PASSED [ 19%]
tests/test_conservation_checker.py::test_soc_cumulative_drift_bias_trips PASSED [ 19%]
tests/test_core_models.py::test_models_immutability PASSED               [ 20%]
tests/test_core_models.py::test_building_archetype_room_count PASSED     [ 21%]
tests/test_core_models.py::test_building_invalid_parameters PASSED       [ 21%]
tests/test_core_models.py::test_solar_array_scenario_capacities[0.0] PASSED [ 22%]
tests/test_core_models.py::test_solar_array_scenario_capacities[50.0] PASSED [ 22%]
tests/test_core_models.py::test_solar_array_scenario_capacities[100.0] PASSED [ 23%]
tests/test_core_models.py::test_solar_array_scenario_capacities[200.0] PASSED [ 24%]
tests/test_core_models.py::test_solar_array_invalid PASSED               [ 24%]
tests/test_core_models.py::test_battery_scenario_capacities_and_properties[0.0] PASSED [ 25%]
tests/test_core_models.py::test_battery_scenario_capacities_and_properties[50.0] PASSED [ 26%]
tests/test_core_models.py::test_battery_scenario_capacities_and_properties[100.0] PASSED [ 26%]
tests/test_core_models.py::test_battery_scenario_capacities_and_properties[200.0] PASSED [ 27%]
tests/test_core_models.py::test_battery_invalid_parameters PASSED        [ 27%]
tests/test_core_models.py::test_grid_outage_parameters PASSED            [ 28%]
tests/test_core_models.py::test_inverter_parameters PASSED               [ 29%]
tests/test_core_models.py::test_system_parameters_defaults PASSED       [ 29%]
tests/test_core_models.py::test_battery_step_result_model PASSED         [ 30%]
tests/test_core_models.py::test_hourly_record_total_demand_property PASSED [ 31%]
tests/test_core_models.py::test_hourly_record_residual_property PASSED   [ 31%]
tests/test_core_models.py::test_load_tier_enum PASSED                    [ 32%]
tests/test_demand_schedule.py::test_schedule_contract_signature_conformance PASSED [ 32%]
tests/test_demand_schedule.py::test_schedule_array_lengths_and_types PASSED [ 33%]
tests/test_demand_schedule.py::test_schedule_occupancy_bounds PASSED     [ 34%]
tests/test_demand_schedule.py::test_schedule_weekday_diurnal_profile PASSED [ 34%]
tests/test_demand_schedule.py::test_schedule_saturday_diurnal_profile PASSED [ 35%]
tests/test_demand_schedule.py::test_schedule_sunday_building_closure PASSED [ 36%]
tests/test_demand_schedule.py::test_schedule_holiday_on_weekday PASSED   [ 36%]
tests/test_demand_schedule.py::test_schedule_break_week_admin_occupancy PASSED [ 37%]
tests/test_demand_schedule.py::test_schedule_dst_free_timezone PASSED    [ 37%]
tests/test_demand_schedule.py::test_schedule_leap_year_2016 PASSED      [ 38%]
tests/test_demand_schedule.py::test_schedule_determinism PASSED          [ 39%]
tests/test_demand_schedule.py::test_schedule_invalid_empty_timestamps PASSED [ 39%]
tests/test_demand_schedule.py::test_academic_calendar_validation PASSED  [ 40%]
tests/test_equipment_audit.py::test_audit_csv_fixture_loads_successfully PASSED [ 40%]
tests/test_equipment_audit.py::test_audit_total_connected_load_plausibility PASSED [ 41%]
tests/test_equipment_audit.py::test_audit_tier_classification_coverage PASSED [ 42%]
tests/test_equipment_audit.py::test_audit_room_archetype_coverage PASSED [ 42%]
tests/test_equipment_audit.py::test_audit_validation_passes_cleanly PASSED [ 43%]
tests/test_equipment_audit.py::test_cooling_equipment_identification PASSED [ 44%]
tests/test_equipment_audit.py::test_duty_cycle_effect_on_daily_energy PASSED [ 44%]
tests/test_equipment_audit.py::test_summary_by_room_type PASSED          [ 45%]
tests/test_equipment_audit.py::test_audit_load_nonexistent_file_raises PASSED [ 45%]
tests/test_interfaces.py::test_tiered_demand_immutability_and_validation PASSED [ 46%]
tests/test_interfaces.py::test_tiered_demand_gross_and_at_methods PASSED [ 47%]
tests/test_interfaces.py::test_occupancy_schedule_bounds_and_lengths PASSED [ 47%]
tests/test_interfaces.py::test_outage_schedule_validation_and_methods PASSED [ 48%]
tests/test_interfaces.py::test_battery_step_result_validation PASSED     [ 49%]
tests/test_interfaces.py::test_battery_step_result_net_stored_and_delivered PASSED [ 49%]
tests/test_interfaces.py::test_shed_result_invariants PASSED             [ 50%]
tests/test_interfaces.py::test_shed_result_conservation_violation_raises PASSED [ 50%]
tests/test_interfaces.py::test_all_dataclasses_frozen PASSED             [ 51%]
tests/test_load_shedding.py::test_shed_result_conservation_invariant_helper PASSED [ 52%]
tests/test_load_shedding.py::test_compute_tier_audit_shares_values PASSED [ 52%]
tests/test_load_shedding.py::test_grid_available_serves_all_tiers PASSED  [ 53%]
tests/test_load_shedding.py::test_outage_instant_tier3_shedding_above_threshold PASSED [ 54%]
tests/test_load_shedding.py::test_outage_exact_threshold_boundary_serves_tier2 PASSED [ 54%]
tests/test_load_shedding.py::test_outage_below_threshold_sheds_tier2 PASSED [ 55%]
tests/test_load_shedding.py::test_custom_tier2_shed_soc_fraction PASSED   [ 55%]
tests/test_load_shedding.py::test_parametric_battery_capacities_and_shed_invariants[0.0] PASSED [ 56%]
tests/test_load_shedding.py::test_parametric_battery_capacities_and_shed_invariants[50.0] PASSED [ 57%]
tests/test_load_shedding.py::test_parametric_battery_capacities_and_shed_invariants[100.0] PASSED [ 57%]
tests/test_load_shedding.py::test_parametric_battery_capacities_and_shed_invariants[200.0] PASSED [ 58%]
tests/test_load_shedding.py::test_hypothesis_battery_soc_and_demand_conservation_invariant[demand0-True-0.0] PASSED [ 59%]
tests/test_load_shedding.py::test_hypothesis_battery_soc_and_demand_conservation_invariant[demand1-True-10.0] PASSED [ 59%]
tests/test_load_shedding.py::test_hypothesis_battery_soc_and_demand_conservation_invariant[demand2-False-0.0] PASSED [ 60%]
tests/test_load_shedding.py::test_hypothesis_battery_soc_and_demand_conservation_invariant[demand3-False-10.0] PASSED [ 60%]
tests/test_load_shedding.py::test_hypothesis_battery_soc_and_demand_conservation_invariant[demand4-False-15.0] PASSED [ 61%]
tests/test_load_shedding.py::test_hypothesis_battery_soc_and_demand_conservation_invariant[demand0-False-20.0] PASSED [ 62%]
tests/test_load_shedding.py::test_hypothesis_battery_soc_and_demand_conservation_invariant[demand1-False-25.0] PASSED [ 62%]
tests/test_load_shedding.py::test_hypothesis_battery_soc_and_demand_conservation_invariant[demand2-False-50.0] PASSED [ 63%]
tests/test_load_shedding.py::test_hypothesis_battery_soc_and_demand_conservation_invariant[demand3-False-100.0] PASSED [ 64%]
tests/test_load_shedding.py::test_hypothesis_battery_soc_and_demand_conservation_invariant[demand4-False-15.0] PASSED [ 65%]
tests/test_load_shedding.py::test_harness_subflow_balance_integration PASSED [ 65%]
tests/test_load_shedding.py::test_unserved_tracker_normal_operation_no_outages PASSED [ 66%]
tests/test_load_shedding.py::test_unserved_tracker_multi_hour_outage_with_shortfall PASSED [ 67%]
tests/test_load_shedding.py::test_tracker_catastrophic_shortfall PASSED  [ 67%]
tests/test_load_shedding.py::test_zero_demand_edge_case PASSED           [ 68%]
tests/test_load_shedding.py::test_invalid_arguments_raise_errors PASSED  [ 68%]
tests/test_mock_bills.py::test_generate_12_monthly_bills PASSED          [ 69%]
tests/test_mock_bills.py::test_mock_bill_internal_energy_conservation PASSED [ 70%]
tests/test_mock_bills.py::test_annual_eui_benchmark_conformance PASSED   [ 70%]
tests/test_mock_bills.py::test_committed_fixture_eui_plausibility PASSED [ 71%]
tests/test_mock_bills.py::test_hot_season_cooling_elevation PASSED       [ 72%]
tests/test_mock_bills.py::test_academic_break_reduction PASSED           [ 72%]
tests/test_mock_bills.py::test_csv_save_and_load_roundtrip PASSED        [ 73%]
tests/test_mock_bills.py::test_generator_seed_reproducibility PASSED     [ 73%]
tests/test_non_cooling_demand.py::test_non_cooling_contract_signature_conformance PASSED [ 74%]
tests/test_non_cooling_demand.py::test_non_cooling_tier_sums_equal_gross PASSED [ 75%]
tests/test_non_cooling_demand.py::test_non_cooling_baseload_rule_exact_ten_percent PASSED [ 75%]
tests/test_non_cooling_demand.py::test_non_cooling_no_double_counting_of_continuous_loads PASSED [ 76%]
tests/test_non_cooling_demand.py::test_non_cooling_baseload_across_night_sunday_and_holiday PASSED [ 77%]
tests/test_non_cooling_demand.py::test_non_cooling_tier1_constant_life_safety PASSED [ 77%]
tests/test_non_cooling_demand.py::test_non_cooling_tier2_and_tier3_ranges PASSED [ 78%]
tests/test_non_cooling_demand.py::test_non_cooling_class_day_demand_exceeds_holiday PASSED [ 78%]
tests/test_non_cooling_demand.py::test_non_cooling_ignores_cooling_equipment PASSED [ 79%]
tests/test_non_cooling_demand.py::test_non_cooling_determinism PASSED    [ 80%]
tests/test_smoke.py::test_package_version PASSED                         [ 80%]
tests/test_smoke.py::test_submodules_importable[ccis_sim.core] PASSED    [ 81%]
tests/test_smoke.py::test_submodules_importable[ccis_sim.demand] PASSED  [ 81%]
tests/test_smoke.py::test_submodules_importable[ccis_sim.solar] PASSED   [ 82%]
tests/test_smoke.py::test_submodules_importable[ccis_sim.battery] PASSED [ 83%]
tests/test_smoke.py::test_submodules_importable[ccis_sim.outage] PASSED  [ 83%]
tests/test_smoke.py::test_submodules_importable[ccis_sim.integration] PASSED [ 84%]
tests/test_smoke.py::test_submodules_importable[ccis_sim.decision] PASSED [ 85%]
tests/test_smoke.py::test_numpy_environment_sanity PASSED                [ 85%]
tests/test_smoke.py::test_scipy_environment_sanity PASSED                [ 86%]
tests/test_weather_ingest.py::test_client_defaults PASSED                [ 86%]
tests/test_weather_ingest.py::test_client_url_construction PASSED        [ 87%]
tests/test_weather_ingest.py::test_client_raw_io_roundtrip PASSED        [ 88%]
tests/test_weather_ingest.py::test_client_network_failure PASSED         [ 88%]
tests/test_weather_ingest.py::test_parse_hourly_json_lst PASSED          [ 89%]
tests/test_weather_ingest.py::test_parse_hourly_json_utc PASSED          [ 90%]
tests/test_weather_ingest.py::test_parse_daily_json PASSED               [ 90%]
tests/test_weather_ingest.py::test_parse_malformed_json PASSED           [ 91%]
tests/test_weather_ingest.py::test_sanitizer_filter_sentinels PASSED     [ 91%]
tests/test_weather_ingest.py::test_sanitizer_interpolate_missing PASSED  [ 92%]
tests/test_weather_ingest.py::test_sanitizer_timezone_alignment_and_midnight_boundary PASSED [ 93%]
tests/test_weather_ingest.py::test_sanitizer_psychrometric_validation PASSED [ 93%]
tests/test_weather_ingest.py::test_sanitizer_standardize_annual_hourly PASSED [ 94%]
tests/test_weather_ingest.py::test_daily_disaggregation_energy_conservation PASSED [ 95%]
tests/test_weather_ingest.py::test_daily_disaggregation_solar_geometry_night_zero PASSED [ 95%]
tests/test_weather_ingest.py::test_daily_disaggregation_temperature_profile PASSED [ 96%]
tests/test_weather_ingest.py::test_daily_disaggregation_relative_humidity_coupling PASSED [ 96%]
tests/test_weather_ingest.py::test_daily_disaggregate_dataframe PASSED   [ 97%]
tests/test_weather_ingest.py::test_committed_fixtures_structure[2016] PASSED [ 98%]
tests/test_weather_ingest.py::test_committed_fixtures_structure[2019] PASSED [ 98%]
tests/test_weather_ingest.py::test_committed_fixtures_climate_comparison PASSED [ 99%]
tests/test_weather_ingest.py::test_raw_files_exist PASSED                [100%]

============================= 161 passed in 18.39s =============================
```

### 3.2 Edge Cases & Negative Testing

1. **Holiday on Regular Class Day:** Tested Maundy Thursday 2019-04-18 (weekday during Semester 2); confirmed `is_holiday == True`, `is_class_day == False`, and all 24 hours produce zero occupancy and exact 10% baseload.
2. **Double-Counting Prevention:** Verified that continuous 24/7 loads (3.4410 kW) are not added on top of 10% peak baseload (6.0659 kW), which would yield 9.5069 kW. Baseload is strictly 6.0659 kW.
3. **Empty Timestamps Guard:** Calling `build_occupancy_schedule([])` raises `ValueError`.
4. **Invalid Ratios:** `AcademicCalendar` rejects negative or $> 1.0$ ratios.
5. **Determinism:** Pure function execution confirmed bitwise identical arrays across repeat calls.

---

## 4. Decisions Recorded

Added to `docs/decisions/decision-log.md`:

- **[D-27]**: Academic Calendar Conventions, Bottom-Up Non-Cooling Demand Aggregation, and Baseload Double-Counting Prevention.
  - Documents academic calendar boundaries (Sem 1: Aug 15 – Dec 15; Sem 2: Jan 15 – May 25; Midyear: May 26 – Aug 14; Winter: Dec 16 – Jan 14).
  - Codifies Philippine regular and special non-working statutory holidays for weather fixture years 2016 and 2019.
  - Details bottom-up demand aggregation and non-cooling daytime peak of 60.6590 kW.
  - Locks the unoccupied baseload rule (10% of daytime peak = 6.0659 kW) without double-counting continuous loads by assigning the residual 2.6249 kW standby load to Tier 3 sheddable plug loads.
  - Formalizes decoupling from cooling loads (DEM-002) and billing calibration (DEM-002.4 / INT-001).

---

## 5. Unified Git Diff

```diff
diff --git a/docs/decisions/decision-log.md b/docs/decisions/decision-log.md
index 52af966..424286b 100644
--- a/docs/decisions/decision-log.md
+++ b/docs/decisions/decision-log.md
@@ -221,9 +221,41 @@ This file exists so that across API-credit-limited handoffs between APC AI insta
      $$0 - \epsilon \le \text{SoC}_{t, \text{ideal}} - \text{SoC}_t \le \Delta E_{\text{idle, max}} + \epsilon$$
      where $\Delta E_{\text{idle, max}} = \left(\frac{C_{\text{bat}} \cdot r_{\text{self}}}{730} + P_{\text{tare}}\right) \Delta t$, based on 730 hours per nominal month ($8,760\text{ h} / 12$). Stored chemical SoC may never exceed the lossless ideal recursion ($SoC_t \le SoC_{t, \text{ideal}} + \epsilon$). When idle loss parameters are zero, the formulation collapses identically to the bilateral tolerance of [D-25].
   5. **Cumulative Continuity Drift Invariant:** Accumulated step differences $\sum (\text{SoC}_{\text{ideal}} - \text{SoC})$ across $N$ evaluated hours must not exceed total allowed idle loss plus the statistical cumulative tolerance $\max(\epsilon, \sqrt{N}\epsilon)$ per [D-21]. Unaccounted cumulative leakage or upward drift trips `ViolationType.SOC_CUMULATIVE_DRIFT`.
-- **Reasoning:** Establishes unambiguous API contracts across all eight parallel Phase 2 sub-models to prevent divergence, while closing physical verification blind spots for standby battery self-discharge and cumulative SoC drift prior to BAT-001/002.
+- **Reasoning:** Establishes unambiguous API contracts across all eight parallel Phase 2 sub-models to prevent divergence, while closing physical verification blind spots for standby battery self-discharge and cumulative SoC drift prior to BAT-001/002.  
 - **Affects:** `CORE-006`, `DEM-001`, `DEM-002`, `SOL-001`, `SOL-002`, `BAT-001`, `BAT-002`, `OUT-001`, `OUT-002`, `INT-001`, `INT-003`.
 
+**[D-27]** Academic Calendar Conventions, Bottom-Up Non-Cooling Demand Aggregation, and Baseload Double-Counting Prevention.  
+- **Date / Session:** 2026-10-21  
+- **Decision:**  
+  1. **Academic Calendar Baseline Model (`AcademicCalendar`):**
+     - Adopted academic calendar boundaries patterned on Mariano Marcos State University (MMSU) Batac campus operations:
+       - First Semester: August 15 to December 15 (18 weeks).
+       - Winter / Semestral Break: December 16 to January 14.
+       - Second Semester: January 15 to May 25 (18 weeks).
+       - Summer / Midyear Break: May 26 to August 14.
+     - Codified Philippine regular and special non-working statutory holidays for weather fixture years 2019 (Proclamation No. 555) and 2016 (Proclamation No. 1105 / 1107), including movable feasts (Holy Week, Eid'l Fitr, Eid'l Adha) and National Heroes Day.
+  2. **Hourly Occupancy Profiles (`build_occupancy_schedule`):**
+     - Class Weekdays (Mon-Fri): 07:00 (0.20 early prep), 08:00–12:00 (1.00 lecture/lab peak), 12:00–13:00 (0.60 lunch dip), 13:00–18:00 (0.95 afternoon classes), 18:00–20:00 (0.30 evening graduate/extension), 20:00–07:00 (0.00 closed).
+     - Class Saturdays: 08:00–12:00 (0.50 morning NSTP/labs), 12:00–13:00 (0.20 lunch dip), 13:00–17:00 (0.30 afternoon labs), 17:00–08:00 (0.00 closed).
+     - Sundays and Gazetted Holidays: 0.00 all 24 hours (facility closed).
+     - Term Break Weekdays: 08:00–12:00 and 13:00–17:00 (0.15 skeleton faculty/admin presence), 12:00–13:00 (0.05 lunch), 17:00–08:00 (0.00 closed).
+  3. **Bottom-Up Non-Cooling Aggregation (`compute_non_cooling_demand`):**
+     - Isolated non-cooling electrical equipment (`item.is_cooling == False`) from `EquipmentAudit`.
+     - Classified equipment into continuous 24/7 loads (`hours_per_day >= 24.0`) and occupancy-driven diurnal loads (`hours_per_day < 24.0`).
+     - Connected non-cooling effective peak is 60.6590 kW (continuous: 3.4410 kW; occupancy peak: 57.2180 kW).
+  4. **Baseload Double-Counting Prevention Rule:**
+     - Target unoccupied non-cooling baseload is 10% of daytime peak ($0.10 \times 60.6590\text{ kW} = 6.0659\text{ kW}$).
+     - Continuous 24/7 equipment already draws 3.4410 kW (Tier 1 life-safety: 1.2150 kW; Tier 2 IT infrastructure: 2.2260 kW).
+     - To prevent double counting continuous loads with the 10% baseload rule, the residual standby margin is defined as $P_{\text{standby}} = \max(0.0, 0.10 \times P_{\text{peak}} - P_{\text{cont, total}}) = 2.6249\text{ kW}$.
+     - This residual represents parasitic standby plug loads (sleep-mode PCs, monitors, troffers, and appliances) and is allocated to Tier 3 (sheddable load).
+     - As occupancy fraction $f$ increases, standby load transitions into active operational load via $(1.0 - f) \times P_{\text{standby}}$.
+     - Resulting gross demand is exactly 6.0659 kW (10% of peak) during all unoccupied hours (nights, Sundays, holidays) and 60.6590 kW at full occupancy, with energy conservation strictly preserved per hour ($\sum \text{Tier}_i = \text{Gross}$).
+  5. **Decoupling from Cooling and Calibration:**
+     - Cooling load calculations are strictly excluded and deferred to DEM-002.
+     - Calibration scaling factors and billing reconciliations are deferred to DEM-002.4 and INT-001.
+- **Reasoning:** Establishes an auditable, physically grounded bottom-up schedule and non-cooling load model without double-counting 24/7 continuous loads, enabling clean integration with OUT-002 tiered shedding and DEM-002 cooling response.  
+- **Affects:** `DEM-001`, `DEM-002`, `OUT-002`, `INT-001`, `INT-002`, `INT-003`.
+
 **[D-34]** Priority-Based Tiered Load Shedding Policy, Low-SoC Threshold Decoupling, and Unserved Energy Tracking Conventions.  
 - **Date / Session:** 2026-10-20  
 - **Decision:**  
diff --git a/docs/tasks/status.md b/docs/tasks/status.md
index 1017ef8..462b083 100644
--- a/docs/tasks/status.md
+++ b/docs/tasks/status.md
@@ -81,11 +81,11 @@ Status: **open**
 
 | ID          | Task                                                                                                 | Status | Notes / Report     |
 | :---------- | :--------------------------------------------------------------------------------------------------- | :----- | :----------------- |
-| **DEM-001** | **Equipment Load & Occupancy Schedule Model**                                                        | `open` |                    |
-| DEM-001.1   | Implement academic schedule engine (classes, breaks, holidays)                                       | `open` | Schedule calendar  |
-| DEM-001.2   | Compute diurnal non-cooling base demand (lighting, IT, plug loads)                                   | `open` | Bottom-up load     |
-| DEM-001.3   | Model unoccupied nighttime baseload (10% of daytime peak)                                            | `open` | Baseload rule      |
-| DEM-001.4   | Write unit tests for equipment aggregation across schedule states                                    | `open` | Test suite         |
+| **DEM-001** | **Equipment Load & Occupancy Schedule Model**                                                        | `done` | [Report](docs/reports/DEM-001-gemini-demand-schedule.md) |
+| DEM-001.1   | Implement academic schedule engine (classes, breaks, holidays)                                       | `done` | Schedule calendar  |
+| DEM-001.2   | Compute diurnal non-cooling base demand (lighting, IT, plug loads)                                   | `done` | Bottom-up load     |
+| DEM-001.3   | Model unoccupied nighttime baseload (10% of daytime peak)                                            | `done` | Baseload rule      |
+| DEM-001.4   | Write unit tests for equipment aggregation across schedule states                                    | `done` | Test suite         |
 | **DEM-002** | **Temperature & Humidity Cooling Response Model**                                                    | `open` |                    |
 | DEM-002.1   | Implement CDD model ($T_{\text{base}} = 24.0^\circ\text{C}$, 4%/°C sensitivity)                      | `open` | Sensible cooling   |
 | DEM-002.2   | Implement latent cooling psychrometric multiplier (+20% humidity)                                    | `open` | Latent load        |
diff --git a/src/ccis_sim/demand/__init__.py b/src/ccis_sim/demand/__init__.py
index 32c1eb6..06584c3 100644
--- a/src/ccis_sim/demand/__init__.py
+++ b/src/ccis_sim/demand/__init__.py
@@ -8,11 +8,25 @@ from ccis_sim.demand.mock_bills import (
     SyntheticBillGenerator,
     SyntheticMonthlyBill,
 )
+from ccis_sim.demand.non_cooling import compute_non_cooling_demand
+from ccis_sim.demand.schedule import (
+    PHILIPPINES_HOLIDAYS_2016,
+    PHILIPPINES_HOLIDAYS_2019,
+    AcademicCalendar,
+    build_occupancy_schedule,
+    get_default_philippine_holidays,
+)
 
 __all__ = [
+    "AcademicCalendar",
     "DEFAULT_ACADEMIC_WEIGHTS",
     "DEFAULT_COOLING_MULTIPLIERS",
     "EquipmentAudit",
     "EquipmentItem",
+    "PHILIPPINES_HOLIDAYS_2016",
+    "PHILIPPINES_HOLIDAYS_2019",
     "SyntheticBillGenerator",
     "SyntheticMonthlyBill",
+    "build_occupancy_schedule",
+    "compute_non_cooling_demand",
+    "get_default_philippine_holidays",
+]
diff --git a/src/ccis_sim/demand/non_cooling.py b/src/ccis_sim/demand/non_cooling.py
new file mode 100644
index 0000000..9df243e
--- /dev/null
+++ b/src/ccis_sim/demand/non_cooling.py
@@ -0,0 +1,93 @@
+"""Diurnal non-cooling electrical demand model for CCIS facility.
+
+Aggregates bottom-up lighting, IT networking, office computing, and plug loads
+across priority tiers 1 to 3 based on the equipment inventory audit and hourly
+occupancy schedules, conforming to:
+- docs/prompts/DEM-001-PROMPT.md
+- docs/context/phase2-interface-contract.md
+- docs/decisions/decision-log.md [D-27]
+"""
+
+from __future__ import annotations
+
+import numpy as np
+
+from ccis_sim.core.interfaces import OccupancySchedule, TieredDemand
+from ccis_sim.core.models import Building
+from ccis_sim.demand.equipment import EquipmentAudit
+
+
+def compute_non_cooling_demand(
+    schedule: OccupancySchedule,
+    audit: EquipmentAudit,
+    building: Building,
+) -> TieredDemand:
+    r"""Compute hourly non-cooling electrical demand decomposed across priority tiers 1 to 3.
+
+    Conforms strictly to docs/context/phase2-interface-contract.md:
+    `compute_non_cooling_demand(schedule: OccupancySchedule, audit: EquipmentAudit, building: Building) -> TieredDemand`
+
+    Load aggregation logic ([ASSUMPTION / [D-27]]):
+    1. Filter out all cooling equipment (`item.is_cooling == False`); cooling response is
+       exclusively evaluated in DEM-002.
+    2. Classify items into:
+       - Continuous 24/7 loads (`hours_per_day >= 24.0`): constant uninterrupted operation
+         (e.g., Tier 1 life-safety signs/alarms/CCTV/stairwell; Tier 2 IDF switches and core routers).
+       - Occupancy-driven loads (`hours_per_day < 24.0`): scaled linearly with hourly
+         `occupancy_fraction` (e.g., PC labs, classroom lighting troffers, faculty workstations).
+    3. Calculate total daytime peak non-cooling demand:
+       $P_{\text{peak}} = P_{\text{cont, total}} + P_{\text{occ\_peak, total}}$.
+    4. Unoccupied Baseload Rule without Double-Counting:
+       Target unoccupied non-cooling load is 10% of daytime peak ($0.10 \times P_{\text{peak}}$).
+       Continuous 24/7 items already draw $P_{\text{cont, total}}$. The residual standby margin:
+       $P_{\text{standby}} = \max(0.0, 0.10 \times P_{\text{peak}} - P_{\text{cont, total}})$.
+       This residual represents parasitic standby plug loads (quiescent draw of sleep-state PCs,
+       monitors, chargers, and appliances) and is allocated to Tier 3 (sheddable load).
+       As occupancy rises ($f \in [0, 1]$), equipment wakes to operational load, and standby
+       transitions to active draw: $(1.0 - f) \times P_{\text{standby}}$.
+    5. Hourly Tier Composition:
+       - Tier 1: $P_{\text{cont}, 1} + f \times P_{\text{occ\_peak}, 1}$
+       - Tier 2: $P_{\text{cont}, 2} + f \times P_{\text{occ\_peak}, 2}$
+       - Tier 3: $P_{\text{cont}, 3} + f \times P_{\text{occ\_peak}, 3} + (1.0 - f) \times P_{\text{standby}}$
+
+    Args:
+        schedule: OccupancySchedule containing hourly occupancy_fraction array.
+        audit: EquipmentAudit inventory containing audited building loads.
+        building: Building envelope definition.
+
+    Returns:
+        TieredDemand instance with tier1_kwh, tier2_kwh, tier3_kwh arrays of length N.
+    """
+    n = len(schedule)
+    if n == 0:
+        raise ValueError("OccupancySchedule must not be empty.")
+
+    # Filter for non-cooling electrical equipment
+    non_cooling_items = [item for item in audit.items if not item.is_cooling]
+
+    # Pre-accumulate continuous loads and full-occupancy peak loads per tier
+    # Units: kW = kWh/h at Δt = 1.0 h
+    p_cont = {1: 0.0, 2: 0.0, 3: 0.0}
+    p_occ_peak = {1: 0.0, 2: 0.0, 3: 0.0}
+
+    for item in non_cooling_items:
+        # Effective kW accounts for duty cycle diversity during operational hours
+        effective_kw = item.count * item.rated_kw * item.duty_cycle
+        if item.hours_per_day >= 24.0:
+            p_cont[item.tier] += effective_kw
+        else:
+            p_occ_peak[item.tier] += effective_kw
+
+    p_cont_total = p_cont[1] + p_cont[2] + p_cont[3]
+    p_occ_total = p_occ_peak[1] + p_occ_peak[2] + p_occ_peak[3]
+    p_peak = p_cont_total + p_occ_total
+
+    # Baseload target is 10% of daytime peak non-cooling demand per DEM-001.3
+    p_unoccupied_target = 0.10 * p_peak
+
+    # Avoid double-counting: subtract continuous 24/7 loads from 10% baseload target
+    p_standby_residual = max(0.0, p_unoccupied_target - p_cont_total)
+
+    f_occ = schedule.occupancy_fraction
+
+    # Vectorized hourly tier load generation
+    tier1_arr = np.full(n, p_cont[1], dtype=np.float64)
+    if p_occ_peak[1] > 0.0:
+        tier1_arr += f_occ * p_occ_peak[1]
+
+    tier2_arr = p_cont[2] + f_occ * p_occ_peak[2]
+    tier3_arr = p_cont[3] + f_occ * p_occ_peak[3] + (1.0 - f_occ) * p_standby_residual
+
+    return TieredDemand(
+        tier1_kwh=tier1_arr,
+        tier2_kwh=tier2_arr,
+        tier3_kwh=tier3_arr,
+    )
diff --git a/src/ccis_sim/demand/schedule.py b/src/ccis_sim/demand/schedule.py
new file mode 100644
index 0000000..8c8db38
--- /dev/null
+++ b/src/ccis_sim/demand/schedule.py
@@ -0,0 +1,248 @@
+"""Academic calendar and building occupancy schedule engine.
+
+Generates hourly occupancy fraction profiles and operational state flags
+(class day, break, holiday) for the CCIS building conforming to:
+- docs/prompts/DEM-001-PROMPT.md
+- docs/context/phase2-interface-contract.md
+- docs/decisions/decision-log.md [D-27]
+"""
+
+from __future__ import annotations
+
+import datetime
+from dataclasses import dataclass, field
+from typing import Sequence
+
+import numpy as np
+import pandas as pd
+
+from ccis_sim.core.interfaces import OccupancySchedule
+
+
+# ==============================================================================
+# Philippine Statutory Holidays (Fixture Years 2016 and 2019)
+# Reference: Proclamation No. 555 (2019) and Proclamation No. 1105 / 1107 (2016)
+# ==============================================================================
+
+# Philippine regular and special non-working holidays for calendar year 2019
+PHILIPPINES_HOLIDAYS_2019: frozenset[datetime.date] = frozenset(
+    [
+        datetime.date(2019, 1, 1),   # New Year's Day (Regular)
+        datetime.date(2019, 2, 5),   # Chinese Lunar New Year (Special)
+        datetime.date(2019, 2, 25),  # EDSA People Power Revolution (Special)
+        datetime.date(2019, 4, 9),   # Araw ng Kagitingan / Day of Valor (Regular)
+        datetime.date(2019, 4, 18),  # Maundy Thursday (Regular)
+        datetime.date(2019, 4, 19),  # Good Friday (Regular)
+        datetime.date(2019, 4, 20),  # Black Saturday (Special)
+        datetime.date(2019, 5, 1),   # Labor Day (Regular)
+        datetime.date(2019, 6, 5),   # Eid'l Fitr (Regular, Proclamation 729)
+        datetime.date(2019, 6, 12),  # Independence Day (Regular)
+        datetime.date(2019, 8, 12),  # Eid'l Adha (Regular, Proclamation 789)
+        datetime.date(2019, 8, 21),  # Ninoy Aquino Day (Special)
+        datetime.date(2019, 8, 26),  # National Heroes Day (Regular, last Mon of Aug)
+        datetime.date(2019, 11, 1),  # All Saints' Day (Special)
+        datetime.date(2019, 11, 2),  # All Souls' Day (Special)
+        datetime.date(2019, 11, 30), # Bonifacio Day (Regular)
+        datetime.date(2019, 12, 8),  # Feast of the Immaculate Conception (Special)
+        datetime.date(2019, 12, 24), # Christmas Eve (Special)
+        datetime.date(2019, 12, 25), # Christmas Day (Regular)
+        datetime.date(2019, 12, 30), # Rizal Day (Regular)
+        datetime.date(2019, 12, 31), # Last Day of the Year (Special)
+    ]
+)
+
+# Philippine regular and special non-working holidays for calendar year 2016 (leap year)
+PHILIPPINES_HOLIDAYS_2016: frozenset[datetime.date] = frozenset(
+    [
+        datetime.date(2016, 1, 1),   # New Year's Day (Regular)
+        datetime.date(2016, 1, 2),   # Additional special non-working day
+        datetime.date(2016, 2, 8),   # Chinese New Year (Special)
+        datetime.date(2016, 2, 25),  # EDSA Revolution Anniversary (Special)
+        datetime.date(2016, 3, 24),  # Maundy Thursday (Regular)
+        datetime.date(2016, 3, 25),  # Good Friday (Regular)
+        datetime.date(2016, 3, 26),  # Black Saturday (Special)
+        datetime.date(2016, 4, 9),   # Araw ng Kagitingan (Regular)
+        datetime.date(2016, 5, 1),   # Labor Day (Regular)
+        datetime.date(2016, 5, 9),   # National Election Day (Special)
+        datetime.date(2016, 6, 12),  # Independence Day (Regular)
+        datetime.date(2016, 7, 6),   # Eid'l Fitr (Regular)
+        datetime.date(2016, 8, 21),  # Ninoy Aquino Day (Special)
+        datetime.date(2016, 8, 29),  # National Heroes Day (Regular)
+        datetime.date(2016, 9, 12),  # Eid'l Adha (Regular)
+        datetime.date(2016, 10, 31), # Additional special non-working day
+        datetime.date(2016, 11, 1),  # All Saints' Day (Special)
+        datetime.date(2016, 11, 30), # Bonifacio Day (Regular)
+        datetime.date(2016, 12, 24), # Special non-working day
+        datetime.date(2016, 12, 25), # Christmas Day (Regular)
+        datetime.date(2016, 12, 26), # Additional special non-working day
+        datetime.date(2016, 12, 30), # Rizal Day (Regular)
+        datetime.date(2016, 12, 31), # Last Day of the Year (Special)
+    ]
+)
+
+
+def get_default_philippine_holidays(year: int) -> frozenset[datetime.date]:
+    """Return statutory holiday set for specified calendar year.
+
+    For fixture years 2019 and 2016, returns exact historical gazetted holidays
+    (including lunar/movable feasts Eid'l Fitr, Eid'l Adha, and Holy Week).
+    For other years, computes fixed-date annual holidays plus National Heroes Day.
+    """
+    if year == 2019:
+        return PHILIPPINES_HOLIDAYS_2019
+    if year == 2016:
+        return PHILIPPINES_HOLIDAYS_2016
+
+    # Fixed-date statutory holidays
+    fixed = {
+        datetime.date(year, 1, 1),    # New Year's Day
+        datetime.date(year, 2, 25),   # EDSA Revolution
+        datetime.date(year, 4, 9),    # Araw ng Kagitingan
+        datetime.date(year, 5, 1),    # Labor Day
+        datetime.date(year, 6, 12),   # Independence Day
+        datetime.date(year, 8, 21),   # Ninoy Aquino Day
+        datetime.date(year, 11, 1),   # All Saints' Day
+        datetime.date(year, 11, 30),  # Bonifacio Day
+        datetime.date(year, 12, 8),   # Immaculate Conception
+        datetime.date(year, 12, 24),  # Christmas Eve
+        datetime.date(year, 12, 25),  # Christmas Day
+        datetime.date(year, 12, 30),  # Rizal Day
+        datetime.date(year, 12, 31),  # New Year's Eve
+    }
+
+    # National Heroes Day: last Monday of August
+    last_day_august = datetime.date(year, 8, 31)
+    offset = (last_day_august.weekday() - 0) % 7  # Monday is weekday 0
+    nat_heroes_day = datetime.date(year, 8, 31 - offset)
+    fixed.add(nat_heroes_day)
+
+    return frozenset(fixed)
+
+
+@dataclass(frozen=True)
+class AcademicCalendar:
+    """Academic calendar boundaries and holiday definitions for Philippine state university.
+
+    Default schedule parameters reflect standard Mariano Marcos State University (MMSU)
+    semester and term break alignments ([ASSUMPTION / [D-27]]):
+    - Semester 1 (Aug 15 - Dec 15): 18-week academic term
+    - Winter / Semestral Break (Dec 16 - Jan 14): semestral vacation and holiday closure
+    - Semester 2 (Jan 15 - May 25): 18-week academic term
+    - Summer / Midyear Break (May 26 - Aug 14): academic vacation, faculty research, midyear maintenance
+
+    Attributes:
+        year: Reference weather year (default 2019).
+        sem1_start: (month, day) for Semester 1 commencement (default (8, 15)).
+        sem1_end: (month, day) for Semester 1 conclusion (default (12, 15)).
+        sem2_start: (month, day) for Semester 2 commencement (default (1, 15)).
+        sem2_end: (month, day) for Semester 2 conclusion (default (5, 25)).
+        holidays: Set of holiday dates; defaults to Philippine national gazetted holidays.
+        break_weekday_admin_ratio: Skeleton faculty/staff occupancy during term break weekdays
+            (default 0.15 per [ASSUMPTION / [D-27]]).
+        break_lunch_ratio: Skeleton staff occupancy during lunch hour on break weekdays
+            (default 0.05 per [ASSUMPTION / [D-27]]).
+    """
+
+    year: int = 2019
+    sem1_start: tuple[int, int] = (8, 15)
+    sem1_end: tuple[int, int] = (12, 15)
+    sem2_start: tuple[int, int] = (1, 15)
+    sem2_end: tuple[int, int] = (5, 25)
+    holidays: frozenset[datetime.date] | None = None
+    break_weekday_admin_ratio: float = 0.15
+    break_lunch_ratio: float = 0.05
+
+    def __post_init__(self) -> None:
+        if self.holidays is None:
+            object.__setattr__(self, "holidays", get_default_philippine_holidays(self.year))
+        else:
+            object.__setattr__(
+                self,
+                "holidays",
+                frozenset(
+                    h if isinstance(h, datetime.date) else pd.to_datetime(h).date()
+                    for h in self.holidays
+                ),
+            )
+
+        if not (0.0 <= self.break_weekday_admin_ratio <= 1.0):
+            raise ValueError(
+                f"break_weekday_admin_ratio must be in [0, 1], got {self.break_weekday_admin_ratio}"
+            )
+        if not (0.0 <= self.break_lunch_ratio <= 1.0):
+            raise ValueError(f"break_lunch_ratio must be in [0, 1], got {self.break_lunch_ratio}")
+
+    def is_holiday(self, d: datetime.date) -> bool:
+        """Check if date is a statutory or special non-working holiday."""
+        return d in self.holidays
+
+    def is_semester(self, d: datetime.date) -> bool:
+        """Check if date falls within regular semester terms (Sem 1 or Sem 2)."""
+        sem1_s = datetime.date(d.year, self.sem1_start[0], self.sem1_start[1])
+        sem1_e = datetime.date(d.year, self.sem1_end[0], self.sem1_end[1])
+        sem2_s = datetime.date(d.year, self.sem2_start[0], self.sem2_start[1])
+        sem2_e = datetime.date(d.year, self.sem2_end[0], self.sem2_end[1])
+
+        return (sem1_s <= d <= sem1_e) or (sem2_s <= d <= sem2_e)
+
+    def is_break(self, d: datetime.date) -> bool:
+        """Check if date falls within academic break (winter or summer break)."""
+        return not self.is_semester(d)
+
+
+def build_occupancy_schedule(
+    timestamps: pd.Series | Sequence[Any],
+    *,
+    calendar: AcademicCalendar | None = None,
+) -> OccupancySchedule:
+    """Build academic building occupancy profile and calendar operational state.
+
+    Conforms strictly to docs/context/phase2-interface-contract.md:
+    `build_occupancy_schedule(timestamps: pd.Series, *, calendar: AcademicCalendar | None = None) -> OccupancySchedule`
+
+    Occupancy fraction conventions ([ASSUMPTION / [D-27]]):
+    - Regular Class Weekdays (Mon-Fri, non-holiday during semester):
+        00:00-07:00: 0.00 (closed)
+        07:00-08:00: 0.20 (early arrival / prep)
+        08:00-12:00: 1.00 (peak morning lecture/labs)
+        12:00-13:00: 0.60 (lunch dip)
+        13:00-18:00: 0.95 (afternoon lecture/labs)
+        18:00-20:00: 0.30 (evening graduate/extension classes)
+        20:00-24:00: 0.00 (closed)
+    - Regular Class Saturdays (Sat, non-holiday during semester):
+        00:00-08:00: 0.00
+        08:00-12:00: 0.50 (morning lab sessions / NSTP)
+        12:00-13:00: 0.20 (lunch dip)
+        13:00-17:00: 0.30 (afternoon lab sessions)
+        17:00-24:00: 0.00
+    - Sundays and Gazetted Holidays:
+        0.00 all hours (building fully closed)
+    - Academic Break Weekdays (Mon-Fri during summer or semestral break, non-holiday):
+        08:00-12:00: break_weekday_admin_ratio (0.15 skeleton faculty/admin presence)
+        12:00-13:00: break_lunch_ratio (0.05 lunch hour)
+        13:00-17:00: break_weekday_admin_ratio (0.15 afternoon office presence)
+        all other hours: 0.00
+    - Academic Break Weekends (Sat-Sun during break):
+        0.00 all hours
+
+    Args:
+        timestamps: Series or sequence of ISO strings, DatetimeIndex, or datetime objects.
+        calendar: AcademicCalendar instance; if None, defaults to AcademicCalendar(year=...).
+
+    Returns:
+        OccupancySchedule container with occupancy_fraction, is_class_day, is_break,
+        and is_holiday numpy arrays of length N.
+    """
+    ts_series = pd.to_datetime(timestamps)
+    n = len(ts_series)
+    if n == 0:
+        raise ValueError("timestamps sequence must not be empty.")
+
+    # Determine reference year from timestamps if calendar not provided
+    if calendar is None:
+        ref_year = int(ts_series[0].year) if hasattr(ts_series, "iloc") else int(ts_series[0].year)
+        cal = AcademicCalendar(year=ref_year)
+    else:
+        cal = calendar
+
+    occ_arr = np.zeros(n, dtype=np.float64)
+    class_day_arr = np.zeros(n, dtype=bool)
+    break_arr = np.zeros(n, dtype=bool)
+    holiday_arr = np.zeros(n, dtype=bool)
+
+    # Convert to Python datetime series for fast component access
+    dt_index = pd.DatetimeIndex(ts_series)
+    dates = dt_index.date
+    hours = dt_index.hour
+    weekdays = dt_index.weekday  # 0=Monday, 5=Saturday, 6=Sunday
+
+    # Precompute unique dates state to vectorize day-level flags
+    unique_dates = np.unique(dates)
+    day_is_holiday: dict[datetime.date, bool] = {d: cal.is_holiday(d) for d in unique_dates}
+    day_is_break: dict[datetime.date, bool] = {d: cal.is_break(d) for d in unique_dates}
+    day_is_sem: dict[datetime.date, bool] = {d: cal.is_semester(d) for d in unique_dates}
+
+    for i in range(n):
+        d = dates[i]
+        h = hours[i]
+        wd = weekdays[i]
+
+        hol = day_is_holiday[d]
+        brk = day_is_break[d]
+        sem = day_is_sem[d]
+
+        holiday_arr[i] = hol
+        break_arr[i] = brk
+
+        # Class day: scheduled semester day, not holiday, not Sunday (Mon-Sat during semester)
+        is_class_d = sem and (not hol) and (wd < 6)
+        class_day_arr[i] = is_class_d
+
+        if hol or wd == 6:
+            # Building closed on holidays and Sundays
+            occ_arr[i] = 0.0
+        elif is_class_d:
+            # Regular semester schedule
+            if wd < 5:
+                # Weekdays (Mon-Fri)
+                if h < 7 or h >= 20:
+                    occ_arr[i] = 0.0
+                elif h == 7:
+                    occ_arr[i] = 0.20
+                elif 8 <= h < 12:
+                    occ_arr[i] = 1.00
+                elif h == 12:
+                    occ_arr[i] = 0.60
+                elif 13 <= h < 18:
+                    occ_arr[i] = 0.95
+                elif 18 <= h < 20:
+                    occ_arr[i] = 0.30
+            else:
+                # Saturday
+                if h < 8 or h >= 17:
+                    occ_arr[i] = 0.0
+                elif 8 <= h < 12:
+                    occ_arr[i] = 0.50
+                elif h == 12:
+                    occ_arr[i] = 0.20
+                elif 13 <= h < 17:
+                    occ_arr[i] = 0.30
+        elif brk:
+            # Term break schedule
+            if wd < 5:
+                # Break weekday: administrative presence
+                if 8 <= h < 12 or 13 <= h < 17:
+                    occ_arr[i] = cal.break_weekday_admin_ratio
+                elif h == 12:
+                    occ_arr[i] = cal.break_lunch_ratio
+                else:
+                    occ_arr[i] = 0.0
+            else:
+                # Break weekend (Sat-Sun)
+                occ_arr[i] = 0.0
+        else:
+            # Fallback for non-class, non-break, non-holiday weekday
+            occ_arr[i] = 0.0
+
+    return OccupancySchedule(
+        occupancy_fraction=occ_arr,
+        is_class_day=class_day_arr,
+        is_break=break_arr,
+        is_holiday=holiday_arr,
+    )
