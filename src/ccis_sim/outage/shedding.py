"""Priority-based tiered load shedding controller and unserved energy tracker (OUT-002).

Implements deterministic hourly load shedding policies and unserved energy accounting
conforming to:
- docs/context/phase2-interface-contract.md (§3 Manifest, §4.3 Shedding vs Reserve)
- docs/decisions/decision-log.md [D-10] (Priority tiers), [D-16]/[D-19] (Audit figures),
  [D-17] (Emergency reserve separation), [D-34] (Shedding policy & reserve threshold).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Mapping

from ccis_sim.core.interfaces import ShedResult
from ccis_sim.core.models import Battery, LoadTier
from ccis_sim.demand.equipment import EquipmentAudit


def shed_for_hour(
    tier_demand_kwh: tuple[float, float, float],
    *,
    grid_available: bool,
    soc_kwh: float,
    battery: Battery,
    tier2_shed_soc_fraction: float = 0.20,
) -> ShedResult:
    """Evaluate priority-based load shedding for a single simulation hour.

    Operational Policy per [D-10], [D-17], and [D-34]:
    1. Grid Connected (grid_available = True):
       - Normal grid supply is available. All electrical load tiers are fully served.
       - Active policy tier is LoadTier.TIER_3_SHEDDABLE (all tiers served).
       - Served = tier_demand_kwh, Unserved = (0.0, 0.0, 0.0).
    2. Utility Outage / Blackout (grid_available = False):
       - Tier 3 (comfort cooling HVAC, non-essential PC labs, discretionary loads) is
         shed immediately upon grid failure ([D-10]).
       - Tier 2 Shedding Rule:
         If battery State-of-Charge is strictly below `tier2_shed_soc_fraction * capacity_kwh`
         (defaulting to 20% SoC per [D-34]), Tier 2 (faculty rooms, admin, servers/smart rooms)
         is also shed to preserve remaining chemical capacity for Tier 1 life-safety.
         - active_tier = LoadTier.TIER_1_CRITICAL (value 1)
         - Served = (tier1, 0.0, 0.0), Unserved = (0.0, tier2, tier3).
       - If SoC is greater than or equal to the threshold (`soc_kwh >= threshold`):
         Both Tier 1 and Tier 2 are served.
         - active_tier = LoadTier.TIER_2_ESSENTIAL (value 2)
         - Served = (tier1, tier2, 0.0), Unserved = (0.0, 0.0, tier3).

    Conservation Invariant:
        For every tier i in (0, 1, 2):
        served_kwh[i] + unserved_kwh[i] == tier_demand_kwh[i]

    Args:
        tier_demand_kwh: 3-tuple containing hourly electrical demand in kWh for
            (Tier 1 Critical, Tier 2 Essential, Tier 3 Sheddable).
        grid_available: Boolean indicating utility grid energization status (True = normal, False = outage).
        soc_kwh: Current battery usable State-of-Charge at start of hour in kWh.
        battery: Battery specification dataclass defining total storage capacity.
        tier2_shed_soc_fraction: SoC fraction threshold below which Tier 2 loads are shed
            during blackouts ([ASSUMPTION]: defaults to 0.20 per [D-34], independent of
            Battery.emergency_reserve_pct).

    Returns:
        ShedResult containing active_tier, served_kwh 3-tuple, and unserved_kwh 3-tuple.

    Raises:
        TypeError: If tier_demand_kwh is not a tuple or battery is not a Battery instance.
        ValueError: If tier_demand_kwh elements or soc_kwh are negative or non-finite,
            or if tier2_shed_soc_fraction is not in [0.0, 1.0].
    """
    # Input validations
    if not isinstance(tier_demand_kwh, tuple) or len(tier_demand_kwh) != 3:
        raise TypeError(f"tier_demand_kwh must be a 3-tuple, got {type(tier_demand_kwh)}")

    for i, d in enumerate(tier_demand_kwh):
        if not isinstance(d, (int, float)):
            raise TypeError(f"tier_demand_kwh[{i}] must be numeric, got {type(d)}")
        if math.isnan(d) or math.isinf(d):
            raise ValueError(f"tier_demand_kwh[{i}] must be finite, got {d}")
        if d < 0.0:
            raise ValueError(f"tier_demand_kwh[{i}] must be non-negative, got {d}")

    if not isinstance(soc_kwh, (int, float)):
        raise TypeError(f"soc_kwh must be numeric, got {type(soc_kwh)}")
    if math.isnan(soc_kwh) or math.isinf(soc_kwh):
        raise ValueError(f"soc_kwh must be finite, got {soc_kwh}")
    if soc_kwh < 0.0:
        raise ValueError(f"soc_kwh must be non-negative, got {soc_kwh}")

    if not isinstance(tier2_shed_soc_fraction, (int, float)):
        raise TypeError(f"tier2_shed_soc_fraction must be numeric, got {type(tier2_shed_soc_fraction)}")
    if not (0.0 <= tier2_shed_soc_fraction <= 1.0):
        raise ValueError(f"tier2_shed_soc_fraction must be in [0.0, 1.0], got {tier2_shed_soc_fraction}")

    t1, t2, t3 = float(tier_demand_kwh[0]), float(tier_demand_kwh[1]), float(tier_demand_kwh[2])

    if grid_available:
        # [ASSUMPTION]: Grid up -> all tiers served, active tier 3
        return ShedResult(
            active_tier=LoadTier.TIER_3_SHEDDABLE,
            served_kwh=(t1, t2, t3),
            unserved_kwh=(0.0, 0.0, 0.0),
        )

    # Grid Unavailable (Outage / Blackout)
    # [ASSUMPTION]: Tier 3 shed immediately upon utility failure
    tier2_threshold_kwh = tier2_shed_soc_fraction * battery.capacity_kwh

    if soc_kwh < tier2_threshold_kwh:
        # [ASSUMPTION]: Deep discharge protection: below 20% SoC, shed Tier 2 to preserve Tier 1
        return ShedResult(
            active_tier=LoadTier.TIER_1_CRITICAL,
            served_kwh=(t1, 0.0, 0.0),
            unserved_kwh=(0.0, t2, t3),
        )

    # SoC is at or above the Tier 2 shedding threshold: Tier 1 and Tier 2 served
    return ShedResult(
        active_tier=LoadTier.TIER_2_ESSENTIAL,
        served_kwh=(t1, t2, 0.0),
        unserved_kwh=(0.0, 0.0, t3),
    )


@dataclass(frozen=True)
class TierAuditComparison:
    """Summary of audited equipment inventory load distribution compared to D-10 nominal targets."""

    total_connected_kw: float
    tier1_connected_kw: float
    tier2_connected_kw: float
    tier3_connected_kw: float
    tier1_connected_pct: float
    tier2_connected_pct: float
    tier3_connected_pct: float
    nominal_tier1_pct: float = 2.0
    nominal_tier2_pct: float = 18.0
    nominal_tier3_pct: float = 80.0

    @property
    def tier1_delta_pct(self) -> float:
        """Difference between audited connected percentage and nominal D-10 target (percentage points)."""
        return self.tier1_connected_pct - self.nominal_tier1_pct

    @property
    def tier2_delta_pct(self) -> float:
        """Difference between audited connected percentage and nominal D-10 target (percentage points)."""
        return self.tier2_connected_pct - self.nominal_tier2_pct

    @property
    def tier3_delta_pct(self) -> float:
        """Difference between audited connected percentage and nominal D-10 target (percentage points)."""
        return self.tier3_connected_pct - self.nominal_tier3_pct

    def as_dict(self) -> dict[str, float]:
        """Convert comparison metrics to dictionary representation."""
        return {
            "total_connected_kw": round(self.total_connected_kw, 4),
            "tier1_connected_kw": round(self.tier1_connected_kw, 4),
            "tier2_connected_kw": round(self.tier2_connected_kw, 4),
            "tier3_connected_kw": round(self.tier3_connected_kw, 4),
            "tier1_connected_pct": round(self.tier1_connected_pct, 4),
            "tier2_connected_pct": round(self.tier2_connected_pct, 4),
            "tier3_connected_pct": round(self.tier3_connected_pct, 4),
            "nominal_tier1_pct": self.nominal_tier1_pct,
            "nominal_tier2_pct": self.nominal_tier2_pct,
            "nominal_tier3_pct": self.nominal_tier3_pct,
            "tier1_delta_pct": round(self.tier1_delta_pct, 4),
            "tier2_delta_pct": round(self.tier2_delta_pct, 4),
            "tier3_delta_pct": round(self.tier3_delta_pct, 4),
        }


def compute_tier_audit_shares(audit: EquipmentAudit) -> TierAuditComparison:
    """Compute tier shares of connected electrical capacity from equipment audit inventory (OUT-002.1).

    Compares the audited nameplate capacity against the nominal 2/18/80 split established in [D-10].
    Per [D-16], [D-19], and [D-34], the audit yields:
    - Total: 147.805 kW (~147.81 kW)
    - Tier 1: 1.215 kW (~0.82% connected, ~1.5% daytime peak)
    - Tier 2: 15.360 kW (~10.39% connected, ~17.0% daytime peak)
    - Tier 3: 131.230 kW (~88.79% connected, ~81.5% daytime peak)

    The discrepancy between connected shares and nominal targets is reported without forcing artificial scaling.

    Args:
        audit: Loaded EquipmentAudit instance containing facility electrical equipment list.

    Returns:
        TierAuditComparison dataclass containing exact connected capacities and percentage deltas.
    """
    t1_kw = audit.total_connected_kw(1)
    t2_kw = audit.total_connected_kw(2)
    t3_kw = audit.total_connected_kw(3)
    total_kw = audit.total_connected_kw()

    if total_kw <= 0.0:
        t1_pct = t2_pct = t3_pct = 0.0
    else:
        t1_pct = (t1_kw / total_kw) * 100.0
        t2_pct = (t2_kw / total_kw) * 100.0
        t3_pct = (t3_kw / total_kw) * 100.0

    return TierAuditComparison(
        total_connected_kw=total_kw,
        tier1_connected_kw=t1_kw,
        tier2_connected_kw=t2_kw,
        tier3_connected_kw=t3_kw,
        tier1_connected_pct=t1_pct,
        tier2_connected_pct=t2_pct,
        tier3_connected_pct=t3_pct,
    )


@dataclass
class UnservedTracker:
    """State tracker accumulating per-tier unserved electrical energy and outage metrics (OUT-002.4).

    Tracks cumulative unserved energy and evaluates whether physical delivery shortfalls
    occurred during outages. If battery discharge falls short of policy served demand,
    the shortfall is allocated strictly in reverse-priority order (lowest-priority
    active tier first).

    Attributes:
        total_hours: Total simulation timesteps recorded.
        total_outage_hours: Number of hours where grid_available was False.
        outage_hours_tier1_served: Number of outage hours where Tier 1 was 100% served.
        outage_hours_tier2_served: Number of outage hours where Tier 2 was 100% served.
        outage_hours_tier3_served: Number of outage hours where Tier 3 was 100% served.
        unserved_tier1_kwh: Cumulative unserved energy for Tier 1 Critical load (kWh).
        unserved_tier2_kwh: Cumulative unserved energy for Tier 2 Essential load (kWh).
        unserved_tier3_kwh: Cumulative unserved energy for Tier 3 Sheddable load (kWh).
        served_tier1_kwh: Cumulative served energy for Tier 1 Critical load (kWh).
        served_tier2_kwh: Cumulative served energy for Tier 2 Essential load (kWh).
        served_tier3_kwh: Cumulative served energy for Tier 3 Sheddable load (kWh).
    """

    total_hours: int = 0
    total_outage_hours: int = 0
    outage_hours_tier1_served: int = 0
    outage_hours_tier2_served: int = 0
    outage_hours_tier3_served: int = 0
    unserved_tier1_kwh: float = 0.0
    unserved_tier2_kwh: float = 0.0
    unserved_tier3_kwh: float = 0.0
    served_tier1_kwh: float = 0.0
    served_tier2_kwh: float = 0.0
    served_tier3_kwh: float = 0.0

    @property
    def total_unserved_kwh(self) -> float:
        """Total cumulative unserved electrical energy across all tiers (kWh)."""
        return self.unserved_tier1_kwh + self.unserved_tier2_kwh + self.unserved_tier3_kwh

    @property
    def total_served_kwh(self) -> float:
        """Total cumulative served electrical energy across all tiers (kWh)."""
        return self.served_tier1_kwh + self.served_tier2_kwh + self.served_tier3_kwh

    @property
    def outage_hours_tier1_served_pct(self) -> float:
        """Percentage of outage hours where Tier 1 was fully served (0.0 to 100.0%)."""
        if self.total_outage_hours == 0:
            return 100.0
        return (self.outage_hours_tier1_served / self.total_outage_hours) * 100.0

    @property
    def outage_hours_tier2_served_pct(self) -> float:
        """Percentage of outage hours where Tier 2 was fully served (0.0 to 100.0%)."""
        if self.total_outage_hours == 0:
            return 100.0
        return (self.outage_hours_tier2_served / self.total_outage_hours) * 100.0

    @property
    def outage_hours_tier3_served_pct(self) -> float:
        """Percentage of outage hours where Tier 3 was fully served (0.0 to 100.0%)."""
        if self.total_outage_hours == 0:
            return 100.0
        return (self.outage_hours_tier3_served / self.total_outage_hours) * 100.0

    def record(
        self,
        result: ShedResult,
        *,
        grid_available: bool,
        battery_shortfall_kwh: float = 0.0,
    ) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
        """Record hourly load shedding outcome and account for physical battery delivery shortfall.

        Shortfall Allocation Principle [D-34]:
        When the microgrid battery cannot physically deliver the full policy-served demand
        (`battery_shortfall_kwh > 0.0`), the shortfall cuts into served energy starting with
        the lowest-priority active tier:
        1. Tier 3 served is cut first until reduced to 0.0.
        2. Any remaining shortfall cuts into Tier 2 served until reduced to 0.0.
        3. Any remaining shortfall cuts into Tier 1 served.

        Energy conservation is strictly maintained:
        actual_served[i] + actual_unserved[i] == result.served_kwh[i] + result.unserved_kwh[i].

        Args:
            result: ShedResult returned by `shed_for_hour`.
            grid_available: Utility grid availability status.
            battery_shortfall_kwh: Unmet discharge energy in kWh where requested battery power
                could not be supplied due to power/energy exhaustion (non-negative).

        Returns:
            A tuple of (actual_served_kwh, actual_unserved_kwh) 3-tuples for the hour.

        Raises:
            ValueError: If battery_shortfall_kwh is negative or non-finite.
        """
        if not isinstance(battery_shortfall_kwh, (int, float)):
            raise TypeError(f"battery_shortfall_kwh must be numeric, got {type(battery_shortfall_kwh)}")
        if math.isnan(battery_shortfall_kwh) or math.isinf(battery_shortfall_kwh):
            raise ValueError(f"battery_shortfall_kwh must be finite, got {battery_shortfall_kwh}")
        if battery_shortfall_kwh < 0.0:
            raise ValueError(f"battery_shortfall_kwh must be non-negative, got {battery_shortfall_kwh}")

        s1, s2, s3 = result.served_kwh
        u1, u2, u3 = result.unserved_kwh

        # Reverse priority shortfall allocation: Tier 3 -> Tier 2 -> Tier 1
        rem = float(battery_shortfall_kwh)

        cut3 = min(s3, rem)
        rem -= cut3

        cut2 = min(s2, rem)
        rem -= cut2

        cut1 = min(s1, rem)
        rem -= cut1

        # Effective actual flows
        act_s1 = s1 - cut1
        act_s2 = s2 - cut2
        act_s3 = s3 - cut3

        act_u1 = u1 + cut1
        act_u2 = u2 + cut2
        act_u3 = u3 + cut3

        # Accumulate metrics
        self.unserved_tier1_kwh += act_u1
        self.unserved_tier2_kwh += act_u2
        self.unserved_tier3_kwh += act_u3

        self.served_tier1_kwh += act_s1
        self.served_tier2_kwh += act_s2
        self.served_tier3_kwh += act_s3

        self.total_hours += 1

        if not grid_available:
            self.total_outage_hours += 1

            # A tier is fully served in an outage hour if actual unserved energy is zero
            if act_u1 <= 1e-6:
                self.outage_hours_tier1_served += 1
            if act_u2 <= 1e-6:
                self.outage_hours_tier2_served += 1
            if act_u3 <= 1e-6:
                self.outage_hours_tier3_served += 1

        return (act_s1, act_s2, act_s3), (act_u1, act_u2, act_u3)

    def summary(self) -> dict[str, Any]:
        """Produce a comprehensive dictionary of unserved load statistics and outage resilience."""
        return {
            "total_hours": self.total_hours,
            "total_outage_hours": self.total_outage_hours,
            "outage_hours_tier1_served": self.outage_hours_tier1_served,
            "outage_hours_tier2_served": self.outage_hours_tier2_served,
            "outage_hours_tier3_served": self.outage_hours_tier3_served,
            "outage_hours_tier1_served_pct": round(self.outage_hours_tier1_served_pct, 2),
            "outage_hours_tier2_served_pct": round(self.outage_hours_tier2_served_pct, 2),
            "outage_hours_tier3_served_pct": round(self.outage_hours_tier3_served_pct, 2),
            "unserved_tier1_kwh": round(self.unserved_tier1_kwh, 6),
            "unserved_tier2_kwh": round(self.unserved_tier2_kwh, 6),
            "unserved_tier3_kwh": round(self.unserved_tier3_kwh, 6),
            "total_unserved_kwh": round(self.total_unserved_kwh, 6),
            "served_tier1_kwh": round(self.served_tier1_kwh, 6),
            "served_tier2_kwh": round(self.served_tier2_kwh, 6),
            "served_tier3_kwh": round(self.served_tier3_kwh, 6),
            "total_served_kwh": round(self.total_served_kwh, 6),
        }

    def reset(self) -> None:
        """Reset all accumulator variables to zero."""
        self.total_hours = 0
        self.total_outage_hours = 0
        self.outage_hours_tier1_served = 0
        self.outage_hours_tier2_served = 0
        self.outage_hours_tier3_served = 0
        self.unserved_tier1_kwh = 0.0
        self.unserved_tier2_kwh = 0.0
        self.unserved_tier3_kwh = 0.0
        self.served_tier1_kwh = 0.0
        self.served_tier2_kwh = 0.0
        self.served_tier3_kwh = 0.0
