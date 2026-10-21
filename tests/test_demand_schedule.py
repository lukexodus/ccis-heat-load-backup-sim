"""Unit tests for academic calendar and building occupancy schedule engine.

Covers DEM-001.1 and DEM-001.4 requirements per docs/prompts/DEM-001-PROMPT.md.
"""

from __future__ import annotations

import datetime

import numpy as np
import pandas as pd
import pytest

from ccis_sim.core.interfaces import OccupancySchedule
from ccis_sim.demand.schedule import (
    PHILIPPINES_HOLIDAYS_2016,
    PHILIPPINES_HOLIDAYS_2019,
    AcademicCalendar,
    build_occupancy_schedule,
    get_default_philippine_holidays,
)
from ccis_sim.weather.loader import load_weather_fixture


def test_schedule_contract_signature_conformance() -> None:
    """Verify build_occupancy_schedule accepts keyword calendar per phase2 contract."""
    ts = pd.date_range("2019-01-01", periods=24, freq="h", tz="Asia/Manila").astype(str)
    cal = AcademicCalendar(year=2019)

    # Call with explicit keyword-only calendar
    schedule = build_occupancy_schedule(pd.Series(ts), calendar=cal)
    assert isinstance(schedule, OccupancySchedule)
    assert len(schedule) == 24

    # Call with calendar=None (default calendar construction)
    schedule_default = build_occupancy_schedule(pd.Series(ts))
    assert isinstance(schedule_default, OccupancySchedule)
    assert len(schedule_default) == 24


def test_schedule_array_lengths_and_types() -> None:
    """Verify all 4 schedule arrays are numpy ndarrays of identical length and expected dtypes."""
    ts = pd.date_range("2019-09-01", periods=48, freq="h", tz="Asia/Manila").astype(str)
    sched = build_occupancy_schedule(ts)

    assert isinstance(sched.occupancy_fraction, np.ndarray)
    assert isinstance(sched.is_class_day, np.ndarray)
    assert isinstance(sched.is_break, np.ndarray)
    assert isinstance(sched.is_holiday, np.ndarray)

    assert sched.occupancy_fraction.dtype == np.float64
    assert sched.is_class_day.dtype == bool
    assert sched.is_break.dtype == bool
    assert sched.is_holiday.dtype == bool

    assert len(sched.occupancy_fraction) == 48
    assert len(sched.is_class_day) == 48
    assert len(sched.is_break) == 48
    assert len(sched.is_holiday) == 48


def test_schedule_occupancy_bounds() -> None:
    """Verify occupancy fraction is strictly bounded within [0.0, 1.0] across full weather fixture."""
    w19 = load_weather_fixture(2019)
    sched = build_occupancy_schedule(w19["timestamp"])

    assert len(sched) == 8760
    assert np.all(sched.occupancy_fraction >= 0.0)
    assert np.all(sched.occupancy_fraction <= 1.0)
    assert np.all(np.isfinite(sched.occupancy_fraction))


def test_schedule_weekday_diurnal_profile() -> None:
    """Verify hour-by-hour profile on a regular semester Wednesday."""
    # 2019-09-18 is a regular Wednesday during Semester 1 (no holiday, no break)
    ts = pd.date_range("2019-09-18 00:00:00+08:00", periods=24, freq="h")
    sched = build_occupancy_schedule(ts)

    assert np.all(sched.is_class_day)
    assert not np.any(sched.is_break)
    assert not np.any(sched.is_holiday)

    # Check night off-hours
    assert sched.occupancy_fraction[2] == 0.0   # 02:00
    assert sched.occupancy_fraction[6] == 0.0   # 06:00

    # Early arrival
    assert sched.occupancy_fraction[7] == 0.20  # 07:00

    # Morning lecture/lab peak
    for h in (8, 9, 10, 11):
        assert sched.occupancy_fraction[h] == 1.00

    # Lunch dip
    assert sched.occupancy_fraction[12] == 0.60

    # Afternoon lecture/lab
    for h in (13, 14, 15, 16, 17):
        assert sched.occupancy_fraction[h] == 0.95

    # Evening graduate/extension
    assert sched.occupancy_fraction[18] == 0.30
    assert sched.occupancy_fraction[19] == 0.30

    # Night off-hours
    assert sched.occupancy_fraction[20] == 0.0
    assert sched.occupancy_fraction[23] == 0.0


def test_schedule_saturday_diurnal_profile() -> None:
    """Verify hour-by-hour profile on a regular semester Saturday."""
    # 2019-09-21 is a Saturday during Semester 1
    ts = pd.date_range("2019-09-21 00:00:00+08:00", periods=24, freq="h")
    sched = build_occupancy_schedule(ts)

    assert np.all(sched.is_class_day)
    assert not np.any(sched.is_break)
    assert not np.any(sched.is_holiday)

    # Off-hours
    assert sched.occupancy_fraction[5] == 0.0
    assert sched.occupancy_fraction[7] == 0.0

    # Saturday morning labs/NSTP
    for h in (8, 9, 10, 11):
        assert sched.occupancy_fraction[h] == 0.50

    # Saturday lunch
    assert sched.occupancy_fraction[12] == 0.20

    # Saturday afternoon labs
    for h in (13, 14, 15, 16):
        assert sched.occupancy_fraction[h] == 0.30

    # Evening closed
    assert sched.occupancy_fraction[17] == 0.0
    assert sched.occupancy_fraction[22] == 0.0


def test_schedule_sunday_building_closure() -> None:
    """Verify Sundays have zero occupancy and is_class_day is False."""
    # 2019-09-22 is a Sunday during Semester 1
    ts = pd.date_range("2019-09-22 00:00:00+08:00", periods=24, freq="h")
    sched = build_occupancy_schedule(ts)

    assert not np.any(sched.is_class_day)
    assert np.all(sched.occupancy_fraction == 0.0)


def test_schedule_holiday_on_weekday() -> None:
    """Verify a gazetted holiday falling on a weekday suppresses class day and sets occupancy to 0."""
    # 2019-04-18 is Maundy Thursday (regular holiday during Semester 2)
    ts = pd.date_range("2019-04-18 00:00:00+08:00", periods=24, freq="h")
    sched = build_occupancy_schedule(ts)

    assert np.all(sched.is_holiday)
    assert not np.any(sched.is_class_day)
    assert np.all(sched.occupancy_fraction == 0.0)


def test_schedule_break_week_admin_occupancy() -> None:
    """Verify term break weekdays maintain skeleton administrative presence."""
    # 2019-07-10 is a Wednesday during Summer Break (midyear)
    ts = pd.date_range("2019-07-10 00:00:00+08:00", periods=24, freq="h")
    sched = build_occupancy_schedule(ts)

    assert np.all(sched.is_break)
    assert not np.any(sched.is_class_day)
    assert not np.any(sched.is_holiday)

    # Skeleton admin presence during office hours (08:00 - 12:00, 13:00 - 17:00)
    for h in (8, 9, 10, 11, 13, 14, 15, 16):
        assert sched.occupancy_fraction[h] == pytest.approx(0.15)

    # Lunch hour dip
    assert sched.occupancy_fraction[12] == pytest.approx(0.05)

    # Off-hours
    assert sched.occupancy_fraction[6] == 0.0
    assert sched.occupancy_fraction[18] == 0.0


def test_schedule_dst_free_timezone() -> None:
    """Verify DST-free Philippine Standard Time (+08:00) produces continuous 24-hour days without jumps."""
    ts = pd.date_range("2019-01-01 00:00:00+08:00", periods=8760, freq="h")
    sched = build_occupancy_schedule(ts)
    assert len(sched) == 8760


def test_schedule_leap_year_2016() -> None:
    """Verify schedule handles 2016 leap year weather fixture and 2016 gazetted holidays."""
    w16 = load_weather_fixture(2016)
    cal16 = AcademicCalendar(year=2016)
    sched = build_occupancy_schedule(w16["timestamp"], calendar=cal16)

    assert len(sched) == 8760
    assert np.sum(sched.is_holiday) > 0
    # National Election Day (2016-05-09) was a special non-working holiday
    assert cal16.is_holiday(datetime.date(2016, 5, 9))


def test_schedule_determinism() -> None:
    """Verify identical inputs produce bitwise identical schedule arrays."""
    ts = pd.date_range("2019-08-01 00:00:00+08:00", periods=500, freq="h")
    s1 = build_occupancy_schedule(ts)
    s2 = build_occupancy_schedule(ts)

    np.testing.assert_array_equal(s1.occupancy_fraction, s2.occupancy_fraction)
    np.testing.assert_array_equal(s1.is_class_day, s2.is_class_day)
    np.testing.assert_array_equal(s1.is_break, s2.is_break)
    np.testing.assert_array_equal(s1.is_holiday, s2.is_holiday)


def test_schedule_invalid_empty_timestamps() -> None:
    """Verify passing empty timestamps raises ValueError."""
    with pytest.raises(ValueError, match="must not be empty"):
        build_occupancy_schedule([])


def test_academic_calendar_validation() -> None:
    """Verify AcademicCalendar rejects invalid ratio parameters."""
    with pytest.raises(ValueError, match="break_weekday_admin_ratio"):
        AcademicCalendar(break_weekday_admin_ratio=1.5)

    with pytest.raises(ValueError, match="break_lunch_ratio"):
        AcademicCalendar(break_lunch_ratio=-0.1)
