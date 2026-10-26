"""Paired and unpaired hypothesis tests over the INT-002 scenario grid (DOC-FIX-001 Part B).

Seeds are common random numbers across sizings, so comparisons that share
(weather_year, outage_regime, demand_scale, temp_offset_c, seed) are paired by seed.

All p-values describe seed-to-seed simulation variability. They are not real-world
inference, and N is small (15 or 30 paired seeds depending on the tranche).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
import pandas as pd
from scipy import stats

SCENARIO_GRID_PATH = Path("results/scenario_grid.csv")

PAIRING_KEYS = ["weather_year", "outage_regime", "demand_scale", "temp_offset_c", "seed"]


def add_combined_unserved(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with ``unserved_t1_2_kwh`` = Tier 1 + Tier 2 unserved energy."""
    out = df.copy()
    out["unserved_t1_2_kwh"] = out["unserved_t1_kwh"] + out["unserved_t2_kwh"]
    return out


def load_scenario_grid(path: str | Path = SCENARIO_GRID_PATH) -> pd.DataFrame:
    """Load the scenario grid CSV and add the combined Tier 1+2 unserved column."""
    return add_combined_unserved(pd.read_csv(path))


def _filter(
    df: pd.DataFrame,
    *,
    weather_year: int,
    outage_regime: str,
    demand_scale: float,
    temp_offset_c: float = 0.0,
    solar_kwp: float,
    battery_kwh: float,
    seed_max: int | None = None,
) -> pd.DataFrame:
    if "unserved_t1_2_kwh" not in df.columns:
        df = add_combined_unserved(df)
    mask = (
        (df["weather_year"] == weather_year)
        & (df["outage_regime"] == outage_regime)
        & np.isclose(df["demand_scale"], demand_scale)
        & np.isclose(df["temp_offset_c"], temp_offset_c)
        & np.isclose(df["solar_kwp"], solar_kwp)
        & np.isclose(df["battery_kwh"], battery_kwh)
    )
    if seed_max is not None:
        mask &= df["seed"] <= seed_max
    return df.loc[mask, PAIRING_KEYS + ["unserved_t1_2_kwh", "grid_import_kwh"]].copy()


def holm_adjust(pvalues: Sequence[float]) -> np.ndarray:
    """Holm-Bonferroni step-down adjusted p-values, preserving input order."""
    p = np.asarray(pvalues, dtype=float)
    m = p.size
    order = np.argsort(p)
    adjusted = np.empty(m, dtype=float)
    running = 0.0
    for rank, idx in enumerate(order):
        running = max(running, (m - rank) * p[idx])
        adjusted[idx] = min(1.0, running)
    return adjusted


def paired_test(
    left: np.ndarray,
    right: np.ndarray,
    *,
    label: str = "",
) -> dict[str, Any]:
    """Wilcoxon signed-rank (primary) and paired t-test (secondary) on differences.

    The 95% CI is the paired t interval for the mean difference. Cohen's dz is
    ``mean(diff) / sd(diff)``.
    """
    a = np.asarray(left, dtype=float)
    b = np.asarray(right, dtype=float)
    if a.shape != b.shape:
        raise ValueError("paired samples must have equal length")
    diff = b - a
    n = int(diff.size)
    if n == 0:
        raise ValueError("paired samples must not be empty")

    mean_diff = float(np.mean(diff))
    median_diff = float(np.median(diff))
    sd_diff = float(np.std(diff, ddof=1)) if n > 1 else 0.0
    se = sd_diff / np.sqrt(n) if n > 0 else 0.0
    t_crit = float(stats.t.ppf(0.975, df=n - 1)) if n > 1 else float("nan")
    ci_half = t_crit * se
    dz = mean_diff / sd_diff if sd_diff > 0.0 else float("nan")

    if n < 2:
        wilcoxon_p = float("nan")
        ttest_p = float("nan")
    elif np.allclose(diff, 0.0):
        wilcoxon_p = 1.0
        ttest_p = 1.0
    else:
        try:
            wilcoxon_p = float(stats.wilcoxon(diff, zero_method="wilcox").pvalue)
        except ValueError:
            wilcoxon_p = float("nan")
        ttest_p = float(stats.ttest_rel(b, a).pvalue)

    return {
        "comparison": label,
        "n": n,
        "mean_diff": mean_diff,
        "median_diff": median_diff,
        "sd_diff": sd_diff,
        "ci95_half": float(ci_half),
        "cohens_dz": float(dz),
        "wilcoxon_p": wilcoxon_p,
        "paired_t_p": ttest_p,
    }


def unpaired_test(left: np.ndarray, right: np.ndarray, *, label: str = "") -> dict[str, Any]:
    """Mann-Whitney U (primary) and Welch t-test (secondary) on independent samples."""
    a = np.asarray(left, dtype=float)
    b = np.asarray(right, dtype=float)
    if a.size == 0 or b.size == 0:
        raise ValueError("unpaired samples must not be empty")

    mw = stats.mannwhitneyu(b, a, alternative="two-sided")
    welch = stats.ttest_ind(b, a, equal_var=False)
    mean_diff = float(np.mean(b) - np.mean(a))
    return {
        "comparison": label,
        "n_left": int(a.size),
        "n_right": int(b.size),
        "mean_left": float(np.mean(a)),
        "mean_right": float(np.mean(b)),
        "mean_diff": mean_diff,
        "mannwhitney_p": float(mw.pvalue),
        "welch_t_p": float(welch.pvalue),
    }


def _merge_paired(
    left_df: pd.DataFrame,
    right_df: pd.DataFrame,
    column: str,
    *,
    on: Sequence[str] | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    keys = list(on) if on is not None else PAIRING_KEYS
    merged = left_df.merge(right_df, on=keys, suffixes=("_left", "_right"))
    if merged.empty:
        raise ValueError("no paired seeds matched between the two selections")
    return merged[f"{column}_left"].to_numpy(), merged[f"{column}_right"].to_numpy()


def sizing_pair_tests(
    df: pd.DataFrame,
    *,
    demand_scale: float = 1.0,
    weather_year: int = 2019,
    outage_regime: str = "typhoon",
) -> pd.DataFrame:
    """Paired unserved T1+2 tests for the five sizing comparisons requested by the APC."""
    pairs = [
        ((100.0, 50.0), (100.0, 100.0)),
        ((100.0, 100.0), (200.0, 100.0)),
        ((200.0, 100.0), (200.0, 200.0)),
        ((0.0, 0.0), (100.0, 100.0)),
    ]
    rows = []
    for (sol_l, bat_l), (sol_r, bat_r) in pairs:
        left_df = _filter(
            df,
            weather_year=weather_year,
            outage_regime=outage_regime,
            demand_scale=demand_scale,
            solar_kwp=sol_l,
            battery_kwh=bat_l,
        )
        right_df = _filter(
            df,
            weather_year=weather_year,
            outage_regime=outage_regime,
            demand_scale=demand_scale,
            solar_kwp=sol_r,
            battery_kwh=bat_r,
        )
        left, right = _merge_paired(left_df, right_df, "unserved_t1_2_kwh")
        label = f"{sol_l:.0f}/{bat_l:.0f} -> {sol_r:.0f}/{bat_r:.0f}"
        rows.append(paired_test(left, right, label=label))

    result = pd.DataFrame(rows)
    result["holm_adjusted_p"] = holm_adjust(result["wilcoxon_p"].to_numpy())
    return result


def grid_import_tests(
    df: pd.DataFrame,
    *,
    demand_scale: float = 1.0,
) -> pd.DataFrame:
    """Paired grid-import tests: 2016 vs 2019, and +2 °C vs base."""
    rows: list[dict[str, Any]] = []

    for sol, bat in ((0.0, 0.0), (100.0, 100.0)):
        d2019 = _filter(
            df,
            weather_year=2019,
            outage_regime="normal",
            demand_scale=demand_scale,
            solar_kwp=sol,
            battery_kwh=bat,
        )
        d2016 = _filter(
            df,
            weather_year=2016,
            outage_regime="normal",
            demand_scale=demand_scale,
            solar_kwp=sol,
            battery_kwh=bat,
        )
        left, right = _merge_paired(
            d2016, d2019, "grid_import_kwh",
            on=["outage_regime", "demand_scale", "temp_offset_c", "seed"],
        )
        rows.append(paired_test(left, right, label=f"2019 minus 2016, normal, {sol:.0f}/{bat:.0f}"))

    base = _filter(
        df,
        weather_year=2019,
        outage_regime="normal",
        demand_scale=demand_scale,
        temp_offset_c=0.0,
        solar_kwp=0.0,
        battery_kwh=0.0,
        seed_max=14,
    )
    hot = _filter(
        df,
        weather_year=2019,
        outage_regime="normal",
        demand_scale=demand_scale,
        temp_offset_c=2.0,
        solar_kwp=0.0,
        battery_kwh=0.0,
    )
    left, right = _merge_paired(
        base, hot, "grid_import_kwh",
        on=["outage_regime", "demand_scale", "seed"],
    )
    rows.append(paired_test(left, right, label="+2 C minus base, 2019 normal, grid-only, 15 seeds"))

    result = pd.DataFrame(rows)
    result["holm_adjusted_p"] = holm_adjust(result["wilcoxon_p"].to_numpy())
    return result


def regime_test(
    df: pd.DataFrame,
    *,
    demand_scale: float = 1.0,
    weather_year: int = 2019,
    solar_kwp: float = 100.0,
    battery_kwh: float = 100.0,
) -> pd.DataFrame:
    """Unpaired typhoon vs normal unserved T1+2 comparison for one sizing."""
    normal = _filter(
        df,
        weather_year=weather_year,
        outage_regime="normal",
        demand_scale=demand_scale,
        solar_kwp=solar_kwp,
        battery_kwh=battery_kwh,
    )
    typhoon = _filter(
        df,
        weather_year=weather_year,
        outage_regime="typhoon",
        demand_scale=demand_scale,
        solar_kwp=solar_kwp,
        battery_kwh=battery_kwh,
    )
    row = unpaired_test(
        normal["unserved_t1_2_kwh"].to_numpy(),
        typhoon["unserved_t1_2_kwh"].to_numpy(),
        label=f"typhoon vs normal, 2019, {solar_kwp:.0f}/{battery_kwh:.0f}",
    )
    return pd.DataFrame([row])


def run_hypothesis_suite(df: pd.DataFrame | None = None) -> dict[str, pd.DataFrame]:
    """Run all Part B test families and return them keyed by family name."""
    data = load_scenario_grid() if df is None else add_combined_unserved(df)
    return {
        "sizing_pairs": sizing_pair_tests(data),
        "grid_import": grid_import_tests(data),
        "regime": regime_test(data),
    }


def format_markdown(tables: Mapping[str, pd.DataFrame]) -> str:
    """Render the test tables as Markdown with the required interpretation caveat."""
    lines = [
        "# Hypothesis Tests (DOC-FIX-001 Part B)",
        "",
        "> **Interpretation:** p-values describe seed-to-seed simulation variability under common",
        "> random numbers, not real-world inference. N is small (15 or 30 paired seeds).",
        "> No claim of precision beyond these data is made.",
        ">",
        "> `mean_diff` is **right minus left** in each `A -> B` comparison. A negative value means",
        "> the right-hand configuration/case has lower unserved energy or grid import.",
        "",
    ]
    titles = {
        "sizing_pairs": "1. Paired sizing comparisons — unserved Tier 1+2, 2019 typhoon, bottom-up",
        "grid_import": "2. Paired grid import — weather year and +2 °C",
        "regime": "3. Unpaired typhoon vs normal — unserved Tier 1+2, 2019, 100/100",
    }
    for key, table in tables.items():
        lines.append(f"## {titles.get(key, key)}")
        lines.append("")
        lines.append(table.to_markdown(index=False))
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    tables = run_hypothesis_suite()
    output = Path("results/hypothesis_tests.md")
    output.write_text(format_markdown(tables), encoding="utf-8")
    print(f"Wrote {output}")
    for name, table in tables.items():
        print(f"\n[{name}]")
        print(table.to_string(index=False))
