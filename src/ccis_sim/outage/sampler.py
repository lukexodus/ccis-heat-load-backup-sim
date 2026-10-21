"""Stochastic utility outage generation and typhoon solar depression sampler.

Implements Poisson arrival processes, Lognormal duration distributions,
integer-hour discretization, interval merging, and typhoon multi-day solar
depression coupling per decisions [D-11], [D-26], and [D-33].
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd
import scipy.stats as stats

from ccis_sim.core.interfaces import OutageSchedule
from ccis_sim.core.models import OutageEvent, OutageType

# ---------------------------------------------------------------------------
# Stochastic Distribution Parameters per [D-11]
# ---------------------------------------------------------------------------
NORMAL_LAMBDA: float = 3.0
"""Annual Poisson arrival rate for normal / baseline weather years (events/year)."""

NORMAL_LOGNORMAL_MU: float = 1.2
"""Log-mean parameter mu for normal year duration distribution on ln(hours)."""

NORMAL_LOGNORMAL_SIGMA: float = 0.8
"""Log-standard-deviation parameter sigma for normal year duration distribution."""

TYPHOON_LAMBDA: float = 8.0
"""Annual Poisson arrival rate for typhoon / extreme weather years (events/year)."""

TYPHOON_LOGNORMAL_MU: float = 2.3
"""Log-mean parameter mu for typhoon year duration distribution on ln(hours)."""

TYPHOON_LOGNORMAL_SIGMA: float = 1.0
"""Log-standard-deviation parameter sigma for typhoon year duration distribution."""

TYPHOON_STORM_DAYS_MIN: int = 3
"""Minimum duration of typhoon solar depression window in consecutive days per [D-11]."""

TYPHOON_STORM_DAYS_MAX: int = 5
"""Maximum duration of typhoon solar depression window in consecutive days per [D-11]."""

TYPHOON_GHI_MULTIPLIER_MIN: float = 0.20
"""Minimum solar GHI multiplier during active typhoon depression window (20% normal GHI)."""

TYPHOON_GHI_MULTIPLIER_MAX: float = 0.30
"""Maximum solar GHI multiplier during active typhoon depression window (30% normal GHI)."""

DEFAULT_ANNUAL_HOURS: int = 8760
"""Standard hours in an annual simulation cycle."""


@dataclass(frozen=True)
class OutageDistributionValidationResult:
    """Goodness-of-fit validation outcome for outage duration and arrival processes.

    Returned by validate_duration_distribution per OUT-001.4.
    """

    ks_statistic: float
    """Kolmogorov-Smirnov test statistic comparing sample durations to target Lognormal."""

    ks_pvalue: float
    """Two-sided p-value from the Kolmogorov-Smirnov test."""

    ks_passed: bool
    """True if ks_pvalue >= alpha (null hypothesis of target Lognormal not rejected)."""

    alpha: float
    """Significance level threshold (e.g. 0.01)."""

    sample_size: int
    """Number of sampled durations evaluated."""

    target_mu: float
    """Target Lognormal log-mean parameter."""

    target_sigma: float
    """Target Lognormal log-std parameter."""

    arrival_passed: bool | None = None
    """True if arrival count is statistically consistent with Poisson(lambda), or None if skipped."""

    mean_arrivals: float | None = None
    """Sample mean annual arrival count across evaluated years, or None if skipped."""

    target_lambda: float | None = None
    """Target Poisson arrival rate parameter, or None if skipped."""

    arrival_pvalue: float | None = None
    """Two-sided p-value from arrival rate z-test, or None if skipped."""

    passed: bool = True
    """Overall test outcome: True if all evaluated tests pass."""

    details: str = ""
    """Human-readable diagnostic summary."""


def sample_raw_durations(
    year_type: str,
    n_samples: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """Sample continuous pre-discretization outage durations from target Lognormal(mu, sigma).

    Parameters
    ----------
    year_type : str
        Climate reliability regime: 'normal' or 'typhoon'.
    n_samples : int
        Number of duration samples to draw.
    rng : np.random.Generator
        Deterministic numpy random number generator.

    Returns
    -------
    np.ndarray
        1D float array of continuous duration samples in hours.
    """
    regime = year_type.strip().lower()
    if regime == "normal":
        mu, sigma = NORMAL_LOGNORMAL_MU, NORMAL_LOGNORMAL_SIGMA
    elif regime == "typhoon":
        mu, sigma = TYPHOON_LOGNORMAL_MU, TYPHOON_LOGNORMAL_SIGMA
    else:
        raise ValueError(f"year_type must be 'normal' or 'typhoon', got '{year_type}'")

    if n_samples <= 0:
        raise ValueError(f"n_samples must be positive, got {n_samples}")

    return rng.lognormal(mean=mu, sigma=sigma, size=n_samples)


def sample_raw_arrivals(
    year_type: str,
    n_years: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """Sample annual outage arrival counts from target Poisson(lambda).

    Parameters
    ----------
    year_type : str
        Climate reliability regime: 'normal' or 'typhoon'.
    n_years : int
        Number of annual arrival counts to draw.
    rng : np.random.Generator
        Deterministic numpy random number generator.

    Returns
    -------
    np.ndarray
        1D integer array of annual arrival counts.
    """
    regime = year_type.strip().lower()
    if regime == "normal":
        lam = NORMAL_LAMBDA
    elif regime == "typhoon":
        lam = TYPHOON_LAMBDA
    else:
        raise ValueError(f"year_type must be 'normal' or 'typhoon', got '{year_type}'")

    if n_years <= 0:
        raise ValueError(f"n_years must be positive, got {n_years}")

    return rng.poisson(lam=lam, size=n_years)


def sample_outage_schedule(
    year_type: str,
    rng: np.random.Generator,
    *,
    n_hours: int = DEFAULT_ANNUAL_HOURS,
) -> OutageSchedule:
    """Generate stochastic Poisson outage arrivals, lognormal durations, and typhoon storm windows.

    Conforms to Phase 2 interface contract (docs/context/phase2-interface-contract.md).
    All stochasticity is sourced exclusively from the provided `rng` instance.

    Parameters
    ----------
    year_type : str
        Reliability regime: 'normal' (lambda=3, mu=1.2, sigma=0.8) or
        'typhoon' (lambda=8, mu=2.3, sigma=1.0) per [D-11].
    rng : np.random.Generator
        Deterministic numpy random number generator.
    n_hours : int, optional
        Simulation horizon in hours (defaults to 8,760 for an annual cycle).

    Returns
    -------
    OutageSchedule
        Immutable schedule with non-overlapping OutageEvent records, grid_available
        boolean mask, and solar ghi_multiplier array.
    """
    regime = year_type.strip().lower()
    if regime not in ("normal", "typhoon"):
        raise ValueError(f"year_type must be 'normal' or 'typhoon', got '{year_type}'")

    if n_hours <= 0:
        raise ValueError(f"n_hours must be positive, got {n_hours}")

    if regime == "normal":
        lam = NORMAL_LAMBDA
        mu = NORMAL_LOGNORMAL_MU
        sigma = NORMAL_LOGNORMAL_SIGMA
        outage_type = OutageType.NORMAL
    else:
        lam = TYPHOON_LAMBDA
        mu = TYPHOON_LOGNORMAL_MU
        sigma = TYPHOON_LOGNORMAL_SIGMA
        outage_type = OutageType.TYPHOON

    # Sample arrival count from Poisson process
    k = int(rng.poisson(lam=lam))

    if k == 0:
        return OutageSchedule(
            events=(),
            grid_available=np.ones(n_hours, dtype=bool),
            year_type=regime,  # type: ignore[arg-type]
            ghi_multiplier=np.ones(n_hours, dtype=np.float64),
        )

    # [ASSUMPTION] Arrival start hours are sampled uniformly over the annual timeline [1, n_hours].
    # Uniform start distribution is adopted as the rigorous baseline, deferring seasonal typhoon
    # clustering (June-November) to future sensitivity refinements per [D-33].
    raw_starts = rng.integers(1, n_hours + 1, size=k)
    raw_durations = rng.lognormal(mean=mu, sigma=sigma, size=k)

    # [ASSUMPTION] Discretization to integer hours via ceiling (math.ceil) with minimum 1 hour:
    # duration_h = max(1, int(math.ceil(d_raw))). This ensures any non-zero outage duration spans
    # at least one discrete simulation hour, introducing a slight upward bias (+0.5h on average).
    order = np.argsort(raw_starts)
    sorted_starts = [int(raw_starts[i]) for i in order]
    sorted_durations = [max(1, int(math.ceil(raw_durations[i]))) for i in order]

    # [ASSUMPTION] Overlapping or contiguous outage intervals are merged into a single continuous
    # event with start = start_1 and end = max(end_1, end_2). This prevents simultaneous/nested
    # outages and ensures grid_available is strictly consistent with discrete OutageEvents.
    # [ASSUMPTION] Events extending past n_hours are clipped at hour n_hours + 1.
    merged_intervals: list[tuple[int, int]] = []
    for s, d in zip(sorted_starts, sorted_durations):
        if s > n_hours:
            continue
        e = min(s + d, n_hours + 1)
        if not merged_intervals:
            merged_intervals.append((s, e))
        else:
            last_s, last_e = merged_intervals[-1]
            if s <= last_e:
                # Contiguous or overlapping: merge
                merged_intervals[-1] = (last_s, max(last_e, e))
            else:
                merged_intervals.append((s, e))

    # Build grid_available boolean mask (True = connected, False = blackout)
    grid_available = np.ones(n_hours, dtype=bool)
    for s, e in merged_intervals:
        grid_available[s - 1 : e - 1] = False

    # Build solar GHI multiplier and OutageEvents
    ghi_multiplier = np.ones(n_hours, dtype=np.float64)
    events: list[OutageEvent] = []

    if regime == "normal":
        for s, e in merged_intervals:
            events.append(
                OutageEvent(
                    start_hour=s,
                    duration_hours=float(e - s),
                    outage_type=outage_type,
                    solar_depression_factor=1.0,
                    solar_depression_duration_hours=0.0,
                )
            )
    else:
        # Typhoon regime: assign solar depression windows
        # [ASSUMPTION] Resolve [D-11] ambiguity ("depressed solar irradiance (20-30% normal GHI)")
        # as an attenuation multiplier m in [0.20, 0.30] (GHI reduced to 20-30% of normal clear-sky
        # level due to dense typhoon cloud cover) per [D-33].
        # [ASSUMPTION] 1 to 2 storm episodes are coupled with the longest outage events, lasting
        # 3 to 5 consecutive days (72-120 hours) starting at the outage event start hour.
        if merged_intervals:
            # Rank merged intervals by duration descending to identify major storm events
            durations = [e - s for s, e in merged_intervals]
            sorted_by_duration = np.argsort(durations)[::-1]
            n_episodes = min(len(merged_intervals), int(rng.integers(1, 3)))
            storm_indices = set(sorted_by_duration[:n_episodes])

            storm_params: dict[int, tuple[float, float]] = {}
            for idx in storm_indices:
                storm_days = int(rng.integers(TYPHOON_STORM_DAYS_MIN, TYPHOON_STORM_DAYS_MAX + 1))
                dep_hours = float(storm_days * 24)
                dep_factor = float(rng.uniform(TYPHOON_GHI_MULTIPLIER_MIN, TYPHOON_GHI_MULTIPLIER_MAX))
                storm_params[idx] = (dep_factor, dep_hours)

                s_storm = merged_intervals[idx][0]
                dep_end = min(n_hours, s_storm - 1 + int(dep_hours))
                ghi_multiplier[s_storm - 1 : dep_end] = np.minimum(
                    ghi_multiplier[s_storm - 1 : dep_end],
                    dep_factor,
                )

            for idx, (s, e) in enumerate(merged_intervals):
                if idx in storm_params:
                    factor, dur_h = storm_params[idx]
                    events.append(
                        OutageEvent(
                            start_hour=s,
                            duration_hours=float(e - s),
                            outage_type=OutageType.TYPHOON,
                            solar_depression_factor=factor,
                            solar_depression_duration_hours=dur_h,
                        )
                    )
                else:
                    events.append(
                        OutageEvent(
                            start_hour=s,
                            duration_hours=float(e - s),
                            outage_type=OutageType.TYPHOON,
                            solar_depression_factor=1.0,
                            solar_depression_duration_hours=0.0,
                        )
                    )

    return OutageSchedule(
        events=tuple(events),
        grid_available=grid_available,
        year_type=regime,  # type: ignore[arg-type]
        ghi_multiplier=ghi_multiplier,
    )


def apply_ghi_multiplier(
    weather_df: pd.DataFrame,
    schedule: OutageSchedule,
) -> pd.DataFrame:
    """Attenuate solar GHI during active typhoon depression windows.

    Conforms to Phase 2 interface contract (docs/context/phase2-interface-contract.md).
    Returns a copy of weather_df with the 'ghi' column scaled by schedule.ghi_multiplier.

    Parameters
    ----------
    weather_df : pd.DataFrame
        Hourly weather dataframe containing at least a 'ghi' column.
    schedule : OutageSchedule
        Outage schedule containing the ghi_multiplier array.

    Returns
    -------
    pd.DataFrame
        Deep copy of weather_df with 'ghi' multiplied by schedule.ghi_multiplier.
    """
    if not isinstance(weather_df, pd.DataFrame):
        raise TypeError(f"weather_df must be a pandas DataFrame, got {type(weather_df)}")

    if "ghi" not in weather_df.columns:
        raise ValueError("weather_df must contain a 'ghi' column.")

    if len(weather_df) != len(schedule.ghi_multiplier):
        raise ValueError(
            f"Length mismatch: weather_df ({len(weather_df)}) vs "
            f"schedule.ghi_multiplier ({len(schedule.ghi_multiplier)})"
        )

    df_copy = weather_df.copy(deep=True)
    df_copy["ghi"] = df_copy["ghi"] * schedule.ghi_multiplier
    return df_copy


def validate_duration_distribution(
    durations: Sequence[float] | np.ndarray,
    year_type: str = "normal",
    *,
    target_mu: float | None = None,
    target_sigma: float | None = None,
    alpha: float = 0.01,
    arrival_counts: Sequence[int] | np.ndarray | None = None,
    target_lambda: float | None = None,
) -> OutageDistributionValidationResult:
    """Validate sample outage durations against Lognormal and arrival counts against Poisson.

    Performs a two-sided Kolmogorov-Smirnov test on pre-discretization durations against
    the continuous Lognormal(mu, sigma) distribution, and an optional arrival count z-test
    against Poisson(lambda) per OUT-001.4.

    Parameters
    ----------
    durations : Sequence[float] | np.ndarray
        Continuous (pre-discretization) duration samples in hours.
    year_type : str, optional
        Regime to determine default parameters: 'normal' or 'typhoon'.
    target_mu : float, optional
        Target log-mean parameter (overrides year_type default if provided).
    target_sigma : float, optional
        Target log-std parameter (overrides year_type default if provided).
    alpha : float, optional
        Significance level threshold (defaults to 0.01).
    arrival_counts : Sequence[int] | np.ndarray, optional
        Sample annual arrival counts from multiple simulated years.
    target_lambda : float, optional
        Target Poisson arrival rate (overrides year_type default if provided).

    Returns
    -------
    OutageDistributionValidationResult
        Diagnostic object containing test statistics, p-values, and pass/fail verdicts.
    """
    regime = year_type.strip().lower()

    # Resolve target Lognormal parameters
    if target_mu is not None and target_sigma is not None:
        mu = float(target_mu)
        sigma = float(target_sigma)
    elif regime == "normal":
        mu = NORMAL_LOGNORMAL_MU
        sigma = NORMAL_LOGNORMAL_SIGMA
    elif regime == "typhoon":
        mu = TYPHOON_LOGNORMAL_MU
        sigma = TYPHOON_LOGNORMAL_SIGMA
    else:
        raise ValueError(
            f"Unknown year_type '{year_type}', expected 'normal' or 'typhoon' "
            "unless target_mu and target_sigma are explicitly provided."
        )

    # Resolve target Poisson arrival rate
    if target_lambda is not None:
        lam = float(target_lambda)
    elif regime == "normal":
        lam = NORMAL_LAMBDA
    elif regime == "typhoon":
        lam = TYPHOON_LAMBDA
    else:
        lam = NORMAL_LAMBDA

    d_arr = np.asarray(durations, dtype=np.float64)
    if len(d_arr) < 2:
        raise ValueError("Need at least 2 duration samples to perform Kolmogorov-Smirnov test.")

    if np.any(d_arr <= 0.0):
        raise ValueError("Durations must be strictly positive for Lognormal distribution.")

    # Two-sided Kolmogorov-Smirnov test
    # In scipy.stats.lognorm: s = sigma, loc = 0, scale = exp(mu)
    ks_res = stats.kstest(d_arr, "lognorm", args=(sigma, 0.0, np.exp(mu)))
    ks_stat = float(ks_res.statistic)
    ks_pval = float(ks_res.pvalue)
    ks_passed = bool(ks_pval >= alpha)

    # Optional Poisson arrival check
    arrival_passed: bool | None = None
    mean_arrivals: float | None = None
    arrival_pval: float | None = None

    if arrival_counts is not None:
        k_arr = np.asarray(arrival_counts, dtype=np.float64)
        m_years = len(k_arr)
        if m_years == 0:
            raise ValueError("arrival_counts array must not be empty.")

        mean_arrivals = float(np.mean(k_arr))
        # For sample mean from Poisson(lambda), standard error is sqrt(lambda / M)
        se = math.sqrt(lam / m_years)
        if se > 0.0:
            z = (mean_arrivals - lam) / se
            # Two-sided normal test
            arrival_pval = float(2.0 * (1.0 - stats.norm.cdf(abs(z))))
            arrival_passed = bool(arrival_pval >= alpha)
        else:
            arrival_passed = bool(math.isclose(mean_arrivals, lam))
            arrival_pval = 1.0 if arrival_passed else 0.0

    overall_passed = ks_passed and (arrival_passed is None or arrival_passed)

    details = (
        f"KS Test: stat={ks_stat:.4f}, pval={ks_pval:.4e}, passed={ks_passed} (alpha={alpha}). "
        f"Target Lognormal(mu={mu}, sigma={sigma}), N={len(d_arr)}."
    )
    if arrival_counts is not None:
        details += (
            f" Arrival Check: mean={mean_arrivals:.4f}, target={lam:.4f}, "
            f"pval={arrival_pval:.4e}, passed={arrival_passed}."
        )

    return OutageDistributionValidationResult(
        ks_statistic=ks_stat,
        ks_pvalue=ks_pval,
        ks_passed=ks_passed,
        alpha=alpha,
        sample_size=len(d_arr),
        target_mu=mu,
        target_sigma=sigma,
        arrival_passed=arrival_passed,
        mean_arrivals=mean_arrivals,
        target_lambda=lam,
        arrival_pvalue=arrival_pval,
        passed=overall_passed,
        details=details,
    )
