"""Scenario Grid and Monte Carlo Simulation Runner (INT-002).

Executes the full comparative scenario matrix across solar PV capacities, battery storage sizes,
weather years, stochastic outage regimes, and demand calibration scales using multiprocessing.
"""

from __future__ import annotations

import multiprocessing as mp
import os
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import pandas as pd
from scipy import stats

from ccis_sim.integration.engine import SimulationConfig, simulate
from ccis_sim.weather.loader import load_weather_fixture

# Global worker cache for weather fixtures to avoid redundant file I/O per task
_WORKER_WEATHER_CACHE: dict[int, pd.DataFrame] = {}


def _init_worker() -> None:
    """Initialize multiprocessing worker process by caching canonical weather fixtures."""
    global _WORKER_WEATHER_CACHE
    try:
        _WORKER_WEATHER_CACHE = {
            2016: load_weather_fixture(2016),
            2019: load_weather_fixture(2019),
        }
    except Exception:
        # Fallback if fixtures cannot be loaded immediately
        _WORKER_WEATHER_CACHE = {}


def compute_bill_calibrated_scale() -> float:
    """Compute the single empirical scale factor reconciling bottom-up demand to synthetic mock bills.

    Scale = bills_total / bottom_up_total ≈ 2.1047 (Phase 1 synthetic billing fixture vs DEM-001/002).
    """
    bills_path = Path("data/fixtures/synthetic-mock-bills-ccis.csv")
    if not bills_path.exists():
        raise FileNotFoundError(f"Synthetic bills fixture not found at {bills_path}")

    bills_df = pd.read_csv(bills_path)
    bills_total = float(bills_df["total_kwh"].sum())

    cfg = SimulationConfig(
        solar_kwp=0.0,
        battery_kwh=0.0,
        weather_year=2019,
        outage_regime="normal",
        seed=42,
        demand_scale=1.0,
    )
    res = simulate(cfg, verify=False)
    bottom_up_total = float(res.metrics["annual_gross_demand_kwh"])

    if bottom_up_total <= 0.0:
        raise ValueError("Bottom-up annual demand must be strictly positive.")

    return bills_total / bottom_up_total


def _run_single_simulation(config: SimulationConfig) -> dict[str, Any]:
    """Execute a single simulation run and extract flat tabular scenario metrics.

    Args:
        config: SimulationConfig defining sizing, weather, regime, seed, and scaling.

    Returns:
        Dictionary mapping column names to scalar summary metrics.
    """
    global _WORKER_WEATHER_CACHE
    if not _WORKER_WEATHER_CACHE:
        _init_worker()

    w_df = _WORKER_WEATHER_CACHE.get(config.weather_year)
    res = simulate(config, weather_df=w_df, verify=True)
    m = res.metrics
    records = res.records

    peak_grid_kw = max((r.grid_import_kwh for r in records), default=0.0)
    battery_cycles = (
        m["annual_battery_discharge_kwh"] / config.battery_kwh
        if config.battery_kwh > 0.0
        else 0.0
    )
    self_sufficiency = m["self_sufficiency_pct"] / 100.0

    return {
        "solar_kwp": float(config.solar_kwp),
        "battery_kwh": float(config.battery_kwh),
        "weather_year": int(config.weather_year),
        "outage_regime": str(config.outage_regime),
        "demand_scale": float(config.demand_scale),
        "temp_offset_c": float(config.temp_offset_c),
        "seed": int(config.seed),
        "grid_import_kwh": float(m["annual_grid_import_kwh"]),
        "solar_gen_kwh": float(m["annual_solar_generation_kwh"]),
        "curtailed_kwh": float(m["annual_solar_curtailed_kwh"]),
        "unserved_t1_kwh": float(m["unserved_tier1_kwh"]),
        "unserved_t2_kwh": float(m["unserved_tier2_kwh"]),
        "unserved_t3_kwh": float(m["unserved_tier3_kwh"]),
        "total_outage_hours": int(m["total_outage_hours"]),
        "outage_hours_t1_served": int(m["outage_hours_tier1_served"]),
        "outage_hours_t2_served": int(m["outage_hours_tier2_served"]),
        "battery_cycles": float(battery_cycles),
        "self_sufficiency": float(self_sufficiency),
        "peak_grid_kw": float(peak_grid_kw),
    }


def generate_scenario_configs(
    bill_scale: float | None = None,
) -> list[SimulationConfig]:
    """Generate the full INT-002 simulation scenario configuration suite.

    Consists of:
    1. Main grid: 4 solar × 4 battery × 2 weather × 2 regimes × 30 seeds (demand_scale=1.0) = 1,920 runs
    2. Sensitivity grid: 4 solar × 4 battery × 1 weather (2019) × 2 regimes × 15 seeds (demand_scale=bill_scale) = 480 runs
    3. Climate +2°C case: 2 solar ({0, 100}) × 2 battery ({0, 100}) × 2019 normal × 15 seeds (temp_offset_c=2.0) = 60 runs
    Total: 2,460 runs.

    Common Random Numbers (CRN) are preserved across sizings for identical (weather, regime, seed) tuples.
    """
    if bill_scale is None:
        bill_scale = compute_bill_calibrated_scale()

    solar_sizes = [0.0, 50.0, 100.0, 200.0]
    battery_sizes = [0.0, 50.0, 100.0, 200.0]
    configs: list[SimulationConfig] = []

    # 1. Main Grid (demand_scale = 1.0, 30 seeds)
    for year in (2019, 2016):
        for regime in ("normal", "typhoon"):
            for seed in range(30):
                for sol in solar_sizes:
                    for bat in battery_sizes:
                        configs.append(
                            SimulationConfig(
                                solar_kwp=sol,
                                battery_kwh=bat,
                                weather_year=year,
                                outage_regime=regime,
                                seed=seed,
                                demand_scale=1.0,
                                temp_offset_c=0.0,
                            )
                        )

    # 2. Sensitivity Grid (demand_scale = bill_scale, 2019 only, 15 seeds)
    for regime in ("normal", "typhoon"):
        for seed in range(15):
            for sol in solar_sizes:
                for bat in battery_sizes:
                    configs.append(
                        SimulationConfig(
                            solar_kwp=sol,
                            battery_kwh=bat,
                            weather_year=2019,
                            outage_regime=regime,
                            seed=seed,
                            demand_scale=bill_scale,
                            temp_offset_c=0.0,
                        )
                    )

    # 3. Climate Sensitivity (+2.0°C perturbation, 2019 normal, 15 seeds)
    for seed in range(15):
        for sol in (0.0, 100.0):
            for bat in (0.0, 100.0):
                configs.append(
                    SimulationConfig(
                        solar_kwp=sol,
                        battery_kwh=bat,
                        weather_year=2019,
                        outage_regime="normal",
                        seed=seed,
                        demand_scale=1.0,
                        temp_offset_c=2.0,
                    )
                )

    return configs


def compute_mc_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Compute Monte Carlo summary statistics per scenario cell.

    Calculates mean, std, 5th percentile, and 95th percentile for:
    - unserved Tier 1 + Tier 2 load (kWh)
    - fraction of outage hours with Tier 1 and Tier 2 fully served
    """
    df_calc = df.copy()
    df_calc["unserved_t12_kwh"] = df_calc["unserved_t1_kwh"] + df_calc["unserved_t2_kwh"]
    df_calc["outage_t12_served_frac"] = np.where(
        df_calc["total_outage_hours"] > 0,
        df_calc["outage_hours_t2_served"] / df_calc["total_outage_hours"],
        1.0,
    )

    group_cols = [
        "solar_kwp",
        "battery_kwh",
        "weather_year",
        "outage_regime",
        "demand_scale",
        "temp_offset_c",
    ]

    rows = []
    for keys, grp in df_calc.groupby(group_cols, sort=True):
        u12 = grp["unserved_t12_kwh"].to_numpy()
        frac = grp["outage_t12_served_frac"].to_numpy()
        n = len(grp)

        rows.append(
            {
                "solar_kwp": keys[0],
                "battery_kwh": keys[1],
                "weather_year": keys[2],
                "outage_regime": keys[3],
                "demand_scale": keys[4],
                "temp_offset_c": keys[5],
                "sample_size": n,
                "unserved_t12_kwh_mean": float(np.mean(u12)),
                "unserved_t12_kwh_std": float(np.std(u12, ddof=1)) if n > 1 else 0.0,
                "unserved_t12_kwh_p5": float(np.percentile(u12, 5)),
                "unserved_t12_kwh_p95": float(np.percentile(u12, 95)),
                "outage_t12_served_frac_mean": float(np.mean(frac)),
                "outage_t12_served_frac_std": float(np.std(frac, ddof=1)) if n > 1 else 0.0,
                "outage_t12_served_frac_p5": float(np.percentile(frac, 5)),
                "outage_t12_served_frac_p95": float(np.percentile(frac, 95)),
            }
        )

    return pd.DataFrame(rows)


def check_convergence(df: pd.DataFrame) -> dict[int, dict[str, Any]]:
    """Evaluate Monte Carlo convergence for the benchmark (100 kWp, 100 kWh, 2019, typhoon) cell.

    Reports sample mean, standard error, 95% Student-t confidence interval,
    and relative CI half-width at N = 10, 20, 30 seeds.
    """
    mask = (
        (df["solar_kwp"] == 100.0)
        & (df["battery_kwh"] == 100.0)
        & (df["weather_year"] == 2019)
        & (df["outage_regime"] == "typhoon")
        & (df["demand_scale"] == 1.0)
        & (df["temp_offset_c"] == 0.0)
    )
    cell_df = df[mask].sort_values("seed")
    u12 = (cell_df["unserved_t1_kwh"] + cell_df["unserved_t2_kwh"]).to_numpy()

    results: dict[int, dict[str, Any]] = {}
    for n in (10, 20, 30):
        if len(u12) < n:
            continue
        sample = u12[:n]
        mean = float(np.mean(sample))
        std = float(np.std(sample, ddof=1)) if n > 1 else 0.0
        se = std / np.sqrt(n)
        t_crit = float(stats.t.ppf(0.975, df=n - 1)) if n > 1 else 1.96
        half_width = float(t_crit * se)
        ci_lower = max(0.0, mean - half_width)
        ci_upper = mean + half_width

        is_converged = False
        rel_half_width = 0.0
        if mean == 0.0:
            is_converged = True
            convergence_note = "Exact zero unserved load (battery fully covers all sampled outages)"
        else:
            rel_half_width = half_width / mean
            is_converged = rel_half_width < 0.10
            convergence_note = (
                f"CI half-width is {rel_half_width * 100:.2f}% of mean "
                f"({'< 10% target met' if is_converged else '>= 10%'})"
            )

        results[n] = {
            "n": n,
            "mean": mean,
            "std": std,
            "se": se,
            "ci_95": (ci_lower, ci_upper),
            "half_width": half_width,
            "rel_half_width": rel_half_width,
            "is_converged": is_converged,
            "note": convergence_note,
        }

    return results


def run_grid(
    configs: Sequence[SimulationConfig] | None = None,
    *,
    output_dir: str | Path = "results",
    num_workers: int | None = None,
    return_df: bool = True,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Execute scenario grid simulations using multiprocessing and serialize output CSVs.

    Args:
        configs: List of SimulationConfig instances to run. If None, runs full INT-002 suite (2,460 runs).
        output_dir: Directory where scenario_grid.csv and mc_summary.csv will be written.
        num_workers: Number of worker processes (default: min(os.cpu_count() or 1, 8)).
        return_df: If True, returns (scenario_grid_df, mc_summary_df).

    Returns:
        Tuple of (scenario_grid_df, mc_summary_df).
    """
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    if configs is None:
        configs = generate_scenario_configs()

    n_workers = num_workers or min(os.cpu_count() or 1, 8)

    if n_workers > 1 and len(configs) > 1:
        with mp.Pool(processes=n_workers, initializer=_init_worker) as pool:
            results = pool.map(_run_single_simulation, configs)
    else:
        _init_worker()
        results = [_run_single_simulation(cfg) for cfg in configs]

    scenario_grid_df = pd.DataFrame(results)
    scenario_grid_csv = out_path / "scenario_grid.csv"
    scenario_grid_df.to_csv(scenario_grid_csv, index=False)

    mc_summary_df = compute_mc_summary(scenario_grid_df)
    mc_summary_csv = out_path / "mc_summary.csv"
    mc_summary_df.to_csv(mc_summary_csv, index=False)

    return scenario_grid_df, mc_summary_df
