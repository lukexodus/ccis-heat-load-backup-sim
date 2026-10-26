"""Multi-criteria decision analysis (AHP), Pareto trade-off optimization, and figure visualization."""

from __future__ import annotations

from ccis_sim.decision.ahp import (
    CRITERIA_NAMES,
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
    CANDIDATE_BATTERY_SIZES,
    CANDIDATE_SOLAR_SIZES,
    aggregate_candidates_for_decision,
    compute_cell_statistics,
    generate_dec_configs,
    get_candidate_sizing_pairs,
    identify_pareto_frontier,
    run_candidate_simulations,
    select_recommended_sizing,
)

__all__ = [
    "CRITERIA_NAMES",
    "ahp_weights",
    "compute_cost_index",
    "get_ahp_weight_sets",
    "get_base_pairwise_matrix",
    "score_candidates",
    "CANDIDATE_SOLAR_SIZES",
    "CANDIDATE_BATTERY_SIZES",
    "get_candidate_sizing_pairs",
    "generate_dec_configs",
    "run_candidate_simulations",
    "compute_cell_statistics",
    "aggregate_candidates_for_decision",
    "identify_pareto_frontier",
    "select_recommended_sizing",
    "ensure_figures_dir",
    "plot_7day_dispatch",
    "plot_soc_duration_curve",
    "plot_unserved_distribution",
    "plot_pareto_scatter",
    "plot_monthly_demand_comparison",
]
