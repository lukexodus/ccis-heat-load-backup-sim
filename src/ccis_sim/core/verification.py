"""Verification and validation harness for CCIS energy simulation.

Implements strict energy conservation and battery boundary checking across
simulation time series, per:
- docs/context/conceptual-model.md §4
- docs/decisions/decision-log.md [D-09], [D-10], [D-17], [D-21]
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
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
    SOC_CONTINUITY = "soc_continuity"
    SOC_CUMULATIVE_DRIFT = "soc_cumulative_drift"
    NON_FINITE_VALUE = "non_finite_value"
    SOLAR_FLOW_BALANCE = "solar_flow_balance"
    DEMAND_FLOW_BALANCE = "demand_flow_balance"


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
    subflow_violations: list[ConservationViolation] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """Whether the time series satisfies all physical invariants and boundary rules."""
        return (
            self.cumulative_conserved
            and len(self.conservation_violations) == 0
            and len(self.battery_violations) == 0
            and len(self.subflow_violations) == 0
        )

    @property
    def total_violations(self) -> int:
        """Total number of failed checks detected across all categories."""
        return (
            len(self.conservation_violations)
            + len(self.battery_violations)
            + len(self.subflow_violations)
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
            f"Sub-Flow Balance Violations: {len(self.subflow_violations)}",
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

        if self.subflow_violations:
            lines.append("\n--- Top Sub-Flow Violations ---")
            for v in self.subflow_violations[:10]:
                lines.append(f"  * {v.summary()}")
            if len(self.subflow_violations) > 10:
                lines.append(f"  ... and {len(self.subflow_violations) - 10} more.")

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

    NUMERIC_FIELDS = (
        "temp_ambient_c",
        "humidity_rel_pct",
        "ghi_w_m2",
        "demand_gross_kwh",
        "demand_served_kwh",
        "solar_generation_kwh",
        "solar_to_demand_kwh",
        "solar_to_battery_kwh",
        "solar_curtailed_kwh",
        "battery_soc_kwh",
        "battery_charge_kwh",
        "battery_discharge_kwh",
        "grid_import_kwh",
        "unserved_load_kwh",
    )

    total_in = 0.0
    total_out = 0.0

    for r in records:
        # 1. Non-finite value guard
        has_non_finite = False
        for field_name in NUMERIC_FIELDS:
            val = getattr(r, field_name, 0.0)
            if math.isnan(val) or math.isinf(val):
                has_non_finite = True
                violations.append(
                    ConservationViolation(
                        hour=r.hour,
                        timestamp=r.timestamp,
                        residual_kwh=float("nan"),
                        tolerance_kwh=tolerance,
                        energy_in_kwh=float("nan"),
                        energy_out_kwh=float("nan"),
                        violation_type=ViolationType.NON_FINITE_VALUE,
                        details=f"Field '{field_name}' contains non-finite value: {val}",
                    )
                )

        if has_non_finite:
            continue

        e_in = r.solar_generation_kwh + r.grid_import_kwh + r.battery_discharge_kwh
        e_out = r.demand_served_kwh + r.battery_charge_kwh + r.solar_curtailed_kwh
        total_in += e_in
        total_out += e_out

        # 2. Hourly energy balance invariant
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

    # 3. Cumulative drift using signed residual invariant property
    net_drift = sum(r.signed_residual_kwh for r in records)
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


def check_subflow_balance(
    records: Sequence[HourlyRecord],
    tolerance: float = 1e-5,
) -> list[ConservationViolation]:
    """Verify sub-component physical flow conservation across a sequence of records.

    Per [D-25], verifies:
    1. Solar generation flow decomposition:
       solar_generation_kwh = solar_to_demand_kwh + solar_to_battery_kwh + solar_curtailed_kwh
    2. Gross demand flow decomposition:
       demand_gross_kwh = demand_served_kwh + unserved_load_kwh

    Args:
        records: Sequence of HourlyRecord instances.
        tolerance: Maximum allowable discrepancy per hour (default 1e-5 kWh).

    Returns:
        List of ConservationViolation instances for any sub-flow decomposition failures.
    """
    violations: list[ConservationViolation] = []
    if not records:
        return violations

    for r in records:
        # Solar sub-flow decomposition
        expected_solar = r.solar_to_demand_kwh + r.solar_to_battery_kwh + r.solar_curtailed_kwh
        solar_diff = abs(r.solar_generation_kwh - expected_solar)
        if solar_diff > tolerance:
            violations.append(
                ConservationViolation(
                    hour=r.hour,
                    timestamp=r.timestamp,
                    residual_kwh=solar_diff,
                    tolerance_kwh=tolerance,
                    energy_in_kwh=r.solar_generation_kwh,
                    energy_out_kwh=expected_solar,
                    violation_type=ViolationType.SOLAR_FLOW_BALANCE,
                    details=(
                        f"Solar generation {r.solar_generation_kwh:.6e} kWh does not equal sum of "
                        f"solar_to_demand ({r.solar_to_demand_kwh:.6e}) + solar_to_battery ({r.solar_to_battery_kwh:.6e}) + "
                        f"solar_curtailed ({r.solar_curtailed_kwh:.6e}) [delta={solar_diff:.6e} kWh > tol {tolerance:.6e} kWh]."
                    ),
                )
            )

        # Demand sub-flow decomposition
        expected_demand = r.demand_served_kwh + r.unserved_load_kwh
        demand_diff = abs(r.demand_gross_kwh - expected_demand)
        if demand_diff > tolerance:
            violations.append(
                ConservationViolation(
                    hour=r.hour,
                    timestamp=r.timestamp,
                    residual_kwh=demand_diff,
                    tolerance_kwh=tolerance,
                    energy_in_kwh=r.demand_gross_kwh,
                    energy_out_kwh=expected_demand,
                    violation_type=ViolationType.DEMAND_FLOW_BALANCE,
                    details=(
                        f"Gross demand {r.demand_gross_kwh:.6e} kWh does not equal sum of "
                        f"demand_served ({r.demand_served_kwh:.6e}) + unserved_load ({r.unserved_load_kwh:.6e}) "
                        f"[delta={demand_diff:.6e} kWh > tol {tolerance:.6e} kWh]."
                    ),
                )
            )

    return violations


def validate_battery_boundaries(
    records: Sequence[HourlyRecord],
    battery: Battery,
    allow_emergency_drawdown: bool = False,
    delta_t_hours: float = 1.0,
    initial_soc_kwh: float | None = None,
    tolerance: float = 1e-5,
) -> list[BatteryBoundaryViolation]:
    """Validate physical and operational battery boundaries across a simulation time series.

    Per [D-09], [D-21], and [D-25], verifies:
    1. Finite numerical values (no NaN or +-inf in SoC or charge/discharge flows).
    2. 0 <= battery_soc_kwh <= Battery.capacity_kwh (hard physical limits).
    3. battery_soc_kwh >= Battery.min_soc_kwh (cell protection floor, unless
       allow_emergency_drawdown=True during an active grid blackout with Tier 1/2 shedding).
    4. battery_charge_kwh <= max_charge_power_kw * delta_t_hours (0.5C limit).
    5. battery_discharge_kwh <= max_discharge_power_kw * delta_t_hours (1.0C limit).
    6. Mutual exclusivity: battery_charge_kwh and battery_discharge_kwh cannot both be > 1e-6 kWh.
    7. Hour-to-hour SoC continuity:
       SoC_t = SoC_{t-1} + eta_chg * charge_t - (discharge_t / eta_dis)
       where round-trip efficiency (92% per [D-09]) is symmetrically split:
       eta_chg = eta_dis = sqrt(Battery.round_trip_efficiency).
       Charge and discharge are AC-side flows (matching hourly energy balance), so internal
       conversion losses appear strictly in the stored chemical SoC.
       The check is skipped if Battery.capacity_kwh == 0.0 (e.g. grid-only baseline).
       For the first record (hour 1), continuity is evaluated against initial_soc_kwh if provided;
       otherwise skipped for the first record.

    Args:
        records: Sequence of HourlyRecord instances.
        battery: Battery specification defining capacity and operational limits.
        allow_emergency_drawdown: If True, allows SoC to dip below min_soc_kwh (down to 0)
            strictly during active blackout hours (grid_available=False, active_load_tier in (1, 2)).
        delta_t_hours: Timestep duration in hours (default 1.0).
        initial_soc_kwh: Optional initial SoC before record 0 for verifying first timestep.
        tolerance: Numerical tolerance for SoC continuity (default 1e-5 kWh).

    Returns:
        List of BatteryBoundaryViolation instances for any boundary violations.
    """
    violations: list[BatteryBoundaryViolation] = []
    if not records:
        return violations

    fp_tol = 1e-9  # Floating-point numerical tolerance
    max_charge_kwh = battery.max_charge_power_kw * delta_t_hours
    max_discharge_kwh = battery.max_discharge_power_kw * delta_t_hours

    eta_chg = math.sqrt(battery.round_trip_efficiency)
    eta_dis = math.sqrt(battery.round_trip_efficiency)

    # Maximum allowable idle loss per hour per [D-26] (self-discharge + tare)
    HOURS_PER_MONTH = 730.0  # 8,760 h / 12 months per [D-26]
    self_discharge_loss_per_hour = (
        battery.capacity_kwh * (battery.self_discharge_pct_per_month / 100.0) / HOURS_PER_MONTH
    )
    max_idle_loss_per_hour = self_discharge_loss_per_hour + battery.tare_loss_kw
    max_idle_loss_step = max_idle_loss_per_hour * delta_t_hours

    cum_soc_diff = 0.0
    total_allowed_idle_loss = 0.0
    evaluated_continuity_steps = 0

    for idx, r in enumerate(records):
        # 1. Non-finite values guard
        has_non_finite = False
        for f_name, f_val in (
            ("battery_soc_kwh", r.battery_soc_kwh),
            ("battery_charge_kwh", r.battery_charge_kwh),
            ("battery_discharge_kwh", r.battery_discharge_kwh),
        ):
            if math.isnan(f_val) or math.isinf(f_val):
                has_non_finite = True
                violations.append(
                    BatteryBoundaryViolation(
                        hour=r.hour,
                        timestamp=r.timestamp,
                        violation_type=ViolationType.NON_FINITE_VALUE,
                        actual_value=float("nan"),
                        limit_value=0.0,
                        details=f"Field '{f_name}' has non-finite value: {f_val}",
                    )
                )

        if has_non_finite:
            continue

        # 2. Negative SoC check
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

        # 3. Exceeds nameplate capacity check
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

        # 4. Minimum SoC floor check
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

        # 5. Charge rate limit (C-rate)
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

        # 6. Discharge rate limit (C-rate)
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

        # 7. Simultaneous charge and discharge prevention
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

        # 8. Hour-to-hour SoC continuity check (one-sided with idle allowance per [D-26])
        if battery.capacity_kwh > 0.0:
            if idx == 0:
                if initial_soc_kwh is not None:
                    expected_soc = (
                        initial_soc_kwh
                        + eta_chg * r.battery_charge_kwh
                        - (r.battery_discharge_kwh / eta_dis)
                    )
                    diff = expected_soc - r.battery_soc_kwh
                    evaluated_continuity_steps += 1
                    cum_soc_diff += diff
                    total_allowed_idle_loss += max_idle_loss_step

                    if diff < -tolerance:
                        violations.append(
                            BatteryBoundaryViolation(
                                hour=r.hour,
                                timestamp=r.timestamp,
                                violation_type=ViolationType.SOC_CONTINUITY,
                                actual_value=r.battery_soc_kwh,
                                limit_value=expected_soc,
                                details=(
                                    f"Hour {r.hour} SoC ({r.battery_soc_kwh:.6f} kWh) is higher than ideal recursion "
                                    f"from initial SoC ({initial_soc_kwh:.6f} kWh) [expected {expected_soc:.6f} kWh, "
                                    f"delta={-diff:.6e} kWh > tol {tolerance:.6e} kWh]."
                                ),
                            )
                        )
                    elif diff > max_idle_loss_step + tolerance:
                        violations.append(
                            BatteryBoundaryViolation(
                                hour=r.hour,
                                timestamp=r.timestamp,
                                violation_type=ViolationType.SOC_CONTINUITY,
                                actual_value=r.battery_soc_kwh,
                                limit_value=expected_soc,
                                details=(
                                    f"Hour {r.hour} SoC loss ({diff:.6f} kWh) exceeds maximum allowable idle loss "
                                    f"({max_idle_loss_step:.6f} kWh) from initial SoC [excess={diff - max_idle_loss_step:.6e} kWh "
                                    f"> tol {tolerance:.6e} kWh]."
                                ),
                            )
                        )
            else:
                prev = records[idx - 1]
                expected_soc = (
                    prev.battery_soc_kwh
                    + eta_chg * r.battery_charge_kwh
                    - (r.battery_discharge_kwh / eta_dis)
                )
                diff = expected_soc - r.battery_soc_kwh
                evaluated_continuity_steps += 1
                cum_soc_diff += diff
                total_allowed_idle_loss += max_idle_loss_step

                if diff < -tolerance:
                    violations.append(
                        BatteryBoundaryViolation(
                            hour=r.hour,
                            timestamp=r.timestamp,
                            violation_type=ViolationType.SOC_CONTINUITY,
                            actual_value=r.battery_soc_kwh,
                            limit_value=expected_soc,
                            details=(
                                f"Hour {r.hour} SoC ({r.battery_soc_kwh:.6f} kWh) is higher than ideal recursion "
                                f"from Hour {prev.hour} ({prev.battery_soc_kwh:.6f} kWh) [expected {expected_soc:.6f} kWh, "
                                f"delta={-diff:.6e} kWh > tol {tolerance:.6e} kWh]."
                            ),
                        )
                    )
                elif diff > max_idle_loss_step + tolerance:
                    violations.append(
                        BatteryBoundaryViolation(
                            hour=r.hour,
                            timestamp=r.timestamp,
                            violation_type=ViolationType.SOC_CONTINUITY,
                            actual_value=r.battery_soc_kwh,
                            limit_value=expected_soc,
                            details=(
                                f"Hour {r.hour} SoC loss ({diff:.6f} kWh) exceeds maximum allowable idle loss "
                                f"({max_idle_loss_step:.6f} kWh) from Hour {prev.hour} [excess={diff - max_idle_loss_step:.6e} kWh "
                                f"> tol {tolerance:.6e} kWh]."
                            ),
                        )
                    )

    # 9. Cumulative SoC continuity drift check per [D-26]
    if battery.capacity_kwh > 0.0 and evaluated_continuity_steps > 0:
        soc_cum_tol = compute_cumulative_tolerance(evaluated_continuity_steps, tolerance)
        if cum_soc_diff < -soc_cum_tol:
            violations.append(
                BatteryBoundaryViolation(
                    hour=records[-1].hour if records else 0,
                    timestamp=records[-1].timestamp if records else "",
                    violation_type=ViolationType.SOC_CUMULATIVE_DRIFT,
                    actual_value=cum_soc_diff,
                    limit_value=-soc_cum_tol,
                    details=(
                        f"Cumulative SoC gain ({-cum_soc_diff:.6e} kWh) exceeded cumulative tolerance "
                        f"({soc_cum_tol:.6e} kWh) across {evaluated_continuity_steps} evaluated hours."
                    ),
                )
            )
        elif cum_soc_diff > total_allowed_idle_loss + soc_cum_tol:
            violations.append(
                BatteryBoundaryViolation(
                    hour=records[-1].hour if records else 0,
                    timestamp=records[-1].timestamp if records else "",
                    violation_type=ViolationType.SOC_CUMULATIVE_DRIFT,
                    actual_value=cum_soc_diff,
                    limit_value=total_allowed_idle_loss + soc_cum_tol,
                    details=(
                        f"Cumulative SoC drift ({cum_soc_diff:.6e} kWh) exceeded total allowed idle loss "
                        f"({total_allowed_idle_loss:.6e} kWh) plus cumulative tolerance ({soc_cum_tol:.6e} kWh) "
                        f"[limit={total_allowed_idle_loss + soc_cum_tol:.6e} kWh] across {evaluated_continuity_steps} evaluated hours."
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
    initial_soc_kwh: float | None = None,
) -> VerificationReport:
    """Execute complete verification harness across a simulation time series.

    Validates both hourly energy conservation invariants and (if battery is provided)
    battery physical boundary conditions and hour-to-hour SoC continuity.

    Args:
        records: Sequence of HourlyRecord instances.
        battery: Optional Battery instance. If provided, battery boundaries are checked.
        tolerance: Per-hour energy balance tolerance (default 1e-5 kWh).
        cumulative_tolerance: Optional cumulative net drift tolerance (default per [D-21]).
        allow_emergency_drawdown: Whether to permit SoC below min_soc during emergency blackouts.
        delta_t_hours: Hourly timestep duration.
        initial_soc_kwh: Optional initial SoC before record 0 for verifying first timestep.

    Returns:
        VerificationReport containing full diagnostics.
    """
    conservation_violations = check_energy_conservation(
        records=records,
        tolerance=tolerance,
        cumulative_tolerance=cumulative_tolerance,
    )

    subflow_violations = check_subflow_balance(
        records=records,
        tolerance=tolerance,
    )

    battery_violations: list[BatteryBoundaryViolation] = []
    if battery is not None:
        battery_violations = validate_battery_boundaries(
            records=records,
            battery=battery,
            allow_emergency_drawdown=allow_emergency_drawdown,
            delta_t_hours=delta_t_hours,
            initial_soc_kwh=initial_soc_kwh,
            tolerance=tolerance,
        )

    # Compute aggregate stats using signed_residual_kwh
    net_drift = sum(r.signed_residual_kwh for r in records)
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
        subflow_violations=subflow_violations,
    )


def assert_simulation_valid(
    records: Sequence[HourlyRecord],
    battery: Battery | None = None,
    tolerance: float = 1e-5,
    cumulative_tolerance: float | None = None,
    allow_emergency_drawdown: bool = False,
    delta_t_hours: float = 1.0,
    initial_soc_kwh: float | None = None,
) -> None:
    """Assertion helper for test suites. Raises AssertionError with detailed report on failure."""
    report = run_verification_harness(
        records=records,
        battery=battery,
        tolerance=tolerance,
        cumulative_tolerance=cumulative_tolerance,
        allow_emergency_drawdown=allow_emergency_drawdown,
        delta_t_hours=delta_t_hours,
        initial_soc_kwh=initial_soc_kwh,
    )
    if not report.is_valid:
        raise AssertionError(f"Simulation verification failed:\n{report.summary()}")


def create_golden_scenario(battery: Battery | None = None) -> list[HourlyRecord]:
    """Construct a canonical 48-hour synthetic reference scenario with exact energy conservation.

    The scenario exercises all primary physical microgrid states:
    - Day 1 (Hours 1–24): Normal grid operation.
      - Hours 1–4: Nighttime battery discharge down to min_soc floor (10.0 kWh), accounting for
        inverter/cell efficiency (losses reflected in stored SoC).
      - Hours 5–6: Nighttime grid import sustaining baseload while battery sits at floor.
      - Hours 7–9: Morning solar generation ramp, serving demand and charging battery with conversion efficiency.
      - Hours 10–14: Peak midday solar surplus filling battery to 100% capacity (100.0 kWh), then curtailing.
      - Hour 15: Exact zero net-load balance (solar generation strictly equals demand).
      - Hours 16–20: Afternoon/evening solar decline supplemented by battery discharge.
      - Hours 21–24: Evening transition back to grid import after battery reaches min_soc.
    - Day 2 (Hours 25–48): Outage resilience and recovery.
      - Hours 25–29: Morning pre-outage charging to full capacity (100 kWh).
      - Hours 30–37: 8-hour grid blackout (grid_available=False), shedding Tier 3 comfort
        cooling to Tier 2 essential load (5.0 kWh), sustained by islanded battery and solar.
      - Hours 38–48: Grid restoration, battery post-outage evening discharge and recovery.

    All 48 hours have identically zero energy balance residuals (residual = 0.000000 kWh),
    strictly conform to Battery boundaries, and satisfy hour-to-hour SoC continuity under [D-25].
    """
    bat = battery or Battery(capacity_kwh=100.0)
    records: list[HourlyRecord] = []

    eta_chg = math.sqrt(bat.round_trip_efficiency)
    eta_dis = math.sqrt(bat.round_trip_efficiency)

    # State tracking
    current_soc = 50.0  # Initial SoC at start of Day 1 (kWh)

    # Calculated schedule parameters maintaining strict exact balances:
    dis_h1_4 = 10.0 * eta_dis
    needed_chg_h10 = (100.0 - (10.0 + 10.0 * eta_chg + 25.0 * eta_chg + 45.0 * eta_chg)) / eta_chg

    # H21: discharge exactly to 10.0 floor
    soc_before_h21 = 100.0 - (15.0 + 15.0 + 20.0 + 15.0 + 15.0) / eta_dis
    dis_h21 = (soc_before_h21 - 10.0) * eta_dis

    # H27-29: pre-charge to 100.0 full capacity before outage
    needed_chg_h29 = (100.0 - (10.0 + 15.0 * eta_chg + 40.0 * eta_chg)) / eta_chg

    # Outage H30-37 (8 hours):
    # H30 has solar 10, served 5, curtailed 5, bat_chg=0, bat_dis=0.
    # H31-37 (7 hours): served 5.0, bat_dis = 5.0.
    soc_after_outage = 100.0 - (7 * 5.0) / eta_dis

    # H38-41: discharge down to 10.0 floor upon grid return
    total_avail_ac = (soc_after_outage - 10.0) * eta_dis
    dis_h38_40 = 15.0
    dis_h41 = total_avail_ac - 3 * dis_h38_40

    day_1_plan = [
        (1, 0.0, 10.0, True, 3, dis_h1_4, 0.0),
        (2, 0.0, 10.0, True, 3, dis_h1_4, 0.0),
        (3, 0.0, 10.0, True, 3, dis_h1_4, 0.0),
        (4, 0.0, 10.0, True, 3, dis_h1_4, 0.0),
        (5, 0.0, 10.0, True, 3, 0.0, 0.0),
        (6, 0.0, 10.0, True, 3, 0.0, 0.0),
        (7, 20.0, 10.0, True, 3, 0.0, 10.0),
        (8, 40.0, 15.0, True, 3, 0.0, 25.0),
        (9, 65.0, 20.0, True, 3, 0.0, 45.0),
        (10, 80.0, 25.0, True, 3, 0.0, needed_chg_h10),
        (11, 85.0, 30.0, True, 3, 0.0, 0.0),
        (12, 90.0, 30.0, True, 3, 0.0, 0.0),
        (13, 70.0, 30.0, True, 3, 0.0, 0.0),
        (14, 45.0, 25.0, True, 3, 0.0, 0.0),
        (15, 25.0, 25.0, True, 3, 0.0, 0.0),
        (16, 10.0, 25.0, True, 3, 15.0, 0.0),
        (17, 5.0, 20.0, True, 3, 15.0, 0.0),
        (18, 0.0, 20.0, True, 3, 20.0, 0.0),
        (19, 0.0, 15.0, True, 3, 15.0, 0.0),
        (20, 0.0, 15.0, True, 3, 15.0, 0.0),
        (21, 0.0, 15.0, True, 3, dis_h21, 0.0),
        (22, 0.0, 10.0, True, 3, 0.0, 0.0),
        (23, 0.0, 10.0, True, 3, 0.0, 0.0),
        (24, 0.0, 10.0, True, 3, 0.0, 0.0),
    ]

    day_2_plan = [
        (25, 0.0, 10.0, True, 3, 0.0, 0.0),
        (26, 0.0, 10.0, True, 3, 0.0, 0.0),
        (27, 25.0, 10.0, True, 3, 0.0, 15.0),
        (28, 55.0, 15.0, True, 3, 0.0, 40.0),
        (29, 65.0, 20.0, True, 3, 0.0, needed_chg_h29),
        (30, 10.0, 25.0, False, 2, 0.0, 0.0),
        (31, 0.0, 25.0, False, 2, 5.0, 0.0),
        (32, 0.0, 25.0, False, 2, 5.0, 0.0),
        (33, 0.0, 25.0, False, 2, 5.0, 0.0),
        (34, 0.0, 25.0, False, 2, 5.0, 0.0),
        (35, 0.0, 25.0, False, 2, 5.0, 0.0),
        (36, 0.0, 25.0, False, 2, 5.0, 0.0),
        (37, 0.0, 25.0, False, 2, 5.0, 0.0),
        (38, 0.0, 15.0, True, 3, dis_h38_40, 0.0),
        (39, 0.0, 15.0, True, 3, dis_h38_40, 0.0),
        (40, 0.0, 15.0, True, 3, dis_h38_40, 0.0),
        (41, 0.0, 15.0, True, 3, dis_h41, 0.0),
        (42, 0.0, 10.0, True, 3, 0.0, 0.0),
        (43, 0.0, 10.0, True, 3, 0.0, 0.0),
        (44, 0.0, 10.0, True, 3, 0.0, 0.0),
        (45, 0.0, 10.0, True, 3, 0.0, 0.0),
        (46, 0.0, 10.0, True, 3, 0.0, 0.0),
        (47, 0.0, 10.0, True, 3, 0.0, 0.0),
        (48, 0.0, 10.0, True, 3, 0.0, 0.0),
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

        current_soc = current_soc + eta_chg * bat_chg - (bat_dis / eta_dis)

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
            battery_soc_kwh=round(current_soc, 8),
            battery_charge_kwh=bat_chg,
            battery_discharge_kwh=bat_dis,
            grid_import_kwh=grid_import,
            unserved_load_kwh=unserved,
            grid_available=grid_avail,
            active_load_tier=tier,
        )
        records.append(rec)

    return records
