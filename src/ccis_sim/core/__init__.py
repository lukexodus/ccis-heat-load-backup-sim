"""Core domain models, interface protocols, and conservation invariants."""

from ccis_sim.core.interfaces import (
    BatteryStepResult,
    OccupancySchedule,
    OutageSchedule,
    ShedResult,
    TieredDemand,
)
from ccis_sim.core.models import (
    Battery,
    Building,
    HourlyRecord,
    LoadTier,
    OutageEvent,
    OutageType,
    RoomInventory,
    SolarArray,
)
from ccis_sim.core.verification import (
    BatteryBoundaryViolation,
    ConservationViolation,
    VerificationReport,
    ViolationType,
    assert_simulation_valid,
    check_energy_conservation,
    check_subflow_balance,
    compute_cumulative_tolerance,
    create_golden_scenario,
    run_verification_harness,
    validate_battery_boundaries,
)

__all__ = [
    "Battery",
    "BatteryBoundaryViolation",
    "BatteryStepResult",
    "Building",
    "ConservationViolation",
    "HourlyRecord",
    "LoadTier",
    "OccupancySchedule",
    "OutageEvent",
    "OutageSchedule",
    "OutageType",
    "RoomInventory",
    "ShedResult",
    "SolarArray",
    "TieredDemand",
    "VerificationReport",
    "ViolationType",
    "assert_simulation_valid",
    "check_energy_conservation",
    "check_subflow_balance",
    "compute_cumulative_tolerance",
    "create_golden_scenario",
    "run_verification_harness",
    "validate_battery_boundaries",
]

