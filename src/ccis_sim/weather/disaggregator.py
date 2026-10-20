"""Daily-to-hourly weather disaggregation engine.

Implements physically-grounded disaggregation of daily NASA POWER meteorological
aggregates (T2M, T2M_MAX, T2M_MIN, RH2M, ALLSKY_SFC_SW_DWN) to hourly time series:
1. Solar Irradiance: Astronomical solar geometry model (declination, sunset hour angle)
   with half-sine daytime distribution, normalized for strict daily energy conservation.
2. Ambient Temperature: Diurnal sinusoidal profile anchored to T2M_MIN at sunrise
   and T2M_MAX at peak afternoon insolation (~14:00 PST).
3. Relative Humidity: Tetens saturation vapor pressure model assuming constant
   daily vapor pressure, yielding inverse diurnal coupling with temperature.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

BATAC_LATITUDE = 18.06   # degrees North
BATAC_LONGITUDE = 120.56 # degrees East
PST_OFFSET = timezone(timedelta(hours=8))


class DailyDisaggregator:
    """Disaggregates daily weather summaries into 24-hour diurnal profiles."""

    def __init__(
        self,
        latitude: float = BATAC_LATITUDE,
        longitude: float = BATAC_LONGITUDE,
        peak_temp_hour: float = 14.0,
    ) -> None:
        self.latitude = latitude
        self.longitude = longitude
        self.peak_temp_hour = peak_temp_hour

    @staticmethod
    def _saturation_vapor_pressure(temp_c: float | np.ndarray) -> float | np.ndarray:
        """Tetens equation for saturation vapor pressure (kPa) over liquid water."""
        return 0.61078 * np.exp((17.27 * temp_c) / (temp_c + 237.3))

    def _solar_geometry(self, day_of_year: int) -> tuple[float, float]:
        """Compute approximate sunrise and sunset solar times (hours from midnight).

        Args:
            day_of_year: Day of year (1 to 365/366).

        Returns:
            Tuple of (sunrise_hour, sunset_hour) in local solar/standard time.
        """
        phi = np.radians(self.latitude)
        # Cooper's equation for solar declination
        delta = np.radians(23.45 * np.sin(np.radians(360.0 / 365.0 * (284 + day_of_year))))

        # Sunset hour angle
        cos_omega_s = -np.tan(phi) * np.tan(delta)
        cos_omega_s = np.clip(cos_omega_s, -1.0, 1.0)
        omega_s_deg = np.degrees(np.arccos(cos_omega_s))

        half_day_hours = omega_s_deg / 15.0
        sunrise = 12.0 - half_day_hours
        sunset = 12.0 + half_day_hours
        return float(sunrise), float(sunset)

    def disaggregate_day(
        self,
        date: datetime,
        t_mean: float,
        t_max: float,
        t_min: float,
        rh_mean: float,
        ghi_daily_kwh: float,
    ) -> dict[str, np.ndarray]:
        """Disaggregate a single day's parameters into 24 hourly values.

        Args:
            date: Calendar date of the observation.
            t_mean: Daily mean temperature (°C).
            t_max: Daily maximum temperature (°C).
            t_min: Daily minimum temperature (°C).
            rh_mean: Daily mean relative humidity (%).
            ghi_daily_kwh: Daily global horizontal insolation (kWh/m^2/day).

        Returns:
            Dictionary with 24-element arrays:
            {'t_amb': ndarray, 'rh': ndarray, 'ghi': ndarray}
        """
        day_of_year = date.timetuple().tm_yday
        h_sr, h_ss = self._solar_geometry(day_of_year)

        # Mid-hour times: 0.5, 1.5, ..., 23.5
        hours = np.arange(24, dtype=float) + 0.5

        # -------------------------------------------------------------
        # 1. Solar Irradiance (GHI) Disaggregation
        # -------------------------------------------------------------
        # Half-sine distribution between sunrise and sunset
        weights = np.zeros(24, dtype=float)
        for i, h in enumerate(hours):
            if h_sr < h < h_ss:
                weights[i] = np.sin(np.pi * (h - h_sr) / (h_ss - h_sr))

        w_sum = np.sum(weights)
        if w_sum > 0.0 and ghi_daily_kwh > 0.0:
            ghi_hourly = (ghi_daily_kwh * 1000.0 / w_sum) * weights
        else:
            ghi_hourly = np.zeros(24, dtype=float)

        # -------------------------------------------------------------
        # 2. Ambient Temperature (t_amb) Disaggregation
        # -------------------------------------------------------------
        t_amb = np.zeros(24, dtype=float)
        h_max = self.peak_temp_hour

        if t_max < t_min:
            t_max, t_min = t_min, t_max

        delta_t = t_max - t_min

        for i, h in enumerate(hours):
            if h <= h_sr:
                t_effective = h + 24.0
                decay_duration = 24.0 - (h_max - h_sr)
                fraction = (t_effective - h_max) / decay_duration
                t_amb[i] = t_min + delta_t * 0.5 * (1.0 + np.cos(np.pi * fraction))
            elif h <= h_max:
                fraction = (h - h_sr) / (h_max - h_sr)
                t_amb[i] = t_min + delta_t * np.sin(np.pi * 0.5 * fraction)
            else:
                decay_duration = 24.0 - (h_max - h_sr)
                fraction = (h - h_max) / decay_duration
                t_amb[i] = t_min + delta_t * 0.5 * (1.0 + np.cos(np.pi * fraction))

        # -------------------------------------------------------------
        # 3. Relative Humidity (rh) Disaggregation
        # -------------------------------------------------------------
        e_s_mean = self._saturation_vapor_pressure(t_mean)
        actual_vapor_pressure = (np.clip(rh_mean, 0.0, 100.0) / 100.0) * e_s_mean
        e_s_hourly = self._saturation_vapor_pressure(t_amb)
        rh_hourly = 100.0 * (actual_vapor_pressure / e_s_hourly)
        rh_hourly = np.clip(rh_hourly, 5.0, 100.0)

        return {
            "t_amb": np.round(t_amb, 2),
            "rh": np.round(rh_hourly, 2),
            "ghi": np.round(ghi_hourly, 2),
        }

    def disaggregate_dataframe(self, daily_df: pd.DataFrame) -> pd.DataFrame:
        """Disaggregate a daily weather DataFrame to a full hourly DataFrame.

        Expected daily_df columns:
            ['t_mean', 't_max', 't_min', 'rh_mean', 'ghi_daily_kwh']
        Index: DatetimeIndex of daily dates.

        Returns:
            pd.DataFrame with PST hourly index and columns:
            ['hour', 'timestamp', 't_amb', 'rh', 'ghi'].
        """
        required_cols = {"t_mean", "t_max", "t_min", "rh_mean", "ghi_daily_kwh"}
        missing = required_cols - set(daily_df.columns)
        if missing:
            raise ValueError(f"Daily DataFrame missing required columns: {missing}")

        all_records: list[dict[str, Any]] = []
        hour_counter = 1

        for date_idx, row in daily_df.iterrows():
            if isinstance(date_idx, pd.Timestamp):
                current_date = date_idx.to_pydatetime()
            else:
                current_date = pd.to_datetime(date_idx).to_pydatetime()

            hourly_data = self.disaggregate_day(
                date=current_date,
                t_mean=float(row["t_mean"]),
                t_max=float(row["t_max"]),
                t_min=float(row["t_min"]),
                rh_mean=float(row["rh_mean"]),
                ghi_daily_kwh=float(row["ghi_daily_kwh"]),
            )

            for h in range(24):
                hour_dt = datetime(
                    current_date.year,
                    current_date.month,
                    current_date.day,
                    h,
                    0,
                    0,
                    tzinfo=PST_OFFSET,
                )
                all_records.append(
                    {
                        "hour": hour_counter,
                        "timestamp": hour_dt.strftime("%Y-%m-%d %H:%M:%S+08:00"),
                        "t_amb": hourly_data["t_amb"][h],
                        "rh": hourly_data["rh"][h],
                        "ghi": hourly_data["ghi"][h],
                    }
                )
                hour_counter += 1

        return pd.DataFrame(all_records)
