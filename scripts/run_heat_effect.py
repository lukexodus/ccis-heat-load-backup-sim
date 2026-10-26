#!/usr/bin/env python3
"""Generate results/heat_effect.md — DOC-FIX-001 Part C heat-effect numbers.

Calls existing demand/simulation functions only. No new model logic.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from ccis_sim.core.models import Building
from ccis_sim.demand.cooling import compute_cooling_demand
from ccis_sim.demand.equipment import EquipmentAudit
from ccis_sim.demand.non_cooling import compute_non_cooling_demand
from ccis_sim.demand.schedule import AcademicCalendar, build_occupancy_schedule
from ccis_sim.integration.engine import SimulationConfig, simulate
from ccis_sim.integration.scenarios import compute_bill_calibrated_scale
from ccis_sim.weather.loader import load_weather_fixture


def _case(year: int, temp_offset_c: float) -> dict:
    """Compute annual and daily demand figures for one weather case."""
    weather = load_weather_fixture(year).copy()
    if temp_offset_c != 0.0:
        weather["t_amb"] = weather["t_amb"] + temp_offset_c

    audit = EquipmentAudit.load_from_csv("data/fixtures/equipment-audit-ccis.csv")
    building = Building()
    calendar = AcademicCalendar()
    schedule = build_occupancy_schedule(weather["timestamp"], calendar=calendar)

    cooling = compute_cooling_demand(weather, schedule.occupancy_fraction, audit, building)
    non_cooling = compute_non_cooling_demand(schedule, audit, building)

    cooling_hourly = cooling.tier1_kwh + cooling.tier2_kwh + cooling.tier3_kwh
    non_cooling_hourly = non_cooling.tier1_kwh + non_cooling.tier2_kwh + non_cooling.tier3_kwh
    total_hourly = cooling_hourly + non_cooling_hourly

    result = simulate(
        SimulationConfig(
            solar_kwp=0.0,
            battery_kwh=0.0,
            weather_year=year,
            temp_offset_c=temp_offset_c,
            outage_regime="normal",
            seed=0,
            demand_scale=1.0,
        ),
        verify=False,
    )

    frame = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(weather["timestamp"]),
            "t_amb": weather["t_amb"].to_numpy(),
            "total_kwh": total_hourly,
            "is_class_day": schedule.is_class_day,
        }
    )
    frame["date"] = frame["timestamp"].dt.date
    daily = (
        frame.groupby("date", as_index=False)
        .agg(
            daily_kwh=("total_kwh", "sum"),
            mean_temp_c=("t_amb", "mean"),
            school_day=("is_class_day", "any"),
        )
        .sort_values("date")
    )

    annual = float(total_hourly.sum())
    cooling_annual = float(cooling_hourly.sum())
    non_cooling_annual = float(non_cooling_hourly.sum())

    school_days = daily[daily["school_day"]]
    regression = stats.linregress(school_days["mean_temp_c"], school_days["daily_kwh"])

    return {
        "year": year,
        "temp_offset_c": temp_offset_c,
        "annual_kwh": annual,
        "cooling_kwh": cooling_annual,
        "non_cooling_kwh": non_cooling_annual,
        "cooling_share_pct": 100.0 * cooling_annual / annual if annual else 0.0,
        "peak_kw": float(result.metrics["peak_demand_kw"]),
        "peak_timestamp": str(result.metrics["peak_timestamp"]),
        "daily_mean_hot_ge30": float(daily.loc[daily["mean_temp_c"] >= 30.0, "daily_kwh"].mean()),
        "daily_mean_cool_lt26": float(daily.loc[daily["mean_temp_c"] < 26.0, "daily_kwh"].mean()),
        "days_ge34": int((daily["mean_temp_c"] >= 34.0).sum()),
        "reg_slope": float(regression.slope),
        "reg_intercept": float(regression.intercept),
        "reg_r2": float(regression.rvalue**2),
        "reg_n": int(school_days.shape[0]),
        "n_days": int(daily.shape[0]),
        "daily": daily,
    }


def _table_row(case: dict, scale: float) -> str:
    return (
        f"| {case['year']}"
        f"{' +2 °C' if case['temp_offset_c'] else ''} "
        f"| {case['annual_kwh'] * scale:,.0f} "
        f"| {case['cooling_kwh'] * scale:,.0f} "
        f"| {case['non_cooling_kwh'] * scale:,.0f} "
        f"| {case['cooling_share_pct']:.1f}% "
        f"| {case['peak_kw'] * scale:,.1f} "
        f"| {case['peak_timestamp']} "
        f"| {case['daily_mean_hot_ge30'] * scale:,.1f} "
        f"| {case['daily_mean_cool_lt26'] * scale:,.1f} "
        f"| {case['days_ge34']} |"
    )


def main() -> None:
    cases = [_case(2019, 0.0), _case(2019, 2.0), _case(2016, 0.0)]
    bill_scale = compute_bill_calibrated_scale()
    base = cases[0]

    lines = [
        "# Heat-Effect Numbers (DOC-FIX-001 Part C)",
        "",
        "> Grid-only runs (solar 0, battery 0, bottom-up demand, seed 0).",
        "> Cooling kWh is computed by calling `compute_cooling_demand` with the same inputs.",
        "> Daily means use all calendar days; the regression uses school days only.",
        "> The 2016 weather case keeps the default (`AcademicCalendar(year=2019)`) calendar,",
        "> matching what `simulate()` does.",
        "",
        "## Table 1 — Bottom-up demand (scale = 1.0)",
        "",
        "| Weather case | Annual kWh | Cooling kWh | Non-cooling kWh | Cooling share | Peak kW | Peak timestamp | Mean daily kWh, days ≥30 °C | Mean daily kWh, days <26 °C | Days ≥34 °C |",
        "| :--- | ---: | ---: | ---: | ---: | ---: | :--- | ---: | ---: | ---: |",
    ]
    for case in cases:
        lines.append(_table_row(case, 1.0))

    lines += [
        "",
        "### Daily regression — 2019, school days only",
        "",
        "| Quantity | Value |",
        "| :--- | ---: |",
        f"| Slope | {base['reg_slope']:.4f} kWh/°C |",
        f"| Intercept | {base['reg_intercept']:,.2f} kWh/day |",
        f"| R² | {base['reg_r2']:.4f} |",
        f"| n (school days) | {base['reg_n']} |",
        "",
        f"## Table 2 — Bill-calibrated demand (scale ≈ {bill_scale:.4f})",
        "",
        "| Weather case | Annual kWh | Cooling kWh | Non-cooling kWh | Cooling share | Peak kW | Peak timestamp | Mean daily kWh, days ≥30 °C | Mean daily kWh, days <26 °C | Days ≥34 °C |",
        "| :--- | ---: | ---: | ---: | ---: | ---: | :--- | ---: | ---: | ---: |",
    ]
    for case in cases:
        lines.append(_table_row(case, bill_scale))

    lines += [
        "",
        "### Daily regression — 2019, school days only (bill-calibrated)",
        "",
        "| Quantity | Value |",
        "| :--- | ---: |",
        f"| Slope | {base['reg_slope'] * bill_scale:.4f} kWh/°C |",
        f"| Intercept | {base['reg_intercept'] * bill_scale:,.2f} kWh/day |",
        f"| R² | {base['reg_r2']:.4f} |",
        f"| n (school days) | {base['reg_n']} |",
        "",
        "## Notes",
        "",
        f"- 2019 baseline: {base['annual_kwh']:,.0f} kWh/yr; cooling is {base['cooling_share_pct']:.1f}% of annual demand.",
        f"- +2 °C perturbation: {cases[1]['annual_kwh']:,.0f} kWh/yr "
        f"({cases[1]['annual_kwh'] - base['annual_kwh']:+,.0f} kWh, "
        f"{100.0 * (cases[1]['annual_kwh'] / base['annual_kwh'] - 1.0):+.2f}%).",
        f"- 2016 weather: {cases[2]['annual_kwh']:,.0f} kWh/yr "
        f"({cases[2]['annual_kwh'] - base['annual_kwh']:+,.0f} kWh, "
        f"{100.0 * (cases[2]['annual_kwh'] / base['annual_kwh'] - 1.0):+.2f}%).",
        f"- Regression slope is a simulation-conditional association, not a causal estimate.",
        "",
    ]

    output = Path("results/heat_effect.md")
    output.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {output}")


if __name__ == "__main__":
    main()
