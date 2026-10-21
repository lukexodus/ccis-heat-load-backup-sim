"""Building electricity demand models: equipment inventory schedules and cooling load."""

from ccis_sim.demand.equipment import EquipmentAudit, EquipmentItem
from ccis_sim.demand.mock_bills import (
    DEFAULT_ACADEMIC_WEIGHTS,
    DEFAULT_COOLING_MULTIPLIERS,
    SyntheticBillGenerator,
    SyntheticMonthlyBill,
)
from ccis_sim.demand.non_cooling import compute_non_cooling_demand
from ccis_sim.demand.schedule import (
    PHILIPPINES_HOLIDAYS_2016,
    PHILIPPINES_HOLIDAYS_2019,
    AcademicCalendar,
    build_occupancy_schedule,
    get_default_philippine_holidays,
)

__all__ = [
    "AcademicCalendar",
    "DEFAULT_ACADEMIC_WEIGHTS",
    "DEFAULT_COOLING_MULTIPLIERS",
    "EquipmentAudit",
    "EquipmentItem",
    "PHILIPPINES_HOLIDAYS_2016",
    "PHILIPPINES_HOLIDAYS_2019",
    "SyntheticBillGenerator",
    "SyntheticMonthlyBill",
    "build_occupancy_schedule",
    "compute_non_cooling_demand",
    "get_default_philippine_holidays",
]
