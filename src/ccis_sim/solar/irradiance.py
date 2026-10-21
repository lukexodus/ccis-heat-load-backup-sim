"""Solar irradiance geometry and NOCT cell temperature thermal derating model.

Calculates hourly plane-of-array (POA) irradiance for a tilted rooftop PV array
at Batac, Ilocos Norte, models cell operating temperature with rooftop mounting
thermal penalty, and applies temperature derating to compute DC power yield per kWp.

Conforms to Phase 2 interface contract (docs/context/phase2-interface-contract.md)
and decisions [D-08] and [D-29].
"""

from __future__ import annotations

import logging
from typing import NamedTuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Standard constants
SOLAR_CONSTANT_W_M2 = 1367.0  # W/m^2 solar constant (G_sc)
STC_IRRADIANCE_W_M2 = 1000.0  # W/m^2 Standard Test Conditions (STC) irradiance
STC_CELL_TEMP_C = 25.0  # °C STC cell reference temperature

# Physical modeling parameters per [D-08] and [D-29]
DEFAULT_TILT_DEG = 15.0  # degrees South-facing optimal tilt for Batac (~18.06°N)
DEFAULT_AZIMUTH_DEG = 180.0  # degrees True South (North = 0°, South = 180°)
BATAC_LATITUDE_DEG = 18.06  # degrees North
BATAC_LONGITUDE_DEG = 120.56  # degrees East
STANDARD_MERIDIAN_DEG = 120.0  # degrees East (UTC+8 Philippine Standard Time)

# [ASSUMPTION] Ground diffuse albedo for academic campus surroundings (grass/concrete mix) per [D-29]
DEFAULT_ALBEDO = 0.20

# [ASSUMPTION] Nominal Operating Cell Temperature with +10°C rooftop thermal penalty per [D-08] and [D-29]
DEFAULT_NOCT_C = 45.0  # °C baseline manufacturer NOCT
ROOFTOP_PENALTY_C = 10.0  # °C close-roof mounting thermal penalty per [D-08]
EFFECTIVE_NOCT_C = DEFAULT_NOCT_C + ROOFTOP_PENALTY_C  # 55.0 °C effective NOCT

# Temperature coefficient of power per [D-08]
TEMP_COEFFICIENT_PER_C = -0.0040  # -0.40%/°C for monocrystalline silicon


class SolarPosition(NamedTuple):
    """Astronomical solar position and geometric angles."""

    solar_time_hours: np.ndarray
    hour_angle_rad: np.ndarray
    declination_rad: np.ndarray
    cos_zenith: np.ndarray
    zenith_rad: np.ndarray
    elevation_deg: np.ndarray
    cos_incidence: np.ndarray


def compute_solar_position(
    timestamps: pd.Series | pd.DatetimeIndex | np.ndarray,
    *,
    tilt_deg: float = DEFAULT_TILT_DEG,
    azimuth_deg: float = DEFAULT_AZIMUTH_DEG,
    latitude_deg: float = BATAC_LATITUDE_DEG,
    longitude_deg: float = BATAC_LONGITUDE_DEG,
    standard_meridian_deg: float = STANDARD_MERIDIAN_DEG,
) -> SolarPosition:
    """Compute astronomical solar position and surface incidence angle.

    Uses the Spencer (1971) Fourier series formulation for solar declination
    and Equation of Time (EoT), with longitude correction for local solar time.

    Args:
        timestamps: Series or array of datetimes (UTC+8 / PST).
        tilt_deg: Surface tilt angle from horizontal in degrees (default: 15.0°).
        azimuth_deg: Surface azimuth from True North in degrees (default: 180.0° / South).
        latitude_deg: Site latitude in degrees North (default: 18.06°).
        longitude_deg: Site longitude in degrees East (default: 120.56°).
        standard_meridian_deg: Timezone standard meridian in degrees East (default: 120.0°).

    Returns:
        SolarPosition named tuple containing solar time, hour angle, declination,
        cos(zenith), zenith, elevation, and cos(incidence).
    """
    dti = pd.DatetimeIndex(pd.to_datetime(timestamps))
    day_of_year = dti.dayofyear.values.astype(np.float64)
    local_hours = (
        dti.hour.values.astype(np.float64)
        + dti.minute.values.astype(np.float64) / 60.0
        + dti.second.values.astype(np.float64) / 3600.0
    )

    phi = np.radians(latitude_deg)
    beta = np.radians(tilt_deg)
    # Duffie & Beckman surface azimuth from South: gamma_DB = azimuth - 180°
    gamma_db = np.radians(azimuth_deg - 180.0)

    # Fractional day angle B in radians (Spencer 1971)
    b = 2.0 * np.pi * (day_of_year - 1.0) / 365.0

    # Spencer Fourier series for solar declination (radians)
    delta = (
        0.006918
        - 0.399912 * np.cos(b)
        + 0.070257 * np.sin(b)
        - 0.006758 * np.cos(2.0 * b)
        + 0.000907 * np.sin(2.0 * b)
        - 0.002697 * np.cos(3.0 * b)
        + 0.00148 * np.sin(3.0 * b)
    )

    # Spencer Equation of Time (minutes)
    eot_min = 229.18 * (
        0.000075
        + 0.001868 * np.cos(b)
        - 0.032077 * np.sin(b)
        - 0.014615 * np.cos(2.0 * b)
        - 0.040849 * np.sin(2.0 * b)
    )

    # Longitude time correction (minutes): 4 min per degree East of meridian
    lon_correction_min = 4.0 * (longitude_deg - standard_meridian_deg)

    # Local Solar Time (hours)
    solar_time = local_hours + (eot_min + lon_correction_min) / 60.0

    # Solar hour angle omega (radians, omega = 0 at solar noon)
    omega = np.radians(15.0 * (solar_time - 12.0))

    # Solar zenith angle: cos(theta_z)
    cos_theta_z = np.sin(phi) * np.sin(delta) + np.cos(phi) * np.cos(delta) * np.cos(omega)
    cos_theta_z = np.clip(cos_theta_z, -1.0, 1.0)
    theta_z = np.arccos(cos_theta_z)
    elevation_deg = 90.0 - np.degrees(theta_z)

    # Angle of incidence theta on tilted plane (Duffie & Beckman eq 1.6.2):
    # cos(theta) = sin(delta)*sin(phi)*cos(beta) - sin(delta)*cos(phi)*sin(beta)*cos(gamma_DB)
    #              + cos(delta)*cos(phi)*cos(beta)*cos(omega)
    #              + cos(delta)*sin(phi)*sin(beta)*cos(gamma_DB)*cos(omega)
    #              + cos(delta)*sin(beta)*sin(gamma_DB)*sin(omega)
    cos_incidence = (
        np.sin(delta) * np.sin(phi) * np.cos(beta)
        - np.sin(delta) * np.cos(phi) * np.sin(beta) * np.cos(gamma_db)
        + np.cos(delta) * np.cos(phi) * np.cos(beta) * np.cos(omega)
        + np.cos(delta) * np.sin(phi) * np.sin(beta) * np.cos(gamma_db) * np.cos(omega)
        + np.cos(delta) * np.sin(beta) * np.sin(gamma_db) * np.sin(omega)
    )
    cos_incidence = np.clip(cos_incidence, -1.0, 1.0)

    return SolarPosition(
        solar_time_hours=solar_time,
        hour_angle_rad=omega,
        declination_rad=delta,
        cos_zenith=cos_theta_z,
        zenith_rad=theta_z,
        elevation_deg=elevation_deg,
        cos_incidence=cos_incidence,
    )


def decompose_ghi_erbs(
    ghi_w_m2: np.ndarray,
    cos_zenith: np.ndarray,
    day_of_year: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Decompose Global Horizontal Irradiance into DHI and DNI via the Erbs model.

    Implements the Erbs, Klein, and Duffie (1982) empirical correlation relating
    the diffuse fraction kd = DHI / GHI to the hourly clearness index kt = GHI / G_0.

    Args:
        ghi_w_m2: 1D array of global horizontal irradiance (W/m^2).
        cos_zenith: 1D array of cos(theta_z) solar zenith cosines.
        day_of_year: 1D array of day numbers (1 to 365/366).

    Returns:
        Tuple of (dhi_w_m2, dni_w_m2) 1D numpy arrays.
    """
    ghi = np.asarray(ghi_w_m2, dtype=np.float64)
    cos_z = np.asarray(cos_zenith, dtype=np.float64)
    doy = np.asarray(day_of_year, dtype=np.float64)

    # Extraterrestrial normal and horizontal irradiance
    # G_on = G_sc * [1 + 0.033 * cos(2*pi*n/365)]
    g_on = SOLAR_CONSTANT_W_M2 * (1.0 + 0.033 * np.cos(2.0 * np.pi * doy / 365.0))
    g_0 = np.maximum(0.0, g_on * cos_z)

    # Daytime mask: sun above horizon and positive irradiance
    daytime = (ghi > 0.0) & (cos_z > 1e-3)

    # Hourly clearness index kt
    kt = np.zeros_like(ghi)
    safe_g0 = np.maximum(g_0[daytime], 1.0)
    kt[daytime] = np.clip(ghi[daytime] / safe_g0, 0.0, 1.2)

    # Erbs piecewise correlation for diffuse fraction kd
    kd = np.ones_like(ghi)  # Night or zero irradiance defaults to 1.0

    mask1 = daytime & (kt <= 0.22)
    kd[mask1] = 1.0 - 0.09 * kt[mask1]

    mask2 = daytime & (kt > 0.22) & (kt <= 0.80)
    kt2 = kt[mask2]
    kd[mask2] = 0.9511 - 0.1604 * kt2 + 4.388 * (kt2**2) - 16.638 * (kt2**3) + 12.336 * (kt2**4)

    mask3 = daytime & (kt > 0.80)
    kd[mask3] = 0.165

    # Compute DHI and DNI
    dhi = np.zeros_like(ghi)
    dhi[daytime] = np.clip(ghi[daytime] * kd[daytime], 0.0, ghi[daytime])

    dni = np.zeros_like(ghi)
    dni[daytime] = np.maximum(0.0, (ghi[daytime] - dhi[daytime]) / cos_z[daytime])
    # Cap DNI at extraterrestrial normal radiation
    dni[daytime] = np.minimum(dni[daytime], g_on[daytime])

    return dhi, dni


def transpose_irradiance_isotropic(
    ghi_w_m2: np.ndarray,
    dhi_w_m2: np.ndarray,
    dni_w_m2: np.ndarray,
    cos_zenith: np.ndarray,
    cos_incidence: np.ndarray,
    *,
    tilt_deg: float = DEFAULT_TILT_DEG,
    albedo: float = DEFAULT_ALBEDO,
) -> np.ndarray:
    """Transpose horizontal solar components to plane-of-array (POA) irradiance.

    Uses the Liu & Jordan (1963) isotropic sky diffuse model:
    G_poa = G_beam + G_diffuse_sky + G_ground_reflected

    Args:
        ghi_w_m2: Global horizontal irradiance (W/m^2).
        dhi_w_m2: Diffuse horizontal irradiance (W/m^2).
        dni_w_m2: Direct normal irradiance (W/m^2).
        cos_zenith: Cosine of solar zenith angle.
        cos_incidence: Cosine of surface incidence angle.
        tilt_deg: Surface tilt from horizontal (degrees).
        albedo: Ground reflectance factor (default: 0.20 per [D-29]).

    Returns:
        1D numpy array of total POA irradiance (W/m^2).
    """
    ghi = np.asarray(ghi_w_m2, dtype=np.float64)
    dhi = np.asarray(dhi_w_m2, dtype=np.float64)
    dni = np.asarray(dni_w_m2, dtype=np.float64)
    cos_z = np.asarray(cos_zenith, dtype=np.float64)
    cos_inc = np.asarray(cos_incidence, dtype=np.float64)

    beta = np.radians(tilt_deg)
    daytime = (ghi > 0.0) & (cos_z > 1e-3)

    # 1. Beam on tilted plane: DNI * max(0, cos(theta))
    g_beam = np.zeros_like(ghi)
    g_beam[daytime] = dni[daytime] * np.maximum(0.0, cos_inc[daytime])

    # 2. Isotropic sky diffuse: DHI * (1 + cos(beta)) / 2
    g_sky = np.zeros_like(ghi)
    g_sky[daytime] = dhi[daytime] * (1.0 + np.cos(beta)) / 2.0

    # 3. Ground-reflected diffuse: GHI * rho_g * (1 - cos(beta)) / 2
    g_ground = np.zeros_like(ghi)
    g_ground[daytime] = ghi[daytime] * albedo * (1.0 - np.cos(beta)) / 2.0

    g_poa = np.zeros_like(ghi)
    g_poa[daytime] = g_beam[daytime] + g_sky[daytime] + g_ground[daytime]
    g_poa = np.maximum(0.0, g_poa)

    return g_poa


def compute_cell_temperature(
    t_amb_c: np.ndarray,
    g_poa_w_m2: np.ndarray,
    *,
    effective_noct_c: float = EFFECTIVE_NOCT_C,
) -> np.ndarray:
    """Compute PV cell operating temperature including rooftop mounting penalty.

    Formula per [D-08] and [D-29]:
    T_cell = T_amb + ((effective_noct - 20.0) / 800.0) * G_poa
    where effective_noct = NOCT_base (45°C) + rooftop_penalty (+10°C) = 55°C.

    Args:
        t_amb_c: Ambient dry-bulb temperature (°C).
        g_poa_w_m2: Plane-of-array irradiance (W/m^2).
        effective_noct_c: Effective NOCT accounting for mounting thermal penalty (°C).

    Returns:
        1D numpy array of cell operating temperature (°C).
    """
    t_amb = np.asarray(t_amb_c, dtype=np.float64)
    g_poa = np.asarray(g_poa_w_m2, dtype=np.float64)

    # (55.0 - 20.0) / 800.0 = 35.0 / 800.0 = 0.04375 °C / (W/m^2)
    thermal_slope = (effective_noct_c - 20.0) / 800.0
    t_cell = t_amb + thermal_slope * np.maximum(0.0, g_poa)
    return t_cell


def compute_thermal_derating_factor(
    t_cell_c: np.ndarray,
    *,
    gamma_per_c: float = TEMP_COEFFICIENT_PER_C,
    t_ref_c: float = STC_CELL_TEMP_C,
) -> np.ndarray:
    """Compute module temperature derating factor relative to STC (25°C).

    Formula per [D-08]:
    f_temp = max(0.0, 1.0 + gamma * (T_cell - 25.0))
    where gamma = -0.40%/°C (-0.0040/°C).

    Args:
        t_cell_c: Cell operating temperature (°C).
        gamma_per_c: Temperature coefficient of power (1/°C, negative).
        t_ref_c: Reference cell temperature (°C, default: 25.0).

    Returns:
        1D numpy array of dimensionless thermal derating factors.
    """
    t_cell = np.asarray(t_cell_c, dtype=np.float64)
    f_temp = 1.0 + gamma_per_c * (t_cell - t_ref_c)
    return np.maximum(0.0, f_temp)


def compute_dc_power_per_kwp(
    weather_df: pd.DataFrame,
    *,
    tilt_deg: float = DEFAULT_TILT_DEG,
    azimuth_deg: float = DEFAULT_AZIMUTH_DEG,
    latitude_deg: float = BATAC_LATITUDE_DEG,
    longitude_deg: float = BATAC_LONGITUDE_DEG,
) -> np.ndarray:
    """Compute hourly DC power output per kWp for a rooftop PV array at Batac.

    Transforms hourly Global Horizontal Irradiance (GHI) and ambient temperature
    into plane-of-array irradiance, calculates cell operating temperature under
    rooftop thermal mounting penalties, and applies module thermal derating.

    Outputs DC power per kWp BEFORE balance-of-system and inverter losses
    (which are modeled in SOL-002 per docs/context/phase2-interface-contract.md).

    Args:
        weather_df: Verified weather DataFrame containing columns:
            ['hour', 'timestamp', 't_amb', 'rh', 'ghi'].
        tilt_deg: Array tilt angle from horizontal in degrees (default: 15.0°).
        azimuth_deg: Array azimuth angle from North in degrees (default: 180.0° / South).
        latitude_deg: Site latitude in degrees North (default: 18.06°).
        longitude_deg: Site longitude in degrees East (default: 120.56°).

    Returns:
        1D numpy float array of length N (8,760 for annual runs) representing
        hourly DC power generation in kW DC per kWp (equivalent to kWh/kWp at Δt = 1.0h).
    """
    if "ghi" not in weather_df.columns:
        raise ValueError("Weather DataFrame missing required column 'ghi'.")
    if "t_amb" not in weather_df.columns:
        raise ValueError("Weather DataFrame missing required column 't_amb'.")

    n_rows = len(weather_df)
    if n_rows == 0:
        return np.empty(0, dtype=np.float64)

    ghi = weather_df["ghi"].values.astype(np.float64)
    t_amb = weather_df["t_amb"].values.astype(np.float64)

    # Validate inputs
    if not np.all(np.isfinite(ghi)):
        raise ValueError("Column 'ghi' contains non-finite values (NaN or inf).")
    if not np.all(np.isfinite(t_amb)):
        raise ValueError("Column 't_amb' contains non-finite values (NaN or inf).")
    if np.any(ghi < 0.0):
        raise ValueError("Column 'ghi' contains negative irradiance values.")

    # Determine timestamps / days of year
    if "timestamp" in weather_df.columns:
        ts = pd.DatetimeIndex(pd.to_datetime(weather_df["timestamp"]))
        doy = ts.dayofyear.values.astype(np.float64)
    elif "hour" in weather_df.columns:
        # Fallback if only 'hour' is provided (1..8760 standard annual sequence)
        hours = weather_df["hour"].values.astype(int)
        # Hour 1 corresponds to 2019-01-01 00:00:00+08:00
        ref_start = pd.Timestamp("2019-01-01 00:00:00+08:00")
        ts = pd.date_range(start=ref_start, periods=len(hours), freq="1h")
        doy = ts.dayofyear.values.astype(np.float64)
    else:
        raise ValueError("Weather DataFrame must contain either 'timestamp' or 'hour' column.")

    # 1. Astronomical solar position
    pos = compute_solar_position(
        ts,
        tilt_deg=tilt_deg,
        azimuth_deg=azimuth_deg,
        latitude_deg=latitude_deg,
        longitude_deg=longitude_deg,
    )

    # 2. GHI -> DHI / DNI decomposition (Erbs correlation)
    dhi, dni = decompose_ghi_erbs(ghi, pos.cos_zenith, doy)

    # 3. Transposition to Plane of Array (Liu-Jordan Isotropic)
    g_poa = transpose_irradiance_isotropic(
        ghi,
        dhi,
        dni,
        pos.cos_zenith,
        pos.cos_incidence,
        tilt_deg=tilt_deg,
        albedo=DEFAULT_ALBEDO,
    )

    # 4. Cell temperature calculation (NOCT + rooftop thermal penalty)
    t_cell = compute_cell_temperature(t_amb, g_poa, effective_noct_c=EFFECTIVE_NOCT_C)

    # 5. Thermal derating factor relative to STC
    f_temp = compute_thermal_derating_factor(t_cell, gamma_per_c=TEMP_COEFFICIENT_PER_C)

    # 6. DC Power output per kWp: (G_poa / 1000 W/m^2) * f_temp
    # Strictly zero whenever GHI is zero or sun is below horizon
    daytime = (ghi > 0.0) & (pos.cos_zenith > 1e-3)
    dc_power_kw_per_kwp = np.zeros(n_rows, dtype=np.float64)
    dc_power_kw_per_kwp[daytime] = (g_poa[daytime] / STC_IRRADIANCE_W_M2) * f_temp[daytime]

    # Clean numerical precision
    dc_power_kw_per_kwp = np.maximum(0.0, dc_power_kw_per_kwp)

    return dc_power_kw_per_kwp
