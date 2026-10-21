"""Solar PV array capacity scaling, inverter clipping, and balance-of-system losses.

Implements conversion of hourly DC generation per kWp (from SOL-001) into AC power
generation (kWh/h) for sized rooftop PV arrays across scenario capacities
(0, 50, 100, 200 kWp per [D-18]), modeling inverter efficiency (98%), DC/AC clipping,
and non-temperature balance-of-system (BOS) derating per decisions [D-08] and [D-30].

Conforms to Phase 2 interface contract (docs/context/phase2-interface-contract.md).
"""

from __future__ import annotations

import logging

import numpy as np

from ccis_sim.core.models import SolarArray

logger = logging.getLogger(__name__)

# [ASSUMPTION] Peak inverter efficiency per [D-08] and [D-30]
DEFAULT_INVERTER_EFFICIENCY: float = 0.980  # 98.0% peak inverter efficiency (SOL-002.2)

# [ASSUMPTION] Commercial rooftop inverter loading ratio (DC/AC ratio) per [D-30]
# Standard IEEE/NREL sizing convention optimizing inverter utilization under tropical thermal derates
DEFAULT_DC_AC_RATIO: float = 1.20

# [ASSUMPTION] Named balance-of-system (BOS) derate factors per [D-08] and [D-30]
# Decomposed so that Non-Thermal BOS * Inverter Efficiency * Assumed Mean Thermal ≈ 0.77 PR
DEFAULT_SOILING_FACTOR: float = 0.960       # 4.0% seasonal soiling/dust loss in Batac
DEFAULT_DC_WIRING_FACTOR: float = 0.985     # 1.5% DC ohmic cabling and connection loss
DEFAULT_AC_WIRING_FACTOR: float = 0.990     # 1.0% AC collection and transformer loss
DEFAULT_MISMATCH_FACTOR: float = 0.980      # 2.0% module mismatch and manufacturer nameplate tolerance
DEFAULT_AVAILABILITY_FACTOR: float = 0.990  # 1.0% operational availability and maintenance downtime

# [ASSUMPTION] Assumed annual mean thermal factor representing cell temperature losses
# Derived from physical NOCT thermal modeling in Batac tropical climate (~13.49% mean thermal loss) per [D-30]
ASSUMED_MEAN_THERMAL_FACTOR: float = 0.8650888630630106

# [ASSUMPTION] Implied annual energy-weighted cell thermal derating factor evaluated upstream
# by SOL-001 under the 2019 Batac weather fixture (SOL-002.4 / [D-35]).
# (Derated DC yield 1,695.05 kWh/kWp / Un-derated POA insolation 1,945.98 kWh/m2 ≈ 0.871056; ~12.89% thermal loss).
IMPLIED_ANNUAL_THERMAL_FACTOR_2019: float = 0.8710563456728557


def get_non_thermal_bos_factor(
    *,
    soiling: float = DEFAULT_SOILING_FACTOR,
    dc_wiring: float = DEFAULT_DC_WIRING_FACTOR,
    ac_wiring: float = DEFAULT_AC_WIRING_FACTOR,
    mismatch: float = DEFAULT_MISMATCH_FACTOR,
    availability: float = DEFAULT_AVAILABILITY_FACTOR,
) -> float:
    """Calculate the cumulative non-thermal Balance-of-System (BOS) derating factor.

    Product of named non-thermal loss factors:
    f_bos = soiling * dc_wiring * ac_wiring * mismatch * availability

    Returns:
        Cumulative dimensionless non-thermal BOS derate factor (~0.9082).
    """
    return soiling * dc_wiring * ac_wiring * mismatch * availability


def get_inverter_ac_rating(
    capacity_kwp: float,
    *,
    dc_ac_ratio: float = DEFAULT_DC_AC_RATIO,
) -> float:
    """Calculate the inverter rated continuous AC power capacity (kW AC).

    Formula per [D-30]:
    P_ac_rated = capacity_kwp / dc_ac_ratio

    Args:
        capacity_kwp: Nameplate DC capacity of the PV array (kWp).
        dc_ac_ratio: Inverter loading ratio (default: 1.20).

    Returns:
        Inverter continuous AC power rating in kW.
    """
    if capacity_kwp <= 0.0:
        return 0.0
    if dc_ac_ratio <= 0.0:
        raise ValueError(f"dc_ac_ratio must be strictly positive, got {dc_ac_ratio}")
    return capacity_kwp / dc_ac_ratio


def compute_ac_generation(
    dc_kw_per_kwp: np.ndarray,
    array: SolarArray,
    *,
    inverter_efficiency: float = DEFAULT_INVERTER_EFFICIENCY,
    dc_ac_ratio: float = DEFAULT_DC_AC_RATIO,
    soiling: float = DEFAULT_SOILING_FACTOR,
    dc_wiring: float = DEFAULT_DC_WIRING_FACTOR,
    ac_wiring: float = DEFAULT_AC_WIRING_FACTOR,
    mismatch: float = DEFAULT_MISMATCH_FACTOR,
    availability: float = DEFAULT_AVAILABILITY_FACTOR,
) -> np.ndarray:
    """Compute hourly AC power generation for a sized solar PV array.

    Scales array capacity, models inverter peak efficiency and DC/AC clipping limit,
    and applies non-thermal balance-of-system (BOS) loss factors to produce hourly
    AC power output. Does not double-count temperature losses, as temperature derating
    is explicitly modeled upstream in dc_kw_per_kwp (SOL-001).

    Conforms to Phase 2 interface contract (docs/context/phase2-interface-contract.md).

    Args:
        dc_kw_per_kwp: 1D numpy array of length N (8,760) representing hourly DC yield
            per unit capacity (kW DC / kWp), computed by SOL-001.
        array: SolarArray instance specifying capacity_kwp and parameters.
        inverter_efficiency: Inverter peak conversion efficiency (default: 0.98 per [D-30]).
        dc_ac_ratio: Inverter DC/AC sizing ratio for clipping (default: 1.20 per [D-30]).
        soiling: Soiling derating factor (default: 0.96).
        dc_wiring: DC wiring derating factor (default: 0.985).
        ac_wiring: AC wiring derating factor (default: 0.99).
        mismatch: Module mismatch derating factor (default: 0.98).
        availability: System availability derating factor (default: 0.99).

    Returns:
        1D numpy float64 array of length N representing hourly AC energy output in kWh/h
        (numerically equivalent to kW AC at Δt = 1.0 h). Guaranteed strictly non-negative,
        bounded by the inverter AC rating, and 0.0 at night and for 0 kWp arrays.
    """
    dc_in = np.asarray(dc_kw_per_kwp, dtype=np.float64)

    if len(dc_in) == 0:
        return np.empty(0, dtype=np.float64)

    if not np.all(np.isfinite(dc_in)):
        raise ValueError("Input 'dc_kw_per_kwp' contains non-finite values (NaN or inf).")
    if np.any(dc_in < 0.0):
        raise ValueError("Input 'dc_kw_per_kwp' contains negative values.")

    # Capacity scenario 0 kWp returns strict zero array
    if array.capacity_kwp == 0.0:
        return np.zeros_like(dc_in)

    # 1. Scale DC power to nameplate capacity
    # dc_raw in kW DC
    dc_raw = dc_in * array.capacity_kwp

    # 2. Apply DC-side balance-of-system losses (soiling, DC wiring, mismatch, availability)
    dc_bos_factor = soiling * dc_wiring * mismatch * availability
    dc_at_inverter = dc_raw * dc_bos_factor

    # 3. Inverter conversion and clipping
    # Gross AC power before clipping (kW)
    ac_gross = dc_at_inverter * inverter_efficiency

    # Inverter AC rating limit (kW AC)
    ac_rating = get_inverter_ac_rating(array.capacity_kwp, dc_ac_ratio=dc_ac_ratio)

    # Inverter clipping: AC output cannot exceed continuous rating
    ac_clipped = np.minimum(ac_gross, ac_rating)

    # 4. Apply AC-side collection and wiring loss
    ac_net = ac_clipped * ac_wiring

    # Clean numerical precision and guarantee strict non-negativity
    ac_net = np.maximum(0.0, ac_net)

    return ac_net
