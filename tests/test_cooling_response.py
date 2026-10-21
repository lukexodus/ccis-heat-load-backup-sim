"""Unit tests for temperature and humidity sensitive AC cooling demand model.

Covers DEM-002.1, DEM-002.2, and DEM-002.3 requirements per docs/prompts/DEM-002-PROMPT.md.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ccis_sim.core.interfaces import TieredDemand
from ccis_sim.core.models import Building
from ccis_sim.demand.cooling import compute_cooling_demand
from ccis_sim.demand.equipment import EquipmentAudit
from ccis_sim.weather.loader import load_weather_fixture


@pytest.fixture
def ccis_audit() -> EquipmentAudit:
    return EquipmentAudit.load_from_csv("data/fixtures/equipment-audit-ccis.csv")


@pytest.fixture
def default_building() -> Building:
    return Building()


def test_cooling_contract_signature_conformance(
    ccis_audit: EquipmentAudit,
    default_building: Building,
) -> None:
    """Verify compute_cooling_demand strictly matches the phase2 interface contract."""
    df = pd.DataFrame(
        {
            "hour": [1, 2, 3],
            "t_amb": [22.0, 28.0, 32.0],
            "rh": [70.0, 80.0, 85.0],
        }
    )
    occ = np.array([0.0, 0.5, 1.0])

    demand = compute_cooling_demand(df, occ, ccis_audit, default_building)
    assert isinstance(demand, TieredDemand)
    assert len(demand) == 3
    assert len(demand.tier1_kwh) == 3
    assert len(demand.tier2_kwh) == 3
    assert len(demand.tier3_kwh) == 3


def test_cooling_zero_at_or_below_base_temperature(
    ccis_audit: EquipmentAudit,
    default_building: Building,
) -> None:
    """Verify zero sensible cooling when ambient temperature is at or below T_base = 24.0°C."""
    # Test temperatures below and exactly at 24.0°C under high humidity and full occupancy
    temps = np.array([16.0, 18.5, 20.0, 22.0, 23.99, 24.0])
    n = len(temps)
    df = pd.DataFrame(
        {
            "hour": list(range(1, n + 1)),
            "t_amb": temps,
            "rh": np.full(n, 90.0),  # extreme humidity
        }
    )
    occ = np.ones(n)  # 100% full occupancy

    demand = compute_cooling_demand(df, occ, ccis_audit, default_building)

    # All tiers must be strictly zero
    np.testing.assert_allclose(demand.tier1_kwh, 0.0)
    np.testing.assert_allclose(demand.tier2_kwh, 0.0)
    np.testing.assert_allclose(demand.tier3_kwh, 0.0)
    np.testing.assert_allclose(demand.gross_kwh, 0.0)


def test_cooling_slope_four_percent_per_celsius_above_base(
    ccis_audit: EquipmentAudit,
    default_building: Building,
) -> None:
    """Verify sensible cooling demand increases at exactly 4.0%/°C above T_base at nominal humidity."""
    # Low humidity (rh <= 60%) so latent multiplier is exactly 1.00
    temps = np.array([24.0, 25.0, 26.0, 28.0, 29.0])
    n = len(temps)
    df = pd.DataFrame(
        {
            "hour": list(range(1, n + 1)),
            "t_amb": temps,
            "rh": np.full(n, 50.0),  # rh <= 60% -> M_latent = 1.0
        }
    )
    occ = np.ones(n)  # full occupancy

    demand = compute_cooling_demand(df, occ, ccis_audit, default_building)

    # Total connected comfort cooling is 74.80 kW (Tier 3)
    p_conn_t3 = 74.80
    expected_t3 = p_conn_t3 * default_building.cooling_sensitivity_per_c * (temps - 24.0)

    np.testing.assert_allclose(demand.tier3_kwh, expected_t3, rtol=1e-6)

    # Check slope directly: delta P / delta T
    dp = demand.tier3_kwh[1] - demand.tier3_kwh[0]  # from 24 to 25 °C (1 °C delta)
    slope_pct = (dp / p_conn_t3) * 100.0
    assert slope_pct == pytest.approx(4.0, rel=1e-5)


def test_cooling_latent_multiplier_low_vs_high_rh(
    ccis_audit: EquipmentAudit,
    default_building: Building,
) -> None:
    """Verify +20% latent penalty at high tropical humidity (RH >= 80%) compared to low RH (RH <= 60%)."""
    t_fixed = 30.0  # 6 °C above base
    df = pd.DataFrame(
        {
            "hour": [1, 2, 3],
            "t_amb": [t_fixed, t_fixed, t_fixed],
            "rh": [50.0, 70.0, 90.0],  # low (<=60%), mid (70%), high (>=80%)
        }
    )
    occ = np.array([1.0, 1.0, 1.0])

    demand = compute_cooling_demand(df, occ, ccis_audit, default_building)

    # Demand at low humidity (RH=50%)
    p_low = demand.tier3_kwh[0]
    # Demand at high humidity (RH=90%) must be exactly 1.20 * p_low (+20% penalty)
    p_high = demand.tier3_kwh[2]
    assert p_high == pytest.approx(1.20 * p_low, rel=1e-5)

    # Demand at mid humidity (RH=70%) must be halfway (1.10 * p_low)
    p_mid = demand.tier3_kwh[1]
    assert p_mid == pytest.approx(1.10 * p_low, rel=1e-5)


def test_cooling_capacity_cap_never_exceeded(
    ccis_audit: EquipmentAudit,
    default_building: Building,
) -> None:
    """Verify cooling demand is capped at total connected cooling capacity under extreme conditions."""
    # Extreme heat and saturated humidity
    df = pd.DataFrame(
        {
            "hour": [1, 2],
            "t_amb": [50.0, 60.0],  # extreme heat (delta T = 26 and 36 °C)
            "rh": [95.0, 99.0],
        }
    )
    occ = np.array([1.0, 1.0])

    demand = compute_cooling_demand(df, occ, ccis_audit, default_building)

    # Connected cooling capacities: Tier 2 = 2.40 kW, Tier 3 = 74.80 kW, Total = 77.20 kW
    np.testing.assert_allclose(demand.tier2_kwh, 2.40, rtol=1e-6)
    np.testing.assert_allclose(demand.tier3_kwh, 74.80, rtol=1e-6)
    np.testing.assert_allclose(demand.gross_kwh, 77.20, rtol=1e-6)


def test_cooling_unoccupied_hours_produce_only_tier2_spot_cooling(
    ccis_audit: EquipmentAudit,
    default_building: Building,
) -> None:
    """Verify unoccupied hours (occupancy=0) shut off comfort cooling (Tier 3) and run only Tier 2 spot cooling."""
    df = pd.DataFrame(
        {
            "hour": [1],
            "t_amb": [32.0],  # 8 °C above base
            "rh": [80.0],
        }
    )
    occ = np.array([0.0])  # Building unoccupied

    demand = compute_cooling_demand(df, occ, ccis_audit, default_building)

    # Life safety: 0 kW
    assert demand.tier1_kwh[0] == 0.0
    # Comfort cooling (Tier 3) must be shut off when unoccupied
    assert demand.tier3_kwh[0] == 0.0
    # Spot cooling (Tier 2) runs 24/7 in telecommunications closets
    assert demand.tier2_kwh[0] > 0.0
    assert demand.tier2_kwh[0] == pytest.approx(
        2.40 * 0.04 * (32.0 - 24.0) * 1.20, rel=1e-5
    )
    # Gross demand equals Tier 2 spot cooling
    assert demand.gross_kwh[0] == pytest.approx(demand.tier2_kwh[0], rel=1e-6)


def test_cooling_tier_sums_equal_gross(
    ccis_audit: EquipmentAudit,
    default_building: Building,
) -> None:
    """Verify energy conservation invariant: tier1 + tier2 + tier3 == gross for all 8,760 hours."""
    w19 = load_weather_fixture(2019)
    # Synthetic occupancy profile: 0.8 during day (8 to 18), 0.0 at night
    hours = np.arange(len(w19)) % 24
    occ = np.where((hours >= 8) & (hours < 18), 0.8, 0.0)

    demand = compute_cooling_demand(w19, occ, ccis_audit, default_building)

    summed_tiers = demand.tier1_kwh + demand.tier2_kwh + demand.tier3_kwh
    np.testing.assert_allclose(demand.gross_kwh, summed_tiers, rtol=1e-12, atol=1e-12)


def test_cooling_monotonic_in_temperature(
    ccis_audit: EquipmentAudit,
    default_building: Building,
) -> None:
    """Verify cooling demand is monotonic non-decreasing with increasing ambient temperature."""
    temps = np.linspace(15.0, 45.0, 31)
    n = len(temps)
    df = pd.DataFrame(
        {
            "hour": list(range(1, n + 1)),
            "t_amb": temps,
            "rh": np.full(n, 75.0),
        }
    )
    occ = np.full(n, 0.75)

    demand = compute_cooling_demand(df, occ, ccis_audit, default_building)

    diffs = np.diff(demand.gross_kwh)
    assert np.all(diffs >= -1e-9), "Cooling demand must be monotonic non-decreasing with temperature."


def test_cooling_determinism(
    ccis_audit: EquipmentAudit,
    default_building: Building,
) -> None:
    """Verify compute_cooling_demand is a pure deterministic calculation."""
    df = pd.DataFrame(
        {
            "hour": [1, 2],
            "t_amb": [28.0, 34.0],
            "rh": [65.0, 85.0],
        }
    )
    occ = np.array([0.5, 0.9])

    d1 = compute_cooling_demand(df, occ, ccis_audit, default_building)
    d2 = compute_cooling_demand(df, occ, ccis_audit, default_building)

    np.testing.assert_array_equal(d1.tier1_kwh, d2.tier1_kwh)
    np.testing.assert_array_equal(d1.tier2_kwh, d2.tier2_kwh)
    np.testing.assert_array_equal(d1.tier3_kwh, d2.tier3_kwh)


def test_cooling_input_validation(
    ccis_audit: EquipmentAudit,
    default_building: Building,
) -> None:
    """Verify error handling on malformed or mismatched inputs."""
    df = pd.DataFrame({"t_amb": [25.0, 26.0], "rh": [70.0, 70.0]})
    # Mismatched occupancy length
    with pytest.raises(ValueError, match="occupancy_fraction length"):
        compute_cooling_demand(df, np.array([0.5]), ccis_audit, default_building)

    # Missing column
    df_missing = pd.DataFrame({"t_amb": [25.0]})
    with pytest.raises(ValueError, match="must contain 't_amb' and 'rh'"):
        compute_cooling_demand(df_missing, np.array([0.5]), ccis_audit, default_building)


def test_cooling_implied_annual_cooling_metrics_report(
    ccis_audit: EquipmentAudit,
    default_building: Building,
) -> None:
    """Report (without asserting) the implied annual cooling kWh for 2019 and 2016 fixtures.

    Uses a synthetic occupancy profile: 0.80 on weekdays 08:00-18:00, 0.0 otherwise.
    These metrics are recorded for downstream calibration in DEM-002.4 / INT-001.
    """
    for year in (2019, 2016):
        weather = load_weather_fixture(year)
        ts = pd.to_datetime(weather["timestamp"])
        hours = ts.dt.hour.values
        dows = ts.dt.dayofweek.values

        # Stated synthetic occupancy: 0.80 on weekdays during 08:00-18:00
        occ = np.where((dows < 5) & (hours >= 8) & (hours < 18), 0.80, 0.0)

        demand = compute_cooling_demand(weather, occ, ccis_audit, default_building)

        annual_kwh_t2 = float(np.sum(demand.tier2_kwh))
        annual_kwh_t3 = float(np.sum(demand.tier3_kwh))
        annual_kwh_gross = float(np.sum(demand.gross_kwh))
        peak_kw = float(np.max(demand.gross_kwh))

        print(
            f"\n[DEM-002 METRICS] Year {year}: "
            f"Annual Cooling = {annual_kwh_gross:,.2f} kWh "
            f"(Tier 2 Spot = {annual_kwh_t2:,.2f} kWh, Tier 3 Comfort = {annual_kwh_t3:,.2f} kWh), "
            f"Peak Cooling Demand = {peak_kw:.2f} kW"
        )
        assert annual_kwh_gross > 0.0
