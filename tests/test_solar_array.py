"""Unit and integration test suite for solar array sizing and inverter clipping.

Verifies:
1. Scenario capacity scaling across matrix (0, 50, 100, 200 kWp per [D-18]).
2. Strict zero AC output at 0 kWp capacity and during nighttime hours.
3. Linear capacity scaling below inverter clipping threshold.
4. Inverter continuous AC clipping at high irradiance.
5. Invariant: AC generation never exceeds inverter rated AC capacity.
6. PR budget decomposition factors multiply to the documented 0.77 baseline.
7. Array preservation: non-negative, finite, no NaNs, shape preservation.
8. Determinism across repeated evaluations.
9. Contract signature conformance per docs/context/phase2-interface-contract.md.
"""

from __future__ import annotations

import numpy as np
import pytest

from ccis_sim.core.models import SolarArray
from ccis_sim.solar.array import (
    ASSUMED_MEAN_THERMAL_FACTOR,
    DEFAULT_AC_WIRING_FACTOR,
    DEFAULT_AVAILABILITY_FACTOR,
    DEFAULT_DC_AC_RATIO,
    DEFAULT_DC_WIRING_FACTOR,
    DEFAULT_INVERTER_EFFICIENCY,
    DEFAULT_MISMATCH_FACTOR,
    DEFAULT_SOILING_FACTOR,
    compute_ac_generation,
    get_inverter_ac_rating,
    get_non_thermal_bos_factor,
)


@pytest.fixture
def synthetic_dc_profile() -> np.ndarray:
    """Synthetic 24-hour DC generation profile (kW DC per kWp)."""
    # 0 at night (hours 0-5 and 19-23), ramping to ~0.75 kW/kWp at solar noon
    hours = np.arange(24)
    profile = np.zeros(24, dtype=np.float64)
    day_mask = (hours >= 6) & (hours <= 18)
    profile[day_mask] = 0.75 * np.sin(np.pi * (hours[day_mask] - 6.0) / 12.0)
    return profile


def test_contract_signature_conformance(synthetic_dc_profile: np.ndarray) -> None:
    """Verify compute_ac_generation matches exact contract signature."""
    array = SolarArray(capacity_kwp=100.0)
    ac_gen = compute_ac_generation(synthetic_dc_profile, array)

    assert isinstance(ac_gen, np.ndarray)
    assert ac_gen.shape == (24,)
    assert ac_gen.dtype == np.float64


@pytest.mark.parametrize("capacity_kwp", [0.0, 50.0, 100.0, 200.0])
def test_scenario_capacities_execution(synthetic_dc_profile: np.ndarray, capacity_kwp: float) -> None:
    """Verify execution across all four scenario matrix capacities (0, 50, 100, 200 kWp)."""
    array = SolarArray(capacity_kwp=capacity_kwp)
    ac_gen = compute_ac_generation(synthetic_dc_profile, array)

    assert len(ac_gen) == len(synthetic_dc_profile)
    assert np.all(np.isfinite(ac_gen))
    assert np.all(ac_gen >= 0.0)

    if capacity_kwp == 0.0:
        assert np.all(ac_gen == 0.0), "0 kWp array must produce strictly 0.0 AC power"
    else:
        assert np.max(ac_gen) > 0.0, f"{capacity_kwp} kWp array must produce positive AC power during day"


def test_zero_nighttime_and_zero_capacity() -> None:
    """Verify strict 0.0 generation at night and for zero capacity."""
    night_profile = np.zeros(24, dtype=np.float64)
    array = SolarArray(capacity_kwp=100.0)
    ac_gen = compute_ac_generation(night_profile, array)
    assert np.all(ac_gen == 0.0), "Nighttime generation must be strictly 0.0"

    day_profile = np.full(24, 0.5, dtype=np.float64)
    zero_array = SolarArray(capacity_kwp=0.0)
    ac_zero = compute_ac_generation(day_profile, zero_array)
    assert np.all(ac_zero == 0.0), "Zero capacity array must produce strictly 0.0"


def test_linearity_below_clipping(synthetic_dc_profile: np.ndarray) -> None:
    """Verify linear scaling with capacity when operating below inverter clipping limit."""
    # Scale profile down to ensure no clipping occurs
    low_profile = synthetic_dc_profile * 0.5  # max ~0.375 kW/kWp
    array_50 = SolarArray(capacity_kwp=50.0)
    array_100 = SolarArray(capacity_kwp=100.0)

    ac_50 = compute_ac_generation(low_profile, array_50)
    ac_100 = compute_ac_generation(low_profile, array_100)

    # 100 kWp array should produce exactly 2x the 50 kWp array
    assert np.allclose(ac_100, ac_50 * 2.0, rtol=1e-6)


def test_inverter_clipping_at_high_irradiance() -> None:
    """Verify inverter clipping occurs when gross AC exceeds continuous rating."""
    array = SolarArray(capacity_kwp=100.0)
    dc_ac_ratio = 1.20
    ac_rating = get_inverter_ac_rating(100.0, dc_ac_ratio=dc_ac_ratio)  # 83.333 kW AC

    # Feed exceptionally high DC yield that would exceed inverter capacity
    high_dc = np.array([1.2, 1.5, 2.0])  # kW/kWp
    ac_gen = compute_ac_generation(high_dc, array, dc_ac_ratio=dc_ac_ratio)

    # Output after AC wiring loss should equal ac_rating * DEFAULT_AC_WIRING_FACTOR
    expected_clipped = ac_rating * DEFAULT_AC_WIRING_FACTOR
    for val in ac_gen:
        assert pytest.approx(val, rel=1e-5) == expected_clipped


def test_ac_output_never_exceeds_rating() -> None:
    """Verify invariant: AC generation never exceeds continuous inverter AC rating."""
    for cap in (50.0, 100.0, 200.0):
        array = SolarArray(capacity_kwp=cap)
        ac_rating = get_inverter_ac_rating(cap)
        extreme_dc = np.linspace(0.0, 3.0, 100)
        ac_gen = compute_ac_generation(extreme_dc, array)

        assert np.all(ac_gen <= ac_rating + 1e-9), f"AC output exceeded inverter rating {ac_rating} kW"


def test_pr_budget_decomposition_reconciliation() -> None:
    """Verify PR budget factors multiply to the documented 0.77 baseline per [D-08] and [D-30]."""
    bos_non_thermal = get_non_thermal_bos_factor(
        soiling=DEFAULT_SOILING_FACTOR,
        dc_wiring=DEFAULT_DC_WIRING_FACTOR,
        ac_wiring=DEFAULT_AC_WIRING_FACTOR,
        mismatch=DEFAULT_MISMATCH_FACTOR,
        availability=DEFAULT_AVAILABILITY_FACTOR,
    )

    total_pr = bos_non_thermal * DEFAULT_INVERTER_EFFICIENCY * ASSUMED_MEAN_THERMAL_FACTOR
    assert pytest.approx(total_pr, abs=1e-4) == 0.7700, (
        f"PR budget product {total_pr:.4f} does not reconcile to baseline 0.77"
    )

    # Check each individual named factor is documented within standard physical ranges
    assert 0.90 <= DEFAULT_SOILING_FACTOR <= 0.99
    assert 0.95 <= DEFAULT_DC_WIRING_FACTOR <= 0.995
    assert 0.98 <= DEFAULT_AC_WIRING_FACTOR <= 0.999
    assert 0.95 <= DEFAULT_MISMATCH_FACTOR <= 0.995
    assert 0.98 <= DEFAULT_AVAILABILITY_FACTOR <= 0.999
    assert DEFAULT_INVERTER_EFFICIENCY == 0.980


def test_determinism(synthetic_dc_profile: np.ndarray) -> None:
    """Verify determinism across repeated executions."""
    array = SolarArray(capacity_kwp=100.0)
    run1 = compute_ac_generation(synthetic_dc_profile, array)
    run2 = compute_ac_generation(synthetic_dc_profile, array)
    assert np.array_equal(run1, run2), "Model execution is non-deterministic"


def test_input_error_handling() -> None:
    """Verify input validation catches negative values, NaNs, and bad parameters."""
    array = SolarArray(capacity_kwp=50.0)

    # Empty array returns empty array
    empty = compute_ac_generation(np.array([]), array)
    assert len(empty) == 0

    # Negative DC input
    with pytest.raises(ValueError, match="negative values"):
        compute_ac_generation(np.array([-0.1, 0.5]), array)

    # NaN in input
    with pytest.raises(ValueError, match="non-finite"):
        compute_ac_generation(np.array([0.5, np.nan]), array)

    # Invalid dc_ac_ratio
    with pytest.raises(ValueError, match="dc_ac_ratio must be strictly positive"):
        get_inverter_ac_rating(100.0, dc_ac_ratio=-1.0)
