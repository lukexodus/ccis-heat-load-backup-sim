# Task Report: BAT-001 — Battery Dispatch Dynamics, SoC Tracking & Losses

**Date:** 2026-10-21  
**Agent:** gemini  
**Task ID:** BAT-001  
**Status:** done  
**Commit:** `feat(BAT-001): implement battery dispatch dynamics, SoC tracking, and limits`  
**Patch File:** `patch/BAT-001-gemini-battery-dynamics.patch`  

---

## 1. Executive Summary

This unit of work completes task `BAT-001` ("Battery Dispatch Dynamics, SoC Tracking & Losses"), delivering the single time-step battery dispatch algorithm (`step_battery`) that the `INT-001` simulation engine dispatcher invokes on every hourly iteration.

The implementation strictly adheres to the `docs/context/phase2-interface-contract.md` specification and verification harness conventions:
1. **Symmetric Round-Trip Efficiency Split (`[D-25]`):** Charge and discharge are modeled strictly as AC-side flows matching bus power conservation. Internal electrochemical and power electronic conversion losses are applied symmetrically to the chemical State-of-Charge via $\eta_{\text{chg}} = \eta_{\text{dis}} = \sqrt{\eta_{\text{rt}}} = \sqrt{0.92} \approx 0.9591663$.
2. **C-Rate Power Caps & Headroom/Floor Limiting:** Charging is bounded by the inverter 0.5C power cap ($0.5 \times C_{\text{bat}} \Delta t$) and available chemical headroom ($C_{\text{bat}} - \text{SoC}$). Discharging is bounded by the inverter 1.0C power cap ($1.0 \times C_{\text{bat}} \Delta t$) and available chemical energy above `soc_floor_kwh` (defaulting to `battery.min_soc_kwh`).
3. **Mutual Exclusivity & Source Prevention:** Simultaneous charge and discharge requests exceeding $10^{-6}\text{ kWh}$ each are rejected at the source via `ValueError`.
4. **Zero-Capacity Edge Handling:** Zero-capacity batteries report zero flows and zero SoC without numerical divergence.
5. **Decoupled Standby Losses:** Standby tare loss and ambient self-discharge are explicitly excluded from this module per [D-26] and deferred to `BAT-002` (`apply_idle_losses`).

All 10 dedicated unit and property tests in `tests/test_battery_dynamics.py` pass, and the complete project test suite passes cleanly with 148 passed tests (100% green).

---

## 2. Implementation Details

### 2.1 Changes Made

- `src/ccis_sim/battery/dynamics.py`: Created module implementing `step_battery` conforming to `phase2-interface-contract.md` and returning `BatteryStepResult`.
- `src/ccis_sim/battery/__init__.py`: Exported public symbol `step_battery`.
- `tests/test_battery_dynamics.py`: Created 10 test functions covering contract signature conformance, round-trip efficiency return, C-rate limiting (0.5C charge / 1.0C discharge), headroom and floor limits (including emergency drawdown to 0.0), simultaneous charge/discharge rejection, zero-capacity handling, input validation, execution determinism, and property-based verification using Hypothesis chaining multi-hour sequences against `run_verification_harness`.
- `docs/decisions/decision-log.md`: Appended decision `[D-31]` formalizing battery dispatch dynamics, AC-flow conversion accounting, and C-rate & headroom/floor limiting.
- `docs/tasks/status.md`: Updated `BAT-001` and subtasks `BAT-001.1`–`BAT-001.4` status to `done`.

### 2.2 Conformance to Specifications & Decisions

- **Contract Signatures:** Matches `docs/context/phase2-interface-contract.md` §3 exactly:
  `step_battery(soc_kwh: float, battery: Battery, charge_request_kwh: float, discharge_request_kwh: float, *, soc_floor_kwh: float | None = None, delta_t_hours: float = 1.0) -> BatteryStepResult`.
- **Pure Function Conventions:** `step_battery` has zero side-effects, no global state, and returns immutable `BatteryStepResult`.
- **First-Law Invariant Compliance:** Satisfies hour-to-hour SoC continuity $\text{SoC}_t = \text{SoC}_{t-1} + \eta_{\text{chg}} P_{\text{chg}} \Delta t - (P_{\text{dis}} / \eta_{\text{dis}}) \Delta t$ per `[D-25]` within $10^{-5}\text{ kWh}$.

---

## 3. Verification & Test Evidence

### 3.1 Test Execution

Command executed:
```bash
pytest -v
```

**Results:**
- Tests passed: 148
- Tests failed: 0
- Tests skipped: 0

Verbatim output excerpt from test run:
```text
Test session starts (platform: linux, Python 3.14.8, pytest 9.1.1, pytest-sugar 1.1.1)
rootdir: /home/lukexodus/projects/ccis-heat-load-backup-sim-BAT-001
configfile: pyproject.toml
testpaths: tests
plugins: instafail-0.5.0, sugar-1.1.1, case-1.5.3, requests-mock-1.12.1, cov-7.1.0, typeguard-4.6.0, anyio-4.15.1, platformdirs-4.13.0, hypothesis-6.169.0, inline-snapshot-0.36.0, time-machine-3.5.1
collected 148 items

 tests/test_baseline_smoke.py::test_baseline_simulation_record_count_and_hours ✓
 tests/test_battery_dynamics.py::test_contract_signature_conformance ✓
 tests/test_battery_dynamics.py::test_efficiency_split_roundtrip ✓
 tests/test_battery_dynamics.py::test_c_rate_caps ✓
 tests/test_battery_dynamics.py::test_headroom_limiting ✓
 tests/test_battery_dynamics.py::test_floor_limiting ✓
 tests/test_battery_dynamics.py::test_simultaneous_request_rejected ✓
 tests/test_battery_dynamics.py::test_zero_capacity_case ✓
 tests/test_battery_dynamics.py::test_input_validation_and_errors ✓
 tests/test_battery_dynamics.py::test_determinism ✓
 tests/test_battery_dynamics.py::test_hypothesis_property_verification_harness ✓
 tests/test_conservation_checker.py::...
 tests/test_load_shedding.py::...
 tests/test_weather_ingest.py::...

Results (7.93s):
     148 passed
```

### 3.2 Edge Cases & Negative Testing

1. **Non-finite Values:** `NaN` and `+inf` inputs across all float parameters (`soc_kwh`, requests, `delta_t_hours`, `soc_floor_kwh`) raise `ValueError`.
2. **Negative Values:** Negative requests, negative initial SoC, or non-positive `delta_t_hours` raise `ValueError`.
3. **Capacity Overshoot:** Initial SoC or floor exceeding rated capacity raises `ValueError`.
4. **Mutual Exclusivity:** Requesting both charge and discharge ($> 10^{-6}\text{ kWh}$) raises `ValueError`.
5. **Zero Capacity:** When `battery.capacity_kwh == 0.0`, returns zero flows and marks requests as curtailed/unmet.
6. **Property Invariant Testing:** Hypothesis generates randomized multi-hour operational sequences, verifying that every synthesized time series passes `run_verification_harness` with zero conservation or boundary violations.

---

## 4. Decisions Recorded

- **[D-31]**: Formalized battery dispatch dynamics, AC-side conversion efficiency split ($\eta_{\text{chg}} = \eta_{\text{dis}} = \sqrt{\eta_{\text{rt}}}$), C-rate and headroom/floor bounds, mutual exclusivity enforcement, and separation of idle standby losses.

---

## 5. Unified Git Diff

```diff
diff --git a/docs/decisions/decision-log.md b/docs/decisions/decision-log.md
index 52af966..c071190 100644
--- a/docs/decisions/decision-log.md
+++ b/docs/decisions/decision-log.md
@@ -243,3 +243,24 @@ This file exists so that across API-credit-limited handoffs between APC AI insta
      - In accordance with the prompt specification, this discrepancy from D-10's nominal 2/18/80 split is explicitly exposed via `compute_tier_audit_shares` and reported as an audit reality rather than forced to match nominal assumptions.
 - **Reasoning:** Formalizes exact deterministic load-shedding dispatch rules and energy accounting, guaranteeing conservation and clean policy decoupling ahead of full system integration.
 - **Affects:** `OUT-002`, `INT-001`, `INT-002`, `DEC-002`.
+
+**[D-31]** Battery Dispatch Dynamics, AC-Flow Conversion Accounting, and C-Rate & Headroom/Floor Limiting.  
+- **Date / Session:** 2026-10-21  
+- **Decision:**  
+  1. **Canonical Time-Step Battery Dispatch (`step_battery`):** Implemented in `src/ccis_sim/battery/dynamics.py` conforming strictly to the contract in `docs/context/phase2-interface-contract.md`.
+  2. **AC-Side Energy Flow & Conversion Conventions:**
+     - Charge request ($P_{\text{chg, req}}$) and discharge request ($P_{\text{dis, req}}$) are AC-side quantities at the microgrid bus.
+     - Symmetrical conversion efficiency $\eta_{\text{chg}} = \eta_{\text{dis}} = \sqrt{\eta_{\text{rt}}} = \sqrt{0.92}$ per [D-25].
+     - Energy stored during charge: $\Delta \text{SoC} = \eta_{\text{chg}} \cdot P_{\text{chg, ac}} \Delta t$.
+     - Energy extracted during discharge: $\Delta \text{SoC} = (P_{\text{dis, ac}} / \eta_{\text{dis}}) \Delta t$.
+  3. **C-Rate and Energy Headroom / Floor Constraints:**
+     - Maximum AC charge is constrained by $\min(P_{\text{max, chg}} \Delta t, (C_{\text{bat}} - \text{SoC}_{t-1}) / \eta_{\text{chg}})$.
+     - Maximum AC discharge is constrained by $\min(P_{\text{max, dis}} \Delta t, \max(0, \text{SoC}_{t-1} - \text{SoC}_{\text{floor}}) \cdot \eta_{\text{dis}})$, defaulting $\text{SoC}_{\text{floor}} = \text{battery.min\_soc\_kwh}$.
+     - When `cur_soc <= effective_floor`, discharge is zero and State-of-Charge remains unchanged without artificial inflation.
+  4. **Mutual Exclusivity & Zero-Capacity Edge Cases:**
+     - Simultaneous requests exceeding $10^{-6}\text{ kWh}$ each trigger `ValueError` at the source.
+     - For zero-capacity battery ($C_{\text{bat}} = 0$), all flows are 0, SoC is 0, and requests are reported as 100% curtailed or unmet.
+  5. **Idle Loss Separation:** Idle self-discharge and standby tare losses are explicitly excluded from this module per [D-26] and deferred to BAT-002.
+- **Reasoning:** Enforces exact first-law thermodynamic conservation and verification harness compliance for battery dispatch without leaky abstractions.
+- **Affects:** `BAT-001`, `BAT-002`, `INT-001`, `INT-002`.
+
diff --git a/docs/tasks/status.md b/docs/tasks/status.md
index 2621b96..ae3ac3f 100644
--- a/docs/tasks/status.md
+++ b/docs/tasks/status.md
@@ -101,11 +101,11 @@ Status: **open**
 | SOL-002.2   | Model inverter peak efficiency (98%) and DC/AC clipping limits                                       | `open` | Inverter clipping  |
 | SOL-002.3   | Incorporate balance-of-system derates (PR = 0.77, soiling, wiring)                                   | `open` | BOS losses         |
 | SOL-002.4   | Validate annual specific yield against Luzon benchmark (1,298 kWh/kWp)                               | `open` | Yield benchmark    |
-| **BAT-001** | **Battery Dispatch Dynamics, SoC Tracking & Losses**                                                 | `open` |                    |
-| BAT-001.1   | Implement time-stepped State-of-Charge tracking logic                                                | `open` | SoC recursion      |
-| BAT-001.2   | Apply LFP round-trip efficiency (92% RTE, $\sqrt{\eta}$ charge/discharge)                            | `open` | Efficiency losses  |
-| BAT-001.3   | Enforce charge/discharge power limits (0.5C charge, 1.0C discharge)                                  | `open` | C-rate constraints |
-| BAT-001.4   | Write unit tests for simultaneous charge/discharge prevention                                        | `open` | Boundary tests     |
+| **BAT-001** | **Battery Dispatch Dynamics, SoC Tracking & Losses**                                                 | `done` | [BAT-001-gemini-battery-dynamics.md](../reports/BAT-001-gemini-battery-dynamics.md)                      |
+| BAT-001.1   | Implement time-stepped State-of-Charge tracking logic                                                | `done` | SoC recursion      |
+| BAT-001.2   | Apply LFP round-trip efficiency (92% RTE, $\sqrt{\eta}$ charge/discharge)                            | `done` | Efficiency losses  |
+| BAT-001.3   | Enforce charge/discharge power limits (0.5C charge, 1.0C discharge)                                  | `done` | C-rate constraints |
+| BAT-001.4   | Write unit tests for simultaneous charge/discharge prevention                                        | `done` | Boundary tests     |
 | **BAT-002** | **Battery Outage Reserve & State-of-Charge Constraints**                                             | `open` |                    |
 | BAT-002.1   | Enforce 10% minimum SoC reserve floor (90% usable DoD)                                               | `open` | Reserve floor      |
 | BAT-002.2   | Implement configurable emergency outage reserve %                                                    | `open` | Outage cushion     |
diff --git a/src/ccis_sim/battery/__init__.py b/src/ccis_sim/battery/__init__.py
index c54efb5..83d978a 100644
--- a/src/ccis_sim/battery/__init__.py
+++ b/src/ccis_sim/battery/__init__.py
@@ -1 +1,5 @@
 """Battery energy storage system (BESS) dispatch dynamics, state-of-charge, and limits."""
+
+from ccis_sim.battery.dynamics import step_battery
+
+__all__ = ["step_battery"]
diff --git a/src/ccis_sim/battery/dynamics.py b/src/ccis_sim/battery/dynamics.py
new file mode 100644
index 0000000..9df6b5c
--- /dev/null
+++ b/src/ccis_sim/battery/dynamics.py
@@ -0,0 +1,192 @@
+"""Battery dispatch dynamics, State-of-Charge tracking, and physical limits.
+
+Implements the single time-step battery dispatch algorithm (BAT-001) per
+decision [D-25], [D-26], and [D-31].
+"""
+
+from __future__ import annotations
+
+import math
+
+from ccis_sim.core.interfaces import BatteryStepResult
+from ccis_sim.core.models import Battery
+
+
+def step_battery(
+    soc_kwh: float,
+    battery: Battery,
+    charge_request_kwh: float,
+    discharge_request_kwh: float,
+    *,
+    soc_floor_kwh: float | None = None,
+    delta_t_hours: float = 1.0,
+) -> BatteryStepResult:
+    """Dispatches battery energy storage for a single discrete time-step.
+
+    Computes AC-side charge and discharge flows, shortfalls, and the resulting
+    chemical State-of-Charge (SoC) subject to physical inverter power limits
+    (C-rate), usable energy boundaries, and symmetric conversion efficiency.
+
+    [ASSUMPTION] Per decision [D-25], charge and discharge are modeled strictly
+    as AC-side flows (matching microgrid bus power conservation). Electrochemical
+    and power electronics conversion losses are accounted for symmetrically on the
+    chemical State-of-Charge:
+        eta_chg = eta_dis = sqrt(battery.round_trip_efficiency).
+    When charging:
+        Delta SoC = +eta_chg * charge_kwh
+    When discharging:
+        Delta SoC = -discharge_kwh / eta_dis
+
+    [ASSUMPTION] Idle losses, ambient self-discharge (2%/month), and inverter tare
+    standby losses are explicitly excluded from this module per [D-26] and are
+    managed independently by BAT-002 (ccis_sim.battery.reserve.apply_idle_losses).
+
+    [ASSUMPTION] Simultaneous charge and discharge requests exceeding 1e-6 kWh
+    each are physically mutually exclusive and raise a ValueError at the source.
+
+    [ASSUMPTION] Floating-point comparison tolerance fp_tol = 1e-9 is applied
+    to guard boundary evaluations against benign numerical representation noise.
+
+    Args:
+        soc_kwh: Stored chemical State-of-Charge at the start of the timestep (kWh).
+        battery: Battery specification defining capacity, C-rates, and efficiency.
+        charge_request_kwh: Desired AC-side energy to charge into the battery (kWh).
+        discharge_request_kwh: Desired AC-side energy to discharge from the battery (kWh).
+        soc_floor_kwh: Optional minimum allowable chemical SoC floor (kWh).
+            Defaults to battery.min_soc_kwh if None.
+        delta_t_hours: Timestep duration in hours (default 1.0).
+
+    Returns:
+        BatteryStepResult containing resulting chemical SoC, AC-side flows, and shortfalls.
+
+    Raises:
+        TypeError: If battery is not a Battery instance or numeric fields are invalid types.
+        ValueError: If non-finite values are passed, requests are negative, delta_t_hours <= 0,
+            or simultaneous charging and discharging is requested.
+    """
+    if not isinstance(battery, Battery):
+        raise TypeError(f"battery must be an instance of Battery, got {type(battery)}")
+
+    # Type and finiteness validation
+    for name, val in (
+        ("soc_kwh", soc_kwh),
+        ("charge_request_kwh", charge_request_kwh),
+        ("discharge_request_kwh", discharge_request_kwh),
+        ("delta_t_hours", delta_t_hours),
+    ):
+        if not isinstance(val, (int, float)):
+            raise TypeError(f"'{name}' must be numeric, got {type(val)}")
+        if math.isnan(val) or math.isinf(val):
+            raise ValueError(f"'{name}' must be finite, got {val}")
+
+    if delta_t_hours <= 0.0:
+        raise ValueError(f"delta_t_hours must be strictly positive, got {delta_t_hours}")
+
+    if charge_request_kwh < 0.0:
+        raise ValueError(f"charge_request_kwh must be non-negative, got {charge_request_kwh}")
+
+    if discharge_request_kwh < 0.0:
+        raise ValueError(f"discharge_request_kwh must be non-negative, got {discharge_request_kwh}")
+
+    fp_tol = 1e-9
+
+    # Physical boundary check on initial SoC
+    if soc_kwh < -fp_tol:
+        raise ValueError(f"soc_kwh cannot be physically negative, got {soc_kwh}")
+
+    # Mutual exclusivity check
+    if charge_request_kwh > 1e-6 and discharge_request_kwh > 1e-6:
+        raise ValueError(
+            f"Simultaneous charging ({charge_request_kwh:.6f} kWh) and discharging "
+            f"({discharge_request_kwh:.6f} kWh) is physically prohibited."
+        )
+
+    # Zero-capacity battery edge case (e.g. grid-only baseline per [D-23])
+    if battery.capacity_kwh == 0.0:
+        return BatteryStepResult(
+            soc_kwh=0.0,
+            charge_kwh=0.0,
+            discharge_kwh=0.0,
+            charge_curtailed_kwh=charge_request_kwh,
+            discharge_unmet_kwh=discharge_request_kwh,
+        )
+
+    if soc_kwh > battery.capacity_kwh + fp_tol:
+        raise ValueError(
+            f"soc_kwh ({soc_kwh:.6f} kWh) exceeds battery rated capacity "
+            f"({battery.capacity_kwh:.6f} kWh)."
+        )
+
+    # Validate soc_floor_kwh if provided
+    if soc_floor_kwh is not None:
+        if not isinstance(soc_floor_kwh, (int, float)):
+            raise TypeError(f"'soc_floor_kwh' must be numeric, got {type(soc_floor_kwh)}")
+        if math.isnan(soc_floor_kwh) or math.isinf(soc_floor_kwh):
+            raise ValueError(f"'soc_floor_kwh' must be finite, got {soc_floor_kwh}")
+        if soc_floor_kwh < -fp_tol:
+            raise ValueError(f"'soc_floor_kwh' cannot be physically negative, got {soc_floor_kwh}")
+        if soc_floor_kwh > battery.capacity_kwh + fp_tol:
+            raise ValueError(
+                f"'soc_floor_kwh' ({soc_floor_kwh:.6f} kWh) cannot exceed battery capacity "
+                f"({battery.capacity_kwh:.6f} kWh)."
+            )
+        effective_floor = max(0.0, min(battery.capacity_kwh, float(soc_floor_kwh)))
+    else:
+        effective_floor = battery.min_soc_kwh
+
+    # Clamp initial SoC within [0, capacity] to absorb fp noise
+    cur_soc = max(0.0, min(battery.capacity_kwh, float(soc_kwh)))
+
+    # Symmetric efficiency split per [D-25]
+    eta_chg = math.sqrt(battery.round_trip_efficiency)
+    eta_dis = math.sqrt(battery.round_trip_efficiency)
+
+    # 1. Evaluate Charge Operation
+    if charge_request_kwh > 1e-6:
+        # C-rate power cap (AC side)
+        max_charge_c_rate_kwh = battery.max_charge_power_kw * delta_t_hours
+        # Headroom cap in chemical energy converted to AC equivalent
+        headroom_chemical_kwh = max(0.0, battery.capacity_kwh - cur_soc)
+        max_charge_headroom_kwh = headroom_chemical_kwh / eta_chg
+
+        max_charge_allowed_kwh = min(max_charge_c_rate_kwh, max_charge_headroom_kwh)
+        actual_charge_kwh = min(charge_request_kwh, max_charge_allowed_kwh)
+
+        # Update State-of-Charge
+        delta_soc = actual_charge_kwh * eta_chg
+        new_soc = min(battery.capacity_kwh, cur_soc + delta_soc)
+
+        charge_curtailed_kwh = max(0.0, charge_request_kwh - actual_charge_kwh)
+
+        return BatteryStepResult(
+            soc_kwh=new_soc,
+            charge_kwh=actual_charge_kwh,
+            discharge_kwh=0.0,
+            charge_curtailed_kwh=charge_curtailed_kwh,
+            discharge_unmet_kwh=0.0,
+        )
+
+    # 2. Evaluate Discharge Operation
+    if discharge_request_kwh > 1e-6:
+        # C-rate power cap (AC side)
+        max_discharge_c_rate_kwh = battery.max_discharge_power_kw * delta_t_hours
+        # Available chemical energy above floor converted to AC equivalent
+        available_chemical_kwh = max(0.0, cur_soc - effective_floor)
+        max_discharge_floor_kwh = available_chemical_kwh * eta_dis
+
+        max_discharge_allowed_kwh = min(max_discharge_c_rate_kwh, max_discharge_floor_kwh)
+        actual_discharge_kwh = min(discharge_request_kwh, max_discharge_allowed_kwh)
+
+        # Update State-of-Charge
+        delta_soc = actual_discharge_kwh / eta_dis
+        new_soc = max(effective_floor, cur_soc - delta_soc) if cur_soc >= effective_floor else cur_soc
+
+        discharge_unmet_kwh = max(0.0, discharge_request_kwh - actual_discharge_kwh)
+
+        return BatteryStepResult(
+            soc_kwh=new_soc,
+            charge_kwh=0.0,
+            discharge_kwh=actual_discharge_kwh,
+            charge_curtailed_kwh=0.0,
+            discharge_unmet_kwh=discharge_unmet_kwh,
+        )
+
+    # 3. Idle / Zero-Flow Operation
+    return BatteryStepResult(
+        soc_kwh=cur_soc,
+        charge_kwh=0.0,
+        discharge_kwh=0.0,
+        charge_curtailed_kwh=charge_request_kwh,
+        discharge_unmet_kwh=discharge_request_kwh,
+    )
diff --git a/tests/test_battery_dynamics.py b/tests/test_battery_dynamics.py
new file mode 100644
index 0000000..ecb38c2
--- /dev/null
+++ b/tests/test_battery_dynamics.py
@@ -0,0 +1,368 @@
+"""Unit tests and property-based verification for BAT-001 Battery Dispatch Dynamics.
+
+Verifies step_battery efficiency split, C-rate limits, headroom/floor limits,
+simultaneous charge/discharge rejection, zero-capacity handling, and full
+invariant compliance against run_verification_harness.
+"""
+
+from __future__ import annotations
+
+import inspect
+import math
+
+import hypothesis
+import hypothesis.strategies as st
+import pytest
+
+from ccis_sim.battery.dynamics import step_battery
+from ccis_sim.core.interfaces import BatteryStepResult
+from ccis_sim.core.models import Battery, HourlyRecord, LoadTier
+from ccis_sim.core.verification import run_verification_harness
+
+
+@pytest.fixture
+def standard_battery() -> Battery:
+    """Standard 100 kWh, 92% RTE, 0.5C charge, 1.0C discharge battery."""
+    return Battery(
+        capacity_kwh=100.0,
+        round_trip_efficiency=0.92,
+        min_soc_pct=0.10,
+        max_charge_c_rate=0.5,
+        max_discharge_c_rate=1.0,
+    )
+
+
+def test_contract_signature_conformance() -> None:
+    """Validate that step_battery public signature conforms exactly to contract."""
+    sig = inspect.signature(step_battery)
+    params = list(sig.parameters.values())
+
+    assert len(params) == 6
+    assert params[0].name == "soc_kwh"
+    assert params[1].name == "battery"
+    assert params[2].name == "charge_request_kwh"
+    assert params[3].name == "discharge_request_kwh"
+    assert params[4].name == "soc_floor_kwh"
+    assert params[4].kind == inspect.Parameter.KEYWORD_ONLY
+    assert params[4].default is None
+    assert params[5].name == "delta_t_hours"
+    assert params[5].kind == inspect.Parameter.KEYWORD_ONLY
+    assert params[5].default == 1.0
+
+
+def test_efficiency_split_roundtrip(standard_battery: Battery) -> None:
+    """Verify symmetric sqrt(RTE) efficiency split per [D-25].
+
+    Charging with E_ac stores E_ac * sqrt(RTE) chemical kWh.
+    Discharging chemical energy back to initial SoC returns E_ac * RTE AC kWh.
+    """
+    initial_soc = 20.0
+    charge_req = 30.0  # AC kWh
+
+    eta = math.sqrt(standard_battery.round_trip_efficiency)
+
+    # 1. Charge step
+    res_chg = step_battery(
+        soc_kwh=initial_soc,
+        battery=standard_battery,
+        charge_request_kwh=charge_req,
+        discharge_request_kwh=0.0,
+    )
+    assert res_chg.charge_kwh == pytest.approx(charge_req)
+    assert res_chg.charge_curtailed_kwh == 0.0
+    expected_soc_after_chg = initial_soc + charge_req * eta
+    assert res_chg.soc_kwh == pytest.approx(expected_soc_after_chg)
+
+    # 2. Discharge step back to initial SoC
+    # To return to initial_soc, chemical energy to remove is charge_req * eta
+    # AC energy delivered will be (charge_req * eta) * eta = charge_req * RTE
+    res_dis = step_battery(
+        soc_kwh=res_chg.soc_kwh,
+        battery=standard_battery,
+        charge_request_kwh=0.0,
+        discharge_request_kwh=100.0,  # Request plenty
+        soc_floor_kwh=initial_soc,
+    )
+    expected_ac_delivered = charge_req * standard_battery.round_trip_efficiency
+    assert res_dis.discharge_kwh == pytest.approx(expected_ac_delivered)
+    assert res_dis.soc_kwh == pytest.approx(initial_soc)
+
+    # Round trip ratio
+    rte_observed = res_dis.discharge_kwh / res_chg.charge_kwh
+    assert rte_observed == pytest.approx(standard_battery.round_trip_efficiency)
+
+
+def test_c_rate_caps(standard_battery: Battery) -> None:
+    """Verify AC-side C-rate power caps (0.5C charge = 50 kW, 1.0C discharge = 100 kW)."""
+    # 1. Charge C-rate cap at delta_t = 1.0 h
+    res_chg = step_battery(
+        soc_kwh=10.0,
+        battery=standard_battery,
+        charge_request_kwh=80.0,
+        discharge_request_kwh=0.0,
+    )
+    assert res_chg.charge_kwh == pytest.approx(50.0)
+    assert res_chg.charge_curtailed_kwh == pytest.approx(30.0)
+
+    # 2. Charge C-rate cap at delta_t = 0.5 h (cap = 25 kWh)
+    res_chg_half = step_battery(
+        soc_kwh=10.0,
+        battery=standard_battery,
+        charge_request_kwh=40.0,
+        discharge_request_kwh=0.0,
+        delta_t_hours=0.5,
+    )
+    assert res_chg_half.charge_kwh == pytest.approx(25.0)
+    assert res_chg_half.charge_curtailed_kwh == pytest.approx(15.0)
+
+    # 3. Discharge C-rate cap at delta_t = 1.0 h
+    # Battery at 100 kWh, min SoC = 10 kWh -> 90 kWh chemical available
+    # 90 * sqrt(0.92) ~= 86.32 kWh AC, which is less than 100 kW * 1 h cap.
+    # To test discharge C-rate cap, use a 200 kWh battery where 0.5C charge / 1.0C discharge = 200 kW
+    # or test at delta_t = 0.5 h on standard battery where 1.0C * 100 kW * 0.5 h = 50 kWh cap.
+    res_dis_half = step_battery(
+        soc_kwh=100.0,
+        battery=standard_battery,
+        charge_request_kwh=0.0,
+        discharge_request_kwh=80.0,
+        delta_t_hours=0.5,
+    )
+    assert res_dis_half.discharge_kwh == pytest.approx(50.0)
+    assert res_dis_half.discharge_unmet_kwh == pytest.approx(30.0)
+
+
+def test_headroom_limiting(standard_battery: Battery) -> None:
+    """Verify that charging is strictly limited by remaining capacity headroom."""
+    eta = math.sqrt(standard_battery.round_trip_efficiency)
+    cur_soc = 95.0
+    headroom_chem = 5.0  # kWh chemical
+    max_ac_charge = headroom_chem / eta  # ~= 5.21286 kWh AC
+
+    res = step_battery(
+        soc_kwh=cur_soc,
+        battery=standard_battery,
+        charge_request_kwh=20.0,
+        discharge_request_kwh=0.0,
+    )
+    assert res.charge_kwh == pytest.approx(max_ac_charge)
+    assert res.soc_kwh == pytest.approx(100.0)
+    assert res.charge_curtailed_kwh == pytest.approx(20.0 - max_ac_charge)
+
+
+def test_floor_limiting(standard_battery: Battery) -> None:
+    """Verify that discharge is strictly bounded by minimum SoC floor."""
+    eta = math.sqrt(standard_battery.round_trip_efficiency)
+    # Default floor: battery.min_soc_kwh = 10.0 kWh
+    cur_soc = 15.0
+    avail_chem = 5.0
+    max_ac_discharge = avail_chem * eta
+
+    res = step_battery(
+        soc_kwh=cur_soc,
+        battery=standard_battery,
+        charge_request_kwh=0.0,
+        discharge_request_kwh=20.0,
+    )
+    assert res.discharge_kwh == pytest.approx(max_ac_discharge)
+    assert res.soc_kwh == pytest.approx(10.0)
+    assert res.discharge_unmet_kwh == pytest.approx(20.0 - max_ac_discharge)
+
+    # Custom higher floor (e.g. 20 kWh)
+    res_custom = step_battery(
+        soc_kwh=cur_soc,
+        battery=standard_battery,
+        charge_request_kwh=0.0,
+        discharge_request_kwh=20.0,
+        soc_floor_kwh=20.0,
+    )
+    # Since cur_soc (15.0) < floor (20.0), available is 0
+    assert res_custom.discharge_kwh == 0.0
+    assert res_custom.soc_kwh == 15.0
+    assert res_custom.discharge_unmet_kwh == 20.0
+
+    # Emergency drawdown floor down to 0.0 kWh
+    res_emergency = step_battery(
+        soc_kwh=10.0,
+        battery=standard_battery,
+        charge_request_kwh=0.0,
+        discharge_request_kwh=20.0,
+        soc_floor_kwh=0.0,
+    )
+    assert res_emergency.discharge_kwh == pytest.approx(10.0 * eta)
+    assert res_emergency.soc_kwh == pytest.approx(0.0)
+
+
+def test_simultaneous_request_rejected(standard_battery: Battery) -> None:
+    """Verify that simultaneous charge and discharge requests (> 1e-6 kWh) raise ValueError."""
+    with pytest.raises(ValueError, match="Simultaneous charging.*discharging.*prohibited"):
+        step_battery(
+            soc_kwh=50.0,
+            battery=standard_battery,
+            charge_request_kwh=5.0,
+            discharge_request_kwh=5.0,
+        )
+
+
+def test_zero_capacity_case() -> None:
+    """Verify zero-capacity battery handles all flows as zero and SoC as zero."""
+    zero_bat = Battery(capacity_kwh=0.0, round_trip_efficiency=0.92, min_soc_pct=0.10)
+    res = step_battery(
+        soc_kwh=0.0,
+        battery=zero_bat,
+        charge_request_kwh=15.0,
+        discharge_request_kwh=0.0,
+    )
+    assert res.soc_kwh == 0.0
+    assert res.charge_kwh == 0.0
+    assert res.charge_curtailed_kwh == 15.0
+
+    res_dis = step_battery(
+        soc_kwh=0.0,
+        battery=zero_bat,
+        charge_request_kwh=0.0,
+        discharge_request_kwh=10.0,
+    )
+    assert res_dis.soc_kwh == 0.0
+    assert res_dis.discharge_kwh == 0.0
+    assert res_dis.discharge_unmet_kwh == 10.0
+
+
+def test_input_validation_and_errors(standard_battery: Battery) -> None:
+    """Verify parameter type, finiteness, and negative value checks."""
+    # Not a Battery instance
+    with pytest.raises(TypeError, match="battery must be an instance of Battery"):
+        step_battery(soc_kwh=10.0, battery="not_a_battery", charge_request_kwh=1.0, discharge_request_kwh=0.0)  # type: ignore
+
+    # Non-finite values
+    with pytest.raises(ValueError, match="must be finite"):
+        step_battery(soc_kwh=float("nan"), battery=standard_battery, charge_request_kwh=0.0, discharge_request_kwh=0.0)
+    with pytest.raises(ValueError, match="must be finite"):
+        step_battery(soc_kwh=10.0, battery=standard_battery, charge_request_kwh=float("inf"), discharge_request_kwh=0.0)
+
+    # Negative values
+    with pytest.raises(ValueError, match="non-negative"):
+        step_battery(soc_kwh=10.0, battery=standard_battery, charge_request_kwh=-1.0, discharge_request_kwh=0.0)
+    with pytest.raises(ValueError, match="non-negative"):
+        step_battery(soc_kwh=10.0, battery=standard_battery, charge_request_kwh=0.0, discharge_request_kwh=-1.0)
+    with pytest.raises(ValueError, match="strictly positive"):
+        step_battery(soc_kwh=10.0, battery=standard_battery, charge_request_kwh=0.0, discharge_request_kwh=0.0, delta_t_hours=0.0)
+
+    # Initial SoC out of range
+    with pytest.raises(ValueError, match="exceeds battery rated capacity"):
+        step_battery(soc_kwh=150.0, battery=standard_battery, charge_request_kwh=0.0, discharge_request_kwh=0.0)
+    with pytest.raises(ValueError, match="cannot be physically negative"):
+        step_battery(soc_kwh=-5.0, battery=standard_battery, charge_request_kwh=0.0, discharge_request_kwh=0.0)
+
+    # soc_floor_kwh out of range
+    with pytest.raises(ValueError, match="cannot exceed battery capacity"):
+        step_battery(soc_kwh=50.0, battery=standard_battery, charge_request_kwh=0.0, discharge_request_kwh=0.0, soc_floor_kwh=120.0)
+    with pytest.raises(ValueError, match="cannot be physically negative"):
+        step_battery(soc_kwh=50.0, battery=standard_battery, charge_request_kwh=0.0, discharge_request_kwh=0.0, soc_floor_kwh=-1.0)
+
+
+def test_determinism(standard_battery: Battery) -> None:
+    """Verify identical inputs yield identical outputs bit-for-bit."""
+    reqs = [(10.0, 0.0), (30.0, 0.0), (0.0, 25.0), (0.0, 0.0), (5.0, 0.0)]
+    soc_run1 = 20.0
+    results_run1 = []
+    for chg, dis in reqs:
+        res = step_battery(soc_kwh=soc_run1, battery=standard_battery, charge_request_kwh=chg, discharge_request_kwh=dis)
+        results_run1.append(res)
+        soc_run1 = res.soc_kwh
+
+    soc_run2 = 20.0
+    results_run2 = []
+    for chg, dis in reqs:
+        res = step_battery(soc_kwh=soc_run2, battery=standard_battery, charge_request_kwh=chg, discharge_request_kwh=dis)
+        results_run2.append(res)
+        soc_run2 = res.soc_kwh
+
+    for r1, r2 in zip(results_run1, results_run2):
+        assert r1 == r2
+
+
+@hypothesis.given(
+    requests=st.lists(
+        st.tuples(
+            st.floats(min_value=0.0, max_value=80.0, allow_nan=False, allow_infinity=False),
+            st.booleans(),  # True for charge, False for discharge
+        ),
+        min_size=10,
+        max_size=48,
+    )
+)
+@hypothesis.settings(max_examples=40, deadline=None)
+def test_hypothesis_property_verification_harness(requests: list[tuple[float, bool]]) -> None:
+    """Property test: arbitrary charge/discharge sequences chained over hours pass the verification harness."""
+    battery = Battery(
+        capacity_kwh=100.0,
+        round_trip_efficiency=0.92,
+        min_soc_pct=0.10,
+        max_charge_c_rate=0.5,
+        max_discharge_c_rate=1.0,
+        self_discharge_pct_per_month=0.0,  # Dynamics module does not apply idle losses
+        tare_loss_kw=0.0,
+    )
+
+    initial_soc = 50.0
+    cur_soc = initial_soc
+    records: list[HourlyRecord] = []
+
+    for hour_idx, (magnitude, is_charge) in enumerate(requests, start=1):
+        chg_req = magnitude if is_charge else 0.0
+        dis_req = magnitude if not is_charge else 0.0
+
+        step_res = step_battery(
+            soc_kwh=cur_soc,
+            battery=battery,
+            charge_request_kwh=chg_req,
+            discharge_request_kwh=dis_req,
+        )
+
+        cur_soc = step_res.soc_kwh
+
+        # Construct a physically balanced HourlyRecord around this battery step
+        solar_gen = step_res.charge_kwh
+        solar_to_battery = step_res.charge_kwh
+        curtailed = step_res.charge_curtailed_kwh
+
+        demand_gross = step_res.discharge_kwh
+        demand_served = step_res.discharge_kwh
+        unserved = step_res.discharge_unmet_kwh
+
+        record = HourlyRecord(
+            hour=hour_idx,
+            timestamp=f"2019-01-01 {hour_idx-1:02d}:00:00+08:00",
+            temp_ambient_c=25.0,
+            humidity_rel_pct=60.0,
+            ghi_w_m2=0.0,
+            demand_gross_kwh=demand_gross,
+            demand_served_kwh=demand_served,
+            solar_generation_kwh=solar_gen,
+            solar_to_demand_kwh=0.0,
+            solar_to_battery_kwh=solar_to_battery,
+            solar_curtailed_kwh=0.0,  # Battery step curtailment isn't solar curtailment unless on bus
+            battery_soc_kwh=step_res.soc_kwh,
+            battery_charge_kwh=step_res.charge_kwh,
+            battery_discharge_kwh=step_res.discharge_kwh,
+            grid_import_kwh=0.0,
+            unserved_load_kwh=0.0,
+            grid_available=True,
+            active_load_tier=LoadTier.TIER_3_SHEDDABLE,
+        )
+        records.append(record)
+
+    # Invariant harness evaluation
+    report = run_verification_harness(
+        records,
+        battery=battery,
+        initial_soc_kwh=initial_soc,
+    )
+    assert report.is_valid, (
+        f"Verification harness found violations: "
+        f"conservation={report.conservation_violations}, "
+        f"battery={report.battery_violations}, "
+        f"subflow={report.subflow_violations}, "
+        f"cum_drift={report.cumulative_net_drift_kwh}"
+    )
```

---

## 6. Flagged for APC / Operator Attention

- [x] **No contract alterations:** `step_battery` strictly satisfies `docs/context/phase2-interface-contract.md`.
- [x] **Idle Loss Separation:** Confirmed that ambient self-discharge and tare losses are omitted from `step_battery` and left for `BAT-002` (`apply_idle_losses`) per `[D-26]`.
- [x] **Reserved Decision `[D-31]`:** Recorded in `docs/decisions/decision-log.md` with no collisions.
