"""Unit tests for validation.hypothesis (DOC-FIX-001 Part B)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ccis_sim.validation.hypothesis import (
    add_combined_unserved,
    format_markdown,
    grid_import_tests,
    holm_adjust,
    paired_test,
    regime_test,
    run_hypothesis_suite,
    sizing_pair_tests,
    unpaired_test,
)


def _row(
    *,
    sol: float,
    bat: float,
    seed: int,
    year: int = 2019,
    regime: str = "typhoon",
    scale: float = 1.0,
    temp_offset: float = 0.0,
    u12: float,
    grid: float = 0.0,
) -> dict:
    return {
        "solar_kwp": sol,
        "battery_kwh": bat,
        "weather_year": year,
        "outage_regime": regime,
        "demand_scale": scale,
        "temp_offset_c": temp_offset,
        "seed": seed,
        "unserved_t1_kwh": u12 / 2.0,
        "unserved_t2_kwh": u12 / 2.0,
        "unserved_t3_kwh": 0.0,
        "grid_import_kwh": grid,
    }


def test_add_combined_unserved_sums_tiers() -> None:
    df = pd.DataFrame([_row(sol=0, bat=0, seed=1, u12=10.0)])
    out = add_combined_unserved(df)
    assert out.loc[0, "unserved_t1_2_kwh"] == pytest.approx(10.0)


def test_holm_adjust_monotone_and_bounded() -> None:
    raw = np.array([0.01, 0.04, 0.03, 0.20])
    adjusted = holm_adjust(raw)
    assert np.all(adjusted >= raw - 1e-12)
    assert np.all(adjusted <= 1.0)
    assert adjusted[0] <= adjusted[2] <= adjusted[3]


def test_paired_test_detects_consistent_shift() -> None:
    left = np.arange(10, dtype=float)
    right = left + 5.0
    result = paired_test(left, right, label="shift")
    assert result["n"] == 10
    assert result["mean_diff"] == pytest.approx(5.0)
    assert result["wilcoxon_p"] < 0.01
    assert result["paired_t_p"] < 0.01


def test_paired_test_rejects_length_mismatch() -> None:
    with pytest.raises(ValueError, match="equal length"):
        paired_test(np.zeros(3), np.zeros(4))


def test_unpaired_test_reports_sample_sizes() -> None:
    result = unpaired_test(np.zeros(5), np.ones(7), label="x")
    assert result["n_left"] == 5
    assert result["n_right"] == 7
    assert result["mean_diff"] == pytest.approx(1.0)


def test_sizing_pair_tests_pair_on_seed() -> None:
    rows = []
    for seed in range(6):
        rows.append(_row(sol=100.0, bat=50.0, seed=seed, u12=10.0))
        rows.append(_row(sol=100.0, bat=100.0, seed=seed, u12=4.0))
        rows.append(_row(sol=200.0, bat=100.0, seed=seed, u12=2.0))
        rows.append(_row(sol=200.0, bat=200.0, seed=seed, u12=1.0))
        rows.append(_row(sol=0.0, bat=0.0, seed=seed, u12=20.0))
    table = sizing_pair_tests(pd.DataFrame(rows))
    assert len(table) == 4
    assert (table["n"] == 6).all()
    assert "holm_adjusted_p" in table.columns
    # mean_diff is right minus left; every right-hand sizing unserves less.
    assert (table["mean_diff"] < 0.0).all()


def test_grid_import_tests_pair_weather_and_offset() -> None:
    rows = []
    for seed in range(6):
        rows.append(_row(sol=0.0, bat=0.0, seed=seed, regime="normal", year=2019, grid=100.0, u12=0.0))
        rows.append(_row(sol=0.0, bat=0.0, seed=seed, regime="normal", year=2016, grid=110.0, u12=0.0))
        rows.append(_row(sol=100.0, bat=100.0, seed=seed, regime="normal", year=2019, grid=50.0, u12=0.0))
        rows.append(_row(sol=100.0, bat=100.0, seed=seed, regime="normal", year=2016, grid=60.0, u12=0.0))
    for seed in range(6):
        rows.append(
            _row(
                sol=0.0,
                bat=0.0,
                seed=seed,
                regime="normal",
                year=2019,
                temp_offset=2.0,
                grid=120.0,
                u12=0.0,
            )
        )
    table = grid_import_tests(pd.DataFrame(rows))
    assert len(table) == 3
    assert (table["n"] == 6).all()


def test_regime_test_is_unpaired() -> None:
    rows = []
    for seed in range(8):
        rows.append(_row(sol=100.0, bat=100.0, seed=seed, regime="normal", u12=1.0))
        rows.append(_row(sol=100.0, bat=100.0, seed=seed, regime="typhoon", u12=9.0))
    table = regime_test(pd.DataFrame(rows))
    assert len(table) == 1
    assert table.loc[0, "n_left"] == 8
    assert table.loc[0, "n_right"] == 8
    assert "mannwhitney_p" in table.columns


def test_run_hypothesis_suite_and_markdown() -> None:
    rows = []
    for seed in range(15):
        for (sol, bat), value in [
            ((100.0, 50.0), 10.0),
            ((100.0, 100.0), 4.0),
            ((200.0, 100.0), 2.0),
            ((200.0, 200.0), 1.0),
            ((0.0, 0.0), 20.0),
        ]:
            rows.append(_row(sol=sol, bat=bat, seed=seed, u12=value))
            rows.append(
                _row(
                    sol=sol,
                    bat=bat,
                    seed=seed,
                    regime="normal",
                    grid=100.0 - float(seed),
                    u12=0.0,
                )
            )
            rows.append(
                _row(
                    sol=sol,
                    bat=bat,
                    seed=seed,
                    regime="normal",
                    year=2016,
                    grid=110.0 - float(seed),
                    u12=0.0,
                )
            )
        rows.append(
            _row(
                sol=0.0,
                bat=0.0,
                seed=seed,
                regime="normal",
                temp_offset=2.0,
                grid=120.0,
                u12=0.0,
            )
        )
    df = pd.DataFrame(rows)
    tables = run_hypothesis_suite(df)
    assert set(tables) == {"sizing_pairs", "grid_import", "regime"}
    markdown = format_markdown(tables)
    assert "not real-world inference" in markdown
    assert "comparison" in markdown
    assert "wilcoxon_p" in markdown
