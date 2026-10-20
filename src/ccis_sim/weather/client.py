"""NASA POWER REST API client for fetching meteorological time series.

Target coordinates: Batac, Ilocos Norte (18.06°N, 120.56°E).
Provides methods for querying NASA POWER hourly (2001–present) and daily (1981–present)
point APIs, caching raw JSON responses, and offline fallback loading.
"""

from __future__ import annotations

import json
import logging
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Sequence

logger = logging.getLogger(__name__)

BATAC_LATITUDE: float = 18.06
BATAC_LONGITUDE: float = 120.56

NASA_POWER_BASE_URL: str = "https://power.larc.nasa.gov/api/temporal"
DEFAULT_DAILY_ENDPOINT: str = f"{NASA_POWER_BASE_URL}/daily/point"
DEFAULT_HOURLY_ENDPOINT: str = f"{NASA_POWER_BASE_URL}/hourly/point"

DAILY_PARAMETERS: tuple[str, ...] = (
    "T2M",
    "T2M_MAX",
    "T2M_MIN",
    "RH2M",
    "ALLSKY_SFC_SW_DWN",
)

HOURLY_PARAMETERS: tuple[str, ...] = (
    "T2M",
    "RH2M",
    "ALLSKY_SFC_SW_DWN",
)


class NasaPowerClient:
    """REST API client for NASA POWER agroclimatology & renewable energy data."""

    def __init__(
        self,
        daily_endpoint: str = DEFAULT_DAILY_ENDPOINT,
        hourly_endpoint: str = DEFAULT_HOURLY_ENDPOINT,
        timeout: float = 60.0,
    ) -> None:
        self.daily_endpoint = daily_endpoint
        self.hourly_endpoint = hourly_endpoint
        self.timeout = timeout

    def fetch_daily(
        self,
        latitude: float = BATAC_LATITUDE,
        longitude: float = BATAC_LONGITUDE,
        start_date: str = "20190101",
        end_date: str = "20191231",
        parameters: Sequence[str] = DAILY_PARAMETERS,
        community: str = "RE",
    ) -> dict[str, Any]:
        """Fetch daily time-series from NASA POWER API.

        Args:
            latitude: Target latitude in decimal degrees.
            longitude: Target longitude in decimal degrees.
            start_date: Start date string formatted as 'YYYYMMDD'.
            end_date: End date string formatted as 'YYYYMMDD'.
            parameters: Meteorological parameters to query.
            community: Community code ('RE' for Renewable Energy).

        Returns:
            Decoded JSON dictionary from NASA POWER response.
        """
        params = {
            "parameters": ",".join(parameters),
            "community": community,
            "longitude": f"{longitude:.4f}",
            "latitude": f"{latitude:.4f}",
            "start": start_date,
            "end": end_date,
            "format": "JSON",
        }
        url = f"{self.daily_endpoint}?{urllib.parse.urlencode(params)}"
        logger.info("Requesting NASA POWER daily data from: %s", url)
        return self._send_request(url)

    def fetch_hourly(
        self,
        latitude: float = BATAC_LATITUDE,
        longitude: float = BATAC_LONGITUDE,
        start_date: str = "20190101",
        end_date: str = "20191231",
        parameters: Sequence[str] = HOURLY_PARAMETERS,
        community: str = "RE",
        time_standard: str = "LST",
    ) -> dict[str, Any]:
        """Fetch hourly time-series from NASA POWER API.

        Args:
            latitude: Target latitude in decimal degrees.
            longitude: Target longitude in decimal degrees.
            start_date: Start date string formatted as 'YYYYMMDD'.
            end_date: End date string formatted as 'YYYYMMDD'.
            parameters: Meteorological parameters to query.
            community: Community code ('RE' for Renewable Energy).
            time_standard: Time standard ('LST' or 'UTC').

        Returns:
            Decoded JSON dictionary from NASA POWER response.
        """
        params = {
            "parameters": ",".join(parameters),
            "community": community,
            "longitude": f"{longitude:.4f}",
            "latitude": f"{latitude:.4f}",
            "start": start_date,
            "end": end_date,
            "time-standard": time_standard,
            "format": "JSON",
        }
        url = f"{self.hourly_endpoint}?{urllib.parse.urlencode(params)}"
        logger.info("Requesting NASA POWER hourly data from: %s", url)
        return self._send_request(url)

    def fetch_annual_hourly(
        self,
        year: int,
        latitude: float = BATAC_LATITUDE,
        longitude: float = BATAC_LONGITUDE,
        parameters: Sequence[str] = HOURLY_PARAMETERS,
        community: str = "RE",
        time_standard: str = "LST",
    ) -> dict[str, Any]:
        """Fetch hourly series spanning a full annual calendar cycle for Batac.

        When time_standard is 'LST' (the NASA POWER default), hours are indexed in
        Local Solar Time. For Batac (120.56°E, ~0.56° from the 120°E PST central meridian),
        LST is within 2.2 minutes of Philippine Standard Time (PST = UTC+8). The query
        runs from YYYY0101 to YYYY1231.

        When time_standard is 'UTC', Jan 1 00:00 PST corresponds to Dec 31 16:00 UTC,
        so the query spans from (YYYY-1)1231 to YYYY1231.
        """
        if time_standard.upper() == "UTC":
            start_date = f"{year - 1}1231"
            end_date = f"{year}1231"
        else:
            start_date = f"{year}0101"
            end_date = f"{year}1231"

        return self.fetch_hourly(
            latitude=latitude,
            longitude=longitude,
            start_date=start_date,
            end_date=end_date,
            parameters=parameters,
            community=community,
            time_standard=time_standard,
        )

    def _send_request(self, url: str) -> dict[str, Any]:
        """Execute HTTP request with custom User-Agent and JSON decoding."""
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "ccis-heat-load-backup-sim/0.1.0 (Batac CCIS M&S Project)",
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                content = resp.read().decode("utf-8")
                return json.loads(content)
        except urllib.error.URLError as exc:
            logger.error("Failed to fetch data from NASA POWER: %s", exc)
            raise ConnectionError(f"NASA POWER API request failed: {exc}") from exc

    @staticmethod
    def save_raw(data: dict[str, Any], filepath: str | Path) -> Path:
        """Persist raw API JSON response to disk."""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        logger.info("Saved raw NASA POWER payload to %s", path)
        return path

    @staticmethod
    def load_raw(filepath: str | Path) -> dict[str, Any]:
        """Load raw API JSON response from disk (offline fallback)."""
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"Raw weather file not found at: {path}")
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
