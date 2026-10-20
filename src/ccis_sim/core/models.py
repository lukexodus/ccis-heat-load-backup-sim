"""Canonical immutable domain models and interface contracts for CCIS simulation.

Conforms to specifications locked in:
- docs/context/conceptual-model.md §4
- docs/decisions/decision-log.md [D-05] through [D-11]
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Mapping


class OutageType(str, Enum):
    """Classification of power outages per decision [D-11]."""

    NORMAL = "normal"
    TYPHOON = "typhoon"


class LoadTier(int, Enum):
    """Priority load shedding tier per decision [D-10]."""

    TIER_1_CRITICAL = 1   # Life-safety, emergency egress, network headend (2% load)
    TIER_2_ESSENTIAL = 2  # Faculty rooms, admin, servers/smart rooms (18% load)
    TIER_3_SHEDDABLE = 3  # Computer labs, comfort HVAC (80% load - shed during blackouts)


@dataclass(frozen=True)
class RoomInventory:
    """Designated space breakdown for CCIS 2-storey facility per decision [D-06]."""

    hyflex_smart_rooms: int = 2
    lecture_rooms: int = 6
    cod_office: int = 1
    dean_and_secretary: int = 1
    faculty_rooms: int = 2
    computer_labs: int = 6

    @property
    def total_rooms(self) -> int:
        """Total count of designated spaces in CCIS facility."""
        return (
            self.hyflex_smart_rooms
            + self.lecture_rooms
            + self.cod_office
            + self.dean_and_secretary
            + self.faculty_rooms
            + self.computer_labs
        )


@dataclass(frozen=True)
class Building:
    """Building envelope and architectural baseline for MMSU CCIS per decisions [D-06], [D-07], and [D-18].

    Static building envelope parameters. Equipment electrical loading and schedules
    are parameterized and loaded separately in CORE-003.
    usable_rooftop_area_m2 is derived from the ~1,250 m² footprint of the 2-storey facility
    minus parapets and mechanical setbacks, accommodating up to 200 kWp PV at 6.0 m²/kWp (per [D-18]).
    """

    name: str = "MMSU College of Computing and Information Sciences"
    gross_floor_area_m2: float = 2500.0
    usable_rooftop_area_m2: float = 1200.0   # [ASSUMPTION / [D-18]] ~1,250 m² 2-storey footprint minus setbacks (~1,200 m² usable)
    floors: int = 2
    rooms: RoomInventory = field(default_factory=RoomInventory)
    t_base_cooling_c: float = 24.0           # Balance-point temperature per [D-07]
    cooling_sensitivity_per_c: float = 0.04  # 4%/°C electrical demand increase per [D-07]
    latent_cooling_penalty: float = 0.20     # +20% latent cooling penalty per [D-07]

    def __post_init__(self) -> None:
        if self.gross_floor_area_m2 <= 0:
            raise ValueError(f"gross_floor_area_m2 must be positive, got {self.gross_floor_area_m2}")
        if self.usable_rooftop_area_m2 <= 0:
            raise ValueError(
                f"usable_rooftop_area_m2 must be positive, got {self.usable_rooftop_area_m2}"
            )
        if self.floors <= 0:
            raise ValueError(f"floors must be positive, got {self.floors}")


@dataclass(frozen=True)
class SolarArray:
    """Rooftop solar photovoltaic array parameters per decision [D-08].

    Can be instantiated across scenario matrix capacities (0, 50, 100, 200 kWp).
    """

    capacity_kwp: float
    tilt_deg: float = 15.0                  # 15° True South per [D-08]
    azimuth_deg: float = 180.0              # 180° = True South
    performance_ratio: float = 0.77         # Baseline system PR per [D-08]
    temp_coeff_pct_per_c: float = -0.40     # -0.40%/°C thermal coefficient per [D-08]
    noct_c: float = 45.0                    # Nominal Operating Cell Temperature per [D-08]
    roof_mount_derate_c: float = 10.0       # +10°C thermal penalty for roof mounting per [D-08]
    t_ref_c: float = 25.0                   # Standard Test Condition reference temperature

    def __post_init__(self) -> None:
        if self.capacity_kwp < 0.0:
            raise ValueError(f"capacity_kwp must be non-negative, got {self.capacity_kwp}")
        if not (0.0 <= self.performance_ratio <= 1.0):
            raise ValueError(f"performance_ratio must be in [0, 1], got {self.performance_ratio}")


@dataclass(frozen=True)
class Battery:
    """Lithium Iron Phosphate (LFP) Battery Energy Storage System (BESS) per decisions [D-09] and [D-17].

    Can be instantiated across scenario matrix capacities (0, 50, 100, 200 kWh).
    Static parameters and boundary limits. Dispatch logic is handled in Phase 2 (BAT-001/002).
    emergency_reserve_pct specifies a configurable operational blackout reserve (per [D-17] and BAT-002),
    distinct from and additional to the non-discretionary 10% min SoC protection floor from [D-09].
    """

    capacity_kwh: float
    round_trip_efficiency: float = 0.92      # 92% round-trip efficiency per [D-09]
    usable_dod: float = 0.90                 # 90% usable depth of discharge per [D-09]
    min_soc_pct: float = 0.10                # 10% minimum SoC reserve per [D-09]
    max_charge_c_rate: float = 0.5           # 0.5C maximum charging rate per [D-09]
    max_discharge_c_rate: float = 1.0        # 1.0C maximum continuous discharge per [D-09]
    emergency_reserve_pct: float = 0.20      # [D-17] Default 20% emergency blackout reserve (configurable in [0.10, 0.50] for BAT-002)
    self_discharge_pct_per_month: float = 2.0  # [D-26] Monthly ambient self-discharge rate (default 2.0%/month for LFP)
    tare_loss_kw: float = 0.0                # [D-26] Standby tare loss in kW (inverter/BMS tare modeled on SoC-side)

    def __post_init__(self) -> None:
        if self.capacity_kwh < 0.0:
            raise ValueError(f"capacity_kwh must be non-negative, got {self.capacity_kwh}")
        if not (0.0 < self.round_trip_efficiency <= 1.0):
            raise ValueError(
                f"round_trip_efficiency must be in (0, 1], got {self.round_trip_efficiency}"
            )
        if not (0.0 < self.usable_dod <= 1.0):
            raise ValueError(f"usable_dod must be in (0, 1], got {self.usable_dod}")
        if not (0.0 <= self.min_soc_pct < 1.0):
            raise ValueError(f"min_soc_pct must be in [0, 1), got {self.min_soc_pct}")
        if not (0.0 <= self.emergency_reserve_pct <= 1.0):
            raise ValueError(
                f"emergency_reserve_pct must be in [0, 1], got {self.emergency_reserve_pct}"
            )
        if self.self_discharge_pct_per_month < 0.0:
            raise ValueError(
                f"self_discharge_pct_per_month must be non-negative, got {self.self_discharge_pct_per_month}"
            )
        if self.tare_loss_kw < 0.0:
            raise ValueError(f"tare_loss_kw must be non-negative, got {self.tare_loss_kw}")
        if self.min_soc_pct + self.usable_dod > 1.0 + 1e-9:
            raise ValueError(
                f"min_soc_pct + usable_dod cannot exceed 1.0, got {self.min_soc_pct + self.usable_dod}"
            )

    @property
    def min_soc_kwh(self) -> float:
        """Absolute minimum allowable energy stored in battery (kWh)."""
        return self.capacity_kwh * self.min_soc_pct

    @property
    def max_soc_kwh(self) -> float:
        """Maximum allowable energy stored in battery (kWh)."""
        return self.capacity_kwh * (self.min_soc_pct + self.usable_dod)

    @property
    def usable_capacity_kwh(self) -> float:
        """Total usable energy capacity between min_soc and max_soc (kWh)."""
        return self.capacity_kwh * self.usable_dod

    @property
    def emergency_reserve_kwh(self) -> float:
        """Outage emergency reserve energy buffer (kWh)."""
        return self.capacity_kwh * self.emergency_reserve_pct

    @property
    def max_charge_power_kw(self) -> float:
        """Maximum continuous charging power limit (kW)."""
        return self.capacity_kwh * self.max_charge_c_rate

    @property
    def max_discharge_power_kw(self) -> float:
        """Maximum continuous discharging power limit (kW)."""
        return self.capacity_kwh * self.max_discharge_c_rate


@dataclass(frozen=True)
class OutageEvent:
    """Discrete utility grid outage event per decision [D-11]."""

    start_hour: int
    duration_hours: float
    outage_type: OutageType = OutageType.NORMAL
    solar_depression_factor: float = 1.0
    solar_depression_duration_hours: float = 0.0

    def __post_init__(self) -> None:
        if self.start_hour < 1 or self.start_hour > 8760:
            raise ValueError(f"start_hour must be in [1, 8760], got {self.start_hour}")
        if self.duration_hours <= 0.0:
            raise ValueError(f"duration_hours must be positive, got {self.duration_hours}")
        if not (0.0 <= self.solar_depression_factor <= 1.0):
            raise ValueError(
                f"solar_depression_factor must be in [0, 1], got {self.solar_depression_factor}"
            )

    @property
    def end_hour(self) -> float:
        """Hour at which grid supply is restored."""
        return self.start_hour + self.duration_hours

    def is_active_at(self, hour: int) -> bool:
        """Check whether the grid outage is active at a given chronological hour."""
        return self.start_hour <= hour < self.end_hour

    def is_solar_depressed_at(self, hour: int) -> bool:
        """Check whether solar depression is active at a given chronological hour."""
        depression_end = self.start_hour + self.solar_depression_duration_hours
        return self.start_hour <= hour < depression_end


@dataclass(frozen=True)
class HourlyRecord:
    """Canonical time-step record representing the complete state of the CCIS microgrid.

    Fields match docs/context/conceptual-model.md §4 verbatim.
    """

    hour: int                     # 1 to 8760 (chronological hour of year)
    timestamp: str                # ISO 8601 string (e.g., "2026-04-15T14:00:00+08:00")
    temp_ambient_c: float         # Ambient dry-bulb temperature (°C)
    humidity_rel_pct: float       # Relative humidity (%)
    ghi_w_m2: float               # Global Horizontal Solar Irradiance (W/m²)
    demand_gross_kwh: float       # Total unconstrained building electrical load (kWh)
    demand_served_kwh: float      # Actual electrical load served after load shedding (kWh)
    solar_generation_kwh: float   # Net AC electrical generation from PV array (kWh)
    solar_to_demand_kwh: float    # Direct solar electricity consumed by building (kWh)
    solar_to_battery_kwh: float   # Excess solar electricity routed to battery charging (kWh)
    solar_curtailed_kwh: float    # Excess generation curtailed or exported to grid (kWh)
    battery_soc_kwh: float        # Battery usable energy stored at end of hour (kWh)
    battery_charge_kwh: float     # Energy transferred into battery during this hour (kWh)
    battery_discharge_kwh: float  # Energy extracted from battery during this hour (kWh)
    grid_import_kwh: float        # Electrical energy imported from INEC utility grid (kWh)
    unserved_load_kwh: float      # Deficit electrical energy unserved during blackout (kWh)
    grid_available: bool          # True = INEC grid UP; False = Outage / Blackout
    active_load_tier: int         # 1 = Life Safety only, 2 = Essential IT, 3 = Normal (all loads)

    def __post_init__(self) -> None:
        if self.hour < 1 or self.hour > 8760:
            raise ValueError(f"hour must be in range 1..8760, got {self.hour}")
        if self.active_load_tier not in (1, 2, 3):
            raise ValueError(f"active_load_tier must be 1, 2, or 3, got {self.active_load_tier}")

    @property
    def energy_balance_residual_kwh(self) -> float:
        """Calculate physical energy balance residual: |Total Energy In - Total Energy Out|.

        Total In = solar_generation_kwh + grid_import_kwh + battery_discharge_kwh
        Total Out = demand_served_kwh + battery_charge_kwh + solar_curtailed_kwh
        """
        energy_in = self.solar_generation_kwh + self.grid_import_kwh + self.battery_discharge_kwh
        energy_out = self.demand_served_kwh + self.battery_charge_kwh + self.solar_curtailed_kwh
        return abs(energy_in - energy_out)

    @property
    def signed_residual_kwh(self) -> float:
        """Calculate signed energy balance residual: Total Energy In - Total Energy Out.

        Total In = solar_generation_kwh + grid_import_kwh + battery_discharge_kwh
        Total Out = demand_served_kwh + battery_charge_kwh + solar_curtailed_kwh
        Signed Residual = Total In - Total Out
        """
        energy_in = self.solar_generation_kwh + self.grid_import_kwh + self.battery_discharge_kwh
        energy_out = self.demand_served_kwh + self.battery_charge_kwh + self.solar_curtailed_kwh
        return energy_in - energy_out

    def is_energy_conserved(self, tolerance: float = 1e-5) -> bool:
        """Verify strict energy balance invariant (residual <= 10^-5 kWh)."""
        return self.energy_balance_residual_kwh <= tolerance

    def to_dict(self) -> dict[str, Any]:
        """Convert record to primitive Python dictionary suitable for JSON/CSV/DataFrame."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> HourlyRecord:
        """Construct an HourlyRecord from a dictionary or mapping, with type coercion."""
        return cls(
            hour=int(data["hour"]),
            timestamp=str(data["timestamp"]),
            temp_ambient_c=float(data["temp_ambient_c"]),
            humidity_rel_pct=float(data["humidity_rel_pct"]),
            ghi_w_m2=float(data["ghi_w_m2"]),
            demand_gross_kwh=float(data["demand_gross_kwh"]),
            demand_served_kwh=float(data["demand_served_kwh"]),
            solar_generation_kwh=float(data["solar_generation_kwh"]),
            solar_to_demand_kwh=float(data["solar_to_demand_kwh"]),
            solar_to_battery_kwh=float(data["solar_to_battery_kwh"]),
            solar_curtailed_kwh=float(data["solar_curtailed_kwh"]),
            battery_soc_kwh=float(data["battery_soc_kwh"]),
            battery_charge_kwh=float(data["battery_charge_kwh"]),
            battery_discharge_kwh=float(data["battery_discharge_kwh"]),
            grid_import_kwh=float(data["grid_import_kwh"]),
            unserved_load_kwh=float(data["unserved_load_kwh"]),
            grid_available=bool(data["grid_available"]),
            active_load_tier=int(data["active_load_tier"]),
        )
