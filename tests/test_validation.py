"""Comprehensive test suite for simulation verification, plausibility, and sensitivity (INT-003).

Tests:
1. Physical conservation invariant audits across 8+ configurations.
2. Seed reproducibility (identical hash on same seed, divergence on different seed).
3. Negative controls (deliberate +1e-3 kWh residual, SoC below min_soc, NaN).
4. ASHRAE Guideline 14 statistical metrics calculation and plausibility checks.
5. Solar yield reconciliation (POA x PR vs Luzon target).
6. One-at-a-time (OAT) parameter sensitivity sweeps.
"""

from __future__ import annotations

import dataclasses
import hashlib
import math
import tempfile
from pathlib import Path

import pytest

from ccis_sim.core.models import Battery, HourlyRecord
from ccis_sim.core.verification import assert_simulation_valid
from ccis_sim.demand.mock_bills import SyntheticBillGenerator
from ccis_sim.integration.engine import SimulationConfig, simulate
from ccis_sim.integration.exporters import export_hourly_csv
from ccis_sim.validation.audit import AuditResult, audit_run
from ccis_sim.validation.plausibility import (
    compute_ashrae_metrics,
    compute_plausibility_summary,
    reconcile_solar_yield,
)
from ccis_sim.validation.sensitivity import run_oat_sensitivity_analysis


# ==============================================================================
# 1. Physical Conservation Invariant Audits (8 Standard Configurations)
# ==============================================================================


@pytest.mark.parametrize(
    ("solar_kwp", "battery_kwh", "year", "regime"),
    [
        # 4 Core Configurations under 2019 Normal
        (0.0, 0.0, 2019, "normal"),
        (100.0, 0.0, 2019, "normal"),
        (100.0, 100.0, 2019, "normal"),
        (200.0, 200.0, 2019, "normal"),
        # 4 Core Configurations under 2019 Typhoon
        (0.0, 0.0, 2019, "typhoon"),
        (100.0, 0.0, 2019, "typhoon"),
        (100.0, 100.0, 2019, "typhoon"),
        (200.0, 200.0, 2019, "typhoon"),
    ],
)
def test_standard_8_configurations_audit_pass(
    solar_kwp: float,
    battery_kwh: float,
    year: int,
    regime: str,
):
    """Verify that all 8 primary configuration combinations strictly pass invariant audits."""
    cfg = SimulationConfig(
        solar_kwp=solar_kwp,
        battery_kwh=battery_kwh,
        weather_year=year,
        outage_regime=regime,
        seed=0,
    )
    result = audit_run(cfg, tolerance=1e-5)

    assert result.passed is True, f"Audit failed for {result.summary()}"
    assert result.max_hourly_residual <= 1e-5, f"Max residual {result.max_hourly_residual} > 1e-5"
    assert abs(result.cumulative_residual) <= 1e-3, f"Cumulative drift {result.cumulative_residual} > 1e-3"
    assert result.soc_within_bounds is True, f"SoC outside bounds: [{result.min_soc_observed}, {result.max_soc_observed}]"
    assert result.non_finite_count == 0, f"Found {result.non_finite_count} non-finite values"
    assert result.tier_conservation_passed is True, "Tier demand conservation violated"


def test_2016_hot_year_audit_pass():
    """Verify that 2016 El Niño hot year configurations also pass audit invariants."""
    for solar, bat in ((0.0, 0.0), (100.0, 100.0), (200.0, 200.0)):
        cfg = SimulationConfig(
            solar_kwp=solar,
            battery_kwh=bat,
            weather_year=2016,
            outage_regime="normal",
            seed=0,
        )
        res = audit_run(cfg)
        assert res.passed is True, f"2016 hot year audit failed: {res.summary()}"


# ==============================================================================
# 2. Seed Reproducibility
# ==============================================================================


def test_seed_reproducibility_identical_hash():
    """Verify that identical random seeds yield bit-identical hourly CSV artifacts."""
    cfg1 = SimulationConfig(solar_kwp=100.0, battery_kwh=100.0, weather_year=2019, outage_regime="normal", seed=42)
    cfg2 = SimulationConfig(solar_kwp=100.0, battery_kwh=100.0, weather_year=2019, outage_regime="normal", seed=42)

    res1 = simulate(cfg1)
    res2 = simulate(cfg2)

    with tempfile.TemporaryDirectory() as td:
        p1 = export_hourly_csv(res1.records, Path(td) / "run1.csv")
        p2 = export_hourly_csv(res2.records, Path(td) / "run2.csv")

        hash1 = hashlib.sha256(p1.read_bytes()).hexdigest()
        hash2 = hashlib.sha256(p2.read_bytes()).hexdigest()

    assert hash1 == hash2, f"CSV hashes differed on identical seed 42: {hash1} != {hash2}"


def test_seed_reproducibility_different_outages():
    """Verify that differing random seeds generate distinct stochastic outage schedules."""
    cfg1 = SimulationConfig(solar_kwp=100.0, battery_kwh=100.0, weather_year=2019, outage_regime="normal", seed=42)
    cfg3 = SimulationConfig(solar_kwp=100.0, battery_kwh=100.0, weather_year=2019, outage_regime="normal", seed=43)

    res1 = simulate(cfg1)
    res3 = simulate(cfg3)

    # Grid availability arrays must differ
    diff_hours = (res1.outage_schedule.grid_available != res3.outage_schedule.grid_available).sum()
    assert diff_hours > 0, "Outage schedules should differ between seeds 42 and 43"

    with tempfile.TemporaryDirectory() as td:
        p1 = export_hourly_csv(res1.records, Path(td) / "run1.csv")
        p3 = export_hourly_csv(res3.records, Path(td) / "run3.csv")

        hash1 = hashlib.sha256(p1.read_bytes()).hexdigest()
        hash3 = hashlib.sha256(p3.read_bytes()).hexdigest()

    assert hash1 != hash3, "Hourly CSV hashes should differ between different seeds"


# ==============================================================================
# 3. Negative Controls (Caught by assert_simulation_valid)
# ==============================================================================


@pytest.fixture
def clean_records() -> tuple[list[HourlyRecord], Battery]:
    """Provide a validated 48-hour sequence of simulation records and active battery."""
    cfg = SimulationConfig(solar_kwp=100.0, battery_kwh=100.0, weather_year=2019, outage_regime="normal", seed=0)
    res = simulate(cfg)
    bat = Battery(capacity_kwh=100.0)
    # Take first 48 hours for fast negative control testing
    records = list(res.records[:48])
    # Baseline assertion must pass
    assert_simulation_valid(records=records, battery=bat, initial_soc_kwh=100.0)
    return records, bat


def test_negative_control_residual_perturbation(clean_records):
    """Negative Control 1: An injected +1e-3 kWh residual must be caught by assert_simulation_valid.

    Cites test_deliberate_hourly_residual_violation_caught in tests/test_conservation_checker.py.
    """
    records, bat = clean_records
    # Perturb hour 10: add 1e-3 kWh to grid_import without balancing demand or battery
    perturbed_records = list(records)
    r = perturbed_records[10]
    bad_record = dataclasses.replace(r, grid_import_kwh=r.grid_import_kwh + 1e-3)
    perturbed_records[10] = bad_record

    with pytest.raises(AssertionError) as exc_info:
        assert_simulation_valid(records=perturbed_records, battery=bat, initial_soc_kwh=100.0)
    assert "energy balance residual" in str(exc_info.value).lower()


def test_negative_control_soc_below_min_floor(clean_records):
    """Negative Control 2: An SoC below min_soc floor (10 kWh for 100 kWh battery) must be caught.

    Cites test_battery_min_soc_floor_normal_vs_emergency in tests/test_conservation_checker.py.
    """
    records, bat = clean_records
    perturbed_records = list(records)
    # Battery capacity is 100 kWh, min_soc floor is 10 kWh. Set SoC to 5 kWh.
    r = perturbed_records[15]
    bad_record = dataclasses.replace(r, battery_soc_kwh=5.0)
    perturbed_records[15] = bad_record

    with pytest.raises(AssertionError) as exc_info:
        assert_simulation_valid(records=perturbed_records, battery=bat, initial_soc_kwh=100.0)
    assert "min_soc_violation" in str(exc_info.value) or "soc_continuity" in str(exc_info.value)


def test_negative_control_nan_value(clean_records):
    """Negative Control 3: An injected NaN in numeric fields must be caught.

    Cites test_non_finite_value_caught_in_conservation in tests/test_conservation_checker.py.
    """
    records, bat = clean_records
    perturbed_records = list(records)
    r = perturbed_records[20]
    bad_record = dataclasses.replace(r, solar_generation_kwh=float("nan"))
    perturbed_records[20] = bad_record

    with pytest.raises(AssertionError) as exc_info:
        assert_simulation_valid(records=perturbed_records, battery=bat, initial_soc_kwh=100.0)
    assert "non-finite" in str(exc_info.value).lower()


# ==============================================================================
# 4. Plausibility & ASHRAE Guideline 14 Metrics
# ==============================================================================


def test_ashrae_guideline_14_metrics_and_synthetic_bills():
    """Verify ASHRAE Guideline 14 calculation against synthetic mock utility bills."""
    bills_path = Path("data/fixtures/synthetic-mock-bills-ccis.csv")
    bills = SyntheticBillGenerator.load_from_csv(bills_path)
    bill_monthly = [b.total_kwh for b in bills]

    cfg = SimulationConfig(solar_kwp=0.0, battery_kwh=0.0, weather_year=2019, outage_regime="normal", seed=0)
    res = simulate(cfg)

    summary = compute_plausibility_summary(res.records)
    sim_monthly = summary.monthly_profile_kwh

    metrics = compute_ashrae_metrics(sim_monthly=sim_monthly, measured_monthly=bill_monthly)

    assert metrics.n_periods == 12
    # Bottom-up uncalibrated is ~189,356 kWh vs mock bills ~398,537 kWh (-52.5% uncalibrated gap)
    assert pytest.approx(metrics.sim_total_kwh, rel=1e-3) == 189355.61
    assert pytest.approx(metrics.measured_total_kwh, rel=1e-3) == 398536.77
    assert metrics.nmbe_pct < -50.0
    assert metrics.cv_rmse_pct > 50.0
    # Because it is uncalibrated bottom-up demand, it intentionally does NOT pass the ASHRAE ±5% monthly threshold
    assert metrics.ashrae_monthly_pass is False


def test_plausibility_summary_day_type_means():
    """Verify that regular academic weekdays consume significantly more than weekends and vacations."""
    cfg = SimulationConfig(solar_kwp=0.0, battery_kwh=0.0, weather_year=2019, outage_regime="normal", seed=0)
    res = simulate(cfg)
    summary = compute_plausibility_summary(res.records)

    assert summary.weekday_mean_kwh_per_day > summary.weekend_mean_kwh_per_day
    assert summary.weekend_mean_kwh_per_day > summary.vacation_mean_kwh_per_day
    assert summary.gross_eui_kwh_per_m2 == pytest.approx(75.74, abs=0.1)
    assert summary.peak_demand_kw == pytest.approx(95.71, abs=0.1)


def test_solar_yield_reconciliation():
    """Verify solar specific yield POA x PR theoretical reconciliation."""
    recon = reconcile_solar_yield()
    # Theoretical: 1,945.98 * 0.77 = 1,498.40 kWh/kWp
    assert pytest.approx(recon["theoretical_poa_pr_kwh_per_kwp"], abs=0.1) == 1498.40
    # Luzon benchmark target: 1,298.0 kWh/kWp
    assert recon["target_specific_yield_kwh_per_kwp"] == 1298.0
    # Delta vs target: +16.24%
    assert pytest.approx(recon["delta_vs_target_pct"], abs=0.1) == 16.24
    # Delta vs theoretical POA x PR: +0.69%
    assert pytest.approx(recon["delta_vs_poa_pr_pct"], abs=0.1) == 0.69


# ==============================================================================
# 5. One-at-a-Time (OAT) Sensitivity Sweep
# ==============================================================================


def test_oat_sensitivity_sweep_execution():
    """Verify that OAT sensitivity analysis runs cleanly across all 5 parameters."""
    res = run_oat_sensitivity_analysis(weather_year=2019, outage_regime="normal", seed=0)

    assert len(res.points) == 15  # 3 * 5 parameters = 15 points
    assert res.base_grid_import_kwh > 0.0

    # Verify that higher cooling slope increases grid import
    cs_points = [p for p in res.points if p.parameter == "Cooling Slope (%/°C)"]
    assert len(cs_points) == 3
    # Sorted by slope: 3% -> 4% -> 5%
    cs_sorted = sorted(cs_points, key=lambda p: float(p.value))
    assert cs_sorted[0].grid_import_kwh < cs_sorted[1].grid_import_kwh < cs_sorted[2].grid_import_kwh

    # Verify that higher BOS factor decreases grid import (higher solar output)
    bos_points = [p for p in res.points if p.parameter == "PR-Driving BOS Factor"]
    assert len(bos_points) == 3
    # -5% BOS should have higher grid import than +5% BOS
    bos_minus = next(p for p in bos_points if "-5%" in p.label)
    bos_plus = next(p for p in bos_points if "+5%" in p.label)
    assert bos_minus.grid_import_kwh > bos_plus.grid_import_kwh
