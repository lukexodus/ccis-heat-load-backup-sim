"""Baseline grid-only continuous simulation engine (CORE-005 Phase 1 Exit Gate).

Implements the minimal grid-only, zero-solar, zero-battery simulation across 8,760 hours,
using a placeholder demand schedule calibrated to 159.41 kWh/m²·yr per:
- docs/prompts/CORE-005-PROMPT.md
- docs/decisions/decision-log.md [D-05], [D-06], [D-07], [D-16], [D-19], [D-20], [D-21], [D-23]
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import pandas as pd

from ccis_sim.core.models import Building, HourlyRecord, LoadTier
from ccis_sim.demand.equipment import EquipmentAudit
from ccis_sim.weather.loader import load_weather_fixture

logger = logging.getLogger(__name__)

# Fixed calibration factor derived on 2019 baseline weather fixture to hit 159.41 kWh/m²·yr (398,525 kWh)
CALIBRATION_FACTOR_2019 = 1.2285756306528773


@dataclass(frozen=True)
class BaselineMetrics:
    """Summary key performance indicators for baseline grid-only simulation."""

    annual_energy_kwh: float
    peak_demand_kw: float
    peak_timestamp: str
    peak_hour: int
    eui_kwh_per_m2_year: float
    load_factor: float
    monthly_energy_kwh: dict[int, float]

    def summary(self) -> str:
        """Format a human-readable summary of baseline performance metrics."""
        lines = [
            "=== Baseline Simulation Metrics ===",
            f"Annual Energy Consumption: {self.annual_energy_kwh:,.2f} kWh",
            f"Annual Energy Use Intensity (EUI): {self.eui_kwh_per_m2_year:.2f} kWh/m²·yr",
            f"Peak Electrical Demand: {self.peak_demand_kw:.2f} kW (Hour {self.peak_hour} at {self.peak_timestamp})",
            f"Annual Load Factor: {self.load_factor:.4f} ({self.load_factor*100:.2f}%)",
            "Monthly Consumption Breakdown:",
        ]
        month_names = [
            "Jan", "Feb", "Mar", "Apr", "May", "Jun",
            "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
        ]
        for m in range(1, 13):
            kwh = self.monthly_energy_kwh.get(m, 0.0)
            lines.append(f"  {month_names[m-1]}: {kwh:,.2f} kWh")
        return "\n".join(lines)


def compute_placeholder_demand(
    weather_df: pd.DataFrame,
    audit: EquipmentAudit,
    building: Building,
    calibration_factor: float = CALIBRATION_FACTOR_2019,
) -> list[float]:
    """Compute hourly electrical demand time-series using a lightweight placeholder model.

    NOTE per [D-23]: This is a deliberately simple placeholder model for Phase 1 baseline
    smoke-testing. Full schedule diversity and psychrometric heat response will be
    implemented by Phase 2 tracks DEM-001 and DEM-002.

    Model components:
    1. Baseload: 10% continuous 24/7 standby power (IDF switches, network, egress lighting).
    2. Occupancy Profile:
       - Weekdays (Mon-Fri): 08:00-12:00 (45%), 12:00-13:00 (30%), 13:00-17:00 (50%), 17:00-19:00 (20%).
       - Saturdays: 08:00-13:00 (15%).
       - Sundays/Nights: 0% occupancy (baseload only).
    3. Cooling Temperature Sensitivity:
       During active daytime hours (07:00-18:00 weekdays, 08:00-13:00 Saturdays), when T_amb > 24.0°C,
       cooling electrical load increases at +4.0%/°C per [D-07].
    4. Calibration:
       Pre-calibrated multiplier applied so 2019 annual total matches the 159.41 kWh/m²·yr
       target established in [D-16]/[D-19] (398,525.0 kWh).

    Args:
        weather_df: Hourly weather DataFrame containing 'timestamp' and 't_amb'.
        audit: CCIS EquipmentAudit instance providing connected power ratings.
        building: Building envelope definition providing t_base_cooling_c and cooling_sensitivity.
        calibration_factor: Multiplier to calibrate demand to target EUI (default CALIBRATION_FACTOR_2019).

    Returns:
        List of hourly gross demand in kWh for all rows in weather_df.
    """
    total_connected_kw = audit.total_connected_kw()
    cooling_connected_kw = sum(item.total_kw for item in audit.items if item.is_cooling)

    timestamps = pd.to_datetime(weather_df["timestamp"])
    hours = timestamps.dt.hour.values
    dayofweek = timestamps.dt.dayofweek.values
    temps = weather_df["t_amb"].values


    demand_series: list[float] = []

    for h, dow, temp in zip(hours, dayofweek, temps):
        f_base = 0.10  # 10% standby baseload
        f_occ = 0.0

        if dow < 5:  # Monday to Friday
            if 8 <= h < 12:
                f_occ = 0.45
            elif 12 <= h < 13:
                f_occ = 0.30
            elif 13 <= h < 17:
                f_occ = 0.50
            elif 17 <= h < 19:
                f_occ = 0.20
        elif dow == 5:  # Saturday
            if 8 <= h < 13:
                f_occ = 0.15

        # Base active schedule load (kW = kWh over 1h)
        p_sched = total_connected_kw * (f_base + f_occ)

        # Temperature-driven cooling adjustment per [D-07]
        cooling_adjustment = 0.0
        if temp > building.t_base_cooling_c and (f_occ > 0.0 or (dow < 5 and 7 <= h <= 18)):
            delta_t = temp - building.t_base_cooling_c
            cooling_adjustment = (
                cooling_connected_kw * 0.35 * building.cooling_sensitivity_per_c * delta_t
            )

        hourly_uncalibrated = p_sched + cooling_adjustment
        hourly_demand = hourly_uncalibrated * calibration_factor
        demand_series.append(hourly_demand)

    return demand_series


def simulate_baseline(
    weather_fixture: int | str | Path | pd.DataFrame = 2019,
    equipment_audit: EquipmentAudit | Path | str | None = None,
    building: Building | None = None,
    calibration_factor: float = CALIBRATION_FACTOR_2019,
) -> list[HourlyRecord]:
    """Execute grid-only baseline simulation emitting 8,760 canonical HourlyRecords.

    Args:
        weather_fixture: Calendar year (2016, 2019), path to weather CSV, or DataFrame.
        equipment_audit: EquipmentAudit instance or path to equipment CSV (defaults to CCIS fixture).
        building: Building envelope instance (defaults to standard Building()).
        calibration_factor: Calibration scaling multiplier.

    Returns:
        List of 8,760 HourlyRecord instances with exact physical energy balance.
    """
    # 1. Resolve inputs
    if isinstance(weather_fixture, pd.DataFrame):
        weather_df = weather_fixture.copy()
    else:
        weather_df = load_weather_fixture(weather_fixture)

    if equipment_audit is None:
        fixture_path = Path(__file__).resolve().parents[3] / "data/fixtures/equipment-audit-ccis.csv"
        audit = EquipmentAudit.load_from_csv(fixture_path)
    elif isinstance(equipment_audit, (str, Path)):
        audit = EquipmentAudit.load_from_csv(equipment_audit)
    else:
        audit = equipment_audit

    bldg = building or Building()

    # 2. Compute placeholder demand series
    demand_series = compute_placeholder_demand(
        weather_df=weather_df,
        audit=audit,
        building=bldg,
        calibration_factor=calibration_factor,
    )

    records: list[HourlyRecord] = []

    hours = weather_df["hour"].values
    timestamps = weather_df["timestamp"].values
    t_ambs = weather_df["t_amb"].values
    rhs = weather_df["rh"].values
    ghis = weather_df["ghi"].values

    for h, ts_raw, t_amb, rh, ghi, demand in zip(
        hours, timestamps, t_ambs, rhs, ghis, demand_series
    ):
        # Format timestamp to ISO 8601 with T
        ts = str(ts_raw).replace(" ", "T")
        demand_val = float(demand)

        # Grid-only baseline dispatch:
        # grid_import exactly equals served demand equals gross demand
        rec = HourlyRecord(
            hour=int(h),
            timestamp=ts,
            temp_ambient_c=float(t_amb),
            humidity_rel_pct=float(rh),
            ghi_w_m2=float(ghi),
            demand_gross_kwh=demand_val,
            demand_served_kwh=demand_val,
            solar_generation_kwh=0.0,
            solar_to_demand_kwh=0.0,
            solar_to_battery_kwh=0.0,
            solar_curtailed_kwh=0.0,
            battery_soc_kwh=0.0,
            battery_charge_kwh=0.0,
            battery_discharge_kwh=0.0,
            grid_import_kwh=demand_val,
            unserved_load_kwh=0.0,
            grid_available=True,
            active_load_tier=LoadTier.TIER_3_SHEDDABLE,
        )
        records.append(rec)


    return records


def compute_baseline_metrics(
    records: Sequence[HourlyRecord],
    building: Building | None = None,
) -> BaselineMetrics:
    """Calculate key headline metrics from baseline simulation records.

    Args:
        records: Sequence of HourlyRecord instances.
        building: Building instance providing gross floor area (default 2,500 m²).

    Returns:
        BaselineMetrics with annual energy, peak demand, EUI, load factor, and monthly totals.
    """
    bldg = building or Building()
    if not records:
        return BaselineMetrics(
            annual_energy_kwh=0.0,
            peak_demand_kw=0.0,
            peak_timestamp="",
            peak_hour=0,
            eui_kwh_per_m2_year=0.0,
            load_factor=0.0,
            monthly_energy_kwh={},
        )

    annual_energy = sum(r.demand_served_kwh for r in records)
    peak_rec = max(records, key=lambda r: r.demand_served_kwh)
    peak_kw = peak_rec.demand_served_kwh
    peak_ts = peak_rec.timestamp
    peak_hour = peak_rec.hour

    eui = annual_energy / bldg.gross_floor_area_m2
    total_hours = len(records)
    load_factor = annual_energy / (peak_kw * total_hours) if peak_kw > 0 and total_hours > 0 else 0.0

    # Monthly breakdown using ISO format YYYY-MM-DD
    monthly_energy: dict[int, float] = {m: 0.0 for m in range(1, 13)}
    for r in records:
        month = int(r.timestamp[5:7])
        monthly_energy[month] += r.demand_served_kwh


    return BaselineMetrics(
        annual_energy_kwh=annual_energy,
        peak_demand_kw=peak_kw,
        peak_timestamp=peak_ts,
        peak_hour=peak_hour,
        eui_kwh_per_m2_year=eui,
        load_factor=load_factor,
        monthly_energy_kwh=monthly_energy,
    )


def run_baseline_simulation(
    weather_fixture: int | str | Path | pd.DataFrame = 2019,
    equipment_audit: EquipmentAudit | Path | str | None = None,
    building: Building | None = None,
    calibration_factor: float = CALIBRATION_FACTOR_2019,
) -> tuple[list[HourlyRecord], BaselineMetrics]:
    """Convenience driver executing baseline simulation and returning records plus metrics."""
    bldg = building or Building()
    records = simulate_baseline(
        weather_fixture=weather_fixture,
        equipment_audit=equipment_audit,
        building=bldg,
        calibration_factor=calibration_factor,
    )
    metrics = compute_baseline_metrics(records=records, building=bldg)
    return records, metrics
