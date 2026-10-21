"""Unit tests and property-based verification for BAT-001 Battery Dispatch Dynamics.

Verifies step_battery efficiency split, C-rate limits, headroom/floor limits,
simultaneous charge/discharge rejection, zero-capacity handling, and full
invariant compliance against run_verification_harness.
"""

from __future__ import annotations

import inspect
import math

import hypothesis
import hypothesis.strategies as st
import pytest

from ccis_sim.battery.dynamics import step_battery
from ccis_sim.core.interfaces import BatteryStepResult
from ccis_sim.core.models import Battery, HourlyRecord, LoadTier
from ccis_sim.core.verification import run_verification_harness


@pytest.fixture
def standard_battery() -> Battery:
    """Standard 100 kWh, 92% RTE, 0.5C charge, 1.0C discharge battery."""
    return Battery(
        capacity_kwh=100.0,
        round_trip_efficiency=0.92,
        min_soc_pct=0.10,
        max_charge_c_rate=0.5,
        max_discharge_c_rate=1.0,
    )


def test_contract_signature_conformance() -> None:
    """Validate that step_battery public signature conforms exactly to contract."""
    sig = inspect.signature(step_battery)
    params = list(sig.parameters.values())

    assert len(params) == 6
    assert params[0].name == "soc_kwh"
    assert params[1].name == "battery"
    assert params[2].name == "charge_request_kwh"
    assert params[3].name == "discharge_request_kwh"
    assert params[4].name == "soc_floor_kwh"
    assert params[4].kind == inspect.Parameter.KEYWORD_ONLY
    assert params[4].default is None
    assert params[5].name == "delta_t_hours"
    assert params[5].kind == inspect.Parameter.KEYWORD_ONLY
    assert params[5].default == 1.0


def test_efficiency_split_roundtrip(standard_battery: Battery) -> None:
    """Verify symmetric sqrt(RTE) efficiency split per [D-25].

    Charging with E_ac stores E_ac * sqrt(RTE) chemical kWh.
    Discharging chemical energy back to initial SoC returns E_ac * RTE AC kWh.
    """
    initial_soc = 20.0
    charge_req = 30.0  # AC kWh

    eta = math.sqrt(standard_battery.round_trip_efficiency)

    # 1. Charge step
    res_chg = step_battery(
        soc_kwh=initial_soc,
        battery=standard_battery,
        charge_request_kwh=charge_req,
        discharge_request_kwh=0.0,
    )
    assert res_chg.charge_kwh == pytest.approx(charge_req)
    assert res_chg.charge_curtailed_kwh == 0.0
    expected_soc_after_chg = initial_soc + charge_req * eta
    assert res_chg.soc_kwh == pytest.approx(expected_soc_after_chg)

    # 2. Discharge step back to initial SoC
    # To return to initial_soc, chemical energy to remove is charge_req * eta
    # AC energy delivered will be (charge_req * eta) * eta = charge_req * RTE
    res_dis = step_battery(
        soc_kwh=res_chg.soc_kwh,
        battery=standard_battery,
        charge_request_kwh=0.0,
        discharge_request_kwh=100.0,  # Request plenty
        soc_floor_kwh=initial_soc,
    )
    expected_ac_delivered = charge_req * standard_battery.round_trip_efficiency
    assert res_dis.discharge_kwh == pytest.approx(expected_ac_delivered)
    assert res_dis.soc_kwh == pytest.approx(initial_soc)

    # Round trip ratio
    rte_observed = res_dis.discharge_kwh / res_chg.charge_kwh
    assert rte_observed == pytest.approx(standard_battery.round_trip_efficiency)


def test_c_rate_caps(standard_battery: Battery) -> None:
    """Verify AC-side C-rate power caps (0.5C charge = 50 kW, 1.0C discharge = 100 kW)."""
    # 1. Charge C-rate cap at delta_t = 1.0 h
    res_chg = step_battery(
        soc_kwh=10.0,
        battery=standard_battery,
        charge_request_kwh=80.0,
        discharge_request_kwh=0.0,
    )
    assert res_chg.charge_kwh == pytest.approx(50.0)
    assert res_chg.charge_curtailed_kwh == pytest.approx(30.0)

    # 2. Charge C-rate cap at delta_t = 0.5 h (cap = 25 kWh)
    res_chg_half = step_battery(
        soc_kwh=10.0,
        battery=standard_battery,
        charge_request_kwh=40.0,
        discharge_request_kwh=0.0,
        delta_t_hours=0.5,
    )
    assert res_chg_half.charge_kwh == pytest.approx(25.0)
    assert res_chg_half.charge_curtailed_kwh == pytest.approx(15.0)

    # 3. Discharge C-rate cap at delta_t = 1.0 h
    # Battery at 100 kWh, min SoC = 10 kWh -> 90 kWh chemical available
    # 90 * sqrt(0.92) ~= 86.32 kWh AC, which is less than 100 kW * 1 h cap.
    # To test discharge C-rate cap, use a 200 kWh battery where 0.5C charge / 1.0C discharge = 200 kW
    # or test at delta_t = 0.5 h on standard battery where 1.0C * 100 kW * 0.5 h = 50 kWh cap.
    res_dis_half = step_battery(
        soc_kwh=100.0,
        battery=standard_battery,
        charge_request_kwh=0.0,
        discharge_request_kwh=80.0,
        delta_t_hours=0.5,
    )
    assert res_dis_half.discharge_kwh == pytest.approx(50.0)
    assert res_dis_half.discharge_unmet_kwh == pytest.approx(30.0)


def test_headroom_limiting(standard_battery: Battery) -> None:
    """Verify that charging is strictly limited by remaining capacity headroom."""
    eta = math.sqrt(standard_battery.round_trip_efficiency)
    cur_soc = 95.0
    headroom_chem = 5.0  # kWh chemical
    max_ac_charge = headroom_chem / eta  # ~= 5.21286 kWh AC

    res = step_battery(
        soc_kwh=cur_soc,
        battery=standard_battery,
        charge_request_kwh=20.0,
        discharge_request_kwh=0.0,
    )
    assert res.charge_kwh == pytest.approx(max_ac_charge)
    assert res.soc_kwh == pytest.approx(100.0)
    assert res.charge_curtailed_kwh == pytest.approx(20.0 - max_ac_charge)


def test_floor_limiting(standard_battery: Battery) -> None:
    """Verify that discharge is strictly bounded by minimum SoC floor."""
    eta = math.sqrt(standard_battery.round_trip_efficiency)
    # Default floor: battery.min_soc_kwh = 10.0 kWh
    cur_soc = 15.0
    avail_chem = 5.0
    max_ac_discharge = avail_chem * eta

    res = step_battery(
        soc_kwh=cur_soc,
        battery=standard_battery,
        charge_request_kwh=0.0,
        discharge_request_kwh=20.0,
    )
    assert res.discharge_kwh == pytest.approx(max_ac_discharge)
    assert res.soc_kwh == pytest.approx(10.0)
    assert res.discharge_unmet_kwh == pytest.approx(20.0 - max_ac_discharge)

    # Custom higher floor (e.g. 20 kWh)
    res_custom = step_battery(
        soc_kwh=cur_soc,
        battery=standard_battery,
        charge_request_kwh=0.0,
        discharge_request_kwh=20.0,
        soc_floor_kwh=20.0,
    )
    # Since cur_soc (15.0) < floor (20.0), available is 0
    assert res_custom.discharge_kwh == 0.0
    assert res_custom.soc_kwh == 15.0
    assert res_custom.discharge_unmet_kwh == 20.0

    # Emergency drawdown floor down to 0.0 kWh
    res_emergency = step_battery(
        soc_kwh=10.0,
        battery=standard_battery,
        charge_request_kwh=0.0,
        discharge_request_kwh=20.0,
        soc_floor_kwh=0.0,
    )
    assert res_emergency.discharge_kwh == pytest.approx(10.0 * eta)
    assert res_emergency.soc_kwh == pytest.approx(0.0)


def test_simultaneous_request_rejected(standard_battery: Battery) -> None:
    """Verify that simultaneous charge and discharge requests (> 1e-6 kWh) raise ValueError."""
    with pytest.raises(ValueError, match="Simultaneous charging.*discharging.*prohibited"):
        step_battery(
            soc_kwh=50.0,
            battery=standard_battery,
            charge_request_kwh=5.0,
            discharge_request_kwh=5.0,
        )


def test_zero_capacity_case() -> None:
    """Verify zero-capacity battery handles all flows as zero and SoC as zero."""
    zero_bat = Battery(capacity_kwh=0.0, round_trip_efficiency=0.92, min_soc_pct=0.10)
    res = step_battery(
        soc_kwh=0.0,
        battery=zero_bat,
        charge_request_kwh=15.0,
        discharge_request_kwh=0.0,
    )
    assert res.soc_kwh == 0.0
    assert res.charge_kwh == 0.0
    assert res.charge_curtailed_kwh == 15.0

    res_dis = step_battery(
        soc_kwh=0.0,
        battery=zero_bat,
        charge_request_kwh=0.0,
        discharge_request_kwh=10.0,
    )
    assert res_dis.soc_kwh == 0.0
    assert res_dis.discharge_kwh == 0.0
    assert res_dis.discharge_unmet_kwh == 10.0


def test_input_validation_and_errors(standard_battery: Battery) -> None:
    """Verify parameter type, finiteness, and negative value checks."""
    # Not a Battery instance
    with pytest.raises(TypeError, match="battery must be an instance of Battery"):
        step_battery(soc_kwh=10.0, battery="not_a_battery", charge_request_kwh=1.0, discharge_request_kwh=0.0)  # type: ignore

    # Non-finite values
    with pytest.raises(ValueError, match="must be finite"):
        step_battery(soc_kwh=float("nan"), battery=standard_battery, charge_request_kwh=0.0, discharge_request_kwh=0.0)
    with pytest.raises(ValueError, match="must be finite"):
        step_battery(soc_kwh=10.0, battery=standard_battery, charge_request_kwh=float("inf"), discharge_request_kwh=0.0)

    # Negative values
    with pytest.raises(ValueError, match="non-negative"):
        step_battery(soc_kwh=10.0, battery=standard_battery, charge_request_kwh=-1.0, discharge_request_kwh=0.0)
    with pytest.raises(ValueError, match="non-negative"):
        step_battery(soc_kwh=10.0, battery=standard_battery, charge_request_kwh=0.0, discharge_request_kwh=-1.0)
    with pytest.raises(ValueError, match="strictly positive"):
        step_battery(soc_kwh=10.0, battery=standard_battery, charge_request_kwh=0.0, discharge_request_kwh=0.0, delta_t_hours=0.0)

    # Initial SoC out of range
    with pytest.raises(ValueError, match="exceeds battery rated capacity"):
        step_battery(soc_kwh=150.0, battery=standard_battery, charge_request_kwh=0.0, discharge_request_kwh=0.0)
    with pytest.raises(ValueError, match="cannot be physically negative"):
        step_battery(soc_kwh=-5.0, battery=standard_battery, charge_request_kwh=0.0, discharge_request_kwh=0.0)

    # soc_floor_kwh out of range
    with pytest.raises(ValueError, match="cannot exceed battery capacity"):
        step_battery(soc_kwh=50.0, battery=standard_battery, charge_request_kwh=0.0, discharge_request_kwh=0.0, soc_floor_kwh=120.0)
    with pytest.raises(ValueError, match="cannot be physically negative"):
        step_battery(soc_kwh=50.0, battery=standard_battery, charge_request_kwh=0.0, discharge_request_kwh=0.0, soc_floor_kwh=-1.0)


def test_determinism(standard_battery: Battery) -> None:
    """Verify identical inputs yield identical outputs bit-for-bit."""
    reqs = [(10.0, 0.0), (30.0, 0.0), (0.0, 25.0), (0.0, 0.0), (5.0, 0.0)]
    soc_run1 = 20.0
    results_run1 = []
    for chg, dis in reqs:
        res = step_battery(soc_kwh=soc_run1, battery=standard_battery, charge_request_kwh=chg, discharge_request_kwh=dis)
        results_run1.append(res)
        soc_run1 = res.soc_kwh

    soc_run2 = 20.0
    results_run2 = []
    for chg, dis in reqs:
        res = step_battery(soc_kwh=soc_run2, battery=standard_battery, charge_request_kwh=chg, discharge_request_kwh=dis)
        results_run2.append(res)
        soc_run2 = res.soc_kwh

    for r1, r2 in zip(results_run1, results_run2):
        assert r1 == r2


@hypothesis.given(
    requests=st.lists(
        st.tuples(
            st.floats(min_value=0.0, max_value=80.0, allow_nan=False, allow_infinity=False),
            st.booleans(),  # True for charge, False for discharge
        ),
        min_size=10,
        max_size=48,
    )
)
@hypothesis.settings(max_examples=40, deadline=None)
def test_hypothesis_property_verification_harness(requests: list[tuple[float, bool]]) -> None:
    """Property test: arbitrary charge/discharge sequences chained over hours pass the verification harness."""
    battery = Battery(
        capacity_kwh=100.0,
        round_trip_efficiency=0.92,
        min_soc_pct=0.10,
        max_charge_c_rate=0.5,
        max_discharge_c_rate=1.0,
        self_discharge_pct_per_month=0.0,  # Dynamics module does not apply idle losses
        tare_loss_kw=0.0,
    )

    initial_soc = 50.0
    cur_soc = initial_soc
    records: list[HourlyRecord] = []

    for hour_idx, (magnitude, is_charge) in enumerate(requests, start=1):
        chg_req = magnitude if is_charge else 0.0
        dis_req = magnitude if not is_charge else 0.0

        step_res = step_battery(
            soc_kwh=cur_soc,
            battery=battery,
            charge_request_kwh=chg_req,
            discharge_request_kwh=dis_req,
        )

        cur_soc = step_res.soc_kwh

        # Construct a physically balanced HourlyRecord around this battery step
        solar_gen = step_res.charge_kwh
        solar_to_battery = step_res.charge_kwh
        curtailed = step_res.charge_curtailed_kwh

        demand_gross = step_res.discharge_kwh
        demand_served = step_res.discharge_kwh
        unserved = step_res.discharge_unmet_kwh

        record = HourlyRecord(
            hour=hour_idx,
            timestamp=f"2019-01-01 {hour_idx-1:02d}:00:00+08:00",
            temp_ambient_c=25.0,
            humidity_rel_pct=60.0,
            ghi_w_m2=0.0,
            demand_gross_kwh=demand_gross,
            demand_served_kwh=demand_served,
            solar_generation_kwh=solar_gen,
            solar_to_demand_kwh=0.0,
            solar_to_battery_kwh=solar_to_battery,
            solar_curtailed_kwh=0.0,  # Battery step curtailment isn't solar curtailment unless on bus
            battery_soc_kwh=step_res.soc_kwh,
            battery_charge_kwh=step_res.charge_kwh,
            battery_discharge_kwh=step_res.discharge_kwh,
            grid_import_kwh=0.0,
            unserved_load_kwh=0.0,
            grid_available=True,
            active_load_tier=LoadTier.TIER_3_SHEDDABLE,
        )
        records.append(record)

    # Invariant harness evaluation
    report = run_verification_harness(
        records,
        battery=battery,
        initial_soc_kwh=initial_soc,
    )
    assert report.is_valid, (
        f"Verification harness found violations: "
        f"conservation={report.conservation_violations}, "
        f"battery={report.battery_violations}, "
        f"subflow={report.subflow_violations}, "
        f"cum_drift={report.cumulative_net_drift_kwh}"
    )
