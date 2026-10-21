"""Unit and property tests for priority-based tiered load shedding controller (OUT-002).

Validates:
- OUT-002.1: Tier mapping and comparison of audited equipment inventory to D-10 nominal 2/18/80 split.
- OUT-002.2: Instantaneous Tier 3 shedding on utility grid failure.
- OUT-002.3: Battery low-SoC Tier 2 shedding rule (<20% SoC) with exact threshold boundaries.
- OUT-002.4: UnservedTracker metrics accumulation, reverse-priority shortfall allocation, and full-service tracking.
- Per-tier energy conservation invariants and sub-flow balance conformance via HourlyRecord and verification harness.
"""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from ccis_sim.core.interfaces import ShedResult
from ccis_sim.core.models import Battery, HourlyRecord, LoadTier
from ccis_sim.core.verification import check_subflow_balance, run_verification_harness
from ccis_sim.demand.equipment import EquipmentAudit
from ccis_sim.outage.shedding import (
    TierAuditComparison,
    UnservedTracker,
    compute_tier_audit_shares,
    shed_for_hour,
)


@pytest.fixture
def standard_battery() -> Battery:
    """Fixture providing a standard 100 kWh battery with 10% min SoC."""
    return Battery(
        capacity_kwh=100.0,
        round_trip_efficiency=0.92,
        min_soc_pct=0.10,
        emergency_reserve_pct=0.20,
        max_charge_c_rate=0.5,
        max_discharge_c_rate=1.0,
    )


@pytest.fixture
def equipment_audit_fixture() -> EquipmentAudit:
    """Fixture loading the committed CCIS equipment audit CSV."""
    fixture_path = Path("data/fixtures/equipment-audit-ccis.csv")
    return EquipmentAudit.load_from_csv(fixture_path)


# -----------------------------------------------------------------------------
# OUT-002.1: Tier Mapping & Audit Share Helper
# -----------------------------------------------------------------------------


def test_compute_tier_audit_shares_against_committed_fixture(
    equipment_audit_fixture: EquipmentAudit,
) -> None:
    """Validate tier connected capacity shares and verify documented discrepancy against D-10 nominal."""
    comparison = compute_tier_audit_shares(equipment_audit_fixture)

    assert isinstance(comparison, TierAuditComparison)
    # Check total connected load matches [D-16]/[D-19] (147.805 kW)
    assert math.isclose(comparison.total_connected_kw, 147.805, rel_tol=1e-4)

    # Check tier breakdown
    assert math.isclose(comparison.tier1_connected_kw, 1.215, rel_tol=1e-4)
    assert math.isclose(comparison.tier2_connected_kw, 15.360, rel_tol=1e-4)
    assert math.isclose(comparison.tier3_connected_kw, 131.230, rel_tol=1e-4)

    # Check connected percentage shares (~0.82%, ~10.39%, ~88.79%)
    assert math.isclose(comparison.tier1_connected_pct, (1.215 / 147.805) * 100.0, rel_tol=1e-4)
    assert math.isclose(comparison.tier2_connected_pct, (15.360 / 147.805) * 100.0, rel_tol=1e-4)
    assert math.isclose(comparison.tier3_connected_pct, (131.230 / 147.805) * 100.0, rel_tol=1e-4)

    # Check comparison deltas against nominal 2/18/80
    assert math.isclose(comparison.nominal_tier1_pct, 2.0)
    assert math.isclose(comparison.nominal_tier2_pct, 18.0)
    assert math.isclose(comparison.nominal_tier3_pct, 80.0)

    assert comparison.tier1_delta_pct < 0.0  # ~0.82% is lower than 2.0%
    assert comparison.tier2_delta_pct < 0.0  # ~10.39% is lower than 18.0%
    assert comparison.tier3_delta_pct > 0.0  # ~88.79% is higher than 80.0%

    d = comparison.as_dict()
    assert "total_connected_kw" in d
    assert "tier1_delta_pct" in d


def test_compute_tier_audit_shares_empty_audit() -> None:
    """Check zero-equipment audit edge case."""
    empty_audit = EquipmentAudit(items=[])
    comp = compute_tier_audit_shares(empty_audit)
    assert comp.total_connected_kw == 0.0
    assert comp.tier1_connected_pct == 0.0
    assert comp.tier2_connected_pct == 0.0
    assert comp.tier3_connected_pct == 0.0


# -----------------------------------------------------------------------------
# OUT-002.2: Automated Shedding on Grid Failure (Instant Tier 3 Drop)
# -----------------------------------------------------------------------------


def test_grid_available_all_tiers_served(standard_battery: Battery) -> None:
    """When grid is available, all tiers are served regardless of battery SoC."""
    demand = (2.0, 18.0, 80.0)
    # Even with low SoC (e.g. 5.0 kWh < 20 kWh threshold), grid provides power
    result = shed_for_hour(
        demand,
        grid_available=True,
        soc_kwh=5.0,
        battery=standard_battery,
    )
    assert result.active_tier == LoadTier.TIER_3_SHEDDABLE
    assert result.served_kwh == (2.0, 18.0, 80.0)
    assert result.unserved_kwh == (0.0, 0.0, 0.0)


def test_instant_tier3_shed_on_grid_loss(standard_battery: Battery) -> None:
    """When grid fails and SoC is healthy (>=20%), Tier 3 is instantly shed, Tiers 1+2 served."""
    demand = (2.5, 15.0, 75.0)
    result = shed_for_hour(
        demand,
        grid_available=False,
        soc_kwh=50.0,  # 50 kWh is well above 20.0 kWh threshold
        battery=standard_battery,
    )
    assert result.active_tier == LoadTier.TIER_2_ESSENTIAL
    assert result.served_kwh == (2.5, 15.0, 0.0)
    assert result.unserved_kwh == (0.0, 0.0, 75.0)


def test_grid_restoration_returns_to_tier3(standard_battery: Battery) -> None:
    """Grid restoration immediately returns active tier to Tier 3."""
    demand = (1.5, 12.0, 60.0)
    # Hour 1: Outage with low SoC -> Tier 1 only
    r1 = shed_for_hour(
        demand,
        grid_available=False,
        soc_kwh=15.0,
        battery=standard_battery,
    )
    assert r1.active_tier == LoadTier.TIER_1_CRITICAL

    # Hour 2: Grid restored -> Tier 3 full service
    r2 = shed_for_hour(
        demand,
        grid_available=True,
        soc_kwh=15.0,
        battery=standard_battery,
    )
    assert r2.active_tier == LoadTier.TIER_3_SHEDDABLE
    assert r2.served_kwh == demand
    assert r2.unserved_kwh == (0.0, 0.0, 0.0)


# -----------------------------------------------------------------------------
# OUT-002.3: Battery Low-SoC Tier 2 Shedding Rule & Exact Boundaries
# -----------------------------------------------------------------------------


def test_soc_threshold_exact_boundary(standard_battery: Battery) -> None:
    """Test exact behavior at the 20% SoC boundary: strictly below vs equal vs strictly above."""
    demand = (1.0, 10.0, 50.0)
    # standard_battery capacity = 100 kWh, 20% threshold = 20.0 kWh
    threshold = 20.0

    # 1. Just below threshold (19.9999 kWh): Tier 2 is shed
    r_below = shed_for_hour(
        demand,
        grid_available=False,
        soc_kwh=threshold - 1e-4,
        battery=standard_battery,
        tier2_shed_soc_fraction=0.20,
    )
    assert r_below.active_tier == LoadTier.TIER_1_CRITICAL
    assert r_below.served_kwh == (1.0, 0.0, 0.0)
    assert r_below.unserved_kwh == (0.0, 10.0, 50.0)

    # 2. Exactly equal to threshold (20.0000 kWh): Tier 2 is served
    r_equal = shed_for_hour(
        demand,
        grid_available=False,
        soc_kwh=threshold,
        battery=standard_battery,
        tier2_shed_soc_fraction=0.20,
    )
    assert r_equal.active_tier == LoadTier.TIER_2_ESSENTIAL
    assert r_equal.served_kwh == (1.0, 10.0, 0.0)
    assert r_equal.unserved_kwh == (0.0, 0.0, 50.0)

    # 3. Just above threshold (20.0001 kWh): Tier 2 is served
    r_above = shed_for_hour(
        demand,
        grid_available=False,
        soc_kwh=threshold + 1e-4,
        battery=standard_battery,
        tier2_shed_soc_fraction=0.20,
    )
    assert r_above.active_tier == LoadTier.TIER_2_ESSENTIAL
    assert r_above.served_kwh == (1.0, 10.0, 0.0)
    assert r_above.unserved_kwh == (0.0, 0.0, 50.0)


def test_custom_tier2_shed_soc_fraction(standard_battery: Battery) -> None:
    """Verify custom tier2_shed_soc_fraction parameter decouples from battery emergency reserve."""
    demand = (2.0, 20.0, 80.0)
    # Battery emergency reserve is 20%, but test custom 35% shed threshold (35.0 kWh)
    r_at_30 = shed_for_hour(
        demand,
        grid_available=False,
        soc_kwh=30.0,
        battery=standard_battery,
        tier2_shed_soc_fraction=0.35,
    )
    # 30 kWh < 35 kWh -> Tier 2 shed
    assert r_at_30.active_tier == LoadTier.TIER_1_CRITICAL
    assert r_at_30.served_kwh == (2.0, 0.0, 0.0)

    r_at_40 = shed_for_hour(
        demand,
        grid_available=False,
        soc_kwh=40.0,
        battery=standard_battery,
        tier2_shed_soc_fraction=0.35,
    )
    # 40 kWh >= 35 kWh -> Tier 2 served
    assert r_at_40.active_tier == LoadTier.TIER_2_ESSENTIAL
    assert r_at_40.served_kwh == (2.0, 20.0, 0.0)


# -----------------------------------------------------------------------------
# Conservation Invariant & Subflow Balance Conformance
# -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    "demand,grid_up,soc",
    [
        ((1.2, 15.3, 85.0), True, 50.0),
        ((1.2, 15.3, 85.0), False, 30.0),
        ((1.2, 15.3, 85.0), False, 10.0),
        ((0.0, 0.0, 0.0), False, 5.0),
        ((5.0, 0.0, 25.0), False, 15.0),
    ],
)
def test_per_tier_conservation_invariant(
    demand: tuple[float, float, float],
    grid_up: bool,
    soc: float,
    standard_battery: Battery,
) -> None:
    """Assert served + unserved == demand for every tier across all operating regimes."""
    res = shed_for_hour(demand, grid_available=grid_up, soc_kwh=soc, battery=standard_battery)

    for i in range(3):
        assert math.isclose(res.served_kwh[i] + res.unserved_kwh[i], demand[i], abs_tol=1e-9)


def test_harness_subflow_balance_integration(standard_battery: Battery) -> None:
    """Verify that records constructed from shed_for_hour strictly satisfy the harness subflow checks."""
    demand = (2.0, 18.0, 80.0)
    records: list[HourlyRecord] = []

    # Simulate 3 sequential hours: Grid Up, Outage with High SoC, Outage with Low SoC
    scenarios = [
        (True, 60.0),
        (False, 50.0),
        (False, 15.0),
    ]

    for h, (grid_avail, soc) in enumerate(scenarios, start=1):
        res = shed_for_hour(demand, grid_available=grid_avail, soc_kwh=soc, battery=standard_battery)
        gross = sum(demand)
        served = sum(res.served_kwh)
        unserved = sum(res.unserved_kwh)

        # Build HourlyRecord reflecting the shedding decision
        # Hour 1: Grid import = served = 100.0
        # Hour 2: Battery discharge = served = 20.0
        # Hour 3: Battery discharge = served = 2.0
        import_kwh = served if grid_avail else 0.0
        discharge_kwh = 0.0 if grid_avail else served

        rec = HourlyRecord(
            hour=h,
            timestamp=f"2019-01-01T{h:02d}:00:00+08:00",
            temp_ambient_c=25.0,
            humidity_rel_pct=70.0,
            ghi_w_m2=0.0,
            demand_gross_kwh=gross,
            demand_served_kwh=served,
            solar_generation_kwh=0.0,
            solar_to_demand_kwh=0.0,
            solar_to_battery_kwh=0.0,
            solar_curtailed_kwh=0.0,
            battery_charge_kwh=0.0,
            battery_discharge_kwh=discharge_kwh,
            battery_soc_kwh=soc,
            grid_import_kwh=import_kwh,
            unserved_load_kwh=unserved,
            grid_available=grid_avail,
            active_load_tier=int(res.active_tier),
        )
        records.append(rec)

    # Validate with check_subflow_balance
    violations = check_subflow_balance(records)
    assert len(violations) == 0, f"Expected 0 subflow violations, got {violations}"

    # Verify each individual record has 0.0 residual
    for r in records:
        assert r.energy_balance_residual_kwh <= 1e-6


# -----------------------------------------------------------------------------
# OUT-002.4: UnservedTracker & Shortfall Allocation
# -----------------------------------------------------------------------------


def test_unserved_tracker_normal_operation_no_outages(standard_battery: Battery) -> None:
    """When grid is always available, tracker accumulates zero unserved load and zero outage hours."""
    tracker = UnservedTracker()
    demand = (2.0, 10.0, 40.0)

    for _ in range(24):
        res = shed_for_hour(demand, grid_available=True, soc_kwh=80.0, battery=standard_battery)
        tracker.record(res, grid_available=True, battery_shortfall_kwh=0.0)

    summary = tracker.summary()
    assert summary["total_hours"] == 24
    assert summary["total_outage_hours"] == 0
    assert summary["total_unserved_kwh"] == 0.0
    assert summary["outage_hours_tier1_served_pct"] == 100.0


def test_unserved_tracker_multi_hour_outage_with_shortfall(standard_battery: Battery) -> None:
    """Validate reverse-priority shortfall allocation over a 3-hour outage scenario.

    Hour 1: Outage, SoC healthy (50 kWh) -> T1=2, T2=10 served, T3=80 shed. Battery supplies 12 kWh (no shortfall).
    Hour 2: Outage, SoC healthy (30 kWh) -> T1=2, T2=10 served, T3=80 shed. Battery shortfall of 4 kWh.
            Shortfall cuts Tier 2 served from 10 to 6 kWh. Tier 1 remains 100% served.
    Hour 3: Outage, SoC low (10 kWh < 20 kWh) -> T1=2 served, T2=10 shed, T3=80 shed. Battery shortfall of 0.5 kWh.
            Shortfall cuts Tier 1 served from 2.0 to 1.5 kWh.
    """
    tracker = UnservedTracker()
    demand = (2.0, 10.0, 80.0)

    # Hour 1: No shortfall
    r1 = shed_for_hour(demand, grid_available=False, soc_kwh=50.0, battery=standard_battery)
    act_s1, act_u1 = tracker.record(r1, grid_available=False, battery_shortfall_kwh=0.0)
    assert act_s1 == (2.0, 10.0, 0.0)
    assert act_u1 == (0.0, 0.0, 80.0)

    # Hour 2: Shortfall = 4.0 kWh (cuts Tier 2)
    r2 = shed_for_hour(demand, grid_available=False, soc_kwh=30.0, battery=standard_battery)
    act_s2, act_u2 = tracker.record(r2, grid_available=False, battery_shortfall_kwh=4.0)
    assert act_s2 == (2.0, 6.0, 0.0)
    assert act_u2 == (0.0, 4.0, 80.0)

    # Hour 3: Tier 2 shed by policy; shortfall = 0.5 kWh (cuts Tier 1)
    r3 = shed_for_hour(demand, grid_available=False, soc_kwh=10.0, battery=standard_battery)
    act_s3, act_u3 = tracker.record(r3, grid_available=False, battery_shortfall_kwh=0.5)
    assert act_s3 == (1.5, 0.0, 0.0)
    assert act_u3 == (0.5, 10.0, 80.0)

    # Evaluate cumulative totals
    assert tracker.total_hours == 3
    assert tracker.total_outage_hours == 3

    # Tier 1 fully served in Hours 1 and 2 (unserved == 0.0), but not in Hour 3 (unserved == 0.5)
    assert tracker.outage_hours_tier1_served == 2
    assert math.isclose(tracker.outage_hours_tier1_served_pct, (2 / 3) * 100.0, rel_tol=1e-4)

    # Tier 2 fully served in Hour 1 (unserved == 0.0), not in Hour 2 (shortfall) or Hour 3 (policy shed)
    assert tracker.outage_hours_tier2_served == 1
    assert math.isclose(tracker.outage_hours_tier2_served_pct, (1 / 3) * 100.0, rel_tol=1e-4)

    # Tier 3 was never fully served during blackout
    assert tracker.outage_hours_tier3_served == 0
    assert tracker.outage_hours_tier3_served_pct == 0.0

    # Total unserved energy
    assert math.isclose(tracker.unserved_tier1_kwh, 0.5)
    assert math.isclose(tracker.unserved_tier2_kwh, 14.0)  # 0 + 4.0 + 10.0
    assert math.isclose(tracker.unserved_tier3_kwh, 240.0)  # 80.0 * 3
    assert math.isclose(tracker.total_unserved_kwh, 254.5)

    # Total served energy
    assert math.isclose(tracker.served_tier1_kwh, 5.5)  # 2.0 + 2.0 + 1.5
    assert math.isclose(tracker.served_tier2_kwh, 16.0)  # 10.0 + 6.0 + 0.0
    assert math.isclose(tracker.served_tier3_kwh, 0.0)
    assert math.isclose(tracker.total_served_kwh, 21.5)

    # Check conservation across the entire 3 hours
    total_demand = sum(demand) * 3  # (2 + 10 + 80) * 3 = 276.0
    assert math.isclose(tracker.total_served_kwh + tracker.total_unserved_kwh, total_demand)


def test_tracker_catastrophic_shortfall(standard_battery: Battery) -> None:
    """Verify that a massive shortfall cascades from Tier 3 down to Tier 1."""
    tracker = UnservedTracker()
    demand = (1.0, 5.0, 20.0)  # Total 26.0

    # Grid up: all 26 served, but shortfall = 24.0
    r = shed_for_hour(demand, grid_available=True, soc_kwh=100.0, battery=standard_battery)
    # Shortfall cuts:
    # Tier 3: cuts all 20.0 (rem = 4.0)
    # Tier 2: cuts 4.0 (rem = 0.0, Tier 2 served remaining = 1.0)
    # Tier 1: uncut (1.0 served)
    act_s, act_u = tracker.record(r, grid_available=True, battery_shortfall_kwh=24.0)
    assert act_s == (1.0, 1.0, 0.0)
    assert act_u == (0.0, 4.0, 20.0)


# -----------------------------------------------------------------------------
# Input Validation & Edge Cases
# -----------------------------------------------------------------------------


def test_zero_demand_edge_case(standard_battery: Battery) -> None:
    """Verify clean zero demand handling."""
    res = shed_for_hour((0.0, 0.0, 0.0), grid_available=False, soc_kwh=0.0, battery=standard_battery)
    assert res.served_kwh == (0.0, 0.0, 0.0)
    assert res.unserved_kwh == (0.0, 0.0, 0.0)
    assert res.active_tier == LoadTier.TIER_1_CRITICAL


def test_invalid_arguments_raise_errors(standard_battery: Battery) -> None:
    """Assert invalid types, sentinels, and out-of-bounds parameters raise appropriate exceptions."""
    # Invalid tuple length
    with pytest.raises(TypeError):
        shed_for_hour((1.0, 2.0), grid_available=True, soc_kwh=50.0, battery=standard_battery)  # type: ignore

    # Negative demand
    with pytest.raises(ValueError, match="non-negative"):
        shed_for_hour((-1.0, 2.0, 3.0), grid_available=True, soc_kwh=50.0, battery=standard_battery)

    # Non-finite demand
    with pytest.raises(ValueError, match="finite"):
        shed_for_hour((float("nan"), 2.0, 3.0), grid_available=True, soc_kwh=50.0, battery=standard_battery)

    # Negative SoC
    with pytest.raises(ValueError, match="non-negative"):
        shed_for_hour((1.0, 2.0, 3.0), grid_available=True, soc_kwh=-5.0, battery=standard_battery)

    # Invalid fraction
    with pytest.raises(ValueError, match="in \\[0.0, 1.0\\]"):
        shed_for_hour((1.0, 2.0, 3.0), grid_available=True, soc_kwh=50.0, battery=standard_battery, tier2_shed_soc_fraction=1.5)

    # Tracker negative shortfall
    tracker = UnservedTracker()
    r = shed_for_hour((1.0, 2.0, 3.0), grid_available=True, soc_kwh=50.0, battery=standard_battery)
    with pytest.raises(ValueError, match="non-negative"):
        tracker.record(r, grid_available=True, battery_shortfall_kwh=-1.0)
