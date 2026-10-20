"""Unit tests for Phase 2 interface types and data contracts per [D-26]."""

from __future__ import annotations

import math
import numpy as np
import pytest

from ccis_sim.core.interfaces import (
    BatteryStepResult,
    OccupancySchedule,
    OutageSchedule,
    ShedResult,
    TieredDemand,
)
from ccis_sim.core.models import Battery, LoadTier, OutageEvent, OutageType


def test_tiered_demand_valid():
    """Verify standard TieredDemand initialization, gross_kwh property, and indexing."""
    t1 = np.array([1.0, 2.0, 3.0])
    t2 = np.array([4.0, 5.0, 6.0])
    t3 = np.array([7.0, 8.0, 9.0])
    td = TieredDemand(tier1_kwh=t1, tier2_kwh=t2, tier3_kwh=t3)

    assert len(td) == 3
    assert np.array_equal(td.gross_kwh, np.array([12.0, 15.0, 18.0]))
    assert td.at(0) == (1.0, 4.0, 7.0)
    assert td.at(2) == (3.0, 6.0, 9.0)


def test_tiered_demand_validation_errors():
    """Verify TieredDemand rejects unequal lengths, empty arrays, NaN, and negative values."""
    # Unequal lengths
    with pytest.raises(ValueError, match="Tier array lengths must be equal"):
        TieredDemand(np.array([1.0, 2.0]), np.array([1.0]), np.array([1.0, 2.0]))

    # Empty arrays
    with pytest.raises(ValueError, match="must not be empty"):
        TieredDemand(np.array([]), np.array([]), np.array([]))

    # NaN / Inf
    with pytest.raises(ValueError, match="non-finite"):
        TieredDemand(np.array([1.0, float("nan")]), np.array([1.0, 2.0]), np.array([1.0, 2.0]))

    # Negative values
    with pytest.raises(ValueError, match="negative"):
        TieredDemand(np.array([1.0, -0.5]), np.array([1.0, 2.0]), np.array([1.0, 2.0]))


def test_occupancy_schedule_valid():
    """Verify OccupancySchedule instantiation and property behaviors."""
    occ = np.array([0.0, 0.5, 1.0])
    cd = np.array([False, True, True])
    brk = np.array([True, False, False])
    hol = np.array([False, False, False])

    sched = OccupancySchedule(
        occupancy_fraction=occ,
        is_class_day=cd,
        is_break=brk,
        is_holiday=hol,
    )
    assert len(sched) == 3
    assert sched.is_class_day[1] is np.True_ or sched.is_class_day[1] is True


def test_occupancy_schedule_validation_errors():
    """Verify OccupancySchedule bounds and length validations."""
    occ = np.array([0.0, 1.2])  # > 1.0
    cd = np.array([True, True])
    brk = np.array([False, False])
    hol = np.array([False, False])

    with pytest.raises(ValueError, match="within \\[0.0, 1.0\\]"):
        OccupancySchedule(occ, cd, brk, hol)

    with pytest.raises(ValueError, match="must be equal"):
        OccupancySchedule(np.array([0.5]), cd, brk, hol)


def test_outage_schedule_valid_and_defaults():
    """Verify OutageSchedule initialization and default GHI multiplier."""
    event = OutageEvent(
        start_hour=100,
        duration_hours=8,
        outage_type=OutageType.TYPHOON,
    )
    ga = np.ones(8760, dtype=bool)
    ga[100:108] = False

    sched = OutageSchedule(
        events=(event,),
        grid_available=ga,
        year_type="typhoon",
    )
    assert len(sched) == 8760
    assert sched.year_type == "typhoon"
    assert len(sched.ghi_multiplier) == 8760
    assert np.all(sched.ghi_multiplier == 1.0)


def test_outage_schedule_validation_errors():
    """Verify OutageSchedule validation checks."""
    ga = np.ones(10, dtype=bool)
    with pytest.raises(ValueError, match="year_type must be 'normal' or 'typhoon'"):
        OutageSchedule(events=(), grid_available=ga, year_type="invalid_regime")  # type: ignore

    with pytest.raises(ValueError, match="Length mismatch"):
        OutageSchedule(events=(), grid_available=ga, year_type="normal", ghi_multiplier=np.ones(5))

    with pytest.raises(ValueError, match="non-negative"):
        OutageSchedule(events=(), grid_available=ga, year_type="normal", ghi_multiplier=np.array([-1.0] * 10))


def test_battery_step_result_valid_and_mutual_exclusion():
    """Verify BatteryStepResult validation and simultaneous charge/discharge rejection."""
    # Valid discharge step
    res_dis = BatteryStepResult(
        soc_kwh=50.0,
        charge_kwh=0.0,
        discharge_kwh=10.0,
        charge_curtailed_kwh=0.0,
        discharge_unmet_kwh=2.0,
    )
    assert res_dis.soc_kwh == 50.0

    # Mutual exclusion rejection
    with pytest.raises(ValueError, match="Simultaneous charging.*and discharging.*prohibited"):
        BatteryStepResult(
            soc_kwh=50.0,
            charge_kwh=5.0,
            discharge_kwh=5.0,
            charge_curtailed_kwh=0.0,
            discharge_unmet_kwh=0.0,
        )

    # Negative value rejection
    with pytest.raises(ValueError, match="must be non-negative"):
        BatteryStepResult(
            soc_kwh=-1.0,
            charge_kwh=0.0,
            discharge_kwh=0.0,
            charge_curtailed_kwh=0.0,
            discharge_unmet_kwh=0.0,
        )


def test_shed_result_valid_and_validation_errors():
    """Verify ShedResult structure and validation checks."""
    sr = ShedResult(
        active_tier=LoadTier.TIER_2_ESSENTIAL,
        served_kwh=(1.0, 5.0, 0.0),
        unserved_kwh=(0.0, 0.0, 20.0),
    )
    assert sr.active_tier == LoadTier.TIER_2_ESSENTIAL

    # Invalid active tier
    with pytest.raises(ValueError, match="valid LoadTier"):
        ShedResult(
            active_tier=4,  # type: ignore
            served_kwh=(1.0, 5.0, 0.0),
            unserved_kwh=(0.0, 0.0, 20.0),
        )

    # Invalid tuple length
    with pytest.raises(ValueError, match="3-tuple"):
        ShedResult(
            active_tier=LoadTier.TIER_1_CRITICAL,
            served_kwh=(1.0, 5.0),  # type: ignore
            unserved_kwh=(0.0, 0.0, 0.0),
        )


def test_battery_idle_loss_attributes_default_and_validation():
    """Verify Battery dataclass self_discharge_pct_per_month and tare_loss_kw attributes."""
    b = Battery(capacity_kwh=100.0)
    assert b.self_discharge_pct_per_month == 2.0
    assert b.tare_loss_kw == 0.0

    with pytest.raises(ValueError, match="self_discharge_pct_per_month must be non-negative"):
        Battery(capacity_kwh=100.0, self_discharge_pct_per_month=-1.0)

    with pytest.raises(ValueError, match="tare_loss_kw must be non-negative"):
        Battery(capacity_kwh=100.0, tare_loss_kw=-0.5)
