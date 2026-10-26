"""Unit tests for decision analysis module (DEC-001, DEC-002, and DEC-003 figures).

Tests:
- AHP eigenvector solver, consistency ratio (CR <= 0.10), and inconsistent matrix rejection.
- Multi-criteria normalization and candidate scoring.
- Multi-objective Pareto frontier identification over (Reliability, Cost, Self-sufficiency).
- Sizing recommendation rule evaluation on synthetic candidate data.
- Figure generation smoke test.
"""

from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from ccis_sim.decision.ahp import (
    ahp_weights,
    compute_cost_index,
    get_ahp_weight_sets,
    get_base_pairwise_matrix,
    score_candidates,
)
from ccis_sim.decision.plots import (
    ensure_figures_dir,
    plot_7day_dispatch,
    plot_monthly_demand_comparison,
    plot_pareto_scatter,
    plot_soc_duration_curve,
    plot_unserved_distribution,
)
from ccis_sim.decision.sizing import (
    aggregate_candidates_for_decision,
    compute_cell_statistics,
    generate_dec_configs,
    get_candidate_sizing_pairs,
    identify_pareto_frontier,
    select_recommended_sizing,
)


class TestAHP:
    """Tests for Analytic Hierarchy Process solver (DEC-001)."""

    def test_ahp_perfectly_consistent_3x3(self):
        """A perfectly consistent matrix has lambda_max = n, CI = 0, and CR = 0."""
        # True weights: w = [0.6, 0.3, 0.1]
        w_true = np.array([0.6, 0.3, 0.1])
        matrix = np.outer(w_true, 1.0 / w_true)

        weights, lambda_max, ci, cr = ahp_weights(matrix)

        np.testing.assert_allclose(weights, w_true, atol=1e-5)
        assert pytest.approx(lambda_max, abs=1e-4) == 3.0
        assert pytest.approx(ci, abs=1e-4) == 0.0
        assert pytest.approx(cr, abs=1e-4) == 0.0

    def test_ahp_base_pairwise_matrix(self):
        """Verify the 4x4 base pairwise comparison matrix defined in [D-38]."""
        matrix = get_base_pairwise_matrix()
        assert matrix.shape == (4, 4)

        weights, lambda_max, ci, cr = ahp_weights(matrix)

        assert len(weights) == 4
        assert pytest.approx(np.sum(weights), abs=1e-6) == 1.0
        # CR must be strictly <= 0.10
        assert cr <= 0.10
        assert cr >= 0.0
        assert lambda_max >= 4.0

        # Criteria weights should follow priority order: Reliability > Cost > Self-Sufficiency > Curtailment
        assert weights[0] > weights[1] > weights[2] > weights[3]

    def test_ahp_inconsistent_matrix_raises(self):
        """An excessively inconsistent matrix (CR > 0.10) must raise ValueError."""
        # Grossly inconsistent judgments
        bad_matrix = np.array(
            [
                [1.0, 9.0, 1.0 / 9.0],
                [1.0 / 9.0, 1.0, 9.0],
                [9.0, 1.0 / 9.0, 1.0],
            ]
        )
        with pytest.raises(ValueError, match="exceeds allowable threshold"):
            ahp_weights(bad_matrix)

    def test_ahp_weight_sets(self):
        """Check predefined weight profiles: base, equal, reliability_heavy."""
        w_sets = get_ahp_weight_sets()
        assert "base" in w_sets
        assert "equal" in w_sets
        assert "reliability_heavy" in w_sets

        for name, w in w_sets.items():
            assert len(w) == 4
            assert pytest.approx(np.sum(w), abs=1e-6) == 1.0

        np.testing.assert_allclose(w_sets["equal"], [0.25, 0.25, 0.25, 0.25])
        np.testing.assert_allclose(w_sets["reliability_heavy"], [0.60, 0.20, 0.10, 0.10])

    def test_cost_index_computation(self):
        """Verify cost index calculation for scalar and vector inputs across r values."""
        cost_base = compute_cost_index(100.0, 50.0, r=0.6)
        assert pytest.approx(cost_base) == 100.0 + 50.0 * 0.6  # 130.0

        cost_r03 = compute_cost_index(100.0, 50.0, r=0.3)
        assert pytest.approx(cost_r03) == 115.0

        cost_r10 = compute_cost_index(100.0, 50.0, r=1.0)
        assert pytest.approx(cost_r10) == 150.0

        # Vectorized
        sols = np.array([50.0, 100.0])
        bats = np.array([25.0, 50.0])
        costs = compute_cost_index(sols, bats, r=0.6)
        np.testing.assert_allclose(costs, [65.0, 130.0])

    def test_score_candidates(self):
        """Test candidate scoring and normalization."""
        candidates = pd.DataFrame(
            [
                {
                    "solar_kwp": 50.0,
                    "battery_kwh": 25.0,
                    "reliability": 0.70,
                    "cost_index": 65.0,
                    "self_sufficiency": 0.40,
                    "curtailment": 1000.0,
                    "unserved_t1_2_mean": 200.0,
                },
                {
                    "solar_kwp": 150.0,
                    "battery_kwh": 100.0,
                    "reliability": 0.95,
                    "cost_index": 210.0,
                    "self_sufficiency": 0.80,
                    "curtailment": 5000.0,
                    "unserved_t1_2_mean": 20.0,
                },
            ]
        )
        weights = [0.50, 0.20, 0.20, 0.10]
        scored = score_candidates(candidates, weights=weights, r=0.6)

        assert "ahp_score" in scored.columns
        assert "ahp_rank" in scored.columns
        assert len(scored) == 2
        assert set(scored["ahp_rank"]) == {1, 2}
        assert scored.iloc[0]["ahp_score"] >= scored.iloc[1]["ahp_score"]


class TestParetoAndSizing:
    """Tests for Pareto frontier and sizing recommendation rules (DEC-002)."""

    def test_pareto_toy_dataset(self):
        """A dominated point must have is_pareto = False; non-dominated must have True."""
        # Point A: Rel 0.90, Cost 100, SS 0.60
        # Point B: Rel 0.80, Cost 120, SS 0.50 (Strictly dominated by A: lower rel, higher cost, lower SS)
        # Point C: Rel 0.95, Cost 150, SS 0.70 (Non-dominated: higher rel and SS, but higher cost)
        toy_df = pd.DataFrame(
            [
                {"solar_kwp": 100.0, "battery_kwh": 50.0, "cost_index": 100.0, "reliability": 0.90, "self_sufficiency": 0.60},
                {"solar_kwp": 100.0, "battery_kwh": 70.0, "cost_index": 120.0, "reliability": 0.80, "self_sufficiency": 0.50},
                {"solar_kwp": 150.0, "battery_kwh": 100.0, "cost_index": 150.0, "reliability": 0.95, "self_sufficiency": 0.70},
            ]
        )
        pareto_df = identify_pareto_frontier(toy_df, r=0.6)
        res = dict(zip(zip(pareto_df["solar_kwp"], pareto_df["battery_kwh"]), pareto_df["is_pareto"]))

        assert res[(100.0, 50.0)] is True or res[(100.0, 50.0)] == True
        assert res[(100.0, 70.0)] is False or res[(100.0, 70.0)] == False
        assert res[(150.0, 100.0)] is True or res[(150.0, 100.0)] == True

    def test_sizing_recommendation_rule_unambiguous(self):
        """Test the formal sizing rule selecting the cheapest Pareto qualifying sizing."""
        # 3 candidate sizings under bottom-up and bill-calibrated demand
        # Sizing 1 (50/25): Cost 65. BU Rel 0.85 (<0.90), BC Rel 0.70 (<0.80) -> Fails both
        # Sizing 2 (100/50): Cost 130. BU Rel 0.92 (>=0.90), BC Rel 0.82 (>=0.80) -> Qualifies both
        # Sizing 3 (150/100): Cost 210. BU Rel 0.98 (>=0.90), BC Rel 0.91 (>=0.80) -> Qualifies both, but higher cost
        rows = [
            # Bottom-up
            {"solar_kwp": 50.0, "battery_kwh": 25.0, "demand_case": "bottom_up", "cost_index": 65.0, "reliability": 0.85, "self_sufficiency": 0.40, "unserved_t1_2_mean": 150.0, "reliability_ci95_half": 0.05, "reliability_p5": 0.80, "reliability_p50": 0.85, "reliability_p95": 0.90, "unserved_t1_2_std": 20.0, "unserved_t1_2_ci95_half": 5.0, "unserved_t1_2_p5": 100.0, "unserved_t1_2_p95": 200.0, "grid_import_mean": 50000.0},
            {"solar_kwp": 100.0, "battery_kwh": 50.0, "demand_case": "bottom_up", "cost_index": 130.0, "reliability": 0.92, "self_sufficiency": 0.65, "unserved_t1_2_mean": 60.0, "reliability_ci95_half": 0.03, "reliability_p5": 0.88, "reliability_p50": 0.92, "reliability_p95": 0.96, "unserved_t1_2_std": 15.0, "unserved_t1_2_ci95_half": 4.0, "unserved_t1_2_p5": 40.0, "unserved_t1_2_p95": 90.0, "grid_import_mean": 35000.0},
            {"solar_kwp": 150.0, "battery_kwh": 100.0, "demand_case": "bottom_up", "cost_index": 210.0, "reliability": 0.98, "self_sufficiency": 0.80, "unserved_t1_2_mean": 10.0, "reliability_ci95_half": 0.02, "reliability_p5": 0.95, "reliability_p50": 0.98, "reliability_p95": 1.00, "unserved_t1_2_std": 5.0, "unserved_t1_2_ci95_half": 1.5, "unserved_t1_2_p5": 0.0, "unserved_t1_2_p95": 20.0, "grid_import_mean": 20000.0},
            # Bill-calibrated
            {"solar_kwp": 50.0, "battery_kwh": 25.0, "demand_case": "bill_calibrated", "cost_index": 65.0, "reliability": 0.70, "self_sufficiency": 0.25, "unserved_t1_2_mean": 400.0, "reliability_ci95_half": 0.06, "reliability_p5": 0.60, "reliability_p50": 0.70, "reliability_p95": 0.80, "unserved_t1_2_std": 40.0, "unserved_t1_2_ci95_half": 10.0, "unserved_t1_2_p5": 300.0, "unserved_t1_2_p95": 500.0, "grid_import_mean": 120000.0},
            {"solar_kwp": 100.0, "battery_kwh": 50.0, "demand_case": "bill_calibrated", "cost_index": 130.0, "reliability": 0.82, "self_sufficiency": 0.45, "unserved_t1_2_mean": 180.0, "reliability_ci95_half": 0.04, "reliability_p5": 0.75, "reliability_p50": 0.82, "reliability_p95": 0.88, "unserved_t1_2_std": 25.0, "unserved_t1_2_ci95_half": 7.0, "unserved_t1_2_p5": 140.0, "unserved_t1_2_p95": 230.0, "grid_import_mean": 90000.0},
            {"solar_kwp": 150.0, "battery_kwh": 100.0, "demand_case": "bill_calibrated", "cost_index": 210.0, "reliability": 0.91, "self_sufficiency": 0.60, "unserved_t1_2_mean": 50.0, "reliability_ci95_half": 0.03, "reliability_p5": 0.85, "reliability_p50": 0.91, "reliability_p95": 0.95, "unserved_t1_2_std": 12.0, "unserved_t1_2_ci95_half": 3.5, "unserved_t1_2_p5": 30.0, "unserved_t1_2_p95": 70.0, "grid_import_mean": 60000.0},
        ]
        toy_df = pd.DataFrame(rows)
        rec = select_recommended_sizing(toy_df, r=0.6, threshold_bottom_up=0.90, threshold_bill_calibrated=0.80)

        # Cheapest qualifying sizing must be (100.0, 50.0)
        assert rec["solar_kwp"] == 100.0
        assert rec["battery_kwh"] == 50.0
        assert rec["cost_index"] == 130.0
        assert rec["is_robust"] is True

    def test_generate_dec_configs(self):
        """Verify configuration matrix generation dimensions."""
        pairs = get_candidate_sizing_pairs()
        assert len(pairs) == 24  # 4 solar x 6 battery
        assert (0.0, 0.0) not in pairs  # Excluded from active pairs

        # With 2 seeds, 2 regimes, 2 demand scales: (24 + 1) * 2 * 2 * 2 = 200 configs
        cfgs = generate_dec_configs(bill_scale=2.1, n_seeds=2)
        assert len(cfgs) == 200


class TestFiguresCreation:
    """Smoke tests verifying that figure generators produce valid images (DEC-003.1/.2)."""

    def test_figure_generation_smoke(self, tmp_path: Path):
        """Verify that figure files are created at expected paths and are non-empty."""
        from ccis_sim.core.models import HourlyRecord

        # Create dummy hourly records for 168 hours matching canonical HourlyRecord schema
        records = []
        for h in range(168):
            records.append(
                HourlyRecord(
                    hour=h + 1,
                    timestamp=f"2019-07-{1 + h//24:02d}T{h%24:02d}:00:00+08:00",
                    temp_ambient_c=30.0,
                    humidity_rel_pct=75.0,
                    ghi_w_m2=500.0 if 6 <= h % 24 <= 18 else 0.0,
                    demand_gross_kwh=30.0,
                    demand_served_kwh=30.0,
                    solar_generation_kwh=50.0 if 6 <= h % 24 <= 18 else 0.0,
                    solar_to_demand_kwh=20.0 if 6 <= h % 24 <= 18 else 0.0,
                    solar_to_battery_kwh=20.0 if 6 <= h % 24 <= 18 else 0.0,
                    solar_curtailed_kwh=10.0 if 6 <= h % 24 <= 18 else 0.0,
                    battery_soc_kwh=40.0,
                    battery_charge_kwh=20.0 if 6 <= h % 24 <= 18 else 0.0,
                    battery_discharge_kwh=10.0 if not (6 <= h % 24 <= 18) else 0.0,
                    grid_import_kwh=10.0 if (h < 40 or h > 80) else 0.0,
                    unserved_load_kwh=0.0,
                    grid_available=h < 40 or h > 80,  # Outage from hour 40 to 80
                    active_load_tier=3,
                )
            )

        f1 = plot_7day_dispatch(records, battery_kwh=50.0, output_path=tmp_path / "fig1.png", start_hour=0)
        assert f1.exists()
        assert f1.stat().st_size > 1000

        f2 = plot_soc_duration_curve(records, records, battery_kwh=50.0, output_path=tmp_path / "fig2.png")
        assert f2.exists()
        assert f2.stat().st_size > 1000
