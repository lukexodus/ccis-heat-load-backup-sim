"""Verification and physical invariant audit harness for CCIS microgrid simulation (INT-003).

Executes comprehensive energy balance, battery boundary, finite value, and
tier demand conservation checks across multi-scenario simulation runs.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Sequence

import pandas as pd

from ccis_sim.core.models import HourlyRecord
from ccis_sim.integration.engine import SimulationConfig, SimulationResult, simulate


@dataclass(frozen=True)
class AuditResult:
    """Outcome of an invariant audit execution on a simulation configuration."""

    config: SimulationConfig
    passed: bool
    max_hourly_residual: float
    cumulative_residual: float
    min_soc_observed: float
    max_soc_observed: float
    soc_within_bounds: bool
    non_finite_count: int
    tier_conservation_passed: bool
    details: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        """Format a single-line summary of audit verification."""
        status = "PASSED" if self.passed else "FAILED"
        return (
            f"[{status}] solar={self.config.solar_kwp:.0f}kWp, bat={self.config.battery_kwh:.0f}kWh, "
            f"year={self.config.weather_year}, regime={self.config.outage_regime} | "
            f"max_res={self.max_hourly_residual:.2e} kWh, cum_res={self.cumulative_residual:.2e} kWh, "
            f"SoC=[{self.min_soc_observed:.1f}, {self.max_soc_observed:.1f}], "
            f"non_finite={self.non_finite_count}, tier_cons={self.tier_conservation_passed}"
        )


def audit_run(
    config: SimulationConfig,
    weather_df: pd.DataFrame | None = None,
    seed: int | None = None,
    tolerance: float = 1e-5,
) -> AuditResult:
    """Execute simulation with verification enabled and audit physical conservation invariants.

    Parameters
    ----------
    config : SimulationConfig
        Target simulation sizing and operational configuration.
    weather_df : pd.DataFrame, optional
        Pre-loaded weather DataFrame to reuse across runs.
    seed : int, optional
        Random seed override (defaults to config.seed).
    tolerance : float, optional
        Maximum allowable energy balance residual per hour in kWh (default: 1e-5).

    Returns
    -------
    AuditResult
        Structured verification record containing residual metrics, SoC bounds,
        finite counts, and tier-conservation status.
    """
    res: SimulationResult = simulate(
        config=config,
        weather_df=weather_df,
        seed=seed,
        verify=True,
    )

    records: Sequence[HourlyRecord] = res.records
    numeric_fields = (
        "demand_gross_kwh",
        "demand_served_kwh",
        "solar_generation_kwh",
        "solar_to_demand_kwh",
        "solar_to_battery_kwh",
        "solar_curtailed_kwh",
        "battery_soc_kwh",
        "battery_charge_kwh",
        "battery_discharge_kwh",
        "grid_import_kwh",
        "unserved_load_kwh",
    )

    non_finite_count = 0
    tier_conservation_passed = True
    tier_mismatch_max = 0.0

    soc_values = [r.battery_soc_kwh for r in records]
    min_soc_observed = min(soc_values) if soc_values else 0.0
    max_soc_observed = max(soc_values) if soc_values else 0.0

    for r in records:
        # Check finite values
        for f in numeric_fields:
            val = getattr(r, f, 0.0)
            if not math.isfinite(val):
                non_finite_count += 1

        # Check hourly tier demand conservation: served + unserved == gross demand
        tier_sum = r.demand_served_kwh + r.unserved_load_kwh
        diff = abs(tier_sum - r.demand_gross_kwh)
        if diff > tier_mismatch_max:
            tier_mismatch_max = diff
        if diff > 1e-7:
            tier_conservation_passed = False

    max_hourly_residual = max(r.energy_balance_residual_kwh for r in records)
    cumulative_residual = sum(r.signed_residual_kwh for r in records)

    # Validate SoC bounds against physical battery specifications
    if config.battery_kwh > 0.0:
        min_allowed_soc = 0.10 * config.battery_kwh  # 10% min_soc protection floor
        max_allowed_soc = config.battery_kwh
        soc_within_bounds = (
            (min_soc_observed >= min_allowed_soc - 1e-7)
            and (max_soc_observed <= max_allowed_soc + 1e-7)
        )
    else:
        soc_within_bounds = (abs(min_soc_observed) < 1e-7) and (abs(max_soc_observed) < 1e-7)

    # Verification threshold pass/fail determination
    # Note: Cumulative tolerance scales as O(sqrt(N) * epsilon) per [D-21]
    cum_tolerance = max(tolerance, math.sqrt(len(records)) * tolerance)
    passed = (
        (max_hourly_residual <= tolerance)
        and (abs(cumulative_residual) <= cum_tolerance)
        and soc_within_bounds
        and (non_finite_count == 0)
        and tier_conservation_passed
    )

    details = {
        "record_count": len(records),
        "cum_tolerance_kwh": cum_tolerance,
        "max_hourly_tolerance_kwh": tolerance,
        "tier_mismatch_max_kwh": tier_mismatch_max,
        "tracker_summary": res.tracker_summary,
    }

    return AuditResult(
        config=config,
        passed=passed,
        max_hourly_residual=max_hourly_residual,
        cumulative_residual=cumulative_residual,
        min_soc_observed=min_soc_observed,
        max_soc_observed=max_soc_observed,
        soc_within_bounds=soc_within_bounds,
        non_finite_count=non_finite_count,
        tier_conservation_passed=tier_conservation_passed,
        details=details,
    )


def run_standard_audit_matrix() -> list[AuditResult]:
    """Execute audit across the standard verification matrix specified in INT-003.

    Covers 8 primary configurations across sizing and weather/outage regimes:
    4 sizings:
      - grid-only (0 kWp PV, 0 kWh battery)
      - PV-only 100 (100 kWp PV, 0 kWh battery)
      - PV+battery 100/100 (100 kWp PV, 100 kWh battery)
      - PV+battery 200/200 (200 kWp PV, 200 kWh battery)
    across {2019 normal, 2019 typhoon}, plus 2016 normal benchmark configurations.
    """
    configs = [
        # 1-4: 2019 Normal
        SimulationConfig(solar_kwp=0.0, battery_kwh=0.0, weather_year=2019, outage_regime="normal", seed=0),
        SimulationConfig(solar_kwp=100.0, battery_kwh=0.0, weather_year=2019, outage_regime="normal", seed=0),
        SimulationConfig(solar_kwp=100.0, battery_kwh=100.0, weather_year=2019, outage_regime="normal", seed=0),
        SimulationConfig(solar_kwp=200.0, battery_kwh=200.0, weather_year=2019, outage_regime="normal", seed=0),
        # 5-8: 2019 Typhoon
        SimulationConfig(solar_kwp=0.0, battery_kwh=0.0, weather_year=2019, outage_regime="typhoon", seed=0),
        SimulationConfig(solar_kwp=100.0, battery_kwh=0.0, weather_year=2019, outage_regime="typhoon", seed=0),
        SimulationConfig(solar_kwp=100.0, battery_kwh=100.0, weather_year=2019, outage_regime="typhoon", seed=0),
        SimulationConfig(solar_kwp=200.0, battery_kwh=200.0, weather_year=2019, outage_regime="typhoon", seed=0),
        # 9-12: 2016 Normal (El Niño hot year)
        SimulationConfig(solar_kwp=0.0, battery_kwh=0.0, weather_year=2016, outage_regime="normal", seed=0),
        SimulationConfig(solar_kwp=100.0, battery_kwh=0.0, weather_year=2016, outage_regime="normal", seed=0),
        SimulationConfig(solar_kwp=100.0, battery_kwh=100.0, weather_year=2016, outage_regime="normal", seed=0),
        SimulationConfig(solar_kwp=200.0, battery_kwh=200.0, weather_year=2016, outage_regime="normal", seed=0),
    ]

    results = []
    for cfg in configs:
        res = audit_run(cfg)
        results.append(res)
    return results
