"""Command-line interface (CLI) for the CCIS Heat, Load and Backup Power Simulation.

Entry point: `ccis-sim` (or `python -m ccis_sim.cli`).
Provides subcommands:
  - `run`: Execute an integrated annual simulation run with configurable system sizing,
           weather regime, and reliability conditions per INT-001.2.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ccis_sim.integration.engine import SimulationConfig, simulate
from ccis_sim.integration.exporters import export_all


def _format_summary_table(metrics: dict[str, float | int | str], config: SimulationConfig) -> str:
    """Format key simulation metrics into an ASCII report table."""
    lines = [
        "=" * 72,
        "   CCIS HEAT, LOAD AND BACKUP POWER SIMULATION — ANNUAL RUN SUMMARY",
        "=" * 72,
        f" Configuration:",
        f"   Solar PV Capacity:       {config.solar_kwp:8.2f} kWp",
        f"   Battery BESS Capacity:   {config.battery_kwh:8.2f} kWh",
        f"   Weather Reference Year:  {config.weather_year:8d} (offset: {config.temp_offset_c:+.1f}°C)",
        f"   Outage Arrival Regime:   {config.outage_regime:>8s} (seed: {config.seed})",
        f"   Tier 2 Shed SoC Floor:   {config.tier2_shed_soc_fraction * 100:8.1f}%",
        f"   Emergency Reserve Ratio: {config.emergency_reserve_pct * 100:8.1f}%",
        "-" * 72,
        f" Energy Balance Totals:",
        f"   Gross Demand:            {metrics.get('annual_gross_demand_kwh', 0.0):12,.2f} kWh",
        f"   Served Demand:           {metrics.get('annual_served_demand_kwh', 0.0):12,.2f} kWh",
        f"   Unserved Deficit:        {metrics.get('annual_unserved_load_kwh', 0.0):12,.2f} kWh",
        f"   Utility Grid Import:     {metrics.get('annual_grid_import_kwh', 0.0):12,.2f} kWh",
        f"   Solar Generation:        {metrics.get('annual_solar_generation_kwh', 0.0):12,.2f} kWh",
        f"   Solar Direct to Demand:  {metrics.get('annual_solar_to_demand_kwh', 0.0):12,.2f} kWh",
        f"   Solar to Battery:        {metrics.get('annual_solar_to_battery_kwh', 0.0):12,.2f} kWh",
        f"   Solar Curtailed:         {metrics.get('annual_solar_curtailed_kwh', 0.0):12,.2f} kWh",
        f"   Battery Charge:          {metrics.get('annual_battery_charge_kwh', 0.0):12,.2f} kWh",
        f"   Battery Discharge:       {metrics.get('annual_battery_discharge_kwh', 0.0):12,.2f} kWh",
        "-" * 72,
        f" Performance & Reliability:",
        f"   Peak Gross Demand:       {metrics.get('peak_demand_kw', 0.0):12.2f} kW at hour {metrics.get('peak_hour', 0)}",
        f"   Facility EUI (Served):   {metrics.get('eui_kwh_per_m2_year', 0.0):12.2f} kWh/m²·yr",
        f"   Facility EUI (Gross):    {metrics.get('gross_eui_kwh_per_m2_year', 0.0):12.2f} kWh/m²·yr",
        f"   Solar Self-Sufficiency:  {metrics.get('self_sufficiency_pct', 0.0):12.2f} %",
        f"   Solar Specific Yield:    {metrics.get('solar_specific_yield_kwh_per_kwp', 0.0):12.2f} kWh/kWp",
        f"   Total Outage Hours:      {metrics.get('total_outage_hours', 0):12d} hours",
        f"   Tier 1 (Critical) Unserved: {metrics.get('unserved_tier1_kwh', 0.0):9,.2f} kWh (Covered: {metrics.get('outage_tier1_coverage_pct', 0.0):5.1f}%)",
        f"   Tier 2 (Essential) Unserved: {metrics.get('unserved_tier2_kwh', 0.0):8,.2f} kWh (Covered: {metrics.get('outage_tier2_coverage_pct', 0.0):5.1f}%)",
        f"   Tier 3 (Sheddable) Unserved: {metrics.get('unserved_tier3_kwh', 0.0):8,.2f} kWh (Covered: {metrics.get('outage_tier3_coverage_pct', 0.0):5.1f}%)",
        "-" * 72,
        f" Conservation Invariants:",
        f"   Max Hourly Residual:     {metrics.get('max_energy_balance_residual_kwh', 0.0):12.4e} kWh (limit: 1.0000e-05)",
        f"   Cumulative Net Drift:    {metrics.get('cumulative_net_drift_kwh', 0.0):12.4e} kWh",
        "=" * 72,
    ]
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the ccis-sim CLI."""
    parser = argparse.ArgumentParser(
        prog="ccis-sim",
        description="CCIS Microgrid Heat, Load and Backup Power Simulation Engine",
    )
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # 'run' subcommand
    run_parser = subparsers.add_parser(
        "run",
        help="Execute an integrated annual simulation run",
    )
    run_parser.add_argument(
        "--solar-kwp",
        type=float,
        default=0.0,
        help="Solar PV DC capacity in kWp (0 to 200, default: 0.0)",
    )
    run_parser.add_argument(
        "--battery-kwh",
        type=float,
        default=0.0,
        help="Battery storage nominal capacity in kWh (0 to 200, default: 0.0)",
    )
    run_parser.add_argument(
        "--weather",
        type=int,
        choices=[2016, 2019],
        default=2019,
        help="Weather dataset year (2019 baseline or 2016 hot year, default: 2019)",
    )
    run_parser.add_argument(
        "--temp-offset",
        type=float,
        default=0.0,
        help="Additive dry-bulb temperature offset in °C (default: 0.0)",
    )
    run_parser.add_argument(
        "--outages",
        type=str,
        choices=["normal", "typhoon"],
        default="normal",
        help="Utility grid outage arrival regime ('normal' or 'typhoon', default: 'normal')",
    )
    run_parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Deterministic random seed for stochastic outage generation (default: 42)",
    )
    run_parser.add_argument(
        "--initial-soc",
        type=float,
        default=None,
        help="Initial battery state-of-charge in kWh (default: full battery capacity)",
    )
    run_parser.add_argument(
        "--tier2-shed-soc",
        type=float,
        default=0.20,
        help="Battery SoC fraction threshold below which Tier 2 is shed (default: 0.20)",
    )
    run_parser.add_argument(
        "--emergency-reserve",
        type=float,
        default=0.20,
        help="Battery operational emergency reserve fraction (default: 0.20)",
    )
    run_parser.add_argument(
        "--allow-emergency-drawdown",
        action="store_true",
        help="Allow battery drawdown below 10%% min_soc during emergency blackouts",
    )
    run_parser.add_argument(
        "--out",
        "-o",
        type=str,
        default="results",
        help="Output directory to save simulation files (default: 'results')",
    )
    run_parser.add_argument(
        "--prefix",
        type=str,
        default="ccis_sim",
        help="Prefix for generated output filenames (default: 'ccis_sim')",
    )
    run_parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress printing the summary table to stdout",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI execution entrypoint."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.subcommand == "run":
        config = SimulationConfig(
            solar_kwp=args.solar_kwp,
            battery_kwh=args.battery_kwh,
            weather_year=args.weather,
            temp_offset_c=args.temp_offset,
            outage_regime=args.outages,
            seed=args.seed,
            initial_soc_kwh=args.initial_soc,
            tier2_shed_soc_fraction=args.tier2_shed_soc,
            emergency_reserve_pct=args.emergency_reserve,
            allow_emergency_drawdown=args.allow_emergency_drawdown,
        )

        # Execute simulation
        result = simulate(config)

        # Output to disk
        out_paths = export_all(result, args.out, prefix=args.prefix)

        if not args.quiet:
            print(_format_summary_table(result.metrics, config))
            print(f"\nSimulation artifacts saved to: {Path(args.out).resolve()}")
            print(f"  Hourly records: {out_paths['hourly_csv'].name}")
            print(f"  Daily summary:  {out_paths['daily_csv'].name}")
            print(f"  Annual metrics: {out_paths['summary_json'].name}\n")

        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
