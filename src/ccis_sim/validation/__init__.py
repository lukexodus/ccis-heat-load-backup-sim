"""Validation, verification, and plausibility auditing package for CCIS microgrid simulation."""

from __future__ import annotations

from ccis_sim.validation.audit import (
    AuditResult,
    audit_run,
    run_standard_audit_matrix,
)
from ccis_sim.validation.plausibility import (
    ASHRAEMetrics,
    PlausibilitySummary,
    compute_ashrae_metrics,
    compute_plausibility_summary,
    reconcile_solar_yield,
)
from ccis_sim.validation.sensitivity import (
    SensitivityPoint,
    SensitivitySweepResult,
    run_oat_sensitivity_analysis,
)

__all__ = [
    "AuditResult",
    "audit_run",
    "run_standard_audit_matrix",
    "ASHRAEMetrics",
    "PlausibilitySummary",
    "compute_ashrae_metrics",
    "compute_plausibility_summary",
    "reconcile_solar_yield",
    "SensitivityPoint",
    "SensitivitySweepResult",
    "run_oat_sensitivity_analysis",
]
