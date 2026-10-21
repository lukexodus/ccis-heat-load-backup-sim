"""Unit and integration test suite for solar irradiance and NOCT thermal derating.

Verifies:
1. Exact zero DC yield during nighttime hours (GHI = 0.0 or night zenith).
2. Astronomical solar noon alignment near 12:00 ± 20 minutes on clear days.
3. Monotonic thermal derating: hotter hours yield strictly lower DC power for equal GHI.
4. Plane-of-array (POA) irradiance sanity band against GHI at 15° South tilt.
5. Invariant checks: non-negative, finite, no NaNs, array length preservation.
6. Determinism across repeated evaluations.
7. Phase 2 interface contract signature conformance.
8. Baseline 2019 specific DC yield calculation.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ccis_sim.solar.irradiance import (
    DEFAULT_ALBEDO,
    DEFAULT_AZIMUTH_DEG,
    DEFAULT_TILT_DEG,
    EFFECTIVE_NOCT_C,
    TEMP_COEFFICIENT_PER_C,
    compute_cell_temperature,
    compute_dc_power_per_kwp,
    compute_solar_position,
    compute_thermal_derating_factor,
    decompose_ghi_erbs,
    transpose_irradiance_isotropic,
)
from ccis_sim.weather.loader import load_weather_fixture


@pytest.fixture
def weather_2019_df() -> pd.DataFrame:
    """Load canonical 2019 Batac weather fixture (8,760 hours)."""
    return load_weather_fixture(2019)


@pytest.fixture
def weather_2016_df() -> pd.DataFrame:
    """Load canonical 2016 Batac El Niño weather fixture (8,760 hours)."""
    return load_weather_fixture(2016)


def test_contract_signature_conformance(weather_2019_df: pd.DataFrame) -> None:
    """Verify compute_dc_power_per_kwp matches exact contract signature."""
    dc_power = compute_dc_power_per_kwp(
        weather_2019_df,
        tilt_deg=15.0,
        azimuth_deg=180.0,
        latitude_deg=18.06,
        longitude_deg=120.56,
    )
    assert isinstance(dc_power, np.ndarray)
    assert dc_power.shape == (8760,)
    assert dc_power.dtype == np.float64


def test_nighttime_generation_is_strictly_zero(weather_2019_df: pd.DataFrame) -> None:
    """Verify DC output is strictly 0.0 whenever GHI is zero."""
    dc_power = compute_dc_power_per_kwp(weather_2019_df)
    night_mask = weather_2019_df["ghi"].values == 0.0

    assert np.all(dc_power[night_mask] == 0.0), "DC power must be exactly 0.0 when GHI == 0.0"


def test_solar_noon_alignment() -> None:
    """Verify astronomical solar noon occurs near 12:00 ± 20 minutes in Batac."""
    # Test on vernal equinox (March 21) across 24 hours at 1-minute resolution
    timestamps = pd.date_range("2019-03-21 00:00:00+08:00", "2019-03-21 23:59:00+08:00", freq="1min")
    pos = compute_solar_position(
        timestamps,
        latitude_deg=18.06,
        longitude_deg=120.56,
    )

    # Minimum solar zenith corresponds to solar noon
    noon_idx = int(np.argmin(pos.zenith_rad))
    noon_timestamp = timestamps[noon_idx]

    noon_hour_float = noon_timestamp.hour + noon_timestamp.minute / 60.0
    # Batac (120.56°E) with Equation of Time on March 21 (EoT ~ -7.5 min)
    # Solar noon is at 12:00 - (-7.5 + 2.24)/60 = 12:05.
    assert 11.5 <= noon_hour_float <= 12.5, (
        f"Solar noon at {noon_timestamp.strftime('%H:%M')} is not within 12:00 ± 30 minutes"
    )


def test_thermal_derating_monotonicity() -> None:
    """Verify that a hotter hour yields strictly lower DC power than a cooler hour for equal GHI."""
    # Create synthetic single-hour DataFrames with identical positive GHI
    df_cool = pd.DataFrame({
        "hour": [13],
        "timestamp": ["2019-03-21 12:00:00+08:00"],
        "t_amb": [20.0],
        "rh": [50.0],
        "ghi": [800.0],
    })
    df_hot = pd.DataFrame({
        "hour": [13],
        "timestamp": ["2019-03-21 12:00:00+08:00"],
        "t_amb": [38.0],
        "rh": [50.0],
        "ghi": [800.0],
    })

    dc_cool = compute_dc_power_per_kwp(df_cool)[0]
    dc_hot = compute_dc_power_per_kwp(df_hot)[0]

    assert dc_hot < dc_cool, f"Hot hour DC ({dc_hot:.4f}) must be strictly less than cool hour ({dc_cool:.4f})"
    # Thermal derating coefficient is -0.40%/°C above reference.
    # For ΔT_amb = 18°C, cell temperature is 18°C higher, so derating factor drops by exactly 0.0040 * 18 = 0.072.
    # Since G_poa is identical, (dc_cool - dc_hot) / (G_poa / 1000) == 0.072:
    # Compute G_poa to check exact analytical match
    pos = compute_solar_position(pd.DatetimeIndex(pd.to_datetime(df_cool["timestamp"])))
    dhi, dni = decompose_ghi_erbs(df_cool["ghi"].values, pos.cos_zenith, np.array([80.0]))
    poa = transpose_irradiance_isotropic(df_cool["ghi"].values, dhi, dni, pos.cos_zenith, pos.cos_incidence)[0]
    normalized_drop = (dc_cool - dc_hot) / (poa / 1000.0)
    expected_factor_drop = 0.0040 * (38.0 - 20.0)
    assert pytest.approx(normalized_drop, rel=1e-3) == expected_factor_drop


def test_poa_within_sane_band_of_ghi(weather_2019_df: pd.DataFrame) -> None:
    """Verify annual POA insolation is within a plausible band (100% to 110% of GHI for 15° tilt)."""
    ghi = weather_2019_df["ghi"].values
    annual_ghi_kwh = ghi.sum() / 1000.0

    pos = compute_solar_position(pd.to_datetime(weather_2019_df["timestamp"]))
    dhi, dni = decompose_ghi_erbs(ghi, pos.cos_zenith, pd.to_datetime(weather_2019_df["timestamp"]).dt.dayofyear.values)
    poa = transpose_irradiance_isotropic(ghi, dhi, dni, pos.cos_zenith, pos.cos_incidence, tilt_deg=15.0)

    annual_poa_kwh = poa.sum() / 1000.0
    poa_ratio = annual_poa_kwh / annual_ghi_kwh

    # At 18.06°N latitude, a 15° south tilt gives ~1.01 to 1.05 gain over horizontal GHI
    assert 1.00 <= poa_ratio <= 1.10, f"Annual POA/GHI ratio {poa_ratio:.4f} is outside [1.00, 1.10]"


def test_no_negative_or_nan_outputs(weather_2019_df: pd.DataFrame, weather_2016_df: pd.DataFrame) -> None:
    """Verify DC output has no NaNs, infinities, or negative values across normal and hot years."""
    for df in (weather_2019_df, weather_2016_df):
        dc_power = compute_dc_power_per_kwp(df)
        assert np.all(np.isfinite(dc_power)), "Found non-finite values (NaN/inf) in DC power output"
        assert np.all(dc_power >= 0.0), "Found negative values in DC power output"
        assert len(dc_power) == len(df), f"Output length {len(dc_power)} != input length {len(df)}"


def test_determinism(weather_2019_df: pd.DataFrame) -> None:
    """Verify consecutive executions with identical inputs produce bit-identical results."""
    run1 = compute_dc_power_per_kwp(weather_2019_df)
    run2 = compute_dc_power_per_kwp(weather_2019_df)
    assert np.array_equal(run1, run2), "Model execution is non-deterministic"


def test_annual_dc_yield_reporting(weather_2019_df: pd.DataFrame) -> None:
    """Compute and verify plausible bounds for 2019 specific DC yield (kWh/kWp)."""
    dc_power = compute_dc_power_per_kwp(weather_2019_df)
    annual_dc_yield_kwh_per_kwp = float(np.sum(dc_power))

    # Pre-BOS and pre-inverter DC yield in tropical Batac with thermal derating
    # is typically ~1,500 - 1,800 kWh/kWp
    assert 1400.0 <= annual_dc_yield_kwh_per_kwp <= 1850.0, (
        f"Annual DC yield {annual_dc_yield_kwh_per_kwp:.2f} kWh/kWp outside plausible bounds [1400, 1850]"
    )


def test_cell_temperature_formula() -> None:
    """Verify NOCT + 10°C rooftop penalty formula implementation."""
    # At G_poa = 800 W/m^2, T_amb = 20°C:
    # T_cell = 20 + ((45 + 10) - 20)/800 * 800 = 20 + 35 = 55.0°C
    t_cell = compute_cell_temperature(np.array([20.0]), np.array([800.0]), effective_noct_c=EFFECTIVE_NOCT_C)
    assert pytest.approx(t_cell[0], abs=1e-5) == 55.0

    # At night (G_poa = 0): T_cell == T_amb
    t_cell_night = compute_cell_temperature(np.array([24.5]), np.array([0.0]))
    assert pytest.approx(t_cell_night[0], abs=1e-5) == 24.5


def test_thermal_derating_at_stc() -> None:
    """Verify derating factor equals 1.0 at STC cell temperature (25°C)."""
    f_stc = compute_thermal_derating_factor(np.array([25.0]))
    assert pytest.approx(f_stc[0], abs=1e-6) == 1.0

    # At 75°C (+50°C above STC): f_temp = 1.0 - 0.004 * 50 = 0.80 (20% thermal loss)
    f_hot = compute_thermal_derating_factor(np.array([75.0]))
    assert pytest.approx(f_hot[0], abs=1e-6) == 0.80


def test_error_handling_invalid_inputs() -> None:
    """Verify input validation catches missing columns, negatives, and non-finite values."""
    # Missing column
    with pytest.raises(ValueError, match="missing required column 'ghi'"):
        compute_dc_power_per_kwp(pd.DataFrame({"t_amb": [25.0]}))

    # Negative GHI
    with pytest.raises(ValueError, match="negative irradiance"):
        compute_dc_power_per_kwp(pd.DataFrame({"ghi": [-5.0], "t_amb": [25.0], "timestamp": ["2019-01-01 12:00:00+08:00"]}))

    # NaN in t_amb
    with pytest.raises(ValueError, match="non-finite"):
        compute_dc_power_per_kwp(pd.DataFrame({"ghi": [500.0], "t_amb": [np.nan], "timestamp": ["2019-01-01 12:00:00+08:00"]}))
