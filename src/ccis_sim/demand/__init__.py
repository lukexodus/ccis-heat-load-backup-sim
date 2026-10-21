"""Building electricity demand models: equipment inventory schedules and cooling load."""

from ccis_sim.demand.cooling import compute_cooling_demand
from ccis_sim.demand.equipment import EquipmentAudit, EquipmentItem
from ccis_sim.demand.mock_bills import (
    DEFAULT_ACADEMIC_WEIGHTS,
    DEFAULT_COOLING_MULTIPLIERS,
    SyntheticBillGenerator,
    SyntheticMonthlyBill,
)

__all__ = [
    "DEFAULT_ACADEMIC_WEIGHTS",
    "DEFAULT_COOLING_MULTIPLIERS",
    "EquipmentAudit",
    "EquipmentItem",
    "SyntheticBillGenerator",
    "SyntheticMonthlyBill",
    "compute_cooling_demand",
]
