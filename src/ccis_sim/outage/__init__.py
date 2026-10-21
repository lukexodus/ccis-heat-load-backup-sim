"""Stochastic utility outage generation (Poisson/Lognormal) and priority load shedding."""

from ccis_sim.outage.sampler import (
    DEFAULT_ANNUAL_HOURS,
    NORMAL_LAMBDA,
    NORMAL_LOGNORMAL_MU,
    NORMAL_LOGNORMAL_SIGMA,
    TYPHOON_GHI_MULTIPLIER_MAX,
    TYPHOON_GHI_MULTIPLIER_MIN,
    TYPHOON_LAMBDA,
    TYPHOON_LOGNORMAL_MU,
    TYPHOON_LOGNORMAL_SIGMA,
    TYPHOON_STORM_DAYS_MAX,
    TYPHOON_STORM_DAYS_MIN,
    OutageDistributionValidationResult,
    apply_ghi_multiplier,
    sample_outage_schedule,
    sample_raw_arrivals,
    sample_raw_durations,
    validate_duration_distribution,
)
from ccis_sim.outage.shedding import (
    TierAuditComparison,
    UnservedTracker,
    compute_tier_audit_shares,
    shed_for_hour,
)

__all__ = [
    # Shedding (OUT-002)
    "shed_for_hour",
    "UnservedTracker",
    "TierAuditComparison",
    "compute_tier_audit_shares",
    # Sampler (OUT-001)
    "sample_outage_schedule",
    "apply_ghi_multiplier",
    "validate_duration_distribution",
    "OutageDistributionValidationResult",
    "sample_raw_durations",
    "sample_raw_arrivals",
    "NORMAL_LAMBDA",
    "NORMAL_LOGNORMAL_MU",
    "NORMAL_LOGNORMAL_SIGMA",
    "TYPHOON_LAMBDA",
    "TYPHOON_LOGNORMAL_MU",
    "TYPHOON_LOGNORMAL_SIGMA",
    "TYPHOON_STORM_DAYS_MIN",
    "TYPHOON_STORM_DAYS_MAX",
    "TYPHOON_GHI_MULTIPLIER_MIN",
    "TYPHOON_GHI_MULTIPLIER_MAX",
    "DEFAULT_ANNUAL_HOURS",
]
