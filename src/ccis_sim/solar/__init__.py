"""Solar photovoltaic output models: array sizing, inverter clipping, and balance-of-system losses."""

from __future__ import annotations

from ccis_sim.solar.array import (
    ASSUMED_MEAN_THERMAL_FACTOR,
    DEFAULT_AC_WIRING_FACTOR,
    DEFAULT_AVAILABILITY_FACTOR,
    DEFAULT_DC_AC_RATIO,
    DEFAULT_DC_WIRING_FACTOR,
    DEFAULT_INVERTER_EFFICIENCY,
    DEFAULT_MISMATCH_FACTOR,
    DEFAULT_SOILING_FACTOR,
    compute_ac_generation,
    get_inverter_ac_rating,
    get_non_thermal_bos_factor,
)

__all__ = [
    "ASSUMED_MEAN_THERMAL_FACTOR",
    "DEFAULT_AC_WIRING_FACTOR",
    "DEFAULT_AVAILABILITY_FACTOR",
    "DEFAULT_DC_AC_RATIO",
    "DEFAULT_DC_WIRING_FACTOR",
    "DEFAULT_INVERTER_EFFICIENCY",
    "DEFAULT_MISMATCH_FACTOR",
    "DEFAULT_SOILING_FACTOR",
    "compute_ac_generation",
    "get_inverter_ac_rating",
    "get_non_thermal_bos_factor",
]
