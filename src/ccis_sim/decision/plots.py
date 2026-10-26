"""Publication-quality visualization and figure generation suite (DEC-003.1 / DEC-003.2).

Generates matplotlib figures saved to results/figures/ (150 dpi) conforming to
task specifications and academic reporting standards:
1. 7-day dispatch stacked area chart during typhoon outage.
2. Battery State-of-Charge (SoC) duration curves.
3. Distribution of unserved Tier 1+2 energy across Monte Carlo seeds.
4. Pareto frontier trade-off scatter across demand cases.
5. Monthly building electricity demand profile (bottom-up vs synthetic bills).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence

import matplotlib
matplotlib.use("Agg")  # Non-interactive headless backend
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from ccis_sim.core.models import HourlyRecord
from ccis_sim.demand.mock_bills import SyntheticBillGenerator
from ccis_sim.integration.engine import SimulationConfig, simulate


def ensure_figures_dir(output_dir: Path | str = "results/figures") -> Path:
    """Ensure destination directory for figures exists."""
    p = Path(output_dir).resolve()
    p.mkdir(parents=True, exist_ok=True)
    return p


def plot_7day_dispatch(
    records: Sequence[HourlyRecord],
    battery_kwh: float,
    output_path: Path | str = "results/figures/fig1_dispatch_7day.png",
    start_hour: int | None = None,
) -> Path:
    """Figure 1: 7-day chronological dispatch stacked area chart during an outage window.

    Shows power flows meeting demand (Solar to load, Battery discharge, Grid import,
    and Unserved shortfall) with stored battery SoC on a secondary right axis.
    """
    path = Path(output_path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)

    # Find a 7-day window (168h) containing an outage if start_hour not specified
    if start_hour is None:
        outage_hours = [i for i, r in enumerate(records) if not r.grid_available]
        if outage_hours:
            center_outage = outage_hours[len(outage_hours) // 2]
            start_hour = max(0, min(center_outage - 84, len(records) - 168))
        else:
            start_hour = 24 * 180  # Default to mid-year

    window = records[start_hour : start_hour + 168]
    hours = np.arange(len(window))

    solar_to_load = np.array([r.solar_to_demand_kwh for r in window])
    bat_discharge = np.array([r.battery_discharge_kwh for r in window])
    grid_import = np.array([r.grid_import_kwh for r in window])
    unserved = np.array([r.unserved_load_kwh for r in window])
    soc_kwh = np.array([r.battery_soc_kwh for r in window])
    grid_avail = np.array([r.grid_available for r in window])

    fig, ax1 = plt.subplots(figsize=(12, 5.5), dpi=150)

    # Stacked area of electrical supply dispatch
    ax1.stackplot(
        hours,
        solar_to_load,
        bat_discharge,
        grid_import,
        unserved,
        labels=["Solar to Demand", "Battery Discharge", "Grid Import", "Unserved Shortfall"],
        colors=["#f39c12", "#27ae60", "#2980b9", "#e74c3c"],
        alpha=0.85,
    )

    # Highlight outage periods with shaded vertical spans
    in_outage = False
    outage_start = 0
    for h, avail in enumerate(grid_avail):
        if not avail and not in_outage:
            in_outage = True
            outage_start = h
        elif avail and in_outage:
            in_outage = False
            ax1.axvspan(outage_start, h, color="grey", alpha=0.25, hatch="//", label="Grid Outage" if outage_start == 0 else "")
    if in_outage:
        ax1.axvspan(outage_start, len(grid_avail), color="grey", alpha=0.25, hatch="//")

    ax1.set_xlim(0, 168)
    ax1.set_xlabel("Time Elapsed (Hours over 7-Day Window)", fontsize=11, fontweight="bold")
    ax1.set_ylabel("Hourly Electrical Flow (kW or kWh/h)", fontsize=11, fontweight="bold")
    ax1.set_title("Figure 1: 7-Day Microgrid Dispatch Dynamics Across Outage Window", fontsize=12, fontweight="bold")
    ax1.grid(True, linestyle=":", alpha=0.6)

    # Secondary axis for Battery SoC
    ax2 = ax1.twinx()
    ax2.plot(hours, soc_kwh, color="#8e44ad", linewidth=2.0, linestyle="--", label="Battery Stored SoC (kWh)")
    if battery_kwh > 0:
        ax2.set_ylim(0, battery_kwh * 1.1)
        ax2.axhline(0.10 * battery_kwh, color="darkred", linestyle=":", linewidth=1.2, label="10% Protection Floor")
    ax2.set_ylabel("Battery State-of-Charge (kWh)", color="#8e44ad", fontsize=11, fontweight="bold")
    ax2.tick_params(axis="y", labelcolor="#8e44ad")

    # Combine legends
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    # Remove duplicate labels
    by_label = dict(zip(labels1 + labels2, lines1 + lines2))
    ax1.legend(by_label.values(), by_label.keys(), loc="upper left", framealpha=0.9, fontsize=9)

    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close(fig)
    return path


def plot_soc_duration_curve(
    records_normal: Sequence[HourlyRecord],
    records_typhoon: Sequence[HourlyRecord],
    battery_kwh: float,
    output_path: Path | str = "results/figures/fig2_soc_duration_curve.png",
) -> Path:
    """Figure 2: Battery State-of-Charge duration curve (Normal vs Typhoon outage regimes)."""
    path = Path(output_path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)

    soc_normal = np.sort([r.battery_soc_kwh for r in records_normal])[::-1]
    soc_typhoon = np.sort([r.battery_soc_kwh for r in records_typhoon])[::-1]
    pct_year = np.linspace(0, 100, len(soc_normal))

    fig, ax = plt.subplots(figsize=(8, 5), dpi=150)
    ax.plot(pct_year, soc_normal, label="Normal Reliability Regime", color="#2980b9", linewidth=2.0)
    ax.plot(pct_year, soc_typhoon, label="Typhoon Reliability Regime", color="#c0392b", linewidth=2.0, linestyle="--")

    if battery_kwh > 0:
        ax.axhline(battery_kwh, color="black", linestyle=":", label=f"Nominal Capacity ({battery_kwh:.0f} kWh)")
        ax.axhline(0.10 * battery_kwh, color="red", linestyle=":", label=f"Min SoC Floor ({0.10*battery_kwh:.0f} kWh)")
        ax.set_ylim(0, battery_kwh * 1.08)

    ax.set_xlim(0, 100)
    ax.set_xlabel("Percentage of Annual Hours Exceeded (%)", fontsize=11, fontweight="bold")
    ax.set_ylabel("Battery Usable State-of-Charge (kWh)", fontsize=11, fontweight="bold")
    ax.set_title("Figure 2: Annual Battery State-of-Charge Duration Curve", fontsize=12, fontweight="bold")
    ax.grid(True, linestyle=":", alpha=0.6)
    ax.legend(loc="upper right", framealpha=0.9, fontsize=9.5)

    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close(fig)
    return path


def plot_unserved_distribution(
    runs_df: pd.DataFrame,
    recommended_pair: tuple[float, float],
    output_path: Path | str = "results/figures/fig3_unserved_distribution.png",
) -> Path:
    """Figure 3: Unserved Tier 1+2 energy distributions across Monte Carlo seeds (Typhoon regime).

    Compares 3 representative sizings: (100 kWp, 50 kWh), Recommended Sizing, and (200 kWp, 200 kWh).
    """
    path = Path(output_path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)

    df_typh = runs_df[
        (runs_df["outage_regime"] == "typhoon")
        & (runs_df["demand_scale"] == 1.0)
    ].copy()
    df_typh["unserved_t1_2_kwh"] = df_typh["unserved_t1_kwh"] + df_typh["unserved_t2_kwh"]

    rec_sol, rec_bat = recommended_pair
    triplet = [
        (100.0, 50.0, "100 kWp / 50 kWh\n(moderate system)"),
        (rec_sol, rec_bat, f"{rec_sol:.0f} kWp / {rec_bat:.0f} kWh\n(recommended)"),
        (200.0, 200.0, "200 kWp / 200 kWh\n(max grid cap)"),
    ]

    data_to_plot = []
    labels = []
    for sol, bat, name in triplet:
        subset = df_typh[(df_typh["solar_kwp"] == sol) & (df_typh["battery_kwh"] == bat)]
        if not subset.empty:
            data_to_plot.append(subset["unserved_t1_2_kwh"].to_numpy())
            labels.append(name)
        else:
            data_to_plot.append(np.array([0.0]))
            labels.append(name)

    fig, ax = plt.subplots(figsize=(9.0, 5.2), dpi=150)
    box = ax.boxplot(
        data_to_plot,
        tick_labels=labels,
        patch_artist=True,
        showmeans=True,
        meanline=True,
    )
    ax.tick_params(axis="x", labelsize=9)
    colors = ["#3498db", "#2ecc71", "#9b59b6"]
    for patch, color in zip(box["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)

    ax.set_ylabel("Unserved Tier 1 + 2 Energy (kWh / year)", fontsize=11, fontweight="bold")
    ax.set_title("Figure 3: Unserved Critical Energy Distribution across 50 Stochastic Seeds (Typhoon)", fontsize=11, fontweight="bold")
    ax.grid(True, linestyle=":", alpha=0.6)

    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close(fig)
    return path


def plot_pareto_scatter(
    candidates_df: pd.DataFrame,
    recommended_pair: tuple[float, float],
    output_path: Path | str = "results/figures/fig4_pareto_scatter.png",
) -> Path:
    """Figure 4: Pareto trade-off scatter (Cost Index vs Reliability) for both demand cases."""
    path = Path(output_path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.5), dpi=150, sharey=True)

    cases = [
        ("bottom_up", "Panel A: Bottom-Up Demand (Primary, Scale = 1.0)", ax1),
        ("bill_calibrated", "Panel B: Bill-Calibrated Demand (Sensitivity, Scale ≈ 2.10)", ax2),
    ]

    rec_sol, rec_bat = recommended_pair

    for case_key, title, ax in cases:
        sub = candidates_df[
            (candidates_df["demand_case"] == case_key)
            & (candidates_df["solar_kwp"] > 0)
        ].copy()

        # Non-Pareto vs Pareto points (cast to bool to handle mixed-type column)
        is_pareto_bool = sub["is_pareto"].astype(bool)
        non_pareto = sub[~is_pareto_bool]
        pareto = sub[is_pareto_bool].sort_values("cost_index")

        sc1 = ax.scatter(
            non_pareto["cost_index"],
            non_pareto["reliability"] * 100.0,
            c=non_pareto["self_sufficiency"] * 100.0,
            cmap="viridis",
            s=60,
            alpha=0.5,
            edgecolors="none",
            label="Dominated Sizing",
            vmin=30,
            vmax=90,
        )

        sc2 = ax.scatter(
            pareto["cost_index"],
            pareto["reliability"] * 100.0,
            c=pareto["self_sufficiency"] * 100.0,
            cmap="viridis",
            s=120,
            marker="o",
            edgecolors="black",
            linewidth=1.5,
            label="Pareto Optimal Frontier",
            vmin=30,
            vmax=90,
        )

        # Connect Pareto frontier with step / line
        if not pareto.empty:
            ax.plot(
                pareto["cost_index"],
                pareto["reliability"] * 100.0,
                color="black",
                linestyle="--",
                alpha=0.7,
                linewidth=1.2,
            )

        # Mark recommended point
        rec_pt = sub[(sub["solar_kwp"] == rec_sol) & (sub["battery_kwh"] == rec_bat)]
        if not rec_pt.empty:
            ax.scatter(
                rec_pt["cost_index"],
                rec_pt["reliability"] * 100.0,
                color="#e74c3c",
                s=280,
                marker="*",
                edgecolors="black",
                linewidth=1.5,
                zorder=5,
                label=f"Recommended ({rec_sol:.0f}kWp/{rec_bat:.0f}kWh)",
            )

        ax.set_xlabel("Relative Sizing Cost Index (PV + 0.6×Battery)", fontsize=10.5, fontweight="bold")
        if ax == ax1:
            ax.set_ylabel("Tier 1+2 Outage Hours Served (%) [Typhoon]", fontsize=10.5, fontweight="bold")
        ax.set_title(title, fontsize=11, fontweight="bold")
        ax.grid(True, linestyle=":", alpha=0.6)
        ax.legend(loc="lower right", framealpha=0.9, fontsize=8.5)

    cbar_ax = fig.add_axes([0.92, 0.15, 0.02, 0.7])
    cbar = fig.colorbar(sc2, cax=cbar_ax)
    cbar.set_label("Annual Self-Sufficiency (%)", fontsize=10.5, fontweight="bold")

    fig.suptitle("Figure 4: Multi-Objective Pareto Trade-Off: Cost vs Resilience vs Self-Sufficiency", fontsize=12, fontweight="bold")
    plt.subplots_adjust(right=0.90, wspace=0.10)
    plt.savefig(path, dpi=150)
    plt.close(fig)
    return path


def plot_monthly_demand_comparison(
    records: Sequence[HourlyRecord],
    bills_path: Path | str = "data/fixtures/synthetic-mock-bills-ccis.csv",
    output_path: Path | str = "results/figures/fig5_monthly_demand_comparison.png",
) -> Path:
    """Figure 5: Monthly electricity consumption: Bottom-Up model vs Synthetic Mock Utility Bills.

    Visualizes the ~2.1x demand gap between bottom-up academic schedule and continuous baseload.
    """
    path = Path(output_path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)

    # 1. Monthly bottom-up simulation
    monthly_sim = np.zeros(12, dtype=np.float64)
    for r in records:
        m = int(r.timestamp[5:7]) - 1
        monthly_sim[m] += r.demand_gross_kwh

    # 2. Mock utility bills
    bills = SyntheticBillGenerator.load_from_csv(bills_path)
    monthly_bills = np.array([b.total_kwh for b in bills])

    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    x = np.arange(12)
    width = 0.38

    fig, ax = plt.subplots(figsize=(10, 5), dpi=150)
    b1 = ax.bar(x - width / 2, monthly_sim / 1e3, width, label="Bottom-Up Model (DEM-001/002, scale=1.0)", color="#3498db")
    b2 = ax.bar(x + width / 2, monthly_bills / 1e3, width, label="Synthetic Utility Bills (CORE-003, scale≈2.10)", color="#e67e22")

    tot_sim = np.sum(monthly_sim) / 1e3
    tot_bill = np.sum(monthly_bills) / 1e3
    ratio = tot_bill / tot_sim

    ax.set_xticks(x)
    ax.set_xticklabels(month_names, fontsize=10)
    ax.set_ylabel("Monthly Electricity Consumption (MWh)", fontsize=11, fontweight="bold")
    ax.set_title(
        f"Figure 5: Monthly Demand Profile: Bottom-Up vs Synthetic Bills\n"
        f"Annual: Bottom-Up = {tot_sim:.1f} MWh (EUI 75.7) vs Bills = {tot_bill:.1f} MWh (EUI 159.4) | Ratio = {ratio:.2f}×",
        fontsize=11,
        fontweight="bold",
    )
    ax.grid(True, axis="y", linestyle=":", alpha=0.6)
    ax.legend(loc="upper left", framealpha=0.9, fontsize=9.5)

    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close(fig)
    return path
