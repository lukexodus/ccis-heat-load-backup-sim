"""One-at-a-time (OAT) parameter sensitivity analysis harness (INT-003).

Systematically evaluates microgrid sensitivity to key dispatch, thermal,
and physical storage parameters relative to the 100 kWp / 100 kWh baseline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Sequence

from ccis_sim.core.models import Battery, Building
import ccis_sim.integration.engine as engine_module
from ccis_sim.integration.engine import SimulationConfig, simulate
from ccis_sim.solar import array as solar_array_module


@dataclass(frozen=True)
class SensitivityPoint:
    """Individual sensitivity evaluation result for a perturbed parameter value."""

    parameter: str
    label: str
    value: Any
    grid_import_kwh: float
    unserved_tier1_2_kwh: float
    delta_grid_import_kwh: float
    delta_unserved_tier1_2_kwh: float
    is_exposed: bool
    notes: str = ""


@dataclass(frozen=True)
class SensitivitySweepResult:
    """Complete collection of OAT sensitivity points evaluated against a common baseline."""

    base_grid_import_kwh: float
    base_unserved_tier1_2_kwh: float
    points: list[SensitivityPoint] = field(default_factory=list)

    def to_dataframe_dict(self) -> list[dict[str, Any]]:
        """Export sensitivity results as list of dictionary records for tabular rendering."""
        rows = []
        for p in self.points:
            rows.append(
                {
                    "Parameter": p.parameter,
                    "Variation": p.label,
                    "Value": str(p.value),
                    "Grid Import (kWh)": round(p.grid_import_kwh, 2),
                    "Δ Grid (kWh)": round(p.delta_grid_import_kwh, 2),
                    "Unserved T1+2 (kWh)": round(p.unserved_tier1_2_kwh, 2),
                    "Δ Unserved T1+2 (kWh)": round(p.delta_unserved_tier1_2_kwh, 2),
                    "Exposed Parameter": "Yes" if p.is_exposed else "Monkeypatched",
                    "Notes": p.notes,
                }
            )
        return rows


def run_oat_sensitivity_analysis(
    weather_year: int = 2019,
    outage_regime: str = "normal",
    seed: int = 0,
) -> SensitivitySweepResult:
    """Run full One-at-a-Time (OAT) sensitivity matrix on 100 kWp / 100 kWh CCIS system.

    Parameters tested:
    1. Emergency Outage Reserve (0.10, 0.20, 0.50): exposed on SimulationConfig.
    2. Tier-2 Shed Threshold (0.10, 0.20, 0.30): exposed on SimulationConfig.
    3. Cooling Temperature Sensitivity Slope (3, 4, 5 %/°C): exposed on Building.
    4. PR-Driving Balance-of-System (BOS) Losses (±5%): monkeypatched in test harness.
    5. Battery Round-Trip Efficiency (0.88, 0.92, 0.96): monkeypatched in test harness.

    Returns
    -------
    SensitivitySweepResult
        Collection of all evaluation points with absolute and differential metrics.
    """
    base_cfg = SimulationConfig(
        solar_kwp=100.0,
        battery_kwh=100.0,
        weather_year=weather_year,
        outage_regime=outage_regime,
        seed=seed,
    )

    # 0. Baseline evaluation
    base_res = simulate(base_cfg)
    base_grid = base_res.metrics["annual_grid_import_kwh"]
    base_unserved_t1_2 = (
        base_res.tracker_summary["unserved_tier1_kwh"]
        + base_res.tracker_summary["unserved_tier2_kwh"]
    )

    points: list[SensitivityPoint] = []

    def add_point(
        param: str,
        label: str,
        val: Any,
        res: Any,
        is_exposed: bool,
        notes: str = "",
    ) -> None:
        grid = res.metrics["annual_grid_import_kwh"]
        unserved = (
            res.tracker_summary["unserved_tier1_kwh"]
            + res.tracker_summary["unserved_tier2_kwh"]
        )
        points.append(
            SensitivityPoint(
                parameter=param,
                label=label,
                value=val,
                grid_import_kwh=grid,
                unserved_tier1_2_kwh=unserved,
                delta_grid_import_kwh=grid - base_grid,
                delta_unserved_tier1_2_kwh=unserved - base_unserved_t1_2,
                is_exposed=is_exposed,
                notes=notes,
            )
        )

    # 1. Emergency Reserve (0.10, 0.20, 0.50)
    for er in (0.10, 0.20, 0.50):
        cfg = SimulationConfig(
            solar_kwp=100.0,
            battery_kwh=100.0,
            weather_year=weather_year,
            outage_regime=outage_regime,
            seed=seed,
            emergency_reserve_pct=er,
        )
        res = simulate(cfg)
        add_point(
            param="Emergency Reserve Fraction",
            label=f"Reserve = {er:.0%}",
            val=er,
            res=res,
            is_exposed=True,
            notes="Configurable on SimulationConfig.emergency_reserve_pct",
        )

    # 2. Tier-2 Shed Threshold (0.10, 0.20, 0.30)
    for t2 in (0.10, 0.20, 0.30):
        cfg = SimulationConfig(
            solar_kwp=100.0,
            battery_kwh=100.0,
            weather_year=weather_year,
            outage_regime=outage_regime,
            seed=seed,
            tier2_shed_soc_fraction=t2,
        )
        res = simulate(cfg)
        add_point(
            param="Tier-2 Shedding Threshold",
            label=f"Shed SoC = {t2:.0%}",
            val=t2,
            res=res,
            is_exposed=True,
            notes="Configurable on SimulationConfig.tier2_shed_soc_fraction",
        )

    # 3. Cooling Slope (3, 4, 5 %/°C)
    for cs in (0.03, 0.04, 0.05):
        bldg = Building(cooling_sensitivity_per_c=cs)
        res = simulate(base_cfg, building=bldg)
        add_point(
            param="Cooling Slope (%/°C)",
            label=f"Slope = {cs*100:.1f}%/°C",
            val=cs,
            res=res,
            is_exposed=True,
            notes="Exposed on Building archetype constructor",
        )

    # 4. PR-Driving BOS Factor (±5%)
    orig_compute_ac = engine_module.compute_ac_generation
    try:
        for mult, name in ((0.95, "-5% BOS (lower PR)"), (1.00, "Baseline BOS (PR 0.77)"), (1.05, "+5% BOS (higher PR)")):
            def _make_patched_compute(factor: float):
                def _patched(dc_kw_per_kwp, array, **kwargs):
                    kwargs["soiling"] = solar_array_module.DEFAULT_SOILING_FACTOR * factor
                    return orig_compute_ac(dc_kw_per_kwp, array, **kwargs)
                return _patched

            engine_module.compute_ac_generation = _make_patched_compute(mult)
            res = simulate(base_cfg)
            add_point(
                param="PR-Driving BOS Factor",
                label=name,
                val=f"{mult*100:.0f}% of base",
                res=res,
                is_exposed=False,
                notes="Monkeypatched in engine.compute_ac_generation (soiling factor)",
            )
    finally:
        engine_module.compute_ac_generation = orig_compute_ac

    # 5. Battery RTE (0.88, 0.92, 0.96)
    orig_defaults = Battery.__init__.__defaults__
    try:
        for rte in (0.88, 0.92, 0.96):
            Battery.__init__.__defaults__ = (rte, *orig_defaults[1:])
            res = simulate(base_cfg)
            add_point(
                param="Battery Round-Trip Efficiency (RTE)",
                label=f"RTE = {rte:.2f}",
                val=rte,
                res=res,
                is_exposed=False,
                notes="Monkeypatched in Battery.__init__.__defaults__ (not on SimulationConfig)",
            )
    finally:
        Battery.__init__.__defaults__ = orig_defaults

    return SensitivitySweepResult(
        base_grid_import_kwh=base_grid,
        base_unserved_tier1_2_kwh=base_unserved_t1_2,
        points=points,
    )
