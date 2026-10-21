"""Unit and regression tests for INT-002 Scenario Grid and Monte Carlo runner."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ccis_sim.integration.engine import SimulationConfig, simulate
from ccis_sim.integration.scenarios import (
    check_convergence,
    compute_bill_calibrated_scale,
    compute_mc_summary,
    run_grid,
)


def test_demand_scale_validation() -> None:
    """Verify that demand_scale must be strictly positive."""
    with pytest.raises(ValueError, match="demand_scale must be > 0.0"):
        SimulationConfig(demand_scale=0.0)

    with pytest.raises(ValueError, match="demand_scale must be > 0.0"):
        SimulationConfig(demand_scale=-1.5)


def test_demand_scale_unity_equals_int001() -> None:
    """Verify demand_scale=1.0 reproduces the default unscaled simulation bit-for-bit."""
    cfg_default = SimulationConfig(
        solar_kwp=100.0,
        battery_kwh=100.0,
        weather_year=2019,
        outage_regime="normal",
        seed=101,
    )
    cfg_unity = SimulationConfig(
        solar_kwp=100.0,
        battery_kwh=100.0,
        weather_year=2019,
        outage_regime="normal",
        seed=101,
        demand_scale=1.0,
    )

    res_default = simulate(cfg_default, verify=False)
    res_unity = simulate(cfg_unity, verify=False)

    assert res_default.metrics["annual_gross_demand_kwh"] == res_unity.metrics["annual_gross_demand_kwh"]
    assert res_default.metrics["annual_grid_import_kwh"] == res_unity.metrics["annual_grid_import_kwh"]
    assert res_default.metrics["annual_solar_generation_kwh"] == res_unity.metrics["annual_solar_generation_kwh"]
    assert res_default.metrics["annual_unserved_load_kwh"] == res_unity.metrics["annual_unserved_load_kwh"]


def test_demand_scale_doubles_gross_demand() -> None:
    """Verify demand_scale=2.0 strictly doubles annual gross demand."""
    cfg_1 = SimulationConfig(
        solar_kwp=0.0,
        battery_kwh=0.0,
        weather_year=2019,
        outage_regime="normal",
        seed=42,
        demand_scale=1.0,
    )
    cfg_2 = SimulationConfig(
        solar_kwp=0.0,
        battery_kwh=0.0,
        weather_year=2019,
        outage_regime="normal",
        seed=42,
        demand_scale=2.0,
    )

    res_1 = simulate(cfg_1, verify=False)
    res_2 = simulate(cfg_2, verify=False)

    demand_1 = res_1.metrics["annual_gross_demand_kwh"]
    demand_2 = res_2.metrics["annual_gross_demand_kwh"]

    assert np.isclose(demand_2, 2.0 * demand_1, rtol=1e-12)


def test_bill_calibrated_scale_value() -> None:
    """Verify compute_bill_calibrated_scale returns expected value (~2.105)."""
    scale = compute_bill_calibrated_scale()
    assert 2.10 <= scale <= 2.11
    # Check exact expected ratio: 398536.77 / 189355.61 ≈ 2.1047
    assert np.isclose(scale, 2.10470014, rtol=1e-5)


def test_run_grid_tiny_determinism(tmp_path) -> None:
    """Verify run_grid executes deterministically and creates output CSVs."""
    test_configs = [
        SimulationConfig(
            solar_kwp=50.0,
            battery_kwh=50.0,
            weather_year=2019,
            outage_regime="normal",
            seed=1,
            demand_scale=1.0,
        ),
        SimulationConfig(
            solar_kwp=50.0,
            battery_kwh=50.0,
            weather_year=2019,
            outage_regime="normal",
            seed=2,
            demand_scale=1.0,
        ),
    ]

    out_dir_1 = tmp_path / "run1"
    out_dir_2 = tmp_path / "run2"

    df_grid1, df_mc1 = run_grid(test_configs, output_dir=out_dir_1, num_workers=2)
    df_grid2, df_mc2 = run_grid(test_configs, output_dir=out_dir_2, num_workers=2)

    # Check files exist
    assert (out_dir_1 / "scenario_grid.csv").exists()
    assert (out_dir_1 / "mc_summary.csv").exists()

    # Check bitwise equality of results
    pd.testing.assert_frame_equal(df_grid1, df_grid2)
    pd.testing.assert_frame_equal(df_mc1, df_mc2)
    assert len(df_grid1) == 2
    assert len(df_mc1) == 1  # 1 unique cell (solar 50, battery 50, 2019, normal, scale 1.0, temp 0.0)


def test_mc_summary_and_convergence_logic() -> None:
    """Verify compute_mc_summary and check_convergence logic on synthetic test data."""
    test_data = [
        {
            "solar_kwp": 100.0,
            "battery_kwh": 100.0,
            "weather_year": 2019,
            "outage_regime": "typhoon",
            "demand_scale": 1.0,
            "temp_offset_c": 0.0,
            "seed": s,
            "grid_import_kwh": 10000.0,
            "solar_gen_kwh": 150000.0,
            "curtailed_kwh": 2000.0,
            "unserved_t1_kwh": 0.0,
            "unserved_t2_kwh": float(s % 5),
            "unserved_t3_kwh": 50.0,
            "total_outage_hours": 20,
            "outage_hours_t1_served": 20,
            "outage_hours_t2_served": 18,
            "battery_cycles": 120.0,
            "self_sufficiency": 0.85,
            "peak_grid_kw": 45.0,
        }
        for s in range(30)
    ]
    df = pd.DataFrame(test_data)
    summary = compute_mc_summary(df)
    assert len(summary) == 1
    assert summary["sample_size"].iloc[0] == 30
    assert summary["unserved_t12_kwh_mean"].iloc[0] == 2.0

    conv = check_convergence(df)
    assert 10 in conv
    assert 20 in conv
    assert 30 in conv
    assert conv[30]["n"] == 30
    assert conv[30]["mean"] == 2.0
    assert conv[30]["half_width"] > 0.0
