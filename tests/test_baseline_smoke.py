"""Unit and integration tests for baseline grid-only simulation (CORE-005 Phase 1 Exit Gate).

Validates:
1. HourlyRecord series structure (8,760 hours, chronological 1..8760, ISO timestamps).
2. Determinism (same inputs produce identical records).
3. Zero-solar, zero-battery dispatch contracts.
4. Energy balance verification harness conformance (zero residuals, zero drift).
5. Battery handling (both battery=None and battery=Battery(capacity_kwh=0.0) pass).
6. Negative control: proves harness fails when deliberate leaks/biases are injected.
7. Headline KPI metrics & calibration conformance (EUI within 150-300 kWh/m²·yr band, target 159.41).
8. Climate sensitivity sanity: 2016 El Niño hot-year peak exceeds 2019 baseline peak.
"""

from __future__ import annotations

import copy
import pytest

from ccis_sim.core.models import Battery, Building, HourlyRecord, LoadTier
from ccis_sim.core.verification import (
    assert_simulation_valid,
    run_verification_harness,
)
from ccis_sim.integration import (
    CALIBRATION_FACTOR_2019,
    BaselineMetrics,
    compute_baseline_metrics,
    run_baseline_simulation,
    simulate_baseline,
)


# =========================================================================
# CORE-005.1: Simulation Execution & Dispatch Contracts
# =========================================================================


def test_baseline_simulation_record_count_and_hours():
    """Verify that baseline simulation generates exactly 8,760 records numbered 1 to 8760."""
    records, metrics = run_baseline_simulation(weather_fixture=2019)

    assert len(records) == 8760
    assert records[0].hour == 1
    assert records[-1].hour == 8760

    # Sequential hour integrity
    for i, r in enumerate(records, start=1):
        assert r.hour == i
        assert "+08:00" in r.timestamp
        assert "T" in r.timestamp


def test_baseline_simulation_dispatch_invariants():
    """Verify zero-solar, zero-battery, grid-only dispatch contracts for every hour."""
    records, _ = run_baseline_simulation(weather_fixture=2019)

    for r in records:
        # Zero solar contracts
        assert r.solar_generation_kwh == 0.0
        assert r.solar_to_demand_kwh == 0.0
        assert r.solar_to_battery_kwh == 0.0
        assert r.solar_curtailed_kwh == 0.0

        # Zero battery contracts
        assert r.battery_soc_kwh == 0.0
        assert r.battery_charge_kwh == 0.0
        assert r.battery_discharge_kwh == 0.0

        # Grid-only supply contracts
        assert r.grid_available is True
        assert r.active_load_tier == LoadTier.TIER_3_SHEDDABLE
        assert r.unserved_load_kwh == 0.0
        assert r.grid_import_kwh == pytest.approx(r.demand_served_kwh, abs=1e-9)
        assert r.demand_served_kwh == pytest.approx(r.demand_gross_kwh, abs=1e-9)
        assert r.grid_import_kwh > 0.0


def test_baseline_simulation_determinism():
    """Verify that identical inputs produce bitwise identical records across separate runs."""
    records_run1 = simulate_baseline(weather_fixture=2019)
    records_run2 = simulate_baseline(weather_fixture=2019)

    assert len(records_run1) == len(records_run2) == 8760
    for r1, r2 in zip(records_run1, records_run2):
        assert r1 == r2


# =========================================================================
# CORE-005.2: Verification Harness & Negative Control
# =========================================================================


def test_baseline_simulation_passes_verification_harness():
    """Verify that 8,760 baseline records pass the CORE-004 verification harness with 0 violations."""
    records, _ = run_baseline_simulation(weather_fixture=2019)

    # 1. Verification with battery=None (standard grid-only simulation)
    report_none = run_verification_harness(records, battery=None)
    assert report_none.is_valid
    assert len(report_none.conservation_violations) == 0
    assert len(report_none.battery_violations) == 0
    assert report_none.cumulative_conserved
    assert report_none.max_residual_kwh <= 1e-12

    # 2. Verification with zero-capacity Battery (tests 0 kWh boundary conformance)
    zero_battery = Battery(capacity_kwh=0.0)
    report_zero_bat = run_verification_harness(records, battery=zero_battery)
    assert report_zero_bat.is_valid
    assert len(report_zero_bat.battery_violations) == 0

    # 3. Direct assertion helper does not raise
    assert_simulation_valid(records, battery=None)
    assert_simulation_valid(records, battery=zero_battery)


def test_baseline_negative_control_single_hour_violation_caught():
    """Negative control: tampering with a single hour's energy balance must cause harness failure."""
    records = simulate_baseline(weather_fixture=2019)

    # Tamper with Hour 500: inject 1.0 kWh phantom energy deficit
    r = records[499]
    leaky_rec = HourlyRecord(
        hour=r.hour,
        timestamp=r.timestamp,
        temp_ambient_c=r.temp_ambient_c,
        humidity_rel_pct=r.humidity_rel_pct,
        ghi_w_m2=r.ghi_w_m2,
        demand_gross_kwh=r.demand_gross_kwh,
        demand_served_kwh=r.demand_served_kwh,
        solar_generation_kwh=r.solar_generation_kwh,
        solar_to_demand_kwh=r.solar_to_demand_kwh,
        solar_to_battery_kwh=r.solar_to_battery_kwh,
        solar_curtailed_kwh=r.solar_curtailed_kwh,
        battery_soc_kwh=r.battery_soc_kwh,
        battery_charge_kwh=r.battery_charge_kwh,
        battery_discharge_kwh=r.battery_discharge_kwh,
        grid_import_kwh=r.grid_import_kwh - 1.0,  # Under-supplied by 1.0 kWh!
        unserved_load_kwh=r.unserved_load_kwh,
        grid_available=r.grid_available,
        active_load_tier=r.active_load_tier,
    )
    records[499] = leaky_rec

    report = run_verification_harness(records)
    assert not report.is_valid
    assert len(report.conservation_violations) == 1
    assert report.conservation_violations[0].hour == 500

    with pytest.raises(AssertionError, match="Simulation verification failed"):
        assert_simulation_valid(records)


def test_baseline_negative_control_cumulative_drift_caught():
    """Negative control: small persistent bias (0.9e-5 kWh/hr) passing hourly checks must fail cumulative check."""
    records = simulate_baseline(weather_fixture=2019)

    # Inject +0.9e-5 kWh into every hour's grid import (passes per-hour 1e-5 tolerance)
    biased_records: list[HourlyRecord] = []
    for r in records:
        biased = HourlyRecord(
            hour=r.hour,
            timestamp=r.timestamp,
            temp_ambient_c=r.temp_ambient_c,
            humidity_rel_pct=r.humidity_rel_pct,
            ghi_w_m2=r.ghi_w_m2,
            demand_gross_kwh=r.demand_gross_kwh,
            demand_served_kwh=r.demand_served_kwh,
            solar_generation_kwh=r.solar_generation_kwh,
            solar_to_demand_kwh=r.solar_to_demand_kwh,
            solar_to_battery_kwh=r.solar_to_battery_kwh,
            solar_curtailed_kwh=r.solar_curtailed_kwh,
            battery_soc_kwh=r.battery_soc_kwh,
            battery_charge_kwh=r.battery_charge_kwh,
            battery_discharge_kwh=r.battery_discharge_kwh,
            grid_import_kwh=r.grid_import_kwh + 0.9e-5,  # Persistent upward bias
            unserved_load_kwh=r.unserved_load_kwh,
            grid_available=r.grid_available,
            active_load_tier=r.active_load_tier,
        )
        assert biased.is_energy_conserved(tolerance=1e-5)
        biased_records.append(biased)

    report = run_verification_harness(biased_records)
    assert not report.is_valid
    assert len(report.conservation_violations) == 0  # No hourly failures
    assert not report.cumulative_conserved           # Cumulative drift trips!

    with pytest.raises(AssertionError, match="Simulation verification failed"):
        assert_simulation_valid(biased_records)


# =========================================================================
# CORE-005.3: Baseline Headline Metrics & Climate Sensitivity
# =========================================================================


def test_baseline_headline_metrics_committed_values():
    """Commit 2019 baseline headline numbers as expected values with explicit tolerance."""
    records, metrics = run_baseline_simulation(weather_fixture=2019)

    # 1. Calibration target: exactly 398,525.0 kWh (+/- 0.01%)
    EXPECTED_ANNUAL_KWH = 398525.00
    EXPECTED_EUI = 159.4100
    EXPECTED_PEAK_KW = 124.44
    EXPECTED_PEAK_HOUR = 2030
    EXPECTED_PEAK_TS = "2019-03-26T13:00:00+08:00"
    EXPECTED_LOAD_FACTOR = 0.3656

    assert metrics.annual_energy_kwh == pytest.approx(EXPECTED_ANNUAL_KWH, rel=1e-4)
    assert metrics.eui_kwh_per_m2_year == pytest.approx(EXPECTED_EUI, rel=1e-4)
    assert metrics.peak_demand_kw == pytest.approx(EXPECTED_PEAK_KW, abs=0.1)
    assert metrics.peak_hour == EXPECTED_PEAK_HOUR
    assert metrics.peak_timestamp == EXPECTED_PEAK_TS
    assert metrics.load_factor == pytest.approx(EXPECTED_LOAD_FACTOR, abs=0.01)

    # 2. Regional EUI benchmark band (150 - 300 kWh/m²·yr) conformance
    assert 150.0 <= metrics.eui_kwh_per_m2_year <= 300.0

    # 3. Monthly sum adds up to annual total
    assert sum(metrics.monthly_energy_kwh.values()) == pytest.approx(EXPECTED_ANNUAL_KWH, rel=1e-5)


def test_climate_sensitivity_2016_hot_year_versus_2019():
    """Verify 2016 anomalous hot year sensitivity produces higher peak demand than 2019."""
    _, metrics_2019 = run_baseline_simulation(weather_fixture=2019)
    _, metrics_2016 = run_baseline_simulation(weather_fixture=2016)

    # 2016 El Niño hot year peak demand MUST exceed 2019 peak demand
    assert metrics_2016.peak_demand_kw > metrics_2019.peak_demand_kw
    peak_delta_kw = metrics_2016.peak_demand_kw - metrics_2019.peak_demand_kw
    assert peak_delta_kw > 1.0  # +1.11 kW increase due to peak afternoon heat

    # 2016 annual EUI remains in valid benchmark band (150-300 kWh/m²·yr)
    assert 150.0 <= metrics_2016.eui_kwh_per_m2_year <= 300.0
    assert metrics_2016.eui_kwh_per_m2_year == pytest.approx(159.30, abs=0.5)
