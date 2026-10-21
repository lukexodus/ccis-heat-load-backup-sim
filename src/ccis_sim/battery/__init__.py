"""Battery energy storage system (BESS) dispatch dynamics, state-of-charge, and limits."""

from ccis_sim.battery.reserve import apply_idle_losses, soc_floor_kwh

__all__ = ["soc_floor_kwh", "apply_idle_losses"]
