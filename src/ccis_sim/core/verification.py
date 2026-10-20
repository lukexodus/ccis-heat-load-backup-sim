"""Verification and validation harness for CCIS energy simulation.

Implements strict energy conservation and battery boundary checking across
simulation time series, per:
- docs/context/conceptual-model.md §4
- docs/decisions/decision-log.md [D-09], [D-10], [D-17], [D-21]
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Sequence

from ccis_sim.core.models import Battery, HourlyRecord, LoadTier


class ViolationType(str, Enum):
    """Classification of verification and boundary invariant violations."""

    HOURLY_ENERGY_BALANCE = "hourly_energy_balance"
    CUMULATIVE_ENERGY_BALANCE = "cumulative_energy_balance"
    NEGATIVE_SOC = "negative_soc"
    EXCEEDS_CAPACITY = "exceeds_capacity"
    MIN_SOC_VIOLATION = "min_soc_violation"
    CHARGE_RATE_EXCEEDED = "charge_rate_exceeded"
    DISCHARGE_RATE_EXCEEDED = "discharge_rate_exceeded"
    SIMULTANEOUS_CHARGE_DISCHARGE = "simultaneous_charge_discharge"


@dataclass(frozen=True)
class ConservationViolation:
    """Detailed record of an energy balance conservation failure."""

    hour: int
    timestamp: str
    residual_kwh: float
    tolerance_kwh: float
    energy_in_kwh: float
    energy_out_kwh: float
    violation_type: ViolationType = ViolationType.HOURLY_ENERGY_BALANCE
    details: str = ""

    def summary(self) -> str:
        """Return formatted single-line violation summary."""
        return (
            f"Hour {self.hour} ({self.timestamp}): residual {self.residual_kwh:.6e} kWh "
            f"> tolerance {self.tolerance_kwh:.6e} kWh "
            f"[In={self.energy_in_kwh:.4f} kWh, Out={self.energy_out_kwh:.4f} kWh] - {self.details}"
        )


@dataclass(frozen=True)
class BatteryBoundaryViolation:
    """Detailed record of a battery boundary or operating invariant violation."""

    hour: int
    timestamp: str
    violation_type: ViolationType
    actual_value: float
    limit_value: float
    details: str = ""

    def summary(self) -> str:
        """Return formatted single-line violation summary."""
        return (
            f"Hour {self.hour} ({self.timestamp}): {self.violation_type.value} "
            f"- actual={self.actual_value:.4f}, limit={self.limit_value:.4f} - {self.details}"
        )


@dataclass(frozen=True)
class VerificationReport:
    """Comprehensive outcome of verification harness across a simulation run."""

    total_records: int
    conservation_violations: list[ConservationViolation]
    battery_violations: list[BatteryBoundaryViolation]
    cumulative_net_drift_kwh: float
    cumulative_tolerance_kwh: float
    cumulative_conserved: bool
    max_residual_kwh: float

    @property
    def is_valid(self) -> bool:
        """Whether the time series satisfies all physical invariants and boundary rules."""
        return (
            self.cumulative_conserved
            and len(self.conservation_violations) == 0
            and len(self.battery_violations) == 0
        )

    @property
    def total_violations(self) -> int:
        """Total number of failed checks detected across all categories."""
        return (
            len(self.conservation_violations)
            + len(self.battery_violations)
            + (0 if self.cumulative_conserved else 1)
        )

    def summary(self) -> str:
        """Format a human-readable verification summary report."""
        status = "PASSED" if self.is_valid else "FAILED"
        lines = [
            f"=== Simulation Verification Report: {status} ===",
            f"Evaluated Records: {self.total_records}",
            f"Max Hourly Residual: {self.max_residual_kwh:.6e} kWh",
            f"Cumulative Net Drift: {self.cumulative_net_drift_kwh:.6e} kWh "
            f"(tolerance: {self.cumulative_tolerance_kwh:.6e} kWh, "
            f"conserved: {self.cumulative_conserved})",
            f"Hourly Conservation Violations: {len(self.conservation_violations)}",
            f"Battery Boundary Violations: {len(self.battery_violations)}",
        ]

        if self.conservation_violations:
            lines.append("\n--- Top Conservation Violations ---")
            for v in self.conservation_violations[:10]:
                lines.append(f"  * {v.summary()}")
            if len(self.conservation_violations) > 10:
                lines.append(f"  ... and {len(self.conservation_violations) - 10} more.")

        if self.battery_violations:
            lines.append("\n--- Top Battery Boundary Violations ---")
            for v in self.battery_violations[:10]:
                lines.append(f"  * {v.summary()}")
            if len(self.battery_violations) > 10:
                lines.append(f"  ... and {len(self.battery_violations) - 10} more.")

        return "\n".join(lines)


def compute_cumulative_tolerance(n_records: int, tolerance_hour: float = 1e-5) -> float:
    """Compute statistically defensible cumulative conservation tolerance per [D-21].

    Random numerical rounding across independent hourly calculations scales as
    O(sqrt(N) * epsilon). To permit benign zero-mean IEEE 754 floating point jitter
    while reliably catching systematic numerical bias, the cumulative tolerance is:
        tolerance_cum = max(tolerance_hour, sqrt(N) * tolerance_hour)

    For N = 8,760 hours and epsilon = 1e-5 kWh, tolerance_cum ~= 9.359e-4 kWh (~0.001 kWh).
    A systematic bias of 0.9e-5 kWh/hr produces 0.0788 kWh >> 9.359e-4 kWh, tripping cleanly.
    """
    if n_records <= 0:
        return tolerance_hour
    return max(tolerance_hour, math.sqrt(n_records) * tolerance_hour)


def check_energy_conservation(
    records: Sequence[HourlyRecord],
    tolerance: float = 1e-5,
    cumulative_tolerance: float | None = None,
) -> list[ConservationViolation]:
    """Verify strict physical energy balance conservation across a sequence of records.

    Reuses HourlyRecord.energy_balance_residual_kwh and HourlyRecord.is_energy_conserved()
    to guarantee identical residual calculation logic as canonical models.

    Args:
        records: Sequence of HourlyRecord instances.
        tolerance: Maximum allowable residual per hour (default 1e-5 kWh per [D-05]).
        cumulative_tolerance: Maximum allowable cumulative net drift across all records.
            If None, defaults to compute_cumulative_tolerance(len(records), tolerance) per [D-21].

    Returns:
        List of ConservationViolation instances for any hourly or cumulative failures.
    """
    violations: list[ConservationViolation] = []
    if not records:
        return violations

    total_in = 0.0
    total_out = 0.0

    for r in records:
        e_in = r.solar_generation_kwh + r.grid_import_kwh + r.battery_discharge_kwh
        e_out = r.demand_served_kwh + r.battery_charge_kwh + r.solar_curtailed_kwh
        total_in += e_in
        total_out += e_out

        residual = r.energy_balance_residual_kwh
        if not r.is_energy_conserved(tolerance=tolerance):
            violations.append(
                ConservationViolation(
                    hour=r.hour,
                    timestamp=r.timestamp,
                    residual_kwh=residual,
                    tolerance_kwh=tolerance,
                    energy_in_kwh=e_in,
                    energy_out_kwh=e_out,
                    violation_type=ViolationType.HOURLY_ENERGY_BALANCE,
                    details=(
                        f"Hourly energy balance residual {residual:.6e} kWh exceeded "
                        f"tolerance {tolerance:.6e} kWh"
                    ),
                )
            )

    net_drift = total_in - total_out
    cum_tol = (
        cumulative_tolerance
        if cumulative_tolerance is not None
        else compute_cumulative_tolerance(len(records), tolerance)
    )

    if abs(net_drift) > cum_tol:
        violations.append(
            ConservationViolation(
                hour=0,
                timestamp="CUMULATIVE_RUN",
                residual_kwh=abs(net_drift),
                tolerance_kwh=cum_tol,
                energy_in_kwh=total_in,
                energy_out_kwh=total_out,
                violation_type=ViolationType.CUMULATIVE_ENERGY_BALANCE,
                details=(
                    f"Cumulative energy imbalance drift of {abs(net_drift):.6e} kWh "
                    f"exceeded cumulative tolerance {cum_tol:.6e} kWh across {len(records)} hours."
                ),
            )
        )

    return violations


def validate_battery_boundaries(
    records: Sequence[HourlyRecord],
    battery: Battery,
    allow_emergency_drawdown: bool = False,
    delta_t_hours: float = 1.0,
) -> list[BatteryBoundaryViolation]:
    """Validate physical and operational battery boundaries across a simulation time series.

    Per [D-09] and [D-21], verifies:
    1. 0 <= battery_soc_kwh <= Battery.capacity_kwh (hard physical limits)
    2. battery_soc_kwh >= Battery.min_soc_kwh (cell protection floor, unless
       allow_emergency_drawdown=True during an active grid blackout with Tier 1/2 shedding)
    3. battery_charge_kwh <= max_charge_power_kw * delta_t_hours (0.5C limit)
    4. battery_discharge_kwh <= max_discharge_power_kw * delta_t_hours (1.0C limit)
    5. Mutual exclusivity: battery_charge_kwh and battery_discharge_kwh cannot both be > 1e-6 kWh

    Args:
        records: Sequence of HourlyRecord instances.
        battery: Battery specification defining capacity and operational limits.
        allow_emergency_drawdown: If True, allows SoC to dip below min_soc_kwh (down to 0)
            strictly during active blackout hours (grid_available=False, active_load_tier in (1, 2)).
        delta_t_hours: Timestep duration in hours (default 1.0).

    Returns:
        List of BatteryBoundaryViolation instances for any boundary violations.
    """
    violations: list[BatteryBoundaryViolation] = []
    if not records:
        return violations

    fp_tol = 1e-9  # Floating-point numerical tolerance
    max_charge_kwh = battery.max_charge_power_kw * delta_t_hours
    max_discharge_kwh = battery.max_discharge_power_kw * delta_t_hours

    for r in records:
        # 1. Negative SoC check
        if r.battery_soc_kwh < -fp_tol:
            violations.append(
                BatteryBoundaryViolation(
                    hour=r.hour,
                    timestamp=r.timestamp,
                    violation_type=ViolationType.NEGATIVE_SOC,
                    actual_value=r.battery_soc_kwh,
                    limit_value=0.0,
                    details=f"Battery SoC {r.battery_soc_kwh:.6f} kWh is physically negative.",
                )
            )

        # 2. Exceeds nameplate capacity check
        if r.battery_soc_kwh > battery.capacity_kwh + fp_tol:
            violations.append(
                BatteryBoundaryViolation(
                    hour=r.hour,
                    timestamp=r.timestamp,
                    violation_type=ViolationType.EXCEEDS_CAPACITY,
                    actual_value=r.battery_soc_kwh,
                    limit_value=battery.capacity_kwh,
                    details=(
                        f"Battery SoC {r.battery_soc_kwh:.4f} kWh exceeds rated "
                        f"capacity {battery.capacity_kwh:.4f} kWh."
                    ),
                )
            )

        # 3. Minimum SoC floor check
        is_emergency = (not r.grid_available) and (
            r.active_load_tier in (LoadTier.TIER_1_CRITICAL, LoadTier.TIER_2_ESSENTIAL, 1, 2)
        )
        if r.battery_soc_kwh < battery.min_soc_kwh - fp_tol:
            if not (allow_emergency_drawdown and is_emergency):
                violations.append(
                    BatteryBoundaryViolation(
                        hour=r.hour,
                        timestamp=r.timestamp,
                        violation_type=ViolationType.MIN_SOC_VIOLATION,
                        actual_value=r.battery_soc_kwh,
                        limit_value=battery.min_soc_kwh,
                        details=(
                            f"Battery SoC {r.battery_soc_kwh:.4f} kWh fell below minimum protection floor "
                            f"{battery.min_soc_kwh:.4f} kWh ({battery.min_soc_pct*100:.0f}%) "
                            f"outside permitted emergency conditions."
                        ),
                    )
                )

        # 4. Charge rate limit (C-rate)
        if r.battery_charge_kwh > max_charge_kwh + fp_tol:
            violations.append(
                BatteryBoundaryViolation(
                    hour=r.hour,
                    timestamp=r.timestamp,
                    violation_type=ViolationType.CHARGE_RATE_EXCEEDED,
                    actual_value=r.battery_charge_kwh,
                    limit_value=max_charge_kwh,
                    details=(
                        f"Battery charge {r.battery_charge_kwh:.4f} kWh exceeded "
                        f"max power limit {max_charge_kwh:.4f} kWh (C-rate {battery.max_charge_c_rate}C)."
                    ),
                )
            )

        # 5. Discharge rate limit (C-rate)
        if r.battery_discharge_kwh > max_discharge_kwh + fp_tol:
            violations.append(
                BatteryBoundaryViolation(
                    hour=r.hour,
                    timestamp=r.timestamp,
                    violation_type=ViolationType.DISCHARGE_RATE_EXCEEDED,
                    actual_value=r.battery_discharge_kwh,
                    limit_value=max_discharge_kwh,
                    details=(
                        f"Battery discharge {r.battery_discharge_kwh:.4f} kWh exceeded "
                        f"max power limit {max_discharge_kwh:.4f} kWh (C-rate {battery.max_discharge_c_rate}C)."
                    ),
                )
            )

        # 6. Simultaneous charge and discharge prevention
        if r.battery_charge_kwh > 1e-6 and r.battery_discharge_kwh > 1e-6:
            violations.append(
                BatteryBoundaryViolation(
                    hour=r.hour,
                    timestamp=r.timestamp,
                    violation_type=ViolationType.SIMULTANEOUS_CHARGE_DISCHARGE,
                    actual_value=min(r.battery_charge_kwh, r.battery_discharge_kwh),
                    limit_value=0.0,
                    details=(
                        f"Simultaneous charge ({r.battery_charge_kwh:.4f} kWh) and discharge "
                        f"({r.battery_discharge_kwh:.4f} kWh) in same hour."
                    ),
                )
            )

    return violations


def run_verification_harness(
    records: Sequence[HourlyRecord],
    battery: Battery | None = None,
    tolerance: float = 1e-5,
    cumulative_tolerance: float | None = None,
    allow_emergency_drawdown: bool = False,
    delta_t_hours: float = 1.0,
) -> VerificationReport:
    """Execute complete verification harness across a simulation time series.

    Validates both hourly energy conservation invariants and (if battery is provided)
    battery physical boundary conditions.

    Args:
        records: Sequence of HourlyRecord instances.
        battery: Optional Battery instance. If provided, battery boundaries are checked.
        tolerance: Per-hour energy balance tolerance (default 1e-5 kWh).
        cumulative_tolerance: Optional cumulative net drift tolerance (default per [D-21]).
        allow_emergency_drawdown: Whether to permit SoC below min_soc during emergency blackouts.
        delta_t_hours: Hourly timestep duration.

    Returns:
        VerificationReport containing full diagnostics.
    """
    conservation_violations = check_energy_conservation(
        records=records,
        tolerance=tolerance,
        cumulative_tolerance=cumulative_tolerance,
    )

    battery_violations: list[BatteryBoundaryViolation] = []
    if battery is not None:
        battery_violations = validate_battery_boundaries(
            records=records,
            battery=battery,
            allow_emergency_drawdown=allow_emergency_drawdown,
            delta_t_hours=delta_t_hours,
        )

    # Compute aggregate stats
    total_in = sum(
        r.solar_generation_kwh + r.grid_import_kwh + r.battery_discharge_kwh for r in records
    )
    total_out = sum(
        r.demand_served_kwh + r.battery_charge_kwh + r.solar_curtailed_kwh for r in records
    )
    net_drift = total_in - total_out
    cum_tol = (
        cumulative_tolerance
        if cumulative_tolerance is not None
        else compute_cumulative_tolerance(len(records), tolerance)
    )
    cum_conserved = abs(net_drift) <= cum_tol
    max_residual = max((r.energy_balance_residual_kwh for r in records), default=0.0)

    # Filter out cumulative violation from conservation_violations list if we want to separate
    # hourly vs cumulative in the report object:
    hourly_conservation_violations = [
        v for v in conservation_violations if v.violation_type != ViolationType.CUMULATIVE_ENERGY_BALANCE
    ]

    return VerificationReport(
        total_records=len(records),
        conservation_violations=hourly_conservation_violations,
        battery_violations=battery_violations,
        cumulative_net_drift_kwh=net_drift,
        cumulative_tolerance_kwh=cum_tol,
        cumulative_conserved=cum_conserved,
        max_residual_kwh=max_residual,
    )


def assert_simulation_valid(
    records: Sequence[HourlyRecord],
    battery: Battery | None = None,
    tolerance: float = 1e-5,
    cumulative_tolerance: float | None = None,
    allow_emergency_drawdown: bool = False,
    delta_t_hours: float = 1.0,
) -> None:
    """Assertion helper for test suites. Raises AssertionError with detailed report on failure."""
    report = run_verification_harness(
        records=records,
        battery=battery,
        tolerance=tolerance,
        cumulative_tolerance=cumulative_tolerance,
        allow_emergency_drawdown=allow_emergency_drawdown,
        delta_t_hours=delta_t_hours,
    )
    if not report.is_valid:
        raise AssertionError(f"Simulation verification failed:\n{report.summary()}")


def create_golden_scenario(battery: Battery | None = None) -> list[HourlyRecord]:
    """Construct a canonical 48-hour synthetic reference scenario with exact energy conservation.

    The scenario exercises all primary physical microgrid states:
    - Day 1 (Hours 1–24): Normal grid operation.
      - Hours 1–4: Nighttime battery discharge down to min_soc floor (10.0 kWh).
      - Hours 5–6: Nighttime grid import sustaining baseload while battery sits at floor.
      - Hours 7–9: Morning solar generation ramp, serving demand and charging battery.
      - Hours 10–14: Peak midday solar surplus filling battery to 100% capacity, then curtailing.
      - Hour 15: Exact zero net-load balance (solar generation strictly equals demand).
      - Hours 16–20: Afternoon/evening solar decline supplemented by battery discharge.
      - Hours 21–24: Evening transition back to grid import after battery reaches min_soc.
    - Day 2 (Hours 25–48): Outage resilience and recovery.
      - Hours 25–29: Morning pre-outage charging to full capacity (100 kWh).
      - Hours 30–37: 8-hour grid blackout (grid_available=False), shedding Tier 3 comfort
        cooling to Tier 2 essential load (5.0 kWh), sustained by islanded battery and solar.
      - Hours 38–48: Grid restoration, battery post-outage evening discharge and recovery.

    All 48 hours have identically zero energy balance residuals (residual = 0.000000)
    and strictly conform to Battery boundaries.
    """
    bat = battery or Battery(capacity_kwh=100.0)
    records: list[HourlyRecord] = []

    # State tracking
    current_soc = 50.0  # Initial SoC at start of Day 1 (kWh)

    # 48-hour schedule definitions: (hour, solar_gen, demand_gross, grid_avail, tier, target_bat_dis, target_bat_chg)
    # We will compute the exact flows to guarantee strict mathematical balance.
    # Day 1:
    day_1_plan = [
        # Night: battery discharges 10 kWh/hr down to min_soc (10 kWh)
        (1, 0.0, 10.0, True, 3, 10.0, 0.0),
        (2, 0.0, 10.0, True, 3, 10.0, 0.0),
        (3, 0.0, 10.0, True, 3, 10.0, 0.0),
        (4, 0.0, 10.0, True, 3, 10.0, 0.0),  # hits 10.0 kWh min_soc
        # Night: battery at floor, grid imports 10 kWh
        (5, 0.0, 10.0, True, 3, 0.0, 0.0),
        (6, 0.0, 10.0, True, 3, 0.0, 0.0),
        # Morning ramp: solar serves demand and charges battery
        (7, 20.0, 10.0, True, 3, 0.0, 10.0),  # SoC -> 20.0
        (8, 40.0, 15.0, True, 3, 0.0, 25.0),  # SoC -> 45.0
        (9, 65.0, 20.0, True, 3, 0.0, 45.0),  # SoC -> 90.0 (45 <= 50kW max charge)
        # Midday: battery reaches full (100 kWh), remainder curtailed
        (10, 80.0, 25.0, True, 3, 0.0, 10.0), # SoC -> 100.0, curtailed = 45.0
        (11, 85.0, 30.0, True, 3, 0.0, 0.0),  # SoC = 100.0, curtailed = 55.0
        (12, 90.0, 30.0, True, 3, 0.0, 0.0),  # SoC = 100.0, curtailed = 60.0
        (13, 70.0, 30.0, True, 3, 0.0, 0.0),  # SoC = 100.0, curtailed = 40.0
        (14, 45.0, 25.0, True, 3, 0.0, 0.0),  # SoC = 100.0, curtailed = 20.0
        # Zero net-load hour
        (15, 25.0, 25.0, True, 3, 0.0, 0.0),  # Net load = 0
        # Afternoon decline: solar + battery discharge
        (16, 10.0, 25.0, True, 3, 15.0, 0.0), # SoC -> 85.0
        (17, 5.0, 20.0, True, 3, 15.0, 0.0),  # SoC -> 70.0
        (18, 0.0, 20.0, True, 3, 20.0, 0.0),  # SoC -> 50.0
        # Evening: battery discharge down to min_soc
        (19, 0.0, 15.0, True, 3, 15.0, 0.0),  # SoC -> 35.0
        (20, 0.0, 15.0, True, 3, 15.0, 0.0),  # SoC -> 20.0
        (21, 0.0, 15.0, True, 3, 10.0, 0.0),  # SoC -> 10.0 (hits floor), grid import = 5
        (22, 0.0, 10.0, True, 3, 0.0, 0.0),   # grid import = 10
        (23, 0.0, 10.0, True, 3, 0.0, 0.0),   # grid import = 10
        (24, 0.0, 10.0, True, 3, 0.0, 0.0),   # grid import = 10
    ]

    # Day 2:
    day_2_plan = [
        # Early morning grid import
        (25, 0.0, 10.0, True, 3, 0.0, 0.0),   # SoC = 10.0
        (26, 0.0, 10.0, True, 3, 0.0, 0.0),   # SoC = 10.0
        # Solar ramp pre-charging battery
        (27, 25.0, 10.0, True, 3, 0.0, 15.0), # SoC -> 25.0
        (28, 50.0, 15.0, True, 3, 0.0, 35.0), # SoC -> 60.0
        (29, 60.0, 20.0, True, 3, 0.0, 40.0), # SoC -> 100.0 (full!)
        # Hours 30-37: 8-hour blackout! Shedding to Tier 2 (served = 5.0 kW)
        (30, 10.0, 25.0, False, 2, 0.0, 0.0), # Solar 10 serves 5kW, curtails 5kW, SoC=100
        (31, 0.0, 25.0, False, 2, 5.0, 0.0),  # Islanded battery discharge -> SoC 95.0
        (32, 0.0, 25.0, False, 2, 5.0, 0.0),  # SoC -> 90.0
        (33, 0.0, 25.0, False, 2, 5.0, 0.0),  # SoC -> 85.0
        (34, 0.0, 25.0, False, 2, 5.0, 0.0),  # SoC -> 80.0
        (35, 0.0, 25.0, False, 2, 5.0, 0.0),  # SoC -> 75.0
        (36, 0.0, 25.0, False, 2, 5.0, 0.0),  # SoC -> 70.0
        (37, 0.0, 25.0, False, 2, 5.0, 0.0),  # SoC -> 65.0
        # Hours 38-48: Grid restored, Tier 3 active
        (38, 0.0, 15.0, True, 3, 15.0, 0.0),  # SoC -> 50.0
        (39, 0.0, 15.0, True, 3, 15.0, 0.0),  # SoC -> 35.0
        (40, 0.0, 15.0, True, 3, 15.0, 0.0),  # SoC -> 20.0
        (41, 0.0, 15.0, True, 3, 10.0, 0.0),  # SoC -> 10.0 (hits floor), grid import = 5
        (42, 0.0, 10.0, True, 3, 0.0, 0.0),   # grid import = 10
        (43, 0.0, 10.0, True, 3, 0.0, 0.0),   # grid import = 10
        (44, 0.0, 10.0, True, 3, 0.0, 0.0),   # grid import = 10
        (45, 0.0, 10.0, True, 3, 0.0, 0.0),   # grid import = 10
        (46, 0.0, 10.0, True, 3, 0.0, 0.0),   # grid import = 10
        (47, 0.0, 10.0, True, 3, 0.0, 0.0),   # grid import = 10
        (48, 0.0, 10.0, True, 3, 0.0, 0.0),   # grid import = 10
    ]

    for (h, solar_gen, demand_gross, grid_avail, tier, bat_dis, bat_chg) in (day_1_plan + day_2_plan):
        # Determine demand served based on tier and grid availability
        if grid_avail:
            demand_served = demand_gross
            unserved = 0.0
        else:
            # During blackout, Tier 2 served = 5.0 kWh; unserved = gross - served
            demand_served = 5.0
            unserved = demand_gross - demand_served

        # Compute direct solar to demand
        solar_to_demand = min(solar_gen, demand_served)
        solar_surplus = solar_gen - solar_to_demand

        solar_to_bat = bat_chg
        solar_curtailed = solar_surplus - solar_to_bat

        # Deficit after solar and battery discharge
        remaining_demand = demand_served - solar_to_demand - bat_dis
        if remaining_demand > 1e-9:
            grid_import = remaining_demand
        else:
            grid_import = 0.0

        current_soc = current_soc + bat_chg - bat_dis

        # Format ISO timestamp (starting 2026-04-15)
        day_offset = (h - 1) // 24
        hour_in_day = (h - 1) % 24
        ts = f"2026-04-{15 + day_offset:02d}T{hour_in_day:02d}:00:00+08:00"

        rec = HourlyRecord(
            hour=h,
            timestamp=ts,
            temp_ambient_c=25.0 + (5.0 if 8 <= hour_in_day <= 16 else 0.0),
            humidity_rel_pct=75.0,
            ghi_w_m2=solar_gen * 10.0,
            demand_gross_kwh=demand_gross,
            demand_served_kwh=demand_served,
            solar_generation_kwh=solar_gen,
            solar_to_demand_kwh=solar_to_demand,
            solar_to_battery_kwh=solar_to_bat,
            solar_curtailed_kwh=solar_curtailed,
            battery_soc_kwh=round(current_soc, 6),
            battery_charge_kwh=bat_chg,
            battery_discharge_kwh=bat_dis,
            grid_import_kwh=grid_import,
            unserved_load_kwh=unserved,
            grid_available=grid_avail,
            active_load_tier=tier,
        )
        records.append(rec)

    return records
