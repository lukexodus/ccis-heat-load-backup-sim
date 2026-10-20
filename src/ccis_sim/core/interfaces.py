"""Shared interface types and data contracts for Phase 2 parallel sub-models.

Defines canonical dataclasses for demand decomposition, occupancy schedules,
outage scheduling, battery dispatch step results, and tiered load shedding results
per decision [D-26] and docs/context/phase2-interface-contract.md.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Literal

import numpy as np

from ccis_sim.core.models import LoadTier, OutageEvent


@dataclass(frozen=True)
class TieredDemand:
    """Hourly electrical demand decomposed by priority tier per [D-10] and [D-26].

    All tier arrays are 1D numpy float arrays of length N (8,760 for an annual run),
    where index i represents hour i + 1. Units are kWh per hour (= kW at Δt = 1.0 h).
    """

    tier1_kwh: np.ndarray
    tier2_kwh: np.ndarray
    tier3_kwh: np.ndarray

    def __post_init__(self) -> None:
        t1 = np.asarray(self.tier1_kwh, dtype=np.float64)
        t2 = np.asarray(self.tier2_kwh, dtype=np.float64)
        t3 = np.asarray(self.tier3_kwh, dtype=np.float64)

        object.__setattr__(self, "tier1_kwh", t1)
        object.__setattr__(self, "tier2_kwh", t2)
        object.__setattr__(self, "tier3_kwh", t3)

        if not (len(t1) == len(t2) == len(t3)):
            raise ValueError(
                f"Tier array lengths must be equal, got tier1={len(t1)}, tier2={len(t2)}, tier3={len(t3)}"
            )
        if len(t1) == 0:
            raise ValueError("Tier arrays must not be empty.")

        for name, arr in (("tier1_kwh", t1), ("tier2_kwh", t2), ("tier3_kwh", t3)):
            if not np.all(np.isfinite(arr)):
                raise ValueError(f"Array '{name}' contains non-finite values (NaN or inf).")
            if np.any(arr < 0.0):
                raise ValueError(f"Array '{name}' contains negative demand values.")

    @property
    def gross_kwh(self) -> np.ndarray:
        """Total gross demand across all three priority tiers (kWh)."""
        return self.tier1_kwh + self.tier2_kwh + self.tier3_kwh

    def at(self, i: int) -> tuple[float, float, float]:
        """Return (tier1, tier2, tier3) demand in kWh at hour index i."""
        return (float(self.tier1_kwh[i]), float(self.tier2_kwh[i]), float(self.tier3_kwh[i]))

    def __len__(self) -> int:
        return len(self.tier1_kwh)


@dataclass(frozen=True)
class OccupancySchedule:
    """Academic building occupancy profile and calendar operational state.

    All arrays are 1D numpy arrays of length N (8,760 for an annual run).
    occupancy_fraction contains floats in [0.0, 1.0].
    is_class_day, is_break, is_holiday are boolean arrays.
    """

    occupancy_fraction: np.ndarray
    is_class_day: np.ndarray
    is_break: np.ndarray
    is_holiday: np.ndarray

    def __post_init__(self) -> None:
        occ = np.asarray(self.occupancy_fraction, dtype=np.float64)
        cd = np.asarray(self.is_class_day, dtype=bool)
        brk = np.asarray(self.is_break, dtype=bool)
        hol = np.asarray(self.is_holiday, dtype=bool)

        object.__setattr__(self, "occupancy_fraction", occ)
        object.__setattr__(self, "is_class_day", cd)
        object.__setattr__(self, "is_break", brk)
        object.__setattr__(self, "is_holiday", hol)

        if not (len(occ) == len(cd) == len(brk) == len(hol)):
            raise ValueError(
                f"Schedule array lengths must be equal, got occ={len(occ)}, class={len(cd)}, "
                f"break={len(brk)}, holiday={len(hol)}"
            )
        if len(occ) == 0:
            raise ValueError("Schedule arrays must not be empty.")

        if not np.all(np.isfinite(occ)):
            raise ValueError("occupancy_fraction contains non-finite values (NaN or inf).")
        if np.any(occ < 0.0) or np.any(occ > 1.0):
            raise ValueError("occupancy_fraction values must be within [0.0, 1.0].")

    def __len__(self) -> int:
        return len(self.occupancy_fraction)


@dataclass(frozen=True)
class OutageSchedule:
    """Stochastic utility grid outage schedule and typhoon solar depression profile.

    events: Tuple of discrete OutageEvent records occurring within the annual cycle.
    grid_available: Boolean array of length N (True = grid connected, False = blackout).
    year_type: Climate reliability regime ("normal" or "typhoon").
    ghi_multiplier: Solar GHI attenuation factor (defaults to 1.0 for normal days,
        depressed to 0.20–0.30 during multi-day typhoon events per [D-11]).
    """

    events: tuple[OutageEvent, ...]
    grid_available: np.ndarray
    year_type: Literal["normal", "typhoon"]
    ghi_multiplier: np.ndarray | None = None

    def __post_init__(self) -> None:
        ga = np.asarray(self.grid_available, dtype=bool)
        object.__setattr__(self, "grid_available", ga)

        if len(ga) == 0:
            raise ValueError("grid_available array must not be empty.")

        if self.year_type not in ("normal", "typhoon"):
            raise ValueError(f"year_type must be 'normal' or 'typhoon', got '{self.year_type}'")

        if self.ghi_multiplier is None:
            mult = np.ones(len(ga), dtype=np.float64)
        else:
            mult = np.asarray(self.ghi_multiplier, dtype=np.float64)

        object.__setattr__(self, "ghi_multiplier", mult)

        if len(ga) != len(mult):
            raise ValueError(
                f"Length mismatch: grid_available ({len(ga)}) vs ghi_multiplier ({len(mult)})"
            )

        if not np.all(np.isfinite(mult)):
            raise ValueError("ghi_multiplier contains non-finite values (NaN or inf).")
        if np.any(mult < 0.0):
            raise ValueError("ghi_multiplier values must be non-negative.")

    def __len__(self) -> int:
        return len(self.grid_available)


@dataclass(frozen=True)
class BatteryStepResult:
    """Result of a single time-step battery dispatch operation (BAT-001).

    charge_kwh and discharge_kwh are AC-side energy flows achieved at the microgrid bus.
    charge_curtailed_kwh and discharge_unmet_kwh are shortfalls against the dispatch request.
    soc_kwh is the resulting stored chemical state-of-charge.
    """

    soc_kwh: float
    charge_kwh: float
    discharge_kwh: float
    charge_curtailed_kwh: float
    discharge_unmet_kwh: float

    def __post_init__(self) -> None:
        for name, val in (
            ("soc_kwh", self.soc_kwh),
            ("charge_kwh", self.charge_kwh),
            ("discharge_kwh", self.discharge_kwh),
            ("charge_curtailed_kwh", self.charge_curtailed_kwh),
            ("discharge_unmet_kwh", self.discharge_unmet_kwh),
        ):
            if not isinstance(val, (int, float)):
                raise TypeError(f"Field '{name}' must be numeric, got {type(val)}")
            if math.isnan(val) or math.isinf(val):
                raise ValueError(f"Field '{name}' must be finite, got {val}")
            if val < 0.0:
                raise ValueError(f"Field '{name}' must be non-negative, got {val}")

        # Mutual exclusivity: cannot simultaneously charge and discharge
        if self.charge_kwh > 1e-6 and self.discharge_kwh > 1e-6:
            raise ValueError(
                f"Simultaneous charging ({self.charge_kwh:.6f} kWh) and discharging "
                f"({self.discharge_kwh:.6f} kWh) is physically prohibited."
            )


@dataclass(frozen=True)
class ShedResult:
    """Outcome of tiered priority load shedding for a single hour (OUT-002).

    active_tier: Highest active load tier (Tier 1 Critical, Tier 2 Essential, Tier 3 Discretionary).
    served_kwh: 3-tuple of served energy (tier1_served, tier2_served, tier3_served) in kWh.
    unserved_kwh: 3-tuple of unserved energy (tier1_unserved, tier2_unserved, tier3_unserved) in kWh.
    """

    active_tier: LoadTier | int
    served_kwh: tuple[float, float, float]
    unserved_kwh: tuple[float, float, float]

    def __post_init__(self) -> None:
        # Validate tier
        valid_tiers = (
            LoadTier.TIER_1_CRITICAL,
            LoadTier.TIER_2_ESSENTIAL,
            LoadTier.TIER_3_SHEDDABLE,
            1,
            2,
            3,
        )
        if self.active_tier not in valid_tiers:
            raise ValueError(f"active_tier must be a valid LoadTier (1, 2, or 3), got {self.active_tier}")

        # Validate tuples
        for name, tup in (("served_kwh", self.served_kwh), ("unserved_kwh", self.unserved_kwh)):
            if not isinstance(tup, tuple) or len(tup) != 3:
                raise ValueError(f"'{name}' must be a 3-tuple, got {tup}")
            for i, val in enumerate(tup):
                if not isinstance(val, (int, float)):
                    raise TypeError(f"'{name}[{i}]' must be numeric, got {type(val)}")
                if math.isnan(val) or math.isinf(val):
                    raise ValueError(f"'{name}[{i}]' must be finite, got {val}")
                if val < 0.0:
                    raise ValueError(f"'{name}[{i}]' must be non-negative, got {val}")
