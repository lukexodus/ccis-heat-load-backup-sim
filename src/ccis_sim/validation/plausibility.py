"""Plausibility evaluation and benchmark reconciliation module (INT-003).

Provides calculation and comparison routines for ASHRAE Guideline 14 metrics
(NMBE, CV(RMSE)), diurnal/seasonal demand profiles, and solar yield reconciliation.
"""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import pandas as pd

from ccis_sim.core.models import HourlyRecord
from ccis_sim.demand.schedule import AcademicCalendar


@dataclass(frozen=True)
class ASHRAEMetrics:
    """ASHRAE Guideline 14 statistical validation metrics for monthly calibration."""

    n_periods: int
    sim_total_kwh: float
    measured_total_kwh: float
    measured_mean_kwh: float
    nmbe_pct: float
    nmbe_raw_pct: float
    cv_rmse_pct: float
    ashrae_monthly_pass: bool
    notes: str = ""

    def summary(self) -> str:
        """Format human-readable summary of statistical fit."""
        pass_str = "PASS" if self.ashrae_monthly_pass else "FAIL"
        return (
            f"ASHRAE Guideline 14 Monthly Fit: [{pass_str}] | "
            f"NMBE={self.nmbe_pct:.2f}% (thresh ±5.0%), "
            f"CV(RMSE)={self.cv_rmse_pct:.2f}% (thresh 15.0%) | "
            f"Sim={self.sim_total_kwh:,.1f} kWh, Measured={self.measured_total_kwh:,.1f} kWh"
        )


@dataclass(frozen=True)
class PlausibilitySummary:
    """Consolidated headline demand and profile plausibility metrics."""

    annual_gross_kwh: float
    annual_served_kwh: float
    gross_eui_kwh_per_m2: float
    served_eui_kwh_per_m2: float
    peak_demand_kw: float
    peak_timestamp: str
    peak_hour: int
    load_factor: float
    monthly_profile_kwh: list[float]
    weekday_mean_kwh_per_day: float
    weekend_mean_kwh_per_day: float
    vacation_mean_kwh_per_day: float
    n_weekdays: int
    n_weekends: int
    n_vacation_days: int


def compute_ashrae_metrics(
    sim_monthly: Sequence[float],
    measured_monthly: Sequence[float],
) -> ASHRAEMetrics:
    """Calculate ASHRAE Guideline 14 NMBE and CV(RMSE) statistical metrics.

    Formulas per ASHRAE Guideline 14-2014 for monthly utility billing comparisons:
        NMBE = [sum(y_sim - y_meas) / ((n - 1) * y_meas_mean)] * 100%
        CV(RMSE) = [sqrt(sum((y_sim - y_meas)^2) / (n - 1)) / y_meas_mean] * 100%

    Parameters
    ----------
    sim_monthly : Sequence[float]
        Sequence of simulated monthly energy totals in kWh (length N, typically 12).
    measured_monthly : Sequence[float]
        Sequence of measured (or synthetic mock utility bill) monthly energy totals.

    Returns
    -------
    ASHRAEMetrics
        Calculated NMBE, CV(RMSE), and compliance indicator against ASHRAE Guideline 14
        monthly thresholds (|NMBE| <= 5%, CV(RMSE) <= 15%).
    """
    n = len(measured_monthly)
    if n == 0 or len(sim_monthly) != n:
        raise ValueError(f"Inputs must have equal positive lengths, got {len(sim_monthly)} and {n}")

    meas_total = float(sum(measured_monthly))
    sim_total = float(sum(sim_monthly))
    meas_mean = meas_total / n

    if meas_mean <= 0.0:
        raise ValueError(f"Measured mean must be positive, got {meas_mean}")

    diffs = [float(s) - float(m) for s, m in zip(sim_monthly, measured_monthly)]

    # Degrees of freedom: n - 1 (or n - p where p = 1 regression parameter)
    dof = max(1, n - 1)

    nmbe_pct = (sum(diffs) / (dof * meas_mean)) * 100.0
    nmbe_raw_pct = (sum(diffs) / (n * meas_mean)) * 100.0
    sum_sq_err = sum(d**2 for d in diffs)
    cv_rmse_pct = (math.sqrt(sum_sq_err / dof) / meas_mean) * 100.0

    # ASHRAE Guideline 14 monthly thresholds: |NMBE| <= 5%, CV(RMSE) <= 15%
    passes_threshold = (abs(nmbe_pct) <= 5.0) and (cv_rmse_pct <= 15.0)

    notes = (
        "Evaluation against ASHRAE Guideline 14 monthly thresholds (±5% NMBE, 15% CV(RMSE)). "
        "Caution: synthetic utility bills and bottom-up models are derived from the same audit "
        "and do not constitute independent empirical validation."
    )

    return ASHRAEMetrics(
        n_periods=n,
        sim_total_kwh=sim_total,
        measured_total_kwh=meas_total,
        measured_mean_kwh=meas_mean,
        nmbe_pct=nmbe_pct,
        nmbe_raw_pct=nmbe_raw_pct,
        cv_rmse_pct=cv_rmse_pct,
        ashrae_monthly_pass=passes_threshold,
        notes=notes,
    )


def compute_plausibility_summary(
    records: Sequence[HourlyRecord],
    building_area_m2: float = 2500.0,
    calendar: AcademicCalendar | None = None,
) -> PlausibilitySummary:
    """Compute annual headline KPIs, 12-month profile, and day-type mean consumptions.

    Parameters
    ----------
    records : Sequence[HourlyRecord]
        Complete annual sequence of 8,760 HourlyRecord objects.
    building_area_m2 : float, optional
        Facility gross floor area (default: 2,500 m²).
    calendar : AcademicCalendar, optional
        Academic schedule definition for day-type categorization.

    Returns
    -------
    PlausibilitySummary
        Structured object containing headline KPIs and day-type means.
    """
    if not records:
        raise ValueError("Cannot compute plausibility summary on empty records.")

    cal = calendar or AcademicCalendar()

    annual_gross_kwh = sum(r.demand_gross_kwh for r in records)
    annual_served_kwh = sum(r.demand_served_kwh for r in records)

    gross_eui = annual_gross_kwh / building_area_m2
    served_eui = annual_served_kwh / building_area_m2

    peak_rec = max(records, key=lambda r: r.demand_gross_kwh)
    peak_demand_kw = peak_rec.demand_gross_kwh
    peak_timestamp = peak_rec.timestamp
    peak_hour = peak_rec.hour

    load_factor = (
        annual_gross_kwh / (peak_demand_kw * len(records)) if peak_demand_kw > 0.0 else 0.0
    )

    # Monthly aggregation
    monthly_sums: dict[int, float] = defaultdict(float)
    daily_sums: dict[str, float] = defaultdict(float)

    for r in records:
        # ISO timestamp format: "YYYY-MM-DDTHH:MM:SS+08:00"
        month_idx = int(r.timestamp[5:7])
        date_str = r.timestamp[:10]
        monthly_sums[month_idx] += r.demand_gross_kwh
        daily_sums[date_str] += r.demand_gross_kwh

    monthly_profile_kwh = [monthly_sums[m] for m in range(1, 13)]

    # Day-type grouping: weekday vs weekend vs vacation
    weekday_days: list[float] = []
    weekend_days: list[float] = []
    vacation_days: list[float] = []

    for date_str, daily_kwh in sorted(daily_sums.items()):
        dt = pd.to_datetime(date_str)
        d = dt.date()
        is_break_or_hol = cal.is_break(d) or cal.is_holiday(d)
        is_weekend = dt.weekday() >= 5

        if is_break_or_hol:
            vacation_days.append(daily_kwh)
        elif is_weekend:
            weekend_days.append(daily_kwh)
        else:
            weekday_days.append(daily_kwh)

    weekday_mean = sum(weekday_days) / len(weekday_days) if weekday_days else 0.0
    weekend_mean = sum(weekend_days) / len(weekend_days) if weekend_days else 0.0
    vacation_mean = sum(vacation_days) / len(vacation_days) if vacation_days else 0.0

    return PlausibilitySummary(
        annual_gross_kwh=annual_gross_kwh,
        annual_served_kwh=annual_served_kwh,
        gross_eui_kwh_per_m2=gross_eui,
        served_eui_kwh_per_m2=served_eui,
        peak_demand_kw=peak_demand_kw,
        peak_timestamp=peak_timestamp,
        peak_hour=peak_hour,
        load_factor=load_factor,
        monthly_profile_kwh=monthly_profile_kwh,
        weekday_mean_kwh_per_day=weekday_mean,
        weekend_mean_kwh_per_day=weekend_mean,
        vacation_mean_kwh_per_day=vacation_mean,
        n_weekdays=len(weekday_days),
        n_weekends=len(weekend_days),
        n_vacation_days=len(vacation_days),
    )


def reconcile_solar_yield(
    transposed_poa_kwh_m2: float = 1945.98,
    baseline_pr: float = 0.77,
    target_specific_yield: float = 1298.0,
    simulated_specific_yield: float = 1508.74,
) -> dict[str, float]:
    """Reconcile simulated rooftop solar specific yield against regional benchmarks.

    Parameters
    ----------
    transposed_poa_kwh_m2 : float, optional
        Annual Plane-of-Array insolation in Batac (default: 1,945.98 kWh/m²).
    baseline_pr : float, optional
        Nominal system performance ratio per [D-08] (default: 0.77).
    target_specific_yield : float, optional
        Multi-system Luzon benchmark target from literature (default: 1,298 kWh/kWp).
    simulated_specific_yield : float, optional
        Simulated end-to-end AC specific yield in Batac (default: 1,508.74 kWh/kWp).

    Returns
    -------
    dict[str, float]
        Reconciliation breakdown with theoretical product, percentage deltas,
        and insolation comparison.
    """
    theoretical_poa_pr = transposed_poa_kwh_m2 * baseline_pr
    delta_vs_target_pct = (
        (simulated_specific_yield - target_specific_yield) / target_specific_yield
    ) * 100.0
    delta_vs_poa_pr_pct = (
        (simulated_specific_yield - theoretical_poa_pr) / theoretical_poa_pr
    ) * 100.0

    return {
        "transposed_poa_kwh_m2": transposed_poa_kwh_m2,
        "baseline_pr": baseline_pr,
        "theoretical_poa_pr_kwh_per_kwp": theoretical_poa_pr,
        "target_specific_yield_kwh_per_kwp": target_specific_yield,
        "simulated_specific_yield_kwh_per_kwp": simulated_specific_yield,
        "delta_vs_target_pct": delta_vs_target_pct,
        "delta_vs_poa_pr_pct": delta_vs_poa_pr_pct,
    }
