"""Solar photovoltaic output models: irradiance geometry, NOCT thermal derating, array sizing, and BOS losses."""

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
from ccis_sim.solar.irradiance import (
    compute_cell_temperature,
    compute_dc_power_per_kwp,
    compute_solar_position,
    compute_thermal_derating_factor,
    decompose_ghi_erbs,
    transpose_irradiance_isotropic,
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
    "compute_cell_temperature",
    "compute_dc_power_per_kwp",
    "compute_solar_position",
    "compute_thermal_derating_factor",
    "decompose_ghi_erbs",
    "get_inverter_ac_rating",
    "get_non_thermal_bos_factor",
    "transpose_irradiance_isotropic",
]
