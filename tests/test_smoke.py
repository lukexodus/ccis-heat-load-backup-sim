"""Smoke test suite verifying basic environment and package layout."""

import importlib
import numpy as np
import pytest
from scipy import stats

import ccis_sim


def test_package_version():
    """Verify package version is defined and matches specification."""
    assert hasattr(ccis_sim, "__version__")
    assert ccis_sim.__version__ == "0.1.0"


@pytest.mark.parametrize(
    "submodule_name",
    [
        "ccis_sim.core",
        "ccis_sim.demand",
        "ccis_sim.solar",
        "ccis_sim.battery",
        "ccis_sim.outage",
        "ccis_sim.integration",
        "ccis_sim.decision",
    ],
)
def test_submodules_importable(submodule_name: str):
    """Verify all architectural submodules are importable."""
    mod = importlib.import_module(submodule_name)
    assert mod is not None
    assert mod.__doc__ is not None
    assert len(mod.__doc__.strip()) > 0


def test_numpy_environment_sanity():
    """Verify NumPy operations function correctly."""
    arr = np.linspace(0.0, 1.0, 10)
    assert len(arr) == 10
    assert np.isclose(arr[0], 0.0)
    assert np.isclose(arr[-1], 1.0)


def test_scipy_environment_sanity():
    """Verify SciPy stats distributions function correctly."""
    # Test standard normal CDF: P(Z <= 0) == 0.5
    prob = stats.norm.cdf(0.0)
    assert np.isclose(prob, 0.5)

    # Test lognormal CDF for outage durations
    lognorm_prob = stats.lognorm.cdf(1.0, s=0.8, scale=np.exp(1.2))
    assert 0.0 < lognorm_prob < 1.0
