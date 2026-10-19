"""Equipment audit domain model and inventory parser for CCIS simulation.

Conforms to specifications locked in:
- docs/prompts/CORE-003-PROMPT.md
- docs/decisions/decision-log.md [D-06] (18 rooms layout), [D-10] (Tiers 1, 2, 3)
- docs/decisions/decision-log.md [D-16] (Equipment audit inventory and load assumptions)
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

import pandas as pd


@dataclass(frozen=True)
class EquipmentItem:
    """Individual electrical equipment item entry in the building audit.

    Attributes:
        item: Descriptive name of the electrical equipment.
        room_type: Room archetype category (e.g., 'computer_lab', 'lecture_room',
            'hyflex_smart_room', 'dean_and_secretary', 'cod_office', 'faculty_room',
            'building_common').
        count: Total physical count across all rooms of room_type.
        rated_kw: Rated active electrical power per single unit in kW.
        hours_per_day: Nominal operating hours per weekday (0.0 to 24.0).
        tier: Critical priority load shedding tier per [D-10] (1, 2, or 3).
        duty_cycle: Operating diversity factor / duty cycle during active hours (0.0 to 1.0).
        notes: Audit notes, assumption citations, or standard specifications.
    """

    item: str
    room_type: str
    count: int
    rated_kw: float
    hours_per_day: float
    tier: int
    duty_cycle: float = 1.0
    notes: str = ""

    def __post_init__(self) -> None:
        if self.count <= 0:
            raise ValueError(f"count must be a positive integer, got {self.count}")
        if self.rated_kw < 0.0:
            raise ValueError(f"rated_kw must be non-negative, got {self.rated_kw}")
        if not (0.0 <= self.hours_per_day <= 24.0):
            raise ValueError(f"hours_per_day must be in [0, 24], got {self.hours_per_day}")
        if self.tier not in (1, 2, 3):
            raise ValueError(f"tier must be 1, 2, or 3 per [D-10], got {self.tier}")
        if not (0.0 <= self.duty_cycle <= 1.0):
            raise ValueError(f"duty_cycle must be in [0.0, 1.0], got {self.duty_cycle}")

    @property
    def total_kw(self) -> float:
        """Total nameplate connected electrical capacity for this equipment item (kW)."""
        return self.count * self.rated_kw

    @property
    def nominal_daily_kwh(self) -> float:
        """Nominal daily electrical energy consumption without duty cycle derating (kWh/day)."""
        return self.total_kw * self.hours_per_day

    @property
    def effective_daily_kwh(self) -> float:
        """Effective daily electrical energy consumption accounting for duty cycle (kWh/day)."""
        return self.total_kw * self.hours_per_day * self.duty_cycle

    @property
    def is_cooling(self) -> bool:
        """Determine whether the equipment contributes to sensible/latent cooling load."""
        item_lower = self.item.lower()
        return "ac unit" in item_lower or "split ac" in item_lower or "spot cooling" in item_lower


@dataclass
class EquipmentAudit:
    """Comprehensive building equipment audit inventory.

    Attributes:
        items: List of EquipmentItem records.
        floor_area_m2: Gross floor area of facility in square meters (default 2500.0 m² per [D-06]).
        building_name: Name of facility.
    """

    items: list[EquipmentItem] = field(default_factory=list)
    floor_area_m2: float = 2500.0
    building_name: str = "MMSU College of Computing and Information Sciences"

    def __post_init__(self) -> None:
        if self.floor_area_m2 <= 0.0:
            raise ValueError(f"floor_area_m2 must be positive, got {self.floor_area_m2}")

    def add_item(self, item: EquipmentItem) -> None:
        """Add an equipment item to the audit inventory."""
        self.items.append(item)

    @classmethod
    def load_from_csv(
        cls,
        csv_path: Path | str,
        floor_area_m2: float = 2500.0,
        building_name: str = "MMSU College of Computing and Information Sciences",
    ) -> EquipmentAudit:
        """Load and parse an equipment audit CSV fixture.

        Expected minimum columns: item, room_type, count, rated_kw, hours_per_day, tier.
        Optional columns: duty_cycle, notes.
        """
        path = Path(csv_path)
        if not path.exists():
            raise FileNotFoundError(f"Equipment audit fixture file not found: {path}")

        audit = cls(floor_area_m2=floor_area_m2, building_name=building_name)

        with open(path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            required_cols = {"item", "room_type", "count", "rated_kw", "hours_per_day", "tier"}
            if not reader.fieldnames or not required_cols.issubset(set(reader.fieldnames)):
                raise ValueError(
                    f"CSV missing required columns: {required_cols - set(reader.fieldnames or [])}"
                )

            for row in reader:
                item = EquipmentItem(
                    item=row["item"].strip(),
                    room_type=row["room_type"].strip(),
                    count=int(row["count"]),
                    rated_kw=float(row["rated_kw"]),
                    hours_per_day=float(row["hours_per_day"]),
                    tier=int(row["tier"]),
                    duty_cycle=float(row.get("duty_cycle", 1.0) or 1.0),
                    notes=row.get("notes", "").strip(),
                )
                audit.add_item(item)

        return audit

    def total_connected_kw(self, tier: int | None = None) -> float:
        """Calculate total connected electrical power capacity (kW), optionally filtered by tier."""
        if tier is not None:
            return sum(item.total_kw for item in self.items if item.tier == tier)
        return sum(item.total_kw for item in self.items)

    def total_nominal_daily_kwh(self, tier: int | None = None) -> float:
        """Calculate total nominal daily energy consumption (kWh/day), optionally filtered by tier."""
        if tier is not None:
            return sum(item.nominal_daily_kwh for item in self.items if item.tier == tier)
        return sum(item.nominal_daily_kwh for item in self.items)

    def total_effective_daily_kwh(self, tier: int | None = None) -> float:
        """Calculate total effective daily energy consumption (kWh/day), optionally filtered by tier."""
        if tier is not None:
            return sum(item.effective_daily_kwh for item in self.items if item.tier == tier)
        return sum(item.effective_daily_kwh for item in self.items)

    def tier_breakdown_kw(self) -> dict[int, float]:
        """Return connected power in kW broken down by tier {1: kW, 2: kW, 3: kW}."""
        return {
            1: self.total_connected_kw(tier=1),
            2: self.total_connected_kw(tier=2),
            3: self.total_connected_kw(tier=3),
        }

    def tier_breakdown_pct(self) -> dict[int, float]:
        """Return percentage of connected power broken down by tier."""
        total = self.total_connected_kw()
        if total == 0.0:
            return {1: 0.0, 2: 0.0, 3: 0.0}
        return {t: (kw / total) * 100.0 for t, kw in self.tier_breakdown_kw().items()}

    def by_room_type(self, room_type: str) -> list[EquipmentItem]:
        """Filter audit items belonging to a specific room archetype."""
        return [item for item in self.items if item.room_type == room_type]

    def summary_by_room_type(self) -> dict[str, dict[str, float]]:
        """Return aggregated summary metrics by room archetype."""
        summary: dict[str, dict[str, float]] = {}
        for item in self.items:
            if item.room_type not in summary:
                summary[item.room_type] = {
                    "total_kw": 0.0,
                    "nominal_daily_kwh": 0.0,
                    "effective_daily_kwh": 0.0,
                    "unit_count": 0.0,
                }
            summary[item.room_type]["total_kw"] += item.total_kw
            summary[item.room_type]["nominal_daily_kwh"] += item.nominal_daily_kwh
            summary[item.room_type]["effective_daily_kwh"] += item.effective_daily_kwh
            summary[item.room_type]["unit_count"] += item.count
        return summary

    def to_dataframe(self) -> pd.DataFrame:
        """Convert equipment audit records to a pandas DataFrame."""
        records = [
            {
                "item": item.item,
                "room_type": item.room_type,
                "count": item.count,
                "rated_kw": item.rated_kw,
                "hours_per_day": item.hours_per_day,
                "tier": item.tier,
                "duty_cycle": item.duty_cycle,
                "total_kw": item.total_kw,
                "nominal_daily_kwh": item.nominal_daily_kwh,
                "effective_daily_kwh": item.effective_daily_kwh,
                "is_cooling": item.is_cooling,
                "notes": item.notes,
            }
            for item in self.items
        ]
        return pd.DataFrame(records)

    def validate(self) -> list[str]:
        """Validate inventory consistency against architectural baselines.

        Returns a list of validation warning/error strings (empty if valid).
        """
        errors = []
        if not self.items:
            errors.append("Equipment audit contains no items.")
            return errors

        # Check room types present
        room_types = {item.room_type for item in self.items}
        expected_archetypes = {
            "computer_lab",
            "lecture_room",
            "hyflex_smart_room",
            "dean_and_secretary",
            "cod_office",
            "faculty_room",
        }
        missing = expected_archetypes - room_types
        if missing:
            errors.append(f"Missing expected 18-room archetypes from [D-06]: {missing}")

        # Check total connected power is positive
        if self.total_connected_kw() <= 0.0:
            errors.append("Total connected load must be positive.")

        # Check tier distribution
        pcts = self.tier_breakdown_pct()
        if pcts.get(1, 0.0) <= 0.0:
            errors.append("Tier 1 life safety load must be greater than 0%.")

        return errors
