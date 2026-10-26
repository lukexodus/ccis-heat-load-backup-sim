"""Pareto trade-off optimization, candidate evaluation, and sizing recommendation engine (DEC-002).

Evaluates candidate microgrid sizing configurations (solar in {50, 100, 150, 200} kWp,
battery in {0, 25, 50, 100, 150, 200} kWh) across stochastic outage regimes,
constructs non-dominated Pareto frontiers, and executes formal sizing rules.
"""

from __future__ import annotations

import multiprocessing as mp
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import pandas as pd
from scipy import stats

from ccis_sim.decision.ahp import compute_cost_index, score_candidates
from ccis_sim.integration.engine import SimulationConfig, simulate
from ccis_sim.integration.scenarios import compute_bill_calibrated_scale
from ccis_sim.weather.loader import load_weather_fixture

CANDIDATE_SOLAR_SIZES: list[float] = [50.0, 100.0, 150.0, 200.0]
CANDIDATE_BATTERY_SIZES: list[float] = [0.0, 25.0, 50.0, 100.0, 150.0, 200.0]

_DEC_WEATHER_CACHE: dict[int, pd.DataFrame] = {}


def _init_dec_worker() -> None:
    """Initialize worker process by pre-loading and caching canonical weather fixtures once."""
    global _DEC_WEATHER_CACHE
    try:
        _DEC_WEATHER_CACHE[2016] = load_weather_fixture(2016)
        _DEC_WEATHER_CACHE[2019] = load_weather_fixture(2019)
    except Exception:
        _DEC_WEATHER_CACHE = {}


def _run_dec_simulation(config: SimulationConfig) -> dict[str, Any]:
    """Execute a single simulation run optimized for batch decision evaluation."""
    global _DEC_WEATHER_CACHE
    if not _DEC_WEATHER_CACHE:
        _init_dec_worker()

    w_df = _DEC_WEATHER_CACHE.get(config.weather_year)
    res = simulate(config, weather_df=w_df, verify=False)
    m = res.metrics

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
    }


def get_candidate_sizing_pairs() -> list[tuple[float, float]]:
    """Return the list of 24 candidate sizing pairs (excluding 0/0 reference baseline per [D-38])."""
    pairs: list[tuple[float, float]] = []
    for sol in CANDIDATE_SOLAR_SIZES:
        for bat in CANDIDATE_BATTERY_SIZES:
            pairs.append((sol, bat))
    return pairs


def generate_dec_configs(
    bill_scale: float | None = None,
    n_seeds: int = 50,
    weather_year: int = 2019,
    sizing_pairs: Sequence[tuple[float, float]] | None = None,
) -> list[SimulationConfig]:
    """Generate configuration matrix for DEC-002 candidate evaluation.

    Includes all 24 solar/battery candidate combinations plus the 0/0 reference baseline.
    Evaluated across normal and typhoon regimes, both demand scales (1.0 and bill-calibrated),
    and N random seeds using Common Random Numbers (CRN).
    """
    if bill_scale is None:
        bill_scale = compute_bill_calibrated_scale()

    if sizing_pairs is None:
        # All 24 candidates + (0, 0) reference
        pairs = [(0.0, 0.0)] + get_candidate_sizing_pairs()
    else:
        pairs = list(sizing_pairs)

    configs: list[SimulationConfig] = []
    for scale in (1.0, float(bill_scale)):
        for regime in ("normal", "typhoon"):
            for seed in range(n_seeds):
                for sol, bat in pairs:
                    configs.append(
                        SimulationConfig(
                            solar_kwp=sol,
                            battery_kwh=bat,
                            weather_year=weather_year,
                            outage_regime=regime,
                            seed=seed,
                            demand_scale=scale,
                        )
                    )
    return configs


def run_candidate_simulations(
    configs: Sequence[SimulationConfig],
    n_workers: int | None = None,
) -> pd.DataFrame:
    """Execute simulation batch across multiprocessing worker pool."""
    workers = n_workers or min(mp.cpu_count(), 8)
    with mp.Pool(processes=workers, initializer=_init_dec_worker) as pool:
        records = pool.map(_run_dec_simulation, configs)
    return pd.DataFrame(records)


def compute_cell_statistics(series: pd.Series) -> dict[str, float]:
    """Compute sample mean, standard deviation, 95% CI half-width, and percentiles."""
    vals = series.to_numpy(dtype=np.float64)
    n = len(vals)
    if n == 0:
        return {"mean": 0.0, "std": 0.0, "ci95_half": 0.0, "p5": 0.0, "p50": 0.0, "p95": 0.0}

    mean_val = float(np.mean(vals))
    std_val = float(np.std(vals, ddof=1)) if n > 1 else 0.0
    se = std_val / np.sqrt(n) if n > 0 else 0.0
    t_crit = float(stats.t.ppf(0.975, df=n - 1)) if n > 1 else 1.96
    ci95_half = t_crit * se

    p5 = float(np.percentile(vals, 5))
    p50 = float(np.percentile(vals, 50))
    p95 = float(np.percentile(vals, 95))

    return {
        "mean": mean_val,
        "std": std_val,
        "ci95_half": ci95_half,
        "p5": p5,
        "p50": p50,
        "p95": p95,
    }


def aggregate_candidates_for_decision(
    runs_df: pd.DataFrame,
    r: float = 0.6,
) -> pd.DataFrame:
    """Aggregate simulation runs into candidate summary records for AHP and Pareto analysis.

    For each sizing and demand scale:
    - Extracts mean fraction of outage hours with Tier 1+2 served in typhoon regime (Reliability).
    - Extracts mean self-sufficiency and curtailment (normal regime).
    - Computes cost index = solar_kwp + battery_kwh * r.
    - Computes full sample statistics (mean, std, 95% CI, percentiles).
    """
    df = runs_df.copy()
    # Add combined unserved Tier 1+2 metric
    df["unserved_t1_2_kwh"] = df["unserved_t1_kwh"] + df["unserved_t2_kwh"]
    # Fraction of outage hours where T1+2 were served
    # In HourlyRecord/scenarios, outage_hours_t2_served represents hours where Tier 2 was served.
    # By priority structure, Tier 1 is always served whenever Tier 2 is served.
    df["t1_2_served_fraction"] = np.where(
        df["total_outage_hours"] > 0,
        df["outage_hours_t2_served"] / df["total_outage_hours"],
        1.0,
    )

    rows = []
    group_cols = ["solar_kwp", "battery_kwh", "weather_year", "demand_scale"]

    for (sol, bat, year, scale), group in df.groupby(group_cols):
        # Normal regime subset (baseline grid metrics)
        norm_group = group[group["outage_regime"] == "normal"]
        # Typhoon regime subset (extreme reliability metrics)
        typh_group = group[group["outage_regime"] == "typhoon"]

        typh_rel_stats = compute_cell_statistics(typh_group["t1_2_served_fraction"])
        typh_unserved_stats = compute_cell_statistics(typh_group["unserved_t1_2_kwh"])

        norm_rel_stats = compute_cell_statistics(norm_group["t1_2_served_fraction"])
        norm_unserved_stats = compute_cell_statistics(norm_group["unserved_t1_2_kwh"])

        ss_mean = float(norm_group["self_sufficiency"].mean())
        curt_mean = float(norm_group["curtailed_kwh"].mean())
        grid_mean = float(norm_group["grid_import_kwh"].mean())
        solar_mean = float(norm_group["solar_gen_kwh"].mean())
        cycles_mean = float(norm_group["battery_cycles"].mean())
        cost = compute_cost_index(sol, bat, r=r)

        rows.append(
            {
                "solar_kwp": sol,
                "battery_kwh": bat,
                "weather_year": year,
                "demand_scale": scale,
                "demand_case": "bottom_up" if abs(scale - 1.0) < 1e-3 else "bill_calibrated",
                "cost_index": cost,
                # Typhoon reliability (AHP Criterion 1)
                "reliability": typh_rel_stats["mean"],
                "reliability_std": typh_rel_stats["std"],
                "reliability_ci95_half": typh_rel_stats["ci95_half"],
                "reliability_p5": typh_rel_stats["p5"],
                "reliability_p50": typh_rel_stats["p50"],
                "reliability_p95": typh_rel_stats["p95"],
                # Typhoon unserved Tier 1+2 (tie-breaker & engineering KPI)
                "unserved_t1_2_mean": typh_unserved_stats["mean"],
                "unserved_t1_2_std": typh_unserved_stats["std"],
                "unserved_t1_2_ci95_half": typh_unserved_stats["ci95_half"],
                "unserved_t1_2_p5": typh_unserved_stats["p5"],
                "unserved_t1_2_p50": typh_unserved_stats["p50"],
                "unserved_t1_2_p95": typh_unserved_stats["p95"],
                # Normal reliability
                "normal_reliability_mean": norm_rel_stats["mean"],
                "normal_unserved_t1_2_mean": norm_unserved_stats["mean"],
                # Grid & Solar performance metrics (Normal regime)
                "self_sufficiency": ss_mean,
                "self_sufficiency_mean": ss_mean,
                "curtailment": curt_mean,
                "curtailed_mean": curt_mean,
                "grid_import_mean": grid_mean,
                "solar_gen_mean": solar_mean,
                "battery_cycles_mean": cycles_mean,
            }
        )

    res_df = pd.DataFrame(rows)
    return res_df


def identify_pareto_frontier(
    candidates_df: pd.DataFrame,
    r: float = 0.6,
) -> pd.DataFrame:
    """Identify non-dominated Pareto optimal solutions over (Reliability ↑, Cost ↓, Self-sufficiency ↑).

    Per decision [D-38], candidate evaluations exclude solar = 0 (except for comparison).
    A candidate A dominates candidate B if:
      - Reliability(A) >= Reliability(B)
      - Cost(A) <= Cost(B)
      - Self_sufficiency(A) >= Self_sufficiency(B)
      with strict inequality in at least one metric.
    """
    df = candidates_df.copy()
    if "cost_index" not in df.columns:
        df["cost_index"] = compute_cost_index(df["solar_kwp"], df["battery_kwh"], r=r)

    # Exclude (0, 0) baseline from candidate trade-off competition if requested
    # But evaluate among all active solar candidates
    n = len(df)
    is_pareto = np.ones(n, dtype=bool)

    rel = df["reliability"].to_numpy()
    cost = df["cost_index"].to_numpy()
    ss = df["self_sufficiency"].to_numpy()

    tol = 1e-6
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            # Does j dominate i?
            j_no_worse = (
                (rel[j] >= rel[i] - tol)
                and (cost[j] <= cost[i] + tol)
                and (ss[j] >= ss[i] - tol)
            )
            j_strictly_better = (
                (rel[j] > rel[i] + tol)
                or (cost[j] < cost[i] - tol)
                or (ss[j] > ss[i] + tol)
            )
            if j_no_worse and j_strictly_better:
                is_pareto[i] = False
                break

    df["is_pareto"] = is_pareto
    return df


def select_recommended_sizing(
    candidates_df: pd.DataFrame,
    r: float = 0.6,
    threshold_bottom_up: float = 0.90,
    threshold_bill_calibrated: float = 0.80,
) -> dict[str, Any]:
    """Execute formal sizing recommendation rule locked in [D-38].

    Rule:
    "The cheapest non-dominated sizing whose mean Tier 1+2 outage-hours-served fraction
    is >= 0.90 in the typhoon regime under the bottom-up demand AND >= 0.80 under the
    bill-calibrated demand."

    If no single sizing simultaneously meets both, reports the best qualifying sizing
    under each demand case and the best composite trade-off.
    """
    df = candidates_df.copy()
    # Separate by demand case
    bu_df = df[df["demand_case"] == "bottom_up"].copy()
    bc_df = df[df["demand_case"] == "bill_calibrated"].copy()

    # Determine Pareto frontier for each demand case
    bu_pareto = identify_pareto_frontier(bu_df, r=r)
    bc_pareto = identify_pareto_frontier(bc_df, r=r)

    # Candidates meeting thresholds (excluding 0 solar)
    bu_qualifying = bu_pareto[
        (bu_pareto["solar_kwp"] > 0)
        & (bu_pareto["is_pareto"])
        & (bu_pareto["reliability"] >= threshold_bottom_up - 1e-4)
    ]
    bc_qualifying = bc_pareto[
        (bc_pareto["solar_kwp"] > 0)
        & (bc_pareto["is_pareto"])
        & (bc_pareto["reliability"] >= threshold_bill_calibrated - 1e-4)
    ]

    # Find common sizings meeting both criteria
    bu_pairs = set(zip(bu_qualifying["solar_kwp"], bu_qualifying["battery_kwh"]))
    bc_pairs = set(zip(bc_qualifying["solar_kwp"], bc_qualifying["battery_kwh"]))
    joint_pairs = bu_pairs.intersection(bc_pairs)

    joint_qualifying_rows = []
    for sol, bat in joint_pairs:
        cost = compute_cost_index(sol, bat, r=r)
        joint_qualifying_rows.append({"solar_kwp": sol, "battery_kwh": bat, "cost_index": cost})

    if joint_qualifying_rows:
        joint_df = pd.DataFrame(joint_qualifying_rows).sort_values("cost_index").reset_index(drop=True)
        recommended_solar = float(joint_df.iloc[0]["solar_kwp"])
        recommended_battery = float(joint_df.iloc[0]["battery_kwh"])
        is_robust = True
        status_note = "Qualifies simultaneously under both bottom-up (>=90%) and bill-calibrated (>=80%) demand."
    else:
        # Fallback: pick cheapest Pareto sizing from bill-calibrated that also has highest reliability
        is_robust = False
        if not bc_qualifying.empty:
            best_bc = bc_qualifying.sort_values("cost_index").iloc[0]
            recommended_solar = float(best_bc["solar_kwp"])
            recommended_battery = float(best_bc["battery_kwh"])
            status_note = "No sizing jointly qualified; selected cheapest bill-calibrated qualifying Pareto sizing."
        elif not bu_qualifying.empty:
            best_bu = bu_qualifying.sort_values("cost_index").iloc[0]
            recommended_solar = float(best_bu["solar_kwp"])
            recommended_battery = float(best_bu["battery_kwh"])
            status_note = "No sizing qualified under bill-calibrated demand; selected cheapest bottom-up qualifying sizing."
        else:
            # Pick highest reliability sizing
            max_bu = bu_pareto.sort_values("reliability", ascending=False).iloc[0]
            recommended_solar = float(max_bu["solar_kwp"])
            recommended_battery = float(max_bu["battery_kwh"])
            status_note = "No candidate reached threshold; selected maximum achievable reliability sizing."

    # Extract detailed metrics for recommended sizing under both demand cases
    rec_bu = bu_df[
        (bu_df["solar_kwp"] == recommended_solar) & (bu_df["battery_kwh"] == recommended_battery)
    ].iloc[0]
    rec_bc = bc_df[
        (bc_df["solar_kwp"] == recommended_solar) & (bc_df["battery_kwh"] == recommended_battery)
    ].iloc[0]

    return {
        "solar_kwp": recommended_solar,
        "battery_kwh": recommended_battery,
        "cost_index": compute_cost_index(recommended_solar, recommended_battery, r=r),
        "is_robust": is_robust,
        "status_note": status_note,
        "bottom_up_metrics": rec_bu.to_dict(),
        "bill_calibrated_metrics": rec_bc.to_dict(),
        "bu_qualifying_count": len(bu_qualifying),
        "bc_qualifying_count": len(bc_qualifying),
        "joint_qualifying_count": len(joint_qualifying_rows),
    }
