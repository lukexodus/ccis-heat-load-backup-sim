"""Weather data sanitizer for missing-value filtering, timezone alignment, and validation.

Handles:
- NASA POWER missing value sentinel (-999.0) replacement and interpolation.
- Timezone alignment to Philippine Standard Time (PST = UTC+8).
- Psychrometric boundary sanity checks (temperatures, humidity, solar irradiance).
- Annual 8,760-hour standardization (dropping Feb 29 in leap years per TMY/ASHRAE convention).
"""

from __future__ import annotations

import logging
from datetime import timezone, timedelta

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Philippine Standard Time is UTC+8
PST_OFFSET = timezone(timedelta(hours=8))
PST_TIMEZONE_STR = "+08:00"

SENTINEL_FILL_VALUE = -999.0

# Physical plausibility boundaries for Batac, Ilocos Norte
BOUNDS_T_AMB = (-10.0, 55.0)  # °C
BOUNDS_RH = (0.0, 100.0)      # %
BOUNDS_GHI = (0.0, 1500.0)    # W/m^2


class PsychrometricValidationError(ValueError):
    """Raised when weather parameters violate physical plausibility bounds."""
    pass


class WeatherSanitizer:
    """Sanitizes raw weather time-series for simulation consumption."""

    @staticmethod
    def filter_sentinels(df: pd.DataFrame, sentinel: float = SENTINEL_FILL_VALUE) -> pd.DataFrame:
        """Replace NASA POWER missing-value sentinels (-999.0) with np.nan."""
        clean_df = df.copy()
        for col in clean_df.columns:
            if pd.api.types.is_numeric_dtype(clean_df[col]):
                is_sentinel = np.isclose(clean_df[col], sentinel, atol=1e-3)
                clean_df.loc[is_sentinel, col] = np.nan
        return clean_df

    @staticmethod
    def interpolate_missing(
        df: pd.DataFrame,
        limit: int = 24,
        method: str = "time",
    ) -> pd.DataFrame:
        """Interpolate missing NaN values linearly with forward/backward boundary fill.

        Args:
            df: DataFrame with DatetimeIndex and numeric columns.
            limit: Maximum consecutive hours to interpolate linearly.
            method: Interpolation method (default 'time').

        Returns:
            Fully populated DataFrame with zero NaNs.
        """
        clean_df = df.copy()
        if isinstance(clean_df.index, pd.DatetimeIndex):
            clean_df = clean_df.interpolate(method="time", limit=limit)
        else:
            clean_df = clean_df.interpolate(method="linear", limit=limit)

        clean_df = clean_df.bfill().ffill()

        nan_count = clean_df.isna().sum().sum()
        if nan_count > 0:
            raise ValueError(f"Interpolation incomplete: {nan_count} NaN values remain in dataset.")

        return clean_df

    @staticmethod
    def align_to_pst(df: pd.DataFrame) -> pd.DataFrame:
        """Align DatetimeIndex to Philippine Standard Time (PST = UTC+8).

        If the index is in UTC, it is converted to PST (+8 hours).
        If the index is naive or in LST (already local time for Batac 120.56°E),
        it is localized to PST (+08:00).
        Adds canonical ISO-8601 string column 'timestamp' (YYYY-MM-DD HH:MM:SS+08:00).
        """
        clean_df = df.copy()

        if isinstance(clean_df.index, pd.DatetimeIndex):
            if clean_df.index.tz is None:
                # Naive index: if named timestamp_utc, localize UTC then convert
                if clean_df.index.name == "timestamp_utc":
                    utc_idx = clean_df.index.tz_localize("UTC")
                    clean_df.index = utc_idx.tz_convert(PST_OFFSET)
                else:
                    # Default local time (LST) for Batac
                    clean_df.index = clean_df.index.tz_localize(PST_OFFSET)
            else:
                # Timezone-aware: convert directly to PST
                clean_df.index = clean_df.index.tz_convert(PST_OFFSET)
            clean_df.index.name = "timestamp_pst"
        elif "timestamp_utc" in clean_df.columns:
            utc_series = pd.to_datetime(clean_df["timestamp_utc"], utc=True)
            clean_df["timestamp_pst"] = utc_series.dt.tz_convert(PST_OFFSET)
            clean_df = clean_df.set_index("timestamp_pst")
        else:
            raise ValueError("DataFrame has neither a DatetimeIndex nor a 'timestamp_utc' column.")

        clean_df["timestamp"] = clean_df.index.strftime("%Y-%m-%d %H:%M:%S+08:00")
        return clean_df

    @staticmethod
    def validate_psychrometrics(df: pd.DataFrame) -> None:
        """Check that meteorological values fall within physically plausible bounds."""
        if "t_amb" in df.columns:
            t_min, t_max = df["t_amb"].min(), df["t_amb"].max()
            if t_min < BOUNDS_T_AMB[0] or t_max > BOUNDS_T_AMB[1]:
                raise PsychrometricValidationError(
                    f"Ambient temperature out of bounds [{BOUNDS_T_AMB[0]}, {BOUNDS_T_AMB[1]}]: "
                    f"min={t_min:.2f}°C, max={t_max:.2f}°C"
                )

        if "rh" in df.columns:
            rh_min, rh_max = df["rh"].min(), df["rh"].max()
            if rh_min < BOUNDS_RH[0] - 1e-3 or rh_max > BOUNDS_RH[1] + 1e-3:
                raise PsychrometricValidationError(
                    f"Relative humidity out of bounds [{BOUNDS_RH[0]}, {BOUNDS_RH[1]}]: "
                    f"min={rh_min:.2f}%, max={rh_max:.2f}%"
                )

        if "ghi" in df.columns:
            ghi_min, ghi_max = df["ghi"].min(), df["ghi"].max()
            if ghi_min < BOUNDS_GHI[0] - 1e-3 or ghi_max > BOUNDS_GHI[1]:
                raise PsychrometricValidationError(
                    f"Solar irradiance GHI out of bounds [{BOUNDS_GHI[0]}, {BOUNDS_GHI[1]}]: "
                    f"min={ghi_min:.2f} W/m^2, max={ghi_max:.2f} W/m^2"
                )

    @classmethod
    def standardize_annual_hourly(
        cls,
        df: pd.DataFrame,
        target_year: int,
        drop_leap_day: bool = True,
    ) -> pd.DataFrame:
        """Filter to target calendar year in PST, sanitize, and format as 8,760 hours.

        Args:
            df: Hourly DataFrame with PST DatetimeIndex.
            target_year: Calendar year (e.g., 2016, 2019).
            drop_leap_day: If True, omit Feb 29 rows in leap years to maintain
                the canonical 8,760-hour contract per [D-05].

        Returns:
            Canonical DataFrame with columns ['hour', 'timestamp', 't_amb', 'rh', 'ghi']
            containing exactly 8,760 rows indexed 1..8,760.
        """
        if not isinstance(df.index, pd.DatetimeIndex) or df.index.tz is None:
            raise ValueError("Input DataFrame must possess a timezone-aware PST DatetimeIndex.")

        year_mask = df.index.year == target_year
        year_df = df.loc[year_mask].copy()

        # Handle leap year
        is_leap = (target_year % 4 == 0 and (target_year % 100 != 0 or target_year % 400 == 0))
        if is_leap and drop_leap_day:
            leap_mask = ~((year_df.index.month == 2) & (year_df.index.day == 29))
            year_df = year_df.loc[leap_mask].copy()

        if len(year_df) != 8760:
            raise ValueError(
                f"Expected exactly 8,760 hours for standardized year {target_year}, "
                f"but found {len(year_df)} hours."
            )

        cls.validate_psychrometrics(year_df)

        result = pd.DataFrame(
            {
                "hour": np.arange(1, 8761, dtype=int),
                "timestamp": year_df.index.strftime("%Y-%m-%d %H:%M:%S+08:00"),
                "t_amb": np.round(year_df["t_amb"].values, 2),
                "rh": np.round(np.clip(year_df["rh"].values, 0.0, 100.0), 2),
                "ghi": np.round(np.clip(year_df["ghi"].values, 0.0, None), 2),
            }
        )

        return result
