# Task Report: CORE-001 — Implement Canonical Domain Models & Interface Contracts

**Date:** 2026-10-19  
**Agent:** gemini  
**Task ID:** CORE-001  
**Status:** done  
**Commit:** pending  
**Patch File:** `patch/CORE-001-gemini-domain-models.patch`  

---

## 1. Executive Summary

This task implements `CORE-001` (Canonical Domain Models & Interface Contracts, covering subtasks `CORE-001.1` through `CORE-001.4`), establishing the bedrock data contracts in `src/ccis_sim/core/` for the CCIS Heat, Load and Backup Power Simulation. 

All domain entities (`Building`, `RoomInventory`, `SolarArray`, `Battery`, `OutageEvent`, and `HourlyRecord`) are defined as frozen immutable dataclasses (`@dataclass(frozen=True)`). `Building` encodes the locked 18-room archetype from `[D-06]` and thermal baseline from `[D-07]`. `SolarArray` supports scenario matrix capacities (0, 50, 100, 200 kWp) with NOCT and rooftop derating parameters from `[D-08]`. `Battery` models LFP storage characteristics from `[D-09]` (92% RTE, 90% usable DoD, 10% min SoC reserve, 0.5C/1.0C limits). `OutageEvent` encapsulates normal and typhoon grid failures with solar depression coupling from `[D-11]`. `HourlyRecord` mirrors the exact 18-field canonical interface contract from `docs/context/conceptual-model.md` §4 and provides bidirectional dictionary serialization (`to_dict` / `from_dict`) and local energy balance conservation validation. A comprehensive test suite in `tests/test_core_models.py` verified 100% test pass rate (29/29 tests green across the entire test suite).

---

## 2. Implementation Details

### 2.1 Changes Made

- `src/ccis_sim/core/models.py`:
  - `RoomInventory`: Dataclass capturing the 18-space CCIS layout (2 hyflex smart rooms, 6 lecture rooms, 1 COD office, 1 Dean + Secretary office, 2 faculty offices, 6 computer labs).
  - `Building`: Immutable envelope dataclass with 2,500 m² gross floor area, 1,200 m² usable rooftop area, 2 floors, $T_{\text{base}} = 24.0^\circ\text{C}$, 4%/°C cooling sensitivity, and +20% latent cooling penalty.
  - `SolarArray`: Immutable PV array dataclass parameterized by `capacity_kwp` with $15^\circ$ True South tilt, PR 0.77, tempco -0.40%/°C, NOCT 45°C, and +10°C roof-mount thermal derate.
  - `Battery`: Immutable LFP storage dataclass parameterized by `capacity_kwh` with 92% RTE, 90% usable DoD, 10% minimum SoC reserve, 20% emergency blackout reserve, and 0.5C/1.0C charge/discharge power limits.
  - `OutageType` and `OutageEvent`: Dataclass modeling discrete grid outage events, supporting normal and typhoon events with solar depression factors (20–30% GHI for 3–5 days).
  - `LoadTier`: Enumeration of priority load-shedding tiers (Tier 1: 2%, Tier 2: 18%, Tier 3: 80%).
  - `HourlyRecord`: Verbatim 18-field canonical state record, with `to_dict()`, `from_dict()`, and `is_energy_conserved()` physical invariant checker ($\le 10^{-5}\text{ kWh}$).
- `src/ccis_sim/core/__init__.py`: Exported all domain entities and enumerations.
- `tests/test_core_models.py`: Added 19 comprehensive unit tests covering immutability enforcement, boundary conditions, parameter validation, dict serialization round-tripping, and physical conservation invariants.
- `docs/tasks/status.md`: Updated `CORE-001` and `CORE-001.1`–`CORE-001.4` rows to `done`.

### 2.2 Boundary Design Rationale

- **Equipment Loading Boundary:** In conformance with task guidelines, equipment electrical loading and schedules are not hard-coded in `Building`. `Building` holds static envelope and room layout metadata; `CORE-003` will attach dynamic equipment audit fixtures and operating schedules to this baseline.
- **Dispatch Logic Boundary:** Dispatch logic is strictly excluded from `Battery`. The dataclass specifies only capacity, physical state bounds (`min_soc_kwh`, `max_soc_kwh`), and C-rate power constraints (`max_charge_power_kw`, `max_discharge_power_kw`). The dispatch engine belongs to Phase 2 (`BAT-001`/`BAT-002`).

---

## 3. Verification & Test Evidence

### 3.1 Test Execution

Command executed:
```bash
pytest -v
```

**Results:**
- Tests passed: 29
- Tests failed: 0
- Tests skipped: 0

```text
============================= test session starts ==============================
platform linux -- Python 3.14.7, pytest-9.1.0, pytest-sugar-1.1.1
rootdir: /home/lukexodus/projects/ccis-heat-load-backup-sim
configfile: pyproject.toml
testpaths: tests

 tests/test_core_models.py::test_models_immutability ✓             3% ▍         
 tests/test_core_models.py::test_building_archetype_room_count ✓   7% ▊         
 tests/test_core_models.py::test_building_invalid_parameters ✓    10% █         
 tests/test_core_models.py::test_solar_array_scenario_capacities[0.0] ✓14% █▍        
 tests/test_core_models.py::test_solar_array_scenario_capacities[50.0] ✓17% █▊        
 tests/test_core_models.py::test_solar_array_scenario_capacities[100.0] ✓21% ██▏       
 tests/test_core_models.py::test_solar_array_scenario_capacities[200.0] ✓24% ██▌       
 tests/test_core_models.py::test_solar_array_invalid ✓            28% ██▊       
 tests/test_core_models.py::test_battery_scenario_capacities_and_properties[0.0] ✓31% ███▏      
 tests/test_core_models.py::test_battery_scenario_capacities_and_properties[50.0] ✓34% ███▌      
 tests/test_core_models.py::test_battery_scenario_capacities_and_properties[100.0] ✓38% ███▊      
 tests/test_core_models.py::test_battery_scenario_capacities_and_properties[200.0] ✓41% ████▎     
 tests/test_core_models.py::test_battery_invalid ✓                45% ████▌     
 tests/test_core_models.py::test_outage_event_normal ✓            48% ████▉     
 tests/test_core_models.py::test_outage_event_typhoon ✓           52% █████▎    
 tests/test_core_models.py::test_outage_invalid ✓                 55% █████▌    
 tests/test_core_models.py::test_hourly_record_dict_serialization_roundtrip ✓59% █████▉    
 tests/test_core_models.py::test_hourly_record_energy_conservation_invariant ✓62% ██████▎   
 tests/test_core_models.py::test_hourly_record_validation ✓       66% ██████▋   
 tests/test_smoke.py::test_package_version ✓                      69% ██████▉   
 tests/test_smoke.py::test_submodules_importable[ccis_sim.core] ✓ 72% ███████▎  
 tests/test_smoke.py::test_submodules_importable[ccis_sim.demand] ✓76% ███████▋  
 tests/test_smoke.py::test_submodules_importable[ccis_sim.solar] ✓79% ███████▉  
 tests/test_smoke.py::test_submodules_importable[ccis_sim.battery] ✓83% ████████▍ 
 tests/test_smoke.py::test_submodules_importable[ccis_sim.outage] ✓86% ████████▋ 
 tests/test_smoke.py::test_submodules_importable[ccis_sim.integration] ✓90% █████████ 
 tests/test_smoke.py::test_submodules_importable[ccis_sim.decision] ✓93% █████████▍
 tests/test_smoke.py::test_numpy_environment_sanity ✓             97% █████████▋
 tests/test_smoke.py::test_scipy_environment_sanity ✓            100% ██████████

Results (2.65s):
      29 passed
```

### 3.2 Edge Cases & Negative Testing

- Tested mutability failure (`FrozenInstanceError`) on all dataclasses.
- Tested boundary capacities (0 kWp, 0 kWh) ensuring baseline simulation without solar or battery functions without division-by-zero errors.
- Tested physical energy conservation invariant under exact balance, micro-floating point deviation ($10^{-6}\text{ kWh}$), and intentional imbalance ($2.0\text{ kWh}$ discrepancy detected and rejected).
- Tested range validation on hours ($1 \le h \le 8760$), active load tier ($1, 2, 3$), and parameter ranges (efficiencies, depths of discharge).

---

## 4. Decisions Recorded

No new decision IDs were reserved or required for `CORE-001`. Reserved decision IDs D-12 and D-13 remain unused as all domain parameters and interfaces strictly conform to previously locked decisions `[D-05]` through `[D-11]`.

---

## 5. Unified Git Diff

```diff
diff --git a/src/ccis_sim/core/__init__.py b/src/ccis_sim/core/__init__.py
index 711053f..f752e25 100644
--- a/src/ccis_sim/core/__init__.py
+++ b/src/ccis_sim/core/__init__.py
@@ -1 +1,23 @@
 """Core domain models, interface protocols, and conservation invariants."""
+
+from ccis_sim.core.models import (
+    Battery,
+    Building,
+    HourlyRecord,
+    LoadTier,
+    OutageEvent,
+    OutageType,
+    RoomInventory,
+    SolarArray,
+)
+
+__all__ = [
+    "Battery",
+    "Building",
+    "HourlyRecord",
+    "LoadTier",
+    "OutageEvent",
+    "OutageType",
+    "RoomInventory",
+    "SolarArray",
+]
diff --git a/src/ccis_sim/core/models.py b/src/ccis_sim/core/models.py
new file mode 100644
index 0000000..f6b2839
--- /dev/null
+++ b/src/ccis_sim/core/models.py
@@ -0,0 +1,208 @@
+"""Canonical immutable domain models and interface contracts for CCIS simulation.
+
+Conforms to specifications locked in:
+- docs/context/conceptual-model.md §4
+- docs/decisions/decision-log.md [D-05] through [D-11]
+"""
+
+from __future__ import annotations
+
+from dataclasses import asdict, dataclass, field
+from enum import Enum
+from typing import Any, Mapping
+
+
+class OutageType(str, Enum):
+    """Classification of power outages per decision [D-11]."""
+
+    NORMAL = "normal"
+    TYPHOON = "typhoon"
+
+
+class LoadTier(int, Enum):
+    """Priority load shedding tier per decision [D-10]."""
+
+    TIER_1_CRITICAL = 1   # Life-safety, emergency egress, network headend (2% load)
+    TIER_2_ESSENTIAL = 2  # Faculty rooms, admin, servers/smart rooms (18% load)
+    TIER_3_SHEDDABLE = 3  # Computer labs, comfort HVAC (80% load - shed during blackouts)
+
+
+@dataclass(frozen=True)
+class RoomInventory:
+    """Designated space breakdown for CCIS 2-storey facility per decision [D-06]."""
+
+    hyflex_smart_rooms: int = 2
+    lecture_rooms: int = 6
+    cod_office: int = 1
+    dean_and_secretary: int = 1
+    faculty_rooms: int = 2
+    computer_labs: int = 6
+
+    @property
+    def total_rooms(self) -> int:
+        """Total count of designated spaces in CCIS facility."""
+        return (
+            self.hyflex_smart_rooms
+            + self.lecture_rooms
+            + self.cod_office
+            + self.dean_and_secretary
+            + self.faculty_rooms
+            + self.computer_labs
+        )
+
+
+@dataclass(frozen=True)
+class Building:
+    """Building envelope and architectural baseline for MMSU CCIS per decision [D-06].
+
+    Static building envelope parameters. Equipment electrical loading and schedules
+    are parameterized and loaded separately in CORE-003.
+    """
+
+    name: str = "MMSU College of Computing and Information Sciences"
+    gross_floor_area_m2: float = 2500.0
+    usable_rooftop_area_m2: float = 1200.0
+    floors: int = 2
+    rooms: RoomInventory = field(default_factory=RoomInventory)
+    t_base_cooling_c: float = 24.0           # Balance-point temperature per [D-07]
+    cooling_sensitivity_per_c: float = 0.04  # 4%/°C electrical demand increase per [D-07]
+    latent_cooling_penalty: float = 0.20     # +20% latent cooling penalty per [D-07]
+
+    def __post_init__(self) -> None:
+        if self.gross_floor_area_m2 <= 0:
+            raise ValueError(f"gross_floor_area_m2 must be positive, got {self.gross_floor_area_m2}")
+        if self.usable_rooftop_area_m2 <= 0:
+            raise ValueError(
+                f"usable_rooftop_area_m2 must be positive, got {self.usable_rooftop_area_m2}"
+            )
+        if self.floors <= 0:
+            raise ValueError(f"floors must be positive, got {self.floors}")
+
+
+@dataclass(frozen=True)
+class SolarArray:
+    """Rooftop solar photovoltaic array parameters per decision [D-08].
+
+    Can be instantiated across scenario matrix capacities (0, 50, 100, 200 kWp).
+    """
+
+    capacity_kwp: float
+    tilt_deg: float = 15.0                  # 15° True South per [D-08]
+    azimuth_deg: float = 180.0              # 180° = True South
+    performance_ratio: float = 0.77         # Baseline system PR per [D-08]
+    temp_coeff_pct_per_c: float = -0.40     # -0.40%/°C thermal coefficient per [D-08]
+    noct_c: float = 45.0                    # Nominal Operating Cell Temperature per [D-08]
+    roof_mount_derate_c: float = 10.0       # +10°C thermal penalty for roof mounting per [D-08]
+    t_ref_c: float = 25.0                   # Standard Test Condition reference temperature
+
+    def __post_init__(self) -> None:
+        if self.capacity_kwp < 0.0:
+            raise ValueError(f"capacity_kwp must be non-negative, got {self.capacity_kwp}")
+        if not (0.0 <= self.performance_ratio <= 1.0):
+            raise ValueError(f"performance_ratio must be in [0, 1], got {self.performance_ratio}")
+
+
+@dataclass(frozen=True)
+class Battery:
+    """Lithium Iron Phosphate (LFP) Battery Energy Storage System (BESS) per decision [D-09].
+
+    Can be instantiated across scenario matrix capacities (0, 50, 100, 200 kWh).
+    Static parameters and boundary limits. Dispatch logic is handled in Phase 2 (BAT-001/002).
+    """
+
+    capacity_kwh: float
+    round_trip_efficiency: float = 0.92      # 92% round-trip efficiency per [D-09]
+    usable_dod: float = 0.90                 # 90% usable depth of discharge per [D-09]
+    min_soc_pct: float = 0.10                # 10% minimum SoC reserve per [D-09]
+    max_charge_c_rate: float = 0.5           # 0.5C maximum charging rate per [D-09]
+    max_discharge_c_rate: float = 1.0        # 1.0C maximum continuous discharge per [D-09]
+    emergency_reserve_pct: float = 0.20      # 20% reserved for blackouts per [D-09]
+
+    def __post_init__(self) -> None:
+        if self.capacity_kwh < 0.0:
+            raise ValueError(f"capacity_kwh must be non-negative, got {self.capacity_kwh}")
+        if not (0.0 < self.round_trip_efficiency <= 1.0):
+            raise ValueError(
+                f"round_trip_efficiency must be in (0, 1], got {self.round_trip_efficiency}"
+            )
+        if not (0.0 < self.usable_dod <= 1.0):
+            raise ValueError(f"usable_dod must be in (0, 1], got {self.usable_dod}")
+        if not (0.0 <= self.min_soc_pct < 1.0):
+            raise ValueError(f"min_soc_pct must be in [0, 1), got {self.min_soc_pct}")
+        if self.min_soc_pct + self.usable_dod > 1.0 + 1e-9:
+            raise ValueError(
+                f"min_soc_pct + usable_dod cannot exceed 1.0, got {self.min_soc_pct + self.usable_dod}"
+            )
+
+    @property
+    def min_soc_kwh(self) -> float:
+        """Absolute minimum allowable energy stored in battery (kWh)."""
+        return self.capacity_kwh * self.min_soc_pct
+
+    @property
+    def max_soc_kwh(self) -> float:
+        """Maximum allowable energy stored in battery (kWh)."""
+        return self.capacity_kwh * (self.min_soc_pct + self.usable_dod)
+
+    @property
+    def usable_capacity_kwh(self) -> float:
+        """Total usable energy capacity between min_soc and max_soc (kWh)."""
+        return self.capacity_kwh * self.usable_dod
+
+    @property
+    def emergency_reserve_kwh(self) -> float:
+        """Outage emergency reserve energy buffer (kWh)."""
+        return self.capacity_kwh * self.emergency_reserve_pct
+
+    @property
+    def max_charge_power_kw(self) -> float:
+        """Maximum continuous charging power limit (kW)."""
+        return self.capacity_kwh * self.max_charge_c_rate
+
+    @property
+    def max_discharge_power_kw(self) -> float:
+        """Maximum continuous discharging power limit (kW)."""
+        return self.capacity_kwh * self.max_discharge_c_rate
+
+
+@dataclass(frozen=True)
+class OutageEvent:
+    """Discrete utility grid outage event per decision [D-11]."""
+
+    start_hour: int
+    duration_hours: float
+    outage_type: OutageType = OutageType.NORMAL
+    solar_depression_factor: float = 1.0
+    solar_depression_duration_hours: float = 0.0
+
+    def __post_init__(self) -> None:
+        if self.start_hour < 1 or self.start_hour > 8760:
+            raise ValueError(f"start_hour must be in [1, 8760], got {self.start_hour}")
+        if self.duration_hours <= 0.0:
+            raise ValueError(f"duration_hours must be positive, got {self.duration_hours}")
+        if not (0.0 <= self.solar_depression_factor <= 1.0):
+            raise ValueError(
+                f"solar_depression_factor must be in [0, 1], got {self.solar_depression_factor}"
+            )
+
+    @property
+    def end_hour(self) -> float:
+        """Hour at which grid supply is restored."""
+        return self.start_hour + self.duration_hours
+
+    def is_active_at(self, hour: int) -> bool:
+        """Check whether the grid outage is active at a given chronological hour."""
+        return self.start_hour <= hour < self.end_hour
+
+    def is_solar_depressed_at(self, hour: int) -> bool:
+        """Check whether solar depression is active at a given chronological hour."""
+        depression_end = self.start_hour + self.solar_depression_duration_hours
+        return self.start_hour <= hour < depression_end
+
+
+@dataclass(frozen=True)
+class HourlyRecord:
+    """Canonical time-step record representing the complete state of the CCIS microgrid.
+
+    Fields match docs/context/conceptual-model.md §4 verbatim.
+    """
+
+    hour: int                     # 1 to 8760 (chronological hour of year)
+    timestamp: str                # ISO 8601 string (e.g., "2026-04-15T14:00:00+08:00")
+    temp_ambient_c: float         # Ambient dry-bulb temperature (°C)
+    humidity_rel_pct: float       # Relative humidity (%)
+    ghi_w_m2: float               # Global Horizontal Solar Irradiance (W/m²)
+    demand_gross_kwh: float       # Total unconstrained building electrical load (kWh)
+    demand_served_kwh: float      # Actual electrical load served after load shedding (kWh)
+    solar_generation_kwh: float   # Net AC electrical generation from PV array (kWh)
+    solar_to_demand_kwh: float    # Direct solar electricity consumed by building (kWh)
+    solar_to_battery_kwh: float   # Excess solar electricity routed to battery charging (kWh)
+    solar_curtailed_kwh: float    # Excess generation curtailed or exported to grid (kWh)
+    battery_soc_kwh: float        # Battery usable energy stored at end of hour (kWh)
+    battery_charge_kwh: float     # Energy transferred into battery during this hour (kWh)
+    battery_discharge_kwh: float  # Energy extracted from battery during this hour (kWh)
+    grid_import_kwh: float        # Electrical energy imported from INEC utility grid (kWh)
+    unserved_load_kwh: float      # Deficit electrical energy unserved during blackout (kWh)
+    grid_available: bool          # True = INEC grid UP; False = Outage / Blackout
+    active_load_tier: int         # 1 = Life Safety only, 2 = Essential IT, 3 = Normal (all loads)
+
+    def __post_init__(self) -> None:
+        if self.hour < 1 or self.hour > 8760:
+            raise ValueError(f"hour must be in range 1..8760, got {self.hour}")
+        if self.active_load_tier not in (1, 2, 3):
+            raise ValueError(f"active_load_tier must be 1, 2, or 3, got {self.active_load_tier}")
+
+    @property
+    def energy_balance_residual_kwh(self) -> float:
+        """Calculate physical energy balance residual: |Total Energy In - Total Energy Out|.
+
+        Total In = solar_generation_kwh + grid_import_kwh + battery_discharge_kwh
+        Total Out = demand_served_kwh + battery_charge_kwh + solar_curtailed_kwh
+        """
+        energy_in = self.solar_generation_kwh + self.grid_import_kwh + self.battery_discharge_kwh
+        energy_out = self.demand_served_kwh + self.battery_charge_kwh + self.solar_curtailed_kwh
+        return abs(energy_in - energy_out)
+
+    def is_energy_conserved(self, tolerance: float = 1e-5) -> bool:
+        """Verify strict energy balance invariant (residual <= 10^-5 kWh)."""
+        return self.energy_balance_residual_kwh <= tolerance
+
+    def to_dict(self) -> dict[str, Any]:
+        """Convert record to primitive Python dictionary suitable for JSON/CSV/DataFrame."""
+        return asdict(self)
+
+    @classmethod
+    def from_dict(cls, data: Mapping[str, Any]) -> HourlyRecord:
+        """Construct an HourlyRecord from a dictionary or mapping, with type coercion."""
+        return cls(
+            hour=int(data["hour"]),
+            timestamp=str(data["timestamp"]),
+            temp_ambient_c=float(data["temp_ambient_c"]),
+            humidity_rel_pct=float(data["humidity_rel_pct"]),
+            ghi_w_m2=float(data["ghi_w_m2"]),
+            demand_gross_kwh=float(data["demand_gross_kwh"]),
+            demand_served_kwh=float(data["demand_served_kwh"]),
+            solar_generation_kwh=float(data["solar_generation_kwh"]),
+            solar_to_demand_kwh=float(data["solar_to_demand_kwh"]),
+            solar_to_battery_kwh=float(data["solar_to_battery_kwh"]),
+            solar_curtailed_kwh=float(data["solar_curtailed_kwh"]),
+            battery_soc_kwh=float(data["battery_soc_kwh"]),
+            battery_charge_kwh=float(data["battery_charge_kwh"]),
+            battery_discharge_kwh=float(data["battery_discharge_kwh"]),
+            grid_import_kwh=float(data["grid_import_kwh"]),
+            unserved_load_kwh=float(data["unserved_load_kwh"]),
+            grid_available=bool(data["grid_available"]),
+            active_load_tier=int(data["active_load_tier"]),
+        )
```

---

## 6. Flagged for APC / Operator Attention

- [x] All domain contracts are locked and tested.
- [x] Unblocks `CORE-004` (Energy Conservation Test Harness).
- [ ] Phase 1 companion tasks `CORE-002` (Weather Ingestion) and `CORE-003` (Equipment Audit) can proceed in parallel against these models.
