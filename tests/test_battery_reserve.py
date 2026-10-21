"""Unit tests and verification for BAT-002 Battery Outage Reserve & State-of-Charge Constraints.

Verifies operational and hardware protection floors, emergency drawdown override,
chemical idle losses (ambient self-discharge + tare), floor clamping, and
compliance with the verification harness idle-loss allowance per [D-26] and [D-32].
"""

from __future__ import annotations

import inspect
import math

import pytest

from ccis_sim.battery.reserve import HOURS_PER_MONTH, apply_idle_losses, soc_floor_kwh
from ccis_sim.core.models import Battery, HourlyRecord, LoadTier
from ccis_sim.core.verification import run_verification_harness


@pytest.fixture
def standard_battery() -> Battery:
    """Standard 100 kWh battery with 10% min SoC and 20% emergency reserve."""
    return Battery(
        capacity_kwh=100.0,
        round_trip_efficiency=0.92,
        min_soc_pct=0.10,
        emergency_reserve_pct=0.20,
        self_discharge_pct_per_month=2.0,
        tare_loss_kw=0.01,
    )


def test_contract_signatures_conformance() -> None:
    """Validate that soc_floor_kwh and apply_idle_losses signatures conform to contract."""
    sig_floor = inspect.signature(soc_floor_kwh)
    p_floor = list(sig_floor.parameters.values())
    assert len(p_floor) == 4
    assert p_floor[0].name == "battery"
    assert p_floor[1].name == "grid_available"
    assert p_floor[1].kind == inspect.Parameter.KEYWORD_ONLY
    assert p_floor[2].name == "active_load_tier"
    assert p_floor[2].kind == inspect.Parameter.KEYWORD_ONLY
    assert p_floor[3].name == "allow_emergency_drawdown"
    assert p_floor[3].kind == inspect.Parameter.KEYWORD_ONLY
    assert p_floor[3].default is False

    sig_idle = inspect.signature(apply_idle_losses)
    p_idle = list(sig_idle.parameters.values())
    assert len(p_idle) == 3
    assert p_idle[0].name == "soc_kwh"
    assert p_idle[1].name == "battery"
    assert p_idle[2].name == "delta_t_hours"
    assert p_idle[2].default == 1.0


def test_soc_floor_all_cases(standard_battery: Battery) -> None:
    """Verify floor computation across all grid, tier, and drawdown combinations.

    Battery has 100 kWh capacity, 10% min_soc (10 kWh), 20% emergency reserve (20 kWh).
    """
    # 1. Grid Energized (grid_available=True): Operational floor holds back 20% reserve
    for tier in (LoadTier.TIER_1_CRITICAL, LoadTier.TIER_2_ESSENTIAL, LoadTier.TIER_3_SHEDDABLE, 1, 2, 3):
        for drawdown in (False, True):
            # When grid is energized, emergency drawdown has no effect
            assert soc_floor_kwh(
                standard_battery,
                grid_available=True,
                active_load_tier=tier,
                allow_emergency_drawdown=drawdown,
            ) == pytest.approx(30.0)

    # 2. Outage without emergency drawdown (grid_available=False, drawdown=False)
    # Reserve is released; floor drops to hardware cell-protection floor (10 kWh)
    for tier in (LoadTier.TIER_1_CRITICAL, LoadTier.TIER_2_ESSENTIAL, LoadTier.TIER_3_SHEDDABLE, 1, 2, 3):
        assert soc_floor_kwh(
            standard_battery,
            grid_available=False,
            active_load_tier=tier,
            allow_emergency_drawdown=False,
        ) == pytest.approx(10.0)

    # 3. Outage with emergency drawdown enabled (grid_available=False, drawdown=True)
    # Tier 1 (Critical) and Tier 2 (Essential) permit catastrophic drawdown to 0.0 kWh per [D-25]
    for tier in (LoadTier.TIER_1_CRITICAL, LoadTier.TIER_2_ESSENTIAL, 1, 2):
        assert soc_floor_kwh(
            standard_battery,
            grid_available=False,
            active_load_tier=tier,
            allow_emergency_drawdown=True,
        ) == 0.0

    # Tier 3 (Sheddable) does NOT permit drawdown below hardware protection floor
    for tier in (LoadTier.TIER_3_SHEDDABLE, 3):
        assert soc_floor_kwh(
            standard_battery,
            grid_available=False,
            active_load_tier=tier,
            allow_emergency_drawdown=True,
        ) == pytest.approx(10.0)


def test_soc_floor_zero_capacity() -> None:
    """Verify zero-capacity battery always returns 0.0 floor."""
    zero_bat = Battery(capacity_kwh=0.0, round_trip_efficiency=0.92, min_soc_pct=0.10)
    assert soc_floor_kwh(zero_bat, grid_available=True, active_load_tier=LoadTier.TIER_1_CRITICAL) == 0.0
    assert soc_floor_kwh(zero_bat, grid_available=False, active_load_tier=LoadTier.TIER_1_CRITICAL) == 0.0


def test_soc_floor_invalid_inputs(standard_battery: Battery) -> None:
    """Verify input validation on soc_floor_kwh."""
    with pytest.raises(TypeError, match="battery must be an instance of Battery"):
        soc_floor_kwh("not_a_battery", grid_available=True, active_load_tier=1)  # type: ignore

    with pytest.raises(TypeError, match="grid_available must be a bool"):
        soc_floor_kwh(standard_battery, grid_available="yes", active_load_tier=1)  # type: ignore

    with pytest.raises(TypeError, match="allow_emergency_drawdown must be a bool"):
        soc_floor_kwh(standard_battery, grid_available=True, active_load_tier=1, allow_emergency_drawdown="no")  # type: ignore

    with pytest.raises(ValueError, match="active_load_tier must be a valid LoadTier"):
        soc_floor_kwh(standard_battery, grid_available=True, active_load_tier=0)
    with pytest.raises(ValueError, match="active_load_tier must be a valid LoadTier"):
        soc_floor_kwh(standard_battery, grid_available=True, active_load_tier=4)


def test_apply_idle_losses_nominal(standard_battery: Battery) -> None:
    """Verify nominal idle loss calculation over 1.0 h and 2.5 h.

    Capacity = 100 kWh, self_discharge = 2.0%/month, tare = 0.01 kW.
    P_self = 100 * 0.02 / 730 = 2/730 kW.
    P_idle = 2/730 + 0.01 = 0.002739726 + 0.01 = 0.012739726 kW.
    """
    cur_soc = 80.0
    p_self = 100.0 * (2.0 / 100.0) / HOURS_PER_MONTH
    p_idle = p_self + 0.01

    # 1. Delta t = 1.0 h
    new_soc, loss = apply_idle_losses(cur_soc, standard_battery, delta_t_hours=1.0)
    expected_loss = p_idle * 1.0
    assert loss == pytest.approx(expected_loss)
    assert new_soc == pytest.approx(cur_soc - expected_loss)

    # 2. Delta t = 2.5 h
    new_soc_25, loss_25 = apply_idle_losses(cur_soc, standard_battery, delta_t_hours=2.5)
    expected_loss_25 = p_idle * 2.5
    assert loss_25 == pytest.approx(expected_loss_25)
    assert new_soc_25 == pytest.approx(cur_soc - expected_loss_25)


def test_apply_idle_losses_zero_parameters() -> None:
    """Verify zero idle parameters leave SoC completely unchanged."""
    zero_idle_bat = Battery(
        capacity_kwh=100.0,
        round_trip_efficiency=0.92,
        self_discharge_pct_per_month=0.0,
        tare_loss_kw=0.0,
    )
    new_soc, loss = apply_idle_losses(50.0, zero_idle_bat, delta_t_hours=5.0)
    assert loss == 0.0
    assert new_soc == 50.0


def test_apply_idle_losses_clamping_at_floor(standard_battery: Battery) -> None:
    """Verify idle losses clamp exactly at min_soc_kwh hardware protection floor per [D-32]."""
    floor = standard_battery.min_soc_kwh  # 10.0 kWh

    # 1. Initial SoC slightly above floor (10.005 kWh) where nominal loss is ~0.0127 kWh
    cur_soc = 10.005
    new_soc, loss = apply_idle_losses(cur_soc, standard_battery, delta_t_hours=1.0)
    assert new_soc == pytest.approx(floor)
    assert loss == pytest.approx(0.005)

    # 2. Initial SoC exactly at floor (10.0 kWh)
    new_soc_at_floor, loss_at_floor = apply_idle_losses(floor, standard_battery, delta_t_hours=1.0)
    assert new_soc_at_floor == pytest.approx(floor)
    assert loss_at_floor == 0.0

    # 3. Initial SoC below floor (5.0 kWh, e.g. following emergency drawdown)
    # Does not deduct further idle losses below cell starvation threshold
    new_soc_sub, loss_sub = apply_idle_losses(5.0, standard_battery, delta_t_hours=1.0)
    assert new_soc_sub == pytest.approx(5.0)
    assert loss_sub == 0.0


def test_apply_idle_losses_zero_capacity() -> None:
    """Verify zero-capacity battery returns zero loss and zero SoC."""
    zero_bat = Battery(capacity_kwh=0.0, round_trip_efficiency=0.92, min_soc_pct=0.10)
    new_soc, loss = apply_idle_losses(0.0, zero_bat, delta_t_hours=1.0)
    assert new_soc == 0.0
    assert loss == 0.0


def test_apply_idle_losses_validation(standard_battery: Battery) -> None:
    """Verify error checking on apply_idle_losses."""
    with pytest.raises(TypeError, match="battery must be an instance of Battery"):
        apply_idle_losses(10.0, "not_battery")  # type: ignore

    with pytest.raises(TypeError, match="numeric"):
        apply_idle_losses("10.0", standard_battery)  # type: ignore

    with pytest.raises(ValueError, match="must be finite"):
        apply_idle_losses(float("nan"), standard_battery)

    with pytest.raises(ValueError, match="strictly positive"):
        apply_idle_losses(10.0, standard_battery, delta_t_hours=0.0)

    with pytest.raises(ValueError, match="cannot be physically negative"):
        apply_idle_losses(-1.0, standard_battery)

    with pytest.raises(ValueError, match="exceeds battery rated capacity"):
        apply_idle_losses(120.0, standard_battery)


def test_48_hour_outage_reference_loop(standard_battery: Battery) -> None:
    """Simulate a 48-hour continuous outage reference loop without external track dependency.

    Evaluates that:
    1. Without emergency drawdown, SoC never drops below min_soc_kwh floor (10 kWh).
    2. With emergency drawdown on Tier 1 load, SoC discharges safely down to 0.0 kWh.
    """
    eta = math.sqrt(standard_battery.round_trip_efficiency)

    # 1. Normal Outage (no emergency drawdown, Tier 2 load)
    # Start fully charged at 100 kWh. Continuous demand 5.0 kW AC.
    soc = 100.0
    for hour in range(1, 49):
        floor = soc_floor_kwh(
            standard_battery,
            grid_available=False,
            active_load_tier=LoadTier.TIER_2_ESSENTIAL,
            allow_emergency_drawdown=False,
        )
        assert floor == pytest.approx(10.0)

        # Local reference discharge
        demand_ac = 5.0
        avail_chem = max(0.0, soc - floor)
        max_dis_ac = min(standard_battery.max_discharge_power_kw, avail_chem * eta)
        dis_ac = min(demand_ac, max_dis_ac)

        soc = soc - (dis_ac / eta)
        soc, idle_loss = apply_idle_losses(soc, standard_battery)

        assert soc >= floor - 1e-9

    # 2. Emergency Drawdown Outage (allow_emergency_drawdown=True, Tier 1 load)
    # Start at 12 kWh (close to floor). Large demand to exhaust battery.
    soc_em = 12.0
    for hour in range(1, 49):
        floor_em = soc_floor_kwh(
            standard_battery,
            grid_available=False,
            active_load_tier=LoadTier.TIER_1_CRITICAL,
            allow_emergency_drawdown=True,
        )
        assert floor_em == 0.0

        demand_ac = 5.0
        avail_chem = max(0.0, soc_em - floor_em)
        max_dis_ac = min(standard_battery.max_discharge_power_kw, avail_chem * eta)
        dis_ac = min(demand_ac, max_dis_ac)

        soc_em = soc_em - (dis_ac / eta)
        soc_em, idle_loss = apply_idle_losses(soc_em, standard_battery)

        assert soc_em >= 0.0 - 1e-9

    # Battery reached complete exhaustion safely
    assert soc_em == pytest.approx(0.0, abs=1e-6)


def test_chained_idle_losses_pass_verification_harness(standard_battery: Battery) -> None:
    """Verify that a multi-hour simulation chaining apply_idle_losses passes verification harness.

    Tests that hour-to-hour SoC continuity checks accept idle losses within
    the max_idle_loss_per_hour allowance and do not trip SOC_CONTINUITY or SOC_CUMULATIVE_DRIFT.
    """
    initial_soc = 80.0
    cur_soc = initial_soc
    eta = math.sqrt(standard_battery.round_trip_efficiency)
    records: list[HourlyRecord] = []

    for hour in range(1, 73):
        # Alternate between light charging, light discharging, and idle
        if hour % 3 == 1:
            chg_req = 10.0
            dis_req = 0.0
            headroom = max(0.0, standard_battery.capacity_kwh - cur_soc)
            chg_ac = min(chg_req, headroom / eta)
            dis_ac = 0.0
            cur_soc = min(standard_battery.capacity_kwh, cur_soc + chg_ac * eta)
        elif hour % 3 == 2:
            chg_req = 0.0
            dis_req = 8.0
            available = max(0.0, cur_soc - standard_battery.min_soc_kwh)
            chg_ac = 0.0
            dis_ac = min(dis_req, available * eta)
            cur_soc = max(standard_battery.min_soc_kwh, cur_soc - dis_ac / eta)
        else:
            chg_ac = 0.0
            dis_ac = 0.0

        # Apply idle loss after dispatch
        cur_soc, idle_loss = apply_idle_losses(cur_soc, standard_battery)

        record = HourlyRecord(
            hour=hour,
            timestamp=f"2019-01-01 {hour-1:02d}:00:00+08:00",
            temp_ambient_c=26.0,
            humidity_rel_pct=65.0,
            ghi_w_m2=0.0,
            demand_gross_kwh=dis_ac,
            demand_served_kwh=dis_ac,
            solar_generation_kwh=chg_ac,
            solar_to_demand_kwh=0.0,
            solar_to_battery_kwh=chg_ac,
            solar_curtailed_kwh=0.0,
            battery_soc_kwh=cur_soc,
            battery_charge_kwh=chg_ac,
            battery_discharge_kwh=dis_ac,
            grid_import_kwh=0.0,
            unserved_load_kwh=0.0,
            grid_available=True,
            active_load_tier=LoadTier.TIER_3_SHEDDABLE,
        )
        records.append(record)

    report = run_verification_harness(records, battery=standard_battery, initial_soc_kwh=initial_soc)
    assert report.is_valid, (
        f"Verification harness failed: conservation={report.conservation_violations}, "
        f"battery={report.battery_violations}, subflow={report.subflow_violations}, "
        f"cum_drift={report.cumulative_net_drift_kwh}"
    )
