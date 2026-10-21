"""Unit tests for diurnal non-cooling electrical demand model.

Covers DEM-001.2, DEM-001.3, and DEM-001.4 requirements per docs/prompts/DEM-001-PROMPT.md.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ccis_sim.core.interfaces import OccupancySchedule, TieredDemand
from ccis_sim.core.models import Building
from ccis_sim.demand.equipment import EquipmentAudit, EquipmentItem
from ccis_sim.demand.non_cooling import compute_non_cooling_demand
from ccis_sim.demand.schedule import build_occupancy_schedule
from ccis_sim.weather.loader import load_weather_fixture


@pytest.fixture
def ccis_audit() -> EquipmentAudit:
    return EquipmentAudit.load_from_csv("data/fixtures/equipment-audit-ccis.csv")


@pytest.fixture
def default_building() -> Building:
    return Building()


@pytest.fixture
def annual_schedule_2019() -> OccupancySchedule:
    w19 = load_weather_fixture(2019)
    return build_occupancy_schedule(w19["timestamp"])


def test_non_cooling_contract_signature_conformance(
    annual_schedule_2019: OccupancySchedule,
    ccis_audit: EquipmentAudit,
    default_building: Building,
) -> None:
    """Verify compute_non_cooling_demand matches the exact contract signature and returns TieredDemand."""
    demand = compute_non_cooling_demand(annual_schedule_2019, ccis_audit, default_building)

    assert isinstance(demand, TieredDemand)
    assert len(demand) == 8760
    assert len(demand.tier1_kwh) == 8760
    assert len(demand.tier2_kwh) == 8760
    assert len(demand.tier3_kwh) == 8760


def test_non_cooling_tier_sums_equal_gross(
    annual_schedule_2019: OccupancySchedule,
    ccis_audit: EquipmentAudit,
    default_building: Building,
) -> None:
    """Verify energy conservation invariant: tier1 + tier2 + tier3 == gross for all hours."""
    demand = compute_non_cooling_demand(annual_schedule_2019, ccis_audit, default_building)

    summed_tiers = demand.tier1_kwh + demand.tier2_kwh + demand.tier3_kwh
    np.testing.assert_allclose(demand.gross_kwh, summed_tiers, rtol=1e-12, atol=1e-12)


def test_non_cooling_baseload_rule_exact_ten_percent(
    annual_schedule_2019: OccupancySchedule,
    ccis_audit: EquipmentAudit,
    default_building: Building,
) -> None:
    """Verify unoccupied non-cooling demand is exactly 10% of daytime peak non-cooling demand."""
    demand = compute_non_cooling_demand(annual_schedule_2019, ccis_audit, default_building)

    # Calculate daytime peak directly from audit items
    non_cooling = [it for it in ccis_audit.items if not it.is_cooling]
    peak_expected = sum(it.count * it.rated_kw * it.duty_cycle for it in non_cooling)
    unocc_expected = 0.10 * peak_expected

    # Peak expected for CCIS audit is exactly 60.659 kW
    assert peak_expected == pytest.approx(60.6590, rel=1e-4)
    assert unocc_expected == pytest.approx(6.0659, rel=1e-4)

    # Check that at full occupancy (f=1.0), gross equals peak
    full_occ_hours = annual_schedule_2019.occupancy_fraction == 1.0
    assert np.any(full_occ_hours)
    np.testing.assert_allclose(demand.gross_kwh[full_occ_hours], peak_expected, rtol=1e-5)

    # Check that at zero occupancy (f=0.0), gross equals exactly 10% baseload
    zero_occ_hours = annual_schedule_2019.occupancy_fraction == 0.0
    assert np.sum(zero_occ_hours) > 0
    np.testing.assert_allclose(demand.gross_kwh[zero_occ_hours], unocc_expected, rtol=1e-5)


def test_non_cooling_no_double_counting_of_continuous_loads(
    annual_schedule_2019: OccupancySchedule,
    ccis_audit: EquipmentAudit,
    default_building: Building,
) -> None:
    """Verify 24/7 continuous loads (3.441 kW) are NOT double counted with the 10% baseload.

    If double counting occurred, baseload would be 3.441 + 6.0659 = 9.5069 kW.
    Under D-27, baseload must strictly equal 6.0659 kW.
    """
    demand = compute_non_cooling_demand(annual_schedule_2019, ccis_audit, default_building)
    zero_occ_hours = annual_schedule_2019.occupancy_fraction == 0.0

    unoccupied_gross = demand.gross_kwh[zero_occ_hours]
    # Assert baseload is strictly around 6.066 kW, never ~9.5 kW
    assert np.all(unoccupied_gross < 7.0)
    assert np.all(unoccupied_gross == pytest.approx(6.0659, rel=1e-4))


def test_non_cooling_baseload_across_night_sunday_and_holiday(
    ccis_audit: EquipmentAudit,
    default_building: Building,
) -> None:
    """Verify 10% baseload rule holds identically on a weekday night, a Sunday, and a holiday."""
    # 1. Weekday night (2019-09-18 02:00)
    ts_night = pd.date_range("2019-09-18 02:00:00+08:00", periods=1, freq="h")
    sched_night = build_occupancy_schedule(ts_night)
    demand_night = compute_non_cooling_demand(sched_night, ccis_audit, default_building)
    assert demand_night.gross_kwh[0] == pytest.approx(6.0659, rel=1e-4)

    # 2. Entire Sunday (2019-09-22 00:00 to 23:00)
    ts_sun = pd.date_range("2019-09-22 00:00:00+08:00", periods=24, freq="h")
    sched_sun = build_occupancy_schedule(ts_sun)
    demand_sun = compute_non_cooling_demand(sched_sun, ccis_audit, default_building)
    np.testing.assert_allclose(demand_sun.gross_kwh, 6.0659, rtol=1e-4)

    # 3. Entire Holiday (Maundy Thursday 2019-04-18 00:00 to 23:00)
    ts_hol = pd.date_range("2019-04-18 00:00:00+08:00", periods=24, freq="h")
    sched_hol = build_occupancy_schedule(ts_hol)
    demand_hol = compute_non_cooling_demand(sched_hol, ccis_audit, default_building)
    np.testing.assert_allclose(demand_hol.gross_kwh, 6.0659, rtol=1e-4)


def test_non_cooling_tier1_constant_life_safety(
    annual_schedule_2019: OccupancySchedule,
    ccis_audit: EquipmentAudit,
    default_building: Building,
) -> None:
    """Verify Tier 1 load is constant 1.215 kW (exit signs, fire alarm, CCTV, stairwell)."""
    demand = compute_non_cooling_demand(annual_schedule_2019, ccis_audit, default_building)

    # Continuous 24/7 Tier 1 load
    np.testing.assert_allclose(demand.tier1_kwh, 1.2150, rtol=1e-5)


def test_non_cooling_tier2_and_tier3_ranges(
    annual_schedule_2019: OccupancySchedule,
    ccis_audit: EquipmentAudit,
    default_building: Building,
) -> None:
    """Verify Tier 2 (IT/faculty) and Tier 3 (labs/lighting/standby) ranges."""
    demand = compute_non_cooling_demand(annual_schedule_2019, ccis_audit, default_building)

    # Tier 2: 2.226 kW continuous IT up to 11.312 kW at full occupancy
    assert np.min(demand.tier2_kwh) == pytest.approx(2.2260, rel=1e-4)
    assert np.max(demand.tier2_kwh) == pytest.approx(11.3120, rel=1e-4)

    # Tier 3: 2.6249 kW standby baseload up to 48.1320 kW at full occupancy
    assert np.min(demand.tier3_kwh) == pytest.approx(2.6249, rel=1e-4)
    assert np.max(demand.tier3_kwh) == pytest.approx(48.1320, rel=1e-4)


def test_non_cooling_class_day_demand_exceeds_holiday(
    ccis_audit: EquipmentAudit,
    default_building: Building,
) -> None:
    """Verify daily energy on a class weekday strictly exceeds a holiday or Sunday."""
    ts_class = pd.date_range("2019-09-18 00:00:00+08:00", periods=24, freq="h")
    sched_class = build_occupancy_schedule(ts_class)
    demand_class = compute_non_cooling_demand(sched_class, ccis_audit, default_building)

    ts_hol = pd.date_range("2019-04-18 00:00:00+08:00", periods=24, freq="h")
    sched_hol = build_occupancy_schedule(ts_hol)
    demand_hol = compute_non_cooling_demand(sched_hol, ccis_audit, default_building)

    daily_kwh_class = np.sum(demand_class.gross_kwh)
    daily_kwh_hol = np.sum(demand_hol.gross_kwh)

    assert daily_kwh_class > daily_kwh_hol
    assert daily_kwh_class > 2.0 * daily_kwh_hol


def test_non_cooling_ignores_cooling_equipment(
    annual_schedule_2019: OccupancySchedule,
    ccis_audit: EquipmentAudit,
    default_building: Building,
) -> None:
    """Verify air conditioning units in audit inventory are strictly excluded from non-cooling demand."""
    demand_with_ac = compute_non_cooling_demand(annual_schedule_2019, ccis_audit, default_building)

    # Create stripped audit without AC items
    audit_no_ac = EquipmentAudit(floor_area_m2=ccis_audit.floor_area_m2)
    for item in ccis_audit.items:
        if not item.is_cooling:
            audit_no_ac.add_item(item)

    demand_without_ac = compute_non_cooling_demand(annual_schedule_2019, audit_no_ac, default_building)

    np.testing.assert_allclose(demand_with_ac.tier1_kwh, demand_without_ac.tier1_kwh)
    np.testing.assert_allclose(demand_with_ac.tier2_kwh, demand_without_ac.tier2_kwh)
    np.testing.assert_allclose(demand_with_ac.tier3_kwh, demand_without_ac.tier3_kwh)


def test_non_cooling_determinism(
    annual_schedule_2019: OccupancySchedule,
    ccis_audit: EquipmentAudit,
    default_building: Building,
) -> None:
    """Verify compute_non_cooling_demand is a pure deterministic calculation."""
    d1 = compute_non_cooling_demand(annual_schedule_2019, ccis_audit, default_building)
    d2 = compute_non_cooling_demand(annual_schedule_2019, ccis_audit, default_building)

    np.testing.assert_array_equal(d1.tier1_kwh, d2.tier1_kwh)
    np.testing.assert_array_equal(d1.tier2_kwh, d2.tier2_kwh)
    np.testing.assert_array_equal(d1.tier3_kwh, d2.tier3_kwh)
