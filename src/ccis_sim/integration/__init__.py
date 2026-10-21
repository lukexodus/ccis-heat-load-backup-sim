"""Integrated time-step simulation engine, CLI driver, and Monte Carlo scenario runners."""

from ccis_sim.integration.baseline import (
    CALIBRATION_FACTOR_2019,
    DEFAULT_COOLING_DUTY_FACTOR,
    BaselineMetrics,
    compute_baseline_metrics,
    compute_placeholder_demand,
    run_baseline_simulation,
    simulate_baseline,
)
from ccis_sim.integration.engine import (
    SimulationConfig,
    SimulationResult,
    simulate,
)
from ccis_sim.integration.exporters import (
    export_all,
    export_daily_csv,
    export_hourly_csv,
    export_summary_json,
)

__all__ = [
    # Engine (INT-001)
    "simulate",
    "SimulationConfig",
    "SimulationResult",
    "export_all",
    "export_hourly_csv",
    "export_daily_csv",
    "export_summary_json",
    # Baseline (Phase 1 legacy & smoke)
    "CALIBRATION_FACTOR_2019",
    "DEFAULT_COOLING_DUTY_FACTOR",
    "BaselineMetrics",
    "compute_baseline_metrics",
    "compute_placeholder_demand",
    "run_baseline_simulation",
    "simulate_baseline",
]
