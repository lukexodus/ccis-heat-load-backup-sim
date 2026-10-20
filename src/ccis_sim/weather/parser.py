"""Parser for NASA POWER meteorological JSON and CSV payloads.

Transforms raw NASA POWER responses into pandas DataFrames with
validated types, canonical parameter mappings, and timezone awareness.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from io import StringIO
from pathlib import Path
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

# Philippine Standard Time is UTC+8
PST_OFFSET = timezone(timedelta(hours=8))

# Canonical mapping for hourly parameters
HOURLY_RENAME_MAP: dict[str, str] = {
    "T2M": "t_amb",
    "RH2M": "rh",
    "ALLSKY_SFC_SW_DWN": "ghi",
}

# Canonical mapping for daily parameters
DAILY_RENAME_MAP: dict[str, str] = {
    "T2M": "t_mean",
    "T2M_MAX": "t_max",
    "T2M_MIN": "t_min",
    "RH2M": "rh_mean",
    "ALLSKY_SFC_SW_DWN": "ghi_daily_kwh",
}


class WeatherParser:
    """Parses raw NASA POWER responses into structured DataFrames."""

    @staticmethod
    def parse_hourly_json(data: dict[str, Any]) -> pd.DataFrame:
        """Parse raw NASA POWER hourly JSON response.

        NASA POWER hourly JSON has format:
            data["properties"]["parameter"][param_name]["YYYYMMDDHH"] = float_val
        Header defines the time standard:
            data["header"]["time_standard"] -> 'LST' (default) or 'UTC'

        Returns:
            pd.DataFrame with timezone-aware DatetimeIndex (PST if LST, UTC if UTC)
            and columns: ['t_amb', 'rh', 'ghi'].
        """
        if "properties" not in data or "parameter" not in data["properties"]:
            raise ValueError("Malformed NASA POWER JSON: missing 'properties.parameter' key.")

        header = data.get("header", {})
        time_standard = header.get("time_standard", "LST").upper()

        param_dict = data["properties"]["parameter"]
        df_dict: dict[str, dict[str, float]] = {}

        for param_key, series_data in param_dict.items():
            canonical_name = HOURLY_RENAME_MAP.get(param_key, param_key.lower())
            df_dict[canonical_name] = series_data

        df = pd.DataFrame(df_dict)

        # Parse timestamp index formatted as YYYYMMDDHH
        # If time_standard is LST, Batac (120.56°E) is local standard time (PST = UTC+8)
        raw_dt = pd.to_datetime(df.index, format="%Y%m%d%H")
        if time_standard == "UTC":
            df.index = raw_dt.tz_localize("UTC")
            df.index.name = "timestamp_utc"
        else:
            # LST for Batac (120.56°E, ~0.56° from 120°E central meridian) is localized to PST
            df.index = raw_dt.tz_localize(PST_OFFSET)
            df.index.name = "timestamp_pst"

        df = df.sort_index()

        # Enforce numeric float dtype
        for col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        return df

    @staticmethod
    def parse_daily_json(data: dict[str, Any]) -> pd.DataFrame:
        """Parse raw NASA POWER daily JSON response.

        NASA POWER daily JSON has format:
            data["properties"]["parameter"][param_name]["YYYYMMDD"] = float_val

        Returns:
            pd.DataFrame with DatetimeIndex and daily columns:
            ['t_mean', 't_max', 't_min', 'rh_mean', 'ghi_daily_kwh'].
        """
        if "properties" not in data or "parameter" not in data["properties"]:
            raise ValueError("Malformed NASA POWER JSON: missing 'properties.parameter' key.")

        param_dict = data["properties"]["parameter"]
        df_dict: dict[str, dict[str, float]] = {}

        for param_key, series_data in param_dict.items():
            canonical_name = DAILY_RENAME_MAP.get(param_key, param_key.lower())
            df_dict[canonical_name] = series_data

        df = pd.DataFrame(df_dict)
        df.index = pd.to_datetime(df.index, format="%Y%m%d")
        df.index.name = "date"
        df = df.sort_index()

        for col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        return df

    @staticmethod
    def parse_csv(filepath_or_buffer: str | Path | StringIO) -> pd.DataFrame:
        """Parse CSV weather fixture file into a pandas DataFrame."""
        df = pd.read_csv(filepath_or_buffer)
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
        return df
