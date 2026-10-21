"""Temperature and humidity sensitive AC cooling demand model.

Implements the Cooling Degree Day (CDD) sensible response, tropical latent humidity
penalty, inverter modulation bounds, and capacity caps conforming to:
- docs/prompts/DEM-002-PROMPT.md
- docs/context/phase2-interface-contract.md
- docs/decisions/decision-log.md [D-07], [D-10], [D-16], [D-28]
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ccis_sim.core.interfaces import TieredDemand
from ccis_sim.core.models import Building
from ccis_sim.demand.equipment import EquipmentAudit


def compute_cooling_demand(
    weather_df: pd.DataFrame,
    occupancy_fraction: np.ndarray,
    audit: EquipmentAudit,
    building: Building,
    *,
    rh_low: float = 60.0,
    rh_high: float = 80.0,
) -> TieredDemand:
    r"""Compute hourly cooling electrical demand decomposed across priority tiers 1 to 3.

    Conforms strictly to docs/context/phase2-interface-contract.md:
    `compute_cooling_demand(weather_df: pd.DataFrame, occupancy_fraction: np.ndarray, audit: EquipmentAudit, building: Building) -> TieredDemand`

    Cooling model formulation ([ASSUMPTION / [D-28]]):
    1. Sensible Cooling Response ([D-07]):
       Sensible temperature delta above balance-point setpoint:
       $\Delta T_i = \max(0.0, T_{\text{amb}, i} - T_{\text{base}})$, where $T_{\text{base}} = \text{building.t\_base\_cooling\_c} = 24.0^\circ\text{C}$.
       Relative sensitivity: $s_T = \text{building.cooling\_sensitivity\_per\_c} = 0.04$ ($4.0\%/^\circ\text{C}$).
       At or below $T_{\text{base}}$, sensible cooling demand is identically zero.
    2. Tropical Latent Humidity Penalty ([D-07]):
       At tropical high humidity, coil moisture condensation increases enthalpy load:
       $M_{\text{latent}}(RH) = 1.0 + \text{building.latent\_cooling\_penalty} \times \text{clip}\left(\frac{RH - RH_{\text{low}}}{RH_{\text{high}} - RH_{\text{low}}}, 0.0, 1.0\right)$.
       Below $RH_{\text{low}} = 60.0\%$, $M_{\text{latent}} = 1.00$. Above $RH_{\text{high}} = 80.0\%$, $M_{\text{latent}} = 1.20$ (+20% penalty).
       Between 60% and 80%, penalty ramps linearly, avoiding unphysical step discontinuities.
    3. Operational Categories and Tier Allocation ([D-10], [D-16]):
       - Tier 2 Spot Cooling (IDF / telecommunications closets):
         Runs 24/7 uninterrupted ($hours = 24.0$) to dissipate continuous heat from PoE switches
         and routers. Independent of human occupancy ($f_{\text{occ}}$):
         $P_{\text{spot}, i} = \min\left(P_{\text{conn, spot}}, P_{\text{conn, spot}} \times s_T \Delta T_i \times M_{\text{latent}}(RH_i)\right)$.
       - Tier 3 Comfort Cooling (Classrooms, PC labs, faculty/admin offices):
         Operates only when rooms are occupied ($f_{\text{occ}} > 0$). When unoccupied ($f_{\text{occ}} = 0$),
         comfort AC units are turned off:
         $P_{\text{comfort}, i} = \min\left(f_{\text{occ}, i} \times P_{\text{conn, comfort}}, f_{\text{occ}, i} \times P_{\text{conn, comfort}} \times s_T \Delta T_i \times M_{\text{latent}}(RH_i)\right)$.
       - Tier 1 Life-Safety:
         Zero cooling equipment is assigned to Tier 1 in the building audit ($P_{\text{Tier 1}} = 0.0$).
    4. Capacity Cap and Modulation Floor:
       Cooling electrical demand is hard-capped at connected cooling capacity per tier.
       Inverter compressors modulate continuously; cycling at minimum speed over the 1-hour interval
       yields smooth energy integration proportional to required thermal load.

    Args:
        weather_df: DataFrame containing 't_amb' (°C) and 'rh' (%) time series.
        occupancy_fraction: 1D numpy array of length N containing float values in [0.0, 1.0].
        audit: EquipmentAudit inventory containing audited equipment items.
        building: Building envelope providing t_base_cooling_c, cooling_sensitivity_per_c,
            and latent_cooling_penalty.
        rh_low: Lower relative humidity threshold for latent penalty ramp (default 60.0%).
        rh_high: Upper relative humidity threshold for full latent penalty (default 80.0%).

    Returns:
        TieredDemand instance containing tier1_kwh, tier2_kwh, and tier3_kwh arrays of length N.
    """
    n = len(weather_df)
    occ = np.asarray(occupancy_fraction, dtype=np.float64)
    if len(occ) != n:
        raise ValueError(
            f"occupancy_fraction length ({len(occ)}) must match weather_df length ({n})."
        )
    if n == 0:
        raise ValueError("weather_df must not be empty.")

    if "t_amb" not in weather_df.columns or "rh" not in weather_df.columns:
        raise ValueError("weather_df must contain 't_amb' and 'rh' columns.")

    t_amb = weather_df["t_amb"].to_numpy(dtype=np.float64)
    rh = weather_df["rh"].to_numpy(dtype=np.float64)

    # 1. Delta-T above base temperature
    dt = np.maximum(0.0, t_amb - building.t_base_cooling_c)

    # 2. Continuous piecewise-linear latent humidity multiplier
    rh_norm = np.clip((rh - rh_low) / (rh_high - rh_low), 0.0, 1.0)
    m_latent = 1.0 + building.latent_cooling_penalty * rh_norm

    # 3. Disaggregate cooling equipment from audit by tier and operational schedule
    cooling_items = [it for it in audit.items if it.is_cooling]

    # Pre-accumulate connected capacity for spot cooling (24/7) vs comfort cooling per tier
    # Spot cooling: hours_per_day >= 24.0; Comfort cooling: hours_per_day < 24.0
    p_conn_spot = {1: 0.0, 2: 0.0, 3: 0.0}
    p_conn_comfort = {1: 0.0, 2: 0.0, 3: 0.0}

    for item in cooling_items:
        conn_kw = item.count * item.rated_kw
        if item.hours_per_day >= 24.0:
            p_conn_spot[item.tier] += conn_kw
        else:
            p_conn_comfort[item.tier] += conn_kw

    s_t = building.cooling_sensitivity_per_c

    # Vectorized hourly cooling calculation per tier
    tier_arrays: dict[int, np.ndarray] = {}
    for tier in (1, 2, 3):
        tier_arr = np.zeros(n, dtype=np.float64)

        # Spot cooling term (independent of human occupancy, 24/7)
        if p_conn_spot[tier] > 0.0:
            spot_demand = p_conn_spot[tier] * s_t * dt * m_latent
            tier_arr += np.minimum(p_conn_spot[tier], spot_demand)

        # Comfort cooling term (scaled by occupancy_fraction)
        if p_conn_comfort[tier] > 0.0:
            comfort_cap = occ * p_conn_comfort[tier]
            comfort_demand = occ * p_conn_comfort[tier] * s_t * dt * m_latent
            tier_arr += np.minimum(comfort_cap, comfort_demand)

        tier_arrays[tier] = tier_arr

    return TieredDemand(
        tier1_kwh=tier_arrays[1],
        tier2_kwh=tier_arrays[2],
        tier3_kwh=tier_arrays[3],
    )
