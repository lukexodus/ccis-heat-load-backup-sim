"""Battery dispatch dynamics, State-of-Charge tracking, and physical limits.

Implements the single time-step battery dispatch algorithm (BAT-001) per
decision [D-25], [D-26], and [D-31].
"""

from __future__ import annotations

import math

from ccis_sim.core.interfaces import BatteryStepResult
from ccis_sim.core.models import Battery


def step_battery(
    soc_kwh: float,
    battery: Battery,
    charge_request_kwh: float,
    discharge_request_kwh: float,
    *,
    soc_floor_kwh: float | None = None,
    delta_t_hours: float = 1.0,
) -> BatteryStepResult:
    """Dispatches battery energy storage for a single discrete time-step.

    Computes AC-side charge and discharge flows, shortfalls, and the resulting
    chemical State-of-Charge (SoC) subject to physical inverter power limits
    (C-rate), usable energy boundaries, and symmetric conversion efficiency.

    [ASSUMPTION] Per decision [D-25], charge and discharge are modeled strictly
    as AC-side flows (matching microgrid bus power conservation). Electrochemical
    and power electronics conversion losses are accounted for symmetrically on the
    chemical State-of-Charge:
        eta_chg = eta_dis = sqrt(battery.round_trip_efficiency).
    When charging:
        Delta SoC = +eta_chg * charge_kwh
    When discharging:
        Delta SoC = -discharge_kwh / eta_dis

    [ASSUMPTION] Idle losses, ambient self-discharge (2%/month), and inverter tare
    standby losses are explicitly excluded from this module per [D-26] and are
    managed independently by BAT-002 (ccis_sim.battery.reserve.apply_idle_losses).

    [ASSUMPTION] Simultaneous charge and discharge requests exceeding 1e-6 kWh
    each are physically mutually exclusive and raise a ValueError at the source.

    [ASSUMPTION] Floating-point comparison tolerance fp_tol = 1e-9 is applied
    to guard boundary evaluations against benign numerical representation noise.

    Args:
        soc_kwh: Stored chemical State-of-Charge at the start of the timestep (kWh).
        battery: Battery specification defining capacity, C-rates, and efficiency.
        charge_request_kwh: Desired AC-side energy to charge into the battery (kWh).
        discharge_request_kwh: Desired AC-side energy to discharge from the battery (kWh).
        soc_floor_kwh: Optional minimum allowable chemical SoC floor (kWh).
            Defaults to battery.min_soc_kwh if None.
        delta_t_hours: Timestep duration in hours (default 1.0).

    Returns:
        BatteryStepResult containing resulting chemical SoC, AC-side flows, and shortfalls.

    Raises:
        TypeError: If battery is not a Battery instance or numeric fields are invalid types.
        ValueError: If non-finite values are passed, requests are negative, delta_t_hours <= 0,
            or simultaneous charging and discharging is requested.
    """
    if not isinstance(battery, Battery):
        raise TypeError(f"battery must be an instance of Battery, got {type(battery)}")

    # Type and finiteness validation
    for name, val in (
        ("soc_kwh", soc_kwh),
        ("charge_request_kwh", charge_request_kwh),
        ("discharge_request_kwh", discharge_request_kwh),
        ("delta_t_hours", delta_t_hours),
    ):
        if not isinstance(val, (int, float)):
            raise TypeError(f"'{name}' must be numeric, got {type(val)}")
        if math.isnan(val) or math.isinf(val):
            raise ValueError(f"'{name}' must be finite, got {val}")

    if delta_t_hours <= 0.0:
        raise ValueError(f"delta_t_hours must be strictly positive, got {delta_t_hours}")

    if charge_request_kwh < 0.0:
        raise ValueError(f"charge_request_kwh must be non-negative, got {charge_request_kwh}")

    if discharge_request_kwh < 0.0:
        raise ValueError(f"discharge_request_kwh must be non-negative, got {discharge_request_kwh}")

    fp_tol = 1e-9

    # Physical boundary check on initial SoC
    if soc_kwh < -fp_tol:
        raise ValueError(f"soc_kwh cannot be physically negative, got {soc_kwh}")

    # Mutual exclusivity check
    if charge_request_kwh > 1e-6 and discharge_request_kwh > 1e-6:
        raise ValueError(
            f"Simultaneous charging ({charge_request_kwh:.6f} kWh) and discharging "
            f"({discharge_request_kwh:.6f} kWh) is physically prohibited."
        )

    # Zero-capacity battery edge case (e.g. grid-only baseline per [D-23])
    if battery.capacity_kwh == 0.0:
        return BatteryStepResult(
            soc_kwh=0.0,
            charge_kwh=0.0,
            discharge_kwh=0.0,
            charge_curtailed_kwh=charge_request_kwh,
            discharge_unmet_kwh=discharge_request_kwh,
        )

    if soc_kwh > battery.capacity_kwh + fp_tol:
        raise ValueError(
            f"soc_kwh ({soc_kwh:.6f} kWh) exceeds battery rated capacity "
            f"({battery.capacity_kwh:.6f} kWh)."
        )

    # Validate soc_floor_kwh if provided
    if soc_floor_kwh is not None:
        if not isinstance(soc_floor_kwh, (int, float)):
            raise TypeError(f"'soc_floor_kwh' must be numeric, got {type(soc_floor_kwh)}")
        if math.isnan(soc_floor_kwh) or math.isinf(soc_floor_kwh):
            raise ValueError(f"'soc_floor_kwh' must be finite, got {soc_floor_kwh}")
        if soc_floor_kwh < -fp_tol:
            raise ValueError(f"'soc_floor_kwh' cannot be physically negative, got {soc_floor_kwh}")
        if soc_floor_kwh > battery.capacity_kwh + fp_tol:
            raise ValueError(
                f"'soc_floor_kwh' ({soc_floor_kwh:.6f} kWh) cannot exceed battery capacity "
                f"({battery.capacity_kwh:.6f} kWh)."
            )
        effective_floor = max(0.0, min(battery.capacity_kwh, float(soc_floor_kwh)))
    else:
        effective_floor = battery.min_soc_kwh

    # Clamp initial SoC within [0, capacity] to absorb fp noise
    cur_soc = max(0.0, min(battery.capacity_kwh, float(soc_kwh)))

    # Symmetric efficiency split per [D-25]
    eta_chg = math.sqrt(battery.round_trip_efficiency)
    eta_dis = math.sqrt(battery.round_trip_efficiency)

    # 1. Evaluate Charge Operation
    if charge_request_kwh > 1e-6:
        # C-rate power cap (AC side)
        max_charge_c_rate_kwh = battery.max_charge_power_kw * delta_t_hours
        # Headroom cap in chemical energy converted to AC equivalent
        headroom_chemical_kwh = max(0.0, battery.capacity_kwh - cur_soc)
        max_charge_headroom_kwh = headroom_chemical_kwh / eta_chg

        max_charge_allowed_kwh = min(max_charge_c_rate_kwh, max_charge_headroom_kwh)
        actual_charge_kwh = min(charge_request_kwh, max_charge_allowed_kwh)

        # Update State-of-Charge
        delta_soc = actual_charge_kwh * eta_chg
        new_soc = min(battery.capacity_kwh, cur_soc + delta_soc)

        charge_curtailed_kwh = max(0.0, charge_request_kwh - actual_charge_kwh)

        return BatteryStepResult(
            soc_kwh=new_soc,
            charge_kwh=actual_charge_kwh,
            discharge_kwh=0.0,
            charge_curtailed_kwh=charge_curtailed_kwh,
            discharge_unmet_kwh=0.0,
        )

    # 2. Evaluate Discharge Operation
    if discharge_request_kwh > 1e-6:
        # C-rate power cap (AC side)
        max_discharge_c_rate_kwh = battery.max_discharge_power_kw * delta_t_hours
        # Available chemical energy above floor converted to AC equivalent
        available_chemical_kwh = max(0.0, cur_soc - effective_floor)
        max_discharge_floor_kwh = available_chemical_kwh * eta_dis

        max_discharge_allowed_kwh = min(max_discharge_c_rate_kwh, max_discharge_floor_kwh)
        actual_discharge_kwh = min(discharge_request_kwh, max_discharge_allowed_kwh)

        # Update State-of-Charge
        delta_soc = actual_discharge_kwh / eta_dis
        new_soc = max(effective_floor, cur_soc - delta_soc) if cur_soc >= effective_floor else cur_soc

        discharge_unmet_kwh = max(0.0, discharge_request_kwh - actual_discharge_kwh)

        return BatteryStepResult(
            soc_kwh=new_soc,
            charge_kwh=0.0,
            discharge_kwh=actual_discharge_kwh,
            charge_curtailed_kwh=0.0,
            discharge_unmet_kwh=discharge_unmet_kwh,
        )

    # 3. Idle / Zero-Flow Operation
    return BatteryStepResult(
        soc_kwh=cur_soc,
        charge_kwh=0.0,
        discharge_kwh=0.0,
        charge_curtailed_kwh=charge_request_kwh,
        discharge_unmet_kwh=discharge_request_kwh,
    )
