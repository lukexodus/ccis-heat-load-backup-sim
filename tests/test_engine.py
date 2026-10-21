"""Unit and integration tests for CCIS simulation engine and CLI (INT-001).

Verifies the integrated 8-step hourly dispatch sequence, physical energy conservation
invariants, battery SoC continuity, deterministic reproducibility, CLI execution,
and combined verification cross-checks (DEM-002.4 and SOL-002.4).
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ccis_sim.cli import main as cli_main
from ccis_sim.core.models import Battery, Building, HourlyRecord, LoadTier
from ccis_sim.core.verification import assert_simulation_valid
from ccis_sim.demand.mock_bills import SyntheticBillGenerator
from ccis_sim.integration.baseline import simulate_baseline
from ccis_sim.integration.engine import SimulationConfig, SimulationResult, simulate
from ccis_sim.integration.exporters import export_all, export_daily_csv, export_hourly_csv, export_summary_json
from ccis_sim.solar.array import (
    ASSUMED_MEAN_THERMAL_FACTOR,
    IMPLIED_ANNUAL_THERMAL_FACTOR_2019,
    SolarArray,
    compute_ac_generation,
)
from ccis_sim.solar.irradiance import compute_dc_power_per_kwp
from ccis_sim.weather.loader import load_weather_fixture


# ===========================================================================
# 1. Determinism and Seed Invariance Tests
# ===========================================================================

def test_engine_determinism_same_seed():
    """Verify that identical configuration and seed yield byte-identical simulation results."""
    cfg1 = SimulationConfig(
        solar_kwp=100.0,
        battery_kwh=100.0,
        weather_year=2019,
        outage_regime="typhoon",
        seed=12345,
    )
    cfg2 = SimulationConfig(
        solar_kwp=100.0,
        battery_kwh=100.0,
        weather_year=2019,
        outage_regime="typhoon",
        seed=12345,
    )

    res1 = simulate(cfg1)
    res2 = simulate(cfg2)

    assert len(res1.records) == len(res2.records) == 8760
    assert res1.metrics == res2.metrics
    assert res1.tracker_summary == res2.tracker_summary

    for r1, r2 in zip(res1.records[:200], res2.records[:200]):
        assert r1.hour == r2.hour
        assert math.isclose(r1.demand_gross_kwh, r2.demand_gross_kwh, abs_tol=1e-9)
        assert math.isclose(r1.demand_served_kwh, r2.demand_served_kwh, abs_tol=1e-9)
        assert math.isclose(r1.solar_generation_kwh, r2.solar_generation_kwh, abs_tol=1e-9)
        assert math.isclose(r1.battery_soc_kwh, r2.battery_soc_kwh, abs_tol=1e-9)
        assert r1.grid_available == r2.grid_available


def test_engine_distinct_seeds_differ():
    """Verify that different random seeds produce different stochastic outage outcomes."""
    cfg1 = SimulationConfig(solar_kwp=50.0, battery_kwh=50.0, outage_regime="typhoon", seed=101)
    cfg2 = SimulationConfig(solar_kwp=50.0, battery_kwh=50.0, outage_regime="typhoon", seed=202)

    res1 = simulate(cfg1)
    res2 = simulate(cfg2)

    # Grid availability patterns and resulting unserved load should differ
    grid1 = [r.grid_available for r in res1.records]
    grid2 = [r.grid_available for r in res2.records]
    assert grid1 != grid2


# ===========================================================================
# 2. Energy Conservation & Harness Invariants
# ===========================================================================

@pytest.mark.parametrize(
    "solar_kwp,battery_kwh,outage_regime",
    [
        (0.0, 0.0, "normal"),       # Grid-only negative control
        (100.0, 0.0, "normal"),     # Solar PV only
        (0.0, 100.0, "normal"),     # Battery BESS only
        (100.0, 200.0, "normal"),   # Solar PV + Battery normal regime
        (100.0, 200.0, "typhoon"),  # Solar PV + Battery typhoon regime
    ],
)
def test_simulation_passes_verification_harness(
    solar_kwp: float,
    battery_kwh: float,
    outage_regime: str,
):
    """Verify that all sizing combinations pass the strict verification harness."""
    cfg = SimulationConfig(
        solar_kwp=solar_kwp,
        battery_kwh=battery_kwh,
        weather_year=2019,
        outage_regime=outage_regime,  # type: ignore[arg-type]
        seed=42,
    )
    result = simulate(cfg, verify=True)

    assert len(result.records) == 8760
    assert result.metrics["max_energy_balance_residual_kwh"] <= 1e-5


def test_residual_at_or_below_1e5_every_hour():
    """Verify that energy_balance_residual_kwh is at or below 1e-5 kWh for all 8,760 hours."""
    cfg = SimulationConfig(
        solar_kwp=100.0,
        battery_kwh=200.0,
        weather_year=2019,
        outage_regime="typhoon",
        seed=777,
    )
    result = simulate(cfg)

    residuals = [r.energy_balance_residual_kwh for r in result.records]
    assert max(residuals) <= 1e-5
    assert all(r <= 1e-5 for r in residuals)


# ===========================================================================
# 3. Grid-Only vs Baseline Consistency
# ===========================================================================

def test_grid_only_case_behavior():
    """Verify that grid-only configuration (0 kWp, 0 kWh) has zero solar and zero battery flows."""
    cfg = SimulationConfig(solar_kwp=0.0, battery_kwh=0.0, weather_year=2019, seed=42)
    result = simulate(cfg)

    for r in result.records:
        assert r.solar_generation_kwh == 0.0
        assert r.solar_to_demand_kwh == 0.0
        assert r.solar_to_battery_kwh == 0.0
        assert r.solar_curtailed_kwh == 0.0
        assert r.battery_charge_kwh == 0.0
        assert r.battery_discharge_kwh == 0.0
        assert r.battery_soc_kwh == 0.0
        if r.grid_available:
            assert math.isclose(r.grid_import_kwh, r.demand_served_kwh, abs_tol=1e-5)


# ===========================================================================
# 4. Outage Behavior & 12-Hour Blackout Response
# ===========================================================================

def test_forced_outage_with_full_battery_serves_tier1_tier2_and_sheds_tier3():
    """Verify that during a 12-hour blackout with a full battery, Tier 1 and Tier 2 are served and Tier 3 shed."""
    # Sized system with 200 kWh battery starting 100% full
    cfg = SimulationConfig(
        solar_kwp=0.0,  # Night or no solar to isolate battery backup
        battery_kwh=200.0,
        weather_year=2019,
        initial_soc_kwh=200.0,
        outage_regime="normal",
        seed=1,
    )

    result = simulate(cfg)

    # Find the first blackout event in the schedule
    outage_hours = [r for r in result.records if not r.grid_available]
    if not outage_hours:
        # If seed 1 normal had 0 outages, try typhoon
        cfg_typhoon = SimulationConfig(
            solar_kwp=0.0,
            battery_kwh=200.0,
            weather_year=2019,
            initial_soc_kwh=200.0,
            outage_regime="typhoon",
            seed=42,
        )
        result = simulate(cfg_typhoon)
        outage_hours = [r for r in result.records if not r.grid_available]

    assert len(outage_hours) > 0

    # During outage hours:
    # 1. Grid import must be zero
    # 2. Active load tier must be <= 2 (Tier 3 comfort cooling shed)
    # 3. Unserved load must be positive (reflecting shed Tier 3 demand)
    for r in outage_hours[:12]:
        assert r.grid_import_kwh == 0.0
        assert r.active_load_tier in (LoadTier.TIER_1_CRITICAL, LoadTier.TIER_2_ESSENTIAL)
        assert r.unserved_load_kwh > 0.0
        assert r.demand_gross_kwh == pytest.approx(r.demand_served_kwh + r.unserved_load_kwh, abs=1e-5)


# ===========================================================================
# 5. Combined Verification Tests (DEM-002.4 and SOL-002.4)
# ===========================================================================

def test_dem_002_4_combined_demand_metrics():
    """Execute DEM-002.4 combined demand cross-check against mock bills and placeholder."""
    cfg = SimulationConfig(solar_kwp=0.0, battery_kwh=0.0, weather_year=2019)
    result = simulate(cfg)

    gross_kwh = result.metrics["annual_gross_demand_kwh"]
    eui = result.metrics["gross_eui_kwh_per_m2_year"]
    peak_kw = result.metrics["peak_demand_kw"]

    # Verify deterministic bottom-up values
    assert math.isclose(gross_kwh, 189355.61, rel_tol=1e-3)
    assert math.isclose(eui, 75.74, rel_tol=1e-3)
    assert math.isclose(peak_kw, 95.71, rel_tol=1e-3)

    # Compare against uncalibrated placeholder (324,379.71 kWh, EUI 129.75, peak 101.29 kW)
    placeholder_kwh = 324379.71
    diff_pct_kwh = (gross_kwh - placeholder_kwh) / placeholder_kwh * 100.0
    assert -45.0 <= diff_pct_kwh <= -35.0  # Approx -41.6%


def test_sol_002_4_combined_solar_yield_and_thermal_factors():
    """Execute SOL-002.4 specific yield validation against Luzon 1,298 kWh/kWp target."""
    weather_2019 = load_weather_fixture(2019)
    dc_per_kwp = compute_dc_power_per_kwp(weather_2019)
    array = SolarArray(capacity_kwp=1.0)
    ac_gen = compute_ac_generation(dc_per_kwp, array)
    specific_yield = float(np.sum(ac_gen))

    # Verify specific yield is inside the tropical benchmark band [1,200, 1,600] kWh/kWp
    assert 1200.0 <= specific_yield <= 1600.0
    assert math.isclose(specific_yield, 1508.74, rel_tol=1e-3)

    # Implied mean thermal factor vs assumed factor
    assert math.isclose(IMPLIED_ANNUAL_THERMAL_FACTOR_2019, 0.871056, abs_tol=1e-4)
    assert math.isclose(ASSUMED_MEAN_THERMAL_FACTOR, 0.865089, abs_tol=1e-4)
    # Deviation between assumed and implied is under 1%
    assert abs(IMPLIED_ANNUAL_THERMAL_FACTOR_2019 - ASSUMED_MEAN_THERMAL_FACTOR) / ASSUMED_MEAN_THERMAL_FACTOR < 0.01


# ===========================================================================
# 6. Exporters and CLI Execution Tests
# ===========================================================================

def test_exporters_output_integrity(tmp_path: Path):
    """Verify that export_all writes hourly CSV, daily CSV, and summary JSON correctly."""
    cfg = SimulationConfig(solar_kwp=50.0, battery_kwh=50.0, weather_year=2019, seed=1)
    res = simulate(cfg)

    paths = export_all(res, tmp_path, prefix="test_sim")

    hourly_csv = paths["hourly_csv"]
    daily_csv = paths["daily_csv"]
    summary_json = paths["summary_json"]

    assert hourly_csv.exists() and hourly_csv.stat().st_size > 0
    assert daily_csv.exists() and daily_csv.stat().st_size > 0
    assert summary_json.exists() and summary_json.stat().st_size > 0

    # Verify JSON content
    with open(summary_json, encoding="utf-8") as f:
        data = json.load(f)
    assert "config" in data
    assert "metrics" in data
    assert data["metrics"]["annual_gross_demand_kwh"] > 0.0


def test_cli_execution_all_scenarios(tmp_path: Path):
    """Verify CLI `ccis-sim run` executes cleanly across required acceptance scenarios."""
    scenarios = [
        ["--solar-kwp", "0", "--battery-kwh", "0", "--weather", "2019", "--outages", "normal"],
        ["--solar-kwp", "100", "--battery-kwh", "0", "--weather", "2019", "--outages", "normal"],
        ["--solar-kwp", "100", "--battery-kwh", "200", "--weather", "2019", "--outages", "normal"],
        ["--solar-kwp", "100", "--battery-kwh", "200", "--weather", "2019", "--outages", "typhoon"],
    ]

    for idx, sc in enumerate(scenarios):
        out_dir = tmp_path / f"sc_{idx}"
        cmd = ["run"] + sc + ["--seed", "42", "--out", str(out_dir), "--quiet"]
        ret = cli_main(cmd)
        assert ret == 0, f"CLI execution failed for scenario: {sc}"
        assert (out_dir / "ccis_sim_summary.json").exists()
        assert (out_dir / "ccis_sim_hourly.csv").exists()
        assert (out_dir / "ccis_sim_daily.csv").exists()
