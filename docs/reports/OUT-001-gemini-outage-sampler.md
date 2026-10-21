# Task Report: OUT-001 — Stochastic Outage Arrival & Duration Sampler

**Date:** 2026-10-21  
**Agent:** gemini  
**Task ID:** OUT-001  
**Status:** done  
**Commit:** `4a666d6` (`feat(OUT-001): implement stochastic outage sampler and typhoon coupling`)  
**Patch File:** `patch/OUT-001-gemini-outage-sampler.patch`  

---

## 1. Executive Summary

This unit of work completes task `OUT-001` ("Stochastic Outage Arrival & Duration Sampler"), implementing the stochastic utility grid failure engine, Lognormal duration sampler, integer-hour discretization, interval merging, typhoon multi-day solar depression coupling, and Kolmogorov-Smirnov goodness-of-fit validator.

The implementation strictly satisfies the Phase 2 interface contract (`docs/context/phase2-interface-contract.md`) and calibration decision `[D-11]`:
1. **`sample_outage_schedule(year_type: str, rng: np.random.Generator, *, n_hours: int = 8760) -> OutageSchedule` (`src/ccis_sim/outage/sampler.py`)**:
   - Generates annual grid outage schedules driven by a homogeneous Poisson arrival process ($\lambda = 3.0\text{ yr}^{-1}$ for normal years, $\lambda = 8.0\text{ yr}^{-1}$ for typhoon years).
   - Draws continuous pre-discretization durations from calibrated Lognormal distributions ($\mu = 1.2, \sigma = 0.8$ for normal; $\mu = 2.3, \sigma = 1.0$ for typhoon) per `[D-11]`.
   - Discretizes continuous durations to integer hours via ceiling ($\max(1, \lceil D \rceil)$) with a minimum of 1 hour, reflecting that any outage during an hourly simulation step cuts power for that hour (`[ASSUMPTION]`).
   - Merges contiguous or overlapping outage intervals into single contiguous `OutageEvent` records, preventing nested blackouts, and clips boundary events to $[1, n_{\text{hours}} + 1]$ (`[ASSUMPTION]`).
   - Guarantees strict mathematical agreement between discrete `OutageEvent` records and the boolean `grid_available` mask across all 8,760 hours ($\text{total blackout hours} \equiv \sum \text{duration\_hours}$).
2. **Typhoon Solar Depression Coupling (`apply_ghi_multiplier`)**:
   - Resolves the `[D-11]` ambiguity ("depressed solar irradiance (20–30% normal GHI)") as an **attenuation multiplier** $m \in [0.20, 0.30]$ (solar irradiance reduced to 20%–30% of normal clear-sky insolation due to dense typhoon clouds) recorded in `[D-33]`.
   - Couples 1 to 2 multi-day storm episodes with the longest outage events in typhoon years, lasting 3 to 5 consecutive days ($72 \dots 120\text{ h}$) starting at event arrival (`[ASSUMPTION]`).
   - Pure function `apply_ghi_multiplier(weather_df, schedule) -> pd.DataFrame` returns a deep copy with attenuated `ghi`, ensuring input immutability.
3. **Statistical Goodness-of-Fit Validator (`validate_duration_distribution`)**:
   - Performs a two-sided Kolmogorov-Smirnov test on pre-discretization durations against the target continuous Lognormal($\mu, \sigma$) distribution at significance level $\alpha = 0.01$.
   - Performs an asymptotic normal z-test verifying that sample mean annual arrivals converge to Poisson($\lambda$).
   - Returns a structured `OutageDistributionValidationResult` diagnostic dataclass.

All 17 dedicated unit/statistical integration tests and all 233 tests across the entire repository test suite pass cleanly (100% green, 0 failures, 0 regressions).

---

## 2. Implementation Details

### 2.1 Changes Made

- `src/ccis_sim/outage/sampler.py`: Created module implementing `sample_outage_schedule`, `apply_ghi_multiplier`, `validate_duration_distribution`, `OutageDistributionValidationResult`, `sample_raw_durations`, `sample_raw_arrivals`, and calibrated distribution constants.
- `src/ccis_sim/outage/__init__.py`: Re-exported all public functions, classes, and parameter constants alongside existing OUT-002 shedding symbols.
- `tests/test_outage_sampler.py`: Created 17 unit and statistical integration tests covering exact seed reproducibility, Poisson arrival mean convergence over 2,500 sampled years, Kolmogorov-Smirnov goodness-of-fit (passing on target distributions and failing on perturbed distributions), event non-overlapping invariants, `grid_available` mask agreement, normal vs. typhoon GHI multipliers, pure function immutability in `apply_ghi_multiplier`, and contract signature conformance.
- `docs/decisions/decision-log.md`: Appended decision `[D-33]` formalizing stochastic parameters, discretization convention, interval merging, and typhoon solar depression attenuation coupling.
- `docs/tasks/status.md`: Updated `OUT-001` and subtasks `OUT-001.1`–`OUT-001.4` from `open` to `done`.

### 2.2 Conformance to Specifications & Decisions

- **Contract Signatures**: Matches `docs/context/phase2-interface-contract.md` §3 exactly:
  - `sample_outage_schedule(year_type: str, rng: np.random.Generator, *, n_hours: int = 8760) -> OutageSchedule`
  - `apply_ghi_multiplier(weather_df: pd.DataFrame, schedule: OutageSchedule) -> pd.DataFrame`
- **Pure Function & Immutability**: All random draws are sourced exclusively from the passed `rng: np.random.Generator` (no global random state). `apply_ghi_multiplier` performs `weather_df.copy(deep=True)`.
- **Decisions Honored**:
  - `[D-11]`: Normal year ($\lambda = 3.0$, Lognormal $\mu=1.2, \sigma=0.8$); Typhoon year ($\lambda = 8.0$, Lognormal $\mu=2.3, \sigma=1.0$, 3–5 days solar depression with GHI at 20%–30%).
  - `[D-26]`: Conforms to `OutageSchedule` dataclass specification in `src/ccis_sim/core/interfaces.py`.
  - `[D-33]`: Records discretization ceiling bias, interval overlap merging, uniform start hour distribution, and attenuation multiplier interpretation.

---

## 3. Verification & Test Evidence

### 3.1 Test Execution

Command executed:
```bash
pytest -v -p no:sugar
```

**Results:**
- Tests passed: 233
- Tests failed: 0
- Tests skipped: 0
- Total execution time: 18.34s

Verbatim test session output:
```text
============================= test session starts ==============================
platform linux -- Python 3.14.8, pytest-9.1.1, pluggy-1.7.0 -- /usr/bin/python
cachedir: .pytest_cache
hypothesis profile 'default'
rootdir: /home/lukexodus/projects/ccis-heat-load-backup-sim-OUT-001
configfile: pyproject.toml
testpaths: tests
plugins: instafail-0.5.0, case-1.5.3, requests-mock-1.12.1, cov-7.1.0, typeguard-4.6.0, anyio-4.15.1, platformdirs-4.13.0, hypothesis-6.169.0, inline-snapshot-0.36.0, time-machine-3.5.1
collecting ... 
collecting 0 items                                                             
collecting 8 items                                                             
collecting 143 items                                                           
collected 233 items                                                            

tests/test_baseline_smoke.py::test_baseline_simulation_record_count_and_hours PASSED [  0%]
tests/test_baseline_smoke.py::test_baseline_simulation_dispatch_invariants PASSED [  0%]
tests/test_baseline_smoke.py::test_baseline_simulation_determinism PASSED [  1%]
tests/test_baseline_smoke.py::test_baseline_simulation_passes_verification_harness PASSED [  1%]
tests/test_baseline_smoke.py::test_baseline_negative_control_single_hour_violation_caught PASSED [  2%]
tests/test_baseline_smoke.py::test_baseline_negative_control_cumulative_drift_caught PASSED [  2%]
tests/test_baseline_smoke.py::test_baseline_headline_metrics_committed_values PASSED [  3%]
tests/test_baseline_smoke.py::test_climate_sensitivity_2016_hot_year_versus_2019 PASSED [  3%]
tests/test_battery_dynamics.py::test_contract_signature_conformance PASSED [  3%]
tests/test_battery_dynamics.py::test_efficiency_split_roundtrip PASSED   [  4%]
tests/test_battery_dynamics.py::test_c_rate_caps PASSED                  [  4%]
tests/test_battery_dynamics.py::test_headroom_limiting PASSED            [  5%]
tests/test_battery_dynamics.py::test_floor_limiting PASSED               [  5%]
tests/test_battery_dynamics.py::test_simultaneous_request_rejected PASSED [  6%]
tests/test_battery_dynamics.py::test_zero_capacity_case PASSED           [  6%]
tests/test_battery_dynamics.py::test_input_validation_and_errors PASSED  [  6%]
tests/test_battery_dynamics.py::test_determinism PASSED                  [  7%]
tests/test_battery_dynamics.py::test_hypothesis_property_verification_harness PASSED [  7%]
tests/test_battery_reserve.py::test_contract_signatures_conformance PASSED [  8%]
tests/test_battery_reserve.py::test_soc_floor_all_cases PASSED           [  8%]
tests/test_battery_reserve.py::test_soc_floor_zero_capacity PASSED       [  9%]
tests/test_battery_reserve.py::test_soc_floor_invalid_inputs PASSED      [  9%]
tests/test_battery_reserve.py::test_apply_idle_losses_nominal PASSED     [  9%]
tests/test_battery_reserve.py::test_apply_idle_losses_zero_parameters PASSED [ 10%]
tests/test_battery_reserve.py::test_apply_idle_losses_clamping_at_floor PASSED [ 10%]
tests/test_battery_reserve.py::test_apply_idle_losses_zero_capacity PASSED [ 11%]
tests/test_battery_reserve.py::test_apply_idle_losses_validation PASSED  [ 11%]
tests/test_battery_reserve.py::test_48_hour_outage_reference_loop PASSED [ 12%]
tests/test_battery_reserve.py::test_chained_idle_losses_pass_verification_harness PASSED [ 12%]
tests/test_conservation_checker.py::test_golden_scenario_conservation_passes PASSED [ 12%]
tests/test_conservation_checker.py::test_deliberate_hourly_residual_violation_caught PASSED [ 13%]
tests/test_conservation_checker.py::test_cumulative_drift_catches_small_consistent_bias PASSED [ 13%]
tests/test_conservation_checker.py::test_cumulative_tolerance_computation PASSED [ 14%]
tests/test_conservation_checker.py::test_battery_negative_soc_caught PASSED [ 14%]
tests/test_conservation_checker.py::test_battery_exceeds_capacity_caught PASSED [ 15%]
tests/test_conservation_checker.py::test_battery_min_soc_floor_normal_vs_emergency PASSED [ 15%]
tests/test_conservation_checker.py::test_battery_charge_c_rate_exceeded_caught PASSED [ 15%]
tests/test_conservation_checker.py::test_battery_discharge_c_rate_exceeded_caught PASSED [ 16%]
tests/test_conservation_checker.py::test_simultaneous_charge_and_discharge_caught PASSED [ 16%]
tests/test_conservation_checker.py::test_golden_scenario_battery_and_conservation_fully_valid PASSED [ 17%]
tests/test_conservation_checker.py::test_empty_records_handling PASSED   [ 17%]
tests/test_conservation_checker.py::test_soc_continuity_golden_scenario_passes PASSED [ 18%]
tests/test_conservation_checker.py::test_soc_continuity_teleport_violation_caught PASSED [ 18%]
tests/test_conservation_checker.py::test_soc_continuity_zero_capacity_skipped PASSED [ 18%]
tests/test_conservation_checker.py::test_non_finite_value_caught_in_conservation PASSED [ 19%]
tests/test_conservation_checker.py::test_non_finite_value_caught_in_battery_boundaries PASSED [ 19%]
tests/test_conservation_checker.py::test_solar_flow_balance_violation_caught PASSED [ 20%]
tests/test_conservation_checker.py::test_demand_flow_balance_violation_caught PASSED [ 20%]
tests/test_conservation_checker.py::test_hourly_record_signed_residual_property PASSED [ 21%]
tests/test_conservation_checker.py::test_soc_continuity_idle_loss_passes PASSED [ 21%]
tests/test_conservation_checker.py::test_soc_continuity_excessive_idle_loss_fails PASSED [ 21%]
tests/test_conservation_checker.py::test_soc_continuity_higher_than_ideal_recursion_fails PASSED [ 22%]
tests/test_conservation_checker.py::test_soc_cumulative_drift_bias_trips PASSED [ 22%]
tests/test_cooling_response.py::test_cooling_contract_signature_conformance PASSED [ 23%]
tests/test_cooling_response.py::test_cooling_zero_at_or_below_base_temperature PASSED [ 23%]
tests/test_cooling_response.py::test_cooling_slope_four_percent_per_celsius_above_base PASSED [ 24%]
tests/test_cooling_response.py::test_cooling_latent_multiplier_low_vs_high_rh PASSED [ 24%]
tests/test_cooling_response.py::test_cooling_capacity_cap_never_exceeded PASSED [ 24%]
tests/test_cooling_response.py::test_cooling_unoccupied_hours_produce_only_tier2_spot_cooling PASSED [ 25%]
tests/test_cooling_response.py::test_cooling_tier_sums_equal_gross PASSED [ 25%]
tests/test_cooling_response.py::test_cooling_monotonic_in_temperature PASSED [ 26%]
tests/test_cooling_response.py::test_cooling_determinism PASSED          [ 26%]
tests/test_cooling_response.py::test_cooling_input_validation PASSED     [ 27%]
tests/test_cooling_response.py::test_cooling_implied_annual_cooling_metrics_report PASSED [ 27%]
tests/test_core_models.py::test_models_immutability PASSED               [ 27%]
tests/test_core_models.py::test_building_archetype_room_count PASSED     [ 28%]
tests/test_core_models.py::test_building_invalid_parameters PASSED       [ 28%]
tests/test_core_models.py::test_solar_array_scenario_capacities[0.0] PASSED [ 29%]
tests/test_core_models.py::test_solar_array_scenario_capacities[50.0] PASSED [ 29%]
tests/test_core_models.py::test_solar_array_scenario_capacities[100.0] PASSED [ 30%]
tests/test_core_models.py::test_solar_array_scenario_capacities[200.0] PASSED [ 30%]
tests/test_core_models.py::test_solar_array_invalid PASSED               [ 30%]
tests/test_core_models.py::test_battery_scenario_capacities_and_properties[0.0] PASSED [ 31%]
tests/test_core_models.py::test_battery_scenario_capacities_and_properties[50.0] PASSED [ 31%]
tests/test_core_models.py::test_battery_scenario_capacities_and_properties[100.0] PASSED [ 32%]
tests/test_core_models.py::test_battery_scenario_capacities_and_properties[200.0] PASSED [ 32%]
tests/test_core_models.py::test_battery_invalid PASSED                   [ 33%]
tests/test_core_models.py::test_battery_configurable_emergency_reserve PASSED [ 33%]
tests/test_core_models.py::test_outage_event_normal PASSED               [ 33%]
tests/test_core_models.py::test_outage_event_typhoon PASSED              [ 34%]
tests/test_core_models.py::test_outage_invalid PASSED                    [ 34%]
tests/test_core_models.py::test_hourly_record_dict_serialization_roundtrip PASSED [ 35%]
tests/test_core_models.py::test_hourly_record_energy_conservation_invariant PASSED [ 35%]
tests/test_core_models.py::test_hourly_record_validation PASSED          [ 36%]
tests/test_demand_schedule.py::test_schedule_contract_signature_conformance PASSED [ 36%]
tests/test_demand_schedule.py::test_schedule_array_lengths_and_types PASSED [ 36%]
tests/test_demand_schedule.py::test_schedule_occupancy_bounds PASSED     [ 37%]
tests/test_demand_schedule.py::test_schedule_weekday_diurnal_profile PASSED [ 37%]
tests/test_demand_schedule.py::test_schedule_saturday_diurnal_profile PASSED [ 38%]
tests/test_demand_schedule.py::test_schedule_sunday_building_closure PASSED [ 38%]
tests/test_demand_schedule.py::test_schedule_holiday_on_weekday PASSED   [ 39%]
tests/test_demand_schedule.py::test_schedule_break_week_admin_occupancy PASSED [ 39%]
tests/test_demand_schedule.py::test_schedule_dst_free_timezone PASSED    [ 39%]
tests/test_demand_schedule.py::test_schedule_leap_year_2016 PASSED       [ 40%]
tests/test_demand_schedule.py::test_schedule_determinism PASSED          [ 40%]
tests/test_demand_schedule.py::test_schedule_invalid_empty_timestamps PASSED [ 41%]
tests/test_demand_schedule.py::test_academic_calendar_validation PASSED  [ 41%]
tests/test_equipment_audit.py::test_audit_fixture_files_exist PASSED     [ 42%]
tests/test_equipment_audit.py::test_schema_csv_format PASSED             [ 42%]
tests/test_equipment_audit.py::test_equipment_item_valid_instantiation PASSED [ 42%]
tests/test_equipment_audit.py::test_equipment_item_cooling_detection PASSED [ 43%]
tests/test_equipment_audit.py::test_equipment_item_boundary_validation[kwargs0-count must be a positive integer] PASSED [ 43%]
tests/test_equipment_audit.py::test_equipment_item_boundary_validation[kwargs1-count must be a positive integer] PASSED [ 44%]
tests/test_equipment_audit.py::test_equipment_item_boundary_validation[kwargs2-rated_kw must be non-negative] PASSED [ 44%]
tests/test_equipment_audit.py::test_equipment_item_boundary_validation[kwargs3-hours_per_day must be in [0, 24]] PASSED [ 45%]
tests/test_equipment_audit.py::test_equipment_item_boundary_validation[kwargs4-hours_per_day must be in [0, 24]] PASSED [ 45%]
tests/test_equipment_audit.py::test_equipment_item_boundary_validation[kwargs5-tier must be 1, 2, or 3] PASSED [ 45%]
tests/test_equipment_audit.py::test_equipment_item_boundary_validation[kwargs6-tier must be 1, 2, or 3] PASSED [ 46%]
tests/test_equipment_audit.py::test_equipment_item_boundary_validation[kwargs7-duty_cycle must be in [0.0, 1.0]] PASSED [ 46%]
tests/test_equipment_audit.py::test_equipment_item_boundary_validation[kwargs8-duty_cycle must be in [0.0, 1.0]] PASSED [ 47%]
tests/test_equipment_audit.py::test_load_audit_from_csv PASSED           [ 47%]
tests/test_equipment_audit.py::test_all_18_rooms_archetype_covered PASSED [ 48%]
tests/test_equipment_audit.py::test_tier_distribution_and_shedding_alignment PASSED [ 48%]
tests/test_equipment_audit.py::test_building_dataclass_compatibility PASSED [ 48%]
tests/test_equipment_audit.py::test_load_nonexistent_file_raises PASSED  [ 49%]
tests/test_equipment_audit.py::test_exact_connected_capacity_reconciliation PASSED [ 49%]
tests/test_interfaces.py::test_tiered_demand_valid PASSED                [ 50%]
tests/test_interfaces.py::test_tiered_demand_validation_errors PASSED    [ 50%]
tests/test_interfaces.py::test_occupancy_schedule_valid PASSED           [ 51%]
tests/test_interfaces.py::test_occupancy_schedule_validation_errors PASSED [ 51%]
tests/test_interfaces.py::test_outage_schedule_valid_and_defaults PASSED [ 51%]
tests/test_interfaces.py::test_outage_schedule_validation_errors PASSED  [ 52%]
tests/test_interfaces.py::test_battery_step_result_valid_and_mutual_exclusion PASSED [ 52%]
tests/test_interfaces.py::test_shed_result_valid_and_validation_errors PASSED [ 53%]
tests/test_interfaces.py::test_battery_idle_loss_attributes_default_and_validation PASSED [ 53%]
tests/test_load_shedding.py::test_compute_tier_audit_shares_against_committed_fixture PASSED [ 54%]
tests/test_load_shedding.py::test_compute_tier_audit_shares_empty_audit PASSED [ 54%]
tests/test_load_shedding.py::test_grid_available_all_tiers_served PASSED [ 54%]
tests/test_load_shedding.py::test_instant_tier3_shed_on_grid_loss PASSED [ 55%]
tests/test_load_shedding.py::test_grid_restoration_returns_to_tier3 PASSED [ 55%]
tests/test_load_shedding.py::test_soc_threshold_exact_boundary PASSED    [ 56%]
tests/test_load_shedding.py::test_custom_tier2_shed_soc_fraction PASSED  [ 56%]
tests/test_load_shedding.py::test_per_tier_conservation_invariant[demand0-True-50.0] PASSED [ 57%]
tests/test_load_shedding.py::test_per_tier_conservation_invariant[demand1-False-30.0] PASSED [ 57%]
tests/test_load_shedding.py::test_per_tier_conservation_invariant[demand2-False-10.0] PASSED [ 57%]
tests/test_load_shedding.py::test_per_tier_conservation_invariant[demand3-False-5.0] PASSED [ 58%]
tests/test_load_shedding.py::test_per_tier_conservation_invariant[demand4-False-15.0] PASSED [ 58%]
tests/test_load_shedding.py::test_harness_subflow_balance_integration PASSED [ 59%]
tests/test_load_shedding.py::test_unserved_tracker_normal_operation_no_outages PASSED [ 59%]
tests/test_load_shedding.py::test_unserved_tracker_multi_hour_outage_with_shortfall PASSED [ 60%]
tests/test_load_shedding.py::test_tracker_catastrophic_shortfall PASSED  [ 60%]
tests/test_load_shedding.py::test_zero_demand_edge_case PASSED           [ 60%]
tests/test_load_shedding.py::test_invalid_arguments_raise_errors PASSED  [ 61%]
tests/test_mock_bills.py::test_generate_12_monthly_bills PASSED          [ 61%]
tests/test_mock_bills.py::test_mock_bill_internal_energy_conservation PASSED [ 62%]
tests/test_mock_bills.py::test_annual_eui_benchmark_conformance PASSED   [ 62%]
tests/test_mock_bills.py::test_committed_fixture_eui_plausibility PASSED [ 63%]
tests/test_mock_bills.py::test_hot_season_cooling_elevation PASSED       [ 63%]
tests/test_mock_bills.py::test_academic_break_reduction PASSED           [ 63%]
tests/test_mock_bills.py::test_csv_save_and_load_roundtrip PASSED        [ 64%]
tests/test_mock_bills.py::test_generator_seed_reproducibility PASSED     [ 64%]
tests/test_non_cooling_demand.py::test_non_cooling_contract_signature_conformance PASSED [ 65%]
tests/test_non_cooling_demand.py::test_non_cooling_tier_sums_equal_gross PASSED [ 65%]
tests/test_non_cooling_demand.py::test_non_cooling_baseload_rule_exact_ten_percent PASSED [ 66%]
tests/test_non_cooling_demand.py::test_non_cooling_no_double_counting_of_continuous_loads PASSED [ 66%]
tests/test_non_cooling_demand.py::test_non_cooling_baseload_across_night_sunday_and_holiday PASSED [ 66%]
tests/test_non_cooling_demand.py::test_non_cooling_tier1_constant_life_safety PASSED [ 67%]
tests/test_non_cooling_demand.py::test_non_cooling_tier2_and_tier3_ranges PASSED [ 67%]
tests/test_non_cooling_demand.py::test_non_cooling_class_day_demand_exceeds_holiday PASSED [ 68%]
tests/test_non_cooling_demand.py::test_non_cooling_ignores_cooling_equipment PASSED [ 68%]
tests/test_non_cooling_demand.py::test_non_cooling_determinism PASSED    [ 69%]
tests/test_outage_sampler.py::test_deterministic_reproducibility PASSED  [ 69%]
tests/test_outage_sampler.py::test_distinct_seeds_produce_different_schedules PASSED [ 69%]
tests/test_outage_sampler.py::test_poisson_arrival_mean_over_2000_years PASSED [ 70%]
tests/test_outage_sampler.py::test_ks_goodness_of_fit_normal_regime PASSED [ 70%]
tests/test_outage_sampler.py::test_ks_goodness_of_fit_typhoon_regime PASSED [ 71%]
tests/test_outage_sampler.py::test_validator_with_arrival_counts PASSED  [ 71%]
tests/test_outage_sampler.py::test_validator_edge_cases PASSED           [ 72%]
tests/test_outage_sampler.py::test_events_bounds_and_no_overlaps_across_many_seeds[normal] PASSED [ 72%]
tests/test_outage_sampler.py::test_events_bounds_and_no_overlaps_across_many_seeds[typhoon] PASSED [ 72%]
tests/test_outage_sampler.py::test_grid_available_mask_agrees_with_events[normal] PASSED [ 73%]
tests/test_outage_sampler.py::test_grid_available_mask_agrees_with_events[typhoon] PASSED [ 73%]
tests/test_outage_sampler.py::test_normal_year_ghi_multiplier_all_ones PASSED [ 74%]
tests/test_outage_sampler.py::test_typhoon_solar_depression_multipliers_and_windows PASSED [ 74%]
tests/test_outage_sampler.py::test_apply_ghi_multiplier_pure_function_and_accuracy PASSED [ 75%]
tests/test_outage_sampler.py::test_apply_ghi_multiplier_validation_errors PASSED [ 75%]
tests/test_outage_sampler.py::test_contract_signature_conformance PASSED [ 75%]
tests/test_outage_sampler.py::test_zero_arrival_case PASSED              [ 76%]
tests/test_smoke.py::test_package_version PASSED                         [ 76%]
tests/test_smoke.py::test_submodules_importable[ccis_sim.core] PASSED    [ 77%]
tests/test_smoke.py::test_submodules_importable[ccis_sim.demand] PASSED  [ 77%]
tests/test_smoke.py::test_submodules_importable[ccis_sim.solar] PASSED   [ 78%]
tests/test_smoke.py::test_submodules_importable[ccis_sim.battery] PASSED [ 78%]
tests/test_smoke.py::test_submodules_importable[ccis_sim.outage] PASSED  [ 78%]
tests/test_smoke.py::test_submodules_importable[ccis_sim.integration] PASSED [ 79%]
tests/test_smoke.py::test_submodules_importable[ccis_sim.decision] PASSED [ 79%]
tests/test_smoke.py::test_numpy_environment_sanity PASSED                [ 80%]
tests/test_smoke.py::test_scipy_environment_sanity PASSED                [ 80%]
tests/test_solar_array.py::test_contract_signature_conformance PASSED    [ 81%]
tests/test_solar_array.py::test_scenario_capacities_execution[0.0] PASSED [ 81%]
tests/test_solar_array.py::test_scenario_capacities_execution[50.0] PASSED [ 81%]
tests/test_solar_array.py::test_scenario_capacities_execution[100.0] PASSED [ 82%]
tests/test_solar_array.py::test_scenario_capacities_execution[200.0] PASSED [ 82%]
tests/test_solar_array.py::test_zero_nighttime_and_zero_capacity PASSED  [ 83%]
tests/test_solar_array.py::test_linearity_below_clipping PASSED          [ 83%]
tests/test_solar_array.py::test_inverter_clipping_at_high_irradiance PASSED [ 84%]
tests/test_solar_array.py::test_ac_output_never_exceeds_rating PASSED    [ 84%]
tests/test_solar_array.py::test_pr_budget_decomposition_reconciliation PASSED [ 84%]
tests/test_solar_array.py::test_determinism PASSED                       [ 85%]
tests/test_solar_array.py::test_input_error_handling PASSED              [ 85%]
tests/test_solar_irradiance.py::test_contract_signature_conformance PASSED [ 86%]
tests/test_solar_irradiance.py::test_nighttime_generation_is_strictly_zero PASSED [ 86%]
tests/test_solar_irradiance.py::test_solar_noon_alignment PASSED         [ 87%]
tests/test_solar_irradiance.py::test_thermal_derating_monotonicity PASSED [ 87%]
tests/test_solar_irradiance.py::test_poa_within_sane_band_of_ghi PASSED  [ 87%]
tests/test_solar_irradiance.py::test_no_negative_or_nan_outputs PASSED   [ 88%]
tests/test_solar_irradiance.py::test_determinism PASSED                  [ 88%]
tests/test_solar_irradiance.py::test_annual_dc_yield_reporting PASSED    [ 89%]
tests/test_solar_irradiance.py::test_cell_temperature_formula PASSED     [ 89%]
tests/test_solar_irradiance.py::test_thermal_derating_at_stc PASSED      [ 90%]
tests/test_solar_irradiance.py::test_error_handling_invalid_inputs PASSED [ 90%]
tests/test_weather_ingest.py::test_client_defaults PASSED                [ 90%]
tests/test_weather_ingest.py::test_client_url_construction PASSED        [ 91%]
tests/test_weather_ingest.py::test_client_raw_io_roundtrip PASSED        [ 91%]
tests/test_weather_ingest.py::test_client_network_failure PASSED         [ 92%]
tests/test_weather_ingest.py::test_parse_hourly_json_lst PASSED          [ 92%]
tests/test_weather_ingest.py::test_parse_hourly_json_utc PASSED          [ 93%]
tests/test_weather_ingest.py::test_parse_daily_json PASSED               [ 93%]
tests/test_weather_ingest.py::test_parse_malformed_json PASSED           [ 93%]
tests/test_weather_ingest.py::test_sanitizer_filter_sentinels PASSED     [ 94%]
tests/test_weather_ingest.py::test_sanitizer_interpolate_missing PASSED  [ 94%]
tests/test_weather_ingest.py::test_sanitizer_timezone_alignment_and_midnight_boundary PASSED [ 95%]
tests/test_weather_ingest.py::test_sanitizer_psychrometric_validation PASSED [ 95%]
tests/test_weather_ingest.py::test_sanitizer_standardize_annual_hourly PASSED [ 96%]
tests/test_weather_ingest.py::test_daily_disaggregation_energy_conservation PASSED [ 96%]
tests/test_weather_ingest.py::test_daily_disaggregation_solar_geometry_night_zero PASSED [ 96%]
tests/test_weather_ingest.py::test_daily_disaggregation_temperature_profile PASSED [ 97%]
tests/test_weather_ingest.py::test_daily_disaggregation_relative_humidity_coupling PASSED [ 97%]
tests/test_weather_ingest.py::test_daily_disaggregate_dataframe PASSED   [ 98%]
tests/test_weather_ingest.py::test_committed_fixtures_structure[2016] PASSED [ 98%]
tests/test_weather_ingest.py::test_committed_fixtures_structure[2019] PASSED [ 99%]
tests/test_weather_ingest.py::test_committed_fixtures_climate_comparison PASSED [ 99%]
tests/test_weather_ingest.py::test_raw_files_exist PASSED                [100%]

============================= 233 passed in 18.34s =============================
```

### 3.2 Edge Cases & Negative Testing

1. **Deterministic Reproducibility**: Tested that identical RNG seeds yield identical `OutageSchedule` instances (events, grid mask, and GHI multipliers) across both regimes.
2. **Seed Distinctness**: Tested that distinct seeds produce distinct outage event realizations.
3. **Large-Sample Poisson Arrival Convergence**: Evaluated 2,500 simulated years; sample mean arrival counts converged to within $3\sigma$ of target $\lambda = 3.0$ (normal) and $\lambda = 8.0$ (typhoon).
4. **Kolmogorov-Smirnov Goodness-of-Fit**:
   - Correct normal parameters ($\mu=1.2, \sigma=0.8$) passed KS test with $p \ge 0.01$. Deliberately wrong parameters ($\mu=2.5, \sigma=1.2$) failed with $p < 0.01$.
   - Correct typhoon parameters ($\mu=2.3, \sigma=1.0$) passed KS test with $p \ge 0.01$. Deliberately wrong parameters ($\mu=1.0, \sigma=0.5$) failed with $p < 0.01$.
5. **Zero-Arrival Negative Control**: Verified that when a Poisson draw yields $k = 0$, `events = ()`, `grid_available` is all-True, and `ghi_multiplier` is all-1.0.
6. **No-Overlap & Horizon Invariants**: Evaluated 100 random schedules (50 normal, 50 typhoon); verified all start hours lie in $[1, 8760]$, end hours $\le 8761$, durations $\ge 1.0\text{ h}$, and $\text{end}_i \le \text{start}_{i+1}$ (strict separation).
7. **Grid Available Agreement**: Tested all 8,760 hours across 50 schedules; verified exact equality between `not sched.grid_available[h-1]` and `any(ev.is_active_at(h) for ev in sched.events)`.
8. **Typhoon GHI Depression Bounds**: Verified that depressed hours satisfy $0.20 \le \text{multiplier} \le 0.30$, non-depressed hours are strictly $1.0$, and multi-day windows span 72 to 120 hours.
9. **Input Validation Guards**:
   - `sample_outage_schedule`: Rejects invalid `year_type` strings and non-positive `n_hours`.
   - `apply_ghi_multiplier`: Rejects non-DataFrame inputs, DataFrames missing `'ghi'`, and length mismatches.
   - `validate_duration_distribution`: Rejects sample sizes $< 2$, negative/zero durations, unknown regimes, and empty arrival arrays.

---

## 4. Decisions Recorded

- **[D-33]**: Stochastic Outage Process Calibration, Continuous-to-Discrete Discretization, and Typhoon Solar Depression Coupling locked. Formally documents arrival rates, duration distributions, ceiling discretization bias ($\approx +0.5\text{ h}$), interval merging rules, and 20%–30% GHI attenuation interpretation.

---

## 5. Unified Git Diff

```diff
diff --git c/docs/decisions/decision-log.md w/docs/decisions/decision-log.md
index a432d50..ba4c8e7 100644
--- c/docs/decisions/decision-log.md
+++ w/docs/decisions/decision-log.md
@@ -380,3 +380,22 @@ This file exists so that across API-credit-limited handoffs between APC AI insta
      In `compute_ac_generation`, only the non-thermal BOS derates and inverter efficiency/clipping are applied to the input `dc_kw_per_kwp`. Full system annual yield validation against the 1,298 kWh/kWp Luzon benchmark is deferred to `SOL-002.4` following integration with `SOL-001`.  
 - **Reasoning:** Conforms strictly to Phase 2 interface contracts, eliminates double-counting of cell thermal losses, provides physical and auditable BOS loss accounting, and bounds maximum AC power delivery under inverter clipping.  
 - **Affects:** `SOL-002`, `INT-001`, `DEC-002`.
+
+
+**[D-33]** Stochastic Outage Process Calibration, Continuous-to-Discrete Discretization, and Typhoon Solar Depression Coupling locked.  
+- **Date / Session:** 2026-10-21  
+- **Decision:**  
+  1. **Arrival Process Calibration (`sample_outage_schedule`):**  
+     Implement a homogeneous Poisson arrival process with annual rates $\lambda = 3.0\text{ outages/yr}$ for normal / baseline weather years and $\lambda = 8.0\text{ outages/yr}$ for typhoon / extreme weather years per [D-11]. Arrival start hours are sampled uniformly over the annual timeline $[1, n_{\text{hours}}]$. Uniform start distribution is adopted as the rigorous baseline (`[ASSUMPTION]`), deferring seasonal typhoon clustering (June–November) to future sensitivity sweeps since empirical sub-annual hazard rate calibration data is unavailable.  
+  2. **Continuous Duration Sampling:**  
+     Continuous pre-discretization durations are sampled from the target Lognormal($\mu, \sigma$) distribution on $\ln(\text{hours})$, where Normal Year has $(\mu = 1.2, \sigma = 0.8)$ (median 3.32h, mean 4.56h) and Typhoon Year has $(\mu = 2.3, \sigma = 1.0)$ (median 9.97h, mean 16.44h) per [D-11].  
+  3. **Continuous-to-Discrete Hour Discretization & Bias:**  
+     Discretize continuous durations to integer hours via ceiling: $D_{\text{int}} = \max(1, \lceil D \rceil)$ (`[ASSUMPTION]`). Because the CCIS simulation step is $\Delta t = 1.0\text{ h}$, any non-zero outage duration interrupts building electrical service for that hour. This introduces a slight upward discretization bias of $\approx +0.5\text{ h}$ per event.  
+  4. **Interval Merging & Boundary Clipping:**  
+     Multiple outages that overlap or touch ($s_2 \le e_1$) are merged into a single continuous blackout event with $s_{\text{merged}} = s_1$ and $e_{\text{merged}} = \max(e_1, e_2)$ (`[ASSUMPTION]`). Merging avoids unphysical overlapping events and ensures `grid_available` strictly reflects discrete `OutageEvent` records, slightly reducing event count ($<0.01$ events/yr in normal, $\approx 0.10$ events/yr in typhoon) while preserving exact blackout hour unions. Events starting past the simulation horizon ($s > n_{\text{hours}}$) are excluded; events ending past hour $n_{\text{hours}}$ are clipped to end at hour $n_{\text{hours}} + 1$ (`[ASSUMPTION]`).  
+  5. **Typhoon Solar Depression Interpretation & Coupling (`apply_ghi_multiplier`):**  
+     Resolve the [D-11] ambiguity ("depressed solar irradiance (20–30% normal GHI)") as an **attenuation multiplier** $m \in [0.20, 0.30]$ (i.e. insolation reduced to 20%–30% of normal clear-sky insolation due to dense cyclone cloud cover, rather than a 20%–30% reduction). In typhoon years with outages, 1 to 2 storm episodes are coupled with the longest outage events (`[ASSUMPTION]`), lasting 3 to 5 consecutive days ($72 \dots 120\text{ h}$) starting at the outage event start hour. Outside storm episodes and in normal years, the multiplier is strictly $1.0$. `apply_ghi_multiplier` returns a deep copy of the input weather DataFrame, preserving input immutability.  
+  6. **Statistical Goodness-of-Fit Validator (`validate_duration_distribution`):**  
+     Evaluates pre-discretization continuous durations against target Lognormal via two-sided Kolmogorov-Smirnov test at significance level $\alpha = 0.01$, and verifies annual arrival counts against Poisson($\lambda$) via large-sample standard error normal approximation.  
+- **Reasoning:** Conforms strictly to Phase 2 interface contracts (`phase2-interface-contract.md`), eliminates arbitrary constants, provides empirical calibration to Philippine rural cooperative and cyclone data [D-11], and guarantees mathematical consistency between discrete `OutageEvent` records and boolean `grid_available` arrays.  
+- **Affects:** `ccis_sim.outage.sampler`, `ccis_sim.outage`, `INT-001`, `INT-002`, `DEC-002`.
diff --git c/docs/tasks/status.md w/docs/tasks/status.md
index 909d7fa..a405aca 100644
--- c/docs/tasks/status.md
+++ w/docs/tasks/status.md
@@ -103,11 +103,11 @@ Status: **open**
 | BAT-002.2   | Implement configurable emergency outage reserve %                                                    | `done` | Outage cushion                                                                                                      |
 | BAT-002.3   | Incorporate ambient self-discharge (2%/month) and tare loss                                          | `done` | Idle losses                                                                                                         |
 | BAT-002.4   | Write unit tests for deep-discharge protection during long outages                                   | `done` | Protection tests                                                                                                    |
-| **OUT-001** | **Stochastic Outage Arrival & Duration Sampler**                                                     | `open` |                                                                                                                   |
-| OUT-001.1   | Implement Poisson arrival process ($\lambda = 3$ normal, $\lambda = 8$ typhoon)                      | `open` | Poisson arrivals                                                                                                  |
-| OUT-001.2   | Implement Lognormal duration sampler (Normal: $\mu=1.2, \sigma=0.8$; Typhoon: $\mu=2.3, \sigma=1.0$) | `open` | Duration sampler                                                                                                  |
-| OUT-001.3   | Implement typhoon multi-day solar depression (20–30% GHI for 3–5 days)                               | `open` | Storm coupling                                                                                                    |
-| OUT-001.4   | Add Kolmogorov-Smirnov distribution goodness-of-fit validator                                        | `open` | Distribution fit                                                                                                  |
+| **OUT-001** | **Stochastic Outage Arrival & Duration Sampler**                                                     | `done` | [Report](docs/reports/OUT-001-gemini-outage-sampler.md) [D-33]                                                     |
+| OUT-001.1   | Implement Poisson arrival process ($\lambda = 3$ normal, $\lambda = 8$ typhoon)                      | `done` | Poisson arrivals [D-33]                                                                                           |
+| OUT-001.2   | Implement Lognormal duration sampler (Normal: $\mu=1.2, \sigma=0.8$; Typhoon: $\mu=2.3, \sigma=1.0$) | `done` | Duration sampler [D-33]                                                                                           |
+| OUT-001.3   | Implement typhoon multi-day solar depression (20–30% GHI for 3–5 days)                               | `done` | Storm coupling [D-33]                                                                                             |
+| OUT-001.4   | Add Kolmogorov-Smirnov distribution goodness-of-fit validator                                        | `done` | Distribution fit [D-33]                                                                                           |
 | **OUT-002** | **Priority-Based Tiered Load Shedding Controller**                                                   | `done` | [Report](docs/reports/OUT-002-gemini-load-shedding.md)                                                             |
 | OUT-002.1   | Implement load categorization: Tier 1 (2%), Tier 2 (18%), Tier 3 (80%)                               | `done` | Tier mapping helper                                                                                                |
 | OUT-002.2   | Build automated shedding logic on grid failure (instant Tier 3 drop)                                 | `done` | Shedding logic                                                                                                     |
diff --git c/src/ccis_sim/outage/__init__.py w/src/ccis_sim/outage/__init__.py
index 3f8f334..cd75108 100644
--- c/src/ccis_sim/outage/__init__.py
+++ w/src/ccis_sim/outage/__init__.py
@@ -1,5 +1,24 @@
 """Stochastic utility outage generation (Poisson/Lognormal) and priority load shedding."""
 
+from ccis_sim.outage.sampler import (
+    DEFAULT_ANNUAL_HOURS,
+    NORMAL_LAMBDA,
+    NORMAL_LOGNORMAL_MU,
+    NORMAL_LOGNORMAL_SIGMA,
+    TYPHOON_GHI_MULTIPLIER_MAX,
+    TYPHOON_GHI_MULTIPLIER_MIN,
+    TYPHOON_LAMBDA,
+    TYPHOON_LOGNORMAL_MU,
+    TYPHOON_LOGNORMAL_SIGMA,
+    TYPHOON_STORM_DAYS_MAX,
+    TYPHOON_STORM_DAYS_MIN,
+    OutageDistributionValidationResult,
+    apply_ghi_multiplier,
+    sample_outage_schedule,
+    sample_raw_arrivals,
+    sample_raw_durations,
+    validate_duration_distribution,
+)
 from ccis_sim.outage.shedding import (
     TierAuditComparison,
     UnservedTracker,
@@ -8,8 +27,27 @@ from ccis_sim.outage.shedding import (
 )
 
 __all__ = [
+    # Shedding (OUT-002)
     "shed_for_hour",
     "UnservedTracker",
     "TierAuditComparison",
     "compute_tier_audit_shares",
+    # Sampler (OUT-001)
+    "sample_outage_schedule",
+    "apply_ghi_multiplier",
+    "validate_duration_distribution",
+    "OutageDistributionValidationResult",
+    "sample_raw_durations",
+    "sample_raw_arrivals",
+    "NORMAL_LAMBDA",
+    "NORMAL_LOGNORMAL_MU",
+    "NORMAL_LOGNORMAL_SIGMA",
+    "TYPHOON_LAMBDA",
+    "TYPHOON_LOGNORMAL_MU",
+    "TYPHOON_LOGNORMAL_SIGMA",
+    "TYPHOON_STORM_DAYS_MIN",
+    "TYPHOON_STORM_DAYS_MAX",
+    "TYPHOON_GHI_MULTIPLIER_MIN",
+    "TYPHOON_GHI_MULTIPLIER_MAX",
+    "DEFAULT_ANNUAL_HOURS",
 ]
diff --git c/src/ccis_sim/outage/sampler.py w/src/ccis_sim/outage/sampler.py
new file mode 100644
index 0000000..5507fac
--- /dev/null
+++ w/src/ccis_sim/outage/sampler.py
@@ -0,0 +1,510 @@
+"""Stochastic utility outage generation and typhoon solar depression sampler.
+
+Implements Poisson arrival processes, Lognormal duration distributions,
+integer-hour discretization, interval merging, and typhoon multi-day solar
+depression coupling per decisions [D-11], [D-26], and [D-33].
+"""
+
+from __future__ import annotations
+
+import math
+from collections.abc import Sequence
+from dataclasses import dataclass
+from typing import Literal
+
+import numpy as np
+import pandas as pd
+import scipy.stats as stats
+
+from ccis_sim.core.interfaces import OutageSchedule
+from ccis_sim.core.models import OutageEvent, OutageType
+
+# ---------------------------------------------------------------------------
+# Stochastic Distribution Parameters per [D-11]
+# ---------------------------------------------------------------------------
+NORMAL_LAMBDA: float = 3.0
+"""Annual Poisson arrival rate for normal / baseline weather years (events/year)."""
+
+NORMAL_LOGNORMAL_MU: float = 1.2
+"""Log-mean parameter mu for normal year duration distribution on ln(hours)."""
+
+NORMAL_LOGNORMAL_SIGMA: float = 0.8
+"""Log-standard-deviation parameter sigma for normal year duration distribution."""
+
+TYPHOON_LAMBDA: float = 8.0
+"""Annual Poisson arrival rate for typhoon / extreme weather years (events/year)."""
+
+TYPHOON_LOGNORMAL_MU: float = 2.3
+"""Log-mean parameter mu for typhoon year duration distribution on ln(hours)."""
+
+TYPHOON_LOGNORMAL_SIGMA: float = 1.0
+"""Log-standard-deviation parameter sigma for typhoon year duration distribution."""
+
+TYPHOON_STORM_DAYS_MIN: int = 3
+"""Minimum duration of typhoon solar depression window in consecutive days per [D-11]."""
+
+TYPHOON_STORM_DAYS_MAX: int = 5
+"""Maximum duration of typhoon solar depression window in consecutive days per [D-11]."""
+
+TYPHOON_GHI_MULTIPLIER_MIN: float = 0.20
+"""Minimum solar GHI multiplier during active typhoon depression window (20% normal GHI)."""
+
+TYPHOON_GHI_MULTIPLIER_MAX: float = 0.30
+"""Maximum solar GHI multiplier during active typhoon depression window (30% normal GHI)."""
+
+DEFAULT_ANNUAL_HOURS: int = 8760
+"""Standard hours in an annual simulation cycle."""
+
+
+@dataclass(frozen=True)
+class OutageDistributionValidationResult:
+    """Goodness-of-fit validation outcome for outage duration and arrival processes.
+
+    Returned by validate_duration_distribution per OUT-001.4.
+    """
+
+    ks_statistic: float
+    """Kolmogorov-Smirnov test statistic comparing sample durations to target Lognormal."""
+
+    ks_pvalue: float
+    """Two-sided p-value from the Kolmogorov-Smirnov test."""
+
+    ks_passed: bool
+    """True if ks_pvalue >= alpha (null hypothesis of target Lognormal not rejected)."""
+
+    alpha: float
+    """Significance level threshold (e.g. 0.01)."""
+
+    sample_size: int
+    """Number of sampled durations evaluated."""
+
+    target_mu: float
+    """Target Lognormal log-mean parameter."""
+
+    target_sigma: float
+    """Target Lognormal log-std parameter."""
+
+    arrival_passed: bool | None = None
+    """True if arrival count is statistically consistent with Poisson(lambda), or None if skipped."""
+
+    mean_arrivals: float | None = None
+    """Sample mean annual arrival count across evaluated years, or None if skipped."""
+
+    target_lambda: float | None = None
+    """Target Poisson arrival rate parameter, or None if skipped."""
+
+    arrival_pvalue: float | None = None
+    """Two-sided p-value from arrival rate z-test, or None if skipped."""
+
+    passed: bool = True
+    """Overall test outcome: True if all evaluated tests pass."""
+
+    details: str = ""
+    """Human-readable diagnostic summary."""
+
+
+def sample_raw_durations(
+    year_type: str,
+    n_samples: int,
+    rng: np.random.Generator,
+) -> np.ndarray:
+    """Sample continuous pre-discretization outage durations from target Lognormal(mu, sigma).
+
+    Parameters
+    ----------
+    year_type : str
+        Climate reliability regime: 'normal' or 'typhoon'.
+    n_samples : int
+        Number of duration samples to draw.
+    rng : np.random.Generator
+        Deterministic numpy random number generator.
+
+    Returns
+    -------
+    np.ndarray
+        1D float array of continuous duration samples in hours.
+    """
+    regime = year_type.strip().lower()
+    if regime == "normal":
+        mu, sigma = NORMAL_LOGNORMAL_MU, NORMAL_LOGNORMAL_SIGMA
+    elif regime == "typhoon":
+        mu, sigma = TYPHOON_LOGNORMAL_MU, TYPHOON_LOGNORMAL_SIGMA
+    else:
+        raise ValueError(f"year_type must be 'normal' or 'typhoon', got '{year_type}'")
+
+    if n_samples <= 0:
+        raise ValueError(f"n_samples must be positive, got {n_samples}")
+
+    return rng.lognormal(mean=mu, sigma=sigma, size=n_samples)
+
+
+def sample_raw_arrivals(
+    year_type: str,
+    n_years: int,
+    rng: np.random.Generator,
+) -> np.ndarray:
+    """Sample annual outage arrival counts from target Poisson(lambda).
+
+    Parameters
+    ----------
+    year_type : str
+        Climate reliability regime: 'normal' or 'typhoon'.
+    n_years : int
+        Number of annual arrival counts to draw.
+    rng : np.random.Generator
+        Deterministic numpy random number generator.
+
+    Returns
+    -------
+    np.ndarray
+        1D integer array of annual arrival counts.
+    """
+    regime = year_type.strip().lower()
+    if regime == "normal":
+        lam = NORMAL_LAMBDA
+    elif regime == "typhoon":
+        lam = TYPHOON_LAMBDA
+    else:
+        raise ValueError(f"year_type must be 'normal' or 'typhoon', got '{year_type}'")
+
+    if n_years <= 0:
+        raise ValueError(f"n_years must be positive, got {n_years}")
+
+    return rng.poisson(lam=lam, size=n_years)
+
+
+def sample_outage_schedule(
+    year_type: str,
+    rng: np.random.Generator,
+    *,
+    n_hours: int = DEFAULT_ANNUAL_HOURS,
+) -> OutageSchedule:
+    """Generate stochastic Poisson outage arrivals, lognormal durations, and typhoon storm windows.
+
+    Conforms to Phase 2 interface contract (docs/context/phase2-interface-contract.md).
+    All stochasticity is sourced exclusively from the provided `rng` instance.
+
+    Parameters
+    ----------
+    year_type : str
+        Reliability regime: 'normal' (lambda=3, mu=1.2, sigma=0.8) or
+        'typhoon' (lambda=8, mu=2.3, sigma=1.0) per [D-11].
+    rng : np.random.Generator
+        Deterministic numpy random number generator.
+    n_hours : int, optional
+        Simulation horizon in hours (defaults to 8,760 for an annual cycle).
+
+    Returns
+    -------
+    OutageSchedule
+        Immutable schedule with non-overlapping OutageEvent records, grid_available
+        boolean mask, and solar ghi_multiplier array.
+    """
+    regime = year_type.strip().lower()
+    if regime not in ("normal", "typhoon"):
+        raise ValueError(f"year_type must be 'normal' or 'typhoon', got '{year_type}'")
+
+    if n_hours <= 0:
+        raise ValueError(f"n_hours must be positive, got {n_hours}")
+
+    if regime == "normal":
+        lam = NORMAL_LAMBDA
+        mu = NORMAL_LOGNORMAL_MU
+        sigma = NORMAL_LOGNORMAL_SIGMA
+        outage_type = OutageType.NORMAL
+    else:
+        lam = TYPHOON_LAMBDA
+        mu = TYPHOON_LOGNORMAL_MU
+        sigma = TYPHOON_LOGNORMAL_SIGMA
+        outage_type = OutageType.TYPHOON
+
+    # Sample arrival count from Poisson process
+    k = int(rng.poisson(lam=lam))
+
+    if k == 0:
+        return OutageSchedule(
+            events=(),
+            grid_available=np.ones(n_hours, dtype=bool),
+            year_type=regime,  # type: ignore[arg-type]
+            ghi_multiplier=np.ones(n_hours, dtype=np.float64),
+        )
+
+    # [ASSUMPTION] Arrival start hours are sampled uniformly over the annual timeline [1, n_hours].
+    # Uniform start distribution is adopted as the rigorous baseline, deferring seasonal typhoon
+    # clustering (June-November) to future sensitivity refinements per [D-33].
+    raw_starts = rng.integers(1, n_hours + 1, size=k)
+    raw_durations = rng.lognormal(mean=mu, sigma=sigma, size=k)
+
+    # [ASSUMPTION] Discretization to integer hours via ceiling (math.ceil) with minimum 1 hour:
+    # duration_h = max(1, int(math.ceil(d_raw))). This ensures any non-zero outage duration spans
+    # at least one discrete simulation hour, introducing a slight upward bias (+0.5h on average).
+    order = np.argsort(raw_starts)
+    sorted_starts = [int(raw_starts[i]) for i in order]
+    sorted_durations = [max(1, int(math.ceil(raw_durations[i]))) for i in order]
+
+    # [ASSUMPTION] Overlapping or contiguous outage intervals are merged into a single continuous
+    # event with start = start_1 and end = max(end_1, end_2). This prevents simultaneous/nested
+    # outages and ensures grid_available is strictly consistent with discrete OutageEvents.
+    # [ASSUMPTION] Events extending past n_hours are clipped at hour n_hours + 1.
+    merged_intervals: list[tuple[int, int]] = []
+    for s, d in zip(sorted_starts, sorted_durations):
+        if s > n_hours:
+            continue
+        e = min(s + d, n_hours + 1)
+        if not merged_intervals:
+            merged_intervals.append((s, e))
+        else:
+            last_s, last_e = merged_intervals[-1]
+            if s <= last_e:
+                # Contiguous or overlapping: merge
+                merged_intervals[-1] = (last_s, max(last_e, e))
+            else:
+                merged_intervals.append((s, e))
+
+    # Build grid_available boolean mask (True = connected, False = blackout)
+    grid_available = np.ones(n_hours, dtype=bool)
+    for s, e in merged_intervals:
+        grid_available[s - 1 : e - 1] = False
+
+    # Build solar GHI multiplier and OutageEvents
+    ghi_multiplier = np.ones(n_hours, dtype=np.float64)
+    events: list[OutageEvent] = []
+
+    if regime == "normal":
+        for s, e in merged_intervals:
+            events.append(
+                OutageEvent(
+                    start_hour=s,
+                    duration_hours=float(e - s),
+                    outage_type=outage_type,
+                    solar_depression_factor=1.0,
+                    solar_depression_duration_hours=0.0,
+                )
+            )
+    else:
+        # Typhoon regime: assign solar depression windows
+        # [ASSUMPTION] Resolve [D-11] ambiguity ("depressed solar irradiance (20-30% normal GHI)")
+        # as an attenuation multiplier m in [0.20, 0.30] (GHI reduced to 20-30% of normal clear-sky
+        # level due to dense typhoon cloud cover) per [D-33].
+        # [ASSUMPTION] 1 to 2 storm episodes are coupled with the longest outage events, lasting
+        # 3 to 5 consecutive days (72-120 hours) starting at the outage event start hour.
+        if merged_intervals:
+            # Rank merged intervals by duration descending to identify major storm events
+            durations = [e - s for s, e in merged_intervals]
+            sorted_by_duration = np.argsort(durations)[::-1]
+            n_episodes = min(len(merged_intervals), int(rng.integers(1, 3)))
+            storm_indices = set(sorted_by_duration[:n_episodes])
+
+            storm_params: dict[int, tuple[float, float]] = {}
+            for idx in storm_indices:
+                storm_days = int(rng.integers(TYPHOON_STORM_DAYS_MIN, TYPHOON_STORM_DAYS_MAX + 1))
+                dep_hours = float(storm_days * 24)
+                dep_factor = float(rng.uniform(TYPHOON_GHI_MULTIPLIER_MIN, TYPHOON_GHI_MULTIPLIER_MAX))
+                storm_params[idx] = (dep_factor, dep_hours)
+
+                s_storm = merged_intervals[idx][0]
+                dep_end = min(n_hours, s_storm - 1 + int(dep_hours))
+                ghi_multiplier[s_storm - 1 : dep_end] = np.minimum(
+                    ghi_multiplier[s_storm - 1 : dep_end],
+                    dep_factor,
+                )
+
+            for idx, (s, e) in enumerate(merged_intervals):
+                if idx in storm_params:
+                    factor, dur_h = storm_params[idx]
+                    events.append(
+                        OutageEvent(
+                            start_hour=s,
+                            duration_hours=float(e - s),
+                            outage_type=OutageType.TYPHOON,
+                            solar_depression_factor=factor,
+                            solar_depression_duration_hours=dur_h,
+                        )
+                    )
+                else:
+                    events.append(
+                        OutageEvent(
+                            start_hour=s,
+                            duration_hours=float(e - s),
+                            outage_type=OutageType.TYPHOON,
+                            solar_depression_factor=1.0,
+                            solar_depression_duration_hours=0.0,
+                        )
+                    )
+
+    return OutageSchedule(
+        events=tuple(events),
+        grid_available=grid_available,
+        year_type=regime,  # type: ignore[arg-type]
+        ghi_multiplier=ghi_multiplier,
+    )
+
+
+def apply_ghi_multiplier(
+    weather_df: pd.DataFrame,
+    schedule: OutageSchedule,
+) -> pd.DataFrame:
+    """Attenuate solar GHI during active typhoon depression windows.
+
+    Conforms to Phase 2 interface contract (docs/context/phase2-interface-contract.md).
+    Returns a copy of weather_df with the 'ghi' column scaled by schedule.ghi_multiplier.
+
+    Parameters
+    ----------
+    weather_df : pd.DataFrame
+        Hourly weather dataframe containing at least a 'ghi' column.
+    schedule : OutageSchedule
+        Outage schedule containing the ghi_multiplier array.
+
+    Returns
+    -------
+    pd.DataFrame
+        Deep copy of weather_df with 'ghi' multiplied by schedule.ghi_multiplier.
+    """
+    if not isinstance(weather_df, pd.DataFrame):
+        raise TypeError(f"weather_df must be a pandas DataFrame, got {type(weather_df)}")
+
+    if "ghi" not in weather_df.columns:
+        raise ValueError("weather_df must contain a 'ghi' column.")
+
+    if len(weather_df) != len(schedule.ghi_multiplier):
+        raise ValueError(
+            f"Length mismatch: weather_df ({len(weather_df)}) vs "
+            f"schedule.ghi_multiplier ({len(schedule.ghi_multiplier)})"
+        )
+
+    df_copy = weather_df.copy(deep=True)
+    df_copy["ghi"] = df_copy["ghi"] * schedule.ghi_multiplier
+    return df_copy
+
+
+def validate_duration_distribution(
+    durations: Sequence[float] | np.ndarray,
+    year_type: str = "normal",
+    *,
+    target_mu: float | None = None,
+    target_sigma: float | None = None,
+    alpha: float = 0.01,
+    arrival_counts: Sequence[int] | np.ndarray | None = None,
+    target_lambda: float | None = None,
+) -> OutageDistributionValidationResult:
+    """Validate sample outage durations against Lognormal and arrival counts against Poisson.
+
+    Performs a two-sided Kolmogorov-Smirnov test on pre-discretization durations against
+    the continuous Lognormal(mu, sigma) distribution, and an optional arrival count z-test
+    against Poisson(lambda) per OUT-001.4.
+
+    Parameters
+    ----------
+    durations : Sequence[float] | np.ndarray
+        Continuous (pre-discretization) duration samples in hours.
+    year_type : str, optional
+        Regime to determine default parameters: 'normal' or 'typhoon'.
+    target_mu : float, optional
+        Target log-mean parameter (overrides year_type default if provided).
+    target_sigma : float, optional
+        Target log-std parameter (overrides year_type default if provided).
+    alpha : float, optional
+        Significance level threshold (defaults to 0.01).
+    arrival_counts : Sequence[int] | np.ndarray, optional
+        Sample annual arrival counts from multiple simulated years.
+    target_lambda : float, optional
+        Target Poisson arrival rate (overrides year_type default if provided).
+
+    Returns
+    -------
+    OutageDistributionValidationResult
+        Diagnostic object containing test statistics, p-values, and pass/fail verdicts.
+    """
+    regime = year_type.strip().lower()
+
+    # Resolve target Lognormal parameters
+    if target_mu is not None and target_sigma is not None:
+        mu = float(target_mu)
+        sigma = float(target_sigma)
+    elif regime == "normal":
+        mu = NORMAL_LOGNORMAL_MU
+        sigma = NORMAL_LOGNORMAL_SIGMA
+    elif regime == "typhoon":
+        mu = TYPHOON_LOGNORMAL_MU
+        sigma = TYPHOON_LOGNORMAL_SIGMA
+    else:
+        raise ValueError(
+            f"Unknown year_type '{year_type}', expected 'normal' or 'typhoon' "
+            "unless target_mu and target_sigma are explicitly provided."
+        )
+
+    # Resolve target Poisson arrival rate
+    if target_lambda is not None:
+        lam = float(target_lambda)
+    elif regime == "normal":
+        lam = NORMAL_LAMBDA
+    elif regime == "typhoon":
+        lam = TYPHOON_LAMBDA
+    else:
+        lam = NORMAL_LAMBDA
+
+    d_arr = np.asarray(durations, dtype=np.float64)
+    if len(d_arr) < 2:
+        raise ValueError("Need at least 2 duration samples to perform Kolmogorov-Smirnov test.")
+
+    if np.any(d_arr <= 0.0):
+        raise ValueError("Durations must be strictly positive for Lognormal distribution.")
+
+    # Two-sided Kolmogorov-Smirnov test
+    # In scipy.stats.lognorm: s = sigma, loc = 0, scale = exp(mu)
+    ks_res = stats.kstest(d_arr, "lognorm", args=(sigma, 0.0, np.exp(mu)))
+    ks_stat = float(ks_res.statistic)
+    ks_pval = float(ks_res.pvalue)
+    ks_passed = bool(ks_pval >= alpha)
+
+    # Optional Poisson arrival check
+    arrival_passed: bool | None = None
+    mean_arrivals: float | None = None
+    arrival_pval: float | None = None
+
+    if arrival_counts is not None:
+        k_arr = np.asarray(arrival_counts, dtype=np.float64)
+        m_years = len(k_arr)
+        if m_years == 0:
+            raise ValueError("arrival_counts array must not be empty.")
+
+        mean_arrivals = float(np.mean(k_arr))
+        # For sample mean from Poisson(lambda), standard error is sqrt(lambda / M)
+        se = math.sqrt(lam / m_years)
+        if se > 0.0:
+            z = (mean_arrivals - lam) / se
+            # Two-sided normal test
+            arrival_pval = float(2.0 * (1.0 - stats.norm.cdf(abs(z))))
+            arrival_passed = bool(arrival_pval >= alpha)
+        else:
+            arrival_passed = bool(math.isclose(mean_arrivals, lam))
+            arrival_pval = 1.0 if arrival_passed else 0.0
+
+    overall_passed = ks_passed and (arrival_passed is None or arrival_passed)
+
+    details = (
+        f"KS Test: stat={ks_stat:.4f}, pval={ks_pval:.4e}, passed={ks_passed} (alpha={alpha}). "
+        f"Target Lognormal(mu={mu}, sigma={sigma}), N={len(d_arr)}."
+    )
+    if arrival_counts is not None:
+        details += (
+            f" Arrival Check: mean={mean_arrivals:.4f}, target={lam:.4f}, "
+            f"pval={arrival_pval:.4e}, passed={arrival_passed}."
+        )
+
+    return OutageDistributionValidationResult(
+        ks_statistic=ks_stat,
+        ks_pvalue=ks_pval,
+        ks_passed=ks_passed,
+        alpha=alpha,
+        sample_size=len(d_arr),
+        target_mu=mu,
+        target_sigma=sigma,
+        arrival_passed=arrival_passed,
+        mean_arrivals=mean_arrivals,
+        target_lambda=lam,
+        arrival_pvalue=arrival_pval,
+        passed=overall_passed,
+        details=details,
+    )
diff --git c/tests/test_outage_sampler.py w/tests/test_outage_sampler.py
new file mode 100644
index 0000000..001c19d
--- /dev/null
+++ w/tests/test_outage_sampler.py
@@ -0,0 +1,411 @@
+"""Unit and statistical integration tests for stochastic outage sampler (OUT-001).
+
+Verifies Poisson arrival processes, Lognormal duration distributions, Kolmogorov-Smirnov
+goodness-of-fit, non-overlapping interval invariants, grid mask consistency, typhoon
+solar depression attenuation, and Phase 2 contract conformance.
+"""
+
+from __future__ import annotations
+
+import math
+
+import numpy as np
+import pandas as pd
+import pytest
+
+from ccis_sim.core.interfaces import OutageSchedule
+from ccis_sim.core.models import OutageEvent, OutageType
+from ccis_sim.outage.sampler import (
+    DEFAULT_ANNUAL_HOURS,
+    NORMAL_LAMBDA,
+    NORMAL_LOGNORMAL_MU,
+    NORMAL_LOGNORMAL_SIGMA,
+    TYPHOON_GHI_MULTIPLIER_MAX,
+    TYPHOON_GHI_MULTIPLIER_MIN,
+    TYPHOON_LAMBDA,
+    TYPHOON_LOGNORMAL_MU,
+    TYPHOON_LOGNORMAL_SIGMA,
+    TYPHOON_STORM_DAYS_MAX,
+    TYPHOON_STORM_DAYS_MIN,
+    OutageDistributionValidationResult,
+    apply_ghi_multiplier,
+    sample_outage_schedule,
+    sample_raw_arrivals,
+    sample_raw_durations,
+    validate_duration_distribution,
+)
+
+
+# ===========================================================================
+# 1. Reproducibility & Determinism Tests
+# ===========================================================================
+
+def test_deterministic_reproducibility():
+    """Verify that identical seeds produce identical schedules for both regimes."""
+    for regime in ("normal", "typhoon"):
+        rng1 = np.random.default_rng(20261021)
+        rng2 = np.random.default_rng(20261021)
+
+        sched1 = sample_outage_schedule(regime, rng1)
+        sched2 = sample_outage_schedule(regime, rng2)
+
+        assert sched1.year_type == sched2.year_type == regime
+        assert np.array_equal(sched1.grid_available, sched2.grid_available)
+        assert np.array_equal(sched1.ghi_multiplier, sched2.ghi_multiplier)
+        assert len(sched1.events) == len(sched2.events)
+
+        for ev1, ev2 in zip(sched1.events, sched2.events):
+            assert ev1.start_hour == ev2.start_hour
+            assert math.isclose(ev1.duration_hours, ev2.duration_hours, abs_tol=1e-9)
+            assert ev1.outage_type == ev2.outage_type
+            assert math.isclose(ev1.solar_depression_factor, ev2.solar_depression_factor, abs_tol=1e-9)
+            assert math.isclose(ev1.solar_depression_duration_hours, ev2.solar_depression_duration_hours, abs_tol=1e-9)
+
+
+def test_distinct_seeds_produce_different_schedules():
+    """Verify that distinct seeds generate different outage realizations."""
+    rng1 = np.random.default_rng(1001)
+    rng2 = np.random.default_rng(2002)
+
+    sched1 = sample_outage_schedule("typhoon", rng1)
+    sched2 = sample_outage_schedule("typhoon", rng2)
+
+    assert not np.array_equal(sched1.grid_available, sched2.grid_available)
+
+
+# ===========================================================================
+# 2. Statistical Arrival Rate Tests (Poisson Process)
+# ===========================================================================
+
+def test_poisson_arrival_mean_over_2000_years():
+    """Verify mean outage arrival count converges to lambda over >=2,000 sampled years."""
+    n_years = 2500
+    rng = np.random.default_rng(42)
+
+    # Normal year: lambda = 3.0
+    arrivals_normal = sample_raw_arrivals("normal", n_years, rng)
+    mean_normal = float(np.mean(arrivals_normal))
+    se_normal = math.sqrt(NORMAL_LAMBDA / n_years)
+    # 3-sigma tolerance (~99.7% confidence)
+    assert abs(mean_normal - NORMAL_LAMBDA) <= 3.0 * se_normal, (
+        f"Normal mean {mean_normal} deviated from target {NORMAL_LAMBDA} by > 3 SE ({se_normal})"
+    )
+
+    # Typhoon year: lambda = 8.0
+    arrivals_typhoon = sample_raw_arrivals("typhoon", n_years, rng)
+    mean_typhoon = float(np.mean(arrivals_typhoon))
+    se_typhoon = math.sqrt(TYPHOON_LAMBDA / n_years)
+    assert abs(mean_typhoon - TYPHOON_LAMBDA) <= 3.0 * se_typhoon, (
+        f"Typhoon mean {mean_typhoon} deviated from target {TYPHOON_LAMBDA} by > 3 SE ({se_typhoon})"
+    )
+
+
+# ===========================================================================
+# 3. Kolmogorov-Smirnov Goodness-of-Fit Tests (Lognormal Distribution)
+# ===========================================================================
+
+def test_ks_goodness_of_fit_normal_regime():
+    """Verify pre-discretization durations pass KS test against target and fail on wrong params."""
+    rng = np.random.default_rng(2026)
+    durations = sample_raw_durations("normal", 5000, rng)
+
+    # Correct target parameters (mu=1.2, sigma=0.8) -> Must pass at alpha = 0.01
+    res_correct = validate_duration_distribution(durations, year_type="normal", alpha=0.01)
+    assert res_correct.ks_passed is True
+    assert res_correct.ks_pvalue >= 0.01
+    assert res_correct.passed is True
+
+    # Deliberately wrong parameters (mu=2.5, sigma=1.2) -> Must fail
+    res_wrong = validate_duration_distribution(
+        durations,
+        target_mu=2.5,
+        target_sigma=1.2,
+        alpha=0.01,
+    )
+    assert res_wrong.ks_passed is False
+    assert res_wrong.ks_pvalue < 0.01
+    assert res_wrong.passed is False
+
+
+def test_ks_goodness_of_fit_typhoon_regime():
+    """Verify typhoon durations pass KS test against target and fail on wrong params."""
+    rng = np.random.default_rng(777)
+    durations = sample_raw_durations("typhoon", 5000, rng)
+
+    # Correct target parameters (mu=2.3, sigma=1.0) -> Must pass at alpha = 0.01
+    res_correct = validate_duration_distribution(durations, year_type="typhoon", alpha=0.01)
+    assert res_correct.ks_passed is True
+    assert res_correct.ks_pvalue >= 0.01
+    assert res_correct.passed is True
+
+    # Deliberately wrong parameters (mu=1.0, sigma=0.5) -> Must fail
+    res_wrong = validate_duration_distribution(
+        durations,
+        target_mu=1.0,
+        target_sigma=0.5,
+        alpha=0.01,
+    )
+    assert res_wrong.ks_passed is False
+    assert res_wrong.ks_pvalue < 0.01
+    assert res_wrong.passed is False
+
+
+def test_validator_with_arrival_counts():
+    """Verify validate_duration_distribution evaluates arrival counts when provided."""
+    rng = np.random.default_rng(999)
+    durations = sample_raw_durations("normal", 3000, rng)
+    arrivals_consistent = sample_raw_arrivals("normal", 2000, rng)
+
+    res = validate_duration_distribution(
+        durations,
+        year_type="normal",
+        arrival_counts=arrivals_consistent,
+        alpha=0.01,
+    )
+    assert res.passed is True
+    assert res.arrival_passed is True
+    assert res.mean_arrivals is not None
+    assert math.isclose(res.mean_arrivals, NORMAL_LAMBDA, rel_tol=0.05)
+
+    # Inconsistent arrivals (e.g. lambda=8 passed for normal test)
+    arrivals_inconsistent = sample_raw_arrivals("typhoon", 2000, rng)
+    res_bad = validate_duration_distribution(
+        durations,
+        year_type="normal",
+        arrival_counts=arrivals_inconsistent,
+        alpha=0.01,
+    )
+    assert res_bad.arrival_passed is False
+    assert res_bad.passed is False
+
+
+def test_validator_edge_cases():
+    """Verify validation error handling for invalid input data."""
+    with pytest.raises(ValueError, match="Need at least 2 duration samples"):
+        validate_duration_distribution([5.0])
+
+    with pytest.raises(ValueError, match="strictly positive"):
+        validate_duration_distribution([-1.0, 5.0])
+
+    with pytest.raises(ValueError, match="Unknown year_type"):
+        validate_duration_distribution([2.0, 3.0], year_type="invalid")
+
+    with pytest.raises(ValueError, match="arrival_counts array must not be empty"):
+        validate_duration_distribution([2.0, 3.0], year_type="normal", arrival_counts=[])
+
+
+# ===========================================================================
+# 4. Outage Event Invariants & Discretization (No Overlaps, [1, N] Bounds)
+# ===========================================================================
+
+@pytest.mark.parametrize("regime", ["normal", "typhoon"])
+def test_events_bounds_and_no_overlaps_across_many_seeds(regime: str):
+    """Verify that events always lie within [1, N], duration >= 1, and never overlap."""
+    n_hours = 8760
+    rng = np.random.default_rng(54321)
+
+    for _ in range(50):
+        sched = sample_outage_schedule(regime, rng, n_hours=n_hours)
+        events = sched.events
+
+        for i, ev in enumerate(events):
+            # Start hour in [1, N]
+            assert 1 <= ev.start_hour <= n_hours, (
+                f"start_hour {ev.start_hour} outside [1, {n_hours}]"
+            )
+            # Duration must be integer hours >= 1
+            assert ev.duration_hours >= 1.0
+            assert ev.duration_hours == math.floor(ev.duration_hours)
+            # End hour must not exceed N + 1
+            assert ev.end_hour <= n_hours + 1, (
+                f"end_hour {ev.end_hour} exceeded {n_hours + 1}"
+            )
+
+            # Check strict separation between consecutive events (no overlaps)
+            if i + 1 < len(events):
+                next_ev = events[i + 1]
+                assert ev.end_hour <= next_ev.start_hour, (
+                    f"Overlapping events: ev[{i}] ends at {ev.end_hour}, "
+                    f"ev[{i+1}] starts at {next_ev.start_hour}"
+                )
+
+
+# ===========================================================================
+# 5. Grid Available Mask & Event Agreement
+# ===========================================================================
+
+@pytest.mark.parametrize("regime", ["normal", "typhoon"])
+def test_grid_available_mask_agrees_with_events(regime: str):
+    """Verify that grid_available mask strictly matches active hours of OutageEvents."""
+    rng = np.random.default_rng(98765)
+    n_hours = 8760
+
+    for _ in range(25):
+        sched = sample_outage_schedule(regime, rng, n_hours=n_hours)
+        assert len(sched.grid_available) == n_hours
+
+        # Test every single hour
+        for h in range(1, n_hours + 1):
+            is_blackout_from_events = any(ev.is_active_at(h) for ev in sched.events)
+            is_blackout_from_mask = not sched.grid_available[h - 1]
+            assert is_blackout_from_events == is_blackout_from_mask, (
+                f"Disagreement at hour {h}: event={is_blackout_from_events}, mask={is_blackout_from_mask}"
+            )
+
+        # Total blackout hours must equal sum of discrete event durations
+        total_event_hours = sum(int(ev.duration_hours) for ev in sched.events)
+        total_mask_hours = int(np.sum(~sched.grid_available))
+        assert total_event_hours == total_mask_hours
+
+
+# ===========================================================================
+# 6. Solar GHI Multiplier Tests (Normal vs Typhoon)
+# ===========================================================================
+
+def test_normal_year_ghi_multiplier_all_ones():
+    """Verify normal weather years have all-ones GHI multiplier array."""
+    rng = np.random.default_rng(1234)
+    sched = sample_outage_schedule("normal", rng)
+
+    assert len(sched.ghi_multiplier) == 8760
+    assert np.all(sched.ghi_multiplier == 1.0)
+
+    for ev in sched.events:
+        assert ev.solar_depression_factor == 1.0
+        assert ev.solar_depression_duration_hours == 0.0
+
+
+def test_typhoon_solar_depression_multipliers_and_windows():
+    """Verify typhoon solar depression factor is in [0.20, 0.30] inside episodes and 1.0 outside."""
+    rng = np.random.default_rng(202610)
+    found_depressed = False
+
+    for _ in range(50):
+        sched = sample_outage_schedule("typhoon", rng)
+        mult = sched.ghi_multiplier
+        assert len(mult) == 8760
+
+        # Multiplier must always be non-negative and finite
+        assert np.all(np.isfinite(mult))
+        assert np.all(mult >= 0.0)
+
+        # Values must be either 1.0 or within [0.20, 0.30]
+        is_depressed = mult < 1.0
+        if np.any(is_depressed):
+            found_depressed = True
+            depressed_vals = mult[is_depressed]
+            assert np.all(depressed_vals >= TYPHOON_GHI_MULTIPLIER_MIN - 1e-9)
+            assert np.all(depressed_vals <= TYPHOON_GHI_MULTIPLIER_MAX + 1e-9)
+
+        # Verify storm duration on individual events with depression
+        for ev in sched.events:
+            if ev.solar_depression_factor < 1.0:
+                assert TYPHOON_GHI_MULTIPLIER_MIN <= ev.solar_depression_factor <= TYPHOON_GHI_MULTIPLIER_MAX
+                assert ev.solar_depression_duration_hours in (
+                    float(d * 24) for d in range(TYPHOON_STORM_DAYS_MIN, TYPHOON_STORM_DAYS_MAX + 1)
+                )
+
+    assert found_depressed, "Expected at least one depressed window in 50 typhoon runs."
+
+
+# ===========================================================================
+# 7. apply_ghi_multiplier Function Tests
+# ===========================================================================
+
+def test_apply_ghi_multiplier_pure_function_and_accuracy():
+    """Verify apply_ghi_multiplier returns a scaled copy without mutating the input."""
+    # Synthetic weather DataFrame
+    n = 24
+    ghi_original = np.array([500.0] * n, dtype=np.float64)
+    weather_df = pd.DataFrame({
+        "hour": np.arange(1, n + 1),
+        "timestamp": [f"2026-01-01T{h:02d}:00:00+08:00" for h in range(n)],
+        "t_amb": [28.0] * n,
+        "rh": [75.0] * n,
+        "ghi": ghi_original.copy(),
+    })
+
+    # Schedule with 25% depression for hours 5 to 10
+    mult = np.ones(n, dtype=np.float64)
+    mult[4:10] = 0.25
+    sched = OutageSchedule(
+        events=(),
+        grid_available=np.ones(n, dtype=bool),
+        year_type="typhoon",
+        ghi_multiplier=mult,
+    )
+
+    result_df = apply_ghi_multiplier(weather_df, sched)
+
+    # Immutability check: original weather_df untouched
+    assert np.all(weather_df["ghi"].to_numpy() == 500.0)
+
+    # Transformed check
+    expected_ghi = np.array([500.0] * n, dtype=np.float64)
+    expected_ghi[4:10] = 125.0
+    assert np.allclose(result_df["ghi"].to_numpy(), expected_ghi)
+
+
+def test_apply_ghi_multiplier_validation_errors():
+    """Verify input validation errors for apply_ghi_multiplier."""
+    sched = OutageSchedule(
+        events=(),
+        grid_available=np.ones(10, dtype=bool),
+        year_type="normal",
+    )
+
+    # Not a DataFrame
+    with pytest.raises(TypeError, match="must be a pandas DataFrame"):
+        apply_ghi_multiplier({"ghi": [100.0] * 10}, sched)  # type: ignore
+
+    # Missing 'ghi' column
+    df_missing_ghi = pd.DataFrame({"t_amb": [25.0] * 10})
+    with pytest.raises(ValueError, match="must contain a 'ghi' column"):
+        apply_ghi_multiplier(df_missing_ghi, sched)
+
+    # Length mismatch
+    df_mismatched_len = pd.DataFrame({"ghi": [100.0] * 5})
+    with pytest.raises(ValueError, match="Length mismatch"):
+        apply_ghi_multiplier(df_mismatched_len, sched)
+
+
+# ===========================================================================
+# 8. Contract Signature Conformance & Horizon Flexibility
+# ===========================================================================
+
+def test_contract_signature_conformance():
+    """Verify sample_outage_schedule adheres strictly to interface contracts."""
+    rng = np.random.default_rng(101)
+
+    # Default n_hours = 8760
+    sched = sample_outage_schedule("normal", rng)
+    assert len(sched) == DEFAULT_ANNUAL_HOURS
+    assert len(sched.grid_available) == DEFAULT_ANNUAL_HOURS
+    assert len(sched.ghi_multiplier) == DEFAULT_ANNUAL_HOURS
+
+    # Custom horizon n_hours = 168 (1 week)
+    sched_week = sample_outage_schedule("typhoon", rng, n_hours=168)
+    assert len(sched_week) == 168
+    assert len(sched_week.grid_available) == 168
+    assert len(sched_week.ghi_multiplier) == 168
+
+    # Invalid regime
+    with pytest.raises(ValueError, match="year_type must be 'normal' or 'typhoon'"):
+        sample_outage_schedule("unsupported_regime", rng)
+
+    # Invalid n_hours
+    with pytest.raises(ValueError, match="n_hours must be positive"):
+        sample_outage_schedule("normal", rng, n_hours=0)
+
+
+def test_zero_arrival_case():
+    """Verify handling when Poisson draw yields zero events."""
+    # Mock RNG that returns 0 for poisson
+    class ZeroPoissonRNG:
+        def poisson(self, lam: float) -> int:
+            return 0
+
+    sched = sample_outage_schedule("normal", ZeroPoissonRNG())  # type: ignore
+    assert len(sched.events) == 0
+    assert np.all(sched.grid_available)
+    assert np.all(sched.ghi_multiplier == 1.0)
```

---

## 6. Flagged for APC / Operator Attention

- [ ] **Typhoon Solar Depression Multiplier Interpretation (`[D-33]`)**: As noted in `OUT-001-PROMPT.md`, [D-11] wording ("20–30% normal GHI") was interpreted as an attenuation factor $m \in [0.20, 0.30]$ rather than a 20%–30% reduction. Confirmed in [D-33]; please verify this meets the simulation expectations.
- [ ] **Uniform Arrival vs. Seasonal Clustering**: Outage arrival start hours are sampled uniformly over the annual 8,760 hours. While Philippine typhoons predominantly occur during the monsoon season (June–November), homogeneous Poisson arrivals are used pending seasonal hazard rate data.
- [ ] **Phase 2 Complete**: All eight sub-model tracks (`DEM-001`, `DEM-002`, `SOL-001`, `SOL-002`, `BAT-001`, `BAT-002`, `OUT-001`, `OUT-002`) are now implemented and tested on their respective branches/worktrees. The repository is ready for full integration under `INT-001`.
