"""Stochastic utility outage generation (Poisson/Lognormal) and priority load shedding."""

from ccis_sim.outage.shedding import (
    TierAuditComparison,
    UnservedTracker,
    compute_tier_audit_shares,
    shed_for_hour,
)

__all__ = [
    "shed_for_hour",
    "UnservedTracker",
    "TierAuditComparison",
    "compute_tier_audit_shares",
]
