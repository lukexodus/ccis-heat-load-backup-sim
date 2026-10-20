# Task Report: CORE-006 — Phase 2 Interface Contracts & Harness Idle-Loss Allowance

**Date:** 2026-10-20  
**Agent:** gemini  
**Task ID:** CORE-006  
**Status:** done  
**Commit:** `feat(CORE-006): define Phase 2 interface contracts and implement harness idle-loss allowance`  
**Patch File:** `patch/CORE-006-gemini-phase2-contracts.patch`  

---

## 1. Executive Summary

This unit of work completes task `CORE-006` ("Phase 2 Interface Contracts & Harness Idle-Loss Allowance"), establishing the canonical interface contracts, shared data shapes, function signatures, and harness idle-loss verification invariants required prior to dispatching the eight parallel Phase 2 sub-model tracks (`DEM-001`, `DEM-002`, `SOL-001`, `SOL-002`, `BAT-001`, `BAT-002`, `OUT-001`, `OUT-002`).

Specifically, it delivers:
1. **Canonical Shared Interface Types (`src/ccis_sim/core/interfaces.py`)**: Defines immutable frozen dataclasses for inter-track communication:
   - `TieredDemand(tier1_kwh, tier2_kwh, tier3_kwh)` with `gross_kwh` property and `at(i)` indexing method.
   - `OccupancySchedule(occupancy_fraction, is_class_day, is_break, is_holiday)` with float bounds $[0.0, 1.0]$ and boolean flags.
   - `OutageSchedule(events, grid_available, year_type, ghi_multiplier)` with default unit solar multipliers and regime validation.
   - `BatteryStepResult(soc_kwh, charge_kwh, discharge_kwh, charge_curtailed_kwh, discharge_unmet_kwh)` representing AC-side achieved flows and shortfalls with mutual charge/discharge exclusion.
   - `ShedResult(active_tier, served_kwh, unserved_kwh)` capturing per-tier served and unserved allocations under load shedding.
2. **Contract Specification Document (`docs/context/phase2-interface-contract.md`)**: Formally documents exact module targets, function signatures, pure function conventions, explicit deterministic PRNG passing, weather dataframe column standards, cross-track decoupling rules, and the complete `INT-001` hourly dispatch loop.
3. **Battery Model Idle-Loss Parameters (`[D-26]`)**: Added `self_discharge_pct_per_month: float = 2.0` (LFP ambient self-discharge) and `tare_loss_kw: float = 0.0` (BMS/inverter standby consumption) to `Battery` in `src/ccis_sim/core/models.py`. Both are modeled strictly on the stored chemical SoC-side.
4. **Harness Idle-Loss Allowance & Cumulative Drift Invariant (`[D-26]`)**:
   - Upgraded hour-to-hour State-of-Charge continuity checking in `validate_battery_boundaries` to be one-sided with a maximum idle dissipation allowance $\Delta E_{\text{idle, max}} = \left(\frac{C_{\text{bat}} \cdot r_{\text{self}}}{730} + P_{\text{tare}}\right) \Delta t$. SoC may never exceed the ideal lossless recursion ($SoC_t \le SoC_{t, \text{ideal}} + \epsilon$).
   - Implemented cumulative continuity drift checking (`ViolationType.SOC_CUMULATIVE_DRIFT`), bounding total accumulated drift across $N$ hours by total allowed idle loss plus $\max(\epsilon, \sqrt{N}\epsilon)$.

All 120 tests in the test suite pass cleanly (100% green).

---

## 2. Implementation Details

### 2.1 Files Created or Modified

- `src/ccis_sim/core/interfaces.py`: Created shared frozen dataclasses (`TieredDemand`, `OccupancySchedule`, `OutageSchedule`, `BatteryStepResult`, `ShedResult`) with comprehensive `__post_init__` input validations (length matching, non-empty, non-finite rejection, non-negative bounds).
- `src/ccis_sim/core/__init__.py`: Exported all five shared interface dataclasses.
- `src/ccis_sim/core/models.py`: Added `self_discharge_pct_per_month: float = 2.0` and `tare_loss_kw: float = 0.0` attributes to `Battery` with non-negative validation in `__post_init__`.
- `src/ccis_sim/core/verification.py`:
  - Added `ViolationType.SOC_CUMULATIVE_DRIFT`.
  - Updated `validate_battery_boundaries` with nominal 730 h/month idle-loss rate calculation, one-sided continuity check, and cumulative continuity drift verification.
- `docs/context/phase2-interface-contract.md`: Created interface contract document detailing function signatures, track coupling rules, and INT-001 hourly loop diagram.
- `docs/decisions/decision-log.md`: Recorded decision `[D-26]`.
- `docs/tasks/status.md`: Added `CORE-006` row and subtasks (`CORE-006.1`–`CORE-006.3`).
- `tests/test_interfaces.py`: Created 9 dedicated unit tests covering valid instantiation and validation error modes for all new interface types.
- `tests/test_conservation_checker.py`: Added 4 unit tests verifying idle-loss allowance, excessive idle loss detection, upward SoC excursion detection, and 8,760-hour cumulative drift trapping.

### 2.2 Conformance to Specifications & Decisions

- **[D-26] Idle Loss Convention:** Self-discharge and tare loss are modeled on the chemical SoC-side. This ensures internal cell dissipation reduces stored energy without distorting AC-side microgrid bus balances.
- **[D-26] One-Sided Continuity Formulation:**
  $$0 - \epsilon \le \text{SoC}_{t, \text{ideal}} - \text{SoC}_t \le \Delta E_{\text{idle, max}} + \epsilon$$
  When idle loss parameters are zero, the upper limit collapses to $\epsilon$, exactly preserving previous behavior.
- **Pure Function Conventions:** All interface types operate purely on numpy arrays and dataclasses without file I/O or global RNG.

---

## 3. Verification & Test Evidence

### 3.1 Test Execution

Command executed:
```bash
pytest -v
```

**Results:**
- Tests passed: 120
- Tests failed: 0
- Tests skipped: 0
- Duration: 11.17s

Verbatim test output excerpt:
```text
============================= test session starts ==============================
platform linux -- Python 3.14.8, pytest-9.1.1, pluggy-1.6.0
rootdir: /home/lukexodus/projects/ccis-heat-load-backup-sim-CORE-006
configfile: pyproject.toml
collected 120 items

tests/test_baseline_smoke.py ........                                    [  6%]
tests/test_conservation_checker.py ........................              [ 26%]
tests/test_core_models.py ...................                            [ 42%]
tests/test_equipment_audit.py ....................                      [ 59%]
tests/test_interfaces.py .........                                       [ 66%]
tests/test_mock_bills.py ........                                        [ 73%]
tests/test_smoke.py ...........                                          [ 82%]
tests/test_weather_ingest.py ......................                      [100%]

============================= 120 passed in 11.17s =============================
```

### 3.2 Edge Cases & Negative Testing

1. **`test_tiered_demand_validation_errors`**: Validates that `TieredDemand` rejects mismatched array lengths, empty arrays, non-finite values (NaN/inf), and negative demands.
2. **`test_occupancy_schedule_validation_errors`**: Confirms `OccupancySchedule` rejects occupancy fractions outside $[0.0, 1.0]$ and mismatched lengths.
3. **`test_outage_schedule_validation_errors`**: Confirms rejection of invalid `year_type` strings, negative GHI multipliers, and length mismatches.
4. **`test_battery_step_result_valid_and_mutual_exclusion`**: Verifies that simultaneous battery charging and discharging in the same hour is rejected.
5. **`test_shed_result_valid_and_validation_errors`**: Validates active tier range check and tuple length constraints.
6. **`test_soc_continuity_idle_loss_passes`**: Confirms a battery with physical self-discharge and tare loss within limits passes continuity without violations.
7. **`test_soc_continuity_excessive_idle_loss_fails`**: Confirms that losing SoC faster than the computed maximum idle dissipation trips `ViolationType.SOC_CONTINUITY`.
8. **`test_soc_continuity_higher_than_ideal_recursion_fails`**: Confirms that unphysical SoC creation trips `ViolationType.SOC_CONTINUITY`.
9. **`test_soc_cumulative_drift_bias_trips`**: Confirms that an 8,760-hour series with a subtle $0.9 \times 10^{-5}\text{ kWh/h}$ bias passes every individual hourly check but is trapped by `ViolationType.SOC_CUMULATIVE_DRIFT`.

---

## 4. Decisions Recorded

- **[D-26]**: Phase 2 Interface Contracts, Battery Idle-Loss Convention, and Cumulative Continuity Drift Invariant.
  - Locked shared types in `src/ccis_sim/core/interfaces.py`.
  - Locked function signatures in `docs/context/phase2-interface-contract.md`.
  - Added `self_discharge_pct_per_month: float = 2.0` and `tare_loss_kw: float = 0.0` to `Battery`.
  - Codified SoC-side standby loss convention.
  - Implemented one-sided continuity check with idle allowance ($\Delta E_{\text{idle, max}}$).
  - Implemented cumulative continuity drift check (`ViolationType.SOC_CUMULATIVE_DRIFT`).

---

## 5. Unified Git Diff

```diff
diff --git a/docs/context/phase2-interface-contract.md b/docs/context/phase2-interface-contract.md
new file mode 100644
index 0000000..f9864aa
--- /dev/null
+++ b/docs/context/phase2-interface-contract.md
@@ -0,0 +1,114 @@
+# Phase 2 Interface Contracts & Integration Architecture Specification
+
+**Document Version:** 1.0.0  
+**Status:** Locked per Decision [D-26] (CORE-006)  
+**Applies to:** Phase 2 Sub-Model Tracks (`DEM-001`, `DEM-002`, `SOL-001`, `SOL-002`, `BAT-001`, `BAT-002`, `OUT-001`, `OUT-002`) and Phase 3 Integration (`INT-001`).
+
+---
+
+## 1. Executive Summary & Purpose
+
+Phase 2 decomposes the CCIS microgrid simulation into eight parallel tracks implemented concurrently by local agents. To guarantee seamless integration under `INT-001` and eliminate API divergence, this contract locks:
+1. **Canonical Shared Data Structures** (`ccis_sim.core.interfaces`): Immutable numpy array containers for tiered demand, academic calendars, outage schedules, battery dispatch results, and load shedding outcomes.
+2. **Sub-Model Function Signatures**: Exact function names, arguments, keyword-only parameters, and return types across all eight track modules.
+3. **Execution Conventions & Design Rules**: Pure functions, explicit RNG passing, immutable inputs, and weather dataframe column standards.
+4. **The INT-001 Hourly Dispatch Sequence**: How all eight sub-models compose inside the annual time loop to produce valid `HourlyRecord` streams.
+
+---
+
+## 2. Core Operational Conventions
+
+All Phase 2 sub-models must strictly adhere to the following principles:
+- **Pure Functions:** Sub-model logic must have no side effects, no global state, and no file I/O inside domain calculation routines (data loading is isolated to loaders and test harnesses).
+- **Explicit Deterministic PRNG:** Stochastic routines (`OUT-001`) must never invoke `random.*` or `np.random.*` globally; they must accept an explicit `rng: numpy.random.Generator` instance.
+- **Input Immutability:** Functions must treat input dataframes, arrays, and dataclasses as strictly read-only.
+- **Weather DataFrame Contract:** Weather inputs must use verified column names provided by `load_weather_fixture`:
+  - `hour`: Integer chronological hour index ($1 \dots 8760$).
+  - `timestamp`: ISO 8601 string (`YYYY-MM-DDTHH:MM:SS+08:00`).
+  - `t_amb`: Ambient dry-bulb temperature in degrees Celsius (°C).
+  - `rh`: Relative humidity percentage ($0.0 \dots 100.0\%$).
+  - `ghi`: Global Horizontal Irradiance in watts per square meter ($\text{W/m}^2$).
+- **Array Conventions:** Hourly time-series arrays are 1D `numpy.ndarray` instances of length $N = 8,760$ (index $i$ represents hour $i + 1$). Flow rates are in kilowatt-hours per hour ($\text{kWh/h} \equiv \text{kW}$ at $\Delta t = 1.0\text{ h}$).
diff --git a/docs/decisions/decision-log.md b/docs/decisions/decision-log.md
index 106d7bb..3df2d55 100644
--- a/docs/decisions/decision-log.md
+++ b/docs/decisions/decision-log.md
@@ -213,4 +213,18 @@
 
+**[D-26]** Phase 2 Interface Contracts, Battery Idle-Loss Convention, and Cumulative Continuity Drift Invariant.  
+- **Date / Session:** 2026-10-20  
+- **Decision:**  
+  1. **Phase 2 Interface Contracts:** Formalized canonical shared data structures in `src/ccis_sim/core/interfaces.py` (`TieredDemand`, `OccupancySchedule`, `OutageSchedule`, `BatteryStepResult`, `ShedResult`) and locked function signatures and cross-track integration contracts in `docs/context/phase2-interface-contract.md`.
+  2. **Battery Idle-Loss Attributes:** Added `self_discharge_pct_per_month: float = 2.0` (ambient monthly self-discharge) and `tare_loss_kw: float = 0.0` (inverter/BMS standby loss) to the `Battery` dataclass. Both attributes are validated non-negative.
+  3. **SoC-Side Standby Loss Assumption:** Tare loss and self-discharge are modeled strictly as **SoC-side** standby losses (electrochemical and internal dissipation). This ensures internal dissipation reduces stored chemical State-of-Charge without introducing phantom AC-side electrical demand on the microgrid bus, preserving exact AC bus energy balance.
+  4. **One-Sided Continuity with Idle Allowance:** Updated hour-to-hour battery State-of-Charge continuity verification to be one-sided with a physical idle-loss allowance:
+     $$0 - \epsilon \le \text{SoC}_{t, \text{ideal}} - \text{SoC}_t \le \Delta E_{\text{idle, max}} + \epsilon$$
+     where $\Delta E_{\text{idle, max}} = \left(\frac{C_{\text{bat}} \cdot r_{\text{self}}}{730} + P_{\text{tare}}\right) \Delta t$, based on 730 hours per nominal month ($8,760\text{ h} / 12$). Stored chemical SoC may never exceed the lossless ideal recursion ($SoC_t \le SoC_{t, \text{ideal}} + \epsilon$). When idle loss parameters are zero, the formulation collapses identically to the bilateral tolerance of [D-25].
+  5. **Cumulative Continuity Drift Invariant:** Accumulated step differences $\sum (\text{SoC}_{\text{ideal}} - \text{SoC})$ across $N$ evaluated hours must not exceed total allowed idle loss plus the statistical cumulative tolerance $\max(\epsilon, \sqrt{N}\epsilon)$ per [D-21]. Unaccounted cumulative leakage or upward drift trips `ViolationType.SOC_CUMULATIVE_DRIFT`.
+- **Reasoning:** Establishes unambiguous API contracts across all eight parallel Phase 2 sub-models to prevent divergence, while closing physical verification blind spots for standby battery self-discharge and cumulative SoC drift prior to BAT-001/002.
+- **Affects:** `CORE-006`, `DEM-001`, `DEM-002`, `SOL-001`, `SOL-002`, `BAT-001`, `BAT-002`, `OUT-001`, `OUT-002`, `INT-001`, `INT-003`.
diff --git a/docs/tasks/status.md b/docs/tasks/status.md
index 8e0e7a2..1ebcb23 100644
--- a/docs/tasks/status.md
+++ b/docs/tasks/status.md
@@ -70,2 +70,6 @@
 | CORE-005.3   | Generate baseline summary metrics (annual kWh, peak kW, base EUI)                | `done` | 398,525 kWh/yr, 159.41 EUI, 124.44 kW peak, 2016 sensitivity                                                      |
+| **CORE-006** | **Phase 2 Interface Contracts & Harness Idle-Loss Allowance**                    | `done` | [CORE-006-gemini-phase2-contracts.md](../reports/CORE-006-gemini-phase2-contracts.md) [D-26]                      |
+| CORE-006.1   | Define shared interface types in `interfaces.py`                                 | `done` | TieredDemand, OccupancySchedule, OutageSchedule, BatteryStepResult, ShedResult                                    |
+| CORE-006.2   | Author Phase 2 interface contract document                                       | `done` | [phase2-interface-contract.md](../context/phase2-interface-contract.md) locked signatures & dispatch loop          |
+| CORE-006.3   | Harness idle-loss allowance and cumulative SoC continuity drift                  | `done` | One-sided continuity, idle allowance, and SOC_CUMULATIVE_DRIFT [D-26]                                              |
diff --git a/src/ccis_sim/core/__init__.py b/src/ccis_sim/core/__init__.py
index 58bc535..60a1c62 100644
--- a/src/ccis_sim/core/__init__.py
+++ b/src/ccis_sim/core/__init__.py
@@ -1,5 +1,12 @@
 """Core domain models, interface protocols, and conservation invariants."""
 
+from ccis_sim.core.interfaces import (
+    BatteryStepResult,
+    OccupancySchedule,
+    OutageSchedule,
+    ShedResult,
+    TieredDemand,
+)
 from ccis_sim.core.models import (
diff --git a/src/ccis_sim/core/interfaces.py b/src/ccis_sim/core/interfaces.py
new file mode 100644
index 0000000..f5c1d68
--- /dev/null
+++ b/src/ccis_sim/core/interfaces.py
@@ -0,0 +1,228 @@
+"""Shared interface types and data contracts for Phase 2 parallel sub-models."""
diff --git a/src/ccis_sim/core/models.py b/src/ccis_sim/core/models.py
index 0112cb9..c40751e 100644
--- a/src/ccis_sim/core/models.py
+++ b/src/ccis_sim/core/models.py
@@ -123,2 +123,4 @@ class Battery:
     emergency_reserve_pct: float = 0.20      # [D-17] Default 20% emergency blackout reserve (configurable in [0.10, 0.50] for BAT-002)
+    self_discharge_pct_per_month: float = 2.0  # [D-26] Monthly ambient self-discharge rate (default 2.0%/month for LFP)
+    tare_loss_kw: float = 0.0                # [D-26] Standby tare loss in kW (inverter/BMS tare modeled on SoC-side)
diff --git a/src/ccis_sim/core/verification.py b/src/ccis_sim/core/verification.py
index c839fe1..92cf4a6 100644
--- a/src/ccis_sim/core/verification.py
+++ b/src/ccis_sim/core/verification.py
@@ -30,2 +30,3 @@ class ViolationType(str, Enum):
     SOC_CONTINUITY = "soc_continuity"
+    SOC_CUMULATIVE_DRIFT = "soc_cumulative_drift"
     NON_FINITE_VALUE = "non_finite_value"
```

---

## 6. Flagged for APC / Operator Attention

- [x] **Zero Conflict in Reservation:** `[D-26]` claimed and recorded cleanly with zero ID collision.
- [x] **Zero Double-Counting of Thermal Losses:** Explicitly mandated in `docs/context/phase2-interface-contract.md` §4 that `SOL-002` must isolate non-thermal balance-of-system factors from the baseline $PR = 0.77$ to avoid double-counting cell temperature derates from `SOL-001`.
- [x] **Phase 2 Track Readiness:** With `CORE-006` completed and tested, all Phase 2 tracks (`DEM-001`, `DEM-002`, `SOL-001`, `SOL-002`, `BAT-001`, `BAT-002`, `OUT-001`, `OUT-002`) are unblocked to proceed in parallel.
