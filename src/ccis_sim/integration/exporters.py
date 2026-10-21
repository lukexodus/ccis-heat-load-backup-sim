"""Data exporters for CCIS microgrid simulation outputs.

Serializes simulation runs into hourly CSVs, daily aggregate CSVs, and annual summary
JSON files per task specification INT-001.3.
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from ccis_sim.core.models import HourlyRecord
from ccis_sim.integration.engine import SimulationResult


def export_hourly_csv(
    records: Sequence[HourlyRecord],
    output_path: Path | str,
) -> Path:
    """Export time-series of HourlyRecord instances to a structured CSV file.

    Parameters
    ----------
    records : Sequence[HourlyRecord]
        List or sequence of HourlyRecord objects.
    output_path : Path | str
        Destination filesystem path.

    Returns
    -------
    Path
        Resolved path of the created CSV file.
    """
    path = Path(output_path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)

    if not records:
        path.write_text("", encoding="utf-8")
        return path

    fieldnames = list(records[0].to_dict().keys())

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in records:
            writer.writerow(r.to_dict())

    return path


def export_daily_csv(
    records: Sequence[HourlyRecord],
    output_path: Path | str,
) -> Path:
    """Aggregate hourly simulation records into daily totals and export to CSV.

    Parameters
    ----------
    records : Sequence[HourlyRecord]
        List or sequence of HourlyRecord objects.
    output_path : Path | str
        Destination filesystem path.

    Returns
    -------
    Path
        Resolved path of the created CSV file.
    """
    path = Path(output_path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)

    if not records:
        path.write_text("", encoding="utf-8")
        return path

    # Group records by ISO date YYYY-MM-DD
    daily_groups: dict[str, list[HourlyRecord]] = defaultdict(list)
    for r in records:
        date_str = r.timestamp[:10]  # Extracts YYYY-MM-DD
        daily_groups[date_str].append(r)

    fieldnames = [
        "date",
        "temp_ambient_mean_c",
        "temp_ambient_max_c",
        "ghi_total_wh_m2",
        "demand_gross_kwh",
        "demand_served_kwh",
        "unserved_load_kwh",
        "solar_generation_kwh",
        "solar_to_demand_kwh",
        "solar_to_battery_kwh",
        "solar_curtailed_kwh",
        "battery_charge_kwh",
        "battery_discharge_kwh",
        "battery_soc_end_kwh",
        "grid_import_kwh",
        "outage_hours",
        "active_tier_min",
    ]

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for date_str, day_recs in sorted(daily_groups.items()):
            n_hrs = len(day_recs)
            mean_temp = sum(r.temp_ambient_c for r in day_recs) / n_hrs if n_hrs > 0 else 0.0
            max_temp = max((r.temp_ambient_c for r in day_recs), default=0.0)
            ghi_total = sum(r.ghi_w_m2 for r in day_recs)  # Sum of hourly average W/m^2 = Wh/m^2
            gross_dem = sum(r.demand_gross_kwh for r in day_recs)
            served_dem = sum(r.demand_served_kwh for r in day_recs)
            unserved = sum(r.unserved_load_kwh for r in day_recs)
            solar_gen = sum(r.solar_generation_kwh for r in day_recs)
            solar_to_dem = sum(r.solar_to_demand_kwh for r in day_recs)
            solar_to_bat = sum(r.solar_to_battery_kwh for r in day_recs)
            curtailed = sum(r.solar_curtailed_kwh for r in day_recs)
            chg = sum(r.battery_charge_kwh for r in day_recs)
            dis = sum(r.battery_discharge_kwh for r in day_recs)
            soc_end = day_recs[-1].battery_soc_kwh
            grid_imp = sum(r.grid_import_kwh for r in day_recs)
            outage_hrs = sum(1 for r in day_recs if not r.grid_available)
            tier_min = min(r.active_load_tier for r in day_recs)

            row = {
                "date": date_str,
                "temp_ambient_mean_c": round(mean_temp, 3),
                "temp_ambient_max_c": round(max_temp, 3),
                "ghi_total_wh_m2": round(ghi_total, 2),
                "demand_gross_kwh": round(gross_dem, 4),
                "demand_served_kwh": round(served_dem, 4),
                "unserved_load_kwh": round(unserved, 4),
                "solar_generation_kwh": round(solar_gen, 4),
                "solar_to_demand_kwh": round(solar_to_dem, 4),
                "solar_to_battery_kwh": round(solar_to_bat, 4),
                "solar_curtailed_kwh": round(curtailed, 4),
                "battery_charge_kwh": round(chg, 4),
                "battery_discharge_kwh": round(dis, 4),
                "battery_soc_end_kwh": round(soc_end, 4),
                "grid_import_kwh": round(grid_imp, 4),
                "outage_hours": outage_hrs,
                "active_tier_min": tier_min,
            }
            writer.writerow(row)

    return path


def export_summary_json(
    result: SimulationResult,
    output_path: Path | str,
    *,
    indent: int = 2,
) -> Path:
    """Export annual simulation summary metrics and configuration to JSON.

    Parameters
    ----------
    result : SimulationResult
        Completed simulation result instance.
    output_path : Path | str
        Destination filesystem path.
    indent : int, optional
        JSON indentation spacing (default: 2).

    Returns
    -------
    Path
        Resolved path of the created JSON file.
    """
    path = Path(output_path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)

    summary_data = result.to_dict()

    with open(path, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=indent, default=str)

    return path


def export_all(
    result: SimulationResult,
    output_dir: Path | str,
    *,
    prefix: str = "ccis_sim",
) -> dict[str, Path]:
    """Convenience exporter that writes hourly CSV, daily CSV, and summary JSON.

    Parameters
    ----------
    result : SimulationResult
        Completed simulation result instance.
    output_dir : Path | str
        Destination directory.
    prefix : str, optional
        Filename prefix for the generated files (default: 'ccis_sim').

    Returns
    -------
    dict[str, Path]
        Mapping with keys 'hourly_csv', 'daily_csv', 'summary_json'.
    """
    out_dir = Path(output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    hourly_path = export_hourly_csv(result.records, out_dir / f"{prefix}_hourly.csv")
    daily_path = export_daily_csv(result.records, out_dir / f"{prefix}_daily.csv")
    json_path = export_summary_json(result, out_dir / f"{prefix}_summary.json")

    return {
        "hourly_csv": hourly_path,
        "daily_csv": daily_path,
        "summary_json": json_path,
    }
