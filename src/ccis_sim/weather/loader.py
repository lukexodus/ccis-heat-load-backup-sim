"""Loader utility for cached offline weather CSV fixtures."""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

REQUIRED_COLUMNS = ("hour", "timestamp", "t_amb", "rh", "ghi")


def _find_fixture_path(year_or_path: int | str | Path) -> Path:
    """Resolve year integer or filename path to an absolute Path."""
    if isinstance(year_or_path, int) or (isinstance(year_or_path, str) and year_or_path.isdigit()):
        year = int(year_or_path)
        filename = f"batac-weather-hourly-{year}.csv"
        # Check standard relative paths
        candidates = [
            Path("data/fixtures") / filename,
            Path(__file__).resolve().parents[3] / "data" / "fixtures" / filename,
        ]
        for c in candidates:
            if c.exists():
                return c.resolve()
        raise FileNotFoundError(f"Fixture for year {year} not found. Searched: {candidates}")

    path = Path(year_or_path)
    if not path.exists():
        repo_candidate = Path(__file__).resolve().parents[3] / path
        if repo_candidate.exists():
            return repo_candidate.resolve()
        raise FileNotFoundError(f"Weather fixture file not found: {path}")
    return path.resolve()


def load_weather_fixture(
    year_or_path: int | str | Path,
    expected_rows: int = 8760,
) -> pd.DataFrame:
    """Load and validate an offline hourly weather fixture CSV.

    Args:
        year_or_path: Calendar year (e.g., 2016, 2019) or path to CSV file.
        expected_rows: Expected row count (default 8,760 for annual simulation).

    Returns:
        pd.DataFrame containing verified weather columns:
        ['hour', 'timestamp', 't_amb', 'rh', 'ghi'].
    """
    path = _find_fixture_path(year_or_path)
    logger.info("Loading weather fixture from: %s", path)

    df = pd.read_csv(path)

    missing_cols = set(REQUIRED_COLUMNS) - set(df.columns)
    if missing_cols:
        raise ValueError(f"Weather fixture {path.name} missing required columns: {missing_cols}")

    if expected_rows is not None and len(df) != expected_rows:
        raise ValueError(
            f"Weather fixture {path.name} contains {len(df)} rows, expected {expected_rows}."
        )

    for col in ("t_amb", "rh", "ghi"):
        if df[col].isna().any():
            raise ValueError(f"Weather fixture {path.name} contains NaN in column '{col}'.")
        if (df[col] == -999.0).any():
            raise ValueError(f"Weather fixture {path.name} contains un-sanitized sentinel -999 in '{col}'.")

    df["hour"] = df["hour"].astype(int)
    df["t_amb"] = df["t_amb"].astype(float)
    df["rh"] = df["rh"].astype(float)
    df["ghi"] = df["ghi"].astype(float)

    return df
