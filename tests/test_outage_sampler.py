"""Unit and statistical integration tests for stochastic outage sampler (OUT-001).

Verifies Poisson arrival processes, Lognormal duration distributions, Kolmogorov-Smirnov
goodness-of-fit, non-overlapping interval invariants, grid mask consistency, typhoon
solar depression attenuation, and Phase 2 contract conformance.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from ccis_sim.core.interfaces import OutageSchedule
from ccis_sim.core.models import OutageEvent, OutageType
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


# ===========================================================================
# 1. Reproducibility & Determinism Tests
# ===========================================================================

def test_deterministic_reproducibility():
    """Verify that identical seeds produce identical schedules for both regimes."""
    for regime in ("normal", "typhoon"):
        rng1 = np.random.default_rng(20261021)
        rng2 = np.random.default_rng(20261021)

        sched1 = sample_outage_schedule(regime, rng1)
        sched2 = sample_outage_schedule(regime, rng2)

        assert sched1.year_type == sched2.year_type == regime
        assert np.array_equal(sched1.grid_available, sched2.grid_available)
        assert np.array_equal(sched1.ghi_multiplier, sched2.ghi_multiplier)
        assert len(sched1.events) == len(sched2.events)

        for ev1, ev2 in zip(sched1.events, sched2.events):
            assert ev1.start_hour == ev2.start_hour
            assert math.isclose(ev1.duration_hours, ev2.duration_hours, abs_tol=1e-9)
            assert ev1.outage_type == ev2.outage_type
            assert math.isclose(ev1.solar_depression_factor, ev2.solar_depression_factor, abs_tol=1e-9)
            assert math.isclose(ev1.solar_depression_duration_hours, ev2.solar_depression_duration_hours, abs_tol=1e-9)


def test_distinct_seeds_produce_different_schedules():
    """Verify that distinct seeds generate different outage realizations."""
    rng1 = np.random.default_rng(1001)
    rng2 = np.random.default_rng(2002)

    sched1 = sample_outage_schedule("typhoon", rng1)
    sched2 = sample_outage_schedule("typhoon", rng2)

    assert not np.array_equal(sched1.grid_available, sched2.grid_available)


# ===========================================================================
# 2. Statistical Arrival Rate Tests (Poisson Process)
# ===========================================================================

def test_poisson_arrival_mean_over_2000_years():
    """Verify mean outage arrival count converges to lambda over >=2,000 sampled years."""
    n_years = 2500
    rng = np.random.default_rng(42)

    # Normal year: lambda = 3.0
    arrivals_normal = sample_raw_arrivals("normal", n_years, rng)
    mean_normal = float(np.mean(arrivals_normal))
    se_normal = math.sqrt(NORMAL_LAMBDA / n_years)
    # 3-sigma tolerance (~99.7% confidence)
    assert abs(mean_normal - NORMAL_LAMBDA) <= 3.0 * se_normal, (
        f"Normal mean {mean_normal} deviated from target {NORMAL_LAMBDA} by > 3 SE ({se_normal})"
    )

    # Typhoon year: lambda = 8.0
    arrivals_typhoon = sample_raw_arrivals("typhoon", n_years, rng)
    mean_typhoon = float(np.mean(arrivals_typhoon))
    se_typhoon = math.sqrt(TYPHOON_LAMBDA / n_years)
    assert abs(mean_typhoon - TYPHOON_LAMBDA) <= 3.0 * se_typhoon, (
        f"Typhoon mean {mean_typhoon} deviated from target {TYPHOON_LAMBDA} by > 3 SE ({se_typhoon})"
    )


# ===========================================================================
# 3. Kolmogorov-Smirnov Goodness-of-Fit Tests (Lognormal Distribution)
# ===========================================================================

def test_ks_goodness_of_fit_normal_regime():
    """Verify pre-discretization durations pass KS test against target and fail on wrong params."""
    rng = np.random.default_rng(2026)
    durations = sample_raw_durations("normal", 5000, rng)

    # Correct target parameters (mu=1.2, sigma=0.8) -> Must pass at alpha = 0.01
    res_correct = validate_duration_distribution(durations, year_type="normal", alpha=0.01)
    assert res_correct.ks_passed is True
    assert res_correct.ks_pvalue >= 0.01
    assert res_correct.passed is True

    # Deliberately wrong parameters (mu=2.5, sigma=1.2) -> Must fail
    res_wrong = validate_duration_distribution(
        durations,
        target_mu=2.5,
        target_sigma=1.2,
        alpha=0.01,
    )
    assert res_wrong.ks_passed is False
    assert res_wrong.ks_pvalue < 0.01
    assert res_wrong.passed is False


def test_ks_goodness_of_fit_typhoon_regime():
    """Verify typhoon durations pass KS test against target and fail on wrong params."""
    rng = np.random.default_rng(777)
    durations = sample_raw_durations("typhoon", 5000, rng)

    # Correct target parameters (mu=2.3, sigma=1.0) -> Must pass at alpha = 0.01
    res_correct = validate_duration_distribution(durations, year_type="typhoon", alpha=0.01)
    assert res_correct.ks_passed is True
    assert res_correct.ks_pvalue >= 0.01
    assert res_correct.passed is True

    # Deliberately wrong parameters (mu=1.0, sigma=0.5) -> Must fail
    res_wrong = validate_duration_distribution(
        durations,
        target_mu=1.0,
        target_sigma=0.5,
        alpha=0.01,
    )
    assert res_wrong.ks_passed is False
    assert res_wrong.ks_pvalue < 0.01
    assert res_wrong.passed is False


def test_validator_with_arrival_counts():
    """Verify validate_duration_distribution evaluates arrival counts when provided."""
    rng = np.random.default_rng(999)
    durations = sample_raw_durations("normal", 3000, rng)
    arrivals_consistent = sample_raw_arrivals("normal", 2000, rng)

    res = validate_duration_distribution(
        durations,
        year_type="normal",
        arrival_counts=arrivals_consistent,
        alpha=0.01,
    )
    assert res.passed is True
    assert res.arrival_passed is True
    assert res.mean_arrivals is not None
    assert math.isclose(res.mean_arrivals, NORMAL_LAMBDA, rel_tol=0.05)

    # Inconsistent arrivals (e.g. lambda=8 passed for normal test)
    arrivals_inconsistent = sample_raw_arrivals("typhoon", 2000, rng)
    res_bad = validate_duration_distribution(
        durations,
        year_type="normal",
        arrival_counts=arrivals_inconsistent,
        alpha=0.01,
    )
    assert res_bad.arrival_passed is False
    assert res_bad.passed is False


def test_validator_edge_cases():
    """Verify validation error handling for invalid input data."""
    with pytest.raises(ValueError, match="Need at least 2 duration samples"):
        validate_duration_distribution([5.0])

    with pytest.raises(ValueError, match="strictly positive"):
        validate_duration_distribution([-1.0, 5.0])

    with pytest.raises(ValueError, match="Unknown year_type"):
        validate_duration_distribution([2.0, 3.0], year_type="invalid")

    with pytest.raises(ValueError, match="arrival_counts array must not be empty"):
        validate_duration_distribution([2.0, 3.0], year_type="normal", arrival_counts=[])


# ===========================================================================
# 4. Outage Event Invariants & Discretization (No Overlaps, [1, N] Bounds)
# ===========================================================================

@pytest.mark.parametrize("regime", ["normal", "typhoon"])
def test_events_bounds_and_no_overlaps_across_many_seeds(regime: str):
    """Verify that events always lie within [1, N], duration >= 1, and never overlap."""
    n_hours = 8760
    rng = np.random.default_rng(54321)

    for _ in range(50):
        sched = sample_outage_schedule(regime, rng, n_hours=n_hours)
        events = sched.events

        for i, ev in enumerate(events):
            # Start hour in [1, N]
            assert 1 <= ev.start_hour <= n_hours, (
                f"start_hour {ev.start_hour} outside [1, {n_hours}]"
            )
            # Duration must be integer hours >= 1
            assert ev.duration_hours >= 1.0
            assert ev.duration_hours == math.floor(ev.duration_hours)
            # End hour must not exceed N + 1
            assert ev.end_hour <= n_hours + 1, (
                f"end_hour {ev.end_hour} exceeded {n_hours + 1}"
            )

            # Check strict separation between consecutive events (no overlaps)
            if i + 1 < len(events):
                next_ev = events[i + 1]
                assert ev.end_hour <= next_ev.start_hour, (
                    f"Overlapping events: ev[{i}] ends at {ev.end_hour}, "
                    f"ev[{i+1}] starts at {next_ev.start_hour}"
                )


# ===========================================================================
# 5. Grid Available Mask & Event Agreement
# ===========================================================================

@pytest.mark.parametrize("regime", ["normal", "typhoon"])
def test_grid_available_mask_agrees_with_events(regime: str):
    """Verify that grid_available mask strictly matches active hours of OutageEvents."""
    rng = np.random.default_rng(98765)
    n_hours = 8760

    for _ in range(25):
        sched = sample_outage_schedule(regime, rng, n_hours=n_hours)
        assert len(sched.grid_available) == n_hours

        # Test every single hour
        for h in range(1, n_hours + 1):
            is_blackout_from_events = any(ev.is_active_at(h) for ev in sched.events)
            is_blackout_from_mask = not sched.grid_available[h - 1]
            assert is_blackout_from_events == is_blackout_from_mask, (
                f"Disagreement at hour {h}: event={is_blackout_from_events}, mask={is_blackout_from_mask}"
            )

        # Total blackout hours must equal sum of discrete event durations
        total_event_hours = sum(int(ev.duration_hours) for ev in sched.events)
        total_mask_hours = int(np.sum(~sched.grid_available))
        assert total_event_hours == total_mask_hours


# ===========================================================================
# 6. Solar GHI Multiplier Tests (Normal vs Typhoon)
# ===========================================================================

def test_normal_year_ghi_multiplier_all_ones():
    """Verify normal weather years have all-ones GHI multiplier array."""
    rng = np.random.default_rng(1234)
    sched = sample_outage_schedule("normal", rng)

    assert len(sched.ghi_multiplier) == 8760
    assert np.all(sched.ghi_multiplier == 1.0)

    for ev in sched.events:
        assert ev.solar_depression_factor == 1.0
        assert ev.solar_depression_duration_hours == 0.0


def test_typhoon_solar_depression_multipliers_and_windows():
    """Verify typhoon solar depression factor is in [0.20, 0.30] inside episodes and 1.0 outside."""
    rng = np.random.default_rng(202610)
    found_depressed = False

    for _ in range(50):
        sched = sample_outage_schedule("typhoon", rng)
        mult = sched.ghi_multiplier
        assert len(mult) == 8760

        # Multiplier must always be non-negative and finite
        assert np.all(np.isfinite(mult))
        assert np.all(mult >= 0.0)

        # Values must be either 1.0 or within [0.20, 0.30]
        is_depressed = mult < 1.0
        if np.any(is_depressed):
            found_depressed = True
            depressed_vals = mult[is_depressed]
            assert np.all(depressed_vals >= TYPHOON_GHI_MULTIPLIER_MIN - 1e-9)
            assert np.all(depressed_vals <= TYPHOON_GHI_MULTIPLIER_MAX + 1e-9)

        # Verify storm duration on individual events with depression
        for ev in sched.events:
            if ev.solar_depression_factor < 1.0:
                assert TYPHOON_GHI_MULTIPLIER_MIN <= ev.solar_depression_factor <= TYPHOON_GHI_MULTIPLIER_MAX
                assert ev.solar_depression_duration_hours in (
                    float(d * 24) for d in range(TYPHOON_STORM_DAYS_MIN, TYPHOON_STORM_DAYS_MAX + 1)
                )

    assert found_depressed, "Expected at least one depressed window in 50 typhoon runs."


# ===========================================================================
# 7. apply_ghi_multiplier Function Tests
# ===========================================================================

def test_apply_ghi_multiplier_pure_function_and_accuracy():
    """Verify apply_ghi_multiplier returns a scaled copy without mutating the input."""
    # Synthetic weather DataFrame
    n = 24
    ghi_original = np.array([500.0] * n, dtype=np.float64)
    weather_df = pd.DataFrame({
        "hour": np.arange(1, n + 1),
        "timestamp": [f"2026-01-01T{h:02d}:00:00+08:00" for h in range(n)],
        "t_amb": [28.0] * n,
        "rh": [75.0] * n,
        "ghi": ghi_original.copy(),
    })

    # Schedule with 25% depression for hours 5 to 10
    mult = np.ones(n, dtype=np.float64)
    mult[4:10] = 0.25
    sched = OutageSchedule(
        events=(),
        grid_available=np.ones(n, dtype=bool),
        year_type="typhoon",
        ghi_multiplier=mult,
    )

    result_df = apply_ghi_multiplier(weather_df, sched)

    # Immutability check: original weather_df untouched
    assert np.all(weather_df["ghi"].to_numpy() == 500.0)

    # Transformed check
    expected_ghi = np.array([500.0] * n, dtype=np.float64)
    expected_ghi[4:10] = 125.0
    assert np.allclose(result_df["ghi"].to_numpy(), expected_ghi)


def test_apply_ghi_multiplier_validation_errors():
    """Verify input validation errors for apply_ghi_multiplier."""
    sched = OutageSchedule(
        events=(),
        grid_available=np.ones(10, dtype=bool),
        year_type="normal",
    )

    # Not a DataFrame
    with pytest.raises(TypeError, match="must be a pandas DataFrame"):
        apply_ghi_multiplier({"ghi": [100.0] * 10}, sched)  # type: ignore

    # Missing 'ghi' column
    df_missing_ghi = pd.DataFrame({"t_amb": [25.0] * 10})
    with pytest.raises(ValueError, match="must contain a 'ghi' column"):
        apply_ghi_multiplier(df_missing_ghi, sched)

    # Length mismatch
    df_mismatched_len = pd.DataFrame({"ghi": [100.0] * 5})
    with pytest.raises(ValueError, match="Length mismatch"):
        apply_ghi_multiplier(df_mismatched_len, sched)


# ===========================================================================
# 8. Contract Signature Conformance & Horizon Flexibility
# ===========================================================================

def test_contract_signature_conformance():
    """Verify sample_outage_schedule adheres strictly to interface contracts."""
    rng = np.random.default_rng(101)

    # Default n_hours = 8760
    sched = sample_outage_schedule("normal", rng)
    assert len(sched) == DEFAULT_ANNUAL_HOURS
    assert len(sched.grid_available) == DEFAULT_ANNUAL_HOURS
    assert len(sched.ghi_multiplier) == DEFAULT_ANNUAL_HOURS

    # Custom horizon n_hours = 168 (1 week)
    sched_week = sample_outage_schedule("typhoon", rng, n_hours=168)
    assert len(sched_week) == 168
    assert len(sched_week.grid_available) == 168
    assert len(sched_week.ghi_multiplier) == 168

    # Invalid regime
    with pytest.raises(ValueError, match="year_type must be 'normal' or 'typhoon'"):
        sample_outage_schedule("unsupported_regime", rng)

    # Invalid n_hours
    with pytest.raises(ValueError, match="n_hours must be positive"):
        sample_outage_schedule("normal", rng, n_hours=0)


def test_zero_arrival_case():
    """Verify handling when Poisson draw yields zero events."""
    # Mock RNG that returns 0 for poisson
    class ZeroPoissonRNG:
        def poisson(self, lam: float) -> int:
            return 0

    sched = sample_outage_schedule("normal", ZeroPoissonRNG())  # type: ignore
    assert len(sched.events) == 0
    assert np.all(sched.grid_available)
    assert np.all(sched.ghi_multiplier == 1.0)
