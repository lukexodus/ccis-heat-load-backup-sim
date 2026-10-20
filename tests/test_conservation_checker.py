"""Unit tests for verification harness and invariant checker (CORE-004).

Tests strict hourly and cumulative energy balance conservation, battery boundary
validation, and the shared golden reference fixture.
"""

from __future__ import annotations

import pytest

from ccis_sim.core import (
    Battery,
    HourlyRecord,
    ViolationType,
    assert_simulation_valid,
    check_energy_conservation,
    compute_cumulative_tolerance,
    create_golden_scenario,
    run_verification_harness,
    validate_battery_boundaries,
)


def _make_dummy_record(
    hour: int = 1,
    solar_gen: float = 0.0,
    grid_import: float = 10.0,
    bat_dis: float = 0.0,
    demand_served: float = 10.0,
    bat_chg: float = 0.0,
    solar_curt: float = 0.0,
    soc: float = 50.0,
    grid_avail: bool = True,
    tier: int = 3,
) -> HourlyRecord:
    """Helper to construct a single HourlyRecord with specific energy flows."""
    return HourlyRecord(
        hour=hour,
        timestamp=f"2026-04-15T{((hour - 1) % 24):02d}:00:00+08:00",
        temp_ambient_c=25.0,
        humidity_rel_pct=70.0,
        ghi_w_m2=solar_gen * 10.0,
        demand_gross_kwh=demand_served,
        demand_served_kwh=demand_served,
        solar_generation_kwh=solar_gen,
        solar_to_demand_kwh=min(solar_gen, demand_served),
        solar_to_battery_kwh=bat_chg,
        solar_curtailed_kwh=solar_curt,
        battery_soc_kwh=soc,
        battery_charge_kwh=bat_chg,
        battery_discharge_kwh=bat_dis,
        grid_import_kwh=grid_import,
        unserved_load_kwh=0.0,
        grid_available=grid_avail,
        active_load_tier=tier,
    )


# =========================================================================
# CORE-004.1: Energy Conservation Checker Tests
# =========================================================================


def test_golden_scenario_conservation_passes():
    """Verify that the 48-hour golden reference scenario satisfies strict conservation."""
    records = create_golden_scenario()
    assert len(records) == 48

    violations = check_energy_conservation(records, tolerance=1e-5)
    assert len(violations) == 0

    report = run_verification_harness(records)
    assert report.is_valid
    assert report.cumulative_conserved
    assert report.max_residual_kwh <= 1e-12
    assert "PASSED" in report.summary()


def test_deliberate_hourly_residual_violation_caught():
    """Verify that a single unphysical imbalance (> 1e-5 kWh) is caught with exact diagnostics."""
    records = create_golden_scenario()

    # Tamper with Hour 12: inject 0.5 kWh unphysical energy imbalance
    tampered_rec = HourlyRecord(
        hour=12,
        timestamp=records[11].timestamp,
        temp_ambient_c=records[11].temp_ambient_c,
        humidity_rel_pct=records[11].humidity_rel_pct,
        ghi_w_m2=records[11].ghi_w_m2,
        demand_gross_kwh=records[11].demand_gross_kwh,
        demand_served_kwh=records[11].demand_served_kwh + 0.5,  # Unbalanced +0.5 kWh out
        solar_generation_kwh=records[11].solar_generation_kwh,
        solar_to_demand_kwh=records[11].solar_to_demand_kwh,
        solar_to_battery_kwh=records[11].solar_to_battery_kwh,
        solar_curtailed_kwh=records[11].solar_curtailed_kwh,
        battery_soc_kwh=records[11].battery_soc_kwh,
        battery_charge_kwh=records[11].battery_charge_kwh,
        battery_discharge_kwh=records[11].battery_discharge_kwh,
        grid_import_kwh=records[11].grid_import_kwh,
        unserved_load_kwh=records[11].unserved_load_kwh,
        grid_available=records[11].grid_available,
        active_load_tier=records[11].active_load_tier,
    )
    records[11] = tampered_rec

    violations = check_energy_conservation(records, tolerance=1e-5)
    assert len(violations) >= 1

    hourly_violations = [v for v in violations if v.violation_type == ViolationType.HOURLY_ENERGY_BALANCE]
    assert len(hourly_violations) == 1
    v = hourly_violations[0]
    assert v.hour == 12
    assert abs(v.residual_kwh - 0.5) < 1e-9
    assert v.tolerance_kwh == 1e-5
    assert "Hour 12" in v.summary()

    report = run_verification_harness(records)
    assert not report.is_valid
    assert len(report.conservation_violations) == 1

    with pytest.raises(AssertionError, match="Simulation verification failed"):
        assert_simulation_valid(records)


def test_cumulative_drift_catches_small_consistent_bias():
    """Verify that a small persistent bias (0.9e-5 kWh/hr) passes individual checks but trips cumulative check.

    Over 8,760 hours:
    - Per-hour residual = 0.9e-5 kWh <= 1e-5 kWh (individually valid).
    - Cumulative drift = 8,760 * 0.9e-5 = 0.07884 kWh.
    - Cumulative tolerance = sqrt(8760) * 1e-5 ~= 9.359e-4 kWh.
    - Since 0.07884 >> 9.359e-4, the cumulative invariant trips.
    """
    bias_per_hour = 0.9e-5  # Under per-hour 1e-5 tolerance
    records: list[HourlyRecord] = []

    for h in range(1, 8761):
        rec = _make_dummy_record(
            hour=h,
            solar_gen=0.0,
            grid_import=10.0 + bias_per_hour,  # Persistent upward bias
            bat_dis=0.0,
            demand_served=10.0,
            bat_chg=0.0,
            solar_curt=0.0,
            soc=50.0,
        )
        assert rec.is_energy_conserved(tolerance=1e-5), f"Hour {h} should individually pass!"
        records.append(rec)

    # All 8,760 hours pass individual tolerance check
    violations = check_energy_conservation(records, tolerance=1e-5)
    hourly_violations = [v for v in violations if v.violation_type == ViolationType.HOURLY_ENERGY_BALANCE]
    assert len(hourly_violations) == 0, "Individual hours must not trip per-hour check"

    # Cumulative check trips
    cumulative_violations = [
        v for v in violations if v.violation_type == ViolationType.CUMULATIVE_ENERGY_BALANCE
    ]
    assert len(cumulative_violations) == 1
    cum_v = cumulative_violations[0]
    assert cum_v.hour == 0
    assert abs(cum_v.residual_kwh - (8760 * bias_per_hour)) < 1e-6
    expected_cum_tol = compute_cumulative_tolerance(8760, 1e-5)
    assert abs(cum_v.tolerance_kwh - expected_cum_tol) < 1e-9

    # Verification report reflects cumulative failure
    report = run_verification_harness(records, tolerance=1e-5)
    assert not report.is_valid
    assert not report.cumulative_conserved
    assert report.total_violations == 1
    assert "FAILED" in report.summary()


def test_cumulative_tolerance_computation():
    """Verify compute_cumulative_tolerance scaling rules per [D-21]."""
    # 0 or negative records
    assert compute_cumulative_tolerance(0, 1e-5) == 1e-5
    assert compute_cumulative_tolerance(-10, 1e-5) == 1e-5

    # Small records where sqrt(N) <= 1
    assert compute_cumulative_tolerance(1, 1e-5) == 1e-5

    # Annual run N=8,760
    tol_8760 = compute_cumulative_tolerance(8760, 1e-5)
    expected = (8760**0.5) * 1e-5
    assert abs(tol_8760 - expected) < 1e-12
    assert 0.0009 < tol_8760 < 0.0010


# =========================================================================
# CORE-004.2: Battery Boundary Validator Tests
# =========================================================================


def test_battery_negative_soc_caught():
    """Verify that physically negative SoC is caught."""
    bat = Battery(capacity_kwh=100.0)
    rec = _make_dummy_record(hour=1, soc=-0.5)

    violations = validate_battery_boundaries([rec], battery=bat)
    assert len(violations) == 2  # Negative SoC and below min_soc floor
    neg_violations = [v for v in violations if v.violation_type == ViolationType.NEGATIVE_SOC]
    assert len(neg_violations) == 1
    assert neg_violations[0].actual_value == -0.5
    assert neg_violations[0].limit_value == 0.0


def test_battery_exceeds_capacity_caught():
    """Verify that SoC exceeding rated nameplate capacity is caught."""
    bat = Battery(capacity_kwh=100.0)
    rec = _make_dummy_record(hour=1, soc=105.0)

    violations = validate_battery_boundaries([rec], battery=bat)
    assert len(violations) == 1
    assert violations[0].violation_type == ViolationType.EXCEEDS_CAPACITY
    assert violations[0].actual_value == 105.0
    assert violations[0].limit_value == 100.0


def test_battery_min_soc_floor_normal_vs_emergency():
    """Verify min_soc floor protection and emergency drawdown rules."""
    bat = Battery(capacity_kwh=100.0, min_soc_pct=0.10)  # min_soc = 10.0 kWh

    # Case 1: Grid available (normal operation), SoC below floor (5.0 kWh) -> FAILS
    rec_normal = _make_dummy_record(hour=1, soc=5.0, grid_avail=True, tier=3)
    violations = validate_battery_boundaries([rec_normal], battery=bat, allow_emergency_drawdown=False)
    assert len(violations) == 1
    assert violations[0].violation_type == ViolationType.MIN_SOC_VIOLATION
    assert violations[0].limit_value == 10.0

    # Even with allow_emergency_drawdown=True, normal operation must NOT allow drawdown below min_soc
    violations_normal_drawdown = validate_battery_boundaries(
        [rec_normal], battery=bat, allow_emergency_drawdown=True
    )
    assert len(violations_normal_drawdown) == 1
    assert violations_normal_drawdown[0].violation_type == ViolationType.MIN_SOC_VIOLATION

    # Case 2: Outage condition (grid_avail=False, tier=2), allow_emergency_drawdown=False -> FAILS
    rec_outage = _make_dummy_record(hour=2, soc=5.0, grid_avail=False, tier=2)
    violations_outage_no_drawdown = validate_battery_boundaries(
        [rec_outage], battery=bat, allow_emergency_drawdown=False
    )
    assert len(violations_outage_no_drawdown) == 1
    assert violations_outage_no_drawdown[0].violation_type == ViolationType.MIN_SOC_VIOLATION

    # Case 3: Outage condition (grid_avail=False, tier=2), allow_emergency_drawdown=True -> PASSES
    violations_outage_allowed = validate_battery_boundaries(
        [rec_outage], battery=bat, allow_emergency_drawdown=True
    )
    assert len(violations_outage_allowed) == 0


def test_battery_charge_c_rate_exceeded_caught():
    """Verify that charge rate exceeding max_charge_power_kw is caught."""
    bat = Battery(capacity_kwh=100.0, max_charge_c_rate=0.5)  # 50.0 kW limit
    rec = _make_dummy_record(hour=1, bat_chg=55.0, solar_curt=0.0, solar_gen=55.0, grid_import=0.0)

    violations = validate_battery_boundaries([rec], battery=bat)
    c_violations = [v for v in violations if v.violation_type == ViolationType.CHARGE_RATE_EXCEEDED]
    assert len(c_violations) == 1
    assert c_violations[0].actual_value == 55.0
    assert c_violations[0].limit_value == 50.0


def test_battery_discharge_c_rate_exceeded_caught():
    """Verify that discharge rate exceeding max_discharge_power_kw is caught."""
    bat = Battery(capacity_kwh=100.0, max_discharge_c_rate=1.0)  # 100.0 kW limit
    rec = _make_dummy_record(hour=1, bat_dis=110.0, demand_served=110.0, grid_import=0.0)

    violations = validate_battery_boundaries([rec], battery=bat)
    d_violations = [v for v in violations if v.violation_type == ViolationType.DISCHARGE_RATE_EXCEEDED]
    assert len(d_violations) == 1
    assert d_violations[0].actual_value == 110.0
    assert d_violations[0].limit_value == 100.0


def test_simultaneous_charge_and_discharge_caught():
    """Verify that simultaneous charging and discharging in the same hour is caught."""
    bat = Battery(capacity_kwh=100.0)
    rec = _make_dummy_record(hour=1, bat_chg=15.0, bat_dis=10.0)

    violations = validate_battery_boundaries([rec], battery=bat)
    sim_violations = [
        v for v in violations if v.violation_type == ViolationType.SIMULTANEOUS_CHARGE_DISCHARGE
    ]
    assert len(sim_violations) == 1
    assert sim_violations[0].actual_value == 10.0
    assert "Simultaneous charge" in sim_violations[0].details


# =========================================================================
# CORE-004.3: Golden Fixture & Verification Harness Integration
# =========================================================================


def test_golden_scenario_battery_and_conservation_fully_valid():
    """Verify that the 48-hour golden fixture satisfies all boundary conditions and invariants."""
    battery = Battery(capacity_kwh=100.0)
    records = create_golden_scenario(battery=battery)

    # 1. Assert full verification harness
    report = run_verification_harness(records, battery=battery)
    assert report.is_valid
    assert len(report.conservation_violations) == 0
    assert len(report.battery_violations) == 0
    assert report.cumulative_conserved
    assert report.total_records == 48

    # 2. Test assertion function does not raise
    assert_simulation_valid(records, battery=battery)

    # 3. Check specific scenario characteristics
    # Hour 15 has exact zero net-load balance (solar == demand)
    h15 = records[14]
    assert h15.hour == 15
    assert h15.solar_generation_kwh == h15.demand_served_kwh
    assert h15.grid_import_kwh == 0.0
    assert h15.battery_charge_kwh == 0.0
    assert h15.battery_discharge_kwh == 0.0

    # Hours 30-37 simulate outage event
    outage_records = records[29:37]
    assert all(not r.grid_available for r in outage_records)
    assert all(r.active_load_tier == 2 for r in outage_records)
    assert all(r.unserved_load_kwh == 20.0 for r in outage_records)  # 25 gross - 5 served


def test_empty_records_handling():
    """Verify that empty sequences return valid clean reports without crashing."""
    assert check_energy_conservation([]) == []
    bat = Battery(capacity_kwh=100.0)
    assert validate_battery_boundaries([], battery=bat) == []

    report = run_verification_harness([])
    assert report.is_valid
    assert report.total_records == 0
    assert report.max_residual_kwh == 0.0
