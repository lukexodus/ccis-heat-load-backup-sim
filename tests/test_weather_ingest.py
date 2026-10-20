"""Unit and integration test suite for NASA POWER weather ingestion pipeline.

Verifies:
- REST client parameter formatting, URL generation, and error handling.
- JSON and CSV parser data extraction and schema conformance.
- Sentinel value (-999.0) replacement and interpolation.
- Timezone alignment to PST (+08:00) including midnight year-boundary edge cases.
- Psychrometric plausibility boundary enforcement.
- Daily-to-hourly disaggregation energy conservation (sum of hourly GHI == daily total).
- Solar geometry half-sine distribution and nighttime zero-irradiance enforcement.
- Diurnal temperature sinusoidal profiling and psychrometric RH inverse coupling.
- Offline committed CSV fixtures (2016 and 2019) integrity and climatological validity.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from ccis_sim.weather import (
    BATAC_LATITUDE,
    BATAC_LONGITUDE,
    DAILY_PARAMETERS,
    HOURLY_PARAMETERS,
    DailyDisaggregator,
    NasaPowerClient,
    PsychrometricValidationError,
    WeatherParser,
    WeatherSanitizer,
    load_weather_fixture,
)

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "data" / "fixtures"
RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"


# =====================================================================
# 1. NasaPowerClient Tests
# =====================================================================

def test_client_defaults():
    """Verify default coordinates and parameter specifications."""
    assert BATAC_LATITUDE == 18.06
    assert BATAC_LONGITUDE == 120.56
    assert "T2M" in DAILY_PARAMETERS
    assert "T2M_MAX" in DAILY_PARAMETERS
    assert "T2M_MIN" in DAILY_PARAMETERS
    assert "RH2M" in DAILY_PARAMETERS
    assert "ALLSKY_SFC_SW_DWN" in DAILY_PARAMETERS
    assert "ALLSKY_SFC_SW_DWN" in HOURLY_PARAMETERS


def test_client_url_construction():
    """Verify fetch_daily and fetch_hourly construct valid request URLs."""
    client = NasaPowerClient()

    with patch.object(client, "_send_request") as mock_send:
        mock_send.return_value = {"status": "ok"}
        client.fetch_daily(start_date="20190101", end_date="20190102")
        mock_send.assert_called_once()
        called_url = mock_send.call_args[0][0]
        assert "latitude=18.0600" in called_url
        assert "longitude=120.5600" in called_url
        assert "community=RE" in called_url
        assert "start=20190101" in called_url
        assert "end=20190102" in called_url

    with patch.object(client, "_send_request") as mock_send:
        mock_send.return_value = {"status": "ok"}
        client.fetch_hourly(start_date="20190101", end_date="20190102", time_standard="LST")
        mock_send.assert_called_once()
        called_url = mock_send.call_args[0][0]
        assert "time-standard=LST" in called_url


def test_client_raw_io_roundtrip(tmp_path):
    """Verify save_raw and load_raw write and read back identical payloads."""
    payload = {"properties": {"parameter": {"T2M": {"2019010100": 24.5}}}}
    file_path = tmp_path / "raw_test.json"

    NasaPowerClient.save_raw(payload, file_path)
    assert file_path.exists()

    loaded = NasaPowerClient.load_raw(file_path)
    assert loaded == payload


def test_client_network_failure():
    """Verify ConnectionError is raised when an endpoint is unreachable."""
    client = NasaPowerClient(daily_endpoint="http://invalid.unreachable.nasa.gov/api")
    with pytest.raises(ConnectionError):
        client.fetch_daily(start_date="20190101", end_date="20190101")


# =====================================================================
# 2. WeatherParser Tests
# =====================================================================

def test_parse_hourly_json_lst():
    """Verify parse_hourly_json parses LST responses into PST DatetimeIndex."""
    synthetic_json = {
        "header": {"time_standard": "LST"},
        "properties": {
            "parameter": {
                "T2M": {"2019010100": 22.5, "2019010101": 22.1},
                "RH2M": {"2019010100": 85.0, "2019010101": 86.0},
                "ALLSKY_SFC_SW_DWN": {"2019010100": 0.0, "2019010101": 0.0},
            }
        },
    }
    df = WeatherParser.parse_hourly_json(synthetic_json)
    assert len(df) == 2
    assert list(df.columns) == ["t_amb", "rh", "ghi"]
    assert isinstance(df.index, pd.DatetimeIndex)
    assert df.index.tz is not None
    assert str(df.index[0]) == "2019-01-01 00:00:00+08:00"
    assert df.loc[df.index[0], "t_amb"] == 22.5


def test_parse_hourly_json_utc():
    """Verify parse_hourly_json parses UTC responses into UTC DatetimeIndex."""
    synthetic_json = {
        "header": {"time_standard": "UTC"},
        "properties": {
            "parameter": {
                "T2M": {"2019010100": 22.5},
                "RH2M": {"2019010100": 85.0},
                "ALLSKY_SFC_SW_DWN": {"2019010100": 0.0},
            }
        },
    }
    df = WeatherParser.parse_hourly_json(synthetic_json)
    assert len(df) == 1
    assert str(df.index[0]) == "2019-01-01 00:00:00+00:00"


def test_parse_daily_json():
    """Verify parse_daily_json extracts daily meteorological parameters."""
    synthetic_json = {
        "properties": {
            "parameter": {
                "T2M": {"20190101": 25.0},
                "T2M_MAX": {"20190101": 31.0},
                "T2M_MIN": {"20190101": 21.0},
                "RH2M": {"20190101": 78.0},
                "ALLSKY_SFC_SW_DWN": {"20190101": 5.4},
            }
        }
    }
    df = WeatherParser.parse_daily_json(synthetic_json)
    assert len(df) == 1
    assert set(df.columns) == {"t_mean", "t_max", "t_min", "rh_mean", "ghi_daily_kwh"}
    assert df.iloc[0]["t_max"] == 31.0
    assert df.iloc[0]["ghi_daily_kwh"] == 5.4


def test_parse_malformed_json():
    """Verify ValueError is raised on missing properties/parameter keys."""
    with pytest.raises(ValueError, match="Malformed NASA POWER JSON"):
        WeatherParser.parse_hourly_json({"invalid": {}})


# =====================================================================
# 3. WeatherSanitizer Tests
# =====================================================================

def test_sanitizer_filter_sentinels():
    """Verify -999 sentinels are converted to NaN while valid values remain."""
    df = pd.DataFrame(
        {
            "t_amb": [25.0, -999.0, 26.5],
            "rh": [-999.0, 80.0, 75.0],
            "ghi": [0.0, 500.0, -999.0],
        }
    )
    clean_df = WeatherSanitizer.filter_sentinels(df)
    assert np.isnan(clean_df.loc[1, "t_amb"])
    assert clean_df.loc[0, "t_amb"] == 25.0
    assert np.isnan(clean_df.loc[0, "rh"])
    assert np.isnan(clean_df.loc[2, "ghi"])


def test_sanitizer_interpolate_missing():
    """Verify linear interpolation fills NaNs correctly."""
    dates = pd.date_range("2019-01-01 00:00:00", periods=5, freq="h", tz="UTC")
    df = pd.DataFrame(
        {
            "t_amb": [20.0, np.nan, 24.0, np.nan, np.nan],
            "rh": [80.0, 82.0, np.nan, 86.0, 88.0],
        },
        index=dates,
    )
    clean = WeatherSanitizer.interpolate_missing(df)
    assert not clean.isna().any().any()
    assert np.isclose(clean.loc[dates[1], "t_amb"], 22.0)
    assert np.isclose(clean.loc[dates[3], "t_amb"], 24.0)
    assert np.isclose(clean.loc[dates[4], "t_amb"], 24.0)
    assert np.isclose(clean.loc[dates[2], "rh"], 84.0)


def test_sanitizer_timezone_alignment_and_midnight_boundary():
    """Verify timezone alignment to PST and explicit midnight boundary shift."""
    # UTC Dec 31 16:00 corresponds exactly to Jan 01 00:00 PST of the following year
    dates_utc = pd.to_datetime(["2018-12-31 16:00:00", "2018-12-31 23:00:00"], utc=True)
    df_utc = pd.DataFrame({"t_amb": [21.0, 20.0]}, index=dates_utc)

    pst_df = WeatherSanitizer.align_to_pst(df_utc)
    assert str(pst_df.index[0].tzinfo) == "UTC+08:00"
    assert pst_df["timestamp"].iloc[0] == "2019-01-01 00:00:00+08:00"
    assert pst_df["timestamp"].iloc[1] == "2019-01-01 07:00:00+08:00"

    # Also verify naive LST index localizes cleanly to PST without shift
    dates_lst = pd.date_range("2019-01-01 00:00:00", periods=2, freq="h")
    df_lst = pd.DataFrame({"t_amb": [22.0, 21.8]}, index=dates_lst)
    pst_from_lst = WeatherSanitizer.align_to_pst(df_lst)
    assert pst_from_lst["timestamp"].iloc[0] == "2019-01-01 00:00:00+08:00"


def test_sanitizer_psychrometric_validation():
    """Verify psychrometric limits raise PsychrometricValidationError."""
    good_df = pd.DataFrame({"t_amb": [25.0], "rh": [80.0], "ghi": [500.0]})
    WeatherSanitizer.validate_psychrometrics(good_df)

    # Invalid temperature (>55°C)
    bad_temp_df = pd.DataFrame({"t_amb": [60.0], "rh": [80.0], "ghi": [500.0]})
    with pytest.raises(PsychrometricValidationError, match="Ambient temperature out of bounds"):
        WeatherSanitizer.validate_psychrometrics(bad_temp_df)

    # Invalid RH (>100%)
    bad_rh_df = pd.DataFrame({"t_amb": [25.0], "rh": [105.0], "ghi": [500.0]})
    with pytest.raises(PsychrometricValidationError, match="Relative humidity out of bounds"):
        WeatherSanitizer.validate_psychrometrics(bad_rh_df)

    # Invalid negative GHI
    bad_ghi_df = pd.DataFrame({"t_amb": [25.0], "rh": [80.0], "ghi": [-10.0]})
    with pytest.raises(PsychrometricValidationError, match="Solar irradiance GHI out of bounds"):
        WeatherSanitizer.validate_psychrometrics(bad_ghi_df)


def test_sanitizer_standardize_annual_hourly():
    """Verify 8,760 standardization on non-leap and leap years."""
    pst_tz = timezone(timedelta(hours=8))

    # Test non-leap year (2019)
    dates_2019 = pd.date_range("2019-01-01 00:00:00", "2019-12-31 23:00:00", freq="h", tz=pst_tz)
    df_2019 = pd.DataFrame(
        {"t_amb": 25.0, "rh": 75.0, "ghi": 0.0},
        index=dates_2019,
    )
    std_2019 = WeatherSanitizer.standardize_annual_hourly(df_2019, target_year=2019)
    assert len(std_2019) == 8760
    assert std_2019["hour"].iloc[0] == 1
    assert std_2019["hour"].iloc[-1] == 8760
    assert std_2019["timestamp"].iloc[0] == "2019-01-01 00:00:00+08:00"
    assert std_2019["timestamp"].iloc[-1] == "2019-12-31 23:00:00+08:00"

    # Test leap year (2016): has 8,784 hours, Feb 29 omitted to yield 8,760
    dates_2016 = pd.date_range("2016-01-01 00:00:00", "2016-12-31 23:00:00", freq="h", tz=pst_tz)
    assert len(dates_2016) == 8784
    df_2016 = pd.DataFrame(
        {"t_amb": 26.0, "rh": 70.0, "ghi": 0.0},
        index=dates_2016,
    )
    std_2016 = WeatherSanitizer.standardize_annual_hourly(df_2016, target_year=2016, drop_leap_day=True)
    assert len(std_2016) == 8760
    assert not std_2016["timestamp"].str.contains("2016-02-29").any()


# =====================================================================
# 4. DailyDisaggregator Tests
# =====================================================================

def test_daily_disaggregation_energy_conservation():
    """Verify exact daily energy conservation: sum(hourly GHI) == daily insolation."""
    disagg = DailyDisaggregator(latitude=BATAC_LATITUDE, longitude=BATAC_LONGITUDE)
    test_date = datetime(2019, 4, 15)

    for ghi_kwh in [0.0, 1.25, 4.50, 6.85, 7.50]:
        res = disagg.disaggregate_day(
            date=test_date,
            t_mean=28.5,
            t_max=34.0,
            t_min=24.0,
            rh_mean=72.0,
            ghi_daily_kwh=ghi_kwh,
        )
        ghi_hourly = res["ghi"]
        integrated_wh = np.sum(ghi_hourly)
        expected_wh = ghi_kwh * 1000.0
        assert np.isclose(integrated_wh, expected_wh, atol=0.05), (
            f"Energy conservation violation for {ghi_kwh} kWh/m2: "
            f"integrated={integrated_wh} Wh vs expected={expected_wh} Wh"
        )


def test_daily_disaggregation_solar_geometry_night_zero():
    """Verify that irradiance is exactly zero at night (before dawn and after dusk)."""
    disagg = DailyDisaggregator(latitude=BATAC_LATITUDE, longitude=BATAC_LONGITUDE)
    res = disagg.disaggregate_day(
        date=datetime(2019, 6, 21),
        t_mean=28.0,
        t_max=33.0,
        t_min=23.0,
        rh_mean=75.0,
        ghi_daily_kwh=5.5,
    )
    ghi = res["ghi"]
    assert np.all(ghi[:5] == 0.0)
    assert np.all(ghi[20:] == 0.0)
    assert ghi[12] > 0.0
    assert ghi[12] == np.max(ghi)


def test_daily_disaggregation_temperature_profile():
    """Verify diurnal sinusoidal temperature bounded strictly within [t_min, t_max]."""
    disagg = DailyDisaggregator(latitude=BATAC_LATITUDE, peak_temp_hour=14.0)
    res = disagg.disaggregate_day(
        date=datetime(2019, 4, 1),
        t_mean=27.0,
        t_max=35.0,
        t_min=22.0,
        rh_mean=70.0,
        ghi_daily_kwh=6.0,
    )
    t_hourly = res["t_amb"]
    assert np.all(t_hourly >= 22.0 - 0.05)
    assert np.all(t_hourly <= 35.0 + 0.05)
    assert np.argmax(t_hourly) in [13, 14]
    assert np.argmin(t_hourly) in [5, 6]


def test_daily_disaggregation_relative_humidity_coupling():
    """Verify RH maintains inverse diurnal coupling with temperature via vapor pressure."""
    disagg = DailyDisaggregator(latitude=BATAC_LATITUDE)
    res = disagg.disaggregate_day(
        date=datetime(2019, 4, 1),
        t_mean=28.0,
        t_max=35.0,
        t_min=23.0,
        rh_mean=75.0,
        ghi_daily_kwh=6.0,
    )
    rh_hourly = res["rh"]
    t_hourly = res["t_amb"]

    assert np.all(rh_hourly >= 0.0)
    assert np.all(rh_hourly <= 100.0)

    peak_temp_idx = np.argmax(t_hourly)
    min_rh_idx = np.argmin(rh_hourly)
    assert abs(peak_temp_idx - min_rh_idx) <= 1


def test_daily_disaggregate_dataframe():
    """Verify multi-day daily DataFrame disaggregation into 24*N hourly records."""
    dates = pd.date_range("2019-01-01", periods=3, freq="D")
    daily_df = pd.DataFrame(
        {
            "t_mean": [25.0, 26.0, 24.5],
            "t_max": [31.0, 32.0, 30.5],
            "t_min": [21.0, 22.0, 20.5],
            "rh_mean": [78.0, 75.0, 80.0],
            "ghi_daily_kwh": [5.2, 5.5, 4.8],
        },
        index=dates,
    )
    disagg = DailyDisaggregator()
    hourly_df = disagg.disaggregate_dataframe(daily_df)

    assert len(hourly_df) == 3 * 24
    assert list(hourly_df["hour"]) == list(range(1, 73))
    assert list(hourly_df.columns) == ["hour", "timestamp", "t_amb", "rh", "ghi"]


# =====================================================================
# 5. Offline Fixtures & Climatological Plausibility Tests
# =====================================================================

@pytest.mark.parametrize("year", [2016, 2019])
def test_committed_fixtures_structure(year: int):
    """Verify offline CSV fixture files exist, load cleanly, and conform to 8,760 schema."""
    df = load_weather_fixture(year)
    assert len(df) == 8760
    assert list(df.columns) == ["hour", "timestamp", "t_amb", "rh", "ghi"]
    assert df["hour"].iloc[0] == 1
    assert df["hour"].iloc[-1] == 8760
    assert not df.isna().any().any()
    assert (df["ghi"] >= 0.0).all()
    assert (df["rh"] >= 0.0).all() and (df["rh"] <= 100.0).all()


def test_committed_fixtures_climate_comparison():
    """Verify 2016 vs 2019 climatological difference (2016 hot year vs 2019 baseline)."""
    df_2016 = load_weather_fixture(2016)
    df_2019 = load_weather_fixture(2019)

    t_max_2016 = df_2016["t_amb"].max()
    t_max_2019 = df_2019["t_amb"].max()
    t_mean_2016 = df_2016["t_amb"].mean()
    t_mean_2019 = df_2019["t_amb"].mean()

    assert t_max_2016 > t_max_2019, f"Expected 2016 max ({t_max_2016}) > 2019 max ({t_max_2019})"
    assert t_mean_2016 > t_mean_2019, f"Expected 2016 mean ({t_mean_2016}) > 2019 mean ({t_mean_2019})"
    assert t_max_2016 >= 36.0, f"2016 peak heatwave temperature ({t_max_2016}°C) should exceed 36°C"

    # Annual solar yield benchmark for Batac: ~1,800 to 2,000 kWh/m^2/year
    ghi_annual_2016 = df_2016["ghi"].sum() / 1000.0
    ghi_annual_2019 = df_2019["ghi"].sum() / 1000.0
    assert 1800.0 <= ghi_annual_2016 <= 2000.0
    assert 1800.0 <= ghi_annual_2019 <= 2000.0


def test_raw_files_exist():
    """Verify raw API JSON payloads are persisted in data/raw/."""
    assert (RAW_DIR / "nasa_power_hourly_batac_2016.json").exists()
    assert (RAW_DIR / "nasa_power_hourly_batac_2019.json").exists()
    assert (RAW_DIR / "nasa_power_daily_batac_2016.json").exists()
    assert (RAW_DIR / "nasa_power_daily_batac_2019.json").exists()
