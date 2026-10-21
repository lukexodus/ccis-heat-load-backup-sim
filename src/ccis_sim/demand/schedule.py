"""Academic calendar and building occupancy schedule engine.

Generates hourly occupancy fraction profiles and operational state flags
(class day, break, holiday) for the CCIS building conforming to:
- docs/prompts/DEM-001-PROMPT.md
- docs/context/phase2-interface-contract.md
- docs/decisions/decision-log.md [D-27]
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import Sequence

import numpy as np
import pandas as pd

from ccis_sim.core.interfaces import OccupancySchedule


# ==============================================================================
# Philippine Statutory Holidays (Fixture Years 2016 and 2019)
# Reference: Proclamation No. 555 (2019) and Proclamation No. 1105 / 1107 (2016)
# ==============================================================================

# Philippine regular and special non-working holidays for calendar year 2019
PHILIPPINES_HOLIDAYS_2019: frozenset[datetime.date] = frozenset(
    [
        datetime.date(2019, 1, 1),   # New Year's Day (Regular)
        datetime.date(2019, 2, 5),   # Chinese Lunar New Year (Special)
        datetime.date(2019, 2, 25),  # EDSA People Power Revolution (Special)
        datetime.date(2019, 4, 9),   # Araw ng Kagitingan / Day of Valor (Regular)
        datetime.date(2019, 4, 18),  # Maundy Thursday (Regular)
        datetime.date(2019, 4, 19),  # Good Friday (Regular)
        datetime.date(2019, 4, 20),  # Black Saturday (Special)
        datetime.date(2019, 5, 1),   # Labor Day (Regular)
        datetime.date(2019, 6, 5),   # Eid'l Fitr (Regular, Proclamation 729)
        datetime.date(2019, 6, 12),  # Independence Day (Regular)
        datetime.date(2019, 8, 12),  # Eid'l Adha (Regular, Proclamation 789)
        datetime.date(2019, 8, 21),  # Ninoy Aquino Day (Special)
        datetime.date(2019, 8, 26),  # National Heroes Day (Regular, last Mon of Aug)
        datetime.date(2019, 11, 1),  # All Saints' Day (Special)
        datetime.date(2019, 11, 2),  # All Souls' Day (Special)
        datetime.date(2019, 11, 30), # Bonifacio Day (Regular)
        datetime.date(2019, 12, 8),  # Feast of the Immaculate Conception (Special)
        datetime.date(2019, 12, 24), # Christmas Eve (Special)
        datetime.date(2019, 12, 25), # Christmas Day (Regular)
        datetime.date(2019, 12, 30), # Rizal Day (Regular)
        datetime.date(2019, 12, 31), # Last Day of the Year (Special)
    ]
)

# Philippine regular and special non-working holidays for calendar year 2016 (leap year)
PHILIPPINES_HOLIDAYS_2016: frozenset[datetime.date] = frozenset(
    [
        datetime.date(2016, 1, 1),   # New Year's Day (Regular)
        datetime.date(2016, 1, 2),   # Additional special non-working day
        datetime.date(2016, 2, 8),   # Chinese New Year (Special)
        datetime.date(2016, 2, 25),  # EDSA Revolution Anniversary (Special)
        datetime.date(2016, 3, 24),  # Maundy Thursday (Regular)
        datetime.date(2016, 3, 25),  # Good Friday (Regular)
        datetime.date(2016, 3, 26),  # Black Saturday (Special)
        datetime.date(2016, 4, 9),   # Araw ng Kagitingan (Regular)
        datetime.date(2016, 5, 1),   # Labor Day (Regular)
        datetime.date(2016, 5, 9),   # National Election Day (Special)
        datetime.date(2016, 6, 12),  # Independence Day (Regular)
        datetime.date(2016, 7, 6),   # Eid'l Fitr (Regular)
        datetime.date(2016, 8, 21),  # Ninoy Aquino Day (Special)
        datetime.date(2016, 8, 29),  # National Heroes Day (Regular)
        datetime.date(2016, 9, 12),  # Eid'l Adha (Regular)
        datetime.date(2016, 10, 31), # Additional special non-working day
        datetime.date(2016, 11, 1),  # All Saints' Day (Special)
        datetime.date(2016, 11, 30), # Bonifacio Day (Regular)
        datetime.date(2016, 12, 24), # Special non-working day
        datetime.date(2016, 12, 25), # Christmas Day (Regular)
        datetime.date(2016, 12, 26), # Additional special non-working day
        datetime.date(2016, 12, 30), # Rizal Day (Regular)
        datetime.date(2016, 12, 31), # Last Day of the Year (Special)
    ]
)


def get_default_philippine_holidays(year: int) -> frozenset[datetime.date]:
    """Return statutory holiday set for specified calendar year.

    For fixture years 2019 and 2016, returns exact historical gazetted holidays
    (including lunar/movable feasts Eid'l Fitr, Eid'l Adha, and Holy Week).
    For other years, computes fixed-date annual holidays plus National Heroes Day.
    """
    if year == 2019:
        return PHILIPPINES_HOLIDAYS_2019
    if year == 2016:
        return PHILIPPINES_HOLIDAYS_2016

    # Fixed-date statutory holidays
    fixed = {
        datetime.date(year, 1, 1),    # New Year's Day
        datetime.date(year, 2, 25),   # EDSA Revolution
        datetime.date(year, 4, 9),    # Araw ng Kagitingan
        datetime.date(year, 5, 1),    # Labor Day
        datetime.date(year, 6, 12),   # Independence Day
        datetime.date(year, 8, 21),   # Ninoy Aquino Day
        datetime.date(year, 11, 1),   # All Saints' Day
        datetime.date(year, 11, 30),  # Bonifacio Day
        datetime.date(year, 12, 8),   # Immaculate Conception
        datetime.date(year, 12, 24),  # Christmas Eve
        datetime.date(year, 12, 25),  # Christmas Day
        datetime.date(year, 12, 30),  # Rizal Day
        datetime.date(year, 12, 31),  # New Year's Eve
    }

    # National Heroes Day: last Monday of August
    last_day_august = datetime.date(year, 8, 31)
    offset = (last_day_august.weekday() - 0) % 7  # Monday is weekday 0
    nat_heroes_day = datetime.date(year, 8, 31 - offset)
    fixed.add(nat_heroes_day)

    return frozenset(fixed)


@dataclass(frozen=True)
class AcademicCalendar:
    """Academic calendar boundaries and holiday definitions for Philippine state university.

    Default schedule parameters reflect standard Mariano Marcos State University (MMSU)
    semester and term break alignments ([ASSUMPTION / [D-27]]):
    - Semester 1 (Aug 15 - Dec 15): 18-week academic term
    - Winter / Semestral Break (Dec 16 - Jan 14): semestral vacation and holiday closure
    - Semester 2 (Jan 15 - May 25): 18-week academic term
    - Summer / Midyear Break (May 26 - Aug 14): academic vacation, faculty research, midyear maintenance

    Attributes:
        year: Reference weather year (default 2019).
        sem1_start: (month, day) for Semester 1 commencement (default (8, 15)).
        sem1_end: (month, day) for Semester 1 conclusion (default (12, 15)).
        sem2_start: (month, day) for Semester 2 commencement (default (1, 15)).
        sem2_end: (month, day) for Semester 2 conclusion (default (5, 25)).
        holidays: Set of holiday dates; defaults to Philippine national gazetted holidays.
        break_weekday_admin_ratio: Skeleton faculty/staff occupancy during term break weekdays
            (default 0.15 per [ASSUMPTION / [D-27]]).
        break_lunch_ratio: Skeleton staff occupancy during lunch hour on break weekdays
            (default 0.05 per [ASSUMPTION / [D-27]]).
    """

    year: int = 2019
    sem1_start: tuple[int, int] = (8, 15)
    sem1_end: tuple[int, int] = (12, 15)
    sem2_start: tuple[int, int] = (1, 15)
    sem2_end: tuple[int, int] = (5, 25)
    holidays: frozenset[datetime.date] | None = None
    break_weekday_admin_ratio: float = 0.15
    break_lunch_ratio: float = 0.05

    def __post_init__(self) -> None:
        if self.holidays is None:
            object.__setattr__(self, "holidays", get_default_philippine_holidays(self.year))
        else:
            object.__setattr__(
                self,
                "holidays",
                frozenset(
                    h if isinstance(h, datetime.date) else pd.to_datetime(h).date()
                    for h in self.holidays
                ),
            )

        if not (0.0 <= self.break_weekday_admin_ratio <= 1.0):
            raise ValueError(
                f"break_weekday_admin_ratio must be in [0, 1], got {self.break_weekday_admin_ratio}"
            )
        if not (0.0 <= self.break_lunch_ratio <= 1.0):
            raise ValueError(f"break_lunch_ratio must be in [0, 1], got {self.break_lunch_ratio}")

    def is_holiday(self, d: datetime.date) -> bool:
        """Check if date is a statutory or special non-working holiday."""
        return d in self.holidays

    def is_semester(self, d: datetime.date) -> bool:
        """Check if date falls within regular semester terms (Sem 1 or Sem 2)."""
        sem1_s = datetime.date(d.year, self.sem1_start[0], self.sem1_start[1])
        sem1_e = datetime.date(d.year, self.sem1_end[0], self.sem1_end[1])
        sem2_s = datetime.date(d.year, self.sem2_start[0], self.sem2_start[1])
        sem2_e = datetime.date(d.year, self.sem2_end[0], self.sem2_end[1])

        return (sem1_s <= d <= sem1_e) or (sem2_s <= d <= sem2_e)

    def is_break(self, d: datetime.date) -> bool:
        """Check if date falls within academic break (winter or summer break)."""
        return not self.is_semester(d)


def build_occupancy_schedule(
    timestamps: pd.Series | Sequence[Any],
    *,
    calendar: AcademicCalendar | None = None,
) -> OccupancySchedule:
    """Build academic building occupancy profile and calendar operational state.

    Conforms strictly to docs/context/phase2-interface-contract.md:
    `build_occupancy_schedule(timestamps: pd.Series, *, calendar: AcademicCalendar | None = None) -> OccupancySchedule`

    Occupancy fraction conventions ([ASSUMPTION / [D-27]]):
    - Regular Class Weekdays (Mon-Fri, non-holiday during semester):
        00:00-07:00: 0.00 (closed)
        07:00-08:00: 0.20 (early arrival / prep)
        08:00-12:00: 1.00 (peak morning lecture/labs)
        12:00-13:00: 0.60 (lunch dip)
        13:00-18:00: 0.95 (afternoon lecture/labs)
        18:00-20:00: 0.30 (evening graduate/extension classes)
        20:00-24:00: 0.00 (closed)
    - Regular Class Saturdays (Sat, non-holiday during semester):
        00:00-08:00: 0.00
        08:00-12:00: 0.50 (morning lab sessions / NSTP)
        12:00-13:00: 0.20 (lunch dip)
        13:00-17:00: 0.30 (afternoon lab sessions)
        17:00-24:00: 0.00
    - Sundays and Gazetted Holidays:
        0.00 all hours (building fully closed)
    - Academic Break Weekdays (Mon-Fri during summer or semestral break, non-holiday):
        08:00-12:00: break_weekday_admin_ratio (0.15 skeleton faculty/admin presence)
        12:00-13:00: break_lunch_ratio (0.05 lunch hour)
        13:00-17:00: break_weekday_admin_ratio (0.15 afternoon office presence)
        all other hours: 0.00
    - Academic Break Weekends (Sat-Sun during break):
        0.00 all hours

    Args:
        timestamps: Series or sequence of ISO strings, DatetimeIndex, or datetime objects.
        calendar: AcademicCalendar instance; if None, defaults to AcademicCalendar(year=...).

    Returns:
        OccupancySchedule container with occupancy_fraction, is_class_day, is_break,
        and is_holiday numpy arrays of length N.
    """
    ts_series = pd.to_datetime(timestamps)
    n = len(ts_series)
    if n == 0:
        raise ValueError("timestamps sequence must not be empty.")

    # Determine reference year from timestamps if calendar not provided
    if calendar is None:
        ref_year = int(ts_series[0].year) if hasattr(ts_series, "iloc") else int(ts_series[0].year)
        cal = AcademicCalendar(year=ref_year)
    else:
        cal = calendar

    occ_arr = np.zeros(n, dtype=np.float64)
    class_day_arr = np.zeros(n, dtype=bool)
    break_arr = np.zeros(n, dtype=bool)
    holiday_arr = np.zeros(n, dtype=bool)

    # Convert to Python datetime series for fast component access
    dt_index = pd.DatetimeIndex(ts_series)
    dates = dt_index.date
    hours = dt_index.hour
    weekdays = dt_index.weekday  # 0=Monday, 5=Saturday, 6=Sunday

    # Precompute unique dates state to vectorize day-level flags
    unique_dates = np.unique(dates)
    day_is_holiday: dict[datetime.date, bool] = {d: cal.is_holiday(d) for d in unique_dates}
    day_is_break: dict[datetime.date, bool] = {d: cal.is_break(d) for d in unique_dates}
    day_is_sem: dict[datetime.date, bool] = {d: cal.is_semester(d) for d in unique_dates}

    for i in range(n):
        d = dates[i]
        h = hours[i]
        wd = weekdays[i]

        hol = day_is_holiday[d]
        brk = day_is_break[d]
        sem = day_is_sem[d]

        holiday_arr[i] = hol
        break_arr[i] = brk

        # Class day: scheduled semester day, not holiday, not Sunday (Mon-Sat during semester)
        is_class_d = sem and (not hol) and (wd < 6)
        class_day_arr[i] = is_class_d

        if hol or wd == 6:
            # Building closed on holidays and Sundays
            occ_arr[i] = 0.0
        elif is_class_d:
            # Regular semester schedule
            if wd < 5:
                # Weekdays (Mon-Fri)
                if h < 7 or h >= 20:
                    occ_arr[i] = 0.0
                elif h == 7:
                    occ_arr[i] = 0.20
                elif 8 <= h < 12:
                    occ_arr[i] = 1.00
                elif h == 12:
                    occ_arr[i] = 0.60
                elif 13 <= h < 18:
                    occ_arr[i] = 0.95
                elif 18 <= h < 20:
                    occ_arr[i] = 0.30
            else:
                # Saturday
                if h < 8 or h >= 17:
                    occ_arr[i] = 0.0
                elif 8 <= h < 12:
                    occ_arr[i] = 0.50
                elif h == 12:
                    occ_arr[i] = 0.20
                elif 13 <= h < 17:
                    occ_arr[i] = 0.30
        elif brk:
            # Term break schedule
            if wd < 5:
                # Break weekday: administrative presence
                if 8 <= h < 12 or 13 <= h < 17:
                    occ_arr[i] = cal.break_weekday_admin_ratio
                elif h == 12:
                    occ_arr[i] = cal.break_lunch_ratio
                else:
                    occ_arr[i] = 0.0
            else:
                # Break weekend (Sat-Sun)
                occ_arr[i] = 0.0
        else:
            # Fallback for non-class, non-break, non-holiday weekday
            occ_arr[i] = 0.0

    return OccupancySchedule(
        occupancy_fraction=occ_arr,
        is_class_day=class_day_arr,
        is_break=break_arr,
        is_holiday=holiday_arr,
    )
