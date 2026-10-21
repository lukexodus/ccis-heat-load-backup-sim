"""Diurnal non-cooling electrical demand model for CCIS facility.

Aggregates bottom-up lighting, IT networking, office computing, and plug loads
across priority tiers 1 to 3 based on the equipment inventory audit and hourly
occupancy schedules, conforming to:
- docs/prompts/DEM-001-PROMPT.md
- docs/context/phase2-interface-contract.md
- docs/decisions/decision-log.md [D-27]
"""

from __future__ import annotations

import numpy as np

from ccis_sim.core.interfaces import OccupancySchedule, TieredDemand
from ccis_sim.core.models import Building
from ccis_sim.demand.equipment import EquipmentAudit


def compute_non_cooling_demand(
    schedule: OccupancySchedule,
    audit: EquipmentAudit,
    building: Building,
) -> TieredDemand:
    r"""Compute hourly non-cooling electrical demand decomposed across priority tiers 1 to 3.

    Conforms strictly to docs/context/phase2-interface-contract.md:
    `compute_non_cooling_demand(schedule: OccupancySchedule, audit: EquipmentAudit, building: Building) -> TieredDemand`

    Load aggregation logic ([ASSUMPTION / [D-27]]):
    1. Filter out all cooling equipment (`item.is_cooling == False`); cooling response is
       exclusively evaluated in DEM-002.
    2. Classify items into:
       - Continuous 24/7 loads (`hours_per_day >= 24.0`): constant uninterrupted operation
         (e.g., Tier 1 life-safety signs/alarms/CCTV/stairwell; Tier 2 IDF switches and core routers).
       - Occupancy-driven loads (`hours_per_day < 24.0`): scaled linearly with hourly
         `occupancy_fraction` (e.g., PC labs, classroom lighting troffers, faculty workstations).
    3. Calculate total daytime peak non-cooling demand:
       $P_{\text{peak}} = P_{\text{cont, total}} + P_{\text{occ\_peak, total}}$.
    4. Unoccupied Baseload Rule without Double-Counting:
       Target unoccupied non-cooling load is 10% of daytime peak ($0.10 \times P_{\text{peak}}$).
       Continuous 24/7 items already draw $P_{\text{cont, total}}$. The residual standby margin:
       $P_{\text{standby}} = \max(0.0, 0.10 \times P_{\text{peak}} - P_{\text{cont, total}})$.
       This residual represents parasitic standby plug loads (quiescent draw of sleep-state PCs,
       monitors, chargers, and appliances) and is allocated to Tier 3 (sheddable load).
       As occupancy rises ($f \in [0, 1]$), equipment wakes to operational load, and standby
       transitions to active draw: $(1.0 - f) \times P_{\text{standby}}$.
    5. Hourly Tier Composition:
       - Tier 1: $P_{\text{cont}, 1} + f \times P_{\text{occ\_peak}, 1}$
       - Tier 2: $P_{\text{cont}, 2} + f \times P_{\text{occ\_peak}, 2}$
       - Tier 3: $P_{\text{cont}, 3} + f \times P_{\text{occ\_peak}, 3} + (1.0 - f) \times P_{\text{standby}}$

    Args:
        schedule: OccupancySchedule containing hourly occupancy_fraction array.
        audit: EquipmentAudit inventory containing audited building loads.
        building: Building envelope definition.

    Returns:
        TieredDemand instance with tier1_kwh, tier2_kwh, tier3_kwh arrays of length N.
    """
    n = len(schedule)
    if n == 0:
        raise ValueError("OccupancySchedule must not be empty.")

    # Filter for non-cooling electrical equipment
    non_cooling_items = [item for item in audit.items if not item.is_cooling]

    # Pre-accumulate continuous loads and full-occupancy peak loads per tier
    # Units: kW = kWh/h at Δt = 1.0 h
    p_cont = {1: 0.0, 2: 0.0, 3: 0.0}
    p_occ_peak = {1: 0.0, 2: 0.0, 3: 0.0}

    for item in non_cooling_items:
        # Effective kW accounts for duty cycle diversity during operational hours
        effective_kw = item.count * item.rated_kw * item.duty_cycle
        if item.hours_per_day >= 24.0:
            p_cont[item.tier] += effective_kw
        else:
            p_occ_peak[item.tier] += effective_kw

    p_cont_total = p_cont[1] + p_cont[2] + p_cont[3]
    p_occ_total = p_occ_peak[1] + p_occ_peak[2] + p_occ_peak[3]
    p_peak = p_cont_total + p_occ_total

    # Baseload target is 10% of daytime peak non-cooling demand per DEM-001.3
    p_unoccupied_target = 0.10 * p_peak

    # Avoid double-counting: subtract continuous 24/7 loads from 10% baseload target
    p_standby_residual = max(0.0, p_unoccupied_target - p_cont_total)

    f_occ = schedule.occupancy_fraction

    # Vectorized hourly tier load generation
    tier1_arr = np.full(n, p_cont[1], dtype=np.float64)
    if p_occ_peak[1] > 0.0:
        tier1_arr += f_occ * p_occ_peak[1]

    tier2_arr = p_cont[2] + f_occ * p_occ_peak[2]
    tier3_arr = p_cont[3] + f_occ * p_occ_peak[3] + (1.0 - f_occ) * p_standby_residual

    return TieredDemand(
        tier1_kwh=tier1_arr,
        tier2_kwh=tier2_arr,
        tier3_kwh=tier3_arr,
    )
